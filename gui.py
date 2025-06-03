import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import os

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BYMY Chat GUI")

        self.left_frame = ttk.Frame(root, padding="10")
        self.left_frame.pack(side="left", fill="y")

        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.pack(side="right", fill="both", expand=True)

        ttk.Label(self.left_frame, text="Teilnehmer").pack()
        self.user_listbox = tk.Listbox(self.left_frame, height=20, width=25)
        self.user_listbox.pack(fill="y")

        ttk.Label(self.right_frame, text="Chatverlauf").pack()
        self.chat_display = scrolledtext.ScrolledText(self.right_frame, wrap="word", height=20)
        self.chat_display.pack(fill="both", expand=True)

        self.entry = ttk.Entry(self.right_frame)
        self.entry.pack(fill="x", pady=5)
        self.entry.bind("<Return>", self.send_message)

        btn_frame = ttk.Frame(self.right_frame)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="Senden", command=self.send_message).pack(side="left")
        ttk.Button(btn_frame, text="Bild senden", command=self.send_image).pack(side="left")

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg:
            self.chat_display.insert(tk.END, "Du: " + msg + "\n")
            self.entry.delete(0, tk.END)

    def send_image(self):
        file_path = filedialog.askopenfilename(initialdir="send_img", title="Bild auswählen")
        if file_path:
            self.chat_display.insert(tk.END, f"📤 Bild gesendet: {os.path.basename(file_path)}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()
