# Sprachblitz

Diktier-App fürs Handy: sprechen, Text bekommen, weiterverwenden. Gedacht für E-Mails, Notizen und Prompts – auch dann, wenn man nicht nach Tagesschau klingt.

## Was die App kann

- **Aufnahme per Knopfdruck** – einmal tippen zum Starten, nochmal zum Beenden.
- **Zwei Erkennungswege**
  - *Browser*: kostenlos und live, nutzt die Spracherkennung von Chrome bzw. Safari.
  - *Whisper / GPT-Transcribe (OpenAI)*: deutlich treffsicherer bei Dialekt, Nuscheln und Nebengeräuschen. Braucht einen eigenen OpenAI-Schlüssel.
- **Dialekt-Auswahl** – u. a. Bairisch, Schwäbisch, Badisch, Fränkisch, Hessisch, Sächsisch, Kölsch, Plattdeutsch, Österreichisch, Schweizerdeutsch.
- **Aufbereitung mit Claude** – korrigiert falsch verstandene Wörter aus dem Zusammenhang, überträgt Mundart ins Hochdeutsche, setzt Satzzeichen und entfernt Füllwörter. Ausgabe wahlweise als
  - korrigierter Text,
  - fertige E-Mail mit Betreff,
  - Schreiben bzw. Brief zum Ausdrucken oder Versenden,
  - sauber strukturierter KI-Prompt,
  - Stichpunkt-Notiz,
  - oder Rohtext ohne Bearbeitung.
- **Natürlicher Ton** – keine Floskeln wie „Ich hoffe, es geht Ihnen gut“ oder „Zögern Sie nicht …“, keine Modewörter, keine aufgeblähten Sätze. Der Text soll klingen, als hätte man ihn selbst getippt.
- **Fachbereiche Bau und Wohnungswirtschaft** – Fachbegriffe werden richtig erkannt und geschrieben (Bedenkenanmeldung, Behinderungsanzeige, Aufmaß, Nachtrag, Betriebskostenabrechnung, Mieterhöhungsverlangen, Hausgeld usw.). Der rechtliche Rahmen aus VOB/B, BGB (Bauvertrags- und Mietrecht), WEG, einschlägigen DIN-Normen und der DSGVO ist hinterlegt.
- **Hinweise zu Form, Fristen und Datenschutz** – erscheinen getrennt unter dem Ergebnis und landen nicht im Export. Beispiele: „Kündigung nach § 568 BGB nur schriftlich, E-Mail reicht nicht“, „Bedenken nach § 4 Abs. 3 VOB/B unverzüglich schriftlich anmelden“, „Gesundheitsdaten des Mieters nur weitergeben, wenn nötig“. Fehlende Angaben wie Fristen oder Objektadresse werden als Platzhalter in eckigen Klammern markiert statt erfunden.
- **Eigene Begriffe** – Namen, Fachwörter und Firmennamen hinterlegen, damit sie richtig geschrieben werden.
- **Export** – Word (.docx), PDF, TXT, Markdown, direkt als E-Mail, Teilen-Menü des Handys oder Zwischenablage.
- **Verlauf** – die letzten 50 Ergebnisse bleiben auf dem Gerät gespeichert.
- **Installierbar** – lässt sich über „Zum Startbildschirm hinzufügen“ wie eine normale App ablegen.

## Ausprobieren

Die App besteht nur aus statischen Dateien, ein Server-Backend ist nicht nötig. Für das Mikrofon verlangen Browser eine HTTPS-Adresse.

**Variante A – GitHub Pages (empfohlen fürs Handy)**

1. Im Repository auf *Settings → Pages* gehen.
2. Unter *Build and deployment* als Quelle „Deploy from a branch“ wählen, den Branch `claude/speech-to-text-dialect-app-rqdq7v` (bzw. später `main`) und den Ordner `/ (root)` auswählen, speichern.
3. Nach ein bis zwei Minuten ist die App unter `https://<benutzername>.github.io/Scanner-/` erreichbar.
4. Die Adresse auf dem Handy in Chrome (Android) oder Safari (iPhone) öffnen, Mikrofon erlauben, optional zum Startbildschirm hinzufügen.

**Variante B – lokal am Rechner**

```bash
python3 -m http.server 8000
```

Dann `http://localhost:8000` im Browser öffnen.

## Einrichtung in der App (⚙️)

| Einstellung | Wofür |
|---|---|
| Spracherkennung | „Browser“ für kostenlos und schnell, „Whisper / GPT-Transcribe“ für Dialekt |
| OpenAI API-Schlüssel | nur für Whisper nötig – erhältlich unter platform.openai.com |
| Anthropic API-Schlüssel | für die Aufbereitung mit Claude – erhältlich unter console.anthropic.com |
| Modell | Opus 5.5 für beste Qualität, Haiku 5.5 für maximale Geschwindigkeit |
| Automatisch aufbereiten | Ergebnis erscheint direkt nach dem Sprechen |
| Eigene Begriffe | Namen und Fachbegriffe, die oft falsch erkannt werden |
| Grußformel | wird bei E-Mails als Abschluss verwendet |

Ohne Schlüssel funktioniert die App auch – dann mit der Browser-Erkennung und einer einfachen Bereinigung ohne KI.

**Für Bau- und Verwaltungsschreiben:** Fachbereich auswählen, Ausgabe „Schreiben / Brief“ oder „E-Mail“. Die Hinweise unter dem Ergebnis kurz prüfen, Platzhalter in eckigen Klammern ausfüllen. Die Hinweise sind eine Gedächtnisstütze und ersetzen keine Rechtsberatung.

**Empfehlung bei starkem Dialekt:** Whisper / GPT-Transcribe als Erkennung, Dialekt auswählen, Ausgabe „Text korrigieren“ oder „E-Mail“. Die Kombination aus guter Erkennung und anschließender Korrektur im Zusammenhang bringt den größten Unterschied.

## Datenschutz

- Schlüssel, Einstellungen und Verlauf liegen ausschließlich im Browserspeicher des jeweiligen Geräts.
- Audio und Text gehen direkt vom Gerät an den gewählten Anbieter (Google/Apple bei der Browser-Erkennung, OpenAI bei Whisper, Anthropic bei der Aufbereitung). Es gibt keinen eigenen Server dazwischen.
- Der Prototyp ist für den persönlichen Gebrauch gedacht. Für eine Veröffentlichung sollten die API-Schlüssel nicht im Browser liegen, sondern über ein kleines eigenes Backend laufen.

## Vergleichbare Apps

Zur Orientierung: Wispr Flow, Superwhisper und Aqua Voice verfolgen einen ähnlichen Ansatz (Diktat plus KI-Glättung). Die Diktierfunktionen von Gboard, iOS und Microsoft Word erkennen zwar live, bereiten den Text aber nicht auf und tun sich mit Mundart schwer.

## Aufbau

```
index.html            Oberfläche
styles.css            Gestaltung (hell/dunkel)
app.js                Aufnahme, Erkennung, Aufbereitung, Export, Verlauf
sw.js                 Offline-Cache
manifest.webmanifest  Installation als App
vendor/               mitgelieferte Bibliotheken (Anthropic SDK, docx, jsPDF)
```

## Ideen für die nächste Version

- Native App (z. B. mit Capacitor) mit systemweiter Diktier-Tastatur
- Erkennung komplett auf dem Gerät (Whisper lokal) für Offline-Betrieb
- Sprachbefehle („an Max schicken“, „als Aufgabe speichern“)
- Eigenes kleines Backend, damit keine Schlüssel im Browser liegen
