from network_process import send_msg, send_who, send_image
import time
import os

## \brief Startet die textbasierte Chat-Oberfläche (Command Line Interface).
##
## Diese Funktion zeigt ein interaktives Menü an, über das der Benutzer:
## - Textnachrichten senden kann,
## - Bilder aus einem lokalen Ordner an andere Teilnehmer schicken kann,
## - per WHO-Anfrage die aktuellen Teilnehmer im Netzwerk abfragen kann,
## - oder das Programm beenden kann.
##
## Die Funktion läuft in einer Endlosschleife, bis der Benutzer Option 4 (Beenden) auswählt.
##
## \param config Ein Dictionary mit Konfigurationsdaten, z. B. eigenem Handle und WHO-Port.
## \param known_users Ein Dictionary mit bekannten Benutzernamen (Handle) und zugehöriger (IP, Port)-Tupel.
def run_cli(config, known_users):
    while True:
        # Menüauswahl anzeigen
        print("\n--- BYMY Chat ---") 
        print("1) Nachricht senden")  
        print("2) Bild senden") 
        print("3) Teilnehmer anzeigen (WHO)") 
        print("4) Beenden")   

        choice = input("Auswahl: ")    # Eingabe der Benutzerwahl

        ## === OPTION 1: Nachricht senden ===
        if choice == "1":
            handle = input("Empfänger-Handle: ")
            message = input("Nachricht: ")
            
            # Empfänger muss in der Liste bekannter Benutzer sein
            if handle not in known_users:
                print(f" Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.")
                continue

            # Sende Textnachricht an Zielbenutzer
            send_msg(handle, message, known_users, config["handle"])

        ## === OPTION 2: Bild senden ===
        elif choice == "2":
            handle = input("Empfänger-Handle: ")
            
            if handle not in known_users:
                print(f" Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.")
                continue

            # Verzeichnis mit sendbaren Bildern
            folder = "send_img"
            # Filtere alle Bilddateien mit gängigen Endungen
            images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

            if not images:
                print("⚠️ Kein Bild im Ordner 'send_img/' gefunden.")
                continue

            # Liste der verfügbaren Bilder anzeigen
            print("\n📂 Verfügbare Bilder:")
            for idx, name in enumerate(images):
                print(f"  {idx+1}) {name}")

            try:
                num = int(input("➡️ Nummer eingeben: ")) - 1
                if not 0 <= num < len(images):
                    print("❌ Ungültige Nummer.")
                    continue

                # Bildpfad und Dateiinhalt vorbereiten
                path = os.path.join(folder, images[num])
                with open(path, "rb") as f:
                    data = f.read()

                # Bild über UDP senden (wird intern ggf. in Pakete zerlegt)
                send_image(handle, path, data, known_users, config["handle"])
            except Exception as e:
                print(f" Fehler beim Senden: {e}")

        ## === OPTION 3: WHO-Anfrage ===
        elif choice == "3":
            # Anfrage ins Netzwerk senden, um andere Teilnehmer zu ermitteln
            send_who(config["whoisport"])
            print(" Warte kurz auf Antwort von anderen Clients...")
            time.sleep(2)  # Kurz warten, um Antworten einzusammeln

            print(" Aktuelle bekannte Nutzer:")
            for h, (ip, port) in known_users.items():
                print(f"   • {h} @ {ip}:{port}")

        ## === OPTION 4: Beenden ===
        elif choice == "4":
            print(" Beende Chat...")
            break

        ## === Ungültige Eingabe ===
        else:
            print(" Ungültige Eingabe.")
