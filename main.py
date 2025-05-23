from config import lade_konfiguration

def main():
    konfig = lade_konfiguration()
    if konfig:
        print("Konfiguration erfolgreich geladen:")
        for key, value in konfig.items():
            print(f"{key}: {value}")
    else:
        print("Fehler beim Laden der Konfiguration.")

if __name__ == "__main__":
    main()
