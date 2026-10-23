import os
import re
import subprocess
import requests
import json
from datetime import datetime

GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
MY_REPO = "alfrexo95/bounty-bot"
YEAR = str(datetime.now().year)

PAYMENT_ADDRESSES = """
- BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
- ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
- LTC: ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne
- Lightning: chieftrait089@walletofsatoshi.com
"""

# Palabras clave que sabemos que son automatizables (solo documentación)
AUTO_KEYWORDS = ["typo", "copyright", "update year", "readme", "fix link", "broken link"]
# Palabras clave que requieren intervención humana (código)
MANUAL_KEYWORDS = ["bug", "error", "logic", "implement", "feature", "fix", "issue"]

def crear_notificacion(title, url, monto, tipo, es_auto):
    """Crea un Issue en el repositorio del bot con toda la información."""
    monto_str = f"${monto}" if monto != "Desconocido" else "No especificada"
    modo = "🤖 Automatizable (Typos/Docs)" if es_auto else "🧠 Requiere revisión humana (Código)"
    
    body = f"""🤖 **Bounty Encontrado**

- **Título:** {title}
- **Monto:** {monto_str}
- **Tipo:** {tipo}
- **Modo:** {modo}
- **Enlace:** [Ir al Issue]({url})

---
### 💰 Datos de Pago (para copiar y pegar en el PR o comentario)
{PAYMENT_ADDRESSES}

---
*Este issue fue creado automáticamente por tu bot cazador. Revisa el enlace, resuelve el problema y envía el PR manualmente.*
"""
    res = requests.post(f"https://api.github.com/repos/{MY_REPO}/issues", headers=HEADERS, json={
        "title": f"🎯 Bounty ({monto_str}): {title[:50]}",
        "body": body
    })
    if res.status_code == 201:
        print(f"  ✅ Notificación creada: {res.json()['html_url']}")
        return True
    else:
        print(f"  ❌ Error creando notificación: {res.text}")
        return False

def buscar_issues():
    issues = []
    search_url = "https://api.github.com/search/issues?q=is:issue+is:open+language:Python+label:%22good+first+issue%22&sort=created&order=desc&per_page=10"
    print("🔎 Buscando issues en GitHub (good first issue / help wanted)...")
    try:
        res = requests.get(search_url, headers=HEADERS)
        if res.status_code == 200:
            for item in res.json().get("items", []):
                title_lower = item["title"].lower()
                body_lower = (item.get("body") or "").lower()
                full_text = title_lower + " " + body_lower
                
                # Extraer recompensa
                monto = None
                match = re.search(r'(?:\$|USD\s*)(\d{1,5})(?:\.\d{1,2})?|(\d{1,5})\s*(?:\$|USD)', full_text, re.IGNORECASE)
                if match:
                    monto = match.group(1) or match.group(2)
                if not monto:
                    monto = "Desconocido"
                
                # Clasificar si es automatizable o manual
                es_auto = any(kw in full_text for kw in AUTO_KEYWORDS)
                
                item["_monto"] = monto
                item["_es_auto"] = es_auto
                issues.append(item)
        else:
            print(f"  ⚠️ Error API GitHub: {res.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    return issues

def main():
    if not GITHUB_TOKEN:
        print("❌ Falta el secreto PAT_TOKEN")
        return
    issues = buscar_issues()
    if not issues:
        print("No se encontraron issues hoy.")
        return
    
    # Tomar el primero (el más reciente)
    issue = issues[0]
    title = issue["title"]
    url = issue["html_url"]
    monto = issue.get("_monto", "Desconocido")
    es_auto = issue.get("_es_auto", False)
    
    # Determinar tipo (simple)
    if "typo" in title.lower(): tipo = "Typo"
    elif "readme" in title.lower(): tipo = "Documentación"
    elif "copyright" in title.lower(): tipo = "Copyright"
    else: tipo = "Código/Lógica"
    
    print(f"🎯 Analizando: '{title}' | 💵 {monto} | 🤖 Auto: {es_auto}")
    crear_notificacion(title, url, monto, tipo, es_auto)

if __name__ == "__main__":
    main()
