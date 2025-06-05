import sys
import os
import multiprocessing

# Lokale Importe – sicherstellen, dass Projektpfad korrekt eingebunden ist
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_handler import load_config
from discovery_process import run_discovery_process
from network_process import run_network_process
from cli_process import run_cli

# \file main.py
# \brief Hauptmodul zum Starten des BYMY-Chatprogramms mit Discovery, Netzwerk und CLI.
#
# Dieses Skript lädt die Konfiguration und startet drei Prozesse:
# - einen für das Discovery-Protokoll (JOIN/WHO),
# - einen für das Empfangen und Verarbeiten von Nachrichten und Bildern,
# - und das CLI zur Interaktion mit dem Benutzer.
#
# Alle Module kommunizieren über gemeinsame Datenstrukturen (via multiprocessing.Manager).

## \brief Hauptfunktion zur Initialisierung und Ausführung des Programms.
#
# Die Funktion lädt die Konfiguration aus der Datei `config.toml`,
# richtet gemeinsam genutzte Speicherbereiche (z. B. bekannte Benutzer, empfangene Bilder) ein,
# und startet die notwendigen Prozesse für Discovery, Netzwerk und CLI.
if __name__ == "__main__":
    # Multiprocessing Manager zur gemeinsamen Nutzung von Speicher zwischen Prozessen
    manager = multiprocessing.Manager()

    # Gemeinsame Datenstrukturen
    known_users = manager.dict()     # Dictionary: Handle → (IP, Port)
    image_events = manager.list()    # Liste für empfangene Bilder (für GUI/CLI)

    # 🔄 Lokale Konfiguration laden (aus TOML-Datei)
    config_data = load_config()  # normales Dictionary

    # 🧠 Konfiguration in multiprocessing-kompatibles Dictionary überführen
    config = manager.dict()
    for key, value in config_data.items():
        config[key] = value

    # 👁‍🗨 Bildereignisse hinzufügen (für Netzwerkprozess)
    config["image_events"] = image_events

    # ✅ Debug-Ausgabe zur Kontrolle
    print("🔍 Konfiguration geladen:", dict(config))

    # 🛰️ Discovery-Prozess starten (verarbeitet WHO & JOIN)
    p1 = multiprocessing.Process(
        target=run_discovery_process,
        args=(config["whoisport"],)
    )
    p1.start()

    # 🌐 Netzwerkprozess starten (Empfang von Nachrichten/Bildern)
    p2 = multiprocessing.Process(
        target=run_network_process,
        args=(known_users, config)
    )
    p2.start()

    # 👨‍💻 CLI starten (läuft im Hauptprozess)
    run_cli(config, known_users)

    # 🧹 Aufräumen: Subprozesse nach CLI-Beenden beenden
    p1.terminate()
    p2.terminate()
