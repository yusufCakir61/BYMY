import customtkinter as ctk
import tkinter.filedialog
import os
from network_process import send_msg, send_image, send_who

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ChatApp(ctk.CTk):
    def __init__(self, config, known_users):
        super().__init__()
        self.config = config
        self.known_users = known_users
        self.title("BYMY Chat")
        self.geometry("800x600")

        self.selected_user = None

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.user_listbox = ctk.CTkOptionMenu(self, values=["---"], command=self.select_user)
        self.user_listbox.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.refresh_button = ctk.CTkButton(self, text="🔄 WHO aktualisieren", command=self.refresh_users)
        self.refresh_button.grid(row=1, column=0, padx=10, pady=5)

        self.chat_display = ctk.CTkTextbox(self, wrap="word")
        self.chat_display.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="nsew")
        self.chat_display.configure(state="disabled")

        self.entry = ctk.CTkEntry(self)
        self.entry.grid(row=3, column=1, padx=10, pady=(0,10), sticky="ew")

        self.send_button = ctk.CTkButton(self, text="Nachricht senden", command=self.send_message)
        self.send_button.grid(row=3, column=0, padx=10, pady=(0,10))

        self.image_button = ctk.CTkButton(self, text="📤 Bild senden", command=self.send_image)
        self.image_button.grid(row=4, column=0, columnspan=2, pady=5)

        self.after(2000, self.update_display)

    def select_user(self, choice):
        self.selected_user = choice

    def refresh_users(self):
        send_who(self.config["whoisport"])
        self.after(2000, self.update_user_list)

    def update_user_list(self):
        user_list = list(self.known_users.keys())
        if not user_list:
            user_list = ["---"]
        self.user_listbox.configure(values=user_list)
        if self.selected_user not in user_list:
            self.selected_user = user_list[0]
            self.user_listbox.set(self.selected_user)

    def send_message(self):
        msg = self.entry.get()
        to = self.selected_user
        if to and msg and to in self.known_users:
            send_msg(to, msg, self.known_users, self.config["handle"])
            self.entry.delete(0, "end")
            self.display(f"Du → {to}: {msg}")

    def send_image(self):
        to = self.selected_user
        if not to or to not in self.known_users:
            return
        file_path = tkinter.filedialog.askopenfilename(initialdir="send_img", filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not file_path:
            return
        with open(file_path, "rb") as f:
            data = f.read()
        send_image(to, file_path, data, self.known_users, self.config["handle"])
        self.display(f"📤 Du hast ein Bild an {to} gesendet: {os.path.basename(file_path)}")

    def display(self, text):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text + "\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def update_display(self):
        if "image_events" in self.config:
            while self.config["image_events"]:
                event = self.config["image_events"].pop(0)
                self.display(f"📷 {event['from']} hat ein Bild gesendet: {event['filename']}")
        self.after(1000, self.update_display)

def start_gui(config, known_users):
    app = ChatApp(config, known_users)
    app.mainloop()
