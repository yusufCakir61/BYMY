#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

python3 "$DIR/discovery_process.py" &
sleep 1
python3 "$DIR/network_process.py" &
sleep 1
exec python3 "$DIR/cli_process.py"


