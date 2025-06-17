#!/usr/bin/env python3

import socket
from config_handler import get_config

## @file discovery_process.py
#  @brief Discovery-Modul für BYMY Chat (UDP-Broadcast-Discovery nach SLCP-Art)
#  @details
#  Ablauf & Zweck:
#  1) Öffnet einen UDP-Socket am WHOIS-Port für Discovery.
#  2) Wartet endlos auf JOIN, LEAVE oder WHO Nachrichten.
#  3) JOIN: Speichert neuen Nutzer, broadcastet an bekannte.
#  4) LEAVE: Entfernt Nutzer, broadcastet Austritt an bekannte.
#  5) WHO: Antwortet mit allen bekannten Nutzern, wenn Absender bekannt ist.
#  
#  Damit stellt das Modul sicher, dass jeder Client dynamisch andere Clients im LAN finden kann,
#  ohne zentralen Server.

RESET = "\033[0m"
YELLOW = "\033[93m"

##
# @brief Discovery-Hauptprozess: Verwaltet Teilnehmerliste und antwortet auf Anfragen.
# @param whoisport UDP-Port für WHO/JOIN/LEAVE-Kommunikation.
def run_discovery_process(whoisport):
    known_users = {}  # {handle: (ip, port)}

    # 1) UDP-Socket vorbereiten & binden
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", whoisport))

    print(f"{YELLOW}[DISCOVERY] gestartet auf Port {whoisport}{RESET}\n")

    # 2) Endlosschleife für eingehende Nachrichten
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()

        ## 3) JOIN verarbeiten:
        # - JOIN <handle> <port>
        # - speichere Absender & broadcaste an andere bekannte Nutzer.
        if msg.startswith("JOIN"):
            parts = msg.split()
            if len(parts) == 3:
                handle = parts[1]
                port = int(parts[2])
                ip = addr[0]
                known_users[handle] = (ip, port)

                for h, (ip_other, port_other) in known_users.items():
                    if h != handle:
                        try:
                            join_msg = f"JOIN {handle} {port}"
                            sock.sendto(join_msg.encode("utf-8"), (ip_other, port_other))
                        except Exception:
                            pass  # Ignoriere Fehler beim Weiterleiten

        ## 4) LEAVE verarbeiten:
        # - LEAVE <handle>
        # - entferne aus Liste & broadcaste LEAVE an andere bekannte.
        elif msg.startswith("LEAVE"):
            parts = msg.split()
            if len(parts) == 2:
                handle = parts[1]
                known_users.pop(handle, None)

                for h, (ip_other, port_other) in known_users.items():
                    try:
                        sock.sendto(msg.encode("utf-8"), (ip_other, port_other))
                    except Exception:
                        pass

        ## 5) WHO beantworten:
        # - Nur wenn Absender-IP schon in known_users.
        # - Sende KNOWNUSERS <handle1 ip1 port1>, ...
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


## @brief Standalone-Startpunkt: Liest Konfig & ruft Hauptprozess auf.
if __name__ == "__main__":
    config = get_config()
    run_discovery_process(config["whoisport"])