##
# @file cli_process.py
# @brief Command Line Interface (CLI) für BYMY-CHAT
#
# @details
# Dieses Modul steuert den gesamten Terminal-Chat:
# 
# 👉 **GESAMTABLAUF:**
# 1️⃣  Lade und sichere Konfigurationsdatei (TOML)
# 2️⃣  Initialisiere Pipes für IPC zwischen CLI und Netzwerkprozess
# 3️⃣  Starte separaten Listener-Thread für eingehende Nachrichten
# 4️⃣  Starte den Haupt-CLI-Loop für Benutzerinteraktion
# 5️⃣  Verarbeite Steuerbefehle: WHO, ONLINE, OFFLINE, AUTOREPLY, NAME, HILFE, EXIT
# 6️⃣  Unterstütze Bildsuche und Bildversand per Befehl
# 7️⃣  Schließe Chat bei EXIT sauber inkl. LEAVE-Nachricht & Stop-Skript
#

import os, time, sys, toml, subprocess, threading
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from config_handler import get_config

RESET = "\033[0m"; GREEN = "\033[92m"; RED = "\033[91m"
CYAN = "\033[96m"; YELLOW = "\033[93m"; MAG = "\033[95m"; BOLD = "\033[1m"

AWAY_FLAG        = "away.flag"
CONFIG_FILE      = "config.toml"
PIPE_CLI_TO_NET  = "cli_to_network.pipe"
PIPE_NET_TO_CLI  = "network_to_cli.pipe"
offline_txt      = os.path.join("receive", "offline_messages.txt")

known_users = {}              
current_chat = None           
received_leave_ack = threading.Event()   

##
# @brief Ändert einen Wert in der Konfigurationsdatei.
# @details 
# Ablauf:
# 1️⃣  Lade bestehende TOML
# 2️⃣  Ändere Schlüsselwert
# 3️⃣  Speichere wieder als TOML
# 4️⃣  Melde Erfolg oder Fehler
#
def update_config_value(key, value):
    try:
        config = toml.load(CONFIG_FILE)
        config[key] = value
        with open(CONFIG_FILE, "w") as f:
            toml.dump(config, f)
        print(f"{GREEN}✓ {key} erfolgreich geändert auf: {value}{RESET}")
    except Exception as e:
        print(f"{RED}❌ Fehler beim Ändern von {key}: {e}{RESET}")

##
# @brief Zeigt das CLI-Intro mit allen Befehlen.
# @details 
# 1️⃣  Nutzt Farben & Symbole 
# 2️⃣  Listet alle gültigen Chat-Kommandos übersichtlich auf
def show_intro():
    print(f"{BOLD}{CYAN}Willkommen beim BYMY-CHAT{RESET}\n")
    print(f"""Verfügbare Befehle:{RESET}
  {YELLOW}who{RESET}                – Aktive Nutzer anzeigen
  {YELLOW}online{RESET}             – Du bist wieder da
  {YELLOW}offline{RESET}            – Abwesenheitsmodus aktivieren + Autoreply
  {YELLOW}send <bild>{RESET}        – Bild senden (Dateiname reicht)
  {YELLOW}/autoreply <text>{RESET}  – Autoreply-Nachricht ändern
  {YELLOW}/name <nutzer>{RESET}     – Chatpartner wechseln
  {YELLOW}hilfe{RESET}              – Diese Hilfe erneut anzeigen
  {YELLOW}exit{RESET}               – Beenden\n""")

##
# @brief Repariert eine Pipe-Datei.
# @details
# Ablauf:
# 1️⃣  Prüfe ob Pipe existiert
# 2️⃣  Lösche alte Pipe falls nötig
# 3️⃣  Erstelle neue Pipe
# 4️⃣  Gib Statusmeldung aus
def recover_pipe(pipe_name):
    try:
        if os.path.exists(pipe_name):
            os.remove(pipe_name)
        os.mkfifo(pipe_name)
        print(f"{YELLOW}⚠ Pipe {pipe_name} wurde neu erstellt.{RESET}")
    except Exception as e:
        print(f"{RED}❌ Fehler beim Wiederherstellen der Pipe {pipe_name}: {e}{RESET}")

##
# @brief Schreibt ein Befehlskommando in die Netzwerk-Pipe.
# @details
# Ablauf:
# 1️⃣  Öffne CLI->Network Pipe im Schreibmodus
# 2️⃣  Schreibe Kommando
# 3️⃣  Bei Fehler: Pipe reparieren
def send_pipe_command(cmd):
    try:
        with open(PIPE_CLI_TO_NET, "w") as f:
            f.write(cmd + "\n")
    except BrokenPipeError:
        print(f"{RED}❌ Netzwerkprozess nicht aktiv: {cmd}{RESET}")
        recover_pipe(PIPE_CLI_TO_NET)
    except Exception as e:
        print(f"{RED}❌ Fehler beim Pipe-Senden: {e}{RESET}")
        recover_pipe(PIPE_CLI_TO_NET)

##
# @brief Thread-Loop: Lauscht auf Nachrichten von Netzwerkprozess.
# @details 
# Ablauf:
# 1️⃣  Öffne Pipe NETWORK->CLI
# 2️⃣  Verarbeite Nachrichtentypen:
#     - KNOWNUSERS: aktualisiere Liste
#     - MSG: zeige oder speichere bei Away
#     - JOIN/LEAVE: passe Userliste an
#     - IMG: Info über erhaltenes Bild
#     - LEAVE_ACK: Setze Leave-Bestätigung
# 3️⃣  Bei Fehler: Pipe ggf. reparieren
def listen_pipe_loop():
    global known_users
    while True:
        try:
            with open(PIPE_NET_TO_CLI, "r") as pipe:
                for line in pipe:
                    if line.startswith("KNOWNUSERS "):
                        known_users = {}
                        parts = line.strip().partition(" ")[2].split(", ")
                        for p in parts:
                            handle, ip, port = p.split()
                            known_users[handle] = (ip, int(port))
                    elif line.startswith("MSG "):
                        parts = line.strip().split(" ", 2)
                        if len(parts) == 3:
                            _, sender, msg = parts
                            if os.path.exists(AWAY_FLAG):
                                with open(offline_txt, "a", encoding="utf-8") as f:
                                    f.write(f"{sender}: {msg}\n")
                            else:
                                print(f"\n{sender}: {msg}")
                    elif line.startswith("JOIN "):
                        _, sender = line.strip().split()
                        print(f"{sender} ist dem Chat beigetreten.")
                    elif line.startswith("LEAVE "):
                        _, sender = line.strip().split()
                        known_users.pop(sender, None)
                    elif line.startswith("IMG "):
                        _, sender, filename = line.strip().split()
                        print(f"{sender} hat ein Bild gesendet: {filename}")
                    elif line.startswith("LEAVE_ACK "):
                        received_leave_ack.set()
        except Exception as e:
            print(f"{RED}❌ Fehler beim Pipe-Listening: {e}{RESET}")
            time.sleep(1)
            if not os.path.exists(PIPE_NET_TO_CLI):
                recover_pipe(PIPE_NET_TO_CLI)

##
# @brief Sucht nach einer Datei im Home-Verzeichnis.
# @param name Anfang des Dateinamens.
# @return Pfad oder None.
def find_file(name):
    for root, _, files in os.walk(os.path.expanduser("~")):
        for f in files:
            if f.lower().startswith(name.lower()):
                return os.path.join(root, f)
    return None

##
# @brief Haupt-CLI-Loop.
# @details 
# 👉 **Ablauf:**
# 1️⃣  Hole Konfig & Autoreply
# 2️⃣  Führe JOIN aus
# 3️⃣  Starte Nutzereingabe-Loop:
#     - WHO: Aktive Nutzer abrufen
#     - ONLINE/OFFLINE: Status ändern
#     - /AUTOREPLY: Autoreply neu setzen
#     - /NAME: Chatpartner wechseln
#     - HILFE: Intro anzeigen
#     - EXIT: LEAVE senden & Skript stoppen
# 4️⃣  Starte Chat: Nachrichten & Bildversand
# 5️⃣  Wiederhole bis exit
def run_cli():
    global current_chat
    config = get_config()
    config.setdefault("autoreply", "Bin gerade offline.")
    own_handle = config.get("handle", "Ich")
    raw_port   = config.get("port")
    port       = raw_port[0] if isinstance(raw_port, list) else int(raw_port)

    send_pipe_command(f"JOIN {own_handle} {port}")
    show_intro()
    session = PromptSession()
    current_chat = input(f"{MAG}➔ Gebe zuerst 'who' ein um zu starten! {RESET}")

   

##
# @brief Einstiegspunkt: Erstellt Pipes & startet CLI + Listener.
if __name__ == "__main__":
    if not os.path.exists(PIPE_CLI_TO_NET): os.mkfifo(PIPE_CLI_TO_NET)
    if not os.path.exists(PIPE_NET_TO_CLI): os.mkfifo(PIPE_NET_TO_CLI)
    print(f"{YELLOW}[CLI] gestartet mit Pipes.{RESET}")
    threading.Thread(target=listen_pipe_loop, daemon=True).start()
    run_cli()