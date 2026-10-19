import os
import re
import subprocess
import requests
from datetime import datetime

GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
YEAR = str(datetime.now().year)
MY_REPO = "alfrexo95/bounty-bot" # Tu repositorio para las notificaciones

PAYMENT_ADDRESSES = """
₿ BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
Ξ ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
Ł LTC: LcwAfm4xeJt5sHHVHAGN4qfiv7ruYKzqTe
⚡ Lightning: chieftrait089@walletofsatoshi.com
"""

PAYMENT_KEYWORDS = ["payment", "pay", "address", "wallet", "usdc", "lightning", "reward", "bounty", "stripe", "fund"]
REWARD_PATTERN = re.compile(r'(?:\$|USD\s*)(\d{1,5})(?:\.\d{1,2})?|(\d{1,5})\s*(?:\$|USD)', re.IGNORECASE)

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
    """Crea un issue en tu propio repo para avisarte."""
    print("🔔 Creando notificación en tu repositorio...")
    issue_url = f"https://api.github.com/repos/{MY_REPO}/issues"
    body = f"🤖 **Bounty Encontrado**\n\n- **Título:** {title}\n- **Monto:** ${monto}\n- **Tipo:** {tipo}\n- **Enlace:** [Ir al Issue]({url})"
    res = requests.post(issue_url, headers=HEADERS, json={"title": f"🎯 Bounty: ${monto} en {tipo}", "body": body})
    if res.status_code == 201:
        print("✅ Notificación creada en la pestaña Issues de tu repo.")
    else:
        print(f"❌ Error al crear notificación: {res.text}")

def buscar_issues():
    issues = []
    # Búsqueda ampliada: Busca en 'good first issue' y 'help wanted' en Python
    search_url = "https://api.github.com/search/issues?q=is:issue+is:open+language:Python+label:%22good+first+issue%22&sort=created&order=desc&per_page=10"
    
    print("🔎 Buscando issues en GitHub (good first issue / help wanted)...")
    try:
        res = requests.get(search_url, headers=HEADERS)
        if res.status_code == 200:
            items = res.json().get("items", [])
            print(f"   Analizando {len(items)} issues recientes...")
            for item in items:
                title_body = (item["title"] + " " + (item.get("body") or "")).lower()
                
                # 1. Verificar si menciona pago o recompensa
                monto = extraer_recompensa(item["title"] + " " + (item.get("body") or ""))
                
                # Si no tiene un monto claro en dólares, lo ignoramos para no perder tiempo
                if not monto:
                    continue
                
                # 2. Clasificar
                tipo_codigo = clasificar_codigo(item["title"] + " " + (item.get("body") or ""))
                
                item["_monto_detectado"] = monto
                item["_tipo_codigo"] = tipo_codigo
                issues.append(item)
                print(f"   ✅ POSIBLE BOUNTY: '{item['title'][:40]}...' | ${monto} | {tipo_codigo}")
        else:
            print(f"   ⚠️ Error API GitHub: {res.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    return issues

def resolver_issue(issue):
    # (El resto de la función se mantiene igual que antes)
    repo_url = issue["repository_url"]
    repo_name = repo_url.split("/repos/")[1]
    title = issue["title"]
    issue_number = issue["number"]
    monto = issue.get("_monto_detectado", "N/A")
    tipo_codigo = issue.get("_tipo_codigo", "Desconocido")
    issue_body = issue.get("body", "")
    issue_url = issue["html_url"]

    print(f"\n🔍 Analizando: '{title}' | 💵 ${monto} | 🏷️ {tipo_codigo}")
    
    # Avisar por Issue
    crear_notificacion_issue(title, issue_url, monto, tipo_codigo)

    if os.path.exists("repo_temp"): subprocess.run(["rm", "-rf", "repo_temp"])
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_name}.git"
    
    try:
        subprocess.run(["git", "clone", clone_url, "repo_temp"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("  ❌ Error al clonar.")
        return False
        
    os.chdir("repo_temp")
    branch_res = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True)
    base_branch = "main" if "origin/main" in branch_res.stdout else "master"
    cambio_realizado = False

    if "typo" in title.lower() or "readme" in title.lower():
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

    if cambio_realizado:
        subprocess.run(["git", "config", "user.name", "alfrexo95"])
        subprocess.run(["git", "config", "user.email", "alfrexo95@users.noreply.github.com"])
        subprocess.run(["git", "checkout", "-b", "fix/bot-auto-fix"])
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", f"Fix: {title}"])
        subprocess.run(["git", "push", "origin", "fix/bot-auto-fix"])
        
        pr_url = f"https://api.github.com/repos/{repo_name}/pulls"
        pr_data = {"title": f"Fix: {title}", "head": "fix/bot-auto-fix", "base": base_branch, "body": f"Hello! I noticed issue #{issue_number}. I have submitted a small fix. Let me know! 🚀"}
        pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
        
        if pr_res.status_code == 201:
            print(f"  🚀 PR Creado: {pr_res.json()['html_url']}")
            if any(kw in issue_body.lower() for kw in PAYMENT_KEYWORDS):
                comentario = f"Hi! I submitted a PR. Regarding the reward (${monto}), I can receive payment here:\n{PAYMENT_ADDRESSES}\nThanks!"
                requests.post(f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments", headers=HEADERS, json={"body": comentario})
                print("  💬 Comentario de pago enviado.")
            return True
    print("  ❌ No se pudo resolver automáticamente.")
    return False

def main():
    if not GITHUB_TOKEN: return
    issues = buscar_issues()
    if not issues:
        print("No se encontraron issues con recompensa clara hoy.")
        return
    resolver_issue(issues[0])

if __name__ == "__main__":
    main()
