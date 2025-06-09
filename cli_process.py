import os
import time
from network_process import send_msg, send_who, send_image

# ANSI-Farben für Terminalausgabe
RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"

## \file cli_process.py
#  \brief Textbasierte Benutzeroberfläche (CLI) für den BYMY-Chat.
#
#  Dieses Modul stellt eine Kommandozeilen-Schnittstelle bereit, 
#  mit der Benutzer Nachrichten senden, Bilder verschicken, Teilnehmer abfragen 
#  und den Abwesenheitsmodus steuern können.

## \brief Startet die textbasierte Chat-Oberfläche (Command Line Interface).
def run_cli(config, known_users):
    config["away"] = False

    while True:
        print(f"\n{BOLD}{CYAN}========== BYMY CHAT =========={RESET}")
        print(f"{YELLOW}1){RESET} Nachricht senden")
        print(f"{YELLOW}2){RESET} Bild senden")
        print(f"{YELLOW}3){RESET} Teilnehmer anzeigen (WHO)")
        print(f"{YELLOW}4){RESET} Abwesenheitsmodus EIN/AUS")
        print(f"{YELLOW}5){RESET} Beenden")
        print(f"{CYAN}==============================={RESET}")

        choice = input(f"{MAGENTA}➤ Auswahl: {RESET}")
        print("")

        # === OPTION 1: Nachricht senden ===
        if choice == "1":
            handle = input("Empfänger-Handle: ")
            message = input("Nachricht: ")

            if handle not in known_users:
                print(f"{RED}⚠ Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.{RESET}")
                continue

            send_msg(handle, message, known_users, config["handle"])
            print(f"{GREEN}✔ Nachricht gesendet an {handle}.{RESET}")

        # === OPTION 2: Bild senden ===
        elif choice == "2":
            handle = input("Empfänger: ")

            if handle not in known_users:
                print(f"{RED}⚠ Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.{RESET}")
                continue

            folder = "send_img"
            images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

            if not images:
                print(f"{RED}⚠ Kein Bild im Ordner 'send_img/' gefunden.{RESET}")
                continue

            print(f"\n{BOLD}Verfügbare Bilder:{RESET}")
            for idx, name in enumerate(images):
                print(f"  {YELLOW}{idx+1}){RESET} {name}")

            try:
                num = int(input(f"{MAGENTA}➤ Nummer eingeben: {RESET}")) - 1
                if not 0 <= num < len(images):
                    print(f"{RED}❌ Ungültige Nummer.{RESET}")
                    continue

                path = os.path.join(folder, images[num])
                with open(path, "rb") as f:
                    data = f.read()

                send_image(handle, path, data, known_users, config["handle"])
                print(f"{GREEN}✔ Bild '{images[num]}' erfolgreich gesendet an {handle}.{RESET}")
            except Exception as e:
                print(f"{RED}Fehler beim Senden: {e}{RESET}")

        # === OPTION 3: WHO-Anfrage ===
        elif choice == "3":
            send_who(config["whoisport"])
            print(f"{YELLOW}⏳ Warte auf Antwort von anderen Clients...{RESET}")
            time.sleep(2)

            print(f"\n{BOLD}🌐 Aktuelle bekannte Nutzer:{RESET}")
            if known_users:
                for h, (ip, port) in known_users.items():
                    print(f"   • {GREEN}{h}{RESET}")
            else:
                print(f"   {RED}Keine Nutzer gefunden.{RESET}")

        # === OPTION 4: Abwesenheitsmodus toggeln ===
        elif choice == "4":
            config["away"] = not config.get("away", False)
            own_handle = config.get("handle", "Unbekannt")

            if config["away"]:
                print(f"{RED}🔴 Abwesenheitsmodus AKTIV. Auto-Reply ist eingeschaltet.{RESET}")
                status_message = "Ich bin jetzt offline."
            else:
                print(f"{GREEN}🔵 Abwesenheitsmodus DEAKTIVIERT.{RESET}")
                status_message = "Ich bin wieder online."

                # Verpasste Nachrichten anzeigen
                offline_path = os.path.join("receive", "offline_messages.txt")
                if os.path.exists(offline_path):
                    print(f"\n{BOLD}📬 Verpasste Nachrichten während deiner Abwesenheit:{RESET}")
                    with open(offline_path, "r", encoding="utf-8") as f:
                        for line in f:
                            print("   " + line.strip())
                    os.remove(offline_path)
                else:
                    print(f"{CYAN}📭 Keine verpassten Nachrichten.{RESET}")

            # Statusnachricht senden
            for handle in known_users:
                if handle != own_handle:
                    send_msg(handle, status_message, known_users, own_handle)

        # === OPTION 5: Beenden ===
        elif choice == "5":
            print(f"{MAGENTA}👋 Chat wird beendet...{RESET}")
            break

        # === Ungültige Eingabe ===
        else:
            print(f"{RED}❌ Ungültige Eingabe. Bitte eine Zahl von 1 bis 5 eingeben.{RESET}")
