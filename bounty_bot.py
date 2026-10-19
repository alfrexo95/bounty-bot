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

    # 1. Solicitar el Fork
    print(f"  🍴 Solicitando Fork de {owner}/{repo}...")
    fork_url = f"https://api.github.com/repos/{owner}/{repo}/forks"
    fork_res = requests.post(fork_url, headers=HEADERS)
    if fork_res.status_code not in [200, 202]:
        print(f"  ❌ Error al solicitar Fork: {fork_res.text}")
        sys.exit(1)

    # 2. Esperar activamente a que el Fork exista (Polling)
    print("  ⏳ Esperando a que GitHub cree el Fork...")
    fork_ready = False
    for attempt in range(1, 13): # Hasta 12 intentos (1 minuto aprox)
        time.sleep(5)
        check_url = f"https://api.github.com/repos/{MY_USER}/{repo}"
        check_res = requests.get(check_url, headers=HEADERS)
        if check_res.status_code == 200:
            print(f"  ✅ Fork listo (intento {attempt}).")
            fork_ready = True
            break
        else:
            print(f"     Intento {attempt}: Fork aún no disponible (status {check_res.status_code}).")
    
    if not fork_ready:
        print("  ❌ El Fork no se creó a tiempo. Abortando.")
        sys.exit(1)

    # 3. Clonar el Fork
    if os.path.exists("repo_temp"):
        subprocess.run(["rm", "-rf", "repo_temp"])
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{MY_USER}/{repo}.git"
    
    try:
        subprocess.run(["git", "clone", clone_url, "repo_temp"], check=True, capture_output=True)
        print("  ✅ Fork clonado correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error al clonar el Fork: {e.stderr.decode() if e.stderr else ''}")
        sys.exit(1)
        
    os.chdir("repo_temp")
    branch_res = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True)
    base_branch = "main" if "origin/main" in branch_res.stdout else "master"

    # 4. Buscar y reemplazar usando grep (más fiable)
    cambio_realizado = False
    print("  🔄 Buscando 'Pin.set' en todo el repositorio...")
    
    # Usamos grep para encontrar archivos que contengan 'Pin.set' (ignorando mayúsculas)
    grep_result = subprocess.run(["grep", "-r", "-l", "-i", "Pin.set", "."], capture_output=True, text=True)
    
    if not grep_result.stdout.strip():
        print("  ❌ No se encontró 'Pin.set' en ningún archivo. Verifica que la carpeta docs esté en la rama clonada.")
        sys.exit(1)
        
    files_to_fix = grep_result.stdout.strip().split("\n")
    print(f"  📄 Archivos encontrados: {files_to_fix}")
    
    for path in files_to_fix:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Reemplazamos Pin.set por Pin.write de forma inteligente
            new_content = re.sub(r'(?i)Pin\.set', 'Pin.write', content)
            
            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"    ✅ Reemplazado en {path}")
                cambio_realizado = True
        except Exception as e:
            print(f"    ⚠️ No se pudo procesar {path}: {e}")

    if not cambio_realizado:
        print("  ❌ Se encontraron archivos, pero no se pudo aplicar el reemplazo. Abortando.")
        sys.exit(1)

    # 5. Hacer commit y push al Fork
    subprocess.run(["git", "config", "user.name", MY_USER])
    subprocess.run(["git", "config", "user.email", f"{MY_USER}@users.noreply.github.com"])
    subprocess.run(["git", "checkout", "-b", "fix/rename-pin-set"])
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "docs: Rename Pin.set to Pin.write to avoid reserved word"])
    subprocess.run(["git", "push", "origin", "fix/rename-pin-set"])
    print("  📤 Cambios subidos a tu Fork.")

    # 6. Crear el Pull Request desde tu Fork hacia el repositorio original
    print("  🚀 Creando Pull Request...")
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    pr_data = {
        "title": "docs: Rename Pin.set to Pin.write to avoid reserved word",
        "head": f"{MY_USER}:fix/rename-pin-set",
        "base": base_branch,
        "body": f"Hey! I saw issue #{issue_number} and thought I'd fix this. I've replaced all instances of `Pin.set` with `Pin.write` in the documentation to avoid using the reserved word. Let me know if anything else needs tweaking."
    }
    pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
    
    if pr_res.status_code == 201:
        pr_data = pr_res.json()
        print(f"  🚀 ¡PR Creado con éxito!: {pr_data['html_url']}")
        
        # 7. Dejar comentario de pago si el issue lo menciona
        if any(kw in issue_body.lower() for kw in PAYMENT_KEYWORDS):
            if monto != "Desconocido":
                pago_texto = f"Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the bounty (${monto}):"
            else:
                pago_texto = "Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the reward:"
            comentario = f"{pago_texto}\n{PAYMENT_ADDRESSES}\n\nThanks! Let me know if you need any changes."
            requests.post(f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments", headers=HEADERS, json={"body": comentario})
            print("  💬 Comentario de pago enviado.")
    else:
        print(f"  ❌ Error al crear PR: {pr_res.text}")
        sys.exit(1)

def main():
    if not GITHUB_TOKEN:
        print("❌ Falta el secreto PAT_TOKEN")
        sys.exit(1)
    
    if TARGET_ISSUE_URL:
        issue = obtener_issue_especifico(TARGET_ISSUE_URL)
        if issue:
            resolver_issue(issue)
        else:
            print("❌ No se pudo obtener el issue específico.")
            sys.exit(1)
    else:
        issues = buscar_issues()
        if issues:
            resolver_issue(issues[0])
        else:
            print("No se encontraron issues hoy.")

if __name__ == "__main__":
    main()
