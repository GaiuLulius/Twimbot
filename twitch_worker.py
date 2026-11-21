import time
import os
import sys
import random
import threading
import subprocess
from typing import Optional

# Import dos módulos de proxies e viewers
from proxy_manager import ProxyManager
from proxy_sources import webshare, free
from viewer_pool import ViewerPool
from viewer import (
    STATUS_ACTIVE, STATUS_CONNECTING, STATUS_RECONNECTING,
    STATUS_WAITING, STATUS_FAILED, STATUS_STOPPED
)

# Constantes para Web Proxies
WEB_PROXIES = [
    "https://www.croxyproxy.com/",
    "https://www.croxyproxy.rocks/",
    "https://www.croxy.network/",
    "https://www.croxy.org/",
    "https://www.blockaway.net/",
]

BANNER_XPATHS = [
    '//button[.//div[text()="Proceed"]]',
    '//button[.//div[contains(text(), "Continuar")]]',
    '//button[.//div[contains(text(), "Accept")]]',
    '//button[@data-a-target="consent-banner-consent-accept-button"]',
    '//button[@data-a-target="content-classification-gate-overlay-start-watching-button"]'
]

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
try { localStorage.setItem('video-quality', JSON.stringify({'default': '160p30'})); } catch(e) {}
"""


class WebProxyEngine:
    """Motor de 1 navegador com múltiplas abas via Web Proxies (CroxyProxy/BlockAway)"""
    def __init__(self, username, set_160p, show_browser, tab_count, notify_cb, stats_cb):
        self.username = username
        self.set_160p = set_160p
        self.show_browser = show_browser
        self.tab_count = tab_count
        self.notify_cb = notify_cb
        self.stats_cb = stats_cb
        self.tab_handles = []
        self.driver = None
        self.is_running = True

    def pause(self):
        pass

    def resume(self):
        pass

    def log(self, message, level="info"):
        if self.notify_cb:
            self.notify_cb(message, level)

    def _get_chrome_options(self):
        from selenium.webdriver.chrome.options import Options
        options = Options()

        # Stealth anti-bot
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        # Autoplay irrestrito e execucao em abas de segundo plano
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_argument("--mute-audio")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,ThrottleDisplayNoneAndVisibilityHiddenCrossOriginIframes")

        # Performance e recursos
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

        if not self.show_browser:
            # Modo Stealth Offscreen — indetectável
            options.add_argument("--window-position=-9999,-9999")
            options.add_argument("--window-size=1024,700")
        else:
            options.add_argument("--window-size=1024,700")

        return options

    def _tratar_banners_e_gates(self, driver):
        from selenium.webdriver.common.by import By
        for xpath in BANNER_XPATHS:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(1)
            except Exception:
                continue

    def _garantir_reproducao(self, driver):
        try:
            res = driver.execute_script("""
                let video = document.querySelector('video');
                if (video) {
                    video.muted = true;
                    if (video.paused) {
                        video.play();
                    }
                    return {found: true, paused: video.paused, time: video.currentTime};
                }
                return {found: false};
            """)
            if res and res.get("found"):
                return True
        except Exception:
            pass
        return False

    def _carregar_stream_na_aba(self, tab_num, proxy_url):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        proxy_domain = proxy_url.replace("https://", "").replace("http://", "").strip("/")
        self.log(f"[Aba #{tab_num}] Acessando {proxy_domain}...", "info")

        try:
            self.driver.set_page_load_timeout(35)
            self.driver.get(proxy_url)

            input_box = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "url"))
            )
            input_box.clear()
            input_box.send_keys(f"https://www.twitch.tv/{self.username}")
            input_box.send_keys(Keys.ENTER)

            self.log(f"[Aba #{tab_num}] Canal '{self.username}' enviado. Aguardando transmissão...", "info")

            video_carregou = False
            for _ in range(12):
                if not self.is_running:
                    return False
                time.sleep(2)
                self._tratar_banners_e_gates(self.driver)
                if self._garantir_reproducao(self.driver):
                    video_carregou = True
                    break

            if not video_carregou:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    for iframe in iframes:
                        try:
                            self.driver.switch_to.frame(iframe)
                            if self._garantir_reproducao(self.driver):
                                video_carregou = True
                                break
                            self.driver.switch_to.default_content()
                        except Exception:
                            self.driver.switch_to.default_content()

            if video_carregou:
                self.log(f"[Aba #{tab_num}] 🟢 Conexão ativa via {proxy_domain}! Live reproduzindo.", "success")
                return True
            else:
                self.log(f"[Aba #{tab_num}] Vídeo não iniciou em {proxy_domain}.", "warning")
                return False

        except TimeoutException:
            self.log(f"[Aba #{tab_num}] Timeout ao carregar {proxy_domain}.", "warning")
            return False
        except Exception as e:
            self.log(f"[Aba #{tab_num}] Erro: {str(e)[:100]}", "error")
            return False

    def run(self):
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException

        self.is_running = True
        self.tab_handles = []
        modo_txt = "Visível" if self.show_browser else "Stealth Offscreen"
        self.log(f"Iniciando 1 navegador com {self.tab_count} abas para '{self.username}' ({modo_txt})...", "info")

        options = self._get_chrome_options()
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH_JS})
        except Exception as e:
            self.log(f"Erro ao inicializar o Chrome: {e}", "error")
            self.is_running = False
            return

        proxy_pool = WEB_PROXIES.copy()
        random.shuffle(proxy_pool)

        aba_atual = 1
        tentativas = 0
        max_tentativas = self.tab_count * 3

        while aba_atual <= self.tab_count and tentativas < max_tentativas and self.is_running:
            tentativas += 1
            proxy_url = proxy_pool[(tentativas - 1) % len(proxy_pool)]

            if aba_atual == 1 and not self.tab_handles:
                handle = self.driver.current_window_handle
            else:
                try:
                    self.driver.switch_to.new_window('tab')
                    handle = self.driver.current_window_handle
                except Exception:
                    self.driver.execute_script("window.open('about:blank', '_blank');")
                    handle = self.driver.window_handles[-1]
                    self.driver.switch_to.window(handle)

            sucesso = self._carregar_stream_na_aba(aba_atual, proxy_url)

            if sucesso:
                self.tab_handles.append(handle)
                if self.stats_cb:
                    self.stats_cb(len(self.tab_handles), 0, 0, self.tab_count)
                aba_atual += 1
                time.sleep(2)
            else:
                if len(self.driver.window_handles) > 1 and handle != self.driver.window_handles[0]:
                    try:
                        self.driver.close()
                        self.driver.switch_to.window(self.tab_handles[-1] if self.tab_handles else self.driver.window_handles[0])
                    except Exception:
                        pass
                time.sleep(2)

        if not self.is_running:
            self.stop()
            return

        total_ativas = len(self.tab_handles)
        self.log(f"Total: {total_ativas}/{self.tab_count} abas ativas transmitindo na Twitch.", "success")

        try:
            while self.is_running:
                time.sleep(8)
                if not self.driver:
                    break
                try:
                    all_handles = self.driver.window_handles
                    if not all_handles:
                        break
                except WebDriverException:
                    self.log("Janela do navegador foi fechada pelo usuário.", "warning")
                    break

                for h in list(self.tab_handles):
                    if not self.is_running:
                        break
                    try:
                        if h in self.driver.window_handles:
                            self.driver.switch_to.window(h)
                            self._garantir_reproducao(self.driver)
                    except Exception:
                        pass
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            self.stop()

    def stop(self):
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
        self.tab_handles.clear()


class DedicatedProxyEngine:
    """Motor de alta performance usando Playwright, Embed oficial e Pool de Proxies com diversidade de IP"""
    def __init__(self, username, show_browser, tab_count, use_webshare, webshare_api_key, notify_cb, stats_cb):
        self.username = username
        self.show_browser = show_browser
        self.tab_count = tab_count
        self.use_webshare = use_webshare
        self.webshare_api_key = webshare_api_key
        self.notify_cb = notify_cb
        self.stats_cb = stats_cb
        self.pool: Optional[ViewerPool] = None
        self.is_running = True

    def log(self, message, level="info"):
        if self.notify_cb:
            self.notify_cb(message, level)

    def run(self):
        self.is_running = True
        self.log(f"Carregando gerenciador de proxies com IP único para '{self.username}'...", "info")

        pm = ProxyManager()
        loaded_count = 0

        # Carregar Webshare / proxies.txt
        if self.use_webshare:
            if self.webshare_api_key:
                try:
                    urls = webshare.fetch_api(self.webshare_api_key)
                    pm.load(urls, "webshare")
                    loaded_count += len(urls)
                    self.log(f"Carregados {len(urls)} proxies Webshare via API.", "success")
                except Exception as e:
                    self.log(f"Falha ao conectar na API Webshare: {e}", "warning")
            else:
                default_urls = webshare.load_default()
                if default_urls:
                    pm.load(default_urls, "webshare")
                    loaded_count += len(default_urls)
                    self.log(f"Carregados {len(default_urls)} proxies de 'proxies.txt'.", "info")

        # Não injetar listas públicas cruas sem validação.
        # Todos os proxies válidos (Webshare e SOCKS5 colhidos) residem em 'proxies.txt'.

        if loaded_count == 0:
            self.log("Nenhum proxy disponível em 'proxies.txt' ou online. Abortando.", "error")
            return

        modo_txt = "Visível" if self.show_browser else "Stealth Offscreen (Indetectável)"
        self.log(f"Iniciando {self.tab_count} visualizadores embed ({modo_txt})...", "info")

        self.pool = ViewerPool(
            channel=self.username,
            count=self.tab_count,
            proxy_manager=pm,
            on_event=self._on_pool_event,
            show_browser=self.show_browser
        )
        self.pool.start()

        while self.is_running:
            time.sleep(2)
            if not self.pool:
                break

    def _on_pool_event(self, viewer_id: int, status: str, proxy, message: str):
        if not self.is_running:
            return

        proxy_str = getattr(proxy, "url", str(proxy)) if proxy else ""
        if "@" in proxy_str:
            proxy_str = proxy_str.split("@")[-1]

        if status == STATUS_ACTIVE:
            self.log(f"[Viewer #{viewer_id+1}] 🟢 Transmitindo com sucesso via {proxy_str}!", "success")
        elif status == STATUS_CONNECTING:
            self.log(f"[Viewer #{viewer_id+1}] 🟡 Conectando ao player embed via {proxy_str}...", "info")
        elif status == STATUS_RECONNECTING:
            self.log(f"[Viewer #{viewer_id+1}] ⚠️ Reconectando: {message}", "warning")
        elif status == STATUS_WAITING:
            self.log(f"[Viewer #{viewer_id+1}] ⏳ {message}", "info")
        elif status == STATUS_FAILED:
            self.log(f"[Viewer #{viewer_id+1}] ❌ Falha definitiva: {message}", "error")
        elif message and "aguardando" in message:
            self.log(f"[Sistema] ⏱️ {message}", "info")

        if self.pool and self.stats_cb:
            st = self.pool.status()
            self.stats_cb(st["active"], st["reconnecting"], st["failed"], self.tab_count)

    def pause(self):
        if self.pool:
            self.pool.pause()
            self.log("Reconexões pausadas — viewers ativos continuam rodando.", "warning")

    def resume(self):
        if self.pool:
            self.pool.resume()
            self.log("Reconexões retomadas.", "info")

    def stop(self):
        self.is_running = False
        if self.pool:
            self.pool.stop()
            self.pool = None
        self.log("Todos os visualizadores foram encerrados.", "info")


class OrionEngine:
    """Motor nativo do macOS usando Orion (WebKit ultra-leve, 100% não-headless, sem detecção antibot)"""
    def __init__(self, username, tab_count, notify_cb, stats_cb):
        self.username = username
        self.tab_count = tab_count
        self.notify_cb = notify_cb
        self.stats_cb = stats_cb
        self.is_running = True

    def log(self, message, level="info"):
        if self.notify_cb:
            self.notify_cb(message, level)

    def pause(self):
        pass

    def resume(self):
        pass

    def run(self):
        self.is_running = True
        embed_url = f"https://player.twitch.tv/?channel={self.username}&parent=twitch.tv&muted=true&autoplay=true"

        self.log(f"Iniciando Orion Browser nativo com {self.tab_count} aba(s) para '{self.username}'...", "info")
        self.log("Modo nativo WebKit ativo: hardware-accelerated, zero flags de automação (não-headless).", "success")

        # 1. Abrir a primeira aba no Orion
        script_init = f'''
        tell application "Orion"
            activate
            open location "{embed_url}"
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script_init], check=True)
            self.log("[Aba #1] 🟢 Player embed da Twitch aberto no Orion!", "success")
            if self.stats_cb:
                self.stats_cb(1, 0, 0, self.tab_count)
        except Exception as e:
            self.log(f"Erro ao abrir o Orion: {e}", "error")
            self.is_running = False
            return

        # 2. Abrir abas adicionais com intervalo orgânico
        for i in range(2, self.tab_count + 1):
            if not self.is_running:
                break
            time.sleep(random.uniform(3, 6))
            if not self.is_running:
                break

            script_tab = f'''
            tell application "Orion"
                tell front window
                    make new tab with properties {{URL:"{embed_url}"}}
                end tell
            end tell
            '''
            try:
                subprocess.run(["osascript", "-e", script_tab], check=True)
                self.log(f"[Aba #{i}] 🟢 Nova aba carregada no Orion!", "success")
                if self.stats_cb:
                    self.stats_cb(i, 0, 0, self.tab_count)
            except Exception as e:
                self.log(f"[Aba #{i}] Falha ao abrir aba: {e}", "warning")

        self.log(f"Total: {self.tab_count} aba(s) ativas no Orion gerando visualizações reais.", "success")
        self.log("Orion está transmitindo com consumo mínimo. Clique em 'Parar Tudo' quando desejar.", "info")

        # 3. Loop de supervisão
        check_proc = 'tell application "System Events" to (name of processes) contains "Orion"'
        while self.is_running:
            time.sleep(5)
            try:
                res = subprocess.run(["osascript", "-e", check_proc], capture_output=True, text=True)
                if "true" not in res.stdout.lower():
                    self.log("O navegador Orion foi fechado pelo usuário.", "warning")
                    break
            except Exception:
                pass

        self.stop()

    def stop(self):
        self.is_running = False
        try:
            close_script = 'tell application "Orion" to quit'
            subprocess.run(["osascript", "-e", close_script], capture_output=True)
            self.log("Orion fechado e memória liberada.", "info")
        except Exception:
            pass


# PyQt5 Thread Wrapper
try:
    from PyQt5.QtCore import QThread, pyqtSignal

    class TwitchWorkerThread(QThread):
        status_message = pyqtSignal(str, str)
        stats_updated = pyqtSignal(int, int, int, int)  # active, connecting, failed, target
        worker_finished = pyqtSignal()

        def __init__(
            self,
            username: str,
            proxy_mode: str,
            show_browser: bool,
            tab_count: int,
            set_160p: bool = True,
            use_webshare: bool = True,
            webshare_api_key: str = "",
            parent=None
        ):
            super().__init__(parent)
            self.username = username
            self.proxy_mode = proxy_mode
            self.show_browser = show_browser
            self.tab_count = tab_count
            self.set_160p = set_160p
            self.use_webshare = use_webshare
            self.webshare_api_key = webshare_api_key

            if self.proxy_mode == "orion":
                self.engine = OrionEngine(
                    username=self.username,
                    tab_count=self.tab_count,
                    notify_cb=self.status_message.emit,
                    stats_cb=self.stats_updated.emit
                )
            elif self.proxy_mode == "dedicated":
                self.engine = DedicatedProxyEngine(
                    username=self.username,
                    show_browser=self.show_browser,
                    tab_count=self.tab_count,
                    use_webshare=self.use_webshare,
                    webshare_api_key=self.webshare_api_key,
                    notify_cb=self.status_message.emit,
                    stats_cb=self.stats_updated.emit
                )
            else:
                self.engine = WebProxyEngine(
                    username=self.username,
                    set_160p=self.set_160p,
                    show_browser=self.show_browser,
                    tab_count=self.tab_count,
                    notify_cb=self.status_message.emit,
                    stats_cb=self.stats_updated.emit
                )

        def run(self):
            try:
                self.engine.run()
            finally:
                self.worker_finished.emit()

        def pause(self):
            if hasattr(self.engine, "pause"):
                self.engine.pause()

        def resume(self):
            if hasattr(self.engine, "resume"):
                self.engine.resume()

        def stop(self):
            if self.engine:
                self.engine.stop()
            self.quit()
            self.wait(2000)

except ImportError:
    pass
