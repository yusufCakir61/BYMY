import socket

# \file discovery_process.py
# \brief Discovery-Modul zum Erkennen und Antworten auf WHO- und JOIN-Anfragen.
#
# Diese Datei verarbeitet Netzwerkbroadcasts von Chat-Teilnehmern.
# Neue Teilnehmer senden "JOIN", und wer andere sucht, sendet "WHO".

## \brief Startet den Discovery-Prozess für den Chat.
##
## Diese Funktion hört auf einem bestimmten UDP-Port auf eingehende
## JOIN- und WHO-Nachrichten. Bei JOIN werden neue Teilnehmer
## gespeichert, bei WHO wird eine Liste aller bekannten Benutzer
## an den Anfragenden zurückgesendet.
##
## \param whoisport UDP-Port, auf dem Discovery-Nachrichten empfangen werden.
def run_discovery_process(whoisport):
    known_users = []  # Liste bekannter Teilnehmer: (handle, IP, port)

    # UDP-Socket erstellen
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", whoisport))

    print("")
    print("")
    print(f"❗️ Discovery läuft auf Port {whoisport}")

    # Endlosschleife zur Verarbeitung eingehender Nachrichten
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()

        # JOIN <handle> <port> → Teilnehmer hinzufügen
        if msg.startswith("JOIN"):
            parts = msg.split()
            if len(parts) == 3:
                handle = parts[1]
                port = int(parts[2])
                ip = addr[0]

                # Handle nur einmal registrieren
                if not any(u for u in known_users if u[0] == handle):
                    known_users.append((handle, ip, port))
                    print(f"+ Neuer Teilnehmer: {handle} @ {ip}:{port}")

        # WHO → Rückgabe aller bekannten Teilnehmer
        elif msg.startswith("WHO"):
            sender_ip = addr[0]
            # Port des anfragenden Clients ermitteln
            target_port = next((p for h, ip, p in known_users if ip == sender_ip), None)
            if target_port is None:
                continue

            # Antwort vorbereiten
            response = "KNOWNUSERS " + ", ".join([f"{h} {ip} {p}" for h, ip, p in known_users]) + "\n"
            sock.sendto(response.encode("utf-8"), (sender_ip, target_port))
            print(f"➡️ KNOWNUSERS gesendet an {sender_ip}:{target_port}")
            print("")