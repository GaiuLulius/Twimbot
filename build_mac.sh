#!/usr/bin/env bash
set -e

echo "=== Compilando executáveis para macOS ==="
pip install -r requirements.txt
pip install pyinstaller

# 1. Versão Gráfica (.app)
echo "Compilando TwitchBot-Mac-GUI.app..."
pyinstaller --noconfirm --clean --onedir --windowed \
    --name "TwitchBot-Mac-GUI" \
    --icon "icon.icns" \
    --add-data "icon.icns:." \
    --add-data "icon.png:." \
    --add-data "icon.ico:." \
    --add-data "proxies.txt:." \
    main_gui.py

# Remove pasta onedir intermediária mantendo apenas o bundle .app limpo
if [ -d "dist/TwitchBot-Mac-GUI" ] && [ -d "dist/TwitchBot-Mac-GUI.app" ]; then
    rm -rf "dist/TwitchBot-Mac-GUI"
fi

# 2. Versão Terminal CLI
echo "Compilando TwitchBot-Mac-CLI..."
pyinstaller --noconfirm --clean --onefile \
    --name "TwitchBot-Mac-CLI" \
    main.py

echo "=== Concluído! Arquivos gerados na pasta dist/ ==="
ls -lh dist/
