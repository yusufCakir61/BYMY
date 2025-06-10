import socket
import threading
import os
import math

# ANSI-Farben für strukturierte Terminalausgabe
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
MAGENTA = "\033[95m"

# \file network_process.py
# \brief Netzwerkfunktionen für Chat Kommunikation über UDP (Text & Bild).

def send_who(whoisport):
    msg = "WHO\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))
    print(f"{CYAN}🔎 WHO-Anfrage gesendet...{RESET}")

def send_join(handle, port, whoisport):
    msg = f"JOIN {handle} {port}\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))
    print(f"{GREEN}📡 JOIN gesendet als '{handle}' auf Port {port}.{RESET}")

def send_msg(to_handle, text, known_users, my_handle):
    if to_handle not in known_users:
        print(f"{RED}⚠️ Nutzer '{to_handle}' nicht gefunden.{RESET}")
        return
    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}\n"
    print(f"{CYAN}✉ Sende Nachricht an {to_handle} @ {ip}:{port}:{RESET}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode("utf-8"), (ip, port))
    print(f"{GREEN}✅ Nachricht gesendet an {to_handle}.{RESET}")

def send_image(to_handle, filepath, data, known_users, my_handle):
    if to_handle not in known_users:
        print(f"{RED}⚠️ Nutzer '{to_handle}' nicht gefunden.{RESET}")
        return
    ip, port = known_users[to_handle]
    filename = os.path.basename(filepath)
    chunk_size = 4000
    num_chunks = math.ceil(len(data) / chunk_size)
    print(f"{CYAN}📤 Sende Bild '{filename}' in {num_chunks} Teilen an {to_handle}...{RESET}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        header = f"IMG_START {my_handle} {filename} {num_chunks}".encode("utf-8")
        sock.sendto(header, (ip, port))
        for i in range(num_chunks):
            chunk_data = data[i * chunk_size:(i + 1) * chunk_size]
            chunk_msg = f"CHUNK {i}".encode("utf-8") + b"||" + chunk_data
            sock.sendto(chunk_msg, (ip, port))
        sock.sendto(b"IMG_END", (ip, port))
    print(f"{GREEN}✅ Bild erfolgreich übertragen.{RESET}")

def listen_on_port(port, known_users, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    incoming_images = {}
    last_away_state = config.get("away", False)
    offline_msg_path = os.path.join("receive", "offline_messages.txt")

    while True:
        try:
            data, addr = sock.recvfrom(65535)
        except OSError:
            print(f"{RED}🛑 Netzwerk-Socket wurde geschlossen.{RESET}")
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
                print(f"\n{YELLOW}📷 Bildstart: '{filename}' von {sender} ({num_chunks} Teile){RESET}")
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
                    print(f"{GREEN}💾 Bild empfangen & gespeichert: {save_path}{RESET}")
                    if "image_events" in config:
                        config["image_events"].append({
                            "from": info["from"],
                            "filename": info["filename"],
                            "path": save_path
                        })
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
            print(f"{MAGENTA}👥 Teilnehmerliste aktualisiert.{RESET}")

        elif msg.startswith("MSG"):
            parts = msg.split(" ", 2)
            if len(parts) == 3:
                _, sender_handle, text = parts

                is_away = config.get("away", False)
                own_handle = config.get("handle")
                is_autoreply_enabled = config.get("autoreply", False)
                is_autoreply_msg = text == config.get("autoreply", "")

                if is_away:
                    print(f"{YELLOW}\n📥 Nachricht gespeichert (Abwesenheitsmodus) von {sender_handle}.{RESET}")
                    os.makedirs("receive", exist_ok=True)
                    with open(offline_msg_path, "a", encoding="utf-8") as f:
                        f.write(f"{sender_handle}: {text}\n")
                else:
                    print(f"\n{BOLD}📨 {sender_handle}: {RESET}{text}")

                if is_away and is_autoreply_enabled and sender_handle != own_handle and not is_autoreply_msg:
                    send_msg(sender_handle, config["autoreply"], known_users, own_handle)
                    print(f"{CYAN}🤖 Auto-Reply an {sender_handle} gesendet.{RESET}")

        current_away_state = config.get("away", False)
        if last_away_state != current_away_state:
            last_away_state = current_away_state
            if current_away_state:
                info_msg = f"INFO {config.get('handle')} ist jetzt abwesend"
                for handle, (ip, port) in known_users.items():
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(info_msg.encode("utf-8"), (ip, port))
                print(f"{YELLOW}📢 Abwesenheitsmodus aktiviert & Info gesendet.{RESET}")
            else:
                if os.path.exists(offline_msg_path):
                    print(f"\n{BOLD}📬 Verpasste Nachrichten während Abwesenheit:{RESET}")
                    with open(offline_msg_path, "r", encoding="utf-8") as f:
                        for line in f:
                            print("   " + line.strip())
                    os.remove(offline_msg_path)

def run_network_process(known_users, config):
    handle = config["handle"]
    port = config["port"][0]
    whoisport = config["whoisport"]
    send_join(handle, port, whoisport)

    t = threading.Thread(target=listen_on_port, args=(port, known_users, config))
    t.daemon = True
    t.start()

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print(f"{RED}🛑 Netzwerkdienst beendet durch Nutzer.{RESET}")
