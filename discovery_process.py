import socket
from config_handler import get_config

RESET = "\033[0m"
YELLOW = "\033[93m"

##
# @file discovery_process.py
# @brief Verwaltet Discovery-Logik für BYMY Chat via UDP-Broadcast
# @details
# Dieses Modul implementiert Discovery-Funktionalität nach dem SLCP-Protokoll:
# 1. Empfang von JOIN-Nachrichten (Eintritt eines Nutzers)
# 2. Empfang von LEAVE-Nachrichten (Verlassen eines Nutzers)
# 3. Empfang und Beantwortung von WHO-Anfragen (Teilnehmerliste)
# 4. Verwaltung der bekannten Nutzer während der Laufzeit
#

##
# @brief Hauptfunktion für den Discovery-Prozess (Endlosschleife)
# @param whoisport Port für Discovery-Kommunikation (z. B. 4000)
# @note Diese Funktion blockiert dauerhaft. Wird direkt vom Discovery-Prozess gestartet.
#
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

        ##
        # @section JOIN Verarbeitung von Beitrittsnachrichten
        # @details
        # JOIN <handle> <port> wird empfangen, IP stammt aus Absenderadresse.
        # Nutzer wird zur bekannten Liste hinzugefügt und der JOIN wird
        # an alle anderen bekannten Nutzer weitergeleitet.
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
                            join_msg = f"JOIN {handle} {port}"
                            sock.sendto(join_msg.encode("utf-8"), (ip_other, port_other))
                        except Exception:
                            pass

        ##
        # @section LEAVE Verarbeitung von Austrittsnachrichten
        # @details
        # LEAVE <handle> entfernt den Nutzer aus der Liste der bekannten Teilnehmer.
        #
        elif msg.startswith("LEAVE"):
            parts = msg.split()
            if len(parts) == 2:
                handle = parts[1]
                known_users.pop(handle, None)

        ##
        # @section WHO Verarbeitung von Teilnehmerabfragen
        # @details
        # WHO wird beantwortet mit KNOWNUSERS <handle1 ip1 port1>, ...
        # Nur wenn Absender-IP bereits in known_users vorhanden ist.
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
# @brief Startpunkt für Standalone-Discovery-Prozess
# @details Holt Konfiguration und startet Discovery-Schleife.
#
if __name__ == "__main__":
    config = get_config()
    run_discovery_process(config["whoisport"])