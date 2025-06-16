import socket
from config_handler import get_config

RESET = "\033[0m"
YELLOW = "\033[93m"

##
# @file discovery_process.py
# @brief Discovery-Modul für den BYMY-CHAT
#
# @details
# Dieses Modul steuert das Finden und Verwalten der aktiven Nutzer:
# 1. Richtet einen UDP-Broadcast-Socket ein.
# 2. Empfängt JOIN-Nachrichten: speichert neue Nutzer und broadcastet sie weiter.
# 3. Empfängt LEAVE-Nachrichten: entfernt Nutzer und broadcastet sie weiter.
# 4. Beantwortet WHO-Anfragen mit der aktuellen Teilnehmerliste.
#

##
# @brief Führt den Discovery-Prozess aus.
# @param whoisport Port für Discovery-Nachrichten (JOIN, LEAVE, WHO)
# @details
# Hauptschleife:
# - Initialisiert den UDP-Socket für Broadcast.
# - Wartet unendlich auf neue Discovery-Nachrichten.
# - Verarbeitet jede Nachricht direkt nach Erhalt.
#
def run_discovery_process(whoisport):
    known_users = {}  ## Speichert bekannte Teilnehmer {handle: (ip, port)}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", whoisport))

    print(f"{YELLOW}[DISCOVERY] gestartet auf Port {whoisport}{RESET}\n")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()

        ##
        # @brief Behandelt JOIN-Nachricht.
        # @details
        # Erkennt 'JOIN <handle> <port>', trägt neuen Nutzer ein
        # und informiert alle anderen bekannten Nutzer über den Neuzugang.
        #
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
                            sock.sendto(f"JOIN {handle} {port}".encode("utf-8"), (ip_other, port_other))
                        except:
                            pass

        ##
        # @brief Behandelt LEAVE-Nachricht.
        # @details
        # Erkennt 'LEAVE <handle>', entfernt Nutzer aus der Liste
        # und informiert alle anderen über das Verlassen.
        #
        elif msg.startswith("LEAVE"):
            parts = msg.split()
            if len(parts) == 2:
                handle = parts[1]
                known_users.pop(handle, None)

                for h, (ip_other, port_other) in known_users.items():
                    try:
                        sock.sendto(msg.encode("utf-8"), (ip_other, port_other))
                    except:
                        pass

        ##
        # @brief Behandelt WHO-Anfrage.
        # @details
        # Erkennt 'WHO', prüft IP in known_users und sendet eine Liste
        # aller bekannten Nutzer zurück mit 'KNOWNUSERS'.
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
# @brief Startet den Discovery-Prozess im Standalone-Betrieb.
# @details
# Liest Konfigurationsdatei und ruft die Hauptschleife auf.
#
if __name__ == "__main__":
    config = get_config()
    run_discovery_process(config["whoisport"])