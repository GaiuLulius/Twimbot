import os
import sys
import requests
from typing import List

_API_LIST_URL = "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=100"


def fetch_api(api_key: str, timeout: int = 10) -> List[str]:
    """Busca proxies frescos via REST API usando API key."""
    headers = {"Authorization": f"Token {api_key}"}
    response = requests.get(_API_LIST_URL, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    proxies = []
    for p in data.get("results", []):
        ip = p["proxy_address"]
        port = p["port"]
        user = p["username"]
        password = p["password"]
        proxies.append(build_url(ip, str(port), user, password))
    return proxies


def load_default() -> List[str]:
    base_dirs = [
        getattr(sys, "_MEIPASS", ""),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        os.getcwd(),
        os.path.join(os.path.expanduser("~"), ".twitchbot")
    ]
    for d in base_dirs:
        if not d:
            continue
        p = os.path.join(d, "proxies.txt")
        if os.path.exists(p):
            try:
                proxies = load_file(p)
                if proxies:
                    return proxies
            except Exception:
                pass
    return []


def build_url(ip: str, port: str, user: str, password: str) -> str:
    return f"http://{user}:{password}@{ip}:{port}"


def fetch(url: str, timeout: int = 10) -> List[str]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return _parse(response.text)


def load_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return _parse(f.read())


def _parse(text: str) -> List[str]:
    proxies = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("socks5://") or line.startswith("http://") or line.startswith("https://"):
            proxies.append(line)
            continue
        parts = line.split(":")
        if len(parts) == 4:
            ip, port, user, password = parts
            proxies.append(build_url(ip, port, user, password))
        elif len(parts) == 2:
            ip, port = parts
            proxies.append(f"http://{ip}:{port}")
    return proxies
