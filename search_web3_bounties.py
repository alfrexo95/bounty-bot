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

# Palabras clave y patrones que indican una estafa o malware
SCAM_PATTERNS = [
    r"curl\s+.*\|\s*python",  # curl | python
    r"wget\s+.*\|\s*bash",    # wget | bash
    r"bash\s+<\(curl",        # bash <(curl...)
    r"quickstart\.py",        # Scripts de "inicio rápido" sospechosos
    r"private\s*key",         # Petición de clave privada
    r"seed\s*phrase",         # Petición de frase semilla
    r"honeypot",              # Trampas explícitas
    r"wdoom",                 # Token específico de la estafa detectada
    r"doomsday", "wdoom", "honeypot", "prompt-injection", "clanker"               # Proyecto específico de la estafa
]

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def es_malicioso(title, body):
    """Analiza el título y el cuerpo en busca de patrones de estafa."""
    texto = (title + " " + (body or "")).lower()
    for pattern in SCAM_PATTERNS:
        if re.search(pattern, texto):
            return True
    return False

def crear_notificacion(plataforma, title, url, monto, seen):
    if url in seen or url.startswith("https://github.com/alfrexo95"):
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
    except Exception as e:
        print(f"  ❌ Error de conexión Aigen: {e}")

def buscar_arc(seen):
    print("🔎 Buscando bounties en ARC (ArcBounty)...")
    url = "https://arcbounty.app/api/v1/bounties?status=open"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            bounties = res.json()
            for b in bounties[:5]:
                title = b.get("title", "Bounty sin título")
                monto = f"${b.get('reward', 'N/A')} USDC"
                link = f"https://arcbounty.app/bounty/{b.get('id', '')}"
                crear_notificacion("ARC (ArcBounty)", title, link, monto, seen)
    except Exception as e:
        print(f"  ❌ Error de conexión ARC: {e}")

def buscar_github_web3(seen):
    print("🔎 Buscando issues de Roxonn, MergePay y USDC en GitHub...")
    queries = [
        "label:bounty+is:issue+is:open+language:Python+USDC",
        "label:bounty+is:issue+is:open+language:Python+Roxonn",
        "label:bounty+is:issue+is:open+language:Python+MergePay"
    ]
    for query in queries:
        url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=5"
        try:
            res = requests.get(url, headers=HEADERS)
            if res.status_code == 200:
                for item in res.json().get("items", []):
                    link = item["html_url"]
                    if "alfrexo95/bounty-bot" in link: continue
                    
                    repo_name = link.split("/")[3] + "/" + link.split("/")[4]
                    
                    # FILTRO 1: Repositorios sin PRs fusionados (Bounty Farms)
                    prs_url = f"https://api.github.com/search/issues?q=repo:{repo_name}+is:pr+is:merged&per_page=1"
                    prs_res = requests.get(prs_url, headers=HEADERS)
                    if prs_res.status_code == 200 and prs_res.json().get("total_count", 0) == 0:
                        print(f"  ⏭️ Saltando {repo_name} (0 PRs fusionados, probable farm)")
                        continue
                    
                    # FILTRO 2: Contenido malicioso o estafas
                    if es_malicioso(item["title"], item.get("body", "")):
                        print(f"  🚨 BLOQUEADO por seguridad: {item['title'][:50]}")
                        continue
                    
                    body = (item.get("body") or "").lower()
                    match = re.search(r'(?:\$|USD\s*)(\d{1,5})', body, re.IGNORECASE)
                    monto = f"${match.group(1)}" if match else "Ver enlace"
                    plataforma = "MergePay" if "mergepay" in body else ("Roxonn" if "roxonn" in body else "Web3")
                    crear_notificacion(plataforma, item["title"], link, monto, seen)
        except Exception as e:
            print(f"  ❌ Error en búsqueda GitHub: {e}")

if __name__ == "__main__":
    seen_urls = load_seen()
    buscar_aigen(seen_urls)
    buscar_arc(seen_urls)
    buscar_github_web3(seen_urls)
    save_seen(seen_urls)
