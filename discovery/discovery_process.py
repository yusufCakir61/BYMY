## @file network_process.py
## @brief Behandelt Netzwerkkommunikation (JOIN, WHO, MSG) im Chat

import socket

def run_discovery_process(whoisport):
    known_users = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", whoisport))
    print(f" Discovery läuft auf Port {whoisport}")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()

        if msg.startswith("JOIN"):
            parts = msg.split()
            if len(parts) == 3:
                handle = parts[1]
                port = int(parts[2])
                ip = addr[0]
                if not any(u for u in known_users if u[0] == handle):
                    known_users.append((handle, ip, port))
                    print(f"➕ Neuer Teilnehmer: {handle} @ {ip}:{port}")

        elif msg.startswith("WHO"):
            sender_ip = addr[0]
            target_port = next((p for h, ip, p in known_users if ip == sender_ip), None)
            if target_port is None:
                continue
            response = "KNOWNUSERS " + ", ".join([f"{h} {ip} {p}" for h, ip, p in known_users]) + "\n"
            sock.sendto(response.encode("utf-8"), (sender_ip, target_port))
            print(f"➡️ KNOWNUSERS gesendet an {sender_ip}:{target_port}")
