import os, time, sys, toml, subprocess, threading
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from config_handler import get_config

RESET = "\033[0m"; GREEN = "\033[92m"; RED = "\033[91m"
CYAN = "\033[96m"; YELLOW = "\033[93m"; MAG = "\033[95m"; BOLD = "\033[1m"

AWAY_FLAG = "away.flag"
CONFIG_FILE = "config.toml"
PIPE_CLI_TO_NET = "cli_to_network.pipe"
PIPE_NET_TO_CLI = "network_to_cli.pipe"
offline_txt = os.path.join("receive", "offline_messages.txt")
known_users = {}
current_chat = None

def update_config_value(key, value):
    try:
        config = toml.load(CONFIG_FILE)
        config[key] = value
        with open(CONFIG_FILE, "w") as f:
            toml.dump(config, f)
        print(f"{GREEN}✓ {key} erfolgreich geändert auf: {value}{RESET}")
    except Exception as e:
        print(f"{RED}❌ Fehler beim Ändern von {key}: {e}{RESET}")

def show_intro():
    print(f"{BOLD}{CYAN}Willkommen beim BYMY-CHAT{RESET}\n")
    print(f"""Verfügbare Befehle:{RESET}
  {RED}who{RESET}                – Aktive Nutzer anzeigen
  {RED}online{RESET}             – Du bist wieder da
  {RED}offline{RESET}            – Abwesenheitsmodus aktivieren + Autoreply
  {RED}send <bild>{RESET}        – Bild senden (Dateiname reicht)
  {RED}/autoreply <text>{RESET}  – Autoreply-Nachricht ändern
  {RED}/name <nutzer>{RESET}     – Chatpartner wechseln
  {RED}hilfe{RESET}              – Diese Hilfe erneut anzeigen
  {RED}exit{RESET}               – Beenden\n""")

def recover_pipe(pipe_name):
    try:
        if os.path.exists(pipe_name):
            os.remove(pipe_name)
        os.mkfifo(pipe_name)
        print(f"{YELLOW}⚠ Pipe {pipe_name} wurde neu erstellt.{RESET}")
    except Exception as e:
        print(f"{RED}❌ Fehler beim Wiederherstellen der Pipe {pipe_name}: {e}{RESET}")

def send_pipe_command(cmd):
    try:
        with open(PIPE_CLI_TO_NET, "w") as f:
            f.write(cmd + "\n")
    except BrokenPipeError:
        print(f"{RED}❌ Netzwerkprozess ist nicht aktiv – Befehl nicht gesendet: {cmd}{RESET}")
        recover_pipe(PIPE_CLI_TO_NET)
    except Exception as e:
        print(f"{RED}❌ Fehler beim Senden über Pipe: {e}{RESET}")
        recover_pipe(PIPE_CLI_TO_NET)

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
                                print("> ", end="", flush=True)

                    elif line.startswith("JOIN "):
                        _, sender = line.strip().split()
                        print(f"{YELLOW}{sender} ist dem Chat beigetreten.{RESET}")

                    elif line.startswith("IMG "):
                        _, sender, filename = line.strip().split()
                        print(f"{sender} hat ein Bild gesendet: {filename}{RESET}")

        except Exception as e:
            print(f"{RED}❌ Fehler beim Lesen aus Pipe: {e}{RESET}")
            # Kurze Pause, um CPU-Overload zu vermeiden und eventuell Pipe wiederherstellen
            time.sleep(1)
            if not os.path.exists(PIPE_NET_TO_CLI):
                recover_pipe(PIPE_NET_TO_CLI)

def find_file(name):
    for root, _, files in os.walk(os.path.expanduser("~")):
        for f in files:
            if f.lower().startswith(name.lower()):
                return os.path.join(root, f)
    return None

def run_cli():
    global current_chat
    config = get_config()
    config.setdefault("autoreply", "Bin gerade offline.")
    own_handle = config.get("handle", "Ich")
    raw_port = config.get("port")
    port = raw_port[0] if isinstance(raw_port, list) else int(raw_port)
    send_pipe_command(f"JOIN {own_handle} {port}")
    show_intro()
    session = PromptSession()
    current_chat = input(f"{MAG}➔ Gebe zuerst 'who' ein um zu starten! {RESET}")

    while True:
        if current_chat.lower() == "exit":
            send_pipe_command(f"LEAVE {own_handle}")
            for h in known_users:
                if h != own_handle:
                    send_pipe_command(f"SEND_MSG {h} hat den Chat verlassen.")
            print(f"{RED}Chat wird beendet... Bis Bald{RESET}")
            stop_script = os.path.join(os.path.dirname(__file__), "stop_all.sh")
            if os.path.exists(stop_script) and os.access(stop_script, os.X_OK):
                try:
                    subprocess.run(["bash", stop_script])
                except Exception as e:
                    print(f"{RED}❌ Fehler beim Ausführen von stop_all.sh: {e}{RESET}")
            else:
                print(f"{YELLOW}⚠ stop_all.sh nicht gefunden oder nicht ausführbar.{RESET}")
            break

        elif current_chat.lower() == "who":
            send_pipe_command("WHO")
            time.sleep(1)
            if known_users:
                print(f"{BOLD}{RED}🌐 Aktive Nutzer:{RESET}")
                [print(f"  • {h}") for h in known_users]
            else:
                print(f"{RED}❌ Keine Nutzer gefunden.{RESET}")
            current_chat = input(f"{MAG}➔ Chatpartner oder Befehl: {RESET}")
            continue

        elif current_chat.lower() == "offline":
            if not config.get("away", False):
                config["away"] = True
                open(AWAY_FLAG, "w").close()
                print(f"{RED}Abwesenheitsmodus aktiviert.{RESET}")
                auto = config["autoreply"]
                for h in known_users:
                    if h != own_handle:
                        send_pipe_command(f"SEND_MSG {h} {auto}")
            else:
                print(f"{YELLOW}Bereits im Abwesenheitsmodus.{RESET}")
            current_chat = input(f"{MAG}➔ Chatpartner oder Befehl: {RESET}")
            continue

        elif current_chat.lower() == "online":
            if config.get("away", False):
                config["away"] = False
                if os.path.exists(AWAY_FLAG):
                    os.remove(AWAY_FLAG)
                print(f"{GREEN}Du bist wieder online.{RESET}")
                for h in known_users:
                    if h != own_handle:
                        send_pipe_command(f"SEND_MSG {h} Ich bin wieder da.")
                if os.path.exists(offline_txt):
                    print(f"{BOLD}{RED} Verpasste Nachrichten:{RESET}")
                    [print(f" {l.strip()}") for l in open(offline_txt, encoding="utf-8")]
                    os.remove(offline_txt)
                else:
                    print(f"{CYAN}Keine verpassten Nachrichten.{RESET}")
            else:
                print(f"{YELLOW}Du warst nicht offline.{RESET}")
            current_chat = input(f"{MAG}➔ Chatpartner oder Befehl: {RESET}")
            continue

        elif current_chat.lower() == "hilfe":
            show_intro()
            current_chat = input(f"{MAG}➔ Chatpartner oder Befehl: {RESET}")
            continue

        elif current_chat.startswith("/autoreply "):
            new_reply = current_chat[len("/autoreply "):].strip()
            update_config_value("autoreply", new_reply)
            config["autoreply"] = new_reply
            current_chat = input(f"{MAG}➔ Chatpartner oder Befehl: {RESET}")
            continue

        elif current_chat.startswith("/name"):
            new_chat = current_chat[len("/name"):].strip()
            if new_chat in known_users:
                print(f"{CYAN}↪ Wechsel zu {new_chat}{RESET}")
                current_chat = new_chat
            else:
                print(f"{RED}⚠ Nutzer '{new_chat}' nicht bekannt.{RESET}")
                current_chat = input(f"{MAG}➔ Chatpartner: {RESET}")
            continue

        elif current_chat.startswith("/"):
            print(f"{YELLOW}⚠ Unbekannter Befehl: {current_chat}{RESET}")
            current_chat = input(f"{MAG}➔ Chatpartner oder Befehl: {RESET}")
            continue

        elif current_chat not in known_users:
            print(f"{RED}⚠ Nutzer '{current_chat}' nicht bekannt.{RESET}")
            current_chat = input(f"{MAG}➔ Chatpartner: {RESET}")
            continue

        print(f"{CYAN}💬 Chat mit {current_chat} gestartet.{RESET}")
        while True:
            try:
                with patch_stdout():
                    msg = session.prompt("> ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{RED} Chat beendet.{RESET}")
                return

            if msg.lower() == "exit":
                current_chat = "exit"
                break
            if msg.lower() in ["who", "online", "offline", "hilfe"] or msg.startswith("/"):
                current_chat = msg
                break

            sys.stdout.write("\033[F\033[K")
            sys.stdout.flush()

            if msg.startswith("send "):
                name = msg.split(" ", 1)[1].strip()
                path = find_file(name)
                if not path:
                    print(f"{RED}❌ Bild nicht gefunden: {name}{RESET}")
                    continue
                with open(path, "rb") as f:
                    data = f.read()
                send_pipe_command(f"SEND_IMAGE {current_chat} {path} {len(data)}")
                print(f"{'':>40}{GREEN}Du: [Bild gesendet: {os.path.basename(path)}]{RESET}")
                continue

            send_pipe_command(f"SEND_MSG {current_chat} {msg}")
            print(f"{'':>40}{GREEN}Du: {msg}{RESET}")

if __name__ == "__main__":
    if not os.path.exists(PIPE_CLI_TO_NET): os.mkfifo(PIPE_CLI_TO_NET)
    if not os.path.exists(PIPE_NET_TO_CLI): os.mkfifo(PIPE_NET_TO_CLI)
    print(f"{YELLOW}[CLI] gestartet mit Pipes.{RESET}")
    threading.Thread(target=listen_pipe_loop, daemon=True).start()
    run_cli()
