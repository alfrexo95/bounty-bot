import os, requests, json, re

PAT_TOKEN = os.environ.get("PAT_TOKEN")
HEADERS = {"Authorization": f"token {PAT_TOKEN}", "Accept": "application/vnd.github.v3+json"}
MY_REPO = "alfrexo95/bounty-bot"
STATE_FILE = "seen_web3.json"

PAYMENT_INFO = """
### 💰 Payment Details
- BTC: bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00
- ETH: 0xA5E6eB31868A85127B1ED82b8C760193356206ED
- LTC: ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne
- Lightning: chieftrait089@walletofsatoshi.com

**Note:** I am a developer from Cuba. Due to the economic blockade, traditional payment methods are often blocked. Cryptocurrency is the most stable and free way for me to receive payments. I would appreciate it if the bounty could be paid in crypto. Thank you!
"""

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def crear_notificacion(plataforma, title, url, monto, seen):
    if url in seen:
        return False
        
    body = f"""🤖 **Bounty Encontrado en {plataforma}**

- **Título:** {title}
- **Monto:** {monto}
- **Plataforma:** {plataforma}
- **Enlace:** [{url}]({url})

---
{PAYMENT_INFO}
"""
    res = requests.post(f"https://api.github.com/repos/{MY_REPO}/issues", headers=HEADERS, json={
        "title": f"🪙 [{plataforma}] {title[:50]}",
        "body": body,
        "labels": ["bounty", "web3"]
    })
    if res.status_code == 201:
        print(f"  ✅ Notificación creada: {res.json()['html_url']}")
        seen.add(url)
        return True
    else:
        print(f"  ❌ Error: {res.text}")
        return False

def buscar_aigen(seen):
    print("🔎 Buscando misiones en Aigen Protocol...")
    url = "https://cryptogenesis.duckdns.org/work/board"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            misiones = res.json()
            if isinstance(misiones, list):
                for m in misiones[:3]:
                    title = m.get("title", "Misión sin título")
                    monto = m.get("reward", "Desconocido")
                    link = m.get("url", "https://cryptogenesis.duckdns.org/work/board")
                    crear_notificacion("Aigen Protocol", title, link, monto, seen)
        else:
            print(f"  ⚠️ Error Aigen: {res.status_code}")
    except Exception as e:
        print(f"  ❌ Error de conexión Aigen: {e}")

def buscar_vgrant(seen):
    print("🔎 Buscando issues de vGrant en GitHub...")
    queries = [
        "label:bounty+is:issue+is:open+language:Python+USDC",
        "label:bounty+is:issue+is:open+language:Python+vGrant"
    ]
    for query in queries:
        url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=3"
        try:
            res = requests.get(url, headers=HEADERS)
            if res.status_code == 200:
                for item in res.json().get("items", []):
                    title = item["title"]
                    link = item["html_url"]
                    body = (item.get("body") or "").lower()
                    match = re.search(r'(?:\$|USD\s*)(\d{1,5})', body, re.IGNORECASE)
                    monto = f"${match.group(1)}" if match else "Ver enlace"
                    crear_notificacion("vGrant (USDC)", title, link, monto, seen)
        except Exception as e:
            print(f"  ❌ Error en búsqueda vGrant: {e}")

if __name__ == "__main__":
    seen_urls = load_seen()
    buscar_aigen(seen_urls)
    buscar_vgrant(seen_urls)
    save_seen(seen_urls)
