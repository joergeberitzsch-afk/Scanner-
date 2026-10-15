"""Erzeugt den Aushang muellplan_oelknitz_2026.pdf aus termine.csv."""
import csv
import datetime as dt
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HIER = Path(__file__).parent
TONNEN = {
    "schwarz": ("Schwarze Tonne", "Restmüll", HexColor("#2b2b2b"), white),
    "blau": ("Blaue Tonne", "Papier & Pappe", HexColor("#1f6fd1"), white),
    "gelb": ("Gelbe Tonne", "Verpackungen", HexColor("#f5c400"), HexColor("#2b2b2b")),
}
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
GRAU = HexColor("#6b6b6b")
LINIE = HexColor("#d9d9d9")
MONAT_BG = HexColor("#eef2f6")

zeilen = [z for z in open(HIER / "termine.csv", encoding="utf-8") if z.strip() and not z.startswith("#")]
termine = [(dt.date.fromisoformat(r["datum"]), r["tonne"]) for r in csv.DictReader(zeilen)]

c = canvas.Canvas(str(HIER / "muellplan_oelknitz_2026.pdf"), pagesize=A4)
c.setTitle("Müllabfuhr Oelknitz 2026")
B, H = A4
rand = 18 * mm

# Kopf
c.setFont("Helvetica-Bold", 30)
c.drawString(rand, H - 30 * mm, "Müllabfuhr Oelknitz")
c.setFont("Helvetica", 14)
c.setFillColor(GRAU)
c.drawString(rand, H - 39 * mm, "Dorfanger 18  ·  Oktober bis Dezember 2026")
c.setFillColor(HexColor("#2b2b2b"))
c.setFont("Helvetica-Bold", 13)
c.drawString(rand, H - 49 * mm, "Tonne immer am Vorabend rausstellen!")

# Legende
x = rand
for name, inhalt, farbe, schrift in TONNEN.values():
    c.setFillColor(farbe)
    c.roundRect(x, H - 64 * mm, 56 * mm, 10 * mm, 2.5 * mm, fill=1, stroke=0)
    c.setFillColor(schrift)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + 4 * mm, H - 58.2 * mm, name)
    c.setFont("Helvetica", 9)
    c.drawString(x + 4 * mm, H - 62.3 * mm, inhalt)
    x += 59 * mm

# Tabelle
spalten = [rand, rand + 62 * mm, rand + 124 * mm]
y = H - 76 * mm
c.setFillColor(GRAU)
c.setFont("Helvetica-Bold", 10)
for sx, t in zip(spalten, ["ABHOLUNG", "TONNE", "RAUSSTELLEN AM"]):
    c.drawString(sx + 3 * mm, y, t)
y -= 4 * mm
zeile_h = 9.4 * mm
monat = None
for d, t in termine:
    if d.month != monat:
        monat = d.month
        c.setFillColor(MONAT_BG)
        c.rect(rand, y - 7 * mm, B - 2 * rand, 7 * mm, fill=1, stroke=0)
        c.setFillColor(HexColor("#2b2b2b"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(rand + 3 * mm, y - 5 * mm, MONATE[d.month].upper())
        y -= 7 * mm
    name, _, farbe, schrift = TONNEN[t]
    mitte = y - zeile_h / 2
    c.setFillColor(HexColor("#2b2b2b"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(spalten[0] + 3 * mm, mitte - 1.8 * mm, f"{TAGE[d.weekday()][:2]}  {d:%d.%m.}")
    c.setFillColor(farbe)
    c.roundRect(spalten[1], mitte - 3.6 * mm, 54 * mm, 7.2 * mm, 3.6 * mm, fill=1, stroke=0)
    c.setFillColor(schrift)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(spalten[1] + 27 * mm, mitte - 1.6 * mm, name)
    vortag = d - dt.timedelta(days=1)
    c.setFillColor(GRAU)
    c.setFont("Helvetica", 12)
    c.drawString(spalten[2] + 3 * mm, mitte - 1.6 * mm, f"{TAGE[vortag.weekday()]}, {vortag:%d.%m.} abends")
    y -= zeile_h
    c.setStrokeColor(LINIE)
    c.setLineWidth(0.5)
    c.line(rand, y, B - rand, y)

# Fußzeile
c.setFillColor(GRAU)
c.setFont("Helvetica", 9)
c.drawString(rand, 16 * mm, "Schadstoffmobil: Freitag, 30.10.2026, 13:35 – 13:55 Uhr, Wertstoffcontainerplatz Oelknitz")
c.drawString(rand, 11.5 * mm, "Grundlage: Abfallkalender Saale-Holzland-Kreis 2026. Kurzfristige Änderungen unter www.saaleholzlandkreis.de")
c.save()
