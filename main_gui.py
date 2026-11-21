import sys
import os
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox, QSystemTrayIcon, QMenu, QAction,
    QTextEdit, QRadioButton, QButtonGroup, QCheckBox, QFrame
)
from PyQt5.QtGui import QIcon, QTextCursor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from twitch_worker import TwitchWorkerThread
import config

STYLE_SHEET = """
QWidget {
    background-color: #0e0e10;
    color: #efeff1;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QFrame.card {
    background-color: #18181b;
    border: 1px solid #2f2f35;
    border-radius: 8px;
    padding: 12px;
}

QLabel.title {
    font-size: 19px;
    font-weight: bold;
    color: #ffffff;
}

QLabel.subtitle {
    color: #adadb8;
    font-size: 12px;
}

QLabel.badge {
    background-color: #1f1f23;
    border: 1px solid #3a3a44;
    border-radius: 6px;
    padding: 5px 10px;
    font-weight: bold;
    font-size: 12px;
}

QLineEdit {
    background-color: #1f1f23;
    border: 1px solid #3a3a44;
    border-radius: 6px;
    padding: 8px;
    color: #ffffff;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #9146FF;
}

QSpinBox {
    background-color: #1f1f23;
    border: 1px solid #3a3a44;
    border-radius: 6px;
    padding: 6px;
    color: #ffffff;
}

QRadioButton, QCheckBox {
    color: #efeff1;
    spacing: 6px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QPushButton#btn_start {
    background-color: #9146FF;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px;
}
QPushButton#btn_start:hover {
    background-color: #772ce8;
}
QPushButton#btn_start:disabled {
    background-color: #3a3a44;
    color: #70707a;
}

QPushButton#btn_pause {
    background-color: #1f1f23;
    color: #ffd000;
    font-weight: bold;
    border: 1px solid #ffd00055;
    border-radius: 6px;
    padding: 10px;
}
QPushButton#btn_pause:hover {
    background-color: #2b2b33;
}
QPushButton#btn_pause:disabled {
    background-color: #1f1f23;
    color: #55555c;
    border-color: #2f2f35;
}

QPushButton#btn_stop {
    background-color: #eb0400;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px;
}
QPushButton#btn_stop:hover {
    background-color: #c20000;
}
QPushButton#btn_stop:disabled {
    background-color: #2f2f35;
    color: #55555c;
}

QPushButton#btn_harvest {
    background-color: #26262c;
    color: #bf94ff;
    border: 1px solid #772ce8;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton#btn_harvest:hover {
    background-color: #772ce8;
    color: #ffffff;
}
QPushButton#btn_harvest:disabled {
    background-color: #1f1f23;
    color: #55555c;
    border-color: #2f2f35;
}

QPushButton#btn_clear {
    background-color: #1f1f23;
    color: #adadb8;
    border: 1px solid #2f2f35;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#btn_clear:hover {
    background-color: #2f2f35;
    color: #ffffff;
}

QTextEdit#console {
    background-color: #0b0b0e;
    border: 1px solid #232328;
    border-radius: 6px;
    color: #adadb8;
    font-family: Menlo, Monaco, "Courier New", monospace;
    font-size: 11px;
    padding: 8px;
    line-height: 1.4;
}
"""


class HarvestThread(QThread):
    progress = pyqtSignal(str)
    finished_harvest = pyqtSignal(int)

    def __init__(self, target_count=20, max_to_test=250):
        super().__init__()
        self.target_count = target_count
        self.max_to_test = max_to_test

    def run(self):
        try:
            from proxy_harvester import harvest_working_proxies, update_proxies_file
            def cb(msg):
                self.progress.emit(msg)

            proxies = harvest_working_proxies(
                target_count=self.target_count,
                max_to_test=self.max_to_test,
                progress_cb=cb
            )
            base_dir = os.path.dirname(os.path.abspath(__file__))
            p_file = os.path.join(base_dir, "proxies.txt")
            total = update_proxies_file(proxies, file_path=p_file)
            self.finished_harvest.emit(total)
        except Exception as e:
            self.progress.emit(f"Erro ao buscar proxies: {e}")
            self.finished_harvest.emit(-1)


class TwitchGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Twitch Viewer Bot Pro")
        self.resize(800, 720)
        self.setMinimumSize(760, 680)
        self.setStyleSheet(STYLE_SHEET)

        self.worker_thread = None
        self.start_time = None
        self.is_paused = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)

        self._build_ui()
        self._setup_tray()
        self._load_config()

    def _build_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("🎮 Twitch Viewer Bot Pro", self)
        title.setProperty("class", "title")
        subtitle = QLabel("Gerenciador híbrido: Proxies Dedicados / Webshare ou Web Proxies", self)
        subtitle.setProperty("class", "subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Card de Configurações
        card_config = QFrame(self)
        card_config.setProperty("class", "card")
        config_layout = QVBoxLayout(card_config)
        config_layout.setSpacing(10)

        # Linha 1: Canal da Twitch e Quantidade de Viewers
        row1 = QHBoxLayout()
        lbl_channel = QLabel("Canal da Twitch:", self)
        lbl_channel.setFixedWidth(120)
        self.input_channel = QLineEdit(self)
        self.input_channel.setPlaceholderText("ex: gaules, loud_coringa, etc.")

        lbl_bots = QLabel("Qtd. de Bots:", self)
        self.spin_bots = QSpinBox(self)
        self.spin_bots.setRange(1, 50)
        self.spin_bots.setValue(5)
        self.spin_bots.setFixedWidth(85)

        row1.addWidget(lbl_channel)
        row1.addWidget(self.input_channel, 3)
        row1.addWidget(lbl_bots)
        row1.addWidget(self.spin_bots, 1)
        config_layout.addLayout(row1)

        # Linha 2: Modo de Conexão / Navegador
        row_proxy = QHBoxLayout()
        lbl_proxy_mode = QLabel("Navegador / Modo:", self)
        lbl_proxy_mode.setFixedWidth(125)
        lbl_proxy_mode.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        mode_vbox = QVBoxLayout()
        mode_vbox.setSpacing(6)

        self.radio_orion = QRadioButton("🍎 Orion Nativo (Recomendado no Mac - Janela Real WebKit)", self)
        self.radio_dedicated = QRadioButton("🌐 Proxies Dedicados (Playwright Stealth - proxies.txt)", self)
        self.radio_webproxy = QRadioButton("🔄 Web Proxies (Chrome Multi-abas - CroxyProxy)", self)
        self.radio_orion.setChecked(sys.platform == "darwin")
        if sys.platform != "darwin":
            self.radio_dedicated.setChecked(True)
            self.radio_orion.setEnabled(False)

        self.proxy_group = QButtonGroup(self)
        self.proxy_group.addButton(self.radio_orion)
        self.proxy_group.addButton(self.radio_dedicated)
        self.proxy_group.addButton(self.radio_webproxy)

        self.radio_orion.toggled.connect(self._on_mode_changed)
        self.radio_dedicated.toggled.connect(self._on_mode_changed)
        self.radio_webproxy.toggled.connect(self._on_mode_changed)

        mode_vbox.addWidget(self.radio_orion)
        mode_vbox.addWidget(self.radio_dedicated)
        mode_vbox.addWidget(self.radio_webproxy)

        row_proxy.addWidget(lbl_proxy_mode)
        row_proxy.addLayout(mode_vbox)
        row_proxy.addStretch()
        config_layout.addLayout(row_proxy)

        # Linha 3: Modo do Navegador (Visível vs Stealth Offscreen)
        row_browser = QHBoxLayout()
        lbl_mode = QLabel("Exibição:", self)
        lbl_mode.setFixedWidth(125)

        self.radio_offscreen = QRadioButton("👻 Modo Invisível (Stealth Offscreen)", self)
        self.radio_visible = QRadioButton("🖥️ Janela Visível", self)
        self.radio_offscreen.setChecked(True)

        self.browser_group = QButtonGroup(self)
        self.browser_group.addButton(self.radio_offscreen)
        self.browser_group.addButton(self.radio_visible)

        row_browser.addWidget(lbl_mode)
        row_browser.addWidget(self.radio_offscreen)
        row_browser.addWidget(self.radio_visible)
        row_browser.addStretch()
        config_layout.addLayout(row_browser)

        # Linha 4: Otimização
        row_opts = QHBoxLayout()
        lbl_opt = QLabel("Otimização:", self)
        lbl_opt.setFixedWidth(125)
        self.chk_160p = QCheckBox("Forçar qualidade 160p (Economizar CPU e RAM)", self)
        self.chk_160p.setChecked(True)
        row_opts.addWidget(lbl_opt)
        row_opts.addWidget(self.chk_160p)
        row_opts.addStretch()
        config_layout.addLayout(row_opts)

        # Linha 5: Proxies Dedicados
        row_proxy_ctrl = QHBoxLayout()
        row_proxy_ctrl.setSpacing(14)
        lbl_proxy_ctrl = QLabel("Lista de Proxies:", self)
        lbl_proxy_ctrl.setFixedWidth(125)

        self.chk_webshare = QCheckBox("Carregar proxies.txt", self)
        self.chk_webshare.setChecked(True)

        self.btn_harvest = QPushButton("⚡ Buscar Proxies Gratuitos", self)
        self.btn_harvest.setObjectName("btn_harvest")
        self.btn_harvest.clicked.connect(self.start_harvest)

        self.lbl_proxy_count = QLabel(self._get_proxy_count_str(), self)
        self.lbl_proxy_count.setStyleSheet("color: #adadb8; font-size: 11px;")

        row_proxy_ctrl.addWidget(lbl_proxy_ctrl)
        row_proxy_ctrl.addWidget(self.chk_webshare)
        row_proxy_ctrl.addWidget(self.btn_harvest)
        row_proxy_ctrl.addWidget(self.lbl_proxy_count)
        row_proxy_ctrl.addStretch()
        config_layout.addLayout(row_proxy_ctrl)

        # Linha 6: Chave API Webshare (Opcional)
        row_api = QHBoxLayout()
        lbl_api = QLabel("API Key Webshare:", self)
        lbl_api.setFixedWidth(125)
        self.input_api_key = QLineEdit(self)
        self.input_api_key.setPlaceholderText("Opcional: chave REST para auto-atualizar proxies Webshare")
        row_api.addWidget(lbl_api)
        row_api.addWidget(self.input_api_key)
        config_layout.addLayout(row_api)

        main_layout.addWidget(card_config)

        # Botões de Ação
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶  Iniciar Bots", self)
        self.btn_start.setObjectName("btn_start")

        self.btn_pause = QPushButton("❚❚  Pausar", self)
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.setEnabled(False)

        self.btn_stop = QPushButton("■  Parar Tudo", self)
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self.start_bot)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_stop.clicked.connect(self.stop_bot)

        btn_layout.addWidget(self.btn_start, 2)
        btn_layout.addWidget(self.btn_pause, 1)
        btn_layout.addWidget(self.btn_stop, 1)
        main_layout.addLayout(btn_layout)

        # Métricas em tempo real (Badges)
        metrics_layout = QHBoxLayout()
        self.badge_active = QLabel("🟢 Ativos: 0 / 0", self)
        self.badge_active.setProperty("class", "badge")

        self.badge_connecting = QLabel("🟡 Conectando: 0", self)
        self.badge_connecting.setProperty("class", "badge")

        self.badge_failed = QLabel("🔴 Falhas: 0", self)
        self.badge_failed.setProperty("class", "badge")

        self.badge_time = QLabel("⏱️ 00:00:00", self)
        self.badge_time.setProperty("class", "badge")

        metrics_layout.addWidget(self.badge_active)
        metrics_layout.addWidget(self.badge_connecting)
        metrics_layout.addWidget(self.badge_failed)
        metrics_layout.addWidget(self.badge_time)
        metrics_layout.addStretch()

        self.btn_clear = QPushButton("✕  Limpar", self)
        self.btn_clear.setObjectName("btn_clear")
        self.btn_clear.clicked.connect(self.clear_logs)
        metrics_layout.addWidget(self.btn_clear)

        main_layout.addLayout(metrics_layout)

        # Console de Logs Integrado
        self.console = QTextEdit(self)
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.document().setDocumentMargin(10)
        main_layout.addWidget(self.console)

        self.setLayout(main_layout)
        self.append_log("ℹ️ Sistema pronto. Configure o canal e clique em Iniciar.", "info")

    def _setup_tray(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_dir, "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_dir, "icon.icns")

        self.app_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.setWindowIcon(self.app_icon)

        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip("Twitch Viewer Bot")
        menu = QMenu()
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def _on_mode_changed(self):
        is_orion = self.radio_orion.isChecked()
        is_dedicated = self.radio_dedicated.isChecked()

        if is_orion:
            self.radio_offscreen.setEnabled(False)
            self.radio_visible.setChecked(True)
            self.chk_webshare.setEnabled(False)
            self.input_api_key.setEnabled(False)
            self.btn_harvest.setEnabled(False)
        elif is_dedicated:
            self.radio_offscreen.setEnabled(True)
            self.chk_webshare.setEnabled(True)
            self.input_api_key.setEnabled(True)
            self.btn_harvest.setEnabled(True)
        else:  # webproxy
            self.radio_offscreen.setEnabled(True)
            self.chk_webshare.setEnabled(False)
            self.input_api_key.setEnabled(False)
            self.btn_harvest.setEnabled(False)

    def _get_proxy_count_str(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        p_path = os.path.join(base_dir, "proxies.txt")
        if not os.path.exists(p_path):
            p_path = "proxies.txt"
        if os.path.exists(p_path):
            try:
                with open(p_path, "r", encoding="utf-8") as f:
                    count = len([l for l in f if l.strip() and not l.strip().startswith("#")])
                    return f"({count} no arquivo)"
            except Exception:
                pass
        return "(0 no arquivo)"

    def start_harvest(self):
        self.btn_harvest.setEnabled(False)
        self.btn_harvest.setText("⏳ Buscando...")
        self.append_log("Iniciando varredura rápida de proxies SOCKS5 públicos...", "info")
        self.harvest_thread = HarvestThread(target_count=20, max_to_test=250)
        self.harvest_thread.progress.connect(lambda msg: self.append_log(msg, "info"))
        self.harvest_thread.finished_harvest.connect(self._on_harvest_finished)
        self.harvest_thread.start()

    def _on_harvest_finished(self, total):
        self.btn_harvest.setEnabled(True)
        self.btn_harvest.setText("⚡ Buscar Proxies Gratuitos")
        if total >= 0:
            self.lbl_proxy_count.setText(f"({total} no arquivo)")
            self.append_log(f"Busca finalizada! Total de {total} proxies válidos em proxies.txt.", "success")
        else:
            self.append_log("Falha na atualização automática de proxies.", "error")

    def _load_config(self):
        cfg = config.load()
        if cfg.get("channel"):
            self.input_channel.setText(cfg["channel"])
        if cfg.get("viewers"):
            self.spin_bots.setValue(int(cfg["viewers"]))

        pm = cfg.get("proxy_mode", "orion")
        if pm == "orion" and sys.platform == "darwin":
            self.radio_orion.setChecked(True)
        elif pm == "webproxy":
            self.radio_webproxy.setChecked(True)
        else:
            self.radio_dedicated.setChecked(True)

        if cfg.get("show_browser"):
            self.radio_visible.setChecked(True)
        else:
            self.radio_offscreen.setChecked(True)
        self.chk_160p.setChecked(cfg.get("set_160p", True))
        self.chk_webshare.setChecked(cfg.get("use_webshare", True))
        if cfg.get("webshare_api_key"):
            self.input_api_key.setText(cfg["webshare_api_key"])

        self._on_mode_changed()

    def _save_config(self):
        if self.radio_orion.isChecked():
            pm = "orion"
        elif self.radio_webproxy.isChecked():
            pm = "webproxy"
        else:
            pm = "dedicated"

        config.save({
            "channel": self.input_channel.text().strip(),
            "viewers": self.spin_bots.value(),
            "proxy_mode": pm,
            "show_browser": self.radio_visible.isChecked(),
            "set_160p": self.chk_160p.isChecked(),
            "use_webshare": self.chk_webshare.isChecked(),
            "webshare_api_key": self.input_api_key.text().strip()
        })

    def append_log(self, message, level="info"):
        color_map = {
            "info": "#adadb8",
            "success": "#00f59b",
            "warning": "#ffd000",
            "error": "#ff4f4d"
        }
        color = color_map.get(level, "#adadb8")
        timestamp = time.strftime("%H:%M:%S")
        html_line = f"<span style='color: #63636e;'>[{timestamp}]</span> <span style='color: {color};'>{message}</span>"

        self.console.append(html_line)
        self.console.moveCursor(QTextCursor.End)

        try:
            log_file = os.path.join(config._APP_DIR, "bot.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level.upper()}] {message}\n")
        except Exception:
            pass

    def clear_logs(self):
        self.console.clear()

    def start_bot(self):
        channel = self.input_channel.text().strip()
        if not channel:
            self.input_channel.setFocus()
            self.append_log("Por favor, digite o nome do canal da Twitch.", "warning")
            return

        self._save_config()

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.input_channel.setEnabled(False)
        self.spin_bots.setEnabled(False)
        self.radio_orion.setEnabled(False)
        self.radio_dedicated.setEnabled(False)
        self.radio_webproxy.setEnabled(False)
        self.radio_offscreen.setEnabled(False)
        self.radio_visible.setEnabled(False)
        self.chk_160p.setEnabled(False)
        self.chk_webshare.setEnabled(False)
        self.input_api_key.setEnabled(False)
        self.btn_harvest.setEnabled(False)

        if self.radio_orion.isChecked():
            proxy_mode = "orion"
            modo_nome = "Orion Nativo (macOS WebKit - Janela Real)"
        elif self.radio_dedicated.isChecked():
            proxy_mode = "dedicated"
            modo_nome = "Proxies Dedicados (Embed Playwright)"
        else:
            proxy_mode = "webproxy"
            modo_nome = "Web Proxies (Chrome / CroxyProxy)"

        show_browser = self.radio_visible.isChecked()
        tab_count = self.spin_bots.value()
        set_160p = self.chk_160p.isChecked()
        use_webshare = self.chk_webshare.isChecked()
        webshare_api_key = self.input_api_key.text().strip()

        self.badge_active.setText(f"🟢 Ativos: 0 / {tab_count}")
        self.badge_connecting.setText("🟡 Conectando: 0")
        self.badge_failed.setText("🔴 Falhas: 0")
        self.start_time = time.time()
        self.timer.start(1000)

        self.append_log(f"Iniciando {tab_count} visualizadores para '{channel}' via {modo_nome}...", "info")

        self.worker_thread = TwitchWorkerThread(
            username=channel,
            proxy_mode=proxy_mode,
            show_browser=show_browser,
            tab_count=tab_count,
            set_160p=set_160p,
            use_webshare=use_webshare,
            webshare_api_key=webshare_api_key
        )
        self.worker_thread.status_message.connect(self.on_worker_status)
        self.worker_thread.stats_updated.connect(self.on_worker_stats)
        self.worker_thread.worker_finished.connect(self.on_worker_finished)
        self.worker_thread.start()

    def toggle_pause(self):
        if not self.worker_thread:
            return
        if not self.is_paused:
            self.worker_thread.pause()
            self.is_paused = True
            self.btn_pause.setText("▶  Retomar")
        else:
            self.worker_thread.resume()
            self.is_paused = False
            self.btn_pause.setText("❚❚  Pausar")

    def stop_bot(self):
        self.timer.stop()
        self.append_log("Solicitação de parada recebida. Finalizando todos os visualizadores...", "warning")

        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread = None

        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("❚❚  Pausar")
        self.is_paused = False
        self.btn_stop.setEnabled(False)
        self.input_channel.setEnabled(True)
        self.spin_bots.setEnabled(True)
        self.radio_orion.setEnabled(sys.platform == "darwin")
        self.radio_dedicated.setEnabled(True)
        self.radio_webproxy.setEnabled(True)
        self._on_mode_changed()

        self.badge_active.setText("🟢 Ativos: 0 / 0")
        self.badge_connecting.setText("🟡 Conectando: 0")
        self.badge_failed.setText("🔴 Falhas: 0")

    def on_worker_status(self, message, level):
        self.append_log(message, level)

    def on_worker_stats(self, active, connecting, failed, target):
        self.badge_active.setText(f"🟢 Ativos: {active} / {target}")
        self.badge_connecting.setText(f"🟡 Conectando: {connecting}")
        self.badge_failed.setText(f"🔴 Falhas: {failed}")
        if self.tray.isVisible():
            self.tray.setToolTip(f"{active}/{target} bots ativos na Twitch")

    def on_worker_finished(self):
        self.stop_bot()
        self.append_log("Execução finalizada.", "info")

    def _update_timer(self):
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            self.badge_time.setText(f"⏱️ {hrs:02d}:{mins:02d}:{secs:02d}")

    def quit_app(self):
        self.stop_bot()
        QApplication.quit()

    def closeEvent(self, event):
        self.quit_app()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TwitchGUI()
    window.show()
    sys.exit(app.exec_())
