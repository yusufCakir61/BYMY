import socket
import threading
import os
import math
import sys
import json
import signal
import subprocess
from config_handler import get_config

RESET  = "\033[0m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
GREEN  = "\033[92m"

AWAY_FLAG = "away.flag"
os.makedirs("receive", exist_ok=True)
autoreplied_to = set()

def safe_print_from_thread(text):
    sys.stdout.write("\r\033[K")
    print(text)
    sys.stdout.write("> ")
    sys.stdout.flush()

def save_known_users(known_users):
    try:
        with open("known_users.json", "w") as f:
            json.dump(known_users, f)
    except Exception as e:
        print(f"{RED}[FEHLER] Speichern von known_users fehlgeschlagen: {e}{RESET}")

def send_who(whoisport):
    msg = "WHO\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

def send_join(handle, port, whoisport):
    msg = f"JOIN {handle} {port}\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

def send_leave(handle, whoisport):
    msg = f"LEAVE {handle}\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

def send_msg(to_handle, text, known_users, my_handle):
    if to_handle not in known_users:
        return
    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode("utf-8"), (ip, port))

def send_image(to_handle, filepath, data, known_users, my_handle):
    if to_handle not in known_users:
        return
    ip, port = known_users[to_handle]
    filename = os.path.basename(filepath)
    chunk_size = 4000
    num_chunks = math.ceil(len(data) / chunk_size)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        header = f"IMG_START {my_handle} {filename} {num_chunks}".encode("utf-8")
        sock.sendto(header, (ip, port))
        for i in range(num_chunks):
            chunk_data = data[i * chunk_size:(i + 1) * chunk_size]
            chunk_msg = f"CHUNK {i}".encode("utf-8") + b"||" + chunk_data
            sock.sendto(chunk_msg, (ip, port))
        sock.sendto(b"IMG_END", (ip, port))

def listen_on_port(port, known_users, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    incoming_images = {}
    offline_msg_path = os.path.join("receive", "offline_messages.txt")

    while True:
        try:
            data, addr = sock.recvfrom(65535)
        except OSError:
            break

        if data.startswith(b"IMG_START"):
            msg = data.decode("utf-8", errors="ignore").strip()
            parts = msg.split(" ", 3)
            if len(parts) == 4:
                _, sender, filename, num_chunks_str = parts
                num_chunks = int(num_chunks_str)
                key = (addr, filename)
                incoming_images[key] = {
                    "from": sender,
                    "filename": filename,
                    "total": num_chunks,
                    "received": 0,
                    "chunks": {}
                }
            continue

        elif data.startswith(b"CHUNK"):
            try:
                header, chunk_data = data.split(b'||', 1)
                _, chunk_num_str = header.decode("utf-8").split(" ")
                chunk_num = int(chunk_num_str)
                for key in incoming_images:
                    if key[0] == addr:
                        incoming_images[key]["chunks"][chunk_num] = chunk_data
                        incoming_images[key]["received"] += 1
                        break
            except Exception:
                pass
            continue

        elif data.startswith(b"IMG_END"):
            for key, info in list(incoming_images.items()):
                if info["received"] == info["total"]:
                    ordered_data = b''.join(info["chunks"][i] for i in range(info["total"]))
                    image_dir = config.get("imagepath", "receive/")
                    os.makedirs(image_dir, exist_ok=True)
                    save_path = os.path.join(image_dir, info["filename"])
                    with open(save_path, "wb") as f:
                        f.write(ordered_data)
                    safe_print_from_thread(f"{CYAN}[{info['from']}] Bild empfangen: {info['filename']}{RESET}")
                    try:
                        if os.name == "posix":
                            subprocess.run(["xdg-open", save_path], check=False)
                        elif os.name == "nt":
                            os.startfile(save_path)
                        elif sys.platform == "darwin":
                            subprocess.run(["open", save_path], check=False)
                    except Exception as e:
                        safe_print_from_thread(f"{RED}Bildanzeige fehlgeschlagen: {e}{RESET}")
                    del incoming_images[key]
            continue

        msg = data.decode("utf-8", errors="ignore").strip()

        if msg.startswith("KNOWNUSERS"):
            users = msg[len("KNOWNUSERS "):].split(", ")
            for user in users:
                parts = user.split()
                if len(parts) == 3:
                    handle, ip, port_str = parts
                    known_users[handle] = (ip, int(port_str))
            save_known_users(known_users)
            # safe_print_from_thread(f"{GREEN}[DISCOVERY] Benutzerliste aktualisiert ({len(known_users)} Einträge){RESET}")
            continue

        elif msg.startswith("MSG"):
            parts = msg.split(" ", 2)
            if len(parts) == 3:
                _, sender_handle, text = parts
                own_handle = config.get("handle")
                is_autoreply_enabled = config.get("autoreply", False)
                is_autoreply_msg = text == config.get("autoreply", "")
                if sender_handle == own_handle:
                    continue

                is_away = os.path.exists(AWAY_FLAG)
                if is_away:
                    with open(offline_msg_path, "a", encoding="utf-8") as f:
                        f.write(f"{sender_handle}: {text}\n")
                else:
                    safe_print_from_thread(f"{BLUE}[{sender_handle}]{RESET} {text}")

                if is_away and is_autoreply_enabled and not is_autoreply_msg and sender_handle not in autoreplied_to:
                    send_msg(sender_handle, config["autoreply"], known_users, own_handle)
                    autoreplied_to.add(sender_handle)

def handle_sigterm(signum, frame):
    config = get_config()
    handle = config.get("handle")
    whoisport = config.get("whoisport")
    send_leave(handle, whoisport)
   #  print(f"{RED}[NETWORK] LEAVE-Nachricht gesendet. Beende...{RESET}")
    sys.exit(0)

def run_network_process(known_users, config):
    handle = config["handle"]
    port = config["port"][0]
    whoisport = config["whoisport"]
    send_join(handle, port, whoisport)
    print(f"{YELLOW}[NETWORK] gestartet auf Port {port}{RESET}")
    t = threading.Thread(target=listen_on_port, args=(port, known_users, config))
    t.daemon = True
    t.start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass

def start(known_users):
    config = get_config()
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    run_network_process(known_users, config)

if __name__ == "__main__":
    start({})
