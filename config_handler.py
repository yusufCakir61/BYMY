import toml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.toml")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Konfigurationsdatei '{CONFIG_PATH}' nicht gefunden.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return toml.load(f)
