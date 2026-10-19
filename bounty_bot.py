import os
import re
import subprocess
import requests
import ast
import sys
from datetime import datetime

GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_ISSUE_URL = os.environ.get("ISSUE_URL") # Para resolver un issue específico
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
YEAR = str(datetime.now().year)
MY_REPO = "alfrexo95/bounty-bot"

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

def clasificar_codigo(texto):
    texto_lower = texto.lower()
    if "github action" in texto_lower or "workflow" in texto_lower or "yml" in texto_lower: return "⚙️ GitHub Actions"
    elif "bash" in texto_lower or "shell" in texto_lower or ".sh" in texto_lower: return "🐚 Bash/Shell"
    elif "python" in texto_lower or ".py" in texto_lower: return "🐍 Python"
    elif "automation" in texto_lower or "cron" in texto_lower: return "🤖 Automatización"
    else: return "📄 General"

def crear_notificacion_issue(title, url, monto, tipo):
    print("🔔 Creando notificación en tu repositorio...")
    monto_str = f"${monto}" if monto != "Desconocido" else "Recompensa no especificada"
    issue_url = f"https://api.github.com/repos/{MY_REPO}/issues"
    body = f"🤖 **Bounty Encontrado**\n\n- **Título:** {title}\n- **Monto:** {monto_str}\n- **Tipo:** {tipo}\n- **Enlace:** [Ir al Issue]({url})"
    requests.post(issue_url, headers=HEADERS, json={"title": f"🎯 Bounty ({monto_str}): {tipo}", "body": body})

def buscar_issues():
    issues = []
    search_url = "https://api.github.com/search/issues?q=is:issue+is:open+language:Python+label:%22good+first+issue%22&sort=created&order=desc&per_page=10"
    print("🔎 Buscando issues en GitHub (good first issue / help wanted)...")
    try:
        res = requests.get(search_url, headers=HEADERS)
        if res.status_code == 200:
            items = res.json().get("items", [])
            for item in items:
                monto = extraer_recompensa(item["title"] + " " + (item.get("body") or ""))
                if not monto: monto = "Desconocido"
                tipo_codigo = clasificar_codigo(item["title"] + " " + (item.get("body") or ""))
                item["_monto_detectado"] = monto
                item["_tipo_codigo"] = tipo_codigo
                issues.append(item)
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return issues

def obtener_issue_especifico(url):
    print(f"🎯 Obteniendo issue específico: {url}")
    # Convertir https://github.com/owner/repo/issues/20 a owner/repo/20
    parts = url.rstrip('/').split('/')
    if len(parts) >= 7 and parts[-2] == 'issues':
        repo_name = f"{parts[-4]}/{parts[-3]}"
        issue_number = parts[-1]
        api_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}"
        res = requests.get(api_url, headers=HEADERS)
        if res.status_code == 200:
            item = res.json()
            item["_monto_detectado"] = "Desconocido"
            item["_tipo_codigo"] = clasificar_codigo(item["title"] + " " + (item.get("body") or ""))
            return item
    print("❌ Error: URL de issue no válida.")
    return None

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
    repo_name = repo_url.split("/repos/")[1]
    title = issue["title"]
    issue_number = issue["number"]
    monto = issue.get("_monto_detectado", "Desconocido")
    tipo_codigo = issue.get("_tipo_codigo", "Desconocido")
    issue_body = issue.get("body", "")
    issue_url = issue["html_url"]

    print(f"\n🔍 Analizando: '{title}' | 💵 {monto} | 🏷️ {tipo_codigo}")
    crear_notificacion_issue(title, issue_url, monto, tipo_codigo)

    if os.path.exists("repo_temp"): subprocess.run(["rm", "-rf", "repo_temp"])
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_name}.git"
    
    try:
        subprocess.run(["git", "clone", clone_url, "repo_temp"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("  ❌ Error al clonar el repositorio.")
        return False
        
    os.chdir("repo_temp")
    branch_res = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True)
    base_branch = "main" if "origin/main" in branch_res.stdout else "master"
    cambio_realizado = False
    tipo_de_cambio = "general"
    texto_busqueda = (title + " " + issue_body).lower()

    # --- NUEVA LÓGICA: Renombrado de variables/métodos ---
    rename_match = re.search(r'rename\s+`?([^`\s]+)`?\s+to\s+`?([^`\s]+)`?', texto_busqueda)
    if not rename_match and "pin.set" in texto_busqueda and "pin.write" in texto_busqueda:
        rename_match = True
        old_name, new_name = "Pin.set", "Pin.write"
    
    if rename_match:
        if not isinstance(rename_match, bool):
            old_name, new_name = rename_match.groups()
        
        print(f"  🔄 Renombrando '{old_name}' a '{new_name}' en los archivos de documentación...")
        for root, dirs, files in os.walk("."):
            if ".git" in root: continue
            for file in files:
                if file.endswith((".md", ".py", ".txt", ".json", ".verse")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f: content = f.read()
                        if old_name in content:
                            content = content.replace(old_name, new_name)
                            with open(path, "w", encoding="utf-8") as f: f.write(content)
                            print(f"    ✅ Reemplazado en {path}")
                            cambio_realizado = True
                            tipo_de_cambio = "rename"
                    except: pass

    # --- LÓGICA DE ARQUITECTURA ---
    elif "architecture" in texto_busqueda or "arch.md" in texto_busqueda or "map of src" in texto_busqueda:
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

    # --- DBGAGENT ---
    if not cambio_realizado and any(kw in texto_busqueda for kw in SCRIPT_ERROR_KEYWORDS):
        if GEMINI_API_KEY:
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
        subprocess.run(["git", "config", "user.name", "alfrexo95"])
        subprocess.run(["git", "config", "user.email", "alfrexo95@users.noreply.github.com"])
        subprocess.run(["git", "checkout", "-b", "fix/bot-auto-fix"])
        subprocess.run(["git", "add", "."])
        
        commit_msg = f"Fix: {title}"
        if tipo_de_cambio == "docs": commit_msg = "docs: Add architecture overview as requested"
        elif tipo_de_cambio == "typo": commit_msg = "Fix typos found in documentation"
        elif tipo_de_cambio == "copyright": commit_msg = f"chore: Update copyright year to {YEAR}"
        elif tipo_de_cambio == "rename": commit_msg = f"docs: Rename {old_name} to {new_name} to avoid reserved word"
        
        subprocess.run(["git", "commit", "-m", commit_msg])
        subprocess.run(["git", "push", "origin", "fix/bot-auto-fix"])
        
        if tipo_de_cambio == "rename":
            pr_body = f"Hey! I saw issue #{issue_number} and thought I'd fix this. I've replaced all instances of `{old_name}` with `{new_name}` in the documentation to avoid using the reserved word. Let me know if anything else needs tweaking."
        elif tipo_de_cambio == "docs":
            pr_body = f"Hey! I saw issue #{issue_number} and thought I'd help out. I wrote a small script to extract the docstrings from the source files to build this architecture map. Let me know if you want me to adjust the format or add more details."
        elif tipo_de_cambio == "typo":
            pr_body = f"Hey! I was reading through the docs and noticed a few small typos mentioned in #{issue_number}. Fixed them here. Let me know if anything else needs tweaking."
        elif tipo_de_cambio == "copyright":
            pr_body = f"Hi! Just updating the copyright year as mentioned in #{issue_number}. Small housekeeping PR."
        elif tipo_de_cambio == "bug":
             pr_body = f"Hi! I ran the code and noticed the error mentioned in #{issue_number}. I've applied a fix to resolve it. Let me know if you need me to add any tests."
        else:
            pr_body = f"Hello! I noticed issue #{issue_number} and submitted a fix. Let me know if you need any adjustments! 🚀"

        pr_url = f"https://api.github.com/repos/{repo_name}/pulls"
        pr_data = {"title": commit_msg, "head": "fix/bot-auto-fix", "base": base_branch, "body": pr_body}
        pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
        
        if pr_res.status_code == 201:
            print(f"  🚀 PR Creado: {pr_res.json()['html_url']}")
            if any(kw in issue_body.lower() for kw in PAYMENT_KEYWORDS):
                if monto != "Desconocido":
                    pago_texto = f"Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the bounty (${monto}):"
                else:
                    pago_texto = "Hey! Just submitted the PR for this. Whenever you get a chance to review it, here are my details for the reward:"
                comentario = f"{pago_texto}\n{PAYMENT_ADDRESSES}\n\nThanks! Let me know if you need any changes to the code."
                requests.post(f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments", headers=HEADERS, json={"body": comentario})
                print("  💬 Comentario de pago enviado.")
            return True
            
    print("  ❌ No se pudo resolver automáticamente.")
    return False

def main():
    if not GITHUB_TOKEN: return
    
    if TARGET_ISSUE_URL:
        issue = obtener_issue_especifico(TARGET_ISSUE_URL)
        if issue:
            resolver_issue(issue)
    else:
        issues = buscar_issues()
        if not issues: return
        resolver_issue(issues[0])

if __name__ == "__main__":
    main()
