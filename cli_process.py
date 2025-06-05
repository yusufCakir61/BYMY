from network_process import send_msg, send_who, send_image
import time
import os

## \file cli_process.py
#  \brief Textbasierte Benutzeroberfläche (CLI) für den BYMY-Chat.
#
#  Dieses Modul stellt eine Kommandozeilen-Schnittstelle bereit, 
#  mit der Benutzer Nachrichten senden, Bilder verschicken, Teilnehmer abfragen 
#  und den Abwesenheitsmodus steuern können.

## \brief Startet die textbasierte Chat-Oberfläche (Command Line Interface).
##
## Diese Funktion zeigt ein interaktives Menü an, über das der Benutzer:
## - Textnachrichten senden kann,
## - Bilder aus einem lokalen Ordner an andere Teilnehmer schicken kann,
## - per WHO-Anfrage die aktuellen Teilnehmer im Netzwerk abfragen kann,
## - den Abwesenheitsmodus ein- oder ausschalten kann,
## - oder das Programm beenden kann.
##
## Die Funktion läuft in einer Endlosschleife, bis der Benutzer Option 5 (Beenden) auswählt.
##
## \param config Ein Dictionary mit Konfigurationsdaten, z.\u202fB. eigenem Handle und WHO-Port.
## \param known_users Ein Dictionary mit bekannten Benutzernamen (Handle) und zugehöriger (IP, Port)-Tupel.
def run_cli(config, known_users):
    config["away"] = False

    while True:
        print("\n--- BYMY Chat ---") 
        print("1) Nachricht senden")  
        print("2) Bild senden") 
        print("3) Teilnehmer anzeigen (WHO)") 
        print("4) Abwesenheitsmodus EIN/AUS")
        print("5) Beenden")   

        choice = input("Auswahl: ")

        ## === OPTION 1: Nachricht senden ===
        if choice == "1":
            handle = input("Empfänger-Handle: ")
            message = input("Nachricht: ")

            if handle not in known_users:
                print(f" Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.")
                continue

            send_msg(handle, message, known_users, config["handle"])

        ## === OPTION 2: Bild senden ===
        elif choice == "2":
            handle = input("Empfänger-Handle: ")

            if handle not in known_users:
                print(f" Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.")
                continue

            folder = "send_img"
            images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

            if not images:
                print("⚠️ Kein Bild im Ordner 'send_img/' gefunden.")
                continue

            print("\n📂 Verfügbare Bilder:")
            for idx, name in enumerate(images):
                print(f"  {idx+1}) {name}")

            try:
                num = int(input("➞ Nummer eingeben: ")) - 1
                if not 0 <= num < len(images):
                    print("❌ Ungültige Nummer.")
                    continue

                path = os.path.join(folder, images[num])
                with open(path, "rb") as f:
                    data = f.read()

                send_image(handle, path, data, known_users, config["handle"])
            except Exception as e:
                print(f" Fehler beim Senden: {e}")

        ## === OPTION 3: WHO-Anfrage ===
        elif choice == "3":
            send_who(config["whoisport"])
            print(" Warte kurz auf Antwort von anderen Clients...")
            time.sleep(2)

            print(" Aktuelle bekannte Nutzer:")
            for h, (ip, port) in known_users.items():
                print(f"   • {h} @ {ip}:{port}")

        ## === OPTION 4: Abwesenheitsmodus toggeln mit Broadcast-Nachricht ===
        elif choice == "4":
            config["away"] = not config.get("away", False)
            own_handle = config.get("handle", "Unbekannt")

            if config["away"]:
                print("🔴 Abwesenheitsmodus AKTIV. Auto-Reply ist eingeschaltet.")
                status_message = f"Ich bin jetzt offline."
            else:
                print("🔵 Abwesenheitsmodus DEAKTIVIERT.")
                status_message = f"Ich bin wieder online."

            # Sende Statusnachricht an alle bekannten Nutzer
            for handle in known_users:
                if handle != own_handle:
                    send_msg(handle, status_message, known_users, own_handle)

        ## === OPTION 5: Beenden ===
        elif choice == "5":
            print(" Beende Chat...")
            break

        ## === Ungültige Eingabe ===
        else:
            print(" Ungültige Eingabe.")
            