#!/bin/bash



# Alle laufenden Prozesse beenden (CLI, Netzwerk, Discovery)
pkill -f cli_process.py
pkill -f network_process.py
pkill -f discovery_process.py

# Pipes entfernen
rm -f cli_to_network.pipe
rm -f network_to_cli.pipe

# Aufräumen
rm -f away.flag
rm -f receive/offline_messages.txt


