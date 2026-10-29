"""Schlegelstraße 3, Jena – Regelgeschoss 1.–4. OG
Vorschlag zur Bündelung der Installationsführung (Sanitär / Lüftung / Elektro).

Erzeugt ein Planblatt (SVG, A2 quer, Grundriss M 1:100) auf Basis der
Ausführungsplanung Index A (Pläne 301_A_H5_1051 / 301_A_H5_1301).
Geometrie schematisch im WBS-70-Achsraster; Raumflächen gem. Ausführungsplanung.

Aufruf:  python3 grundriss_vorschlag.py  ->  Vorschlag_Installationsknoten_RG.svg
"""

from pathlib import Path

# ---------------------------------------------------------------- Raster ----
AX = "ABCDEFGHI"                     # Querwandachsen, Achsmaß 6,00 m
Y1, Y2, Y3, Y4 = 0.0, 6.14, 8.14, 14.28   # Längsachsen 1–4
T_IN = 0.15                          # tragende Innenwände Bestand
FAC_IN = 0.13                        # Innenkante Außenwand ab Achse
S_TOP = Y4 - FAC_IN                  # Innenkante Nordfassade
S_BOT = Y1 + FAC_IN                  # Innenkante Südfassade
N0 = Y3 + T_IN / 2                   # Nordzone ab Flurwand
S0 = Y2 - T_IN / 2                   # Südzone ab Flurwand
M0, M1 = Y2 + T_IN / 2, Y3 - T_IN / 2   # Mittelzone (Flur), lichte 1,85 m

# Blatt (mm), Plan M 1:100 -> 1 m = 10 mm
SHEET_W, SHEET_H = 594, 420
OX, OY = 52, 52                      # Lage Achse A / Oberkante Bereich
SC = 10.0
TOPY = 17.6                          # obere Planbegrenzung in m


def px(x):
    return OX + x * SC


def py(y):
    return OY + (TOPY - y) * SC


def bx(i):
    """Innenkante West der Achsfeld-Nr. i (0 = A–B)."""
    return 6.0 * i + T_IN / 2


# ------------------------------------------------------------ Farben -------
WE_COL = {
    "1.01": "#e7eef7", "1.02": "#eef4e6", "1.03": "#f6efe3", "1.04": "#f1e9f4",
    "1.05": "#e5f2f0", "1.06": "#f4ede6", "1.07": "#eaf0e0", "1.08": "#eceaf6",
    "1.09": "#f6e9ec", "1.10": "#e8f1f6", "AG": "#f2f2f2",
}
CHG = "#fff3b8"           # geänderter Bereich ggü. AP Index A
WALL = "#3c3c3c"
BEARING = "#8f8f8f"
SHAFT = "#d9481c"

out = []


def add(s):
    out.append(s)


# --------------------------------------------------------------- Räume -----
rooms = []      # (rects[], we, name, nr, area, changed, label_pos)


def room(we, nr, name, area, rects, changed=False, lab=None):
    rooms.append((rects, we, name, nr, area, changed, lab))


def N(i, x0, x1, d0, d1):
    """Rechteck Nordzone: x lokal im Feld i, d = Abstand ab Flurwand."""
    return (bx(i) + x0, N0 + d0, bx(i) + x1, N0 + d1)


def S(i, x0, x1, d0, d1):
    return (bx(i) + x0, S0 - d1, bx(i) + x1, S0 - d0)


def M(gx0, gx1):
    return (gx0, M0, gx1, M1)


W = 5.85            # lichte Feldbreite
DN = S_TOP - N0     # 5,935
DS = S0 - S_BOT     # 5,935

# --- WE 1.02 (5-Raum) – unverändert
room("1.02", "1.02.06", "Wohnen / Essen", "34,59", [N(0, 0, W, 0, DN)])
room("1.02", "1.02.05", "Kochen", "5,18", [M(bx(0), bx(0) + 2.87)])
room("1.02", "1.02.00.2", "Diele", "2,05", [M(bx(0) + 3.02, bx(0) + 4.12)])
room("1.02", "1.02.07", "Gäste-Bad", "3,10", [M(bx(0) + 4.27, bx(0) + W)])
room("1.02", "1.02.08", "Bad", "4,17", [M(bx(1), bx(1) + 2.55)])
room("1.02", "1.02.09", "HWR", "2,52", [M(bx(1) + 2.70, bx(1) + 4.07)])
room("1.02", "1.02.00.1", "Flur", "5,73", [M(bx(1) + 4.22, bx(2) + 1.95)])
room("1.02", "1.02.00", "Flur", "10,48", [S(0, 3.15, W, 0, 1.35), S(1, 0, W, 0, 1.20),
                                         (bx(0) + W, S0 - 1.20, bx(1), S0 - 0.10)])
room("1.02", "1.02.04", "Schlafen", "17,95", [S(0, 0, 3.00, 0, DS)])
room("1.02", "1.02.03", "Kind 3", "11,94", [S(0, 3.15, W, 1.50, DS)])
room("1.02", "1.02.02", "Kind 2", "14,07", [S(1, 0, 3.06, 1.35, DS)])
room("1.02", "1.02.01", "Kind 1", "12,15", [S(1, 3.21, W, 1.35, DS)])

# --- WE 1.03 (2-Raum) – Küchenzeile an Achse D verlegt
room("1.03", "1.03.01", "Bad", "11,22", [N(1, 0, 1.90, 0, DN)])
room("1.03", "1.03.00", "Flur", "10,27", [N(1, 2.05, W, 0, 1.55), N(2, 0, 3.95, 0, 1.55),
                                         (bx(1) + W, N0 + 0.10, bx(2), N0 + 1.40)])
room("1.03", "1.03.02", "Schlafen", "16,20", [N(1, 2.05, W, 1.70, DN)])
room("1.03", "1.03.03", "Wohnen / Kochen", "24,76", [N(2, 0, W, 1.70, DN)], changed=True,
     lab=(bx(2) + 2.6, N0 + 3.9))
room("1.03", "1.03.04", "Abst.", "2,04", [N(2, 4.10, W, 0, 1.40)])

# --- WE 1.04 (1-Raum Typ I) – unverändert
room("1.04", "1.04.01", "Bad", "3,86", [N(3, 0, 2.49, 0, 1.55)])
room("1.04", "1.04.02", "Kochen", "3,28", [N(3, 0, 2.19, 1.70, 3.20)])
room("1.04", "1.04.03", "Schlafen", "4,78", [N(3, 0, 2.24, 3.80, DN)])
room("1.04", "1.04.00", "Flur", "4,04", [N(3, 2.64, W, 0, 1.26)])
room("1.04", "1.04.04", "Wohnen", "16,04", [N(3, 2.64, W, 1.41, DN), N(3, 2.34, 2.64, 1.70, DN),
                                           N(3, 0, 2.34, 3.35, 3.65)],
     lab=(bx(3) + 4.2, N0 + 3.6))

# --- Kern E–F (Bestand / AP)
room("AG", "1.00", "TH 1", "13,29", [N(4, 0, 2.25, 0, DN)])
room("AG", "1.00.03", "Aufzug-Vorraum", "14,10", [N(4, 2.40, W, 0, 2.80), N(4, 4.65, W, 2.80, DN)],
     lab=(bx(4) + 3.9, N0 + 1.55))
room("AG", "", "Aufzug", "", [N(4, 2.45, 4.50, 2.95, 5.55)])

# --- WE 1.05 (1-Raum Typ II) – Nassband getauscht: Bad an Achse G
room("1.05", "1.05.00", "Flur", "4,04", [N(5, 0, 3.21, 0, 1.26)], changed=True)
room("1.05", "1.05.01", "Bad", "3,86", [N(5, 3.36, W, 0, 1.55)], changed=True)
room("1.05", "1.05.02", "Schlafen", "≈ 9,90", [N(5, 0, 2.465, 1.41, DN)], changed=True)
room("1.05", "1.05.03", "Wohnen / Kochen", "≈ 13,90", [N(5, 2.615, W, 1.70, DN), N(5, 2.615, 3.21, 1.41, 1.70)],
     changed=True, lab=(bx(5) + 4.2, N0 + 3.9))

# --- WE 1.06 (1-Raum Typ II) – unverändert
room("1.06", "1.06.01", "Bad", "3,86", [N(6, 0, 2.49, 0, 1.55)])
room("1.06", "1.06.00", "Flur", "4,04", [N(6, 2.64, W, 0, 1.26)])
room("1.06", "1.06.02", "Schlafen", "9,19", [N(6, 0, 2.465, 1.70, DN)])
room("1.06", "1.06.03", "Wohnen / Kochen", "14,67", [N(6, 2.615, W, 1.41, DN)],
     lab=(bx(6) + 4.2, N0 + 3.9))

# --- WE 1.07 (3-Raum groß) – unverändert
room("1.07", "1.07.01", "Wohnen / Kochen", "31,18", [N(7, 0, 3.40, 0, 1.30), N(7, 0, W, 1.30, DN)],
     lab=(bx(7) + 2.6, N0 + 3.9))
room("1.07", "1.07.02", "HWR", "2,52", [N(7, 3.55, W, 0, 1.15)])
room("1.07", "1.07.00", "Flur", "7,87", [M(bx(6) + 5.20, bx(7) + 3.85)])
room("1.07", "1.07.03", "Bad", "6,91", [M(bx(7) + 4.00, bx(7) + W), S(7, 4.15, W, -0.15, 1.45)])
room("1.07", "1.07.05", "Schlafen", "16,30", [S(7, 0, 2.95, 0, DS)])
room("1.07", "1.07.04", "Kind 1", "13,25", [S(7, 3.10, W, 1.60, DS), S(7, 3.10, 4.00, 0, 1.60)],
     lab=(bx(7) + 4.45, S0 - 3.7))

# --- Allgemeinflur
room("AG", "1.00.01/02", "Flur (Unterdecke)", "22,80 + 26,86", [M(bx(2) + 2.10, bx(6) + 5.05)],
     lab=(22.0, M1 - 0.55))

# --- WE 1.01 (3-Raum klein) – Küche an Bad-Installationswand, WM ins Bad
room("1.01", "1.01.05", "Wohnen / Kochen", "19,24", [S(2, 0, 3.40, 0, DS)], changed=True,
     lab=(bx(2) + 1.55, S0 - 3.2))
room("1.01", "1.01.00", "Flur", "9,69", [S(2, 3.55, W, 0, 2.15), S(3, 0, 4.35, 0, 1.15),
                                        (bx(2) + W, S0 - 1.05, bx(3), S0 - 0.10)],
     lab=(bx(3) + 1.0, S0 - 0.6))
room("1.01", "1.01.04", "Bad + WM", "7,53", [S(2, 3.55, W, 2.30, DS)], changed=True)
room("1.01", "1.01.03", "Schlafen", "14,38", [S(3, 0, 3.12, 1.30, DS)])
room("1.01", "1.01.02", "Kind 1", "11,12", [S(3, 3.27, W, 1.60, DS)])
room("1.01", "1.01.01", "Abst.", "2,17", [S(3, 4.50, W, 0, 1.45)], changed=True)

# --- WE 1.10 (1-Raum Typ I, gespiegelt) – unverändert
room("1.10", "1.10.00", "Flur", "4,04", [S(4, 0, 3.21, 0, 1.26)])
room("1.10", "1.10.01", "Bad", "3,86", [S(4, 3.36, W, 0, 1.55)])
room("1.10", "1.10.02", "Kochen", "3,28", [S(4, 3.66, W, 1.70, 3.20)])
room("1.10", "1.10.03", "Schlafen", "4,79", [S(4, 3.61, W, 3.80, DS)])
room("1.10", "1.10.04", "Wohnen", "16,03", [S(4, 0, 3.21, 1.41, DS), S(4, 3.21, 3.51, 1.70, DS),
                                           S(4, 3.51, W, 3.35, 3.65)],
     lab=(bx(4) + 1.6, S0 - 3.7))

# --- WE 1.09 (1-Raum Typ II) – Nassband getauscht: Bad an Achse F
room("1.09", "1.09.01", "Bad", "3,86", [S(5, 0, 2.49, 0, 1.55)], changed=True)
room("1.09", "1.09.00", "Flur", "4,04", [S(5, 2.64, W, 0, 1.26)], changed=True)
room("1.09", "1.09.03", "Wohnen / Kochen", "≈ 13,90", [S(5, 0, 3.235, 1.70, DS), S(5, 2.64, 3.235, 1.41, 1.70)],
     changed=True, lab=(bx(5) + 1.6, S0 - 3.9))
room("1.09", "1.09.02", "Schlafen", "≈ 9,90", [S(5, 3.385, W, 1.41, DS)], changed=True)

# --- WE 1.08 (1-Raum Typ III) – unverändert
room("1.08", "1.08.00", "Flur", "4,04", [S(6, 0, 3.21, 0, 1.26)])
room("1.08", "1.08.01", "Bad", "3,86", [S(6, 3.36, W, 0, 1.55)])
room("1.08", "1.08.02", "Kochen", "3,73", [S(6, 3.36, W, 1.70, 3.20)])
room("1.08", "1.08.03", "Schlafen", "6,50", [S(6, 3.36, W, 3.35, DS)])
room("1.08", "1.08.04", "Wohnen", "13,56", [S(6, 0, 3.21, 1.41, DS)])

# ------------------------------------------------------- Öffnungen ---------
# ("h", x0, x1, y_wall_center, thickness) / ("v", y0, y1, x_wall_center, thickness)
doors = []


def dh(gx0, gx1, yc, t=T_IN, swing=None):
    doors.append(("h", gx0, gx1, yc, t, swing))


def dv(gy0, gy1, xc, t=T_IN, swing=None):
    doors.append(("v", gy0, gy1, xc, t, swing))


# Wohnungseingänge / Treppenhaus an Flurwänden
dh(bx(2) + 2.40, bx(2) + 3.40, Y3, swing="n")      # 1.03
dh(bx(3) + 3.30, bx(3) + 4.30, Y3, swing="n")      # 1.04
dh(bx(5) + 1.10, bx(5) + 2.10, Y3, swing="n")      # 1.05 (neu)
dh(bx(6) + 3.70, bx(6) + 4.70, Y3, swing="n")      # 1.06
dh(bx(4) + 0.70, bx(4) + 1.70, Y3, swing="n")      # TH 1
dh(bx(4) + 2.80, bx(4) + 4.60, Y3)                 # Aufzug-Vorraum
dh(bx(3) + 1.20, bx(3) + 2.20, Y2, swing="s")      # 1.01
dh(bx(4) + 1.10, bx(4) + 2.10, Y2, swing="s")      # 1.10
dh(bx(5) + 3.70, bx(5) + 4.70, Y2, swing="s")      # 1.09 (neu)
dh(bx(6) + 1.10, bx(6) + 2.10, Y2, swing="s")      # 1.08
dv(M0 + 0.40, M0 + 1.40, bx(2) + 2.025, 0.15, swing="w")  # 1.02
dv(M0 + 0.40, M0 + 1.40, bx(6) + 5.125, 0.15, swing="e")  # 1.07
# WE 1.02 intern
dh(bx(0) + 0.80, bx(0) + 2.00, Y3)
dh(bx(0) + 3.15, bx(0) + 4.00, Y3)
dv(M0 + 0.50, M0 + 1.30, bx(0) + 4.195, 0.15, swing="e")
dh(bx(1) + 0.70, bx(1) + 1.55, Y2, swing="n")
dh(bx(1) + 2.90, bx(1) + 3.75, Y2, swing="n")
dh(bx(1) + 4.50, bx(1) + 5.40, Y2)
dh(bx(0) + 3.60, bx(0) + 4.45, S0 - 1.425, 0.15, swing="s")
dv(S0 - 1.10, S0 - 0.25, bx(0) + 3.075, 0.15, swing="w")
dh(bx(1) + 1.00, bx(1) + 1.85, S0 - 1.275, 0.15, swing="s")
dh(bx(1) + 4.00, bx(1) + 4.85, S0 - 1.275, 0.15, swing="s")
# WE 1.03
dv(N0 + 0.25, N0 + 1.10, bx(1) + 1.975, 0.15, swing="w")
dh(bx(1) + 4.60, bx(1) + 5.45, N0 + 1.625, 0.15, swing="n")
dh(bx(2) + 1.20, bx(2) + 2.40, N0 + 1.625, 0.15)
dv(N0 + 0.25, N0 + 1.10, bx(2) + 4.025, 0.15, swing="e")
# WE 1.04
dv(N0 + 0.25, N0 + 1.05, bx(3) + 2.565, 0.15, swing="w")
dh(bx(3) + 0.40, bx(3) + 1.50, N0 + 3.50, 0.30)
dh(bx(3) + 3.00, bx(3) + 3.90, N0 + 1.335, 0.15)
# WE 1.05 (neu)
dh(bx(5) + 0.70, bx(5) + 1.55, N0 + 1.335, 0.15, swing="n")
dv(N0 + 0.20, N0 + 1.00, bx(5) + 3.285, 0.15, swing="e")
# WE 1.06
dv(N0 + 0.25, N0 + 1.05, bx(6) + 2.565, 0.15, swing="w")
dh(bx(6) + 0.70, bx(6) + 1.55, N0 + 1.625, 0.15, swing="n")
# WE 1.07
dh(bx(7) + 1.50, bx(7) + 2.50, Y3)
dh(bx(7) + 1.00, bx(7) + 1.90, Y2, swing="s")
dh(bx(7) + 3.15, bx(7) + 3.95, Y2, swing="s")
dv(M0 + 0.40, M0 + 1.20, bx(7) + 3.925, 0.15, swing="e")
dh(bx(7) + 4.10, bx(7) + 5.00, Y3)
# WE 1.01
dv(S0 - 1.25, S0 - 0.35, bx(2) + 3.475, 0.15, swing="w")
dh(bx(2) + 4.50, bx(2) + 5.35, S0 - 2.225, 0.15, swing="s")
dh(bx(3) + 1.50, bx(3) + 2.35, S0 - 1.225, 0.15, swing="s")
dh(bx(3) + 3.40, bx(3) + 4.20, S0 - 1.375, 0.15, swing="s")
dv(S0 - 1.10, S0 - 0.30, bx(3) + 4.425, 0.15, swing="e")
# WE 1.10
dv(S0 - 1.10, S0 - 0.30, bx(4) + 3.285, 0.15, swing="e")
dh(bx(4) + 1.20, bx(4) + 2.10, S0 - 1.335, 0.15)
dh(bx(4) + 4.00, bx(4) + 5.00, S0 - 1.625, 0.30)
dh(bx(4) + 4.20, bx(4) + 5.10, S0 - 3.50, 0.30, swing="s")
# WE 1.09 (neu)
dv(S0 - 1.00, S0 - 0.20, bx(5) + 2.565, 0.15, swing="w")
dh(bx(5) + 2.70, bx(5) + 3.20, S0 - 1.335, 0.15)
dh(bx(5) + 4.30, bx(5) + 5.15, S0 - 1.335, 0.15, swing="s")
# WE 1.08
dv(S0 - 1.10, S0 - 0.30, bx(6) + 3.285, 0.15, swing="e")
dh(bx(6) + 1.20, bx(6) + 2.10, S0 - 1.335, 0.15)
dh(bx(6) + 3.80, bx(6) + 4.80, S0 - 1.625, 0.30)
dh(bx(6) + 3.80, bx(6) + 4.70, S0 - 3.275, 0.15, swing="s")
# Querwand-Durchgänge innerhalb WE
dv(N0 + 0.10, N0 + 1.40, 12.0, T_IN)      # 1.03 Achse C
dv(S0 - 1.10, S0 - 0.10, 6.0, T_IN)       # 1.02 Achse B
dv(S0 - 1.05, S0 - 0.10, 18.0, T_IN)      # 1.01 Achse D

# --------------------------------------------------------- Schächte --------
# id, x0, y0, x1, y1 (m), Gewerke, versorgte WE, Lage des Etiketts (dx, dy in mm)
shafts = [
    ("IS 1", bx(1), M1 - 0.45, bx(1) + 0.55, M1, "S · L",
     "WE 1.02 Bad, Gäste-Bad, HWR, Küche · WE 1.03 Bad", (bx(1) + 0.95, N0 + 0.75)),
    ("IS 2", bx(3), N0, bx(3) + 0.55, N0 + 0.45, "S · L",
     "WE 1.03 Küche · WE 1.04 Bad + Küche", (bx(3) + 0.30, M1 - 0.42)),
    ("IS 3", bx(2) + 3.55, S0 - 2.75, bx(2) + 4.10, S0 - 2.30, "S · L",
     "WE 1.01 Bad, WM, Küche", (bx(2) + 4.85, S0 - 3.05)),
    ("IS 4", bx(4) + 5.30, N0, bx(4) + W, N0 + 0.45, "E · M",
     "Elektro-/Medien-Hauptsteiger, alle WE", (bx(4) + 4.35, N0 + 0.40)),
    ("IS 5", bx(4) + 5.30, S0 - 0.45, bx(4) + W, S0, "S · L",
     "WE 1.10 · WE 1.09", (bx(4) + 5.55, M0 + 0.40)),
    ("IS 6", bx(6), N0, bx(6) + 0.55, N0 + 0.45, "S · L",
     "WE 1.05 · WE 1.06", (bx(6) + 0.30, M1 - 0.42)),
    ("IS 7", bx(6) + 5.30, S0 - 0.45, bx(6) + W, S0, "S · L",
     "WE 1.08", (bx(6) + 5.55, M0 + 0.40)),
    ("IS 8", bx(7) + 5.30, M1 - 0.45, bx(7) + W, M1, "S · L",
     "WE 1.07 Bad, HWR, Küche", (48.0 + 1.55, M1 + 0.75)),
]

# Küchenzeilen / Sanitärobjekte (schematisch)
kitchens = [
    N(2, 5.25, W, 1.75, 4.10),           # 1.03 an Achse D (neu)
    N(3, 0.0, 0.60, 1.75, 3.15),         # 1.04
    N(5, 3.40, W, 1.75, 2.35),           # 1.05 an Badrückwand (neu)
    N(6, 2.66, 3.26, 1.46, 3.30),        # 1.06
    N(7, 5.25, W, 1.35, 3.60),           # 1.07
    S(2, 2.80, 3.40, 2.40, 5.00),        # 1.01 an Badwand (neu)
    S(4, 5.25, W, 1.75, 3.15),           # 1.10
    S(5, 0.0, 2.45, 1.75, 2.35),         # 1.09 an Badrückwand (neu)
    S(6, 5.25, W, 1.75, 3.15),           # 1.08
    M(bx(0), bx(0) + 0.60),              # 1.02
]

# Bestandsstandorte lt. AP Index A (schematisch, für Übersicht)
bestand = [
    (bx(1) + 0.3, N0 + 1.5), (bx(2) + 0.5, N0 + 1.9), (bx(3) + 0.3, N0 + 0.3),
    (bx(5) + 0.3, N0 + 0.3), (bx(6) + 0.3, N0 + 0.3), (bx(7) + 5.5, N0 + 1.6),
    (bx(0) + 2.6, M1 - 0.3), (bx(0) + 5.5, M1 - 0.3), (bx(1) + 0.3, M1 - 0.3),
    (bx(2) + 0.6, M0 + 0.9), (bx(7) + 5.5, M0 + 0.6),
    (bx(2) + 0.6, S0 - 0.3), (bx(2) + 5.5, S0 - 2.6), (bx(3) + 5.5, S0 - 0.3),
    (bx(4) + 5.5, S0 - 0.3), (bx(5) + 5.5, S0 - 0.3), (bx(6) + 5.5, S0 - 0.3),
]
bestand_kern = (bx(4) + 5.5, N0 + 0.3)


# ============================================================ Zeichnen ======
def rect(x0, y0, x1, y1, **kw):
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    X0, X1 = px(min(x0, x1)), px(max(x0, x1))
    Yt, Yb = py(max(y0, y1)), py(min(y0, y1))
    return f'<rect x="{X0:.2f}" y="{Yt:.2f}" width="{X1 - X0:.2f}" height="{Yb - Yt:.2f}" {a}/>'


def text(x, y, s, size=2.2, anchor="middle", weight="normal", fill="#1d1d1d", extra=""):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{fill}" {extra}>{s}</text>')


def line(x0, y0, x1, y1, stroke="#1d1d1d", w=0.18, extra=""):
    return f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{stroke}" stroke-width="{w}" {extra}/>'


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}mm" height="{SHEET_H}mm" '
    f'viewBox="0 0 {SHEET_W} {SHEET_H}" font-family="Arial Narrow, Arial, Helvetica, sans-serif">')
add("""<defs>
<pattern id="hBear" width="1.2" height="1.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<rect width="1.2" height="1.2" fill="#9a9a9a"/><line x1="0" y1="0" x2="0" y2="1.2" stroke="#6a6a6a" stroke-width="0.35"/></pattern>
<pattern id="hIns" width="1.0" height="1.0" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
<rect width="1" height="1" fill="#fbfbfb"/><line x1="0" y1="0" x2="0" y2="1" stroke="#b5b5b5" stroke-width="0.2"/></pattern>
<pattern id="hShaft" width="0.9" height="0.9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<rect width="0.9" height="0.9" fill="#fbd9cc"/><line x1="0" y1="0" x2="0" y2="0.9" stroke="#d9481c" stroke-width="0.35"/></pattern>
<pattern id="hKit" width="0.8" height="0.8" patternUnits="userSpaceOnUse">
<rect width="0.8" height="0.8" fill="#ffffff"/><circle cx="0.4" cy="0.4" r="0.12" fill="#8a8a8a"/></pattern>
</defs>""")
add(f'<rect width="{SHEET_W}" height="{SHEET_H}" fill="#ffffff"/>')
add(f'<rect x="8" y="8" width="{SHEET_W - 16}" height="{SHEET_H - 16}" fill="none" stroke="#1d1d1d" stroke-width="0.5"/>')

# Kopfzeile
add(text(14, 19, "Schlegelstraße 3, 07747 Jena – Grundriss Regelgeschoss 1.–4. OG", 6.2, "start", "bold"))
add(text(14, 27, "Variantenvorschlag: Bündelung der Installationsführung Sanitär / Lüftung / Elektro "
         "in gemeinsamen Installationsknoten", 3.6, "start"))
add(text(14, 33, "Grundlage: Ausführungsplanung Index A, Pläne 301_A_H5_1051 (GR 1.OG) und 301_A_H5_1301 "
         "(GR Rohbau 1.OG), Stand 27.08.2026 · Geometrie schematisch im WBS-70-Raster · M 1:100 (A2)",
         2.4, "start", fill="#555"))

# Balkone / TH 2
for i in range(8):
    if i != 4:
        add(rect(6 * i + 0.15, Y4 + 0.30, 6 * i + 5.85, Y4 + 1.52, fill="none", stroke="#7a7a7a",
                 stroke_width=0.18, stroke_dasharray="1,0.6"))
        add(text(px(6 * i + 3.0), py(Y4 + 0.80), "Balkon", 1.7, fill="#7a7a7a"))
    add(rect(6 * i + 0.15, Y1 - 1.52, 6 * i + 5.85, Y1 - 0.30, fill="none", stroke="#7a7a7a",
             stroke_width=0.18, stroke_dasharray="1,0.6"))
    add(text(px(6 * i + 3.0), py(Y1 - 1.05), "Balkon", 1.7, fill="#7a7a7a"))
add(rect(27.00, Y4 + 0.30, 29.80, Y4 + 3.10, fill="#f2f2f2", stroke="#1d1d1d", stroke_width=0.35))
for k in range(9):
    yy = Y4 + 0.55 + k * 0.28
    add(line(px(27.15), py(yy), px(28.30), py(yy), w=0.12))
add(text(px(29.05), py(Y4 + 1.75), "TH 2", 1.9, extra='font-style="italic"'))

# Wärmedämmung + Wandkörper (Hintergrund = Wandfarbe)
add(rect(-0.30, Y1 - 0.30, 48.30, Y4 + 0.30, fill="url(#hIns)", stroke="#1d1d1d", stroke_width=0.2))
add(rect(-0.13, Y1 - 0.13, 48.13, Y4 + 0.13, fill=WALL))

# Räume
for rects, we, name, nr, area, changed, lab in rooms:
    col = CHG if changed else WE_COL[we]
    for (x0, y0, x1, y1) in rects:
        add(rect(x0, y0, x1, y1, fill=col))

# Tragende Wände Bestand (Querwände Achsen B–H, Flurlängswände Achsen 2/3)
corr_free = [(bx(2) + 1.95, bx(6) + 5.20)]   # Querwände in Flurzone öffentlich unterbrochen
for k in range(1, 8):
    xa = 6.0 * k
    add(rect(xa - T_IN / 2, S_BOT, xa + T_IN / 2, S0, fill="url(#hBear)"))
    add(rect(xa - T_IN / 2, N0, xa + T_IN / 2, S_TOP, fill="url(#hBear)"))
    if not any(a < xa < b for a, b in corr_free) and k not in (2, 7):
        add(rect(xa - T_IN / 2, M0, xa + T_IN / 2, M1, fill="url(#hBear)"))
for ya in (Y2, Y3):
    add(rect(0.0, ya - T_IN / 2, 48.0, ya + T_IN / 2, fill="url(#hBear)"))
# Wandöffnung Achse 2 für Bad 1.07.03 (L-Form gem. AP)
add(rect(bx(7) + 4.15, Y2 - T_IN / 2 - 0.01, bx(7) + W, Y2 + T_IN / 2 + 0.01, fill=WE_COL["1.07"]))
add(rect(-0.13, Y1 - 0.13, 48.13, Y4 + 0.13, fill="none", stroke="#1d1d1d", stroke_width=0.3))
add(rect(0.13, S_BOT, 47.87, S_TOP, fill="none", stroke="#1d1d1d", stroke_width=0.12))

# Fenster (schematisch)
for i in range(8):
    x = 6 * i
    for a, b, door in ((0.55, 1.75, False), (2.95, 4.15, False), (4.45, 5.35, True)):
        if i == 4:
            continue
        add(rect(x + a, Y4 - 0.13, x + b, Y4 + 0.13, fill="#ffffff", stroke="#1d1d1d", stroke_width=0.12))
        add(line(px(x + a), py(Y4), px(x + b), py(Y4), w=0.12))
    for a, b in ((0.50, 1.40), (1.70, 2.90), (4.10, 5.30)):
        add(rect(x + a, Y1 - 0.13, x + b, Y1 + 0.13, fill="#ffffff", stroke="#1d1d1d", stroke_width=0.12))
        add(line(px(x + a), py(Y1), px(x + b), py(Y1), w=0.12))
add(rect(-0.13, M0 + 0.40, 0.13, M1 - 0.40, fill="#ffffff", stroke="#1d1d1d", stroke_width=0.12))

# Türen / Öffnungen
for kind, a0, a1, c, t, swing in doors:
    if kind == "h":
        add(rect(a0, c - t / 2 - 0.01, a1, c + t / 2 + 0.01, fill="#ffffff"))
        if swing:
            r = (a1 - a0) * SC
            sgn = -1 if swing == "n" else 1
            yb = py(c + t / 2) if swing == "n" else py(c - t / 2)
            add(f'<path d="M {px(a0):.2f} {yb:.2f} L {px(a0):.2f} {yb + sgn * r:.2f} '
                f'A {r:.2f} {r:.2f} 0 0 {1 if swing == "n" else 0} {px(a1):.2f} {yb:.2f}" '
                f'fill="none" stroke="#666" stroke-width="0.12"/>')
    else:
        add(rect(c - t / 2 - 0.01, a0, c + t / 2 + 0.01, a1, fill="#ffffff"))
        if swing:
            r = (a1 - a0) * SC
            sgn = -1 if swing == "w" else 1
            xb = px(c - t / 2) if swing == "w" else px(c + t / 2)
            add(f'<path d="M {xb:.2f} {py(a0):.2f} L {xb + sgn * r:.2f} {py(a0):.2f} '
                f'A {r:.2f} {r:.2f} 0 0 {0 if swing == "w" else 1} {xb:.2f} {py(a1):.2f}" '
                f'fill="none" stroke="#666" stroke-width="0.12"/>')

# Neue Türöffnungen in tragender Flurwand (WE 1.05 / 1.09) – Statik prüfen
for (gx0, gx1, yc, ty) in ((bx(5) + 1.00, bx(5) + 2.20, Y3, M1 - 0.42), (bx(5) + 3.60, bx(5) + 4.80, Y2, M0 + 0.42)):
    add(rect(gx0, yc - 0.22, gx1, yc + 0.22, fill="none", stroke="#c00000", stroke_width=0.35,
             stroke_dasharray="1,0.6"))
    add(f'<circle cx="{px((gx0 + gx1) / 2):.2f}" cy="{py(ty):.2f}" r="1.9" fill="#c00000"/>')
    add(text(px((gx0 + gx1) / 2), py(ty) + 0.9, "!", 2.6, weight="bold", fill="#ffffff"))

# Treppe TH 1 / Aufzug
for k in range(14):
    yy = N0 + 0.6 + k * 0.30
    add(line(px(bx(4) + 0.10), py(yy), px(bx(4) + 1.05), py(yy), w=0.12))
    add(line(px(bx(4) + 1.20), py(yy), px(bx(4) + 2.15), py(yy), w=0.12))
ax0, ay0, ax1, ay1 = N(4, 2.45, 4.50, 2.95, 5.55)
add(line(px(ax0), py(ay0), px(ax1), py(ay1), w=0.15))
add(line(px(ax0), py(ay1), px(ax1), py(ay0), w=0.15))

# Küchenzeilen
for (x0, y0, x1, y1) in kitchens:
    add(rect(x0, y0, x1, y1, fill="url(#hKit)", stroke="#555", stroke_width=0.12))

# Raumstempel
for rects, we, name, nr, area, changed, lab in rooms:
    if lab is None:
        x0, y0, x1, y1 = rects[0]
        lab = ((x0 + x1) / 2, (y0 + y1) / 2)
    X, Y = px(lab[0]), py(lab[1])
    small = name in ("Abst.", "Diele", "HWR", "Gäste-Bad") or (rects[0][2] - rects[0][0]) < 1.8
    fs = 1.75 if small else 2.15
    if nr:
        add(text(X, Y - fs * 1.05, nr, fs * 0.72, fill="#666"))
    add(text(X, Y + 0.2, name, fs, weight="bold"))
    if area:
        add(text(X, Y + fs * 1.15, f"{area} m²", fs * 0.8))

# WE-Bezeichnungen
we_lab = {
    "1.02": (3.0, 12.6, "5-Raum · 123,93 m²"), "1.03": (9.0, 12.85, "2-Raum · 64,49 m²"),
    "1.04": (22.2, 13.4, "1-Raum Typ I · 32,00 m²"), "1.05": (34.3, 13.4, "1-Raum Typ II · ≈ 31,71 m²"),
    "1.06": (40.3, 13.4, "1-Raum Typ II · 31,76 m²"), "1.07": (44.6, 12.85, "3-Raum groß · 78,03 m²"),
    "1.01": (19.6, 0.95, "3-Raum klein · 64,13 m²"), "1.10": (25.8, 0.95, "1-Raum Typ I · 32,00 m²"),
    "1.09": (31.6, 0.95, "1-Raum Typ II · ≈ 31,71 m²"), "1.08": (37.6, 0.95, "1-Raum Typ III · 31,69 m²"),
}
for we, (x, y, s) in we_lab.items():
    add(text(px(x), py(y), f"WE {we}", 2.9, weight="bold", fill="#1f4e79"))
    add(text(px(x), py(y) + 2.7, s, 1.9, fill="#1f4e79"))

# Elektro-Trasse Flur-Unterdecke + Unterverteilungen
ty = py((M0 + M1) / 2 - 0.05)
add(line(px(bx(2) + 2.3), ty, px(bx(6) + 4.9), ty, stroke="#1565c0", w=0.35, extra='stroke-dasharray="1.6,0.8"'))
add(line(px(bx(4) + 5.55), py(N0 + 0.05), px(bx(4) + 5.55), ty, stroke="#1565c0", w=0.35,
         extra='stroke-dasharray="1.6,0.8"'))
uv = [(bx(2) + 1.80, M0 + 0.15), (bx(2) + 3.55, N0 + 0.05), (bx(3) + 4.45, N0 + 0.05),
      (bx(5) + 0.80, N0 + 0.05), (bx(6) + 4.85, N0 + 0.05), (bx(7) + 1.00, M1 - 0.30),
      (bx(3) + 2.35, S0 - 0.30), (bx(4) + 0.80, S0 - 0.30), (bx(5) + 5.45, S0 - 0.30),
      (bx(6) + 0.80, S0 - 0.30)]
for (x, y) in uv:
    add(rect(x - 0.22, y - 0.10, x + 0.22, y + 0.15, fill="#1565c0"))
    add(text(px(x), py(y) - 0.9 if y > Y3 - 0.5 else py(y) + 3.0, "UV", 1.4, fill="#1565c0", weight="bold"))

# Schächte + Etiketten
for sid, x0, y0, x1, y1, gw, wes, (tx, ty) in shafts:
    add(rect(x0, y0, x1, y1, fill="url(#hShaft)", stroke=SHAFT, stroke_width=0.35))
    cx, cy = px((x0 + x1) / 2), py((y0 + y1) / 2)
    X, Y = px(tx), py(ty)
    if abs(X - cx) > 6 or abs(Y - cy) > 4:
        add(line(cx, cy, X, Y, stroke=SHAFT, w=0.22))
    add(f'<rect x="{X - 6.5:.2f}" y="{Y - 2.1:.2f}" width="13" height="4.2" rx="0.8" fill="#ffffff" '
        f'stroke="{SHAFT}" stroke-width="0.3"/>')
    add(text(X - 5.6, Y + 0.85, sid, 2.3, "start", "bold", SHAFT))
    add(text(X + 5.8, Y + 0.85, gw, 1.9, "end", "bold", "#1d1d1d"))

# Achsen + Bemaßung
for k, a in enumerate(AX):
    X = px(6.0 * k)
    for Yc in (py(TOPY) + 1.0, py(Y1 - 1.52) + 4.6):
        add(f'<circle cx="{X:.2f}" cy="{Yc:.2f}" r="2.6" fill="#fff" stroke="#1d1d1d" stroke-width="0.25"/>')
        add(text(X, Yc + 1.0, a, 2.8))
    add(line(X, py(TOPY) + 3.6, X, py(Y1 - 1.52) + 2.0, stroke="#9a9a9a", w=0.12, extra='stroke-dasharray="3,1,0.6,1"'))
for lab, yy in (("1", Y1), ("2", Y2), ("3", Y3), ("4", Y4)):
    Y = py(yy)
    for Xc in (OX - 22, px(48.0) + 22):
        add(f'<circle cx="{Xc:.2f}" cy="{Y:.2f}" r="2.6" fill="#fff" stroke="#1d1d1d" stroke-width="0.25"/>')
        add(text(Xc, Y + 1.0, lab, 2.8))
    add(line(OX - 19.4, Y, px(48.0) + 19.4, Y, stroke="#9a9a9a", w=0.12, extra='stroke-dasharray="3,1,0.6,1"'))


def dim_h(x0, x1, y, lab):
    add(line(px(x0), y, px(x1), y, w=0.15))
    for x in (x0, x1):
        add(line(px(x) - 0.8, y + 0.8, px(x) + 0.8, y - 0.8, w=0.25))
        add(line(px(x), y - 1.4, px(x), y + 1.4, w=0.12))
    add(text((px(x0) + px(x1)) / 2, y - 0.8, lab, 2.0))


def dim_v(y0, y1, x, lab):
    add(line(x, py(y0), x, py(y1), w=0.15))
    for yy in (y0, y1):
        add(line(x - 0.8, py(yy) + 0.8, x + 0.8, py(yy) - 0.8, w=0.25))
        add(line(x - 1.4, py(yy), x + 1.4, py(yy), w=0.12))
    ym = (py(y0) + py(y1)) / 2
    add(f'<text x="{x - 1.0:.2f}" y="{ym:.2f}" font-size="2.0" text-anchor="middle" '
        f'transform="rotate(-90 {x - 1.0:.2f} {ym:.2f})">{lab}</text>')


yd = py(Y1 - 1.52) + 12.5
for k in range(8):
    dim_h(6.0 * k, 6.0 * k + 6.0, yd, "6,00")
dim_h(0, 48.0, yd + 5.0, "48,00")
xd = OX - 8
for (a, b, s) in ((Y1, Y2, "6,14"), (Y2, Y3, "2,00"), (Y3, Y4, "6,14")):
    dim_v(a, b, xd, s)
dim_v(Y1, Y4, xd - 5, "14,28")

# Nordpfeil
nx, ny = px(48.0) + 22, py(TOPY) + 10
add(f'<circle cx="{nx}" cy="{ny}" r="5" fill="none" stroke="#1d1d1d" stroke-width="0.25"/>')
add(f'<path d="M {nx} {ny - 6} L {nx + 2} {ny + 3} L {nx} {ny + 1.6} L {nx - 2} {ny + 3} Z" fill="#1d1d1d"/>')
add(text(nx, ny - 7, "N", 2.6, weight="bold"))

# ===================================================== unterer Bereich ======
BY = 272
add(line(8, BY - 6, SHEET_W - 8, BY - 6, w=0.35))

# --- Übersicht Bestand vs. Vorschlag (M 1:400)
def mini(ox, oy, title, pts, knots):
    s = 2.2     # mm je m
    def X(x): return ox + x * s
    def Y(y): return oy + (Y4 - y) * s
    add(text(ox, oy - 4.2, title, 2.9, "start", "bold"))
    add(f'<rect x="{X(0):.2f}" y="{Y(Y4):.2f}" width="{48 * s:.2f}" height="{Y4 * s:.2f}" fill="#fafafa" '
        f'stroke="#1d1d1d" stroke-width="0.3"/>')
    for k in range(1, 8):
        add(line(X(6 * k), Y(Y4), X(6 * k), Y(Y3), stroke="#888", w=0.25))
        add(line(X(6 * k), Y(Y2), X(6 * k), Y(Y1), stroke="#888", w=0.25))
    for yy in (Y2, Y3):
        add(line(X(0), Y(yy), X(48), Y(yy), stroke="#888", w=0.25))
    add(f'<rect x="{X(24.1):.2f}" y="{Y(Y4):.2f}" width="{5.8 * s:.2f}" height="{(Y4 - Y3) * s:.2f}" '
        f'fill="#e3e3e3"/>')
    for k, a in enumerate(AX):
        add(text(X(6 * k), Y(Y4) - 1.0, a, 1.8, fill="#555"))
    for (x, y) in pts:
        add(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="1.05" fill="{SHAFT}"/>')
    for (x, y, col) in knots:
        add(f'<rect x="{X(x) - 1.5:.2f}" y="{Y(y) - 1.5:.2f}" width="3" height="3" fill="{col}"/>')
    return Y(Y1)


knots_v = [(((s[1] + s[3]) / 2), ((s[2] + s[4]) / 2), "#1565c0" if s[0] == "IS 4" else SHAFT)
           for s in shafts]
# Rückfallvariante: WE 1.05 / 1.09 wie AP Index A, je eigener Schacht
knots_r = knots_v + [(bx(5) + 0.27, N0 + 0.22, "#7a7a7a"), (bx(5) + 5.58, S0 - 0.22, "#7a7a7a")]
yb = mini(16, BY + 5, "Bestand (AP Index A): 17 Sanitär-/Lüftungsstandorte + Kernsteiger",
          bestand, [(bestand_kern[0], bestand_kern[1], "#1565c0")])
yv = mini(16, BY + 46, "Vorschlag: 7 Installationsknoten (S · L) + 1 Kernschacht (E · M)", [], knots_v)
yr = mini(16, BY + 87, "Rückfallvariante (WE 1.05/1.09 wie AP): 9 Knoten + 1 Kernschacht", [], knots_r)
for k, (sym, lab) in enumerate((
        (f'<circle cx="18" cy="{{y}}" r="1.05" fill="{SHAFT}"/>', "Einzelstandort (schematisch)"),
        (f'<rect x="16.5" y="{{y0}}" width="3" height="3" fill="{SHAFT}"/>', "Installationsknoten"),
        ('<rect x="16.5" y="{y0}" width="3" height="3" fill="#1565c0"/>', "Kernschacht E · M"),
        ('<rect x="16.5" y="{y0}" width="3" height="3" fill="#7a7a7a"/>', "zusätzlicher Schacht Rückfallvariante"))):
    xo = (k % 2) * 58
    yy = BY + 125 + (k // 2) * 4.6
    add(sym.format(y=yy, y0=yy - 1.5).replace('cx="18"', f'cx="{18 + xo}"').replace('x="16.5"', f'x="{16.5 + xo}"'))
    add(text(21 + xo, yy + 0.8, lab, 1.9, "start"))

# --- Legende
LX = 150
add(text(LX, BY, "Legende", 3.2, "start", "bold"))
leg = [
    ('<rect x="{x}" y="{y}" width="8" height="3.5" fill="url(#hBear)" stroke="#1d1d1d" stroke-width="0.15"/>',
     "Tragende Wand Bestand (WBS 70)"),
    ('<rect x="{x}" y="{y}" width="8" height="3.5" fill="' + WALL + '"/>', "Nichttragende Wand / Trockenbau"),
    ('<rect x="{x}" y="{y}" width="8" height="3.5" fill="url(#hShaft)" stroke="' + SHAFT +
     '" stroke-width="0.3"/>', "Installationsschacht F90, durchgehend KG–DG"),
    ('<rect x="{x}" y="{y}" width="8" height="3.5" fill="' + CHG + '" stroke="#999" stroke-width="0.15"/>',
     "Raum geändert ggü. AP Index A"),
    ('<rect x="{x}" y="{y}" width="8" height="3.5" fill="url(#hKit)" stroke="#555" stroke-width="0.15"/>',
     "Küchenzeile (Lage)"),
    ('<line x1="{x}" y1="{ym}" x2="{x8}" y2="{ym}" stroke="#1565c0" stroke-width="0.4" stroke-dasharray="1.6,0.8"/>',
     "Elektro-/Medientrasse in Flur-Unterdecke"),
    ('<rect x="{x2}" y="{y}" width="4" height="3" fill="#1565c0"/>', "Wohnungsunterverteilung (UV)"),
    ('<rect x="{x}" y="{y}" width="8" height="3.5" fill="none" stroke="#c00000" stroke-width="0.35" '
     'stroke-dasharray="1,0.6"/><circle cx="{xc}" cy="{ym}" r="1.4" fill="#c00000"/>',
     "Neue Türöffnung in tragender Flurwand – Statik prüfen"),
]
for k, (sym, lab) in enumerate(leg):
    y = BY + 4 + k * 5.0
    add(sym.format(x=LX, y=y, ym=y + 1.75, x8=LX + 8, x2=LX + 2, xc=LX + 4))
    add(text(LX + 11, y + 2.8, lab, 2.1, "start"))
add(text(LX, BY + 48, "S = Sanitär (TW/AW)   L = Abluft DIN 18017-3   E = Elektro   M = Medien/TK", 1.9,
         "start", fill="#444"))

# --- Knotentabelle
TX = 150
TY = BY + 54
add(text(TX, TY, "Installationsknoten je Regelgeschoss", 3.2, "start", "bold"))
cols = [0, 15, 28, 92]
hdr = ["Knoten", "Gewerke", "versorgt", "Lage"]
lage = {"IS 1": "Mittelzone, Achse B/3", "IS 2": "Bad 1.04, Achse D/3", "IS 3": "Bad 1.01, Achse D",
        "IS 4": "Aufzug-Vorraum, F/3", "IS 5": "Bad 1.10, Achse F/2", "IS 6": "Bad 1.06, Achse G/3",
        "IS 7": "Bad 1.08, Achse H/2", "IS 8": "Mittelzone, Achse I/3"}
for c, h in zip(cols, hdr):
    add(text(TX + c, TY + 6, h, 2.0, "start", "bold"))
add(line(TX, TY + 7.3, TX + 128, TY + 7.3, w=0.25))
for r, s in enumerate(shafts):
    y = TY + 11.5 + r * 4.5
    add(text(TX + cols[0], y, s[0], 2.0, "start", "bold", SHAFT))
    add(text(TX + cols[1], y, s[5], 2.0, "start"))
    add(text(TX + cols[2], y, s[6], 1.85, "start"))
    add(text(TX + cols[3], y, lage[s[0]], 1.85, "start"))
add(line(TX, TY + 11.5 + 7.6 * 4.5, TX + 128, TY + 11.5 + 7.6 * 4.5, w=0.15))

# --- Erläuterung
EX = 292
add(text(EX, BY, "Erläuterung", 3.2, "start", "bold"))
notes = [
    ("Ziel", "Statt rund 17 einzelner Anschluss- und Steigerstandorte je Geschoss werden Bad, Küche, "
             "WM und Abluft benachbarter Wohnungen an gemeinsamen Schächten zusammengeführt."),
    ("Prinzip", "Nassräume zweier Wohnungen liegen Rücken an Rücken an derselben Querwandachse "
                "und an der Flurwand. Ein Schacht versorgt beide Seiten über Kernbohrungen in der "
                "Querwand. Die Küchenzeile wird an die Bad-Rückwand bzw. Installationswand gelegt."),
    ("Änderungen", "WE 1.05 und 1.09: Bad und Flur im flurseitigen Band getauscht (Typ II gespiegelt "
                   "im Band, Fassadenräume unverändert). WE 1.03: Küchenzeile an Achse D. WE 1.01: "
                   "Küchenzeile an Bad-Installationswand, WM ins Bad, HWR wird Abstellraum. WE 1.02 und "
                   "1.07: Nassräume der Mittelzone auf je einen Knoten gelegt."),
    ("Elektro", "Ein Hauptsteiger im Kern (Aufzug-Vorraum, Lage gem. AP bereits vorgesehen), "
                "horizontale Verteilung in der Flur-Unterdecke zu den Unterverteilungen der WE."),
    ("Flächen", "Wohnungsgrößen bleiben erhalten. In WE 1.05 und 1.09 verschieben sich durch den "
                "Tausch ca. 0,8 m² vom Wohnen/Kochen (≈ 13,90 m²) zum Schlafen (≈ 9,90 m²), "
                "WE gesamt ≈ 31,71 m² statt 31,76 m². Übrige Flächen gem. AP Index A; Bilanzierung "
                "in der Werkplanung."),
    ("Kritisch", "Die Wohnungstüren von WE 1.05 und 1.09 wandern zur anderen Achse. Die Flurwände "
                 "sind tragend (Wandpfeilernachweise); neue Öffnungslage nur mit statischem Nachweis."),
    ("Rückfall", "Lässt die Statik die neuen Türlagen nicht zu, bleiben WE 1.05 und 1.09 wie in der "
                 "AP mit je eigenem Schacht: 9 Knoten + 1 Kernschacht statt rund 17 Standorten. "
                 "Alle anderen Änderungen bleiben gültig."),
    ("Zu prüfen", "Statik (Türöffnungen Flurwand, Wand-/Deckendurchbrüche, Nutzung vorhandener BD), "
                  "Brandschutz (F90-Schächte, Abschottungen), Schallschutz DIN 4109, "
                  "Fortführung in EG, 5. OG und Drempel, Abstimmung TGA-Planung."),
]


def wrap(s, n):
    words, lines_, cur = s.split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) + 1 > n:
            lines_.append(cur)
            cur = w_
        else:
            cur = (cur + " " + w_).strip()
    lines_.append(cur)
    return lines_


y = BY + 6
for head, body in notes:
    add(text(EX, y, head, 2.15, "start", "bold"))
    for ln in wrap(body, 74):
        add(text(EX + 18, y, ln, 2.0, "start"))
        y += 3.15
    y += 1.3

# --- Schriftfeld
SX, SY, SW, SH = 452, BY + 58, 134, 74
add(f'<rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" fill="none" stroke="#1d1d1d" stroke-width="0.4"/>')
rows = [
    ("Bauvorhaben", "Schlegelstraße 3, 07747 Jena – Sanierung Wohngebäude"),
    ("Bauherr", "jenawohnen GmbH, Löbdergraben 19, 07743 Jena"),
    ("Planinhalt", "Grundriss Regelgeschoss 1.–4. OG"),
    ("", "Vorschlag Installationsknoten (Variante)"),
    ("Planstand", "Variantenstudie V2 · 29.10.2026"),
    ("Maßstab", "1:100 (A2) · Maße schematisch, am Bestand prüfen"),
    ("Grundlage", "AP Index A, 301_A_H5_1051 / 1301"),
]
for k, (a, b) in enumerate(rows):
    yy = SY + 6.5 + k * 9.6
    add(text(SX + 3, yy, a, 1.9, "start", fill="#666"))
    add(text(SX + 3, yy + 4.0, b, 2.4 if k != 3 else 2.4, "start", "bold" if k in (2, 3) else "normal"))
    if k not in (2,) and k < len(rows) - 1:
        add(line(SX, yy + 6.0, SX + SW, yy + 6.0, w=0.15))

add("</svg>")

target = Path(__file__).with_name("Vorschlag_Installationsknoten_RG.svg")
target.write_text("\n".join(out), encoding="utf-8")
print(target)
