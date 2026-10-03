# Bauleiter-Assistent – Testversion 1.1

Lokale Browser-Anwendung für die Bauleitung: Pläne, Baustellenfotos, Mängelliste und Bautagebuch an einem Ort. Die Testversion läuft getrennt von V1 (eigener Port, eigener Datenordner), sodass beide parallel genutzt werden können.

| | V1 | Testversion 1.1 |
|---|---|---|
| Adresse | http://localhost:8787 | http://localhost:8788 |
| Daten | V1-Ordner | `daten_test\` |

## Installation

1. Python 3.8 oder neuer muss installiert sein (vorhanden: Python 3.12). Weitere Pakete werden nicht benötigt.
2. Den Ordner `bauleiter-assistent` an einen beliebigen Ort kopieren, z. B. `C:\Users\<Name>\Bauleiter-Assistent-Test`.
3. Doppelklick auf **`Bauleiter-Assistent_Test_starten.cmd`**.

Der Server startet minimiert, der Browser öffnet sich automatisch. Zum Beenden das minimierte Fenster „Bauleiter-Assistent Testversion“ schließen.

## Was die Startdatei erledigt

- Sucht Python selbstständig (Python-Launcher `py`, dann `python` im PATH, dann die üblichen Installationsordner). Ein fest eingetragener Pfad ist nicht mehr nötig.
- Installiert beim ersten Start fehlende Pakete, falls künftig eine `requirements.txt` beiliegt.
- Prüft vor dem Start, ob der Port frei ist:
  - Läuft der Assistent schon, wird nur der Browser geöffnet.
  - Belegt ein anderes Programm den Port, erscheint eine verständliche Meldung, und das Fenster bleibt offen.
- Der Browser wird erst geöffnet, wenn der Server tatsächlich bereit ist.

## Funktionen

### Pläne
- PDF-, PNG- oder JPG-Pläne hochladen (auch mehrere auf einmal).
- Das Geschoss wird aus dem Dateinamen erkannt, z. B. `A_GR_OG5_ST3_NB.pdf` → OG5, `Grundriss 1.OG.pdf` → OG1. Die Liste ist nach Geschoss sortiert (UG … EG … OG10 … DG).
- Pläne direkt im Browser öffnen, zoomen und als Original herunterladen.

### Fotos
- Fotos hochladen; das Aufnahmedatum wird aus dem Dateinamen gelesen (z. B. `20260912_090810_….jpg` → 12.09.2026), sonst gilt das heutige Datum.
- Je Foto: Notiz, Datum, Geschoss, Zuordnung zu einem Mangel.
- **Markierung auf dem Plan:** „Markieren“ wählen und auf die Stelle im Plan klicken. Markierungen lassen sich verschieben und entfernen.

### Mängelliste
- Erfassung mit Kurzbeschreibung, Beschreibung, Geschoss, Ort/Raum, Gewerk, Firma, Frist und Status (offen / in Arbeit / erledigt).
- Laufende Nummerierung (M1, M2 …), überfällige Fristen werden rot hervorgehoben.
- Filter nach Status, Gewerk, Geschoss, Firma, Freitext und „nur überfällige“.
- Fotos direkt am Mangel anhängen; Mangel auf dem Plan markieren oder im Plan per Klick „Neuer Mangel an dieser Stelle“ anlegen.
- **Druckansicht / PDF** mit den aktuell gesetzten Filtern, inklusive Fotos und Unterschriftszeile.

### Bautagebuch
- Ein Eintrag je Tag: Wetter, Temperatur, Arbeitszeit, Personal (Firma, Gewerk, Anzahl – mit Summe), ausgeführte Leistungen, Behinderungen, Vorkommnisse, Anordnungen, Besucher.
- „Vom letzten Eintrag übernehmen“ übernimmt die Personalliste des Vortags.
- Fotos des Tages erscheinen automatisch im Eintrag und im Ausdruck.
- **Druckansicht / PDF** mit fortlaufender Berichtsnummer.

PDF erzeugen: In der Druckansicht auf „Drucken / als PDF speichern“ klicken und als Drucker „Microsoft Print to PDF“ bzw. „Als PDF speichern“ wählen.

### Übersicht und Einstellungen
- Startseite mit Kennzahlen, fälligen Mängeln (überfällig oder innerhalb von 7 Tagen) und den neuesten Fotos.
- Projektangaben (Nummer, Name, Adresse, Bauherr, Bauleitung) für die Kopfzeilen der Ausdrucke sowie eine Gewerkeliste für die Eingabevorschläge.

## Datensicherung und Fehlerprotokoll

- Bei jedem Start wird der Datenordner als ZIP in `sicherungen\` abgelegt (`daten_JJJJMMTT_HHMMSS.zip`). Die letzten 20 Sicherungen bleiben erhalten.
- **Wiederherstellen:** Assistent beenden, Ordner `daten_test` umbenennen, gewünschte ZIP-Datei nach `daten_test` entpacken, neu starten.
- Fehler werden in `logs\server.log` protokolliert. Bei Problemen bitte diese Datei mitschicken.

## Einstellungen (`config.json`)

| Schlüssel | Bedeutung | Standard |
|---|---|---|
| `port` | Port der Anwendung | 8788 |
| `host` | `127.0.0.1` = nur dieser PC; `0.0.0.0` = im Heimnetz erreichbar (z. B. für ein Tablet) | 127.0.0.1 |
| `datenordner` | Ablage für Datenbank, Pläne und Fotos | daten_test |
| `sicherungen_behalten` | Anzahl aufbewahrter Sicherungen | 20 |
| `max_upload_mb` | Höchstgröße je Datei | 200 |
| `browser_oeffnen` | Browser beim Start öffnen | true |

Hinweis zu `0.0.0.0`: Die Anwendung hat keine Anmeldung. Nur im eigenen, geschützten Netz verwenden.

## Bekannte Einschränkungen der Testversion

- Ein Projekt je Datenordner. Für ein zweites Projekt die Anwendung in einen weiteren Ordner kopieren und in `config.json` einen anderen Port eintragen.
- Bei mehrseitigen PDF-Plänen wird nur Seite 1 angezeigt und markiert.
- Fotos im HEIC-Format (iPhone) werden nicht angenommen; in der Kamera-App „Maximale Kompatibilität“ (JPG) einstellen.
- Keine Benutzerverwaltung.

## Für Entwickler

```
python -m unittest discover -s tests     # automatische Tests
python server.py --pruefen               # Voraussetzungen prüfen
python server.py --port 9000 --kein-browser
```

Aufbau: `server.py` (HTTP-Server, SQLite-Datenbank, Druckansichten), `static/` (Oberfläche in HTML/CSS/JavaScript), `static/vendor/pdfjs/` (pdf.js 3.11.174 von Mozilla, Apache-2.0-Lizenz, für die Planvorschau ohne Internet).
