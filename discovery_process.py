import socket
from config_handler import get_config

# Farbdefinitionen für CLI-Ausgaben
RESET = "\033[0m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
YELLOW = "\033[93m"

def run_discovery_process(whoisport):
    known_users = {}  # {handle: (ip, port)}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", whoisport))

    print(f"{YELLOW}[DISCOVERY] gestartet auf Port {whoisport}{RESET}")
    print("")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()

        if msg.startswith("JOIN"):
            parts = msg.split()
            if len(parts) == 3:
                handle = parts[1]
                port = int(parts[2])
                ip = addr[0]
                current_entry = (ip, port)

                # Nur ausgeben, wenn neu
                if known_users.get(handle) != current_entry:
                    known_users[handle] = current_entry
                    print(f"{GREEN}[DISCOVERY] JOIN von {handle} @ {ip}:{port}{RESET}")

        elif msg == "WHO":
            sender_ip = addr[0]
            sender_port = None

            for h, (ip, port) in known_users.items():
                if ip == sender_ip:
                    sender_port = port
                    break

            if sender_port:
                user_list = ", ".join(f"{h} {ip} {p}" for h, (ip, p) in known_users.items())
                response = f"KNOWNUSERS {user_list}"
                sock.sendto(response.encode("utf-8"), (sender_ip, sender_port))
                # print(f"{BLUE}[DISCOVERY] KNOWNUSERS gesendet an {sender_ip}:{sender_port}{RESET}")

if __name__ == "__main__":
    config = get_config()
    run_discovery_process(config["whoisport"])
