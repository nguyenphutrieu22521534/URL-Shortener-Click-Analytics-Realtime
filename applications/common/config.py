import json
from pathlib import Path

_CONFIG = None


def load_config():
    global _CONFIG

    if _CONFIG is None:
        base_dir = Path(__file__).resolve().parents[2]
        config_path = base_dir / "app-config" / "config.json"

        if not config_path.exists():
            raise RuntimeError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            _CONFIG = json.load(f)

    return _CONFIG


def get_config(key=None, default=None):
    config = load_config()

    if key is None:
        return config

    value = config
    for part in key.split("."):
        if not isinstance(value, dict):
            return default
        value = value.get(part, default)

    return value
