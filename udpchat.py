import socket

def starte_udp_socket(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    print(f"✅ UDP-Socket gestartet auf Port {port}")
    return sock

def sende(sock, nachricht, ip, port):
    sock.sendto(nachricht.encode(), (ip, port))
    print(f"✉️ Gesendet an {ip}:{port}: {nachricht}")

def empfange(sock):
    daten, addr = sock.recvfrom(1024)
    nachricht = daten.decode()
    print(f"\n📨 Nachricht von {addr[0]}:{addr[1]}: {nachricht}")
