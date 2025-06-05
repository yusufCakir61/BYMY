import toml
import os

# \file config_handler.py
# \brief Verwaltet das Laden der Konfigurationsdatei für den Chat-Client.
#
# Diese Datei enthält die Logik zum Einlesen einer TOML-Konfigurationsdatei,
# aus der z. B. der Benutzername (Handle) und andere Parameter ausgelesen werden.

# \brief Pfad zur Konfigurationsdatei
# Der Pfad wird relativ zum aktuellen Dateistandort berechnet.
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.toml")

## \brief Lädt die Konfigurationsdaten aus der Datei 'config.toml'.
##
## Diese Funktion stellt sicher, dass die Datei existiert, und lädt
## dann ihren Inhalt als Dictionary.
##
## \return Dictionary mit Konfigurationseinträgen (z. B. 'handle', 'port', etc.).
## \throws FileNotFoundError Wenn die Datei nicht existiert.
def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Konfigurationsdatei '{CONFIG_PATH}' nicht gefunden.")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return toml.load(f)
