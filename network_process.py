## @file network_process.py
#  @brief Steuert die Netzwerkkommunikation des BYMY-Chatprogramms.
#
#  Dieses Modul übernimmt:
#  - Empfang & Versand von Nachrichten und Bildern per UDP
#  - Verwaltung bekannter Nutzer (JOIN, LEAVE)
#  - Auto-Reply bei gesetztem Abwesenheits-Flag
#  - Kommunikation mit dem CLI-Teil über Pipes
#  - Signalbehandlung für sauberes Beenden

import os               # Betriebssystem-Operationen (z.B. Pipes prüfen)
import socket           # UDP-Sockets für Nachrichtenversand/-empfang
import threading        # Threads, um gleichzeitig zu lauschen & CLI zu bedienen
import signal           # Signal-Handling für sauberes Beenden
import sys              # Systemfunktionen (z.B. sys.exit)
from config_handler import get_config  # Eigene Funktion zum Laden der Config

# Farben für Terminal-Ausgabe (nur optisch, keine Funktion im Protokoll)
RESET  = "\033[0m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
GREEN  = "\033[92m"

# Pipes & Status-Dateien
PIPE_CLI_TO_NET = "cli_to_network.pipe"  ## @var PIPE_CLI_TO_NET Pfad: CLI sendet an Network
PIPE_NET_TO_CLI = "network_to_cli.pipe"  ## @var PIPE_NET_TO_CLI Pfad: Network sendet an CLI
AWAY_FLAG       = "away.flag"             ## @var AWAY_FLAG Datei signalisiert Abwesenheit

# Laufzeitvariablen
autoreplied_to = set()  ## @var autoreplied_to Speichert Nutzer, die schon Auto-Reply bekamen
known_users    = {}     ## @var known_users Speichert bekannte Nutzer als Dict {handle: (ip, port)}


## @brief Schreibt eine Nachricht in die Pipe von Network zu CLI.
#  
#  Öffnet die Pipe @ref PIPE_NET_TO_CLI im Schreibmodus und überträgt die Nachricht.
#  So kann der CLI-Prozess diese lesen und anzeigen.
#
#  @param msg Die Nachricht, die geschrieben werden soll (String).
def write_to_cli(msg):
    try:
        with open(PIPE_NET_TO_CLI, "w") as pipe:
            # Nachricht plus Zeilenumbruch senden
            pipe.write(msg + "\n")
    except Exception as e:
        # Fehlerausgabe in Rot
        print(f"{RED}Fehler beim Schreiben in CLI-Pipe: {e}{RESET}")


        ## @brief Sendet eine WHO-Anfrage via UDP-Broadcast.
#  
#  Diese Anfrage fragt nach anderen aktiven Clients im Netzwerk.
#
#  @param whoisport Der Port, auf dem WHO-Anfragen gesendet werden.
def send_who(whoisport):
    msg = "WHO"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ('255.255.255.255', whoisport))


## @brief Sendet eine JOIN-Nachricht an alle im Netzwerk.
#  
#  Teilt den anderen Clients mit, dass dieser Client nun online ist.
#
#  @param handle Eigenes Handle (Benutzername).
#  @param port Port, auf dem dieser Client erreichbar ist.
#  @param whoisport Port für WHO/JOIN-Broadcasts.
def send_join(handle, port, whoisport):
    msg = f"JOIN {handle} {port}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ('255.255.255.255', whoisport))


## @brief Sendet eine LEAVE-Nachricht, um sich abzumelden.
#
#  Benachrichtigt andere Clients, dass dieser Client offline geht.
#
#  @param handle Eigenes Handle.
#  @param whoisport Port für WHO/LEAVE-Broadcasts.
def send_leave(handle, whoisport):
    msg = f"LEAVE {handle}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ('255.255.255.255', whoisport))


## @brief Sendet eine normale Chat-Nachricht an einen bekannten Nutzer.
#
#  Verwendet UDP-Direct Message, basierend auf der bekannten IP/Port-Kombination.
#
#  @param to_handle Handle des Empfängers.
#  @param text Nachrichtentext.
#  @param known_users Dictionary der bekannten Nutzer.
#  @param my_handle Eigenes Handle.
def send_msg(to_handle, text, known_users, my_handle):
    if to_handle not in known_users:
        print(f"{RED}Empfänger {to_handle} nicht bekannt{RESET}")
        return
    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode("utf-8"), (ip, port))


        ## @brief Sendet eine Bilddatei in mehreren Chunks an einen bekannten Empfänger.
#
#  Das Bild wird in Blöcke geteilt und über UDP verschickt.
#  Zuerst wird eine IMG_START-Nachricht gesendet, dann die Chunks,
#  zum Schluss ein IMG_END.
#
#  @param to_handle Empfänger-Handle.
#  @param filepath Pfad zur Bilddatei.
#  @param filesize Größe der Datei in Bytes.
#  @param known_users Dictionary der bekannten Nutzer.
#  @param config Aktuelle Konfiguration (Handle etc.).
def send_image(to_handle, filepath, filesize, known_users, config):
    if to_handle not in known_users:
        print(f"{RED}Empfänger {to_handle} nicht bekannt{RESET}")
        return
    ip, port = known_users[to_handle]
    chunk_size = 1024
    total_chunks = (filesize + chunk_size - 1) // chunk_size

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock, open(filepath, "rb") as f:
            # Starte Übertragung
            start_msg = f"IMG_START {config['handle']} {os.path.basename(filepath)} {total_chunks}"
            sock.sendto(start_msg.encode(), (ip, port))

            # Sende die Chunks nacheinander
            for i in range(total_chunks):
                chunk_data = f.read(chunk_size)
                chunk_msg = f"CHUNK {i}".encode() + b'||' + chunk_data
                sock.sendto(chunk_msg, (ip, port))

            # Beende Übertragung
            sock.sendto(b"IMG_END", (ip, port))
    except Exception as e:
        print(f"{RED}Fehler beim Bildversand: {e}{RESET}")


## @brief Liest Kommandos aus der CLI-to-Network Pipe & führt sie aus.
#
#  Unterstützt: SEND_MSG, SEND_IMAGE, WHO, JOIN, LEAVE.
#  Arbeitet kontinuierlich im Hauptthread.
#
#  @param config Aktuelle Konfiguration.
def read_cli_pipe(config):
    while True:
        with open(PIPE_CLI_TO_NET, "r") as pipe:
            for line in pipe:
                parts = line.strip().split(" ", 2)
                if not parts:
                    continue
                cmd = parts[0]

                # Nachricht senden
                if cmd == "SEND_MSG" and len(parts) == 3:
                    to, msg = parts[1], parts[2]
                    send_msg(to, msg, known_users, config["handle"])

                # Bild senden
                elif cmd == "SEND_IMAGE" and len(parts) == 4:
                    to, filepath, filesize_str = parts[1], parts[2], parts[3] if len(parts) > 3 else '0'
                    try:
                        filesize = int(filesize_str)
                    except:
                        filesize = 0
                    send_image(to, filepath, filesize, known_users, config)

                # WHO anfragen
                elif cmd == "WHO":
                    send_who(config["whoisport"])

                # JOIN senden
                elif cmd == "JOIN" and len(parts) == 3:
                    _, handle, port = parts
                    send_join(handle, int(port), config["whoisport"])

                # LEAVE senden
                elif cmd == "LEAVE" and len(parts) == 2:
                    send_leave(parts[1], config["whoisport"])