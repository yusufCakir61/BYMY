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