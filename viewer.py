import re
import sys
import time
import asyncio
import threading
from typing import Callable, Optional

from playwright.async_api import async_playwright

STATUS_CONNECTING = "connecting"
STATUS_ACTIVE = "active"
STATUS_RECONNECTING = "reconnecting"
STATUS_WAITING = "waiting"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"

EMBED_URL = "https://player.twitch.tv/?channel={channel}&parent=twitch.tv&muted=true&autoplay=true"

_BROWSER_ARGS_BASE = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--mute-audio",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-blink-features=AutomationControlled",
    "--autoplay-policy=no-user-gesture-required",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
]

_BROWSER_ARGS_OFFSCREEN = [
    "--window-position=-9999,-9999",
    "--window-size=1,1",
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Palavras-chave do botão de reconectar da Twitch (multi-idioma)
_RECONNECT_KEYWORDS = ("recarregar", "reload", "retry", "tentar novamente", "reconectar")


# Auto-aceitar avisos de conteúdo adulto (18+) e consentimento da Twitch
_AUTO_DISMISS_GATES_JS = """
(() => {
    const triggerClick = (el) => {
        if (!el) return;
        const opts = { bubbles: true, cancelable: true, view: window };
        el.dispatchEvent(new PointerEvent('pointerdown', opts));
        el.dispatchEvent(new MouseEvent('mousedown', opts));
        el.dispatchEvent(new PointerEvent('pointerup', opts));
        el.dispatchEvent(new MouseEvent('mouseup', opts));
        el.dispatchEvent(new MouseEvent('click', opts));
        if (typeof el.click === 'function') el.click();
    };

    const dismiss = () => {
        try {
            // 1. Alvo oficial da Twitch para Classificação de Conteúdo Adulto / 18+
            const matureBtn = document.querySelector('[data-a-target="content-classification-gate-overlay-start-watching-button"]');
            if (matureBtn && !matureBtn.disabled) {
                triggerClick(matureBtn);
            }
            // 2. Banner de consentimento / cookies
            const consentBtn = document.querySelector('[data-a-target="consent-banner-consent-accept-button"]');
            if (consentBtn && !consentBtn.disabled) {
                triggerClick(consentBtn);
            }
            // 3. Fallback por texto do botão (multi-idioma)
            const buttons = document.querySelectorAll('button');
            for (const b of buttons) {
                const txt = (b.textContent || '').trim().toLowerCase();
                if (
                    txt.includes('começar a assistir') ||
                    txt.includes('start watching') ||
                    txt.includes('continuar assistindo') ||
                    txt.includes('iniciar visualización') ||
                    txt.includes('entendi') ||
                    txt === 'continuar' ||
                    txt === 'accept' ||
                    txt === 'aceitar' ||
                    txt === 'proceed'
                ) {
                    triggerClick(b);
                }
            }
            // 4. Remove overlay persistente (exige login ou overlay 18+ escuro) e garante playback
            const overlay = document.querySelector(
                '[data-a-target="content-classification-gate-overlay"], [data-a-target="player-overlay-content-gate"]'
            );
            if (overlay) {
                overlay.remove();
            }
            const v = document.querySelector('video');
            if (v && v.paused) {
                v.muted = true;
                v.play().catch(() => {});
            }
        } catch(e) {}
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', dismiss);
    } else {
        dismiss();
    }

    const observer = new MutationObserver(dismiss);
    observer.observe(document.documentElement, { childList: true, subtree: true });
    setInterval(dismiss, 1000);
})();
"""


def _parse_proxy(proxy_url: str) -> dict:
    for scheme in ("socks5://", "http://", "https://"):
        if proxy_url.startswith(scheme):
            rest = proxy_url[len(scheme):]
            if "@" in rest:
                auth, hostport = rest.rsplit("@", 1)
                user, password = auth.split(":", 1)
                return {"server": f"{scheme}{hostport}", "username": user, "password": password}
            return {"server": proxy_url}
    return {"server": proxy_url}


class Viewer(threading.Thread):
    def __init__(self, viewer_id: int, channel: str, proxy, on_status: Callable, show_browser: bool = False):
        super().__init__(daemon=True)
        self.viewer_id = viewer_id
        self.channel = channel
        self.proxy = proxy
        self.on_status = on_status
        self.show_browser = show_browser
        self._running = False
        self._stopped = False
        self._start_time: Optional[float] = None
        self._page = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_active(self) -> bool:
        return self._start_time is not None

    @property
    def uptime(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def run(self):
        # asyncio.run() cria um event loop isolado por thread — evita o
        # "greenlet cannot switch to a different thread" do sync_playwright
        asyncio.run(self._async_run())

    async def _async_run(self):
        self._loop = asyncio.get_event_loop()

        if self._stopped:
            return

        self._running = True
        self.on_status(self.viewer_id, STATUS_CONNECTING, self.proxy, "")

        pw = browser = None

        try:
            pw = await async_playwright().start()

            args = _BROWSER_ARGS_BASE + ([] if self.show_browser else _BROWSER_ARGS_OFFSCREEN)
            # Usa Chrome instalado no sistema quando disponível, com fallback para Chromium padrão
            try:
                browser = await pw.chromium.launch(
                    headless=False,
                    channel="chrome",
                    proxy=_parse_proxy(self.proxy.url),
                    args=args,
                )
            except Exception:
                browser = await pw.chromium.launch(
                    headless=False,
                    proxy=_parse_proxy(self.proxy.url),
                    args=args,
                )

            context = await browser.new_context(user_agent=_USER_AGENT)
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                "try { localStorage.setItem('video-quality', JSON.stringify({'default': '160p30'})); } catch(e) {}"
            )
            await context.add_init_script(_AUTO_DISMISS_GATES_JS)

            page = await context.new_page()
            self._page = page

            url = EMBED_URL.format(channel=self.channel)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._dismiss_gates(page)
            await page.wait_for_selector("video", timeout=30000)
            await self._dismiss_gates(page)
            await page.evaluate(
                "() => { const v = document.querySelector('video');"
                " if(v){ v.muted=true; v.volume=0; v.play().catch(()=>{}); } }"
            )

            await asyncio.sleep(2)
            await self._set_quality_160p(page)

            self._start_time = time.time()
            self.on_status(self.viewer_id, STATUS_ACTIVE, self.proxy, "")

            health_failures = 0
            while self._running:
                await asyncio.sleep(4)
                await self._dismiss_gates(page)
                try:
                    await page.evaluate("""() => {
                        const v = document.querySelector('video');
                        if (v && v.paused) {
                            v.play().catch(() => {});
                        }
                        return document.readyState;
                    }""")
                    health_failures = 0
                except Exception as e:
                    health_failures += 1
                    if health_failures >= 3:
                        raise Exception(f"página desconectada após {health_failures} falhas: {e}")
                    continue

                # Verificação de erro do player da Twitch (Erro 2000 / botão de recarregar)
                if await self._reconnect_button_visible(page):
                    # Tenta clicar no botão de recarregar
                    try:
                        labels = page.locator('[data-a-target="tw-core-button-label-text"]')
                        for i in range(await labels.count()):
                            lbl = labels.nth(i)
                            txt = (await lbl.text_content() or "").lower()
                            if any(kw in txt for kw in _RECONNECT_KEYWORDS):
                                await lbl.click()
                                break
                    except Exception:
                        pass
                    await asyncio.sleep(6)
                    # Se ainda estiver visível, tenta reload suave do embed
                    if await self._reconnect_button_visible(page):
                        try:
                            await page.reload(wait_until="domcontentloaded", timeout=25000)
                            await asyncio.sleep(4)
                        except Exception:
                            pass
                    # Só encerra o proxy se após as tentativas de recuperação o erro persistir
                    if await self._reconnect_button_visible(page):
                        raise Exception("botão de reiniciar detectado e persistente — trocando proxy")

        except Exception as e:
            if self._running:
                self.on_status(self.viewer_id, STATUS_RECONNECTING, self.proxy, str(e))
            return
        finally:
            self._page = None
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if pw:
                try:
                    await pw.stop()
                except Exception:
                    pass

        if self._running:
            self.on_status(self.viewer_id, STATUS_RECONNECTING, self.proxy, "browser fechado inesperadamente")

    async def _dismiss_gates(self, page):
        """Clica imediatamente em avisos de conteúdo adulto (18+) e remove barreiras."""
        try:
            # 1. Clique nativo Playwright com force=True
            selectors = [
                'button[data-a-target="content-classification-gate-overlay-start-watching-button"]',
                '[data-a-target="player-overlay-content-gate"] button',
                'div[data-a-target="content-classification-gate-overlay"] button',
                'button:has-text("Começar a assistir")',
                'button:has-text("Start Watching")',
                'button:has-text("Continuar assistindo")',
                'button:has-text("Entendi")',
                '[data-a-target="consent-banner-consent-accept-button"]',
            ]
            for sel in selectors:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        await loc.first.click(force=True, timeout=1200)
                except Exception:
                    pass

            # 2. Executa bypass no DOM: remove overlay bloqueador se existir e garante playback
            await page.evaluate("""() => {
                const overlay = document.querySelector(
                    '[data-a-target="content-classification-gate-overlay"], [data-a-target="player-overlay-content-gate"]'
                );
                if (overlay) {
                    overlay.remove();
                }
                const v = document.querySelector('video');
                if (v && v.paused) {
                    v.muted = true;
                    v.play().catch(() => {});
                }
            }""")
        except Exception:
            pass

    async def _set_quality_160p(self, page) -> bool:
        """Forces 160p via the player settings UI. Fails silently."""
        try:
            # Reveal controls by hovering the video center
            box = await page.locator("video").first.bounding_box()
            if box:
                await page.mouse.move(
                    box["x"] + box["width"] / 2,
                    box["y"] + box["height"] / 2,
                )
            await asyncio.sleep(0.8)

            # Open settings menu (gear icon)
            await page.locator('[data-a-target="player-settings-button"]').click(timeout=5000)
            await asyncio.sleep(0.5)

            # Navigate to Quality submenu
            await page.locator('[data-a-target="player-settings-menu-item-quality"]').click(timeout=5000)
            await asyncio.sleep(0.5)

            # Find quality options — prefer 160p, fall back to lowest video quality
            # (skip "Auto" and "Somente Áudio" / "Audio Only")
            items = page.locator('[data-a-target="player-settings-menu"] button')
            count = await items.count()
            target_160p = None
            lowest_video = None
            for i in range(count):
                text = (await items.nth(i).text_content() or "").lower()
                if "160p" in text:
                    target_160p = i
                    break
                # track last item that looks like a video quality (e.g. "720p", "480p30")
                if re.search(r'\d+p', text) and "auto" not in text:
                    lowest_video = i
            chosen = target_160p if target_160p is not None else lowest_video
            if chosen is not None:
                await items.nth(chosen).click()
            return True
        except Exception:
            return False

    async def _reconnect_button_visible(self, page) -> bool:
        labels = page.locator('[data-a-target="tw-core-button-label-text"]')
        count = await labels.count()
        for i in range(count):
            text = (await labels.nth(i).text_content() or "").lower()
            if any(kw in text for kw in _RECONNECT_KEYWORDS):
                return True
        return False

    def stop(self):
        self._running = False
        self._stopped = True
        page = self._page
        loop = self._loop
        if page and loop and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(page.close(), loop)
            except Exception:
                pass
