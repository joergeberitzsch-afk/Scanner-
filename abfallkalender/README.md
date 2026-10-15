# Müll-Erinnerung Oelknitz, Dorfanger 18

Erinnerung per WhatsApp jeweils am Vorabend einer Abholung um 18:00 Uhr,
für die schwarze, blaue und gelbe Tonne.

## Schnellstart

- **Hermes/WhatsApp:** Den Text aus `hermes_auftrag.txt` komplett an Hermes schicken. Fertig.
- **Handy-Kalender:** `muellabfuhr_oelknitz_2026.ics` öffnen und importieren. Jeder Termin erinnert am Vortag um 18:00 Uhr.

Oelknitz laut Tourenplan Landkreis 2026: Restmüll Montag (ungerade KW), blaue Tonne
Donnerstag (ungerade KW), gelbe Tonne Donnerstag (gerade KW).

## 1. Termine eintragen

Die Abholtermine stehen im offiziellen Abfallkalender des Saale-Holzland-Kreises
(Veolia): <https://www.veolia.de/abfuhrkalender> bzw. das PDF
„ABFALLKALENDER_SaaleHolzLandkreis_2026.pdf“. Dort Oelknitz heraussuchen und
jede Abholung als eigene Zeile in `termine.csv` eintragen:

```
datum,tonne
2026-10-20,schwarz
2026-10-27,blau
```

Zulässige Werte für `tonne`: `schwarz`, `blau`, `gelb`.

## 2. Testen

```
python3 muell_erinnerung.py --datum 2026-10-19
```

Gibt den Erinnerungstext aus, falls am Folgetag eine Abholung ansteht.
Sonst erfolgt keine Ausgabe.

## 3. Hermes-Cronjob anlegen

Voraussetzung: Hermes läuft mit eingerichtetem WhatsApp-Gateway, und dieser
Ordner liegt auf dem Rechner, auf dem Hermes läuft. Den Job in Hermes (Chat
oder `hermes cron`) etwa so anlegen:

> Jeden Tag um 18:00 Uhr (Europe/Berlin): Führe
> `python3 /PFAD/ZU/abfallkalender/muell_erinnerung.py` aus. Ist die Ausgabe
> nicht leer, schicke sie mir unverändert per WhatsApp. Ist sie leer, schicke
> nichts.

Wichtig ist die Zeitzone Europe/Berlin, damit die Erinnerung auch nach der
Zeitumstellung um 18:00 Uhr Ortszeit ankommt.

## Hinweise

- Verschobene Termine (z. B. rund um Feiertage) kündigt der Landkreis auf
  www.saaleholzlandkreis.de unter „Abfallwirtschaft“ an. Änderungen bitte in
  `termine.csv` nachtragen.
- Zum Jahreswechsel die Termine für 2027 ergänzen.
