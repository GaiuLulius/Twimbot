import requests
from typing import List

# Fontes HTTP (porta 80) — não suportam HTTPS/CONNECT, usadas como fallback
_HTTP_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
]

# Fontes SOCKS5 — suportam HTTPS sem limitação de CONNECT
_SOCKS5_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
]


def fetch(timeout: int = 10) -> List[str]:
    proxies = []

    # SOCKS5 primeiro — são os únicos que funcionam com HTTPS via Playwright
    for url in _SOCKS5_SOURCES:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            for line in response.text.strip().splitlines():
                line = line.strip()
                if line and ":" in line and not line.startswith("#"):
                    proxies.append(f"socks5://{line}")
        except Exception:
            continue

    # HTTP como fallback (podem funcionar para sites HTTP)
    for url in _HTTP_SOURCES:
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            for line in response.text.strip().splitlines():
                line = line.strip()
                if line and ":" in line:
                    proxies.append(f"http://{line}")
        except Exception:
            continue

    return proxies


def validate(proxy_url: str, timeout: int = 5) -> bool:
    try:
        response = requests.get(
            "https://api.ipify.org",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=timeout,
        )
        return response.status_code == 200
    except Exception:
        return False
