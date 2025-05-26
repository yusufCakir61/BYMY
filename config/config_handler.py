## @file network_process.py
## @brief Behandelt Netzwerkkommunikation (JOIN, WHO, MSG) im Chat

import toml
import os

CONFIG_PATH = "config.toml"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Konfigurationsdatei '{CONFIG_PATH}' nicht gefunden.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return toml.load(f)