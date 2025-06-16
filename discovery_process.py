#!/usr/bin/env python3
import socket
from config_handler import get_config

RESET = "\033[0m"
YELLOW = "\033[93m"

def run_discovery_process(whoisport):
    known_users = {}  # {handle: (ip, port)}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", whoisport))

    print(f"{YELLOW}[DISCOVERY] gestartet auf Port {whoisport}{RESET}\n")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()

        if msg.startswith("JOIN"):
            parts = msg.split()
            if len(parts) == 3:
                handle = parts[1]
                port = int(parts[2])
                ip = addr[0]
                known_users[handle] = (ip, port)

                # 🔁 Sende JOIN an alle anderen
                for h, (ip_other, port_other) in known_users.items():
                    if h != handle:
                        try:
                            join_msg = f"JOIN {handle} {port}"
                            sock.sendto(join_msg.encode("utf-8"), (ip_other, port_other))
                        except Exception:
                            pass  # Fehler ignorieren

        elif msg.startswith("LEAVE"):
            parts = msg.split()
            if len(parts) == 2:
                handle = parts[1]
                known_users.pop(handle, None)

                # 🔁 Sende LEAVE an alle anderen
                for h, (ip_other, port_other) in known_users.items():
                    try:
                        sock.sendto(msg.encode("utf-8"), (ip_other, port_other))
                    except Exception:
                        pass

        elif msg == "WHO":
            sender_ip = addr[0]
            sender_port = None
            for h, (ip, p) in known_users.items():
                if ip == sender_ip:
                    sender_port = p
                    break

            if sender_port:
                user_list = ", ".join(f"{h} {ip} {p}" for h, (ip, p) in known_users.items())
                response = f"KNOWNUSERS {user_list}"
                sock.sendto(response.encode("utf-8"), (sender_ip, sender_port))

if __name__ == "__main__":
    config = get_config()
    run_discovery_process(config["whoisport"])
