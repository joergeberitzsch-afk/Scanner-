# A8-Umzug – Stand der SMB-Gegenprobe

Stand: 28.09.2026

## Ziel

Der Mini-PC A8 (`A8_Max`) soll als Server dienen. Letzter offener Punkt: der alte PC `EBERITZSCH` (192.168.178.28) soll die Freigabe `\\192.168.178.78\A8-Daten` lesend öffnen und `Liesmich.txt` anzeigen können.

## Befund alter PC (27.09.2026)

- TCP-Port 445 auf 192.168.178.78 erreichbar
- Lesezugriff auf `Liesmich.txt`: „Zugriff verweigert“
- `net use` mit `A8_MAX\joerg`: Systemfehler 67 (Netzwerkname nicht gefunden)
- `net view \\192.168.178.78`: Systemfehler 53
- `A8-Max.fritz.box` löst auf .78 und .79 auf; .79 ist nicht erreichbar (vermutlich veralteter Eintrag)

## Befund A8 (28.09.2026) – alles unauffällig

| Prüfung | Ergebnis |
|---|---|
| Rechnername | `A8_Max` |
| IPv4 | 192.168.178.78 (WLAN) |
| Netzwerkprofil | Privat |
| Dienst LanmanServer | läuft, Autostart |
| Freigabe `A8-Daten` | vorhanden, Pfad `C:\Users\joerg\A8-Daten`, EncryptData = True |
| Freigaberechte | `A8_MAX\joerg` Read, `A8_MAX\a8leser` Read |
| SMB2 | aktiv; RejectUnencryptedAccess = True |
| Datei- und Druckerfreigabe am WLAN-Adapter | aktiv |
| SmbServerNameHardeningLevel | 0 (Zugriff per IP erlaubt) |
| SMB-Schnittstellen | u. a. 192.168.178.78; 172.22.96.1 = WSL/Docker-intern |

Noch nicht abgelesen: Ergebnis der drei `Test-Path`-Zeilen (Datei vorhanden / lokaler Test / Test über IP). Die Ausgabe steht im Admin-Terminal weiter oben.

## Nächste Schritte

1. Am A8 im Terminal hochscrollen und die drei `Test-Path`-Ergebnisse ablesen (erwartet: dreimal `True`).
2. Am alten PC in `cmd` (nicht PowerShell) nacheinander:
   ```
   net use
   cmdkey /list | findstr 192.168.178
   ```
   Falls hier schon eine Verbindung oder gespeicherte Anmeldedaten zu .78 auftauchen: erst melden, nichts löschen.
3. Danach:
   ```
   net use \\192.168.178.78\A8-Daten /user:A8_MAX\joerg
   type \\192.168.178.78\A8-Daten\Liesmich.txt
   ```
   Kennwort selbst eingeben, nirgends notieren. Pfad ohne abschließenden Backslash und ohne Anführungszeichen.
4. Ergebnis bzw. Fehlermeldung festhalten.

## Rahmenbedingungen

- Keine Schreib- oder Löschversuche auf der Freigabe.
- Alte Ubuntu-/Docker-/Paperless-/n8n-Umgebung auf dem alten PC bleibt gestoppt.
- Keine Kennwörter in Dateien oder Chats.
- Die A8-Weboberflächen sind nicht Teil dieser Prüfung.
