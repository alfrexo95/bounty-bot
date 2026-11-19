import re
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import GRPOConfig, GRPOTrainer

# --- Reward Functions ---

def format_reward_func(completions, **kwargs) -> list[float]:
    """
    Rewards completions that follow the <thought>\n...\n</thought>\n<answer>\n...\n</answer> format.
    """
    pattern = r"^<thought>\n.*?\n</thought>\n<answer>\n.*?\n</answer>$"
    responses = [completion[0]["content"] for completion in completions]
    return [1.0 if re.match(pattern, r, re.DOTALL) else 0.0 for r in responses]

def correctness_reward_func(queries, completions, answer, **kwargs) -> list[float]:
    """
    Rewards completions that contain the correct numerical answer within the <answer> tags.
    """
    responses = [completion[0]["content"] for completion in completions]
    extracted_answers = []
    for r in responses:
        match = re.search(r"<answer>\n(.*?)\n</answer>", r, re.DOTALL)
        extracted_answers.append(match.group(1).strip() if match else "")
    
    return [2.0 if r == a else 0.0 for r, a in zip(extracted_answers, answer)]

def soft_format_reward_func(completions, **kwargs) -> list[float]:
    """
    Partial reward for including tags at all, even if the full structure is wrong.
    """
    responses = [completion[0]["content"] for completion in completions]
    rewards = []
    for r in responses:
        reward = 0.0
        if "<thought>" in r: reward += 0.2
        if "</thought>" in r: reward += 0.2
        if "<answer>" in r: reward += 0.2
        if "</answer>" in r: reward += 0.2
        rewards.append(reward)
    return rewards

# --- Training Pipeline ---

def train():
    model_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B" # Default base
    
    # 1. Load Dataset (GSM8K for math reasoning)
    dataset = load_dataset("openai/gsm8k", "main", split="train")
    
    def format_dataset(examples):
        return {
            "prompt": [
                {"role": "system", "content": "You are a helpful assistant that thinks step-by-step. Provide your reasoning inside <thought> tags and the final answer inside <answer> tags."},
                {"role": "user", "content": q}
            ] for q in examples["question"]
        }, {"answer": examples["answer"]}

    # 2. Configure Model & Tokenizer
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )
    
    model = prepare_model_for_kbit_training(model)
    
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # 3. GRPO Configuration
    training_args = GRPOConfig(
        output_dir="output/grpo-reasoning-model",
        learning_rate=5e-6,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        max_prompt_length=256,
        max_completion_length=512,
        num_generations=8, # Group size for GRPO
        beta=0.04, # KL divergence coefficient
        optim="adamw_8bit",
        logging_steps=10,
        bf16=True,
        remove_unused_columns=False,
    )

    # 4. Initialize Trainer
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=[
            format_reward_func,
            correctness_reward_func,
            soft_format_reward_func
        ],
        args=training_args,
        train_dataset=dataset,
        peft_config=peft_config,
    )

    # 5. Run Training
    trainer.train()
    trainer.save_model("output/grpo-reasoning-model-final")

if __name__ == "__main__":
    train()
