#!/usr/bin/env python3

import toml
import os

## @file config_handler.py
#  @brief Lädt & verwaltet die zentrale Konfigurationsdatei (config.toml)
#  @details
#  Zweck:
#   1) Pfad zur globalen Konfigdatei speichern.
#   2) Funktion zum vollständigen Laden (Dict).
#   3) Funktion zum gezielten Lesen einzelner Werte.
#  Damit greift jedes andere Modul konsistent auf die Chat-Einstellungen zu.

CONFIG_FILE = "config.toml"

##
# @brief Lädt die gesamte Konfiguration aus der TOML-Datei.
# @return Ein Dictionary mit allen Konfigwerten.
# @throws FileNotFoundError, wenn Datei nicht existiert.
def get_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Konfigurationsdatei '{CONFIG_FILE}' nicht gefunden.")
    return toml.load(CONFIG_FILE)

##
# @brief Gibt gezielt einen einzelnen Wert aus der Konfig zurück.
# @param key Schlüsselname (z.B. 'handle', 'port', 'whoisport')
# @param default Optionaler Rückgabewert, falls Key nicht vorhanden.
# @return Der Wert aus der Datei oder der Default.
def get_config_value(key, default=None):
    config = get_config()
    return config.get(key, default)