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

                    ## @brief Lauscht auf eingehende UDP-Pakete und verarbeitet alle Typen.
#
#  Unterstützt:
#  - Empfang und Speichern von Bildern in Chunks
#  - Steuerbefehle (KNOWNUSERS, MSG, JOIN, LEAVE)
#
#  @param port Lokaler UDP-Port zum Hören.
#  @param config Laufzeit-Konfiguration.
def listen_on_port(port, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))  # Bind an alle Interfaces
    image_dir = config.get("imagepath", "receive/")
    os.makedirs(image_dir, exist_ok=True)
    incoming_images = {}

    while True:
        try:
            data, addr = sock.recvfrom(65535)
        except OSError as e:
            print(f"{RED}Socket Error: {e}{RESET}")
            break

        # === Bildübertragung: Startsignal erkennen ===
        if data.startswith(b"IMG_START"):
            try:
                parts = data.decode().strip().split(" ", 3)
                if len(parts) == 4:
                    _, sender, filename, num_chunks_str = parts
                    num_chunks = int(num_chunks_str)
                    # Neues Bild-Objekt vorbereiten
                    incoming_images[(addr, filename)] = {
                        "from": sender,
                        "filename": filename,
                        "total": num_chunks,
                        "received": 0,
                        "chunks": {}
                    }
            except Exception as e:
                print(f"{RED}Fehler bei IMG_START: {e}{RESET}")
            continue

        # === Bildübertragung: Chunk empfangen ===
        elif data.startswith(b"CHUNK"):
            try:
                header, chunk_data = data.split(b'||', 1)
                _, chunk_num_str = header.decode().split()
                chunk_num = int(chunk_num_str)
                for key in incoming_images:
                    if key[0] == addr:
                        incoming_images[key]["chunks"][chunk_num] = chunk_data
                        incoming_images[key]["received"] += 1
                        break
            except Exception as e:
                print(f"{RED}Fehler bei CHUNK: {e}{RESET}")
            continue

        # === Bildübertragung: Ende verarbeiten ===
        elif data.startswith(b"IMG_END"):
            for key, info in list(incoming_images.items()):
                if info["received"] == info["total"]:
                    save_path = os.path.join(image_dir, info["filename"])
                    try:
                        full_data = b''.join(info["chunks"][i] for i in range(info["total"]))
                        with open(save_path, "wb") as f:
                            f.write(full_data)
                        write_to_cli(f"IMG {info['from']} {info['filename']}")
                        del incoming_images[key]
                    except Exception as e:
                        print(f"{RED}Fehler beim Speichern des Bildes: {e}{RESET}")
            continue

        # === Alle sonstigen Befehle (KNOWNUSERS, MSG, JOIN, LEAVE) ===
        msg = data.decode("utf-8", errors="ignore").strip()
        parts = msg.split(" ", 2)
        if not parts:
            continue

        cmd = parts[0]

        ## KNOWNUSERS: Update lokale User-Liste
        if cmd == "KNOWNUSERS":
            entries = msg[len("KNOWNUSERS "):].split(", ")
            for entry in entries:
                p = entry.split()
                if len(p) == 3:
                    h, ip, port_str = p
                    known_users[h] = (ip, int(port_str))
            users_str = ", ".join(f"{h} {ip} {p}" for h, (ip, p) in known_users.items())
            write_to_cli(f"KNOWNUSERS {users_str}")

        ## MSG: Textnachricht empfangen & ggf. Auto-Reply senden
        elif cmd == "MSG" and len(parts) == 3:
            sender = parts[1]
            text = parts[2]
            if sender != config["handle"]:
                if os.path.exists(AWAY_FLAG):
                    with open(os.path.join("receive", "offline_messages.txt"), "a", encoding="utf-8") as f:
                        f.write(f"{sender}: {text}\n")
                    if sender not in autoreplied_to:
                        send_msg(sender, config["autoreply"], known_users, config["handle"])
                        autoreplied_to.add(sender)
                else:
                    write_to_cli(f"MSG {sender} {text}")

        ## JOIN: Neuen Nutzer in known_users eintragen
        elif cmd == "JOIN" and len(parts) == 3:
            join_handle = parts[1]
            join_port = int(parts[2])
            if join_handle != config["handle"]:
                known_users[join_handle] = (addr[0], join_port)
                write_to_cli(f"JOIN {join_handle}")

        ## LEAVE: Nutzer austragen
        elif cmd == "LEAVE" and len(parts) == 2:
            leave_handle = parts[1]
            if leave_handle in known_users:
                del known_users[leave_handle]
            write_to_cli(f"LEAVE {leave_handle}")


## @brief Behandelt SIGTERM oder SIGINT um sich sauber abzumelden.
#  Sendet LEAVE und beendet das Programm.
#
#  @param signum Signalnummer.
#  @param frame Aktueller Stackframe.
def handle_sigterm(signum, frame):
    config = get_config()
    send_leave(config["handle"], config["whoisport"])
    sys.exit(0)


## @brief Startpunkt des Netzwerkprozesses.
#
#  Bindet Signale, startet Listener & Pipe-Reader.
def start():
    config = get_config()
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    port = config["port"][0]
    print(f"{YELLOW}[NETWORK] gestartet auf Port {port}{RESET}\n")
    threading.Thread(target=listen_on_port, args=(port, config), daemon=True).start()
    read_cli_pipe(config)


# === Hauptprogramm ===
if __name__ == "__main__":
    if not os.path.exists(PIPE_CLI_TO_NET):
        os.mkfifo(PIPE_CLI_TO_NET)
    if not os.path.exists(PIPE_NET_TO_CLI):
        os.mkfifo(PIPE_NET_TO_CLI)
    start()