import os
import re
import subprocess
import requests
from datetime import datetime

# --- CONFIGURACIÓN ---
GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
YEAR = str(datetime.now().year)

# Tus direcciones de pago
PAYMENT_ADDRESSES = """
₿ BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
Ξ ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
Ł LTC: LcwAfm4xeJt5sHHVHAGN4qfiv7ruYKzqTe
⚡ Lightning: chieftrait089@walletofsatoshi.com
"""

# Palabras clave para saber si el issue pide pago
PAYMENT_KEYWORDS = ["payment", "pay", "address", "wallet", "usdc", "lightning", "reward", "bounty", "stripe", "fund"]

# Palabras clave que sabemos resolver
KEYWORDS = ["typo", "copyright", "update year", "readme", "fix link", "broken link"]

def buscar_issues():
    issues = []
    url = "https://api.github.com/search/issues?q=label:bounty+is:issue+is:open+language:Python+stars:>1000&sort=created&order=desc&per_page=5"
    
    print("🔎 Buscando issues con recompensa directamente en GitHub...")
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            items = res.json().get("items", [])
            print(f"   Encontrados {len(items)} issues con etiqueta 'bounty'.")
            for item in items:
                title_lower = item["title"].lower()
                if any(kw in title_lower for kw in KEYWORDS):
                    issues.append(item)
        else:
            print(f"   ⚠️ Error en la API de GitHub: {res.status_code}")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        
    return issues

def dejar_comentario_pago(repo_name, issue_number, issue_body):
    """Revisa si el issue pide datos de pago y deja un comentario."""
    body_lower = (issue_body or "").lower()
    
    # Verificar si el issue menciona formas de pago
    if any(kw in body_lower for kw in PAYMENT_KEYWORDS):
        print("  💰 El issue menciona pagos. Preparando comentario con direcciones...")
        
        comentario = f"""Hi! I have submitted a Pull Request to fix this issue. 

Regarding the reward, I can receive the payment in any of the following addresses:

{PAYMENT_ADDRESSES}

Let me know once the PR is merged. Thanks!"""

        comment_url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments"
        res = requests.post(comment_url, headers=HEADERS, json={"body": comentario})
        
        if res.status_code == 201:
            print("  💬 Comentario de pago publicado con éxito en el issue.")
        else:
            print(f"  ❌ Error al publicar comentario: {res.status_code} - {res.text}")
    else:
        print("  ℹ️ El issue no menciona pagos. No se deja comentario.")

def resolver_issue(issue):
    repo_url = issue["repository_url"]
    repo_name = repo_url.split("/repos/")[1]
    title = issue["title"]
    issue_body = issue.get("body", "")
    issue_number = issue["number"]
    
    print(f"\n🔍 Analizando: '{title}' en {repo_name}")

    if os.path.exists("repo_temp"):
        subprocess.run(["rm", "-rf", "repo_temp"])
    
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

    # 1. Lógica para Typos y Links rotos
    if "typo" in title.lower() or "link" in title.lower() or "readme" in title.lower():
        typos = {"recieve": "receive", "occured": "occurred", "seperate": "separate", "definately": "definitely", "teh": "the"}
        for old, new in typos.items():
            result = subprocess.run(["grep", "-r", "-l", old, "--include=*.md", "--include=*.py", "--include=*.js", "--include=*.txt"], capture_output=True, text=True)
            if result.stdout.strip():
                files = result.stdout.strip().split("\n")
                for f in files:
                    with open(f, "r") as file:
                        content = file.read()
                    content = content.replace(old, new)
                    with open(f, "w") as file:
                        file.write(content)
                    print(f"  ✅ Corregido '{old}' -> '{new}' en {f}")
                    cambio_realizado = True

    # 2. Lógica para Copyright / Update Year
    elif "copyright" in title.lower() or "year" in title.lower():
        for root, dirs, files in os.walk("."):
            if ".git" in root: continue
            for file in files:
                if file.endswith((".py", ".js", ".go", ".rs", ".java", ".c", ".cpp", ".md")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r") as f:
                            content = f.read()
                        nuevo_content = re.sub(r"Copyright\s+(?:\(c\)\s+)?20[0-2][0-9]", f"Copyright (c) {YEAR}", content)
                        if nuevo_content != content:
                            with open(path, "w") as f:
                                f.write(nuevo_content)
                            print(f"  ✅ Actualizado año en {path}")
                            cambio_realizado = True
                    except:
                        pass

    if cambio_realizado:
        subprocess.run(["git", "config", "user.name", "alfrexo95"])
        subprocess.run(["git", "config", "user.email", "alfrexo95@users.noreply.github.com"])
        subprocess.run(["git", "checkout", "-b", "fix/bot-auto-fix"])
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", f"Fix: {title}"])
        subprocess.run(["git", "push", "origin", "fix/bot-auto-fix"])
        
        # Crear el Pull Request
        pr_url = f"https://api.github.com/repos/{repo_name}/pulls"
        pr_data = {
            "title": f"Fix: {title}",
            "head": "fix/bot-auto-fix",
            "base": base_branch,
            "body": f"Hello! I noticed issue #{issue_number} while browsing. I have submitted a small fix for this. Let me know if you need any adjustments! 🚀"
        }
        pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
        
        if pr_res.status_code == 201:
            print(f"  🚀 ¡PR Creado con éxito!: {pr_res.json()['html_url']}")
            # AQUI LLAMAMOS A LA FUNCION DE PAGO
            dejar_comentario_pago(repo_name, issue_number, issue_body)
            return True
        else:
            print(f"  ❌ Error al crear PR: {pr_res.text}")
            
    print("  ❌ No se pudo resolver automáticamente.")
    return False

def main():
    if not GITHUB_TOKEN:
        print("❌ Falta el secreto PAT_TOKEN")
        return

    issues = buscar_issues()
    if not issues:
        print("No se encontraron issues compatibles hoy.")
        return

    issue_a_resolver = issues[0]
    print(f"🎯 Seleccionado: {issue_a_resolver['title']}")
    resolver_issue(issue_a_resolver)

if __name__ == "__main__":
    main()
