#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Pipes anlegen (nur falls nicht vorhanden)
[[ -p cli_to_network.pipe ]] || mkfifo cli_to_network.pipe
[[ -p network_to_cli.pipe ]] || mkfifo network_to_cli.pipe

# Prozesse starten
python3 discovery_process.py &
sleep 1
python3 network_process.py &
sleep 1

# CLI starten (blockiert das Script, ist okay)
exec python3 cli_process.py
