#!/bin/bash

##
# @file stop_all.sh
# @brief Beendet alle BYMY-Chat Prozesse und räumt auf.
#
# @details
# Ablauf:
# 1) Beendet alle Python-Prozesse für CLI, Netzwerk und Discovery.
# 2) Löscht die Named Pipes.
# 3) Entfernt Flag-Dateien und gespeicherte Offline-Nachrichten.
#
# @note Dieses Skript kann gefahrlos mehrfach aufgerufen werden.
##

pkill -f cli_process.py
pkill -f network_process.py
pkill -f discovery_process.py

rm -f cli_to_network.pipe
rm -f network_to_cli.pipe

rm -f away.flag
rm -f receive/offline_messages.txt