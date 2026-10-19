import os
import re
import subprocess
import requests
import ast
import time
from datetime import datetime

GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_ISSUE_URL = os.environ.get("ISSUE_URL")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
YEAR = str(datetime.now().year)
MY_REPO = "alfrexo95/bounty-bot"
MY_USER = "alfrexo95" # Tu nombre de usuario en GitHub

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

    # 1. Hacer un FORK del repositorio
    print(f"  🍴 Haciendo Fork de {owner}/{repo} a tu cuenta...")
    fork_url = f"https://api.github.com/repos/{owner}/{repo}/forks"
    requests.post(fork_url, headers=HEADERS)
    time.sleep(5) # Esperar a que GitHub procese el fork

    # 2. Clonar TU Fork (no el original)
    if os.path.exists("repo_temp"): subprocess.run(["rm", "-rf", "repo_temp"])
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{MY_USER}/{repo}.git"
    
    try:
        subprocess.run(["git", "clone", clone_url, "repo_temp"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("  ❌ Error al clonar tu Fork.")
        return False
        
    os.chdir("repo_temp")
    branch_res = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True)
    base_branch = "main" if "origin/main" in branch_res.stdout else "master"
    cambio_realizado = False
    tipo_de_cambio = "general"
    texto_busqueda = (title + " " + issue_body).lower()
    old_name, new_name = "", ""

    # --- LÓGICA DE RENOMBRADO ---
    rename_match = re.search(r'rename\s+`?([^`\s]+)`?\s+to\s+`?([^`\s]+)`?', texto_busqueda)
    if not rename_match and "pin.set" in texto_busqueda and "pin.write" in texto_busqueda:
        old_name, new_name = "Pin.set", "Pin.write"
        cambio_realizado = True
    elif rename_match:
        old_name, new_name = rename_match.groups()
        cambio_realizado = True

    if cambio_realizado:
        print(f"  🔄 Renombrando '{old_name}' a '{new_name}'...")
        for root, dirs, files in os.walk("."):
            if ".git" in root: continue
            for file in files:
                if file.endswith((".md", ".py", ".txt", ".json", ".verse")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f: content = f.read()
                        if old_name in content:
                            with open(path, "w", encoding="utf-8") as f: f.write(content.replace(old_name, new_name))
                            print(f"    ✅ Reemplazado en {path}")
                            tipo_de_cambio = "rename"
                    except: pass

    # --- CREAR PR ---
    if cambio_realizado:
        subprocess.run(["git", "config", "user.name", MY_USER])
        subprocess.run(["git", "config", "user.email", f"{MY_USER}@users.noreply.github.com"])
        subprocess.run(["git", "checkout", "-b", "fix/bot-auto-fix"])
        subprocess.run(["git", "add", "."])
        
        commit_msg = f"docs: Rename {old_name} to {new_name}"
        subprocess.run(["git", "commit", "-m", commit_msg])
        subprocess.run(["git", "push", "origin", "fix/bot-auto-fix"])
        
        # Crear PR desde tu Fork hacia el original
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        pr_data = {
            "title": commit_msg, 
            "head": f"{MY_USER}:fix/bot-auto-fix", # <-- Importante: MY_USER:branch
            "base": base_branch, 
            "body": f"Hey! I saw issue #{issue_number} and thought I'd fix this. I've replaced all instances of `{old_name}` with `{new_name}` to avoid the reserved word. Let me know if anything else needs tweaking."
        }
        pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
        
        if pr_res.status_code == 201:
            print(f"  🚀 PR Creado: {pr_res.json()['html_url']}")
            if any(kw in issue_body.lower() for kw in PAYMENT_KEYWORDS):
                pago_texto = f"Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the bounty (${monto}):" if monto != "Desconocido" else "Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the reward:"
                comentario = f"{pago_texto}\n{PAYMENT_ADDRESSES}\n\nThanks! Let me know if you need any changes."
                requests.post(f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments", headers=HEADERS, json={"body": comentario})
                print("  💬 Comentario de pago enviado.")
            return True
        else:
            print(f"  ❌ Error al crear PR: {pr_res.text}")
            
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
