#!/usr/bin/env bash
set -e

echo "=== Compilando executáveis para Linux ==="
pip install -r requirements.txt
pip install pyinstaller

touch proxies.txt

# 1. Versão Gráfica
echo "[1/2] Compilando TwitchBot-Linux-GUI (Interface Gráfica)..."
pyinstaller --noconfirm --clean --onefile --windowed \
    --name "TwitchBot-Linux-GUI" \
    --add-data "icon.ico:." \
    --add-data "icon.png:." \
    --add-data "proxies.txt:." \
    main_gui.py

# 2. Versão Terminal
echo "[2/2] Compilando TwitchBot-Linux-CLI (Terminal)..."
pyinstaller --noconfirm --clean --onefile --console \
    --name "TwitchBot-Linux-CLI" \
    main.py

echo "=== Concluído! Arquivos gerados na pasta dist/ ==="
ls -lh dist/
