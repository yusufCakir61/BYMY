import sys
import os
import socket
import threading
import math
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTextEdit, QLineEdit, QFileDialog, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from config_handler import load_config
from network_process import send_join, send_msg, send_image, send_who

class ChatGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BYMY Chat (PyQt6)")
        self.resize(900, 600)

        # Config laden
        self.config = load_config()
        self.handle = self.config["handle"]
        self.port = self.config["port"][0]
        self.whoisport = self.config["whoisport"]

        self.known_users = {}

        # UI
        self.setup_ui()

        # JOIN senden
        send_join(self.handle, self.port, self.whoisport)

        # WHO-Anfrage senden
        self.do_who()

        # Empfangen starten
        threading.Thread(target=self.listen_for_messages, daemon=True).start()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        self.user_list = QListWidget()
        left_layout.addWidget(QLabel("Teilnehmer"))
        left_layout.addWidget(self.user_list)
        self.refresh_btn = QPushButton("🔄 WHO")
        self.refresh_btn.clicked.connect(self.do_who)
        left_layout.addWidget(self.refresh_btn)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        right_layout.addWidget(QLabel("Chat"))
        right_layout.addWidget(self.chat_display)

        self.input_line = QLineEdit()
        self.send_btn = QPushButton("Senden")
        self.image_btn = QPushButton("Bild senden")
        self.send_btn.clicked.connect(self.send_message)
        self.image_btn.clicked.connect(self.send_image)

        input_row = QHBoxLayout()
        input_row.addWidget(self.send_btn)
        input_row.addWidget(self.image_btn)

        right_layout.addWidget(self.input_line)
        right_layout.addLayout(input_row)

        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 5)

    def append_chat(self, text):
        self.chat_display.append(text)

    def current_recipient(self):
        selected = self.user_list.currentItem()
        if selected:
            return selected.text().split()[0]
        return None

    def send_message(self):
        text = self.input_line.text()
        to_handle = self.current_recipient()
        if not to_handle:
            QMessageBox.warning(self, "Fehler", "Bitte Empfänger aus Liste wählen.")
            return
        if not text.strip():
            return
        send_msg(to_handle, text.strip(), self.known_users, self.handle)
        self.append_chat(f"<b>Du → {to_handle}:</b> {text}")
        self.input_line.clear()

    def send_image(self):
        to_handle = self.current_recipient()
        if not to_handle:
            QMessageBox.warning(self, "Fehler", "Bitte Empfänger aus Liste wählen.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Bild auswählen", "send_img", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        with open(path, "rb") as f:
            data = f.read()
        send_image(to_handle, path, data, self.known_users, self.handle)
        self.append_chat(f"<i>📤 Bild an {to_handle} gesendet: {os.path.basename(path)}</i>")

    def do_who(self):
        send_who(self.whoisport)
        self.append_chat("<i>WHO-Anfrage gesendet...</i>")

    def listen_for_messages(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", self.port))
        incoming_images = {}

        while True:
            data, addr = sock.recvfrom(65535)
            msg = data.decode("utf-8", errors="ignore").strip()

            if msg.startswith("KNOWNUSERS"):
                users = msg[len("KNOWNUSERS "):].split(", ")
                self.known_users = {}
                self.user_list.clear()
                for user in users:
                    parts = user.split()
                    if len(parts) == 3:
                        h, ip, p = parts
                        self.known_users[h] = (ip, int(p))
                        self.user_list.addItem(f"{h} @ {ip}:{p}")
                self.append_chat("<i>👥 Teilnehmerliste aktualisiert.</i>")

            elif msg.startswith("MSG"):
                parts = msg.split(" ", 2)
                if len(parts) == 3:
                    _, sender, text = parts
                    self.append_chat(f"<b>{sender}:</b> {text}")

            elif msg.startswith("IMG_START"):
                parts = msg.split(" ", 3)
                if len(parts) == 4:
                    _, sender, filename, num_chunks_str = parts
                    num_chunks = int(num_chunks_str)
                    key = (addr, filename)
                    incoming_images[key] = {
                        "from": sender, "filename": filename, "total": num_chunks,
                        "received": 0, "chunks": {}
                    }
                    self.append_chat(f"<i>📷 Empfang startet: {filename} von {sender}</i>")

            elif msg.startswith("CHUNK"):
                try:
                    header, chunk_data = data.split(b'||', 1)
                    _, chunk_num_str = header.decode("utf-8").split(" ")
                    chunk_num = int(chunk_num_str)
                    for key in incoming_images:
                        if key[0] == addr:
                            incoming_images[key]["chunks"][chunk_num] = chunk_data
                            incoming_images[key]["received"] += 1
                            break
                except Exception:
                    pass

            elif msg.startswith("IMG_END"):
                for key, info in list(incoming_images.items()):
                    if info["received"] == info["total"]:
                        ordered_data = b''.join(info["chunks"][i] for i in range(info["total"]))
                        os.makedirs(self.config["imagepath"], exist_ok=True)
                        save_path = os.path.join(self.config["imagepath"], info["filename"])
                        with open(save_path, "wb") as f:
                            f.write(ordered_data)
                        self.append_chat(f"<i>💾 Bild empfangen und gespeichert: {save_path}</i>")
                        del incoming_images[key]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ChatGUI()
    gui.show()
    sys.exit(app.exec())
