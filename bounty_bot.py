import os
import re
import json
import requests
from datetime import datetime

GITHUB_TOKEN = os.environ.get("PAT_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
MY_REPO = "alfrexo95/bounty-bot"
STATE_FILE = "seen_issues.json"

# Mensaje de pago y situación en Cuba
PAYMENT_INFO = """
### 💰 Payment Details
- BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
- ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
- LTC: ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne
- Lightning: chieftrait089@walletofsatoshi.com

**Note:** I am a developer from Cuba. Due to the economic blockade, traditional payment methods are often blocked. Cryptocurrency is the most stable and free way for me to receive payments. I would appreciate it if the bounty could be paid in crypto. Thank you!
"""

# Búsquedas enfocadas en pagos garantizados (Escrow / Lightning)
SEARCH_QUERIES = [
    # 1. Lightning Bounties (Pago en sats garantizado por la plataforma)
    "label:%22%E2%9A%A1+Bounty%22+is:issue+is:open", 
    "label:%22lightning+bounty%22+is:issue+is:open",
    # 2. Bounties con etiqueta genérica pero que mencionan USDC/sats (Escrow)
    "label:bounty+is:issue+is:open+language:Python+usdc",
    "label:bounty+is:issue+is:open+language:Python+sats",
    # 3. Good First Issues que ofrecen pago real (filtraremos por $)
    "label:%22good+first+issue%22+is:issue+is:open+language:Python+bounty"
]

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def crear_notificacion(title, url, monto, plataforma):
    monto_str = f"${monto}" if monto != "Desconocido" else "Ver enlace"
    
    body = f"""🤖 **Bounty con Pago Garantizado (Escrow)**

- **Título:** {title}
- **Monto:** {monto_str}
- **Plataforma:** {plataforma}
- **Enlace:** [Ir al Issue]({url})

---
{PAYMENT_INFO}

---
*Este issue fue creado automáticamente por tu bot. Verifica que el escrow esté activo antes de trabajar.*
"""
    res = requests.post(f"https://api.github.com/repos/{MY_REPO}/issues", headers=HEADERS, json={
        "title": f"💰 Bounty Seguro ({monto_str}): {title[:50]}",
        "body": body,
        "labels": ["bounty", "escrow"]
    })
    if res.status_code == 201:
        print(f"  ✅ Notificación creada: {res.json()['html_url']}")
        return True
    else:
        print(f"  ❌ Error creando notificación: {res.text}")
        return False

def buscar_issues():
    issues = []
    print("🔎 Buscando bounties con pago garantizado...")
    
    for query in SEARCH_QUERIES:
        url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=5"
        try:
            res = requests.get(url, headers=HEADERS)
            if res.status_code == 200:
                for item in res.json().get("items", []):
                    title_lower = item["title"].lower()
                    body_lower = (item.get("body") or "").lower()
                    full_text = title_lower + " " + body_lower
                    
                    # Extraer monto ($ o sats)
                    monto = "Desconocido"
                    match_usd = re.search(r'(?:\$|USD\s*)(\d{1,5})(?:\.\d{1,2})?', full_text, re.IGNORECASE)
                    match_sats = re.search(r'(\d{1,10})\s*(?:sats|sat|SATS)', full_text, re.IGNORECASE)
                    
                    if match_usd:
                        monto = f"${match_usd.group(1)}"
                    elif match_sats:
                        monto = f"{match_sats.group(1)} sats"
                        
                    # Identificar plataforma
                    plataforma = "GitHub Issue"
                    if "lightning bounty" in full_text or "⚡" in item["title"]:
                        plataforma = "Lightning Bounties (Sats)"
                    elif "usdc" in full_text:
                        plataforma = "USDC Escrow"
                    
                    item["_monto"] = monto
                    item["_plataforma"] = plataforma
                    issues.append(item)
            else:
                print(f"  ⚠️ Error en búsqueda: {res.status_code}")
        except Exception as e:
            print(f"  ❌ Error de conexión: {e}")
            
    return issues

def main():
    if not GITHUB_TOKEN:
        print("❌ Falta el secreto PAT_TOKEN")
        return
    
    seen = load_seen()
    issues = buscar_issues()
    
    if not issues:
        print("No se encontraron bounties nuevos.")
        return
    
    # Filtrar los que ya hemos visto
    nuevos = [i for i in issues if str(i["id"]) not in seen]
    
    if not nuevos:
        print("✅ Todos los bounties encontrados ya fueron notificados anteriormente.")
        return
    
    # Tomar el más reciente de los nuevos
    issue = nuevos[0]
    title = issue["title"]
    url = issue["html_url"]
    monto = issue.get("_monto", "Desconocido")
    plataforma = issue.get("_plataforma", "Desconocida")
    issue_id = str(issue["id"])
    
    print(f"🎯 Nuevo Bounty: '{title}' | 💵 {monto} | 🛡️ {plataforma}")
    
    if crear_notificacion(title, url, monto, plataforma):
        seen.add(issue_id)
        save_seen(seen)
        print(f"✅ Estado guardado. Total de bounties notificados: {len(seen)}")

if __name__ == "__main__":
    main()
