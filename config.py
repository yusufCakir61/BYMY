import tomli

def lade_konfiguration(pfad="config.toml"):
    try:
        with open(pfad, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        print("Fehler beim Laden der Konfiguration:", e)
        return None
