import json
from pathlib import Path

_CONFIG = None

def load_config():
    global _CONFIG
    if _CONFIG is None:
        path = Path(__file__).resolve().parents[3] / "app-config" / "config.json"
        _CONFIG = json.load(open(path))
    return _CONFIG

def get_config(key, default=None):
    return load_config().get(key, default)
