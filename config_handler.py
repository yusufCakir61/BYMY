import toml
import os

## @file config_handler.py
#  @brief Liest und verwaltet die zentrale Konfigurationsdatei (`config.toml`) für BYMY-CHAT.
#
#  **Ablauf & Struktur:**
#  1️⃣ Definiert den Speicherort der Config-Datei.  
#  2️⃣ Stellt Funktionen bereit, um die Datei einzulesen.  
#  3️⃣ Ermöglicht das sichere Abfragen einzelner Werte mit Default-Fallback.
#

CONFIG_FILE = "config.toml"  ## @var CONFIG_FILE Absoluter/relativer Pfad zur Konfigurationsdatei.

##
# @brief Liest die komplette Konfigurationsdatei ein.
#
# @details
#  1️⃣ Prüft, ob die Datei existiert.  
#  2️⃣ Wenn nicht, wird ein Fehler ausgelöst.  
#  3️⃣ Wenn ja, wird die TOML-Datei geparst und als Dictionary zurückgegeben.
#
# @return Dict mit allen Konfigurationswerten.
# @throws FileNotFoundError Falls die Datei nicht gefunden wird.
def get_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Konfigurationsdatei '{CONFIG_FILE}' nicht gefunden.")
    return toml.load(CONFIG_FILE)

##
# @brief Liest einen bestimmten Wert aus der Konfiguration.
#
# @details
#  1️⃣ Ruft intern `get_config` auf, um die gesamte Konfiguration zu laden.  
#  2️⃣ Gibt den Wert für den angegebenen Schlüssel zurück.  
#  3️⃣ Wenn der Schlüssel nicht existiert, wird ein übergebener Standardwert verwendet.
#
# @param key Schlüsselname (z.B. `"handle"` oder `"port"`).
# @param default Optionaler Standardwert, falls Schlüssel nicht existiert.
# @return Wert aus der Konfigurationsdatei oder `default`.
def get_config_value(key, default=None):
    config = get_config()
    return config.get(key, default)