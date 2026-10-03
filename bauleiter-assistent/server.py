#!/usr/bin/env python3
"""Bauleiter-Assistent – lokaler Webserver.

Start:   python server.py            (Einstellungen aus config.json)
Prüfen:  python server.py --pruefen  (Python-Version, Port, Datenordner)

Läuft ausschließlich mit der Python-Standardbibliothek (ab Python 3.8).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import logging
import logging.handlers
import os
import re
import socket
import sqlite3
import sys
import threading
import urllib.parse
import urllib.request
import uuid
import webbrowser
import zipfile
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "Bauleiter-Assistent"
VERSION = "1.1-test"
MIN_PYTHON = (3, 8)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 8788,
    "datenordner": "daten_test",
    "sicherungsordner": "sicherungen",
    "logordner": "logs",
    "sicherungen_behalten": 20,
    "max_upload_mb": 200,
    "browser_oeffnen": True,
}

DEFAULT_EINSTELLUNGEN = {
    "projekt_name": "",
    "projekt_nr": "",
    "bauherr": "",
    "adresse": "",
    "bauleiter": "",
    "gewerke": "Rohbau, Elektro, Sanitär, Heizung, Lüftung, Trockenbau, Estrich, "
    "Fliesen, Maler, Bodenbelag, Fenster, Dach, Außenanlagen",
}

MANGEL_STATUS = {"offen": "offen", "in_arbeit": "in Arbeit", "erledigt": "erledigt"}

PLAN_TYPEN = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
FOTO_TYPEN = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

log = logging.getLogger("bauleiter")


# --------------------------------------------------------------------------
# Konfiguration, Protokoll, Sicherung
# --------------------------------------------------------------------------


def lade_konfiguration(pfad: Path) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if pfad.exists():
        with open(pfad, encoding="utf-8") as f:
            daten = json.load(f)
        cfg.update({k: v for k, v in daten.items() if not k.startswith("_")})
    for schluessel in ("datenordner", "sicherungsordner", "logordner"):
        p = Path(cfg[schluessel])
        cfg[schluessel] = p if p.is_absolute() else (pfad.parent / p)
    cfg["port"] = int(cfg["port"])
    return cfg


def protokoll_einrichten(logordner: Path) -> Path:
    logordner.mkdir(parents=True, exist_ok=True)
    datei = logordner / "server.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    datei_handler = logging.handlers.RotatingFileHandler(
        datei, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    datei_handler.setFormatter(fmt)
    konsole = logging.StreamHandler()
    konsole.setFormatter(fmt)
    log.handlers[:] = [datei_handler, konsole]
    log.setLevel(logging.INFO)
    return datei


def sicherung_anlegen(datenordner: Path, zielordner: Path, behalten: int) -> Path | None:
    """Packt den Datenordner in eine datierte ZIP-Datei und räumt alte Sicherungen auf."""
    if not datenordner.exists() or not any(datenordner.rglob("*")):
        return None
    zielordner.mkdir(parents=True, exist_ok=True)
    stempel = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    ziel = zielordner / f"daten_{stempel}.zip"
    n = 1
    while ziel.exists():
        ziel = zielordner / f"daten_{stempel}_{n}.zip"
        n += 1
    tmp = ziel.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w") as zf:
        for datei in sorted(datenordner.rglob("*")):
            if datei.is_file():
                # Bilder und PDFs sind bereits komprimiert
                art = zipfile.ZIP_STORED if datei.suffix.lower() in PLAN_TYPEN or datei.suffix.lower() in FOTO_TYPEN else zipfile.ZIP_DEFLATED
                zf.write(datei, datei.relative_to(datenordner).as_posix(), compress_type=art)
    tmp.replace(ziel)
    alte = sorted(zielordner.glob("daten_*.zip"))
    for datei in alte[: max(0, len(alte) - max(1, behalten))]:
        datei.unlink()
    return ziel


def letzte_sicherung(zielordner: Path) -> str:
    dateien = sorted(zielordner.glob("daten_*.zip")) if zielordner.exists() else []
    return dateien[-1].name if dateien else ""


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

_GESCHOSS_TOKEN = re.compile(r"(?:UG|KG|TG)\d?|EG|OG\d{1,2}|DG")


def geschoss_aus_dateiname(name: str) -> str:
    """'A_GR_OG5_ST3_NB.pdf' -> 'OG5', 'Grundriss 1.OG.pdf' -> 'OG1'."""
    teile = [t for t in re.split(r"[^A-Z0-9]+", Path(name).stem.upper()) if t]
    for i, t in enumerate(teile):
        if _GESCHOSS_TOKEN.fullmatch(t):
            return t
        if t == "OG" and i > 0 and teile[i - 1].isdigit():
            return "OG" + str(int(teile[i - 1]))
        m = re.fullmatch(r"(\d{1,2})OG", t)
        if m:
            return "OG" + str(int(m.group(1)))
    return ""


def geschoss_rang(geschoss: str) -> float:
    g = (geschoss or "").strip().upper()
    if not g:
        return 1000
    m = re.fullmatch(r"(UG|KG|TG)(\d?)", g)
    if m:
        return -int(m.group(2) or 1) - (0.5 if m.group(1) == "TG" else 0)
    if g == "EG":
        return 0
    m = re.fullmatch(r"OG(\d{1,2})", g)
    if m:
        return int(m.group(1))
    if g == "DG":
        return 99
    return 500


def datum_aus_dateiname(name: str) -> str:
    """'20260912_090810_65b56d76.jpg' -> '2026-09-12'."""
    for muster in (r"(20\d{2})(\d{2})(\d{2})[_\-T ]?\d{4,6}", r"(20\d{2})-(\d{2})-(\d{2})", r"(20\d{2})(\d{2})(\d{2})"):
        m = re.search(muster, name)
        if m:
            try:
                return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
            except ValueError:
                continue
    return ""


def heute() -> str:
    return dt.date.today().isoformat()


def jetzt() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def pruefe_datum(wert, feld: str, pflicht: bool = False) -> str:
    wert = (wert or "").strip() if isinstance(wert, str) else wert
    if not wert:
        if pflicht:
            raise ApiFehler(400, f"{feld}: Datum fehlt")
        return ""
    try:
        return dt.date.fromisoformat(str(wert)).isoformat()
    except ValueError:
        raise ApiFehler(400, f"{feld}: ungültiges Datum '{wert}' (erwartet JJJJ-MM-TT)")


def pruefe_koordinate(wert, feld: str):
    if wert is None or wert == "":
        return None
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        raise ApiFehler(400, f"{feld}: keine Zahl")
    if not 0 <= zahl <= 1:
        raise ApiFehler(400, f"{feld}: muss zwischen 0 und 1 liegen")
    return zahl


def pruefe_id(wert, feld: str):
    if wert is None or wert == "":
        return None
    try:
        return int(wert)
    except (TypeError, ValueError):
        raise ApiFehler(400, f"{feld}: ungültige Nummer")


def text(wert, max_len: int = 10000) -> str:
    if wert is None:
        return ""
    return str(wert).strip()[:max_len]


def dateityp_passt(endung: str, kopf: bytes) -> bool:
    if endung == ".pdf":
        return kopf.startswith(b"%PDF")
    if endung in (".jpg", ".jpeg"):
        return kopf.startswith(b"\xff\xd8")
    if endung == ".png":
        return kopf.startswith(b"\x89PNG")
    if endung == ".webp":
        return kopf[:4] == b"RIFF" and kopf[8:12] == b"WEBP"
    if endung == ".gif":
        return kopf.startswith(b"GIF8")
    return False


class ApiFehler(Exception):
    def __init__(self, status: int, meldung: str):
        super().__init__(meldung)
        self.status = status
        self.meldung = meldung


# --------------------------------------------------------------------------
# Datenhaltung
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS plaene (
    id INTEGER PRIMARY KEY,
    bezeichnung TEXT NOT NULL DEFAULT '',
    geschoss TEXT NOT NULL DEFAULT '',
    dateiname TEXT NOT NULL,
    datei TEXT NOT NULL,
    groesse INTEGER NOT NULL DEFAULT 0,
    hochgeladen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS maengel (
    id INTEGER PRIMARY KEY,
    nr INTEGER NOT NULL,
    titel TEXT NOT NULL,
    beschreibung TEXT NOT NULL DEFAULT '',
    geschoss TEXT NOT NULL DEFAULT '',
    ort TEXT NOT NULL DEFAULT '',
    gewerk TEXT NOT NULL DEFAULT '',
    firma TEXT NOT NULL DEFAULT '',
    frist TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'offen',
    plan_id INTEGER,
    x REAL,
    y REAL,
    erstellt TEXT NOT NULL,
    erledigt_am TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS fotos (
    id INTEGER PRIMARY KEY,
    dateiname TEXT NOT NULL,
    datei TEXT NOT NULL,
    groesse INTEGER NOT NULL DEFAULT 0,
    datum TEXT NOT NULL,
    notiz TEXT NOT NULL DEFAULT '',
    geschoss TEXT NOT NULL DEFAULT '',
    plan_id INTEGER,
    x REAL,
    y REAL,
    mangel_id INTEGER,
    hochgeladen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tagebuch (
    datum TEXT PRIMARY KEY,
    wetter TEXT NOT NULL DEFAULT '',
    temperatur TEXT NOT NULL DEFAULT '',
    arbeitszeit TEXT NOT NULL DEFAULT '',
    personal TEXT NOT NULL DEFAULT '[]',
    leistungen TEXT NOT NULL DEFAULT '',
    behinderungen TEXT NOT NULL DEFAULT '',
    vorkommnisse TEXT NOT NULL DEFAULT '',
    anordnungen TEXT NOT NULL DEFAULT '',
    besucher TEXT NOT NULL DEFAULT '',
    geaendert TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS fotos_datum ON fotos(datum);
CREATE INDEX IF NOT EXISTS fotos_plan ON fotos(plan_id);
CREATE INDEX IF NOT EXISTS maengel_plan ON maengel(plan_id);
"""

TAGEBUCH_TEXTFELDER = (
    "wetter", "temperatur", "arbeitszeit", "leistungen",
    "behinderungen", "vorkommnisse", "anordnungen", "besucher",
)


class Datenbank:
    def __init__(self, datenordner: Path):
        self.ordner = datenordner
        self.plan_ordner = datenordner / "dateien" / "plaene"
        self.foto_ordner = datenordner / "dateien" / "fotos"
        for p in (self.plan_ordner, self.foto_ordner):
            p.mkdir(parents=True, exist_ok=True)
        self.pfad = datenordner / "bauleiter.db"
        with closing(self.verbinden()) as con, con:
            con.executescript(SCHEMA)
            con.execute("PRAGMA user_version = 1")
            for k, v in DEFAULT_EINSTELLUNGEN.items():
                con.execute("INSERT OR IGNORE INTO einstellungen VALUES (?, ?)", (k, v))

    def verbinden(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.pfad), timeout=15)
        con.row_factory = sqlite3.Row
        return con

    def abfrage(self, sql: str, params=()) -> list:
        with closing(self.verbinden()) as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def eins(self, sql: str, params=()):
        zeilen = self.abfrage(sql, params)
        return zeilen[0] if zeilen else None

    # -- Einstellungen ------------------------------------------------------

    def einstellungen(self) -> dict:
        werte = dict(DEFAULT_EINSTELLUNGEN)
        werte.update({r["schluessel"]: r["wert"] for r in self.abfrage("SELECT * FROM einstellungen")})
        return werte

    def einstellungen_speichern(self, daten: dict) -> dict:
        with closing(self.verbinden()) as con, con:
            for k in DEFAULT_EINSTELLUNGEN:
                if k in daten:
                    con.execute(
                        "INSERT INTO einstellungen VALUES (?, ?) "
                        "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
                        (k, text(daten[k], 2000)),
                    )
        return self.einstellungen()

    # -- Dateien ------------------------------------------------------------

    def datei_speichern(self, ordner: Path, endung: str, quelle, laenge: int, max_bytes: int) -> tuple:
        if laenge > max_bytes:
            raise ApiFehler(413, f"Datei zu groß (max. {max_bytes // 1_000_000} MB)")
        name = uuid.uuid4().hex + endung
        ziel = ordner / name
        tmp = ordner / (name + ".tmp")
        rest = laenge
        kopf = b""
        try:
            with open(tmp, "wb") as f:
                while rest > 0:
                    block = quelle.read(min(rest, 1 << 20))
                    if not block:
                        raise ApiFehler(400, "Upload unvollständig")
                    if len(kopf) < 16:
                        kopf += block[: 16 - len(kopf)]
                    f.write(block)
                    rest -= len(block)
            if not dateityp_passt(endung, kopf):
                raise ApiFehler(400, "Dateiinhalt passt nicht zur Endung " + endung)
            tmp.replace(ziel)
        finally:
            if tmp.exists():
                tmp.unlink()
        return name, laenge

    # -- Pläne --------------------------------------------------------------

    def plaene(self) -> list:
        zeilen = self.abfrage(
            "SELECT p.*, "
            "(SELECT COUNT(*) FROM fotos f WHERE f.plan_id = p.id AND f.x IS NOT NULL) AS anzahl_fotos, "
            "(SELECT COUNT(*) FROM maengel m WHERE m.plan_id = p.id AND m.x IS NOT NULL) AS anzahl_maengel "
            "FROM plaene p"
        )
        zeilen.sort(key=lambda p: (geschoss_rang(p["geschoss"]), p["bezeichnung"].lower(), p["id"]))
        return zeilen

    def plan(self, plan_id: int) -> dict:
        p = self.eins("SELECT * FROM plaene WHERE id = ?", (plan_id,))
        if not p:
            raise ApiFehler(404, "Plan nicht gefunden")
        return p

    def plan_anlegen(self, dateiname: str, datei: str, groesse: int) -> dict:
        with closing(self.verbinden()) as con, con:
            cur = con.execute(
                "INSERT INTO plaene (bezeichnung, geschoss, dateiname, datei, groesse, hochgeladen) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (Path(dateiname).stem, geschoss_aus_dateiname(dateiname), dateiname, datei, groesse, jetzt()),
            )
            neu = cur.lastrowid
        return self.plan(neu)

    def plan_aendern(self, plan_id: int, daten: dict) -> dict:
        self.plan(plan_id)
        felder = {k: text(daten[k], 200) for k in ("bezeichnung", "geschoss") if k in daten}
        if "geschoss" in felder:
            felder["geschoss"] = felder["geschoss"].upper()
        if felder:
            with closing(self.verbinden()) as con, con:
                con.execute(
                    "UPDATE plaene SET " + ", ".join(f"{k} = ?" for k in felder) + " WHERE id = ?",
                    (*felder.values(), plan_id),
                )
        return self.plan(plan_id)

    def plan_loeschen(self, plan_id: int) -> None:
        p = self.plan(plan_id)
        with closing(self.verbinden()) as con, con:
            con.execute("UPDATE fotos SET plan_id = NULL, x = NULL, y = NULL WHERE plan_id = ?", (plan_id,))
            con.execute("UPDATE maengel SET plan_id = NULL, x = NULL, y = NULL WHERE plan_id = ?", (plan_id,))
            con.execute("DELETE FROM plaene WHERE id = ?", (plan_id,))
        (self.plan_ordner / p["datei"]).unlink(missing_ok=True)

    def markierungen(self, plan_id: int) -> dict:
        self.plan(plan_id)
        return {
            "fotos": self.abfrage(
                "SELECT id, dateiname, datum, notiz, x, y, mangel_id FROM fotos "
                "WHERE plan_id = ? AND x IS NOT NULL ORDER BY id", (plan_id,)),
            "maengel": self.abfrage(
                "SELECT id, nr, titel, status, frist, gewerk, x, y FROM maengel "
                "WHERE plan_id = ? AND x IS NOT NULL ORDER BY nr", (plan_id,)),
        }

    # -- Fotos --------------------------------------------------------------

    def fotos(self, filter_: dict) -> list:
        sql = "SELECT * FROM fotos WHERE 1 = 1"
        params = []
        for feld in ("datum", "geschoss"):
            if filter_.get(feld):
                sql += f" AND {feld} = ?"
                params.append(filter_[feld])
        for feld in ("plan_id", "mangel_id"):
            if filter_.get(feld):
                sql += f" AND {feld} = ?"
                params.append(pruefe_id(filter_[feld], feld))
        if filter_.get("von"):
            sql += " AND datum >= ?"
            params.append(filter_["von"])
        if filter_.get("bis"):
            sql += " AND datum <= ?"
            params.append(filter_["bis"])
        sql += " ORDER BY datum DESC, id DESC"
        if filter_.get("limit"):
            sql += " LIMIT ?"
            params.append(pruefe_id(filter_["limit"], "limit"))
        return self.abfrage(sql, params)

    def foto(self, foto_id: int) -> dict:
        f = self.eins("SELECT * FROM fotos WHERE id = ?", (foto_id,))
        if not f:
            raise ApiFehler(404, "Foto nicht gefunden")
        return f

    def foto_anlegen(self, dateiname: str, datei: str, groesse: int, daten: dict) -> dict:
        datum = pruefe_datum(daten.get("datum"), "datum") or datum_aus_dateiname(dateiname) or heute()
        mangel_id = pruefe_id(daten.get("mangel_id"), "mangel_id")
        if mangel_id:
            self.mangel(mangel_id)
        with closing(self.verbinden()) as con, con:
            cur = con.execute(
                "INSERT INTO fotos (dateiname, datei, groesse, datum, notiz, geschoss, mangel_id, hochgeladen) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (dateiname, datei, groesse, datum, text(daten.get("notiz")),
                 text(daten.get("geschoss"), 20).upper(), mangel_id, jetzt()),
            )
            neu = cur.lastrowid
        return self.foto(neu)

    def foto_aendern(self, foto_id: int, daten: dict) -> dict:
        self.foto(foto_id)
        felder = {}
        if "datum" in daten:
            felder["datum"] = pruefe_datum(daten["datum"], "datum", pflicht=True)
        if "notiz" in daten:
            felder["notiz"] = text(daten["notiz"])
        if "geschoss" in daten:
            felder["geschoss"] = text(daten["geschoss"], 20).upper()
        if "mangel_id" in daten:
            felder["mangel_id"] = pruefe_id(daten["mangel_id"], "mangel_id")
            if felder["mangel_id"]:
                self.mangel(felder["mangel_id"])
        felder.update(self._markierung(daten))
        if felder:
            with closing(self.verbinden()) as con, con:
                con.execute(
                    "UPDATE fotos SET " + ", ".join(f"{k} = ?" for k in felder) + " WHERE id = ?",
                    (*felder.values(), foto_id),
                )
        return self.foto(foto_id)

    def foto_loeschen(self, foto_id: int) -> None:
        f = self.foto(foto_id)
        with closing(self.verbinden()) as con, con:
            con.execute("DELETE FROM fotos WHERE id = ?", (foto_id,))
        (self.foto_ordner / f["datei"]).unlink(missing_ok=True)

    def _markierung(self, daten: dict) -> dict:
        """plan_id/x/y gemeinsam prüfen; plan_id = null entfernt die Markierung."""
        if not any(k in daten for k in ("plan_id", "x", "y")):
            return {}
        plan_id = pruefe_id(daten.get("plan_id"), "plan_id")
        if plan_id is None:
            return {"plan_id": None, "x": None, "y": None}
        self.plan(plan_id)
        x = pruefe_koordinate(daten.get("x"), "x")
        y = pruefe_koordinate(daten.get("y"), "y")
        if (x is None) != (y is None):
            raise ApiFehler(400, "x und y nur gemeinsam angeben")
        return {"plan_id": plan_id, "x": x, "y": y}

    # -- Mängel -------------------------------------------------------------

    def maengel(self, filter_: dict) -> list:
        sql = (
            "SELECT m.*, p.bezeichnung AS plan_bezeichnung, "
            "(SELECT COUNT(*) FROM fotos f WHERE f.mangel_id = m.id) AS anzahl_fotos "
            "FROM maengel m LEFT JOIN plaene p ON p.id = m.plan_id WHERE 1 = 1"
        )
        params = []
        status = filter_.get("status")
        if status == "nicht_erledigt":
            sql += " AND m.status != 'erledigt'"
        elif status:
            sql += " AND m.status = ?"
            params.append(status)
        for feld in ("gewerk", "geschoss", "firma"):
            if filter_.get(feld):
                sql += f" AND m.{feld} = ?"
                params.append(filter_[feld])
        if filter_.get("q"):
            sql += " AND (m.titel LIKE ? OR m.beschreibung LIKE ? OR m.ort LIKE ? OR m.firma LIKE ?)"
            params += ["%" + filter_["q"] + "%"] * 4
        if filter_.get("ueberfaellig") in ("1", "true", True):
            sql += " AND m.status != 'erledigt' AND m.frist != '' AND m.frist < ?"
            params.append(heute())
        sql += " ORDER BY m.nr"
        zeilen = self.abfrage(sql, params)
        h = heute()
        for m in zeilen:
            m["ueberfaellig"] = bool(m["status"] != "erledigt" and m["frist"] and m["frist"] < h)
        return zeilen

    def mangel(self, mangel_id: int) -> dict:
        m = self.eins("SELECT * FROM maengel WHERE id = ?", (mangel_id,))
        if not m:
            raise ApiFehler(404, "Mangel nicht gefunden")
        m["ueberfaellig"] = bool(m["status"] != "erledigt" and m["frist"] and m["frist"] < heute())
        return m

    def _mangel_felder(self, daten: dict, neu: bool) -> dict:
        felder = {}
        if neu or "titel" in daten:
            felder["titel"] = text(daten.get("titel"), 300)
            if not felder["titel"]:
                raise ApiFehler(400, "Bitte eine Kurzbeschreibung (Titel) angeben")
        for k, laenge in (("beschreibung", 10000), ("ort", 200), ("gewerk", 100), ("firma", 200)):
            if k in daten:
                felder[k] = text(daten[k], laenge)
        if "geschoss" in daten:
            felder["geschoss"] = text(daten["geschoss"], 20).upper()
        if "frist" in daten:
            felder["frist"] = pruefe_datum(daten["frist"], "frist")
        if "status" in daten:
            if daten["status"] not in MANGEL_STATUS:
                raise ApiFehler(400, "Ungültiger Status")
            felder["status"] = daten["status"]
            felder["erledigt_am"] = heute() if daten["status"] == "erledigt" else ""
        felder.update(self._markierung(daten))
        return felder

    def mangel_anlegen(self, daten: dict) -> dict:
        felder = self._mangel_felder(daten, neu=True)
        felder.setdefault("status", "offen")
        with closing(self.verbinden()) as con, con:
            nr = con.execute("SELECT COALESCE(MAX(nr), 0) + 1 FROM maengel").fetchone()[0]
            felder.update({"nr": nr, "erstellt": jetzt()})
            cur = con.execute(
                f"INSERT INTO maengel ({', '.join(felder)}) VALUES ({', '.join('?' * len(felder))})",
                tuple(felder.values()),
            )
            neu = cur.lastrowid
        return self.mangel(neu)

    def mangel_aendern(self, mangel_id: int, daten: dict) -> dict:
        alt = self.mangel(mangel_id)
        felder = self._mangel_felder(daten, neu=False)
        if felder.get("status") == alt["status"]:
            felder.pop("erledigt_am", None)  # Erledigt-Datum nicht überschreiben
        if felder:
            with closing(self.verbinden()) as con, con:
                con.execute(
                    "UPDATE maengel SET " + ", ".join(f"{k} = ?" for k in felder) + " WHERE id = ?",
                    (*felder.values(), mangel_id),
                )
        return self.mangel(mangel_id)

    def mangel_loeschen(self, mangel_id: int) -> None:
        self.mangel(mangel_id)
        with closing(self.verbinden()) as con, con:
            con.execute("UPDATE fotos SET mangel_id = NULL WHERE mangel_id = ?", (mangel_id,))
            con.execute("DELETE FROM maengel WHERE id = ?", (mangel_id,))

    # -- Bautagebuch --------------------------------------------------------

    def tagebuch_liste(self) -> list:
        zeilen = self.abfrage(
            "SELECT t.datum, t.wetter, t.personal, "
            "(SELECT COUNT(*) FROM fotos f WHERE f.datum = t.datum) AS anzahl_fotos "
            "FROM tagebuch t ORDER BY t.datum DESC"
        )
        for z in zeilen:
            z["personal_summe"] = sum(int(p.get("anzahl") or 0) for p in json.loads(z.pop("personal") or "[]"))
        return zeilen

    def tagebuch(self, datum: str):
        datum = pruefe_datum(datum, "datum", pflicht=True)
        t = self.eins("SELECT * FROM tagebuch WHERE datum = ?", (datum,))
        if t:
            t["personal"] = json.loads(t["personal"] or "[]")
        return t

    def tagebuch_speichern(self, datum: str, daten: dict) -> dict:
        datum = pruefe_datum(datum, "datum", pflicht=True)
        personal = []
        for zeile in daten.get("personal") or []:
            if not isinstance(zeile, dict):
                raise ApiFehler(400, "personal: ungültiger Eintrag")
            firma, gewerk = text(zeile.get("firma"), 200), text(zeile.get("gewerk"), 100)
            try:
                anzahl = int(zeile.get("anzahl") or 0)
            except (TypeError, ValueError):
                raise ApiFehler(400, "personal: Anzahl muss eine ganze Zahl sein")
            if anzahl < 0:
                raise ApiFehler(400, "personal: Anzahl darf nicht negativ sein")
            if firma or gewerk or anzahl:
                personal.append({"firma": firma, "gewerk": gewerk, "anzahl": anzahl})
        werte = {k: text(daten.get(k)) for k in TAGEBUCH_TEXTFELDER}
        werte.update({"personal": json.dumps(personal, ensure_ascii=False), "geaendert": jetzt()})
        with closing(self.verbinden()) as con, con:
            con.execute(
                f"INSERT INTO tagebuch (datum, {', '.join(werte)}) VALUES (?, {', '.join('?' * len(werte))}) "
                f"ON CONFLICT(datum) DO UPDATE SET {', '.join(f'{k} = excluded.{k}' for k in werte)}",
                (datum, *werte.values()),
            )
        return self.tagebuch(datum)

    def tagebuch_loeschen(self, datum: str) -> None:
        datum = pruefe_datum(datum, "datum", pflicht=True)
        with closing(self.verbinden()) as con, con:
            if con.execute("DELETE FROM tagebuch WHERE datum = ?", (datum,)).rowcount == 0:
                raise ApiFehler(404, "Kein Eintrag für diesen Tag")

    # -- Übersicht ----------------------------------------------------------

    def uebersicht(self) -> dict:
        h = heute()
        in7 = (dt.date.today() + dt.timedelta(days=7)).isoformat()
        z = self.eins(
            "SELECT "
            "(SELECT COUNT(*) FROM plaene) AS plaene, "
            "(SELECT COUNT(*) FROM fotos) AS fotos, "
            "(SELECT COUNT(*) FROM maengel WHERE status != 'erledigt') AS maengel_offen, "
            "(SELECT COUNT(*) FROM maengel WHERE status = 'erledigt') AS maengel_erledigt, "
            "(SELECT COUNT(*) FROM maengel WHERE status != 'erledigt' AND frist != '' AND frist < ?) AS maengel_ueberfaellig, "
            "(SELECT COUNT(*) FROM tagebuch) AS tagebuch_eintraege, "
            "(SELECT MAX(datum) FROM tagebuch) AS tagebuch_letzter, "
            "(SELECT COUNT(*) FROM tagebuch WHERE datum = ?) AS tagebuch_heute",
            (h, h),
        )
        z["faellige_maengel"] = self.abfrage(
            "SELECT id, nr, titel, frist, gewerk, firma, status FROM maengel "
            "WHERE status != 'erledigt' AND frist != '' AND frist <= ? ORDER BY frist, nr LIMIT 15",
            (in7,),
        )
        for m in z["faellige_maengel"]:
            m["ueberfaellig"] = m["frist"] < h
        z["neueste_fotos"] = self.fotos({"limit": 8})
        z["heute"] = h
        return z


# --------------------------------------------------------------------------
# Druckansichten (Browser: Drucken -> Als PDF speichern)
# --------------------------------------------------------------------------

DRUCK_CSS = """
@page { size: A4; margin: 15mm 12mm 18mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; color: #111; margin: 0 auto; max-width: 190mm; padding: 10mm 0; background: #fff; }
h1 { font-size: 17pt; margin: 0 0 2mm; }
h2 { font-size: 12pt; margin: 6mm 0 2mm; border-bottom: 1px solid #999; padding-bottom: 1mm; }
.kopf { display: flex; justify-content: space-between; gap: 8mm; border-bottom: 2px solid #222; padding-bottom: 3mm; margin-bottom: 4mm; }
.kopf .projekt { font-size: 9.5pt; line-height: 1.45; }
.kopf .rechts { text-align: right; font-size: 9.5pt; line-height: 1.45; white-space: nowrap; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #bbb; padding: 1.5mm 2mm; vertical-align: top; text-align: left; }
th { background: #eee; font-size: 9pt; }
tr { break-inside: avoid; }
.klein { font-size: 8.5pt; color: #444; }
.ueberfaellig { color: #b00020; font-weight: 600; }
.status-erledigt { color: #1b6e2e; }
.fotos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm; }
.fotos figure { margin: 0; break-inside: avoid; }
.fotos img { width: 100%; height: 45mm; object-fit: cover; border: 1px solid #ccc; }
.fotos figcaption { font-size: 8.5pt; margin-top: 1mm; }
td img.mini { width: 22mm; height: 16mm; object-fit: cover; margin: 0 1mm 1mm 0; border: 1px solid #ccc; }
.feld { white-space: pre-wrap; min-height: 6mm; }
.leer { color: #888; font-style: italic; }
.fuss { margin-top: 8mm; font-size: 8pt; color: #666; display: flex; justify-content: space-between; }
.unterschrift { margin-top: 14mm; display: flex; gap: 20mm; }
.unterschrift div { flex: 1; border-top: 1px solid #333; padding-top: 1mm; font-size: 9pt; }
.werkzeug { position: sticky; top: 0; background: #f4f4f4; border: 1px solid #ccc; padding: 3mm; margin-bottom: 5mm; display: flex; gap: 3mm; align-items: center; font-size: 10pt; }
.werkzeug button { font-size: 11pt; padding: 2mm 5mm; cursor: pointer; }
@media print { .werkzeug { display: none; } body { padding: 0; max-width: none; } }
"""


def e(wert) -> str:
    return html.escape(str(wert if wert is not None else ""))


def datum_de(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return iso or ""


WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


def druck_seite(titel: str, einstellungen: dict, rechts: str, inhalt: str) -> str:
    projekt = " · ".join(x for x in (einstellungen.get("projekt_nr"), einstellungen.get("projekt_name")) if x)
    zeilen = [f"<strong>{e(projekt or 'Projekt (in Einstellungen eintragen)')}</strong>"]
    for k, label in (("adresse", "Baustelle"), ("bauherr", "Bauherr"), ("bauleiter", "Bauleitung")):
        if einstellungen.get(k):
            zeilen.append(f"{label}: {e(einstellungen[k])}")
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title><style>{DRUCK_CSS}</style></head><body>
<div class="werkzeug"><button onclick="window.print()">Drucken / als PDF speichern</button>
<span>Im Druckdialog als Drucker „Als PDF speichern“ bzw. „Microsoft Print to PDF“ wählen.</span></div>
<div class="kopf"><div class="projekt">{'<br>'.join(zeilen)}</div><div class="rechts">{rechts}</div></div>
<h1>{e(titel)}</h1>
{inhalt}
<div class="fuss"><span>{e(APP_NAME)} {e(VERSION)}</span><span>Stand: {dt.datetime.now().strftime('%d.%m.%Y %H:%M')}</span></div>
</body></html>"""


def druck_maengel(db: Datenbank, filter_: dict) -> str:
    maengel = db.maengel(filter_)
    fotos_je_mangel = {}
    for f in db.abfrage("SELECT id, mangel_id FROM fotos WHERE mangel_id IS NOT NULL ORDER BY datum, id"):
        fotos_je_mangel.setdefault(f["mangel_id"], []).append(f["id"])
    beschreibung = []
    status = filter_.get("status")
    if status:
        beschreibung.append("Status: " + ("nicht erledigt" if status == "nicht_erledigt" else MANGEL_STATUS.get(status, status)))
    for k, label in (("gewerk", "Gewerk"), ("geschoss", "Geschoss"), ("firma", "Firma"), ("q", "Suche")):
        if filter_.get(k):
            beschreibung.append(f"{label}: {filter_[k]}")
    if filter_.get("ueberfaellig") in ("1", "true"):
        beschreibung.append("nur überfällige")
    zeilen = []
    for m in maengel:
        ort = " / ".join(x for x in (m["geschoss"], m["ort"]) if x)
        frist_cls = ' class="ueberfaellig"' if m["ueberfaellig"] else ""
        bilder = "".join(f'<img class="mini" src="/datei/foto/{fid}" alt="">' for fid in fotos_je_mangel.get(m["id"], [])[:3])
        status_txt = MANGEL_STATUS.get(m["status"], m["status"])
        if m["status"] == "erledigt" and m["erledigt_am"]:
            status_txt += f"<br><span class='klein'>{e(datum_de(m['erledigt_am']))}</span>"
        zeilen.append(
            f"<tr><td>{m['nr']}</td>"
            f"<td><strong>{e(m['titel'])}</strong>"
            + (f"<div class='feld klein'>{e(m['beschreibung'])}</div>" if m["beschreibung"] else "")
            + (f"<div>{bilder}</div>" if bilder else "")
            + f"</td><td>{e(ort)}</td><td>{e(m['gewerk'])}<br><span class='klein'>{e(m['firma'])}</span></td>"
            f"<td{frist_cls}>{e(datum_de(m['frist']))}</td>"
            f"<td class='status-{e(m['status'])}'>{status_txt}</td></tr>"
        )
    offen = sum(1 for m in maengel if m["status"] != "erledigt")
    inhalt = (
        f"<p class='klein'>{e(' · '.join(beschreibung) or 'Alle Mängel')} – {len(maengel)} Einträge, davon {offen} nicht erledigt</p>"
        "<table><thead><tr><th style='width:9mm'>Nr.</th><th>Mangel</th><th style='width:28mm'>Ort</th>"
        "<th style='width:32mm'>Gewerk / Firma</th><th style='width:20mm'>Frist</th><th style='width:20mm'>Status</th></tr></thead><tbody>"
        + ("".join(zeilen) or "<tr><td colspan='6' class='leer'>Keine Mängel für diese Auswahl.</td></tr>")
        + "</tbody></table>"
        "<div class='unterschrift'><div>Ort, Datum</div><div>Bauleitung</div><div>Auftragnehmer</div></div>"
    )
    return druck_seite("Mängelliste", db.einstellungen(), f"Datum: {datum_de(heute())}", inhalt)


def druck_tagebuch(db: Datenbank, datum: str) -> str:
    t = db.tagebuch(datum)
    if not t:
        raise ApiFehler(404, "Für diesen Tag gibt es keinen Bautagebuch-Eintrag")
    tag = dt.date.fromisoformat(t["datum"])
    rechts = f"{WOCHENTAGE[tag.weekday()]}, {datum_de(t['datum'])}<br>Bericht Nr. {_berichtnummer(db, t['datum'])}"

    def feld(titel, wert):
        inhalt_ = e(wert) if wert else "<span class='leer'>–</span>"
        return f"<h2>{e(titel)}</h2><div class='feld'>{inhalt_}</div>"

    personal = t["personal"]
    summe = sum(p["anzahl"] for p in personal)
    personal_html = (
        "<table><thead><tr><th>Firma</th><th>Gewerk</th><th style='width:22mm'>Anzahl</th></tr></thead><tbody>"
        + "".join(f"<tr><td>{e(p['firma'])}</td><td>{e(p['gewerk'])}</td><td>{p['anzahl']}</td></tr>" for p in personal)
        + f"<tr><th colspan='2'>Summe</th><th>{summe}</th></tr></tbody></table>"
        if personal else "<div class='leer'>keine Angaben</div>"
    )
    fotos = db.fotos({"datum": t["datum"]})
    fotos_html = ""
    if fotos:
        fotos_html = "<h2>Fotos</h2><div class='fotos'>" + "".join(
            f"<figure><img src='/datei/foto/{f['id']}' alt=''><figcaption>"
            f"{e(' · '.join(x for x in (f['geschoss'], f['notiz']) if x) or f['dateiname'])}</figcaption></figure>"
            for f in reversed(fotos)
        ) + "</div>"
    inhalt = (
        "<table><tr><th style='width:30mm'>Wetter</th><td>" + e(t["wetter"]) + "</td>"
        "<th style='width:28mm'>Temperatur</th><td>" + e(t["temperatur"]) + "</td></tr>"
        "<tr><th>Arbeitszeit</th><td colspan='3'>" + e(t["arbeitszeit"]) + "</td></tr></table>"
        + "<h2>Personal auf der Baustelle</h2>" + personal_html
        + feld("Ausgeführte Leistungen", t["leistungen"])
        + feld("Behinderungen / Erschwernisse", t["behinderungen"])
        + feld("Besondere Vorkommnisse", t["vorkommnisse"])
        + feld("Anordnungen / Vereinbarungen", t["anordnungen"])
        + feld("Besucher / Besprechungen", t["besucher"])
        + fotos_html
        + "<div class='unterschrift'><div>Bauleitung</div><div>gesehen Auftraggeber</div></div>"
    )
    return druck_seite("Bautagebuch", db.einstellungen(), rechts, inhalt)


def _berichtnummer(db: Datenbank, datum: str) -> int:
    return db.eins("SELECT COUNT(*) AS n FROM tagebuch WHERE datum <= ?", (datum,))["n"]


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

ROUTEN = []


def route(methode: str, muster: str):
    def deko(fn):
        ROUTEN.append((methode, re.compile("^" + muster + "$"), fn))
        return fn
    return deko


class Antwort:
    def __init__(self, inhalt: bytes, typ: str, status: int = 200, kopf: dict | None = None):
        self.inhalt, self.typ, self.status, self.kopf = inhalt, typ, status, kopf or {}


class DateiAntwort:
    def __init__(self, pfad: Path, typ: str, dateiname: str, cache: bool = True):
        self.pfad, self.typ, self.dateiname, self.cache = pfad, typ, dateiname, cache


@route("GET", r"/api/info")
def api_info(h, m, q):
    a = h.server.app
    return {
        "app": APP_NAME,
        "version": VERSION,
        "port": a.cfg["port"],
        "datenordner": str(a.cfg["datenordner"].resolve()),
        "sicherungsordner": str(a.cfg["sicherungsordner"].resolve()),
        "letzte_sicherung": letzte_sicherung(a.cfg["sicherungsordner"]),
        "logdatei": str(a.logdatei.resolve()) if a.logdatei else "",
        "python": sys.version.split()[0],
        "max_upload_mb": int(a.cfg["max_upload_mb"]),
    }


@route("GET", r"/api/einstellungen")
def api_einstellungen(h, m, q):
    return h.db.einstellungen()


@route("PUT", r"/api/einstellungen")
def api_einstellungen_speichern(h, m, q):
    return h.db.einstellungen_speichern(h.json_body())


@route("GET", r"/api/uebersicht")
def api_uebersicht(h, m, q):
    return h.db.uebersicht()


@route("GET", r"/api/plaene")
def api_plaene(h, m, q):
    return h.db.plaene()


@route("POST", r"/api/plaene")
def api_plan_hochladen(h, m, q):
    dateiname, endung = h.upload_name(q, PLAN_TYPEN)
    datei, groesse = h.upload_speichern(h.db.plan_ordner, endung)
    plan = h.db.plan_anlegen(dateiname, datei, groesse)
    log.info("Plan hochgeladen: %s (%s, %d Bytes)", dateiname, plan["geschoss"] or "ohne Geschoss", groesse)
    return plan


@route("PATCH", r"/api/plaene/(\d+)")
def api_plan_aendern(h, m, q):
    return h.db.plan_aendern(int(m.group(1)), h.json_body())


@route("DELETE", r"/api/plaene/(\d+)")
def api_plan_loeschen(h, m, q):
    h.db.plan_loeschen(int(m.group(1)))
    return {"ok": True}


@route("GET", r"/api/plaene/(\d+)/markierungen")
def api_markierungen(h, m, q):
    return h.db.markierungen(int(m.group(1)))


@route("GET", r"/api/fotos")
def api_fotos(h, m, q):
    return h.db.fotos(q)


@route("POST", r"/api/fotos")
def api_foto_hochladen(h, m, q):
    dateiname, endung = h.upload_name(q, FOTO_TYPEN)
    # Daten vor dem Speichern prüfen, damit keine verwaisten Dateien entstehen
    pruefe_datum(q.get("datum"), "datum")
    if q.get("mangel_id"):
        h.db.mangel(pruefe_id(q["mangel_id"], "mangel_id"))
    datei, groesse = h.upload_speichern(h.db.foto_ordner, endung)
    return h.db.foto_anlegen(dateiname, datei, groesse, q)


@route("PATCH", r"/api/fotos/(\d+)")
def api_foto_aendern(h, m, q):
    return h.db.foto_aendern(int(m.group(1)), h.json_body())


@route("DELETE", r"/api/fotos/(\d+)")
def api_foto_loeschen(h, m, q):
    h.db.foto_loeschen(int(m.group(1)))
    return {"ok": True}


@route("GET", r"/api/maengel")
def api_maengel(h, m, q):
    return h.db.maengel(q)


@route("POST", r"/api/maengel")
def api_mangel_anlegen(h, m, q):
    return h.db.mangel_anlegen(h.json_body())


@route("GET", r"/api/maengel/(\d+)")
def api_mangel(h, m, q):
    return h.db.mangel(int(m.group(1)))


@route("PATCH", r"/api/maengel/(\d+)")
def api_mangel_aendern(h, m, q):
    return h.db.mangel_aendern(int(m.group(1)), h.json_body())


@route("DELETE", r"/api/maengel/(\d+)")
def api_mangel_loeschen(h, m, q):
    h.db.mangel_loeschen(int(m.group(1)))
    return {"ok": True}


@route("GET", r"/api/tagebuch")
def api_tagebuch_liste(h, m, q):
    return h.db.tagebuch_liste()


@route("GET", r"/api/tagebuch/([\d-]+)")
def api_tagebuch(h, m, q):
    t = h.db.tagebuch(m.group(1))
    if not t:
        raise ApiFehler(404, "Kein Eintrag für diesen Tag")
    return t


@route("PUT", r"/api/tagebuch/([\d-]+)")
def api_tagebuch_speichern(h, m, q):
    return h.db.tagebuch_speichern(m.group(1), h.json_body())


@route("DELETE", r"/api/tagebuch/([\d-]+)")
def api_tagebuch_loeschen(h, m, q):
    h.db.tagebuch_loeschen(m.group(1))
    return {"ok": True}


@route("GET", r"/datei/plan/(\d+)")
def datei_plan(h, m, q):
    p = h.db.plan(int(m.group(1)))
    endung = Path(p["datei"]).suffix.lower()
    return DateiAntwort(h.db.plan_ordner / p["datei"], PLAN_TYPEN[endung], p["dateiname"])


@route("GET", r"/datei/foto/(\d+)")
def datei_foto(h, m, q):
    f = h.db.foto(int(m.group(1)))
    endung = Path(f["datei"]).suffix.lower()
    return DateiAntwort(h.db.foto_ordner / f["datei"], FOTO_TYPEN[endung], f["dateiname"])


@route("GET", r"/druck/maengel")
def seite_druck_maengel(h, m, q):
    return Antwort(druck_maengel(h.db, q).encode("utf-8"), "text/html; charset=utf-8")


@route("GET", r"/druck/tagebuch/([\d-]+)")
def seite_druck_tagebuch(h, m, q):
    return Antwort(druck_tagebuch(h.db, m.group(1)).encode("utf-8"), "text/html; charset=utf-8")


STATIC_TYPEN = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json",
}


@route("GET", r"/(|index\.html|static/.+)")
def statisch(h, m, q):
    rel = m.group(1)
    rel = "index.html" if rel in ("", "index.html") else rel[len("static/"):]
    pfad = (STATIC_DIR / urllib.parse.unquote(rel)).resolve()
    try:
        pfad.relative_to(STATIC_DIR)
    except ValueError:
        raise ApiFehler(404, "Nicht gefunden")
    if not pfad.is_file() or pfad.suffix.lower() not in STATIC_TYPEN:
        raise ApiFehler(404, "Nicht gefunden")
    return DateiAntwort(pfad, STATIC_TYPEN[pfad.suffix.lower()], pfad.name, cache=False)


class Handler(BaseHTTPRequestHandler):
    server_version = f"{APP_NAME}/{VERSION}"
    protocol_version = "HTTP/1.1"

    @property
    def db(self) -> Datenbank:
        return self.server.app.db

    def log_message(self, fmt, *args):
        log.debug("%s %s", self.address_string(), fmt % args)

    def do_GET(self):
        self.verarbeiten("GET")

    def do_POST(self):
        self.verarbeiten("POST")

    def do_PUT(self):
        self.verarbeiten("PUT")

    def do_PATCH(self):
        self.verarbeiten("PATCH")

    def do_DELETE(self):
        self.verarbeiten("DELETE")

    def verarbeiten(self, methode: str):
        url = urllib.parse.urlsplit(self.path)
        q = {k: v[-1] for k, v in urllib.parse.parse_qs(url.query).items()}
        pfad = url.path
        self._body_gelesen = False
        try:
            passend = False
            for m_, muster, fn in ROUTEN:
                treffer = muster.match(pfad)
                if not treffer:
                    continue
                passend = True
                if m_ == methode:
                    self.senden(fn(self, treffer, q))
                    return
            raise ApiFehler(405 if passend else 404, "Methode nicht erlaubt" if passend else "Nicht gefunden")
        except ApiFehler as fehler:
            if fehler.status >= 500:
                log.error("%s %s: %s", methode, pfad, fehler.meldung)
            self.fehler_senden(fehler.status, fehler.meldung)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            log.exception("Fehler bei %s %s", methode, pfad)
            self.fehler_senden(500, "Interner Fehler – Details stehen im Fehlerprotokoll (logs/server.log)")

    # -- Eingabe ------------------------------------------------------------

    def laenge(self) -> int:
        wert = self.headers.get("Content-Length")
        if wert is None:
            raise ApiFehler(411, "Content-Length fehlt")
        try:
            n = int(wert)
        except ValueError:
            raise ApiFehler(400, "Ungültige Content-Length")
        if n < 0:
            raise ApiFehler(400, "Ungültige Content-Length")
        return n

    def json_body(self):
        n = self.laenge()
        if n > 2_000_000:
            raise ApiFehler(413, "Anfrage zu groß")
        roh = self.rfile.read(n)
        self._body_gelesen = True
        try:
            daten = json.loads(roh.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiFehler(400, "Ungültiges JSON")
        if not isinstance(daten, dict):
            raise ApiFehler(400, "JSON-Objekt erwartet")
        return daten

    def upload_name(self, q: dict, erlaubt: dict) -> tuple:
        dateiname = Path((q.get("dateiname") or "").replace("\\", "/")).name.strip()
        if not dateiname:
            raise ApiFehler(400, "Dateiname fehlt")
        endung = Path(dateiname).suffix.lower()
        if endung not in erlaubt:
            raise ApiFehler(400, f"Dateityp {endung or '(ohne Endung)'} nicht erlaubt – erlaubt: {', '.join(sorted(erlaubt))}")
        return dateiname[:250], endung

    def upload_speichern(self, ordner: Path, endung: str) -> tuple:
        n = self.laenge()
        max_bytes = int(self.server.app.cfg["max_upload_mb"]) * 1_000_000
        if n > max_bytes:
            raise ApiFehler(413, f"Datei zu groß (max. {max_bytes // 1_000_000} MB)")
        self._body_gelesen = True  # ab hier liest datei_speichern den Body
        return self.db.datei_speichern(ordner, endung, self.rfile, n, max_bytes)

    # -- Ausgabe ------------------------------------------------------------

    def senden(self, ergebnis):
        if isinstance(ergebnis, DateiAntwort):
            return self.datei_senden(ergebnis)
        if isinstance(ergebnis, Antwort):
            return self.bytes_senden(ergebnis.status, ergebnis.typ, ergebnis.inhalt, ergebnis.kopf)
        inhalt = json.dumps(ergebnis, ensure_ascii=False).encode("utf-8")
        self.bytes_senden(200, "application/json; charset=utf-8", inhalt, {"Cache-Control": "no-store"})

    def body_verwerfen(self):
        """Ungelesenen Body abholen, damit der Client die Fehlermeldung sicher erhält."""
        if getattr(self, "_body_gelesen", True):
            return
        self._body_gelesen = True
        try:
            rest = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            rest = -1
        if rest < 0 or rest > 4_000_000_000:
            self.close_connection = True
            return
        while rest > 0:
            block = self.rfile.read(min(rest, 1 << 20))
            if not block:
                self.close_connection = True
                return
            rest -= len(block)

    def fehler_senden(self, status: int, meldung: str):
        try:
            self.body_verwerfen()
        except OSError:
            self.close_connection = True
        inhalt = json.dumps({"fehler": meldung}, ensure_ascii=False).encode("utf-8")
        try:
            self.bytes_senden(status, "application/json; charset=utf-8", inhalt, {"Cache-Control": "no-store"})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def bytes_senden(self, status: int, typ: str, inhalt: bytes, kopf: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(inhalt)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (kopf or {}).items():
            self.send_header(k, v)
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(inhalt)

    def datei_senden(self, d: DateiAntwort):
        if not d.pfad.is_file():
            raise ApiFehler(404, "Datei fehlt im Datenordner")
        groesse = d.pfad.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", d.typ)
        self.send_header("Content-Length", str(groesse))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "private, max-age=86400" if d.cache else "no-cache")
        if d.cache:
            self.send_header(
                "Content-Disposition", "inline; filename*=UTF-8''" + urllib.parse.quote(d.dateiname)
            )
        self.end_headers()
        with open(d.pfad, "rb") as f:
            while True:
                block = f.read(1 << 16)
                if not block:
                    break
                self.wfile.write(block)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # Unter Windows erlaubt SO_REUSEADDR eine Doppelbelegung des Ports
    allow_reuse_address = os.name != "nt"


class Anwendung:
    def __init__(self, cfg: dict, logdatei: Path | None = None):
        self.cfg = cfg
        self.logdatei = logdatei
        self.db = Datenbank(cfg["datenordner"])

    def server_erstellen(self) -> Server:
        server = Server((self.cfg["host"], self.cfg["port"]), Handler)
        server.app = self
        return server


# --------------------------------------------------------------------------
# Start
# --------------------------------------------------------------------------


def adresse(cfg: dict) -> str:
    host = cfg["host"]
    if host in ("0.0.0.0", "", "::"):
        host = "localhost"
    return f"http://{host}:{cfg['port']}"


def port_status(cfg: dict) -> str:
    """'frei', 'eigene' (Bauleiter-Assistent läuft schon) oder 'belegt'."""
    host = "127.0.0.1" if cfg["host"] in ("0.0.0.0", "", "::") else cfg["host"]
    try:
        with socket.create_connection((host, cfg["port"]), timeout=1):
            pass
    except OSError:
        return "frei"
    try:
        req = urllib.request.Request(adresse(cfg) + "/api/info")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=2) as r:
            info = json.loads(r.read().decode("utf-8"))
        if info.get("app") == APP_NAME and str(info.get("version")) == VERSION:
            return "eigene"
    except Exception:
        pass
    return "belegt"


def pruefen(cfg: dict) -> int:
    """Rückgabe: 0 = startbereit, 2 = läuft bereits, 1 = Problem."""
    if sys.version_info < MIN_PYTHON:
        print(f"FEHLER: Python {'.'.join(map(str, MIN_PYTHON))} oder neuer wird benötigt "
              f"(gefunden: {sys.version.split()[0]}).")
        return 1
    status = port_status(cfg)
    if status == "eigene":
        print(f"Der {APP_NAME} {VERSION} läuft bereits unter {adresse(cfg)}.")
        return 2
    if status == "belegt":
        print(f"FEHLER: Port {cfg['port']} ist bereits von einem anderen Programm belegt.")
        print("Lösung: Das andere Programm beenden oder in config.json einen anderen \"port\" eintragen.")
        return 1
    try:
        cfg["datenordner"].mkdir(parents=True, exist_ok=True)
        probe = cfg["datenordner"] / ".schreibtest"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as fehler:
        print(f"FEHLER: Datenordner {cfg['datenordner']} ist nicht beschreibbar: {fehler}")
        return 1
    print(f"OK: Python {sys.version.split()[0]}, Port {cfg['port']} frei, Datenordner {cfg['datenordner']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {VERSION}")
    parser.add_argument("--config", default=str(BASE_DIR / "config.json"), help="Pfad zur config.json")
    parser.add_argument("--port", type=int, help="Port (überschreibt config.json)")
    parser.add_argument("--pruefen", action="store_true", help="nur Voraussetzungen prüfen")
    parser.add_argument("--kein-browser", action="store_true", help="Browser nicht automatisch öffnen")
    args = parser.parse_args(argv)

    cfg = lade_konfiguration(Path(args.config))
    if args.port:
        cfg["port"] = args.port
    if args.pruefen:
        return pruefen(cfg)

    logdatei = protokoll_einrichten(cfg["logordner"])
    log.info("%s %s startet (Python %s)", APP_NAME, VERSION, sys.version.split()[0])

    status = port_status(cfg)
    if status != "frei":
        if status == "eigene":
            log.info("Läuft bereits unter %s – öffne nur den Browser.", adresse(cfg))
            if cfg["browser_oeffnen"] and not args.kein_browser:
                webbrowser.open(adresse(cfg))
            return 0
        log.error("Port %s ist belegt. In config.json einen anderen Port eintragen.", cfg["port"])
        return 1

    try:
        sicherung = sicherung_anlegen(cfg["datenordner"], cfg["sicherungsordner"], int(cfg["sicherungen_behalten"]))
        if sicherung:
            log.info("Sicherung angelegt: %s", sicherung)
    except Exception:
        log.exception("Sicherung fehlgeschlagen – Start wird fortgesetzt")

    app = Anwendung(cfg, logdatei)
    try:
        server = app.server_erstellen()
    except OSError as fehler:
        log.error("Server kann Port %s nicht öffnen: %s", cfg["port"], fehler)
        return 1

    log.info("Bereit: %s  (Datenordner: %s)", adresse(cfg), cfg["datenordner"].resolve())
    if cfg["browser_oeffnen"] and not args.kein_browser:
        threading.Timer(0.5, webbrowser.open, args=(adresse(cfg),)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Beendet.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
