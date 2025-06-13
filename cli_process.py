import os
import time
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from network_process import send_msg, send_who, send_image

# ───────────────── ANSI-Farben ─────────────────
RESET  = "\033[0m"
GREEN  = "\033[92m"  # eigene Nachrichten
BLUE   = "\033[94m"  # empfangen
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
MAG    = "\033[95m"
BOLD   = "\033[1m"

# ───────────────── Intro ─────────────────
def show_intro():
    print(f"{BOLD}{BLUE}Willkommen beim BYMY-CHAT :) {RESET}")
    print(f"""
{GREEN}Verfügbare Befehle:{RESET}
  {YELLOW}who{RESET}              – Aktive Nutzer anzeigen
  {YELLOW}online{RESET}           – Du bist wieder online
  {YELLOW}offline{RESET}          – Abwesenheitsmodus aktivieren + Autoreply
  {YELLOW}send <bild>{RESET}      – Bild senden (Dateiname reicht)
  {YELLOW}/name{RESET}            – Chatpartner wechseln
  {YELLOW}hilfe{RESET}            – Diese Hilfe erneut anzeigen
  {YELLOW}exit{RESET}             – Beenden
""")

# ───────────────── Chat-Ausgabe ─────────────────
def display_chat(message, sent=True, sender=""):
    for line in message.strip().split("\n"):
        if sent:
            print(f"{'':>40}{GREEN}Du: {line}{RESET}")
        else:
            print(f"{BLUE}{sender}:{RESET} {line}")

# ───────────────── Datei-Suche ─────────────────
def find_file(filename):
    for root, _, files in os.walk(os.path.expanduser("~")):
        for file in files:
            if file.lower().startswith(filename.lower()):
                return os.path.join(root, file)
    return None

# ───────────────── Haupt-Loop ─────────────────
def run_cli(config, known_users):
    config.setdefault("autoreply", "Bin gerade off.")
    session = PromptSession()
    offline_path = os.path.join("receive", "offline_messages.txt")
    own_handle = config.get("handle", "Ich")

    show_intro()
    current_chat = input(f"{MAG}➤ Gebe 'who' ein um zu starten! {RESET}")

    while True:
        if current_chat.lower() == "exit":
            print(f"{RED}👋 Chat beendet. Bis bald!{RESET}")
            break

        # WHO
        if current_chat.lower() == "who":
            send_who(config["whoisport"])
            time.sleep(2)
            print(f"{BOLD} {RED}🌐 Aktive Nutzer:{RESET}" if known_users else f"{RED}❌ Keine Nutzer gefunden.{RESET}")
            for h in known_users:
                print(f"  • {CYAN}{h}{RESET}")
            print("")
            current_chat = input(f"{MAG}➤ Gib den Namen eines Chatpartners ein oder einen Befehl: {RESET}")
            continue

        # OFFLINE
        if current_chat.lower() == "offline":
            if not config.get("away", False):
                config["away"] = True
                print("")
                print(f"{RED}🔴 Abwesenheitsmodus aktiviert.{RESET}")
                autoreply_text = config["autoreply"]
                for h in known_users:
                    if h != own_handle:
                        send_msg(h, autoreply_text, known_users, own_handle)
            else:
                print(f"{YELLOW}⚠ Bereits im Abwesenheitsmodus.{RESET}")
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        # ONLINE
        if current_chat.lower() == "online":
            if config.get("away", False):
                config["away"] = False
                print(f"{GREEN}🔵 Du bist wieder online.{RESET}")
                for h in known_users:
                    if h != own_handle:
                        send_msg(h, "Ich bin wieder da.", known_users, own_handle)

                if os.path.exists(offline_path):
                    print("")
                    print(f"{BOLD} {RED} Verpasste Nachrichten während deiner Abwesenheit:{RESET}")
                    for line in open(offline_path, encoding="utf-8"):
                        print(f" {line.strip()}{RESET}")
                    os.remove(offline_path)
                    print("")
                else:
                    print(f"{CYAN}Keine verpassten Nachrichten.{RESET}\n")
            else:
                print(f"{YELLOW}⚠ Du warst nicht offline.{RESET}")
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        # Hilfe
        if current_chat.lower() == "hilfe":
            show_intro()
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        # /name Wechsel
        if current_chat.startswith("/"):
            current_chat = current_chat[1:]
            continue

        # Unbekannter Nutzer
        if current_chat not in known_users:
            print(f"{RED}⚠ Nutzer '{current_chat}' nicht bekannt.{RESET}")
            current_chat = input(f"{MAG}➤ Chatpartner: {RESET}")
            continue

        print(f"{CYAN}💬 Chat mit {current_chat} gestartet.{RESET}")

        # Chat-Schleife
        while True:
            try:
                with patch_stdout():
                    msg = session.prompt("> ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{RED}Beende Chat...{RESET}")
                return

            if msg.lower() == "exit":
                print(f"{GREEN}👋 Chat beendet. Bis bald!{RESET}")
                return

            if msg.lower() in ["who", "online", "offline", "hilfe"] or msg.startswith("/"):
                current_chat = msg
                break

            sys.stdout.write("\033[F\033[K")
            sys.stdout.flush()

            # Bild senden
            if msg.startswith("send "):
                filename = msg.split(" ", 1)[1].strip()
                file_path = find_file(filename)
                if not file_path:
                    print(f"{RED}❌ Bild nicht gefunden: {filename}{RESET}")
                    continue
                with open(file_path, "rb") as f:
                    data = f.read()
                send_image(current_chat, file_path, data, known_users, own_handle)
                display_chat(f"[Bild gesendet: {os.path.basename(file_path)}]", sent=True)
                continue

            # Text senden
            send_msg(current_chat, msg, known_users, own_handle)
            display_chat(msg, sent=True)