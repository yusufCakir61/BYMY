## @file testmodul.py
#  Dies ist ein Beispielmodul für Doxygen-Dokumentation.
#  @brief Zeigt, wie man Funktionen dokumentiert.

## Das ist eine Beispielklasse.
#  @brief Diese Klasse tut nicht viel.
class BeispielKlasse:
    ## Konstruktor
    def __init__(self, name):
        ## @param name Der Name, der gespeichert wird.
        self.name = name

    ## Gibt eine Begrüßung aus.
    #  @return Ein Begrüßungstext.
    def sag_hallo(self):
        return f"Hallo, {self.name}!"
