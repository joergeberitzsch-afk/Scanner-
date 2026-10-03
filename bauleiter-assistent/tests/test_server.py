"""Tests für den Bauleiter-Assistenten.  Ausführen:  python -m unittest discover -s tests"""
import datetime as dt
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402


def mini_pdf() -> bytes:
    """Erzeugt ein gültiges einseitiges PDF (A4 quer) mit einem Rechteck."""
    inhalt = b"0 0 1 rg 100 100 400 200 re f"
    objekte = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(inhalt), inhalt),
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objekte, 1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objekte) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objekte) + 1, xref)
    return pdf


# 1x1 Pixel JPEG
MINI_JPG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720"
    "222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405"
    "060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282"
    "090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495"
    "969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008"
    "010100003f00fbd3ffd9"
)


class HilfsfunktionenTest(unittest.TestCase):
    def test_geschoss_aus_dateiname(self):
        faelle = {
            "A_GR_OG5_ST3_NB.pdf": "OG5",
            "A_GR_OG10_ST3_NB.pdf": "OG10",
            "A_GR_EG_ST3_NB.pdf": "EG",
            "Grundriss 1.OG.pdf": "OG1",
            "Grundriss_2OG.pdf": "OG2",
            "Schnitt_UG2.pdf": "UG2",
            "Dachgeschoss_DG.pdf": "DG",
            "Lageplan.pdf": "",
            "13_38_12.pdf": "",
        }
        for name, erwartet in faelle.items():
            self.assertEqual(server.geschoss_aus_dateiname(name), erwartet, name)

    def test_geschoss_reihenfolge(self):
        liste = ["OG10", "", "EG", "OG2", "DG", "UG", "OG1", "UG2", "XYZ"]
        self.assertEqual(sorted(liste, key=server.geschoss_rang), ["UG2", "UG", "EG", "OG1", "OG2", "OG10", "DG", "XYZ", ""])

    def test_datum_aus_dateiname(self):
        self.assertEqual(server.datum_aus_dateiname("20260912_090810_65b56d76.jpg"), "2026-09-12")
        self.assertEqual(server.datum_aus_dateiname("IMG-20260131-WA0001.jpg"), "2026-01-31")
        self.assertEqual(server.datum_aus_dateiname("Foto 2026-03-05.png"), "2026-03-05")
        self.assertEqual(server.datum_aus_dateiname("20261340_120000.jpg"), "")
        self.assertEqual(server.datum_aus_dateiname("baustelle.jpg"), "")


class SicherungTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_leerer_ordner_keine_sicherung(self):
        self.assertIsNone(server.sicherung_anlegen(self.tmp / "daten", self.tmp / "sich", 3))

    def test_sicherung_und_aufraeumen(self):
        daten = self.tmp / "daten"
        (daten / "dateien").mkdir(parents=True)
        (daten / "bauleiter.db").write_bytes(b"x" * 100)
        (daten / "dateien" / "a.jpg").write_bytes(b"y")
        ziel = self.tmp / "sich"
        for _ in range(5):
            server.sicherung_anlegen(daten, ziel, 3)
        zips = sorted(ziel.glob("daten_*.zip"))
        self.assertEqual(len(zips), 3)
        with zipfile.ZipFile(zips[-1]) as zf:
            self.assertEqual(sorted(zf.namelist()), ["bauleiter.db", "dateien/a.jpg"])
        self.assertEqual(list(ziel.glob("*.tmp")), [])


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cfg = dict(server.DEFAULT_CONFIG)
        cfg.update({
            "port": 0,
            "datenordner": cls.tmp / "daten",
            "sicherungsordner": cls.tmp / "sicherungen",
            "logordner": cls.tmp / "logs",
            "max_upload_mb": 1,
        })
        cls.app = server.Anwendung(cfg)
        cls.httpd = cls.app.server_erstellen()
        cfg["port"] = cls.httpd.server_address[1]
        cls.basis = f"http://127.0.0.1:{cfg['port']}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.tmp)

    def anfrage(self, methode, pfad, daten=None, roh=None, typ=None):
        body = roh if roh is not None else (json.dumps(daten).encode() if daten is not None else None)
        req = urllib.request.Request(self.basis + pfad, data=body, method=methode)
        if daten is not None:
            req.add_header("Content-Type", "application/json")
        if typ:
            req.add_header("Content-Type", typ)
        try:
            with self.opener.open(req, timeout=5) as r:
                inhalt = r.read()
                return r.status, r.headers, inhalt
        except urllib.error.HTTPError as fehler:
            return fehler.code, fehler.headers, fehler.read()

    def json(self, methode, pfad, daten=None, erwartet=200, **kw):
        status, _, inhalt = self.anfrage(methode, pfad, daten, **kw)
        self.assertEqual(status, erwartet, inhalt[:300])
        return json.loads(inhalt)

    # -- allgemein ----------------------------------------------------------

    def test_info_und_startseite(self):
        info = self.json("GET", "/api/info")
        self.assertEqual(info["app"], server.APP_NAME)
        self.assertEqual(info["version"], server.VERSION)
        status, kopf, inhalt = self.anfrage("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Bauleiter-Assistent", inhalt)
        status, _, _ = self.anfrage("GET", "/static/vendor/pdfjs/pdf.min.js")
        self.assertEqual(status, 200)

    def test_pfad_ausbruch_verhindert(self):
        for pfad in ("/static/../server.py", "/static/%2e%2e/server.py", "/static/..%2fconfig.json"):
            status, _, _ = self.anfrage("GET", pfad)
            self.assertEqual(status, 404, pfad)

    def test_unbekannt_und_methode(self):
        self.assertEqual(self.anfrage("GET", "/api/gibtsnicht")[0], 404)
        self.assertEqual(self.anfrage("DELETE", "/api/plaene")[0], 405)

    def test_port_status_erkennt_eigene_instanz(self):
        self.assertEqual(server.port_status(self.app.cfg), "eigene")

    # -- Einstellungen ------------------------------------------------------

    def test_einstellungen(self):
        neu = self.json("PUT", "/api/einstellungen", {"projekt_name": "Wohnpark Nord", "unbekannt": "x"})
        self.assertEqual(neu["projekt_name"], "Wohnpark Nord")
        self.assertNotIn("unbekannt", neu)
        self.assertIn("Elektro", neu["gewerke"])

    # -- Pläne --------------------------------------------------------------

    def test_plaene_hochladen_sortieren_loeschen(self):
        ids = []
        for name in ("A_GR_OG10_ST3_NB.pdf", "A_GR_EG_ST3_NB.pdf", "A_GR_OG2_ST3_NB.pdf"):
            p = self.json("POST", "/api/plaene?dateiname=" + name, roh=mini_pdf(), typ="application/pdf")
            ids.append(p["id"])
        reihenfolge = [p["geschoss"] for p in self.json("GET", "/api/plaene") if p["id"] in ids]
        self.assertEqual(reihenfolge, ["EG", "OG2", "OG10"])

        status, kopf, inhalt = self.anfrage("GET", f"/datei/plan/{ids[0]}")
        self.assertEqual(status, 200)
        self.assertEqual(kopf["Content-Type"], "application/pdf")
        self.assertTrue(inhalt.startswith(b"%PDF"))

        geaendert = self.json("PATCH", f"/api/plaene/{ids[0]}", {"geschoss": "og9", "bezeichnung": "Grundriss"})
        self.assertEqual((geaendert["geschoss"], geaendert["bezeichnung"]), ("OG9", "Grundriss"))

        datei = self.app.db.plan_ordner / self.app.db.plan(ids[0])["datei"]
        self.assertTrue(datei.exists())
        self.json("DELETE", f"/api/plaene/{ids[0]}")
        self.assertFalse(datei.exists())
        self.assertEqual(self.anfrage("GET", f"/datei/plan/{ids[0]}")[0], 404)

    def test_upload_pruefungen(self):
        # falscher Inhalt
        self.json("POST", "/api/plaene?dateiname=x.pdf", roh=b"kein pdf", erwartet=400)
        # falsche Endung
        self.json("POST", "/api/plaene?dateiname=x.exe", roh=b"MZ", erwartet=400)
        # zu groß (max_upload_mb = 1)
        self.json("POST", "/api/fotos?dateiname=x.jpg", roh=b"\xff\xd8" + b"0" * 1_100_000, erwartet=413)
        # Pfadanteile im Dateinamen werden entfernt
        f = self.json("POST", "/api/fotos?dateiname=..%5C..%5Cboese.jpg", roh=MINI_JPG)
        self.assertEqual(f["dateiname"], "boese.jpg")
        # keine Reste im Ordner
        self.assertEqual(list(self.app.db.plan_ordner.glob("*.tmp")), [])

    # -- Fotos & Markierungen -----------------------------------------------

    def test_fotos_und_markierung(self):
        plan = self.json("POST", "/api/plaene?dateiname=A_GR_OG1_ST3_NB.pdf", roh=mini_pdf())
        foto = self.json("POST", "/api/fotos?dateiname=20260912_090810_65b56d76.jpg", roh=MINI_JPG)
        self.assertEqual(foto["datum"], "2026-09-12")
        foto2 = self.json("POST", "/api/fotos?dateiname=bild.jpg&datum=2026-09-13&geschoss=og1", roh=MINI_JPG)
        self.assertEqual((foto2["datum"], foto2["geschoss"]), ("2026-09-13", "OG1"))
        foto3 = self.json("POST", "/api/fotos?dateiname=bild.jpg", roh=MINI_JPG)
        self.assertEqual(foto3["datum"], dt.date.today().isoformat())

        self.json("PATCH", f"/api/fotos/{foto['id']}", {"plan_id": plan["id"], "x": 0.25, "y": 0.5, "notiz": "Bewehrung"})
        m = self.json("GET", f"/api/plaene/{plan['id']}/markierungen")
        self.assertEqual([(f["id"], f["x"], f["y"]) for f in m["fotos"]], [(foto["id"], 0.25, 0.5)])

        self.json("PATCH", f"/api/fotos/{foto['id']}", {"plan_id": plan["id"], "x": 1.5, "y": 0.5}, erwartet=400)
        self.json("PATCH", f"/api/fotos/{foto['id']}", {"plan_id": 999999, "x": 0.1, "y": 0.1}, erwartet=404)
        self.json("PATCH", f"/api/fotos/{foto['id']}", {"datum": "12.09.2026"}, erwartet=400)

        nach_tag = self.json("GET", "/api/fotos?datum=2026-09-12")
        self.assertIn(foto["id"], [f["id"] for f in nach_tag])

        # Plan löschen entfernt die Markierung, das Foto bleibt
        self.json("DELETE", f"/api/plaene/{plan['id']}")
        f = self.json("GET", f"/api/fotos?datum=2026-09-12")
        f = [x for x in f if x["id"] == foto["id"]][0]
        self.assertEqual((f["plan_id"], f["x"], f["y"], f["notiz"]), (None, None, None, "Bewehrung"))

        datei = self.app.db.foto_ordner / f["datei"]
        self.json("DELETE", f"/api/fotos/{foto['id']}")
        self.assertFalse(datei.exists())

    # -- Mängel -------------------------------------------------------------

    def test_maengel(self):
        self.json("POST", "/api/maengel", {"titel": "  "}, erwartet=400)
        gestern = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        a = self.json("POST", "/api/maengel", {"titel": "Riss in Wand", "gewerk": "Trockenbau", "geschoss": "og3", "frist": gestern})
        b = self.json("POST", "/api/maengel", {"titel": "Steckdose fehlt", "gewerk": "Elektro", "status": "in_arbeit"})
        self.assertEqual(b["nr"], a["nr"] + 1)
        self.assertEqual(a["geschoss"], "OG3")
        self.assertTrue(a["ueberfaellig"])

        ueberfaellig = self.json("GET", "/api/maengel?ueberfaellig=1")
        self.assertIn(a["id"], [m["id"] for m in ueberfaellig])
        self.assertNotIn(b["id"], [m["id"] for m in ueberfaellig])

        erledigt = self.json("PATCH", f"/api/maengel/{a['id']}", {"status": "erledigt"})
        self.assertEqual(erledigt["erledigt_am"], dt.date.today().isoformat())
        self.assertFalse(erledigt["ueberfaellig"])
        offen = self.json("GET", "/api/maengel?status=nicht_erledigt")
        self.assertNotIn(a["id"], [m["id"] for m in offen])
        wieder = self.json("PATCH", f"/api/maengel/{a['id']}", {"status": "offen"})
        self.assertEqual(wieder["erledigt_am"], "")

        self.json("PATCH", f"/api/maengel/{a['id']}", {"status": "kaputt"}, erwartet=400)
        self.json("PATCH", f"/api/maengel/{a['id']}", {"frist": "morgen"}, erwartet=400)
        self.assertEqual(len(self.json("GET", "/api/maengel?q=Steckdose")), 1)

        # Foto zuordnen, Mangel löschen -> Foto bleibt ohne Zuordnung
        foto = self.json("POST", f"/api/fotos?dateiname=m.jpg&mangel_id={b['id']}", roh=MINI_JPG)
        self.assertEqual(foto["mangel_id"], b["id"])
        self.json("POST", "/api/fotos?dateiname=m.jpg&mangel_id=999999", roh=MINI_JPG, erwartet=404)
        self.json("DELETE", f"/api/maengel/{b['id']}")
        self.assertIsNone([f for f in self.json("GET", "/api/fotos") if f["id"] == foto["id"]][0]["mangel_id"])

    def test_mangel_mit_markierung_und_druck(self):
        plan = self.json("POST", "/api/plaene?dateiname=A_GR_OG4_ST3_NB.pdf", roh=mini_pdf())
        m = self.json("POST", "/api/maengel", {
            "titel": "Fliese <gebrochen>", "beschreibung": "Bad & WC", "plan_id": plan["id"], "x": 0.3, "y": 0.7,
            "geschoss": "OG4", "firma": "Muster GmbH",
        })
        self.assertEqual((m["plan_id"], m["x"], m["y"]), (plan["id"], 0.3, 0.7))
        self.json("POST", "/api/maengel", {"titel": "x", "plan_id": plan["id"], "x": 0.3}, erwartet=400)
        status, kopf, inhalt = self.anfrage("GET", "/druck/maengel?geschoss=OG4")
        self.assertEqual(status, 200)
        text = inhalt.decode("utf-8")
        self.assertIn("Fliese &lt;gebrochen&gt;", text)
        self.assertIn("Bad &amp; WC", text)
        self.assertIn("Geschoss: OG4", text)
        self.assertNotIn("<gebrochen>", text)

    # -- Bautagebuch --------------------------------------------------------

    def test_tagebuch(self):
        tag = "2026-09-14"
        self.json("GET", f"/api/tagebuch/{tag}", erwartet=404)
        self.json("PUT", "/api/tagebuch/2026-02-30", {}, erwartet=400)
        self.json("PUT", f"/api/tagebuch/{tag}", {"personal": [{"firma": "A", "anzahl": "x"}]}, erwartet=400)
        t = self.json("PUT", f"/api/tagebuch/{tag}", {
            "wetter": "sonnig", "temperatur": "12 °C", "leistungen": "Decke OG5 betoniert",
            "personal": [{"firma": "Bau GmbH", "gewerk": "Rohbau", "anzahl": 6}, {"firma": "", "gewerk": "", "anzahl": 0}],
        })
        self.assertEqual(t["personal"], [{"firma": "Bau GmbH", "gewerk": "Rohbau", "anzahl": 6}])
        t = self.json("PUT", f"/api/tagebuch/{tag}", {"wetter": "Regen", "personal": t["personal"]})
        self.assertEqual(t["wetter"], "Regen")
        self.assertEqual(t["leistungen"], "")

        self.json("POST", f"/api/fotos?dateiname=t.jpg&datum={tag}", roh=MINI_JPG)
        liste = self.json("GET", "/api/tagebuch")
        eintrag = [x for x in liste if x["datum"] == tag][0]
        self.assertEqual((eintrag["personal_summe"], eintrag["anzahl_fotos"]), (6, 1))

        status, _, inhalt = self.anfrage("GET", f"/druck/tagebuch/{tag}")
        self.assertEqual(status, 200)
        text = inhalt.decode("utf-8")
        self.assertIn("Montag, 14.09.2026", text)
        self.assertIn("Bau GmbH", text)
        self.assertIn("/datei/foto/", text)
        self.assertEqual(self.anfrage("GET", "/druck/tagebuch/2026-01-01")[0], 404)

        self.json("DELETE", f"/api/tagebuch/{tag}")
        self.json("DELETE", f"/api/tagebuch/{tag}", erwartet=404)

    def test_uebersicht(self):
        u = self.json("GET", "/api/uebersicht")
        for k in ("plaene", "fotos", "maengel_offen", "maengel_ueberfaellig", "tagebuch_heute", "faellige_maengel", "neueste_fotos"):
            self.assertIn(k, u)

    def test_ungueltiges_json(self):
        status, _, _ = self.anfrage("POST", "/api/maengel", roh=b"{kaputt", typ="application/json")
        self.assertEqual(status, 400)
        status, _, _ = self.anfrage("POST", "/api/maengel", roh=b"[1,2]", typ="application/json")
        self.assertEqual(status, 400)


class PruefenTest(unittest.TestCase):
    def test_port_belegt_durch_fremdes_programm(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        try:
            cfg = dict(server.DEFAULT_CONFIG, port=s.getsockname()[1])
            self.assertEqual(server.port_status(cfg), "belegt")
        finally:
            s.close()

    def test_pruefen_ok(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            s = __import__("socket").socket()
            s.bind(("127.0.0.1", 0))
            frei = s.getsockname()[1]
            s.close()
            cfg = dict(server.DEFAULT_CONFIG, port=frei, datenordner=tmp / "daten")
            self.assertEqual(server.pruefen(cfg), 0)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
