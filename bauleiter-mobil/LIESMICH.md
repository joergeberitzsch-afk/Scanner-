# Bauleiter mobil – Testvariante ohne Server

Eine einzelne HTML-Datei (`bauleiter-mobil.html`) mit Plänen, Fotos mit Planmarkierung, Mängelliste und Bautagebuch für Handy und Tablet.

## Nutzung

- **Als Link:** Seite im Browser des Handys oder Tablets öffnen und über „Zum Home-Bildschirm“ ablegen.
- **Als Datei:** `bauleiter-mobil.html` auf das Gerät kopieren und im Browser öffnen.

Für PDF-Pläne und den PDF-Export muss die Seite beim Öffnen einmal online sein (pdf.js und jsPDF werden von cdnjs geladen). Erfassen, Markieren und Fotografieren funktionieren danach auch ohne Netz.

## Daten

- Alle Einträge liegen im Speicher des Browsers (IndexedDB) auf genau diesem Gerät. Es gibt keinen Abgleich zwischen Geräten.
- Fotos werden auf 1600 px verkleinert, PDF-Pläne beim Import als Bild der ersten Seite gespeichert.
- Unter „Mehr“ → „Sicherung herunterladen“ entsteht eine JSON-Datei mit allen Daten; „Sicherung einspielen“ stellt sie wieder her, auch auf einem anderen Gerät.
- Beim ersten Öffnen werden Beispieldaten geladen; sie lassen sich mit einem Klick entfernen.

## Unterschiede zur Server-Version (`../bauleiter-assistent`)

| | Server-Version | mobil |
|---|---|---|
| Speicherort | Datenordner auf dem PC, automatische Sicherung | Browser des Geräts, Sicherung von Hand |
| PDF-Pläne | Original bleibt erhalten, mehrseitig ansehbar | nur Seite 1 als Bild |
| PDF-Export | über den Druckdialog | direkt als PDF-Datei |
| Mehrere Geräte | ja, im Heimnetz | nein |
