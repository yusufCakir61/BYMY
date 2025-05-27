import socket
import threading
from config.config_handler import load_config

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
        print(f"⚠️ Nutzer '{to_handle}' nicht gefunden.")
        return

    ip, port = known_users[to_handle]
    msg = f"MSG {my_handle} {text}\n"  # richtiger Absender statt Empfänger
    print(f" MSG an {ip}:{port} → {msg.strip()}")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg.encode("utf-8"), (ip, port))
    print("✅ Nachricht gesendet.")


def listen_on_port(port, known_users):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    print(f" Warte auf Nachrichten auf Port {port}")
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()
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

def run_network_process(known_users):
    config = load_config()
    handle = config["handle"]
    port = config["port"][0]
    whoisport = config["whoisport"]

    send_join(handle, port, whoisport)

    t = threading.Thread(target=listen_on_port, args=(port, known_users))
    t.daemon = True
    t.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("🛑 Netzwerkdienst beendet.")
