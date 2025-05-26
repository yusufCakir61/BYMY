/**
 * @mainpage BYMY Chatprojekt
 *
 * @section intro_sec Einleitung
 * Dies ist die Dokumentation zum BYMY Chatprojekt aus dem Modul
 * Betriebssysteme und Rechnernetze (Sommersemester 2025).
 *
 * Das Projekt ist ein dezentraler Peer-to-Peer-Chat, der ohne zentralen Server
 * funktioniert und über ein textbasiertes Protokoll kommuniziert.
 *
 * @section features_sec Umgesetzte Funktionen
 * - Versand und Empfang von Textnachrichten (MSG)
 * - Teilnehmererkennung per Broadcast (JOIN, WHO, KNOWNUSERS)
 * - Interprozesskommunikation mit multiprocessing.Manager
 * - Konfiguration über eine TOML-Datei
 * - Mehrprozess-Architektur: CLI, Netzwerk, Discovery
 *
 * @section usage_sec Struktur
 * Das Programm besteht aus folgenden Komponenten:
 * - main.py: Startet das gesamte Programm mit allen Prozessen
 * - cli/: Kommandozeilenoberfläche
 * - network/: Nachrichtenversand und -empfang
 * - discovery/: Teilnehmererkennung
 * - config/: Laden der Konfiguration
 *
 * @section future_sec Geplante Erweiterungen
 * - Versand und Empfang von Bildern (IMG)
 * - GUI (grafische Benutzeroberfläche)
 * - Persistente Nachrichtenhistorie
 *
 * @section author_sec Team
 * - Erstellt im Rahmen des Semestersprojekts an der Frankfurt UAS
 */
