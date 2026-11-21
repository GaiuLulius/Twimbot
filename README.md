# Twimbot

Automação multi-plataforma (GUI e CLI) para simulação de visualizadores na Twitch com suporte a proxies dedicados, web proxies e integração nativa.

---

## 🚀 Funcionalidades

- **Interface Gráfica (PyQt5)** com monitoramento em tempo real (ativos, conectando, falhas e tempo decorrido).
- **Modo CLI** headless para servidores e instâncias Linux/Docker.
- **3 Modos de Operação:**
  - `Dedicated Proxies`: rotação com Playwright Stealth / Selenium (HTTP, HTTPS, SOCKS5).
  - `Web Proxies`: multi-abas via provedores web (CroxyProxy, etc).
  - `Orion Nativo`: visualização leve e nativa (macOS).
- **Proxy Harvester:** busca e validação automática de proxies SOCKS5 públicos gratuitos.
- **Modo Stealth:** execução offscreen / headless invisível.
- **Multi-plataforma:** scripts prontos de build para Windows, Linux e macOS.

---

## 📦 Instalação

```bash
git clone git@github-bots:GaiuLulius/Twimbot.git
cd Twimbot

# Criar ambiente virtual
python -m venv .venv

# Ativar venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

---

## ⚙️ Configuração de Proxies

Crie ou edite o arquivo `proxies.txt` na raiz com seus proxies (um por linha):

```text
# Formatos suportados:
IP:PORTA:USUARIO:SENHA
IP:PORTA
socks5://IP:PORTA
http://IP:PORTA
```

---

## 🖥️ Como Executar

### Interface Gráfica (GUI)
```bash
python main_gui.py
```

### Linha de Comando (CLI)
```bash
python main.py
```

---

## 🛠️ Compilação para Executável (.exe / binário)

- **Windows:** execute `build_windows.bat` (gera `dist/TwitchBot-Windows-GUI.exe` e `dist/TwitchBot-Windows-CLI.exe`).
- **Linux:** execute `bash build_linux.sh` (gera `dist/TwitchBot-Linux-GUI` e `dist/TwitchBot-Linux-CLI`).
- **macOS:** execute `bash build_mac.sh` (gera `dist/TwitchBot-Mac-GUI.app`).

---

## 🐳 Docker

```bash
docker build -t twimbot .
docker run -it --rm twimbot
```

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais detalhes.
