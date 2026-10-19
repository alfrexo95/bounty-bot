import os
import re
import subprocess
import requests
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
YEAR = str(datetime.now().year)

# Palabras clave que sabemos resolver (tareas sencillas)
KEYWORDS = ["typo", "copyright", "update year", "readme", "fix link", "broken link"]

def buscar_issues():
    issues = []
    # Búsqueda directa en GitHub: issues abiertos con la etiqueta "bounty", en Python, con +1000 estrellas
    url = "https://api.github.com/search/issues?q=label:bounty+is:issue+is:open+language:Python+stars:>1000&sort=created&order=desc&per_page=5"
    
    print("🔎 Buscando issues con recompensa directamente en GitHub...")
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            items = res.json().get("items", [])
            print(f"   Encontrados {len(items)} issues con etiqueta 'bounty'.")
            for item in items:
                title_lower = item["title"].lower()
                # Solo seleccionamos los que coincidan con nuestras palabras clave resolubles
                if any(kw in title_lower for kw in KEYWORDS):
                    issues.append(item)
        else:
            print(f"   ⚠️ Error en la API de GitHub: {res.status_code}")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        
    return issues

def resolver_issue(issue):
    repo_url = issue["repository_url"]
    repo_name = repo_url.split("/repos/")[1]
    title = issue["title"]
    print(f"\n🔍 Analizando: '{title}' en {repo_name}")

    if os.path.exists("repo_temp"):
        subprocess.run(["rm", "-rf", "repo_temp"])
    
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_name}.git"
    
    try:
        subprocess.run(["git", "clone", clone_url, "repo_temp"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("  ❌ Error al clonar el repositorio (puede ser privado o no existir).")
        return False
        
    os.chdir("repo_temp")

    # Detectar rama principal
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
                        # Busca años viejos (2023, 2024, 2025) y los reemplaza por el año actual
                        nuevo_content = re.sub(r"Copyright\s+(?:\(c\)\s+)?20[0-2][0-9]", f"Copyright (c) {YEAR}", content)
                        if nuevo_content != content:
                            with open(path, "w") as f:
                                f.write(nuevo_content)
                            print(f"  ✅ Actualizado año en {path}")
                            cambio_realizado = True
                    except:
                        pass

    if cambio_realizado:
        # Configurar identidad de Git (para que parezca tuyo)
        subprocess.run(["git", "config", "user.name", "alfrexo95"])
        subprocess.run(["git", "config", "user.email", "alfrexo95@users.noreply.github.com"])
        
        # Crear rama, commit y push
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
            "body": f"Hello! I noticed issue #{issue['number']} while browsing. I have submitted a small fix for this. Let me know if you need any adjustments! 🚀"
        }
        pr_res = requests.post(pr_url, headers=HEADERS, json=pr_data)
        if pr_res.status_code == 201:
            print(f"  🚀 ¡PR Creado con éxito!: {pr_res.json()['html_url']}")
            return True
        else:
            print(f"  ❌ Error al crear PR: {pr_res.text}")
            
    print("  ❌ No se pudo resolver automáticamente (el issue requiere lógica más compleja).")
    return False

def main():
    if not GITHUB_TOKEN:
        print("❌ Falta el secreto PAT_TOKEN")
        return

    issues = buscar_issues()
    if not issues:
        print("No se encontraron issues compatibles hoy. Vuelve a intentarlo más tarde.")
        return

    # LÍMITE CRÍTICO: Solo procesar 1 issue por ejecución
    issue_a_resolver = issues[0]
    print(f"🎯 Seleccionado: {issue_a_resolver['title']}")
    resolver_issue(issue_a_resolver)

if __name__ == "__main__":
    main()
