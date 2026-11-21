# Copilot Instructions for Twitch-main

## What this project does
- This repository implements a Twitch viewer bot using Selenium and proxy web front-ends.
- The core goal is to open multiple browser tabs/windows through proxy services and navigate to a Twitch stream URL.
- There are two main user entry points:
  - `main.py` — CLI-driven flow with saved settings in `settings.txt`
  - `main_gui.py` — PyQt5-based GUI that launches `twitch_worker_main.py` as a subprocess

## Architecture and important files
- `main.py`
  - Direct user prompt flow.
  - Uses `chromedriver_autoinstaller` to install ChromeDriver.
  - Builds a browser session and opens multiple proxy tabs from a hard-coded list.
  - Performs Twitch page interactions with explicit waits and JavaScript clicks.

- `main_gui.py`
  - GUI frontend using PyQt5 and a system tray icon.
  - Collects channel name, 160p quality option, headless option, and number of tabs.
  - Launches `twitch_worker_main.py` via `subprocess.Popen` with command-line arguments.

- `twitch_worker_main.py`
  - Acts as a launcher for the worker path.
  - Passes parameters from the GUI to the worker module.
  - Note: currently it imports `start_worker` from `twitch_worker.py`, but `twitch_worker.py` only defines `TwitchWorker`.

- `twitch_worker.py`
  - Defines a `TwitchWorker(QThread)` class.
  - Uses Selenium to open `https://www.croxyproxy.com/`, enter the Twitch URL, and optionally try to set video quality.
  - Tooling is mixed between PyQt5 and Selenium; treat this as a GUI-worker integration area.

## Important patterns and conventions
- `settings.txt` is used as a simple persisted configuration store:
  - `Twitch Username: ...`
  - `Set 160p: ...`
- The code assumes browsers can be launched without explicit Chrome binary path.
- Quality selection is only controlled when `set_160p` is `yes`; if so, the non-headless browser path is preferred.
- Proxy service URLs are hard-coded in `main.py`.
- The GUI path uses Windows-specific `creationflags=subprocess.CREATE_NO_WINDOW`.

## Dependencies and runtime setup
- Install dependencies with:
  - `pip install -r requirements.txt`
  - or via `run.sh` / `run.bat`
- Key packages:
  - `selenium`
  - `chromedriver-autoinstaller`
  - `PyQt5`
  - `pyinstaller`

## Developer workflows
- Run CLI mode:
  - `python3 main.py`
- Run GUI mode:
  - `python3 main_gui.py`
- Build executables:
  - `pyinstaller main.spec`
  - `pyinstaller main_gui.spec`
  - `Twimbot.spec` / `Twinbot.spec` are additional packaging targets

## What to look for first
- If modifying the GUI path, verify the `twitch_worker_main.py` / `twitch_worker.py` contract.
- `main.py` and `mainCopia.py` are similar; use `main.py` as the active CLI implementation.
- Avoid changing proxy URLs without verifying the proxy page structure, because Selenium relies on `#url` and the Twitch player DOM.

## Notes for AI agents
- Prefer small, incremental changes and validate by running the exact script entry point.
- Do not introduce new config systems; this project uses simple plaintext persistence in `settings.txt`.
- Keep UI text and prompts consistent with the existing Portuguese language style.
- Report integration issues clearly when the GUI/subprocess flow references missing symbols.
