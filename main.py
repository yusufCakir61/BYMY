import threading
import sys
from config import lade_konfiguration
from tcpchat import starte_tcp_server, tcp_client_sende

def zeige_server_banner(port):
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 📡 TCP-Chat | Server-Modus    
 📍 Lausche auf Port {port}
 Tippe 'exit' zum Beenden
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

def zeige_client_banner(zielport):
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 💬 TCP-Chat | Client-Modus    
 ✉️  Sende Nachrichten an 127.0.0.1:{zielport}
 Tippe 'exit' zum Beenden
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

def main():
    konfig = lade_konfiguration()
    if not konfig:
        return

    if len(sys.argv) < 2:
        print("❌ Bitte gib deine Rolle an: 'server' oder 'client'")
        return

    rolle = sys.argv[1].lower()
    server_port = konfig["port"][0]
    client_port = konfig["port"][1]

    if rolle == "server":
        zeige_server_banner(server_port)

        def on_receive(msg):
            # Hier könnte man z. B. automatische Antworten implementieren
            pass

        starte_tcp_server(server_port, on_receive)

        while True:
            eingabe = input("").strip()
            if eingabe == "exit":
                print("🚪 Server beendet.")
                break

    elif rolle == "client":
        zeige_client_banner(server_port)

        while True:
            eingabe = input("💬 Du >> ").strip()
            if eingabe == "exit":
                print("🚪 Client beendet.")
                break
            tcp_client_sende("127.0.0.1", server_port, eingabe)

    else:
        print("❌ Ungültige Rolle. Nutze 'server' oder 'client'")

if __name__ == "__main__":
    main()
