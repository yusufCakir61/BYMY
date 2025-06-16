import socket
from config_handler import get_config

RESET = "\033[0m"
YELLOW = "\033[93m"

##
# @file discovery_process.py
# @brief Discovery-Mechanismus für BYMY-CHAT via UDP Broadcast
#
# @details
# Dieses Modul steuert:
#   1) Empfang von JOIN-Nachrichten (Teilnehmer tritt bei)
#   2) Verarbeitung von LEAVE-Nachrichten (Teilnehmer verlässt)
#   3) Beantwortung von WHO-Nachrichten (Liste aller bekannten)
#   4) Synchronisierung aller bekannten Nutzer
#
# Ablauf:
#   - UDP-Socket einrichten.
#   - Unendlich Loop: Nachrichten empfangen & verarbeiten.
#   - JOIN → Nutzer speichern & broadcasten.
#   - LEAVE → Nutzer entfernen.
#   - WHO → bekannte Nutzerliste senden.
#

##
# @brief Startet den Discovery-Loop.
# @param whoisport UDP-Port für Broadcasts.
# @details
# Ablauf:
#   1) Leeres Dictionary für bekannte Nutzer erstellen.
#   2) UDP-Socket konfigurieren.
#   3) Endlosschleife:
#       a) JOIN empfangen & weiterleiten.
#       b) LEAVE empfangen & entfernen.
#       c) WHO empfangen & beantworten.
#
def run_discovery_process(whoisport):
    known_users = {}  # Format: {handle: (ip, port)}

    # 1️⃣ Socket einrichten
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", whoisport))

    print(f"{YELLOW}[DISCOVERY] gestartet auf Port {whoisport}{RESET}\n")

    # 2️⃣ Haupt-Loop
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()

        ##
        # 2.a) JOIN-Nachricht
        # Ablauf:
        #   - JOIN <handle> <port> verarbeiten.
        #   - Nutzer in known_users speichern.
        #   - JOIN an alle anderen weiterleiten.
        #
        if msg.startswith("JOIN"):
            parts = msg.split()
            if len(parts) == 3:
                handle = parts[1]
                port = int(parts[2])
                ip = addr[0]

                # Nutzer merken
                known_users[handle] = (ip, port)

                # JOIN weiterleiten
                for h, (ip_other, port_other) in known_users.items():
                    if h != handle:
                        try:
                            join_msg = f"JOIN {handle} {port}"
                            sock.sendto(join_msg.encode("utf-8"), (ip_other, port_other))
                        except Exception:
                            pass

        ##
        # 2.b) LEAVE-Nachricht
        # Ablauf:
        #   - LEAVE <handle> erkennen.
        #   - Nutzer aus known_users löschen.
        #
        elif msg.startswith("LEAVE"):
            parts = msg.split()
            if len(parts) == 2:
                handle = parts[1]
                known_users.pop(handle, None)

        ##
        # 2.c) WHO-Nachricht
        # Ablauf:
        #   - WHO prüfen.
        #   - Absender-IP in known_users suchen.
        #   - Wenn gefunden: KNOWNUSERS <Liste> zurücksenden.
        #
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

##
# @brief Einstiegspunkt für Standalone-Nutzung
# @details Holt Config & startet den Discovery-Prozess.
#
if __name__ == "__main__":
    config = get_config()
    run_discovery_process(config["whoisport"])