import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def test_reasoning(model_path):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, 
        torch_dtype=torch.bfloat16, 
        device_map="auto"
    )

    prompt = "If I have 3 apples and buy 2 more, then eat 1, how many do I have?"
    messages = [
        {"role": "system", "content": "You are a helpful assistant that thinks step-by-step. Provide your reasoning inside <thought> tags and the final answer inside <answer> tags."},
        {"role": "user", "content": prompt}
    ]
    
    inputs = tokenizer.apply_chat_template(messages, return_tensors="pt").to("cuda")
    outputs = model.generate(inputs, max_new_tokens=500, do_sample=True, temperature=0.7)
    
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

if __name__ == "__main__":
    # Path to the trained LoRA adapter or merged model
    # test_reasoning("output/grpo-reasoning-model-final")
    pass
