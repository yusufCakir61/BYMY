import os, time, sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from network_process import send_msg, send_who, send_image

# ANSI-Farben
RESET  = "\033[0m"
Grün  = "\033[92m"     # eigene Nachricht(en)
Blau   = "\033[94m"     # empfangen
Gelb = "\033[93m"
Rot    = "\033[91m"
Cyan   = "\033[96m"
Mag    = "\033[95m"
Bold   = "\033[1m"

# ───────────────── Hilfe ───────────────────────────────────────────────
def show_intro():
    print(f"{Bold}{Blau}Willkommen beim BYMY-CHAT :) {RESET}")
    print(f"""
{Grün}Verfügbare Befehle:{RESET}
  {Gelb}who{RESET}              – Aktive Nutzer anzeigen
  {Gelb}online{RESET}           – Du bist wieder online
  {Gelb}offline{RESET}          – Abwesenheitsmodus aktivieren + Autoreply
  {Gelb}send <bild>{RESET}      – Bild senden (Dateiname reicht)
  {Gelb}/name{RESET}            – Chatpartner wechseln
  {Gelb}hilfe{RESET}            – Diese Hilfe erneut anzeigen
  {Gelb}exit{RESET}             – Beenden
""")

# ───────────────── Chat-Ausgabe ─────────────────────────────────────────
def display_chat(msg, sent=True, sender=""):
    for line in msg.strip().split("\n"):
        if sent:
            print(f"{'':>40}{Grün}Du: {line}{RESET}")
        else:
            print(f"{Blau}{sender}:{RESET} {line}")

# ───────────────── Bildsuche ────────────────────────────────────────────
def find_file(name):
    for root, _, files in os.walk(os.path.expanduser("~")):
        for f in files:
            if f.lower().startswith(name.lower()):
                return os.path.join(root, f)
    return None

# ───────────────── Haupt-Loop ───────────────────────────────────────────
def run_cli(config, known_users):
    config.setdefault("autoreply", "Bin gerade offline.")
    session      = PromptSession()
    offline_txt  = os.path.join("receive", "offline_messages.txt")
    own_handle   = config.get("handle", "Ich")

    show_intro()
    current_chat = input(f"{Mag}➤ Gebe 'who' ein um zu starten! {RESET}")

    while True:
        if current_chat.lower() == "exit":
            print(f"{Rot}👋 Chat beendet. Bis bald!{RESET}")
            break

        # —— WHO ——
        if current_chat.lower() == "who":
            send_who(config["whoisport"]); time.sleep(2)
            print(f"{Bold} {Rot}🌐 Aktive Nutzer:{RESET}" if known_users else f"{Rot}❌ Keine Nutzer gefunden.{RESET}")
            [print(f"  • {Cyan}{h}{RESET}") for h in known_users]
            print("")
            current_chat = input(f"{Mag}➤ Gib den Namen eines Chatpartners ein oder einen Befehl: {RESET}"); continue
        print("")

        # —— OFFLINE ——
        if current_chat.lower() == "offline":
            if not config.get("away", False):
                config["away"] = True
                print("")
                print(f"{Rot}🔴 Abwesenheitsmodus aktiviert.{RESET}")
                auto = config["autoreply"]
                for h in known_users:
                    if h != own_handle: send_msg(h, auto, known_users, own_handle)
            else:
                print(f"{Gelb}⚠ Bereits im Abwesenheitsmodus.{RESET}")
            current_chat = input(f"{Mag}➤ Chatpartner oder Befehl: {RESET}"); continue

        # —— ONLINE ——
        if current_chat.lower() == "online":
            if config.get("away", False):
                config["away"] = False
                print(f"{Grün}🔵 Du bist wieder online.{RESET}")
                for h in known_users:
                    if h != own_handle: send_msg(h, "Ich bin wieder da.", known_users, own_handle)
                if os.path.exists(offline_txt):
                    print("")
                    print(f"{Bold} {Rot} Verpasste Nachrichten während deiner Abwesenheit:{RESET}")
                    [print(f" {l.strip()}{RESET}") for l in open(offline_txt, encoding="utf-8")]
                    os.remove(offline_txt)
                    print("")
                else:
                    print(f"{Cyan}Keine verpassten Nachrichten.{RESET}")
                    print("")
            else:
                print(f"{Gelb}⚠ Du warst nicht offline.{RESET}")
            current_chat = input(f"{Mag}➤ Chatpartner oder Befehl: {RESET}"); continue

        # —— Hilfe ——
        if current_chat.lower() == "hilfe":
            show_intro()
            current_chat = input(f"{Mag}➤ Chatpartner oder Befehl: {RESET}"); continue

        # —— Handle mit / wechseln ——
        if current_chat.startswith("/"):
            current_chat = current_chat[1:]; continue

        # —— Unbekannter Chatpartner ——
        if current_chat not in known_users:
            print(f"{Rot}⚠ Nutzer '{current_chat}' nicht bekannt.{RESET}")
            current_chat = input(f"{Mag}➤ Chatpartner: {RESET}"); continue

        print(f"{CYAN}💬 Chat mit {current_chat} gestartet.{RESET}")

        # ───────────────── Chat-Eingabe-Loop ────────────────────────────
        while True:
            try:
                with patch_stdout():
                    msg = session.prompt("> ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{Rot}Beende Chat...{RESET}"); return

            if msg.lower() == "exit":
                print(f"{Grün}👋 Chat beendet. Bis bald!{RESET}")
                return

            if msg.lower() in ["who", "online", "offline", "hilfe"] or msg.startswith("/"):
                current_chat = msg
                break   

            # Eingabezeile entfernen
            sys.stdout.write("\033[F\033[K"); sys.stdout.flush()

            # —— Bild senden ——
            if msg.startswith("send "):
                name = msg.split(" ",1)[1].strip()
                path = find_file(name)
                if not path:
                    print(f"{Rot}❌ Bild nicht gefunden: {name}{RESET}"); continue
                with open(path,"rb") as f: data = f.read()
                send_image(current_chat, path, data, known_users, own_handle)
                display_chat(f"[Bild gesendet: {os.path.basename(path)}]", sent=True)
                continue

            # —— Text senden ——
            send_msg(current_chat, msg, known_users, own_handle)
            display_chat(msg, sent=True)
