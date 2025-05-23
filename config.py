import tomli  # Für Python < 3.11 – bei 3.11 bitte tomllib verwenden

def lade_konfiguration(pfad="config.toml"):
    try:
        with open(pfad, "rb") as f:
            konfig = tomli.load(f)
        return konfig
    except Exception as e:
        print("Fehler beim Laden der Konfiguration:", e)
        return None
