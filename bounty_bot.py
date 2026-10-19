import os
import re
import subprocess
import requests
import ast # NUEVO: Para leer los docstrings de Python
from datetime import datetime

GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
YEAR = str(datetime.now().year)
MY_REPO = "alfrexo95/bounty-bot"

PAYMENT_ADDRESSES = """
₿ BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
Ξ ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
Ł LTC: LcwAfm4xeJt5sHHVHAGN4qfiv7ruYKzqTe
⚡ Lightning: chieftrait089@walletofsatoshi.com
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
    res = requests.post(issue_url, headers=HEADERS, json={"title": f"🎯 Bounty ({monto_str}): {tipo}", "body": body})
    if res.status_code == 201:
        print("✅ Notificación creada en la pestaña Issues de tu repo.")
    else:
        print(f"❌ Error al crear notificación: {res.text}")

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
                print(f"   ✅ SELECCIONADO: '{item['title'][:40]}...' | Monto: {monto} | Tipo: {tipo_codigo}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return issues

def generar_archivo_arquitectura():
    """Busca en la carpeta src/ y genera docs/ARCHITECTURE.md leyendo los docstrings."""
    print("  📝 Generando ARCHITECTURE.md a partir de docstrings...")
    docs_content = "# Architecture Overview\n\n## Core Modules\n"
    encontrados = 0
    
    # Recorrer carpetas buscando archivos .py
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
                            # Tomar la primera línea del docstring
                            short_doc = doc.strip().split('\n')[0]
                            rel_path = os.path.relpath(filepath, '.')
                            docs_content += f"- **{rel_path}**: {short_doc}\n"
                            encontrados += 1
                except Exception:
                    pass

    if encontrados == 0:
        print("  ⚠️ No se encontraron docstrings en el código.")
        return False

    docs_content += "\n## Transaction Lifecycle\n1. Wallet signs a transaction.\n2. Transaction is broadcast to the network.\n3. Validated and added to the mempool.\n4. Miner includes it in a new block.\n5. Block is propagated across the network.\n"

    os.makedirs("docs", exist_ok=True)
    with open("docs/ARCHITECTURE.md", "w", encoding="utf-8") as f:
        f.write(docs_content)
        
    # Actualizar CONTRIBUTING.md
    if os.path.exists("CONTRIBUTING.md"):
        with open("CONTRIBUTING.md", "r", encoding="utf-8") as f:
            contrib = f.read()
        link_text = "\n\nBefore diving into the code, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a high-level map of the modules.\n"
        if "docs/ARCHITECTURE.md" not in contrib:
            with open("CONTRIBUTING.md", "a", encoding="utf-8") as f:
                f.write(link_text)
                
    print(f"  ✅ Archivo generado con {encontrados} módulos documentados.")
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

    texto_busqueda = (title + " " + issue_body).lower()

    # --- NUEVA LÓGICA: Resolver Documentación / Arquitectura ---
    if "architecture" in texto_busqueda or "arch.md" in texto_busqueda or "map of src" in texto_busqueda:
        if generar_archivo_arquitectura():
            cambio_realizado = True

    # --- LÓGICA EXISTENTE: Typos y Copyright ---
    elif "typo" in title.lower() or "readme" in title.lower():
        typos = {"recieve": "receive", "occured": "occurred", "seperate": "separate", "definately": "definitely", "teh": "the"}
        for old, new in typos.items():
            result = subprocess.run(["grep", "-r", "-l", old, "--include=*.md", "--include=*.py", "--include=*.txt"], capture_output=True, text=True)
            if result.stdout.strip():
                for f in result.stdout.strip().split("\n"):
                    with open(f, "r") as file: content = file.read()
                    with open(f, "w") as file: file.write(content.replace(old, new))
                    print(f"  ✅ Corregido '{old}' -> '{new}' en {f}")
                    cambio_realizado = True
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
                            print(f"  ✅ Actualizado año en {path}")
                            cambio_realizado = True
                    except: pass

    # --- INTEGRACIÓN DBGAGENT (Gemini) ---
    if not cambio_realizado and any(kw in texto_busqueda for kw in SCRIPT_ERROR_KEYWORDS):
        if GEMINI_API_KEY:
            print("  🤖 Invocando a dbgagent con Gemini para intentar reparar el script...")
            env = os.environ.copy()
            env["LLM_PROVIDER"] = "GEMINI"
            env["GEMINI_API_KEY"] = GEMINI_API_KEY
            try:
                res_dbg = subprocess.run(["dbgagent", "fix", "."], capture_output=True, text=True, env=env, timeout=120)
                git_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                if git_status.stdout.strip():
                    print("  ✅ dbgagent ha propuesto cambios en el código.")
                    cambio_realizado = True
            except: pass

    # --- CREAR PR ---
    if cambio_realizado:
        subprocess.run(["git", "config", "user.name", "alfrexo95"])
        subprocess.run(["git", "config", "user.email", "alfrexo95@users.noreply.github.com"])
        subprocess.run(["git", "checkout", "-b", "fix/bot-auto-fix"])
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", f"Fix: {title}"])
        subprocess.run(["git", "push", "origin", "fix/bot-auto-fix"])
        
        pr_url = f"https://api.github.com/repos/{repo_name}/pulls"
        pr_data = {"title": f"Fix: {title}", "head": "fix/bot-auto-fix", "base": base_branch, "body": f"Hello! I noticed issue #{issue_number}. I have submitted a fix for this. Let me know! 🚀"}
        pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
        
        if pr_res.status_code == 201:
            print(f"  🚀 PR Creado: {pr_res.json()['html_url']}")
            if any(kw in issue_body.lower() for kw in PAYMENT_KEYWORDS):
                pago_texto = f"Regarding the reward (${monto})," if monto != "Desconocido" else "Regarding the reward,"
                comentario = f"Hi! I submitted a PR. {pago_texto} I can receive the payment here:\n{PAYMENT_ADDRESSES}\nThanks!"
                requests.post(f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments", headers=HEADERS, json={"body": comentario})
                print("  💬 Comentario de pago enviado.")
            return True
            
    print("  ❌ No se pudo resolver automáticamente.")
    return False

def main():
    if not GITHUB_TOKEN: return
    issues = buscar_issues()
    if not issues: return
    resolver_issue(issues[0])

if __name__ == "__main__":
    main()
