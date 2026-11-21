import threading
import time
from dataclasses import dataclass
from typing import List, Optional

PENALIZE_AFTER = 3
DISCARD_AFTER = 5
COOLDOWN_SECONDS = 300


def _extract_ip(url: str) -> str:
    """Extrai o IP de uma URL de proxy (socks5://ip:port ou http://user:pass@ip:port)."""
    host = url.split("://", 1)[-1]
    host = host.split("@")[-1]
    return host.split(":")[0]


@dataclass
class Proxy:
    url: str
    source: str
    failures: int = 0
    consecutive_failures: int = 0
    last_failed: float = 0.0
    in_use: bool = False


class ProxyManager:
    def __init__(self):
        self._proxies: List[Proxy] = []
        self._lock = threading.Lock()

    def load(self, urls: List[str], source: str) -> None:
        with self._lock:
            existing = {p.url for p in self._proxies}
            for url in urls:
                if url not in existing:
                    self._proxies.append(Proxy(url=url, source=source))
                    existing.add(url)

    def acquire(self, preferred_ip: Optional[str] = None, reserved_ips: Optional[set] = None) -> Optional[Proxy]:
        with self._lock:
            now = time.time()
            active_ips = {_extract_ip(p.url) for p in self._proxies if p.in_use}
            blocked = active_ips | (reserved_ips or set())

            def _eligible(proxy: "Proxy", target_ip: Optional[str]) -> bool:
                if proxy.in_use:
                    return False
                ip = _extract_ip(proxy.url)
                if target_ip and ip != target_ip:
                    return False
                if not target_ip and ip in blocked:
                    return False
                if proxy.consecutive_failures >= PENALIZE_AFTER:
                    if now - proxy.last_failed < COOLDOWN_SECONDS:
                        return False
                    proxy.consecutive_failures = 0
                return True

            # Primeira passagem: tentar o IP preferido (mesmo servidor, porta diferente)
            if preferred_ip:
                for source in ("webshare", "free"):
                    for proxy in self._proxies:
                        if proxy.source == source and _eligible(proxy, preferred_ip):
                            proxy.in_use = True
                            return proxy

            # Segunda passagem: qualquer IP que não esteja bloqueado
            for source in ("webshare", "free"):
                for proxy in self._proxies:
                    if proxy.source == source and _eligible(proxy, None):
                        proxy.in_use = True
                        return proxy

            return None

    def release_ok(self, proxy: Proxy) -> None:
        with self._lock:
            proxy.in_use = False
            proxy.consecutive_failures = 0

    def release_failed(self, proxy: Proxy, permanent: bool = False) -> None:
        with self._lock:
            proxy.in_use = False
            if proxy not in self._proxies:
                return
            proxy.failures += 1
            proxy.consecutive_failures += 1
            proxy.last_failed = time.time()
            self._proxies.remove(proxy)
            if not permanent and proxy.failures < DISCARD_AFTER:
                self._proxies.append(proxy)

    def available_count(self) -> dict:
        with self._lock:
            now = time.time()
            result = {"webshare": 0, "free": 0}
            for p in self._proxies:
                if p.in_use:
                    continue
                penalized = (
                    p.consecutive_failures >= PENALIZE_AFTER
                    and now - p.last_failed < COOLDOWN_SECONDS
                )
                if not penalized:
                    result[p.source] = result.get(p.source, 0) + 1
            return result
