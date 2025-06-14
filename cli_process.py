import os, time, sys, json, subprocess, socket, toml
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from config_handler import get_config
from network_process import send_msg, send_who, send_image, send_join, send_leave

RESET = "\033[0m"; GREEN = "\033[92m"; BLUE = "\033[94m"
YELLOW = "\033[93m"; RED = "\033[91m"; CYAN = "\033[96m"
MAG = "\033[95m"; BOLD = "\033[1m"

AWAY_FLAG = "away.flag"
CONFIG_FILE = "config.toml"

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

def display_chat(msg, sent=True, sender=""):
    for line in msg.strip().split("\n"):
        if sent:
            print(f"{'':>40}{GREEN}Du: {line}{RESET}")
        else:
            print(f"{BLUE}{sender}:{RESET} {line}")

def find_file(name):
    for root, _, files in os.walk(os.path.expanduser("~")):
        for f in files:
            if f.lower().startswith(name.lower()):
                return os.path.join(root, f)
    return None

def init_known_users_file():
    if not os.path.exists("known_users.json"):
        with open("known_users.json", "w") as f:
            json.dump({}, f)

def load_known_users():
    try:
        with open("known_users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def check_network_running(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("", port))
        s.close()
        return False
    except OSError:
        return True

def run_cli(config, known_users):
    config.setdefault("autoreply", "Bin gerade offline.")
    session = PromptSession()
    offline_txt = os.path.join("receive", "offline_messages.txt")
    own_handle = config.get("handle", "Ich")

    # JOIN senden beim Start
    raw_port = config.get("port")
    port = raw_port[0] if isinstance(raw_port, list) else int(raw_port)
    send_join(own_handle, port, config["whoisport"])

    show_intro()
    current_chat = input(f"{MAG}➤ Gebe zuerst 'who' ein um zu starten! {RESET}")

    while True:
        if current_chat.lower() == "exit":
            print(f"{RED}Chat wird beendet... Bis Bald{RESET}")

            # Nachricht an alle bekannten Nutzer senden
            for h in known_users:
                if h != own_handle:
                    try:
                        send_msg(h, f"[{own_handle}] hat den Chat verlassen.", known_users, own_handle)
                    except Exception as e:
                        print(f"{YELLOW}⚠ Nachricht an {h} konnte nicht gesendet werden: {e}{RESET}")

            # LEAVE senden
            try:
                send_leave(own_handle, config["whoisport"])
               # print(f"{GREEN}LEAVE gesendet an Discovery.{RESET}")
            except Exception as e:
                print(f"{RED}❌ Fehler beim Senden von LEAVE: {e}{RESET}")

           # print(f"{RED}Chat beendet. Bis bald!{RESET}")
            break

        if current_chat.lower() == "who":
            send_who(config["whoisport"])
            found = False
            for _ in range(6):
                time.sleep(0.5)
                known_users.update(load_known_users())
                if known_users:
                    found = True
                    break
            if found:
                print(f"{BOLD}{RED}🌐 Aktive Nutzer:{RESET}")
                [print(f"  • {CYAN}{h}{RESET}") for h in known_users]
            else:
                print(f"{RED}❌ Keine Nutzer gefunden.{RESET}")
            current_chat = input(f"{MAG}➤ Gib den Namen eines Chatpartners ein oder einen Befehl: {RESET}")
            continue

        if current_chat.lower() == "offline":
            if not config.get("away", False):
                config["away"] = True
                open(AWAY_FLAG, "w").close()
                print(f"{RED}Abwesenheitsmodus aktiviert.{RESET}")
                auto = config["autoreply"]
                for h in known_users:
                    if h != own_handle:
                        send_msg(h, auto, known_users, own_handle)
            else:
                print(f"{YELLOW}Bereits im Abwesenheitsmodus.{RESET}")
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        if current_chat.lower() == "online":
            if config.get("away", False):
                config["away"] = False
                if os.path.exists(AWAY_FLAG):
                    os.remove(AWAY_FLAG)
                print(f"{GREEN}Du bist wieder online.{RESET}")
                for h in known_users:
                    if h != own_handle:
                        send_msg(h, "Ich bin wieder da.", known_users, own_handle)
                if os.path.exists(offline_txt):
                    print(f"{BOLD}{RED} Verpasste Nachrichten während deiner Abwesenheit:{RESET}")
                    [print(f" {l.strip()}{RESET}") for l in open(offline_txt, encoding="utf-8")]
                    os.remove(offline_txt)
                else:
                    print(f"{CYAN}Keine verpassten Nachrichten.{RESET}")
            else:
                print(f"{YELLOW}Du warst nicht offline.{RESET}")
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        if current_chat.lower() == "hilfe":
            show_intro()
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        if current_chat.startswith("/autoreply "):
            new_reply = current_chat[len("/autoreply "):].strip()
            update_config_value("autoreply", new_reply)
            config["autoreply"] = new_reply
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        if current_chat.startswith("/name"):
            new_chat = current_chat[len("/name"):].strip()
            if new_chat in known_users:
                print(f"{CYAN}↪ Wechsel zu {new_chat}{RESET}")
                current_chat = new_chat
            else:
                print(f"{RED}⚠ Nutzer '{new_chat}' nicht bekannt.{RESET}")
                current_chat = input(f"{MAG}➤ Chatpartner: {RESET}")
            continue

        if current_chat.startswith("/"):
            print(f"{YELLOW}⚠ Unbekannter Befehl: {current_chat}{RESET}")
            current_chat = input(f"{MAG}➤ Chatpartner oder Befehl: {RESET}")
            continue

        if current_chat not in known_users:
            print(f"{RED}⚠ Nutzer '{current_chat}' nicht bekannt.{RESET}")
            current_chat = input(f"{MAG}➤ Chatpartner: {RESET}")
            continue

        print(f"{CYAN}💬 Chat mit {current_chat} gestartet.{RESET}")

        while True:
            try:
                with patch_stdout():
                    msg = session.prompt("> ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{RED} 👋 Beende Chat...{RESET}")
                return

            if msg.lower() == "exit":
                current_chat = "exit"
                break

            if msg.lower() in ["who", "online", "offline", "hilfe"] or msg.startswith("/") or msg.startswith("/name"):
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
                try:
                    send_image(current_chat, path, data, known_users, own_handle)
                except Exception:
                    print(f"{RED}❌ Netzwerkverbindung zum Senden nicht verfügbar.{RESET}")
                    continue
                display_chat(f"[Bild gesendet: {os.path.basename(path)}]", sent=True)
                continue

            try:
                send_msg(current_chat, msg, known_users, own_handle)
                display_chat(msg, sent=True)
            except Exception:
                print(f"{RED}❌ Nachricht konnte nicht gesendet werden – Netzwerkdienst nicht verfügbar.{RESET}")
                continue

def start(known_users):
    config = get_config()
    run_cli(config, known_users)

if __name__ == "__main__":
    config = get_config()
    print("")
    print(f"{YELLOW}[CLI] gestartet mit Handle: {config.get('handle')}{RESET}\n")

    try:
        ppid = os.getppid()
        parent_name = subprocess.check_output(["ps", "-p", str(ppid), "-o", "comm="]).decode().strip()
        from_main_sh = "main.sh" in parent_name
    except:
        print(f"{YELLOW}Hinweis: Startumgebung konnte nicht erkannt werden.{RESET}")
        from_main_sh = False

    init_known_users_file()

    raw_port = config.get("port")
    port = raw_port[0] if isinstance(raw_port, list) else int(raw_port)

    net_running = check_network_running(port)

    if not from_main_sh and not net_running:
        print(f"{YELLOW}ACHTUNG: Netzwerk- und Discovery-Dienste müssen separat gestartet werden.{RESET}\n")

    if not net_running:
        print(f"{RED}ACHTUNG: Netzwerkdienst läuft nicht – Chat funktioniert nicht.{RESET}\n")

    try:
        run_cli(config, {})
    except KeyboardInterrupt:
        print(f"\n{RED}Unterbrochen mit Strg+C{RESET}")
    finally:
        try:
            os.remove("known_users.json")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"{RED}❌ Fehler beim Löschen von known_users.json: {e}{RESET}")

        if os.path.exists(AWAY_FLAG):
            try:
                os.remove(AWAY_FLAG)
                print(f"{YELLOW}away.flag gelöscht.{RESET}")
            except Exception as e:
                print(f"{RED}❌ Fehler beim Löschen von away.flag: {e}{RESET}")

        if not from_main_sh:
            stop_script = os.path.join(os.path.dirname(__file__), "stop_all.sh")
            if os.path.exists(stop_script) and os.access(stop_script, os.X_OK):
                try:
                    subprocess.run(["bash", stop_script])
                except Exception as e:
                    print(f"{RED}❌ Fehler beim Ausführen von stop_all.sh: {e}{RESET}")
            else:
                print(f"{RED}❌ stop_all.sh nicht gefunden oder nicht ausführbar.{RESET}")
