import socket
import threading
import os
import math

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

def send_msg(to_handle, text, known_users, my_handle):
    if to_handle not in known_users:
        print(f"⚠️ Nutzer '{to_handle}' nicht gefunden, warte bis Nutzer Online ist!")
        return
    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}\n"
    print(f" MSG an {ip}:{port} → {msg.strip()}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode("utf-8"), (ip, port))
    print("✅ Nachricht gesendet.")

def send_image(to_handle, filepath, data, known_users, my_handle):
    if to_handle not in known_users:
        print(f"⚠️ Nutzer '{to_handle}' nicht gefunden.")
        return
    ip, port = known_users[to_handle]
    filename = os.path.basename(filepath)
    chunk_size = 4000
    num_chunks = math.ceil(len(data) / chunk_size)
    print(f"📤 Sende Bild '{filename}' in {num_chunks} Teilen an {ip}:{port}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        header = f"IMG_START {my_handle} {filename} {num_chunks}".encode("utf-8")
        sock.sendto(header, (ip, port))
        for i in range(num_chunks):
            chunk_data = data[i * chunk_size:(i + 1) * chunk_size]
            chunk_msg = f"CHUNK {i}".encode("utf-8") + b"||" + chunk_data
            sock.sendto(chunk_msg, (ip, port))
        sock.sendto(b"IMG_END", (ip, port))
    print("✅ Bild gesendet ;)!.")

def listen_on_port(port, known_users, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    print(f"📡 Warte auf Nachrichten auf Port {port}")
    incoming_images = {}
    while True:
        data, addr = sock.recvfrom(65535)
        msg = data.decode("utf-8", errors="ignore").strip()
        if msg.startswith("KNOWNUSERS"):
            users = msg[len("KNOWNUSERS "):].split(", ")
            for user in users:
                parts = user.split()
                if len(parts) == 3:
                    handle, ip, port_str = parts
                    known_users[handle] = (ip, int(port_str))
            print("👥 Teilnehmerliste aktualisiert.")
        elif msg.startswith("MSG"):
            parts = msg.split(" ", 2)
            if len(parts) == 3:
                _, handle, text = parts
                print(f"\n📨 Neue Nachricht von {handle}: {text}")
        elif msg.startswith("IMG_START"):
            parts = msg.split(" ", 3)
            if len(parts) == 4:
                _, sender, filename, num_chunks_str = parts
                num_chunks = int(num_chunks_str)
                key = (addr, filename)
                incoming_images[key] = {
                    "from": sender, "filename": filename, "total": num_chunks,
                    "received": 0, "chunks": {}
                }
                print(f"\n📷 Bildstart: {filename} von {sender} (Teile: {num_chunks})")
        elif msg.startswith("CHUNK"):
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
        elif msg.startswith("IMG_END"):
            for key, info in list(incoming_images.items()):
                if info["received"] == info["total"]:
                    ordered_data = b''.join(info["chunks"][i] for i in range(info["total"]))
                    image_dir = config.get("imagepath", "receive/")
                    os.makedirs(image_dir, exist_ok=True)
                    save_path = os.path.join(image_dir, info["filename"])
                    with open(save_path, "wb") as f:
                        f.write(ordered_data)
                    print(f"💾 Bild empfangen & gespeichert: {save_path}")
                    if "image_events" in config:
                        config["image_events"].append({
                            "from": info["from"], "filename": info["filename"], "path": save_path
                        })
                    del incoming_images[key]

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
        print("🛑 Netzwerkdienst beendet. Bye")

