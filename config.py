import json
import os
import sys

if sys.platform == "win32":
    _APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TwitchBot")
else:
    _APP_DIR = os.path.join(os.path.expanduser("~"), ".twitchbot")

os.makedirs(_APP_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(_APP_DIR, "config.json")

DEFAULTS = {
    "channel": "",
    "viewers": 3,
    "proxy_mode": "orion" if sys.platform == "darwin" else "dedicated",
    "show_browser": True,
    "set_160p": True,
    "use_webshare": True,
    "webshare_api_key": ""
}


def load() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save(data: dict) -> None:
    current = load()
    current.update(data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
