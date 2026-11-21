import time
import random
import threading
from typing import Callable, Dict, Optional

from viewer import Viewer, STATUS_ACTIVE, STATUS_RECONNECTING, STATUS_WAITING, STATUS_FAILED
from proxy_manager import ProxyManager, _extract_ip

RECONNECT_DELAY = 2
WAIT_FOR_PROXY_TIMEOUT = 60
STARTUP_DELAY_MIN = 5
STARTUP_DELAY_MAX = 12
MAX_IP_FAILURES = 3  # desiste do IP fixado após N falhas consecutivas


class ViewerPool:
    def __init__(
        self,
        channel: str,
        count: int,
        proxy_manager: ProxyManager,
        on_event: Callable,
        show_browser: bool = False,
    ):
        self.channel = channel
        self.count = count
        self.proxy_manager = proxy_manager
        self.on_event = on_event
        self.show_browser = show_browser
        self._viewers: Dict[int, Optional[Viewer]] = {}
        self._viewer_ips: Dict[int, str] = {}       # IP fixado por viewer ao ficar ativo
        self._viewer_ip_fails: Dict[int, int] = {}  # falhas consecutivas no IP fixado
        self._viewers_lock = threading.Lock()
        self._running = False
        self._paused = False

    def start(self):
        self._running = True
        threading.Thread(target=self._start_staggered, daemon=True).start()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
        # Relança reconexão para viewers que morreram durante a pausa
        with self._viewers_lock:
            dead = [vid for vid, v in self._viewers.items() if v is None or not v.is_alive()]
        for viewer_id in dead:
            threading.Thread(target=self._reconnect, args=(viewer_id,), daemon=True).start()

    def _start_staggered(self):
        for i in range(self.count):
            if not self._running:
                break
            self._start_viewer(i)
            if i < self.count - 1 and self._running:
                delay = random.uniform(STARTUP_DELAY_MIN, STARTUP_DELAY_MAX)
                self.on_event(i, "waiting_next", None, f"aguardando {delay:.0f}s antes do próximo viewer...")
                time.sleep(delay)

    def stop(self):
        self._running = False
        with self._viewers_lock:
            viewers = list(self._viewers.values())
        for viewer in viewers:
            if viewer:
                viewer.stop()

    def get_viewer(self, viewer_id: int):
        with self._viewers_lock:
            return self._viewers.get(viewer_id)

    def status(self) -> dict:
        with self._viewers_lock:
            viewers = list(self._viewers.values())
        active = sum(1 for v in viewers if v and v.is_alive() and v.is_active)
        reconnecting = sum(1 for v in viewers if v and v.is_alive() and not v.is_active)
        failed = sum(1 for v in viewers if v is None)
        return {"active": active, "reconnecting": reconnecting, "failed": failed}

    def _reserved_ips(self, exclude_viewer_id: int) -> set:
        """IPs fixados por outros viewers ativos — não disponíveis para novos viewers."""
        with self._viewers_lock:
            return {ip for vid, ip in self._viewer_ips.items() if vid != exclude_viewer_id}

    def _start_viewer(self, viewer_id: int):
        reserved = self._reserved_ips(viewer_id)
        proxy = self.proxy_manager.acquire(reserved_ips=reserved)
        if proxy is None:
            self.on_event(viewer_id, STATUS_WAITING, None, "sem proxy disponível")
            with self._viewers_lock:
                self._viewers[viewer_id] = None
            return
        viewer = Viewer(
            viewer_id, self.channel, proxy, self._handle_status,
            show_browser=self.show_browser,
        )
        with self._viewers_lock:
            self._viewers[viewer_id] = viewer
        viewer.start()

    def _handle_status(self, viewer_id: int, status: str, proxy, message: str):
        self.on_event(viewer_id, status, proxy, message)
        if status == STATUS_ACTIVE and proxy:
            with self._viewers_lock:
                self._viewer_ips[viewer_id] = _extract_ip(proxy.url)
                self._viewer_ip_fails[viewer_id] = 0
        elif status == STATUS_RECONNECTING and proxy:
            with self._viewers_lock:
                if _extract_ip(proxy.url) == self._viewer_ips.get(viewer_id):
                    fails = self._viewer_ip_fails.get(viewer_id, 0) + 1
                    self._viewer_ip_fails[viewer_id] = fails
                    if fails >= MAX_IP_FAILURES:
                        self._viewer_ips.pop(viewer_id, None)
                        self._viewer_ip_fails[viewer_id] = 0
        elif status == STATUS_FAILED:
            with self._viewers_lock:
                self._viewer_ips.pop(viewer_id, None)
                self._viewer_ip_fails.pop(viewer_id, None)
        if status == STATUS_RECONNECTING and self._running:
            if proxy:
                _PERMANENT_ERRORS = (
                    "ERR_TUNNEL_CONNECTION_FAILED",
                    "ERR_SOCKS_CONNECTION_FAILED",
                    "ERR_PROXY_CONNECTION_FAILED",
                    "ERR_CERT_AUTHORITY_INVALID",
                )
                permanent = any(e in message for e in _PERMANENT_ERRORS)
                self.proxy_manager.release_failed(proxy, permanent=permanent)
            if not self._paused:
                threading.Thread(
                    target=self._reconnect, args=(viewer_id,), daemon=True
                ).start()

    def _reconnect(self, viewer_id: int):
        time.sleep(RECONNECT_DELAY)
        if not self._running:
            return
        deadline = time.time() + WAIT_FOR_PROXY_TIMEOUT
        while time.time() < deadline and self._running:
            with self._viewers_lock:
                preferred_ip = self._viewer_ips.get(viewer_id)
            reserved = self._reserved_ips(viewer_id)
            proxy = self.proxy_manager.acquire(preferred_ip=preferred_ip, reserved_ips=reserved)
            if proxy:
                viewer = Viewer(
                    viewer_id, self.channel, proxy, self._handle_status,
                    show_browser=self.show_browser,
                )
                with self._viewers_lock:
                    self._viewers[viewer_id] = viewer
                viewer.start()
                return
            time.sleep(5)
        self.on_event(viewer_id, STATUS_FAILED, None, "sem proxy disponível por 60s")
        with self._viewers_lock:
            self._viewers[viewer_id] = None
