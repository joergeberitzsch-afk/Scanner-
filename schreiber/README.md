# Schreiber

Eine schlanke Textverarbeitung für den Browser, angelehnt an die Bedienung von Microsoft Word. Die gesamte Anwendung steckt in einer einzigen Datei (`index.html`) und läuft ohne Installation und ohne Server.

## Starten

`index.html` im Browser öffnen (Chrome, Edge, Firefox oder Safari). Für den Import und Export von Word-Dateien wird beim ersten Laden eine Internetverbindung benötigt.

## Funktionen

- **Start:** Rückgängig/Wiederholen, Format übertragen, Formatvorlagen (Standard, Überschrift 1–3, Zitat, Code), Schriftart, Schriftgrad, Fett, Kursiv, Unterstrichen, Durchgestrichen, Hoch-/Tiefgestellt, Schrift- und Hervorhebungsfarbe, Aufzählung, Nummerierung, Einzüge, Ausrichtung, Zeilenabstand
- **Einfügen:** Seitenumbruch, Tabellen (Zeilen/Spalten hinzufügen und löschen), Bilder (auch per Drag & Drop oder Einfügen aus der Zwischenablage), Links, Linie, Datum, Sonderzeichen
- **Layout:** Papierformat (A4, A5, Letter, Legal), Hoch-/Querformat, Seitenränder (u. a. DIN 5008), ein- bis dreispaltiger Satz
- **Ansicht:** Zoom, Seitenbreite, Rechtschreibprüfung, Wörter zählen
- **Datei:** Öffnen von `.docx`, `.html`, `.txt` und `.md`; Speichern als `.docx`, `.html` und `.txt`; Drucken bzw. Speichern als PDF über den Druckdialog
- Suchen und Ersetzen, Statusleiste mit Seiten-, Wort- und Zeichenzahl
- Automatisches Speichern im Browser

## Tastenkürzel

| Kürzel | Funktion |
| --- | --- |
| Strg+B / I / U | Fett / Kursiv / Unterstrichen |
| Strg+L / E / R / J | Links / Zentriert / Rechts / Blocksatz |
| Strg+Alt+1 / 2 / 3 / 0 | Überschrift 1 / 2 / 3 / Standard |
| Strg+Enter | Seitenumbruch |
| Strg+K | Link einfügen |
| Strg+F, Strg+H | Suchen und Ersetzen |
| Strg+S | Als .docx speichern |
| Strg+O | Öffnen |
| Strg+P | Drucken |
| Tab / Umschalt+Tab | Einrücken in Listen, Zellenwechsel in Tabellen |

## Grenzen

Seitenumbrüche werden am Bildschirm als Linien angedeutet; die exakte Seitenaufteilung entsteht beim Drucken bzw. in Word. Kopf- und Fußzeilen, Fußnoten, Inhaltsverzeichnisse, Änderungsverfolgung und Kommentare sind nicht enthalten. Beim Import von `.docx` werden Struktur und Grundformatierung übernommen, komplexe Layouts nur vereinfacht.

## Verwendete Bibliotheken

- [mammoth.js](https://github.com/mwilliamson/mammoth.js) (BSD-2-Clause) für den Import von `.docx`
- [html-docx-js](https://github.com/evidenceprime/html-docx-js) (MIT) für den Export nach `.docx`
