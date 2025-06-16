import toml
import os

CONFIG_FILE = "config.toml"

##
# @file config_handler.py
# @brief Stellt Funktionen zum Laden & Abfragen der Konfiguration bereit.
#
# @details
# Dieses Modul bietet:
#   1) Sicheres Laden der Konfigurationsdatei `config.toml`
#   2) Zugriff auf bestimmte Einträge mit optionalem Default-Wert.
#

##
# @brief Lädt die vollständige Konfiguration.
#
# @details
# Ablauf:
#   1) Prüft, ob `config.toml` existiert.
#   2) Wenn vorhanden: Datei mit toml laden.
#   3) Wenn nicht vorhanden: FileNotFoundError auslösen.
#
# @return Dictionary mit der kompletten Konfiguration.
#
def get_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Konfigurationsdatei '{CONFIG_FILE}' nicht gefunden.")
    return toml.load(CONFIG_FILE)

##
# @brief Holt einen einzelnen Konfigurationswert.
#
# @details
# Ablauf:
#   1) Lädt die komplette Config.
#   2) Sucht den gewünschten Schlüssel.
#   3) Gibt Wert zurück oder Default, wenn nicht vorhanden.
#
# @param key Der zu suchende Schlüssel.
# @param default Wert, der zurückgegeben wird, wenn der Schlüssel fehlt.
# @return Wert des Schlüssels oder default.
#
def get_config_value(key, default=None):
    config = get_config()
    return config.get(key, default)
