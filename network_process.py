import os
import socket
import threading
import signal
import sys
from config_handler import get_config

RESET  = "\033[0m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
GREEN = "\033[92m"

PIPE_CLI_TO_NET = "cli_to_network.pipe"
PIPE_NET_TO_CLI = "network_to_cli.pipe"
AWAY_FLAG = "away.flag"
autoreplied_to = set()
known_users = {}

def write_to_cli(msg):
    try:
        with open(PIPE_NET_TO_CLI, "w") as pipe:
            pipe.write(msg + "\n")
    except Exception as e:
        print(f"{RED}Fehler beim Schreiben in CLI-Pipe: {e}{RESET}")

def send_who(whoisport):
    msg = "WHO"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ('255.255.255.255', whoisport))

def send_join(handle, port, whoisport):
    msg = f"JOIN {handle} {port}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ('255.255.255.255', whoisport))

def send_leave(handle, whoisport):
    msg = f"LEAVE {handle}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ('255.255.255.255', whoisport))

def send_msg(to_handle, text, known_users, my_handle):
    if to_handle not in known_users:
        print(f"{RED}Empfänger {to_handle} nicht bekannt{RESET}")
        return
    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode("utf-8"), (ip, port))

def send_image(to_handle, filepath, filesize, known_users, config):
    if to_handle not in known_users:
        print(f"{RED}Empfänger {to_handle} nicht bekannt{RESET}")
        return
    ip, port = known_users[to_handle]
    chunk_size = 1024
    total_chunks = (filesize + chunk_size - 1) // chunk_size

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock, open(filepath, "rb") as f:
            start_msg = f"IMG_START {config['handle']} {os.path.basename(filepath)} {total_chunks}"
            sock.sendto(start_msg.encode(), (ip, port))

            for i in range(total_chunks):
                chunk_data = f.read(chunk_size)
                chunk_msg = f"CHUNK {i}".encode() + b'||' + chunk_data
                sock.sendto(chunk_msg, (ip, port))

            sock.sendto(b"IMG_END", (ip, port))
    except Exception as e:
        print(f"{RED}Fehler beim Bildversand: {e}{RESET}")

def read_cli_pipe(config):
    while True:
        with open(PIPE_CLI_TO_NET, "r") as pipe:
            for line in pipe:
                parts = line.strip().split(" ", 2)  # <--- maxsplit=2 wichtig!
                if not parts:
                    continue
                cmd = parts[0]

                if cmd == "SEND_MSG" and len(parts) == 3:
                    to, msg = parts[1], parts[2]
                    send_msg(to, msg, known_users, config["handle"])

                elif cmd == "SEND_IMAGE" and len(parts) == 4:
                    # Falls hier 4 Teile erwartet werden: 
                    # evtl. in CLI aufteilen anpassen, hier maxsplit=3
                    to, filepath, filesize_str = parts[1], parts[2], parts[3] if len(parts) > 3 else '0'
                    try:
                        filesize = int(filesize_str)
                    except:
                        filesize = 0
                    send_image(to, filepath, filesize, known_users, config)

                elif cmd == "WHO":
                    send_who(config["whoisport"])

                elif cmd == "JOIN" and len(parts) == 3:
                    _, handle, port = parts
                    send_join(handle, int(port), config["whoisport"])

                elif cmd == "LEAVE" and len(parts) == 2:
                    send_leave(parts[1], config["whoisport"])

def listen_on_port(port, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    image_dir = config.get("imagepath", "receive/")
    os.makedirs(image_dir, exist_ok=True)
    incoming_images = {}

    while True:
        try:
            data, addr = sock.recvfrom(65535)
        except OSError as e:
            print(f"{RED}Socket Error: {e}{RESET}")
            break

        if data.startswith(b"IMG_START"):
            try:
                parts = data.decode().strip().split(" ", 3)
                if len(parts) == 4:
                    _, sender, filename, num_chunks_str = parts
                    num_chunks = int(num_chunks_str)
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

        msg = data.decode("utf-8", errors="ignore").strip()
        parts = msg.split(" ", 2)  # maxsplit=2 hier auch!

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

        elif cmd == "JOIN" and len(parts) == 3:
            join_handle = parts[1]
            join_port = int(parts[2])
            if join_handle != config["handle"]:
                known_users[join_handle] = (addr[0], join_port)
                write_to_cli(f"JOIN {join_handle}")

        elif cmd == "LEAVE" and len(parts) == 2:
            leave_handle = parts[1]
            if leave_handle in known_users:
                del known_users[leave_handle]
            write_to_cli(f"LEAVE {leave_handle}")

def handle_sigterm(signum, frame):
    config = get_config()
    send_leave(config["handle"], config["whoisport"])
    sys.exit(0)

def start():
    config = get_config()
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    port = config["port"][0]
    print(f"{YELLOW}[NETWORK] gestartet auf Port {port}{RESET}\n")
    threading.Thread(target=listen_on_port, args=(port, config), daemon=True).start()
    read_cli_pipe(config)

if __name__ == "__main__":
    if not os.path.exists(PIPE_CLI_TO_NET):
        os.mkfifo(PIPE_CLI_TO_NET)
    if not os.path.exists(PIPE_NET_TO_CLI):
        os.mkfifo(PIPE_NET_TO_CLI)
    start()
