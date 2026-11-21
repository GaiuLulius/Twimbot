import os
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Optional

SOURCES = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt"
]

TEST_URL = "https://player.twitch.tv/?channel=twitch&parent=twitch.tv"


def fetch_raw_proxies(timeout: int = 6) -> List[str]:
    raw = []
    for s in SOURCES:
        try:
            r = requests.get(s, timeout=timeout)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    line = line.strip()
                    if line and ":" in line and not line.startswith("#"):
                        raw.append(line)
        except Exception:
            continue
    # Deduplica preservando ordem
    return list(dict.fromkeys(raw))


def validate_twitch_socks5(proxy_hostport: str, timeout: float = 3.5) -> Optional[str]:
    proxy_url = f"socks5://{proxy_hostport}"
    try:
        r = requests.get(
            TEST_URL,
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )
        if r.status_code == 200 and len(r.text) > 10000:
            return proxy_url
    except Exception:
        pass
    return None


def harvest_working_proxies(
    target_count: int = 25,
    max_to_test: int = 350,
    progress_cb: Optional[Callable[[str], None]] = None
) -> List[str]:
    """Busca e valida proxies SOCKS5 públicos especificamente compatíveis com a Twitch."""
    if progress_cb:
        progress_cb("Baixando listas atualizadas de proxies SOCKS5...")

    candidates = fetch_raw_proxies()
    if not candidates:
        if progress_cb:
            progress_cb("Nenhum proxy baixado das fontes públicas.")
        return []

    to_test = candidates[:max_to_test]
    if progress_cb:
        progress_cb(f"Testando {len(to_test)} proxies contra o player da Twitch...")

    working = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(validate_twitch_socks5, p): p for p in to_test}
        for future in as_completed(futures):
            res = future.result()
            if res:
                working.append(res)
                if progress_cb:
                    progress_cb(f"🟢 Proxy válido encontrado: {res} ({len(working)}/{target_count})")
                if len(working) >= target_count:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

    return working


def update_proxies_file(new_proxies: List[str], file_path: str = "proxies.txt") -> int:
    """Atualiza o arquivo proxies.txt mesclando com os proxies autenticados existentes."""
    existing_lines = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_lines.append(line)
        except Exception:
            pass

    # Mantem proxies autenticados existentes (ex: Webshare IP:PORT:USER:PASS)
    auth_proxies = [p for p in existing_lines if len(p.split(":")) == 4]

    combined = list(dict.fromkeys(auth_proxies + new_proxies))
    with open(file_path, "w", encoding="utf-8") as f:
        for p in combined:
            f.write(f"{p}\n")

    return len(combined)
