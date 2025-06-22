#!/usr/bin/env python3

## @file network_process.py
#  @brief BYMY Netzwerkprozess für Nachrichten- und Bildübertragung
#  @details
#  Struktur & Ablauf:
#   1) Farben & Pipes
#   2) write_to_cli – Nachricht an CLI zurückschreiben
#   3) send_who – WHO an Broadcast
#   4) send_join – JOIN an Broadcast
#   5) send_leave – LEAVE an Broadcast
#   6) send_msg – Textnachricht an User
#   7) send_image – Bild über TCP senden
#   8) tcp_image_receiver – TCP-Server für Bilder
#   9) handle_tcp_connection – TCP-Bild speichern
#  10) read_cli_pipe – CLI-Kommandos lesen
#  11) listen_on_port – UDP-Nachrichten empfangen
#  12) handle_sigterm – Sauberer Shutdown
#  13) start() – Startet alles

import os, socket, threading, signal, sys
from config_handler import get_config

## 1) Farben & Pipes
RESET = "\033[0m"; BLUE = "\033[94m"; CYAN = "\033[96m"
YELLOW = "\033[93m"; RED = "\033[91m"; GREEN = "\033[92m"
PIPE_CLI_TO_NET = "cli_to_network.pipe"
PIPE_NET_TO_CLI = "network_to_cli.pipe"
AWAY_FLAG = "away.flag"
autoreplied_to = set()
known_users = {}

## 2) Nachricht in CLI-Pipe schreiben.
#  @param msg Die Nachricht
def write_to_cli(msg):
    try:
        with open(PIPE_NET_TO_CLI, "w") as pipe:
            pipe.write(msg + "\n")
    except Exception as e:
        print(f"{RED}Fehler beim Schreiben in CLI-Pipe: {e}{RESET}")

## 3) Sende WHO Broadcast.
#  @param whoisport Discovery-Port.
def send_who(whoisport):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(b"WHO", ('255.255.255.255', whoisport))

## 4) Sende JOIN Broadcast.
#  @param handle Eigenes Handle.
#  @param port Eigener UDP-Port.
#  @param whoisport Discovery-Port.
def send_join(handle, port, whoisport):
    msg = f"JOIN {handle} {port}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode(), ('255.255.255.255', whoisport))

## 5) Sende LEAVE Broadcast.
#  @param handle Eigenes Handle.
#  @param whoisport Discovery-Port.
def send_leave(handle, whoisport):
    msg = f"LEAVE {handle}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode(), ('255.255.255.255', whoisport))
        sock.sendto(msg.encode(), ('127.0.0.1', whoisport))

## 6) Sende Textnachricht.
#  @param to_handle Empfänger.
#  @param text Nachricht.
#  @param known_users Bekannte Nutzer.
#  @param my_handle Eigener Name.
def send_msg(to_handle, text, known_users, my_handle):
    if to_handle not in known_users:
        print(f"{RED}Empfänger {to_handle} nicht bekannt{RESET}")
        return
    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode(), (ip, port))

## 7) Sende Bild über TCP.
#  @param to_handle Empfänger.
#  @param filepath Datei.
#  @param filesize Größe.
#  @param known_users Bekannte Nutzer.
#  @param config Config.
def send_image(to_handle, filepath, filesize, known_users, config):
    if to_handle not in known_users:
        print(f"{RED}Empfänger {to_handle} nicht bekannt{RESET}")
        return
    ip, port = known_users[to_handle]
    tcp_port = port + 1
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, tcp_port))
            filename = os.path.basename(filepath)
            header = f"IMG {config['handle']} {filename} {filesize}\n".encode()
            sock.sendall(header)
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk: break
                    sock.sendall(chunk)
    except Exception as e:
        print(f"{RED}Fehler beim Bildversand (TCP): {e}{RESET}")

## 8) TCP-Server für Bilder.
#  @param port UDP-Port.
#  @param config Config.
def tcp_image_receiver(port, config):
    image_dir = config.get("imagepath", "receive")
    os.makedirs(image_dir, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", port + 1))
        server.listen()
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_tcp_connection, args=(conn, addr, image_dir), daemon=True).start()

## 9) Speichert empfangenes TCP-Bild.
#  @param conn TCP-Verbindung.
#  @param addr Absenderadresse.
#  @param image_dir Zielordner.
def handle_tcp_connection(conn, addr, image_dir):
    try:
        header = b''
        while not header.endswith(b'\n'):
            data = conn.recv(1)
            if not data: break
            header += data
        if not header.startswith(b"IMG"): return
        _, sender, filename, size_str = header.decode().strip().split()
        size = int(size_str)
        remaining = size
        chunks = []
        while remaining > 0:
            chunk = conn.recv(min(4096, remaining))
            if not chunk: break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining == 0:
            save_path = os.path.join(image_dir, filename)
            with open(save_path, "wb") as f:
                for c in chunks:
                    f.write(c)
            write_to_cli(f"IMG {sender} {filename}")
    except Exception as e:
        print(f"{RED}[TCP] Fehler bei Bildempfang: {e}{RESET}")
    finally:
        conn.close()

## 10) Liest CLI-Kommandos.
#  @param config Globale Config.
def read_cli_pipe(config):
    while True:
        with open(PIPE_CLI_TO_NET, "r") as pipe:
            for line in pipe:
                parts = line.strip().split(" ", 3)
                if not parts:
                    continue
                cmd = parts[0]
                if cmd == "SEND_MSG" and len(parts) >= 3:
                    to = parts[1]
                    msg = line.strip().split(" ", 2)[2]
                    send_msg(to, msg, known_users, config["handle"])
                elif cmd == "SEND_IMAGE" and len(parts) == 4:
                    to, filepath, filesize_str = parts[1], parts[2], parts[3]
                    try:
                        filesize = int(filesize_str)
                    except ValueError:
                        filesize = os.path.getsize(filepath)
                    send_image(to, filepath, filesize, known_users, config)
                elif cmd == "WHO":
                    send_who(config["whoisport"])
                elif cmd == "JOIN" and len(parts) == 3:
                    _, handle, port = parts
                    send_join(handle, int(port), config["whoisport"])
                elif cmd == "LEAVE" and len(parts) == 2:
                    handle = parts[1]
                    send_leave(handle, config["whoisport"])
                    write_to_cli(f"LEAVE_ACK {handle}")

## 11) Lauscht auf Port & verarbeitet.
#  @param port UDP-Port.
#  @param config Config.
def listen_on_port(port, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    while True:
        try:
            data, addr = sock.recvfrom(65535)
        except OSError as e:
            print(f"{RED}Socket Error: {e}{RESET}")
            break
        msg = data.decode("utf-8", errors="ignore").strip()
        parts = msg.split(" ", 2)
        if not parts:
            continue
        cmd = parts[0]
        if cmd == "KNOWNUSERS":
            entries = msg[len("KNOWNUSERS "):].split(", ")
            for entry in entries:
                p = entry.split()
                if len(p) == 3:
                    h, ip, port_str = p
                    known_users[h] = (ip, int(port_str))
            users_str = ", ".join(f"{h} {ip} {p}" for h, (ip, p) in known_users.items())
            write_to_cli(f"KNOWNUSERS {users_str}")
        elif cmd == "MSG" and len(parts) == 3:
            sender, text = parts[1], parts[2]
            if sender != config["handle"]:
                if os.path.exists(AWAY_FLAG):
                    with open(os.path.join("receive", "offline_messages.txt"), "a", encoding="utf-8") as f:
                        f.write(f"{sender}: {text}\n")
                    if sender not in autoreplied_to:
                        send_msg(sender, config["autoreply"], known_users, config["handle"])
                        autoreplied_to.add(sender)
                else:
                    write_to_cli(f"MSG {sender} {text}")
        elif cmd == "JOIN" and len(parts) == 3:
            join_handle, join_port = parts[1], int(parts[2])
            if join_handle != config["handle"]:
                known_users[join_handle] = (addr[0], join_port)
                write_to_cli(f"JOIN {join_handle}")
        elif cmd == "LEAVE" and len(parts) == 2:
            leave_handle = parts[1]
            if leave_handle == config["handle"]:
                continue
            if leave_handle in known_users:
                del known_users[leave_handle]
            write_to_cli(f"LEAVE {leave_handle}")

## 12) SIGTERM-Handler.
#  @param signum Signal.
#  @param frame Frame.
def handle_sigterm(signum, frame):
    config = get_config()
    send_leave(config["handle"], config["whoisport"])
    sys.exit(0)

## 13) Startet alle Threads & Bindings.
if __name__ == "__main__":
    if not os.path.exists(PIPE_CLI_TO_NET): os.mkfifo(PIPE_CLI_TO_NET)
    if not os.path.exists(PIPE_NET_TO_CLI): os.mkfifo(PIPE_NET_TO_CLI)
    config = get_config()
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    port = config["port"][0]
    print(f"{YELLOW}[NETWORK] gestartet auf Port {port}{RESET}\n")
    threading.Thread(target=tcp_image_receiver, args=(port, config), daemon=True).start()
    threading.Thread(target=listen_on_port, args=(port, config), daemon=True).start()
    read_cli_pipe(config)