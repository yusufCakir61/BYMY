import toml
import os

CONFIG_FILE = "config.toml"

def get_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Konfigurationsdatei '{CONFIG_FILE}' nicht gefunden.")
    return toml.load(CONFIG_FILE)

def get_config_value(key, default=None):
    config = get_config()
    return config.get(key, default)
