@echo off
echo ===========================================
echo   Compilando executaveis para Windows
echo ===========================================

pip install -r requirements.txt
pip install pyinstaller

if not exist proxies.txt type nul > proxies.txt

echo.
echo [1/2] Compilando TwitchBot-Windows-GUI.exe (Interface Grafica)...
pyinstaller --noconfirm --clean --onefile --windowed --name "TwitchBot-Windows-GUI" --icon "icon.ico" --add-data "icon.ico;." --add-data "icon.png;." --add-data "proxies.txt;." main_gui.py

echo.
echo [2/2] Compilando TwitchBot-Windows-CLI.exe (Terminal)...
pyinstaller --noconfirm --clean --onefile --console --name "TwitchBot-Windows-CLI" --icon "icon.ico" main.py

echo.
echo ===========================================
echo   Concluido! Arquivos gerados em dist\
echo ===========================================
dir dist\*.exe
pause
