## @file network_process.py
## @brief Behandelt Netzwerkkommunikation (JOIN, WHO, MSG) im Chat

from network.network_process import send_msg, send_who
import time

def run_cli(config, known_users):
    while True:
        print("\n--- BYMY Chat ---") 
        print("1) Nachricht senden")  
        print("2) Bild senvenv   den (noch nicht verfügbar)") 
        print("3) Teilnehmer anzeigen (WHO)") 
        print("4) Beenden")   
        choice = input("Auswahl: ")    

        if choice == "1":
            handle = input("Empfänger-Handle: ")
            message = input("Nachricht: ")
            if handle not in known_users:
                print(f" Nutzer '{handle}' nicht bekannt. Bitte zuerst WHO ausführen.")
                continue
            send_msg(handle, message, known_users)

        elif choice == "2":
            print(" Bildversand wird noch entwickelt.")

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
            print(" Ungültige Eingabe.")