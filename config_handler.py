import os
import toml

# ─────────────────────────────────────────────────────────────
# config_handler.py
# Zweck: Laden und Verwalten der Konfiguration für den Chat-Client
# ─────────────────────────────────────────────────────────────

# Pfad zur Konfigurationsdatei wird relativ zu diesem File berechnet
BASE_DIR = os.path.dirname(__file__)
CONFIG_FILENAME = "config.toml"
CONFIG_PATH = os.path.join(BASE_DIR, CONFIG_FILENAME)

# ─────────────────────────────────────────────────────────────
# Funktion: Konfiguration aus TOML-Datei laden
# Gibt ein Dictionary zurück mit z. B. 'handle', 'port', etc.
# ─────────────────────────────────────────────────────────────
def load_config():
    """
    Lädt Konfigurationswerte aus 'config.toml'.
    Gibt ein Dictionary zurück mit allen Werten.
    """

    if not os.path.isfile(CONFIG_PATH):
        raise FileNotFoundError(
            f"❌ Konfigurationsdatei nicht gefunden: '{CONFIG_PATH}'"
        )

    with open(CONFIG_PATH, mode="r", encoding="utf-8") as conf_file:
        config = toml.load(conf_file)

    return config