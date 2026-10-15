#!/usr/bin/env python3
"""Gibt die Erinnerung für die Tonnen aus, die morgen abgeholt werden.

Aufruf: python3 muell_erinnerung.py [termine.csv] [--datum JJJJ-MM-TT]
Ohne Abholung am Folgetag erfolgt keine Ausgabe (Exit-Code 0).
"""
import argparse
import csv
import datetime as dt
from pathlib import Path

TONNEN = {
    "schwarz": "⚫ schwarze Tonne (Restabfall)",
    "blau": "🔵 blaue Tonne (Papier)",
    "gelb": "🟡 gelbe Tonne (Verpackungen)",
}
SCHADSTOFF = "☣️ Schadstoffmobil: 13:35 – 13:55 Uhr am Wertstoffcontainerplatz Oelknitz"


def lade_termine(pfad):
    termine = {}
    with open(pfad, newline="", encoding="utf-8") as f:
        zeilen = (z for z in f if z.strip() and not z.lstrip().startswith("#"))
        for eintrag in csv.DictReader(zeilen):
            tonne = eintrag["tonne"].strip().lower()
            if tonne not in TONNEN and tonne != "schadstoff":
                raise ValueError(f"Unbekannte Tonne '{tonne}' am {eintrag['datum']}")
            tag = dt.date.fromisoformat(eintrag["datum"].strip())
            termine.setdefault(tag, []).append(tonne)
    return termine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", nargs="?", default=Path(__file__).with_name("termine.csv"))
    parser.add_argument("--datum", help="Bezugstag (Standard: heute)")
    args = parser.parse_args()

    heute = dt.date.fromisoformat(args.datum) if args.datum else dt.date.today()
    morgen = heute + dt.timedelta(days=1)
    tonnen = lade_termine(args.csv).get(morgen)
    if not tonnen:
        return
    teile = []
    tonnen_morgen = [t for t in TONNEN if t in tonnen]
    if tonnen_morgen:
        liste = "\n".join(f"• {TONNEN[t]}" for t in tonnen_morgen)
        teile.append(f"Bitte heute Abend rausstellen – Abholung morgen, {morgen:%d.%m.%Y}:\n{liste}")
    if "schadstoff" in tonnen:
        teile.append(f"Morgen, {morgen:%d.%m.%Y}, kommt das {SCHADSTOFF}")
    print("\n\n".join(teile))


if __name__ == "__main__":
    main()
