import socket
import threading

def starte_tcp_server(port, on_receive):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", port))
    server_sock.listen()
    print(f"[Server] TCP-Server hört auf Port {port}")

    def client_handler(conn, addr):
        print(f"[Server] Verbindung von {addr}")
        while True:
            try:
                daten = conn.recv(1024)
                if not daten:
                    break
                print(f"\n📨 Nachricht von {addr[0]}:{addr[1]}: {daten.decode()}")
                on_receive(daten.decode())
            except:
                break
        print(f"[Server] Verbindung zu {addr} beendet")
        conn.close()

    def accept_clients():
        while True:
            conn, addr = server_sock.accept()
            threading.Thread(target=client_handler, args=(conn, addr), daemon=True).start()

    threading.Thread(target=accept_clients, daemon=True).start()


def tcp_client_sende(ip, port, nachricht):
    try:
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect((ip, port))
        client_sock.sendall(nachricht.encode())
        client_sock.close()
        print(f"✉️ Gesendet an {ip}:{port}: {nachricht}")
    except Exception as e:
        print(f"Fehler beim Senden: {e}")
