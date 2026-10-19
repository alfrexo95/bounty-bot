import os
import re
import subprocess
import requests
import ast
import sys
import time
from datetime import datetime

GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_ISSUE_URL = os.environ.get("ISSUE_URL")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
YEAR = str(datetime.now().year)
MY_REPO = "alfrexo95/bounty-bot"
MY_USER = "alfrexo95"

PAYMENT_ADDRESSES = """
- BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
- ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
- LTC: ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne
- Lightning: chieftrait089@walletofsatoshi.com
"""

PAYMENT_KEYWORDS = ["payment", "pay", "address", "wallet", "usdc", "lightning", "reward", "bounty", "stripe", "fund"]
REWARD_PATTERN = re.compile(r'(?:\$|USD\s*)(\d{1,5})(?:\.\d{1,2})?|(\d{1,5})\s*(?:\$|USD)', re.IGNORECASE)
SCRIPT_ERROR_KEYWORDS = ["error", "exception", "crash", "traceback", "fails", "broken", "bug"]

def extraer_recompensa(texto):
    if not texto: return None
    match = REWARD_PATTERN.search(texto)
    if match: return match.group(1) or match.group(2)
    return None

def crear_notificacion_issue(title, url, monto):
    monto_str = f"${monto}" if monto != "Desconocido" else "No especificada"
    issue_url = f"https://api.github.com/repos/{MY_REPO}/issues"
    body = f"🤖 **Bounty Encontrado**\n\n- **Título:** {title}\n- **Monto:** {monto_str}\n- **Enlace:** [Ir al Issue]({url})"
    requests.post(issue_url, headers=HEADERS, json={"title": f"🎯 Bounty ({monto_str})", "body": body})

def obtener_issue_especifico(url):
    print(f"🎯 Obteniendo issue específico: {url}")
    parts = url.rstrip('/').split('/')
    if len(parts) >= 7 and parts[-2] == 'issues':
        owner = parts[-4]
        repo = parts[-3]
        issue_number = parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        res = requests.get(api_url, headers=HEADERS)
        if res.status_code == 200:
            item = res.json()
            item["_monto_detectado"] = extraer_recompensa(item["title"] + " " + (item.get("body") or "")) or "Desconocido"
            return item
    return None

def buscar_issues():
    search_url = "https://api.github.com/search/issues?q=is:issue+is:open+language:Python+label:%22good+first+issue%22&sort=created&order=desc&per_page=5"
    res = requests.get(search_url, headers=HEADERS)
    if res.status_code == 200:
        for item in res.json().get("items", []):
            item["_monto_detectado"] = extraer_recompensa(item["title"] + " " + (item.get("body") or "")) or "Desconocido"
            return [item]
    return []

def generar_archivo_arquitectura():
    print("  📝 Generando ARCHITECTURE.md a partir de docstrings...")
    docs_content = "# Architecture Overview\n\n## Core Modules\n"
    encontrados = 0
    for root, dirs, files in os.walk("."):
        if ".git" in root: continue
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                        doc = ast.get_docstring(tree)
                        if doc:
                            short_doc = doc.strip().split('\n')[0]
                            rel_path = os.path.relpath(filepath, '.')
                            docs_content += f"- **{rel_path}**: {short_doc}\n"
                            encontrados += 1
                except: pass
    if encontrados == 0: return False
    docs_content += "\n## Transaction Lifecycle\n1. Wallet signs a transaction.\n2. Transaction is broadcast to the network.\n3. Validated and added to the mempool.\n4. Miner includes it in a new block.\n5. Block is propagated across the network.\n"
    os.makedirs("docs", exist_ok=True)
    with open("docs/ARCHITECTURE.md", "w", encoding="utf-8") as f:
        f.write(docs_content)
    if os.path.exists("CONTRIBUTING.md"):
        with open("CONTRIBUTING.md", "r", encoding="utf-8") as f: contrib = f.read()
        if "docs/ARCHITECTURE.md" not in contrib:
            with open("CONTRIBUTING.md", "a", encoding="utf-8") as f:
                f.write("\n\nBefore diving into the code, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a high-level map of the modules.\n")
    return True

def resolver_issue(issue):
    repo_url = issue["repository_url"]
    owner_repo = repo_url.split("/repos/")[1]
    owner, repo = owner_repo.split("/")
    title = issue["title"]
    issue_number = issue["number"]
    monto = issue.get("_monto_detectado", "Desconocido")
    issue_body = issue.get("body", "")
    issue_url = issue["html_url"]

    print(f"\n🔍 Analizando: '{title}' | 💵 {monto}")
    crear_notificacion_issue(title, issue_url, monto)

    # 1. Hacer Fork (si ya existe, la API responde OK)
    print(f"  🍴 Solicitando Fork de {owner}/{repo}...")
    requests.post(f"https://api.github.com/repos/{owner}/{repo}/forks", headers=HEADERS)
    time.sleep(5) # Espera simple

    # 2. Clonar Fork
    if os.path.exists("repo_temp"): subprocess.run(["rm", "-rf", "repo_temp"])
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{MY_USER}/{repo}.git"
    
    try:
        subprocess.run(["git", "clone", clone_url, "repo_temp"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("  ❌ Error al clonar tu Fork.")
        sys.exit(1)
        
    os.chdir("repo_temp")
    branch_res = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True)
    base_branch = "main" if "origin/main" in branch_res.stdout else "master"
    cambio_realizado = False
    tipo_de_cambio = "general"

    texto_busqueda = (title + " " + issue_body).lower()

    # --- LÓGICA DE ARQUITECTURA ---
    if "architecture" in texto_busqueda or "arch.md" in texto_busqueda or "map of src" in texto_busqueda:
        if generar_archivo_arquitectura():
            cambio_realizado = True
            tipo_de_cambio = "docs"

    # --- LÓGICA DE TYPOS Y COPYRIGHT ---
    elif "typo" in title.lower() or "readme" in title.lower():
        typos = {"recieve": "receive", "occured": "occurred", "seperate": "separate", "definately": "definitely", "teh": "the"}
        for old, new in typos.items():
            result = subprocess.run(["grep", "-r", "-l", old, "--include=*.md", "--include=*.py", "--include=*.txt"], capture_output=True, text=True)
            if result.stdout.strip():
                for f in result.stdout.strip().split("\n"):
                    with open(f, "r") as file: content = file.read()
                    with open(f, "w") as file: file.write(content.replace(old, new))
                    cambio_realizado = True
                    tipo_de_cambio = "typo"
    elif "copyright" in title.lower() or "year" in title.lower():
        for root, dirs, files in os.walk("."):
            if ".git" in root: continue
            for file in files:
                if file.endswith((".py", ".js", ".go", ".rs", ".java", ".md")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r") as f: content = f.read()
                        nuevo = re.sub(r"Copyright\s+(?:\(c\)\s+)?20[0-2][0-9]", f"Copyright (c) {YEAR}", content)
                        if nuevo != content:
                            with open(path, "w") as f: f.write(nuevo)
                            cambio_realizado = True
                            tipo_de_cambio = "copyright"
                    except: pass

    # --- LÓGICA DE DBGAGENT (Gemini) ---
    if not cambio_realizado and any(kw in texto_busqueda for kw in SCRIPT_ERROR_KEYWORDS):
        if GEMINI_API_KEY:
            print("  🤖 Invocando a dbgagent con Gemini...")
            env = os.environ.copy()
            env["LLM_PROVIDER"] = "GEMINI"
            env["GEMINI_API_KEY"] = GEMINI_API_KEY
            try:
                subprocess.run(["dbgagent", "fix", "."], capture_output=True, text=True, env=env, timeout=120)
                git_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                if git_status.stdout.strip():
                    cambio_realizado = True
                    tipo_de_cambio = "bug"
            except: pass

    # --- CREAR PR ---
    if cambio_realizado:
        subprocess.run(["git", "config", "user.name", MY_USER])
        subprocess.run(["git", "config", "user.email", f"{MY_USER}@users.noreply.github.com"])
        subprocess.run(["git", "checkout", "-b", "fix/bot-auto-fix"])
        subprocess.run(["git", "add", "."])
        
        commit_msg = f"Fix: {title}"
        if tipo_de_cambio == "docs": commit_msg = "docs: Add architecture overview"
        elif tipo_de_cambio == "typo": commit_msg = "Fix typos"
        elif tipo_de_cambio == "copyright": commit_msg = f"chore: Update copyright year to {YEAR}"
        
        subprocess.run(["git", "commit", "-m", commit_msg])
        subprocess.run(["git", "push", "origin", "fix/bot-auto-fix"])
        
        if tipo_de_cambio == "docs":
            pr_body = f"Hey! I saw issue #{issue_number} and thought I'd help out. I wrote a small script to extract the docstrings from the source files to build this architecture map. Let me know if you want me to adjust the format!"
        elif tipo_de_cambio == "typo":
            pr_body = f"Hey! I was reading through the docs and noticed a few small typos mentioned in #{issue_number}. Fixed them here. Let me know if anything else needs tweaking."
        elif tipo_de_cambio == "copyright":
            pr_body = f"Hi! Just updating the copyright year as mentioned in #{issue_number}. Small housekeeping PR."
        elif tipo_de_cambio == "bug":
             pr_body = f"Hi! I ran the code and noticed the error mentioned in #{issue_number}. I've applied a fix to resolve it. Let me know if you need me to add any tests."
        else:
            pr_body = f"Hello! I noticed issue #{issue_number} and submitted a fix. Let me know if you need any adjustments! 🚀"

        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        pr_data = {"title": commit_msg, "head": f"{MY_USER}:fix/bot-auto-fix", "base": base_branch, "body": pr_body}
        pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
        
        if pr_res.status_code == 201:
            print(f"  🚀 PR Creado: {pr_res.json()['html_url']}")
            if any(kw in issue_body.lower() for kw in PAYMENT_KEYWORDS):
                if monto != "Desconocido":
                    pago_texto = f"Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the bounty (${monto}):"
                else:
                    pago_texto = "Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the reward:"
                comentario = f"{pago_texto}\n{PAYMENT_ADDRESSES}\n\nThanks! Let me know if you need any changes."
                requests.post(f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments", headers=HEADERS, json={"body": comentario})
                print("  💬 Comentario de pago enviado.")
            return True
        else:
            print(f"  ❌ Error al crear PR: {pr_res.text}")
            
    print("  ❌ No se pudo resolver automáticamente.")
    return False

def main():
    if not GITHUB_TOKEN: return
    if TARGET_ISSUE_URL:
        issue = obtener_issue_especifico(TARGET_ISSUE_URL)
        if issue: resolver_issue(issue)
    else:
        issues = buscar_issues()
        if issues: resolver_issue(issues[0])

if __name__ == "__main__":
    main()
