import threading
import sys
from config import lade_konfiguration
from udpchat import starte_udp_socket, sende, empfange

# Funktion für eingehende Nachrichten
def empfangsschleife(sock):
    while True:
        try:
            empfange(sock)
        except Exception as e:
            print("❌ Fehler beim Empfangen:", e)
            break

def main():
    konfig = lade_konfiguration()
    if not konfig:
        print("Fehler beim Laden der Konfiguration.")
        return

    # Port aus Argument lesen
    if len(sys.argv) < 2:
        print("❌ Bitte gib den Port an: z. B. python3 main.py 5000")
        return

    try:
        port = int(sys.argv[1])
    except:
        print("❌ Ungültiger Port. Beispiel: python3 main.py 5000")
        return

    print(f"\n📢 Willkommen bei UnserChat auf Port {port}!")
    print("Verfügbare Befehle: help, say <zielport>:<Text>, exit\n")

    sock = starte_udp_socket(port)

    # Empfangs-Thread starten
    empfang_thread = threading.Thread(target=empfangsschleife, args=(sock,), daemon=True)
    empfang_thread.start()

    # Eingabeschleife
    while True:
        eingabe = input(">> ").strip()

        if eingabe == "exit":
            print("👋 Tschüss!")
            break

        elif eingabe == "help":
            print("🆘 Befehle:")
            print("  exit                     - beendet das Programm")
            print("  help                     - zeigt diese Hilfe")
            print("  say <port>:<Text>        - sendet Nachricht an Port")

        elif eingabe.startswith("say "):
            try:
                ziel, nachricht = eingabe[4:].split(":", 1)
                zielport = int(ziel)
                sende(sock, nachricht, "127.0.0.1", zielport)
            except:
                print("❌ Nutzung: say <port>:<nachricht>")
        else:
            print("❌ Unbekannter Befehl. Tippe 'help'.")

if __name__ == "__main__":
    main()
