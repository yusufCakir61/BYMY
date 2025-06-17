#!/bin/bash

##
# @file main.sh
# @brief Startet den BYMY Chat-Prozess: Pipes anlegen, Discovery, Netzwerk, CLI.
#
# @details
# Ablauf:
# 1) Wechselt ins Skriptverzeichnis.
# 2) Erstellt die Named Pipes falls nötig.
# 3) Startet den Discovery-Prozess (UDP-Broadcast).
# 4) Startet den Netzwerk-Prozess (Nachrichten, Bilder, TCP-Receiver).
# 5) Startet den CLI-Prozess im Vordergrund.
#
# @note Das Skript blockiert, solange CLI läuft. 
# Beenden der CLI beendet i.d.R. alle Sub-Prozesse.
##

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

[[ -p cli_to_network.pipe ]] || mkfifo cli_to_network.pipe
[[ -p network_to_cli.pipe ]] || mkfifo network_to_cli.pipe

python3 discovery_process.py &
sleep 1

python3 network_process.py &
sleep 1

exec python3 cli_process.py