"""CAD-Export (DXF, AutoCAD 2018) des Grundrissvorschlags Regelgeschoss.

Übernimmt die Geometrie aus grundriss_vorschlag.py. Einheit Meter, Achse A/1 = 0/0.
Variante A und Rückfallvariante B (WE 1.05/1.09) liegen auf getrennten Layern.

Aufruf:  python3 export_dxf.py  ->  Vorschlag_Installationsknoten_RG.dxf
"""

from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

import grundriss_vorschlag as g

doc = ezdxf.new("R2018", setup=True)
doc.header["$INSUNITS"] = 6          # Meter
doc.header["$MEASUREMENT"] = 1
msp = doc.modelspace()

LAYERS = {
    "A_ACHSEN": (8, "DASHDOT"), "A_BEMASSUNG": (7, "Continuous"),
    "A_WAND_BESTAND": (7, "Continuous"), "A_WAND_BESTAND_SCHRAFFUR": (8, "Continuous"),
    "A_AUSSENWAND_DAEMMUNG": (9, "Continuous"), "A_RAUM": (7, "Continuous"),
    "A_RAUMSTEMPEL": (7, "Continuous"), "A_WE_BEZEICHNUNG": (5, "Continuous"),
    "A_TUER": (7, "Continuous"), "A_FENSTER": (7, "Continuous"), "A_BALKON": (8, "DASHED"),
    "A_TREPPE_AUFZUG": (7, "Continuous"), "A_EINRICHTUNG_KUECHE": (8, "Continuous"),
    "A_AENDERUNG": (2, "Continuous"), "A_HINWEIS_STATIK": (1, "DASHED"),
    "TGA_SCHACHT": (30, "Continuous"), "TGA_SCHACHT_BEZ": (30, "Continuous"),
    "ELT_TRASSE": (5, "DASHED"), "ELT_UV": (5, "Continuous"),
    "VAR_B_RAUM": (140, "Continuous"), "VAR_B_RAUMSTEMPEL": (140, "Continuous"),
    "VAR_B_TUER": (140, "Continuous"), "VAR_B_SCHACHT": (140, "Continuous"),
    "PLANKOPF": (7, "Continuous"),
}
for name, (col, lt) in LAYERS.items():
    doc.layers.add(name, color=col, linetype=lt)
doc.layers.get("VAR_B_RAUM").off()
for n in ("VAR_B_RAUMSTEMPEL", "VAR_B_TUER", "VAR_B_SCHACHT"):
    doc.layers.get(n).off()
doc.styles.add("PLAN", font="arial.ttf")


def box(x0, y0, x1, y1, layer, hatch=None, color=None, rgb=None):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})
    if hatch:
        h = msp.add_hatch(color=color or 256, dxfattribs={"layer": hatch[0]})
        if hatch[1] != "SOLID":
            h.set_pattern_fill(hatch[1], scale=hatch[2])
        if rgb:
            h.rgb = rgb
        h.paths.add_polyline_path(pts, is_closed=True)


def txt(s, x, y, hgt, layer, align=TextEntityAlignment.MIDDLE_CENTER, bold=False):
    t = msp.add_text(s, height=hgt, dxfattribs={"layer": layer, "style": "PLAN"})
    t.set_placement((x, y), align=align)
    return t


def stamp(rects, nr, name, area, layer, lab=None):
    x0, y0, x1, y1 = rects[0]
    cx, cy = lab if lab else ((x0 + x1) / 2, (y0 + y1) / 2)
    small = (x1 - x0) < 1.8
    hgt = 0.15 if small else 0.18
    if nr:
        txt(nr, cx, cy + hgt * 1.4, hgt * 0.7, layer)
    txt(name, cx, cy, hgt, layer)
    if area:
        txt(f"{area} m²", cx, cy - hgt * 1.3, hgt * 0.8, layer)


def door(kind, a0, a1, c, t, swing, layer):
    if not swing:
        return
    r = a1 - a0
    if kind == "h":
        yb = c + t / 2 if swing == "n" else c - t / 2
        sgn = 1 if swing == "n" else -1
        msp.add_line((a0, yb), (a0, yb + sgn * r), dxfattribs={"layer": layer})
        start, end = (0, 90) if swing == "n" else (270, 360)
        msp.add_arc((a0, yb), r, start, end, dxfattribs={"layer": layer})
    else:
        xb = c - t / 2 if swing == "w" else c + t / 2
        sgn = -1 if swing == "w" else 1
        msp.add_line((xb, a0), (xb + sgn * r, a0), dxfattribs={"layer": layer})
        start, end = (90, 180) if swing == "w" else (0, 90)
        msp.add_arc((xb, a0), r, start, end, dxfattribs={"layer": layer})


# ---------------------------------------------------------------- Rohbau ---
box(-0.30, g.Y1 - 0.30, 48.30, g.Y4 + 0.30, "A_AUSSENWAND_DAEMMUNG")
_h = msp.add_hatch(color=256, dxfattribs={"layer": "A_AUSSENWAND_DAEMMUNG"})
_h.set_pattern_fill("ANSI37", scale=0.02)
_h.paths.add_polyline_path([(-0.30, g.Y1 - 0.30), (48.30, g.Y1 - 0.30), (48.30, g.Y4 + 0.30), (-0.30, g.Y4 + 0.30)],
                           is_closed=True, flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
_h.paths.add_polyline_path([(-0.13, g.Y1 - 0.13), (48.13, g.Y1 - 0.13), (48.13, g.Y4 + 0.13), (-0.13, g.Y4 + 0.13)],
                           is_closed=True, flags=ezdxf.const.BOUNDARY_PATH_OUTERMOST)
box(-0.13, g.Y1 - 0.13, 48.13, g.Y4 + 0.13, "A_WAND_BESTAND")
box(0.13, g.S_BOT, 47.87, g.S_TOP, "A_WAND_BESTAND")
T = g.T_IN
corr_free = (g.bx(2) + 1.95, g.bx(6) + 5.20)
for k in range(1, 8):
    xa = 6.0 * k
    segs = [(g.S_BOT, g.S0), (g.N0, g.S_TOP)]
    if not (corr_free[0] < xa < corr_free[1]) and k not in (2, 7):
        segs.append((g.M0, g.M1))
    for y0, y1 in segs:
        box(xa - T / 2, y0, xa + T / 2, y1, "A_WAND_BESTAND", ("A_WAND_BESTAND_SCHRAFFUR", "ANSI31", 0.01))
for ya in (g.Y2, g.Y3):
    box(0.13, ya - T / 2, 47.87, ya + T / 2, "A_WAND_BESTAND", ("A_WAND_BESTAND_SCHRAFFUR", "ANSI31", 0.01))

# Balkone, TH 2, Fenster
for i in range(8):
    if i != 4:
        box(6 * i + 0.15, g.Y4 + 0.30, 6 * i + 5.85, g.Y4 + 1.52, "A_BALKON")
    box(6 * i + 0.15, g.Y1 - 1.52, 6 * i + 5.85, g.Y1 - 0.30, "A_BALKON")
    for a, b in ((0.55, 1.75), (2.95, 4.15), (4.45, 5.35)):
        if i != 4:
            box(6 * i + a, g.Y4 - 0.13, 6 * i + b, g.Y4 + 0.13, "A_FENSTER")
            msp.add_line((6 * i + a, g.Y4), (6 * i + b, g.Y4), dxfattribs={"layer": "A_FENSTER"})
    for a, b in ((0.50, 1.40), (1.70, 2.90), (4.10, 5.30)):
        box(6 * i + a, g.Y1 - 0.13, 6 * i + b, g.Y1 + 0.13, "A_FENSTER")
        msp.add_line((6 * i + a, g.Y1), (6 * i + b, g.Y1), dxfattribs={"layer": "A_FENSTER"})
box(27.00, g.Y4 + 0.30, 29.80, g.Y4 + 3.10, "A_TREPPE_AUFZUG")
txt("TH 2", 29.05, g.Y4 + 1.75, 0.18, "A_TREPPE_AUFZUG")
for k in range(14):
    yy = g.N0 + 0.6 + k * 0.30
    msp.add_line((g.bx(4) + 0.10, yy), (g.bx(4) + 1.05, yy), dxfattribs={"layer": "A_TREPPE_AUFZUG"})
    msp.add_line((g.bx(4) + 1.20, yy), (g.bx(4) + 2.15, yy), dxfattribs={"layer": "A_TREPPE_AUFZUG"})
ax0, ay0, ax1, ay1 = g.N(4, 2.45, 4.50, 2.95, 5.55)
msp.add_line((ax0, ay0), (ax1, ay1), dxfattribs={"layer": "A_TREPPE_AUFZUG"})
msp.add_line((ax0, ay1), (ax1, ay0), dxfattribs={"layer": "A_TREPPE_AUFZUG"})

# ---------------------------------------------------------------- Räume ----
VAR_B_ROOMS = {"1.05.00", "1.05.01", "1.05.02", "1.05.03", "1.09.00", "1.09.01", "1.09.02", "1.09.03"}
for rects, we, name, nr, area, changed, lab in g.rooms:
    for (x0, y0, x1, y1) in rects:
        box(x0, y0, x1, y1, "A_RAUM", ("A_AENDERUNG", "SOLID", 0) if changed else None, rgb=(255, 243, 184))
    stamp(rects, nr, name, area, "A_RAUMSTEMPEL", lab)

for kind, a0, a1, c, t, swing in g.doors:
    door(kind, a0, a1, c, t, swing, "A_TUER")

for (x0, y0, x1, y1) in g.kitchens:
    box(x0, y0, x1, y1, "A_EINRICHTUNG_KUECHE")

for we, (x, y, s) in g.we_lab.items():
    txt(f"WE {we}", x, y, 0.30, "A_WE_BEZEICHNUNG")
    txt(s, x, y - 0.32, 0.17, "A_WE_BEZEICHNUNG")

# Hinweis neue Türöffnungen (Statik)
for gx0, gx1, yc in ((g.bx(5) + 1.00, g.bx(5) + 2.20, g.Y3), (g.bx(5) + 3.60, g.bx(5) + 4.80, g.Y2)):
    box(gx0, yc - 0.22, gx1, yc + 0.22, "A_HINWEIS_STATIK")
    txt("! Statik prüfen", (gx0 + gx1) / 2, yc + (-0.42 if yc == g.Y3 else 0.42), 0.14, "A_HINWEIS_STATIK")

# ---------------------------------------------------------------- TGA ------
for sid, x0, y0, x1, y1, gw, wes, (tx, ty) in g.shafts:
    box(x0, y0, x1, y1, "TGA_SCHACHT", ("TGA_SCHACHT", "ANSI37", 0.01))
    txt(f"{sid}  {gw}", tx, ty, 0.20, "TGA_SCHACHT_BEZ")
    if abs(tx - (x0 + x1) / 2) > 0.6 or abs(ty - (y0 + y1) / 2) > 0.4:
        msp.add_line(((x0 + x1) / 2, (y0 + y1) / 2), (tx, ty), dxfattribs={"layer": "TGA_SCHACHT_BEZ"})
yt = (g.M0 + g.M1) / 2 - 0.05
msp.add_line((g.bx(2) + 2.3, yt), (g.bx(6) + 4.9, yt), dxfattribs={"layer": "ELT_TRASSE"})
msp.add_line((g.bx(4) + 5.55, g.N0 + 0.05), (g.bx(4) + 5.55, yt), dxfattribs={"layer": "ELT_TRASSE"})
for (x, y) in g.uv:
    box(x - 0.22, y - 0.10, x + 0.22, y + 0.15, "ELT_UV", ("ELT_UV", "SOLID", 0), color=5)
    txt("UV", x, y + (0.30 if y > g.Y3 - 0.5 else -0.30), 0.12, "ELT_UV")

# --------------------------------------------- Rückfallvariante B (Layer aus)
N, S, W, DN, DS, bx = g.N, g.S, g.W, g.DN, g.DS, g.bx
var_b = [
    ("1.05.01", "Bad", "3,86", [N(5, 0, 2.49, 0, 1.55)]),
    ("1.05.00", "Flur", "4,04", [N(5, 2.64, W, 0, 1.26)]),
    ("1.05.02", "Schlafen", "9,19", [N(5, 0, 2.465, 1.70, DN)]),
    ("1.05.03", "Wohnen / Kochen", "14,67", [N(5, 2.615, W, 1.41, DN)]),
    ("1.09.00", "Flur", "4,04", [S(5, 0, 3.21, 0, 1.26)]),
    ("1.09.01", "Bad", "3,86", [S(5, 3.36, W, 0, 1.55)]),
    ("1.09.03", "Wohnen / Kochen", "14,67", [S(5, 0, 3.235, 1.41, DS)]),
    ("1.09.02", "Schlafen", "9,19", [S(5, 3.385, W, 1.70, DS)]),
]
for nr, name, area, rects in var_b:
    for (x0, y0, x1, y1) in rects:
        box(x0, y0, x1, y1, "VAR_B_RAUM")
    stamp(rects, nr, name, area, "VAR_B_RAUMSTEMPEL")
for args in (("h", bx(5) + 3.70, bx(5) + 4.70, g.Y3, T, "n"), ("h", bx(5) + 1.10, bx(5) + 2.10, g.Y2, T, "s")):
    door(*args, "VAR_B_TUER")
box(bx(5), g.N0, bx(5) + 0.55, g.N0 + 0.45, "VAR_B_SCHACHT", ("VAR_B_SCHACHT", "ANSI37", 0.01))
box(bx(5) + 5.30, g.S0 - 0.45, bx(5) + W, g.S0, "VAR_B_SCHACHT", ("VAR_B_SCHACHT", "ANSI37", 0.01))
txt("Rückfallvariante B: WE 1.05 / 1.09 wie AP Index A (Layer VAR_B_*)", 33.0, -3.6, 0.20, "VAR_B_RAUMSTEMPEL")

# ---------------------------------------------------- Achsen, Bemaßung -----
for k, a in enumerate(g.AX):
    x = 6.0 * k
    msp.add_line((x, g.Y1 - 2.2), (x, g.Y4 + 3.4), dxfattribs={"layer": "A_ACHSEN"})
    for yc in (g.Y4 + 3.7, g.Y1 - 2.5):
        msp.add_circle((x, yc), 0.3, dxfattribs={"layer": "A_ACHSEN"})
        txt(a, x, yc, 0.28, "A_ACHSEN")
for lab, yy in (("1", g.Y1), ("2", g.Y2), ("3", g.Y3), ("4", g.Y4)):
    msp.add_line((-2.0, yy), (50.0, yy), dxfattribs={"layer": "A_ACHSEN"})
    for xc in (-2.3, 50.3):
        msp.add_circle((xc, yy), 0.3, dxfattribs={"layer": "A_ACHSEN"})
        txt(lab, xc, yy, 0.28, "A_ACHSEN")

dim_style = dict(dimstyle="EZDXF", override={"dimlfac": 1.0, "dimzin": 0, "dimtxt": 0.20, "dimasz": 0.12, "dimexe": 0.08, "dimexo": 0.10,
                                             "dimdec": 2, "dimdsep": ord(",")})
for k in range(8):
    msp.add_linear_dim(base=(0, g.Y1 - 3.3), p1=(6.0 * k, g.Y1 - 2.0), p2=(6.0 * k + 6.0, g.Y1 - 2.0),
                       dxfattribs={"layer": "A_BEMASSUNG"}, **dim_style).render()
msp.add_linear_dim(base=(0, g.Y1 - 3.9), p1=(0, g.Y1 - 2.0), p2=(48.0, g.Y1 - 2.0),
                   dxfattribs={"layer": "A_BEMASSUNG"}, **dim_style).render()
for a, b in ((g.Y1, g.Y2), (g.Y2, g.Y3), (g.Y3, g.Y4)):
    msp.add_linear_dim(base=(-3.2, 0), p1=(-1.0, a), p2=(-1.0, b), angle=90,
                       dxfattribs={"layer": "A_BEMASSUNG"}, **dim_style).render()
msp.add_linear_dim(base=(-3.8, 0), p1=(-1.0, g.Y1), p2=(-1.0, g.Y4), angle=90,
                   dxfattribs={"layer": "A_BEMASSUNG"}, **dim_style).render()

# Plankopf
txt("Schlegelstraße 3, 07747 Jena – Grundriss Regelgeschoss 1.–4. OG", 0, g.Y4 + 5.2, 0.45, "PLANKOPF",
    TextEntityAlignment.LEFT)
txt("Variante A: Bündelung der Installationsführung in Installationsknoten · Variantenstudie V2 · 29.10.2026 · "
    "Einheit m, M 1:100 · Geometrie schematisch, Maße am Bestand prüfen · Grundlage AP Index A",
    0, g.Y4 + 4.6, 0.22, "PLANKOPF", TextEntityAlignment.LEFT)

target = Path(__file__).with_name("Vorschlag_Installationsknoten_RG.dxf")
doc.saveas(target)
print(target)
