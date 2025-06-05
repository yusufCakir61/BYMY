import socket
import threading
import os
import math

# \file network_process.py
# \brief Netzwerkfunktionen für Chat-Kommunikation über UDP (Text & Bild).
#
# Dieses Modul implementiert den Sende- und Empfangsmechanismus für:
# - Textnachrichten (MSG)
# - Bilder (IMG_START, CHUNK, IMG_END)
# - Netzwerkabfragen (WHO, JOIN)
# über UDP-Kommunikation.

## \brief Sendet eine WHO-Anfrage via UDP-Broadcast.
## 
## Diese Nachricht wird an alle Clients im lokalen Netzwerk gesendet,
## um eine Liste aktiver Benutzer anzufordern.
## \param whoisport Der UDP-Port, auf dem WHO-Anfragen empfangen werden.
def send_who(whoisport):
    msg = "WHO\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

## \brief Sendet eine JOIN-Nachricht via UDP-Broadcast.
##
## Der eigene Benutzername und Port werden bekanntgegeben, sodass andere Clients
## einen neuen Teilnehmer erkennen und speichern können.
## \param handle Eigenes Handle (Benutzername).
## \param port Eigener Kommunikationsport.
## \param whoisport UDP-Port für Discovery-Prozesse.
def send_join(handle, port, whoisport):
    msg = f"JOIN {handle} {port}\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode("utf-8"), ("255.255.255.255", whoisport))

## \brief Sendet eine Textnachricht an einen bestimmten Benutzer.
##
## Die Nachricht wird direkt an die bekannte IP und den Port des Zielbenutzers gesendet.
## \param to_handle Ziel-Handle (Empfänger).
## \param text Der zu sendende Text.
## \param known_users Dictionary der bekannten Nutzer mit IP & Port.
## \param my_handle Eigenes Handle (Absender).
def send_msg(to_handle, text, known_users, my_handle):
    if to_handle not in known_users:
        print(f"⚠️ Nutzer '{to_handle}' nicht gefunden.")
        return
    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}\n"
    print(f" MSG an {ip}:{port} → {msg.strip()}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode("utf-8"), (ip, port))
    print("✅ Nachricht gesendet.")

## \brief Sendet ein Bild in mehreren Teilen per UDP an einen Benutzer.
##
## Das Bild wird als binäre Daten in maximal 4000-Byte-Chunks gesendet.
## Vorab wird eine IMG_START-Nachricht und nach Abschluss eine IMG_END-Nachricht gesendet.
##
## \param to_handle Empfänger-Handle.
## \param filepath Pfad zur Bilddatei (für den Namen).
## \param data Der Binärinhalt des Bildes.
## \param known_users Bekannte Nutzer mit IP & Port.
## \param my_handle Eigenes Handle (Absender).
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
    print("✅ Bild gesendet.")

## \brief Lauscht auf eingehende Nachrichten und verarbeitet sie.
##
## Diese Funktion wird in einem eigenen Thread gestartet und verarbeitet:
## - Teilnehmerlisten (KNOWNUSERS)
## - Textnachrichten (MSG)
## - Bilddaten (IMG_START, CHUNK, IMG_END)
##
## \param port UDP-Port, auf dem gehört wird.
## \param known_users Geteiltes Dictionary der bekannten Nutzer.
## \param config Konfigurationsobjekt (z. B. Speicherpfad für empfangene Bilder).
def listen_on_port(port, known_users, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    print(f"📡 Warte auf Nachrichten auf Port {port}")
    incoming_images = {}  # Zwischenspeicher für Bildteile

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
                    "from": sender,
                    "filename": filename,
                    "total": num_chunks,
                    "received": 0,
                    "chunks": {}
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
                            "from": info["from"],
                            "filename": info["filename"],
                            "path": save_path
                        })
                    del incoming_images[key]

## \brief Startet den Netzwerkprozess mit JOIN und Empfangs-Thread.
##
## Diese Funktion:
## - sendet zu Beginn eine JOIN-Nachricht
## - startet einen Hintergrundthread für eingehende Nachrichten
##
## \param known_users Gemeinsames Nutzerverzeichnis (Handle → (IP, Port)).
## \param config Konfigurationsdaten inkl. Ports, Handle etc.
def run_network_process(known_users, config):
    handle = config["handle"]
    port = config["port"][0]
    whoisport = config["whoisport"]
    send_join(handle, port, whoisport)

    t = threading.Thread(target=listen_on_port, args=(port, known_users, config))
    t.daemon = True
    t.start()

    try:
        threading.Event().wait()  # Thread am Leben halten
    except KeyboardInterrupt:
        print("🛑 Netzwerkdienst beendet.")
