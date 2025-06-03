from network_process import send_msg, send_who, send_image
import time
import os

def run_cli(config, known_users):
    while True:
        print("\n--- BYMY Chat ---") 
        print("1) Nachricht senden")  
        print("2) Bild senden") 
        print("3) Teilnehmer anzeigen (WHO)") 
        print("4) Beenden")   
        choice = input("Auswahl: ")    

        if choice == "1":
            handle = input("Empfänger-Handle: ")
            message = input("Nachricht: ")
            if handle not in known_users:
                print(f" Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.")
                continue
            send_msg(handle, message, known_users, config["handle"])

        elif choice == "2":
            handle = input("Empfänger-Handle: ")
            if handle not in known_users:
                print(f" Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.")
                continue

            folder = "send_omg"
            images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

            if not images:
                print("⚠️ Kein Bild im Ordner 'send_omg/' gefunden.")
                continue

            print("\n📂 Verfügbare Bilder:")
            for idx, name in enumerate(images):
                print(f"  {idx+1}) {name}")

            try:
                num = int(input("➡️ Nummer eingeben: ")) - 1
                if not 0 <= num < len(images):
                    print("❌ Ungültige Nummer.")
                    continue
                path = os.path.join(folder, images[num])
                with open(path, "rb") as f:
                    data = f.read()
                send_image(handle, path, data, known_users, config["handle"])
            except Exception as e:
                print(f" Fehler beim Senden: {e}")

        elif choice == "3":
            send_who(config["whoisport"])
            print(" Warte kurz auf Antwort von anderen Clients...")
            time.sleep(2)
            print(" Aktuelle bekannte Nutzer:")
            for h, (ip, port) in known_users.items():
                print(f"   • {h} @ {ip}:{port}")

        elif choice == "4":
            print(" Beende Chat...")
            break
        else:
            print(" Ungültige Eingabe.")
