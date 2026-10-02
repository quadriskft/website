"""Tiszta méretrajzok (a Quadris kérésére, a 223032 / 225455 mintájára): tömör fekete profil, csak a befoglaló
méretek és a falvastagság – a többi méret- és segédvonal nélkül. A profil az alvaz_rajzok.py tisztított,
nagy felbontású forrásából jön (a régi, apró méretfeliratok nélkül). Kimenet: <slug>-meretrajz.webp első képként;
a korábbi rajz (-rajz) és a gyári, sok méretes rajz (-1) a kezi_kepsorrend.json „kizart” listáján.

Használat: python3 scripts/termekadatok/tiszta_rajzok.py   (az alvaz_rajzok.py után, a kep_sorrend.py előtt)
"""

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import alvaz_rajzok as A  # noqa: E402
import constellium as C  # noqa: E402
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
# slug -> (szélesség felirat, magasság felirat, falvastagság felirat,
#          a falméret helye: ("h", y-arány) = vízszintes méret a bal oldali falon át az adott magasságban,
#                             ("v", x-arány) = függőleges méret az alsó falon át az adott vízszintes helyen,
#          törlendő maradványok a profil-maszkon [(x0, y0, x1, y1) arányban],
#          [opcionális: a szélesség mérete csak a felső sávé (a magasság ennyi része) – pl. kinyúló kar nélkül])
ITEMS = {
}


# a gyári lap kis, sraffozott keresztmetszet-vázlatából (data/forras/…): slug -> (vázlat, szélesség, magasság,
# falvastagság, a falméret helye)
SKETCH = {
    "2018290-18-mm-keretprofil-elox": ("data/forras/bodega_50042_vazlat.png", "68", "135,5", "2,4", ("h", 0.55),
                                       [(120, 231, 162, 236), (169, 231, 190, 236), (127, 236, 134, 292), (146, 320, 158, 347)]),
}


# a Constellium Děčín (Aluminium Děčín) gyári profilrajzaiból (constellium.py: a profil körvonala méretek nélkül):
# slug -> (profilszám, üreg-küszöb [px], résáthidalás sugara [px], javítások a körvonalképen
#          [("erase", x0, y0, x1, y1) / ("line", x0, y0, x1, y1)], szélesség, magasság, falvastagság, a falméret helye,
#          [a szélesség csak a felső sávé])
# A kettős vonallal rajzolt falak közti keskeny fehér sávok a profil anyaga, a széles fehér tartományok az üregek.
# A Quadris kérésére vonalas rajz (a gyári laphoz hasonlóan): a kitöltött profil külső és belső körvonala.
# (a 206941, 6612225, 6612226 rajza a Quadris kérésére törölve – új forrást keres)
DECIN = {
    # az alsó, ferde fülecske vékony: kisebb simítás, hogy megmaradjon
    # az alsó, ferde fülecske és a talp letört vége a szkenből nem jön ki tisztán: kézzel pótolva
    "2018652-18-mm-keretprofil-erositett-elox": ("8652", 40, 3, [
        ("fill", [(553.8, 436), (557.5, 436), (558.6, 440.3), (567.6, 457.0), (566.6, 459.3), (564.2, 459.2), (553.8, 440.6)]),
        ("clear", [(597.4, 432.9), (597.4, 430), (607, 430), (607, 436.5), (603.2, 436.5)]),
        ("clear", [(559, 439.7), (594.2, 439.7), (595.6, 441.8), (595.6, 445), (561.8, 445), (559.2, 440.4)]),
        ("clear", [(603.3, 430), (607, 430), (607, 444), (603.3, 444)]),
        ("fill", [(556, 432.9), (597.4, 432.9), (603.2, 436.5), (603.2, 441.8), (595.6, 441.8), (594.2, 439.6), (556, 439.6)]),
    ], "40", "126,5", "3", ("h", 0.72), 0.12, 5),
    "2073902-i-90-csavarozhato-kereszttarto": ("10902", 90, 3, [], "85", "90", "3", ("h", 0.40), None, 5, 6),
}


# a gyári rajz méreteiből (mm) vektorosan felépített profil – ahol a szken segédvonalai a körvonalba olvadnak:
# slug -> (építő függvény neve, szélesség, magasság, falvastagság, a falméret helye)
VECTOR = {
    "206941-cd-100x30-mm-alafutasgatlo-elox-profil": ("profil_6941", "30,3", "100", "1,9", ("h", 0.80)),
    "203101-spanner-profil": ("profil_3101", "35", "70", "5", ("h", 0.3)),
    "388005-ponyvabeakaszto-alu-profil-70-mm-elox": ("profil_8005", "70", "18", "2", ("v", 9 / 70),
                                                     dict(idims=[("h", 0.5, 2 / 70, 16 / 70, "ø14")])),
    "388008-27mm-feszito-cso-alu-profil": ("profil_8008", "26,5", "27", "2", ("h", 0.5),
                                           dict(idims=[("h", 0.3, 10.9 / 26.5, 24.9 / 26.5, "ø14")])),
    "238645-kulso-l-profil-140x80mm-elox": ("profil_8645", "80", "140", "2,5", ("v", 0.6),
                                            dict(walls=[("hx", 0.5, 0.01, "2,5")])),
    "238087-70x110-mm-l-kulso-elox": ("profil_8087", "70", "110", "2", ("h", 0.3)),
    "237905-n-25x35-mm-ives-sarokprofil-r50": ("profil_7905", "102", "92", "2,5", ("h", 0.85),
                                               dict(idims=[("h", 0.72, 2.5 / 102, 28 / 102, "25,5")])),
    "237005-142-mm-i-koptato-profil-elox": ("profil_7005", "142", None, "", None),
    "237461-50x260-mm-l-belso-vedoprofil-elox": ("profil_7461", "260", "50", "2,5", ("v", 0.6), dict(walls=[("hx", 0.62, 0.005, "3")])),
    "237461-n-50x260-mm-l-belso-vedoprofil": ("profil_7461", "260", "50", "2,5", ("v", 0.6), dict(walls=[("hx", 0.62, 0.005, "3")])),
    "237000-25x25-mm-ives-sarokprofil-elox": ("profil_237000", "66,5", "66,5", "3", ("h", 0.8),
                                              dict(idims=[("v", 60 / 66.5, 3.2 / 66.5, 28.3 / 66.5, "25"),
                                                          ("h", 60 / 66.5, 3.2 / 66.5, 28.3 / 66.5, "25")])),
    "231381-25-mm-diszlec-alu-3000-mm": ("profil_231381", "25", "5", "", None),
    "225040-koztes-250-mm-elox-profil": ("profil_225040", "272,2", "25", "1,7", ("v", 0.47),
                                         dict(hdims=[(0, 260.5 / 272.2, "260,5"), (17.3 / 272.2, 267.3 / 272.2, "250")],
                                              walls=[("hx", 0.5, 89.8 / 272.2, "1,8")])),
    "225040-n-koztes-250-mm-profil": ("profil_225040", "272,2", "25", "1,7", ("v", 0.47),
                                      dict(hdims=[(0, 260.5 / 272.2, "260,5"), (17.3 / 272.2, 267.3 / 272.2, "250")],
                                           walls=[("hx", 0.5, 89.8 / 272.2, "1,8")])),
    "226795-400-mm-peremes-gumis-oldalfal-elox": ("profil_36795", "408", "27,5", "1,7", ("v", 0.5),
                                                  [(2.5 / 27.5, 1, "25")]),
    "226671-400-mm-gumis-oldalfal-elox": ("profil_36671", "400", "25", "1,7", ("v", 0.5)),
    "208477-cd2-100x30-mm-alafutasgatlo-elox-profil": ("profil_8477", "30,2", "100", "1,5", ("h", 0.85)),
    "2015290-15-mm-keretprofil-elox": ("profil_50290", "132", "68", "2,4", ("v", 0.45)),
    "6612226-hatso-oszlop-128-35-alu-elox-d": ("profil_12226", "128", "35", "3", ("v", 0.75)),
    "6612225-elso-oszlop-90-70-alu-elox-d": ("profil_12225", "90", "70", "3", ("v", 0.45), [(34.79 / 70, 1, "35")]),  # a lemez felső síkja
}


# katalóguslapon fekete (sötét) kitöltésű profilrajz: slug -> (forráskép, kivágás, elforgatás fokban, szélesség, magasság)
DARK = {"232134-285-mm-i-koptato-profil-elox": ("data/forras/232134_lap.png", (284, 60, 318, 618), 90, "285", None)}


def dark_mask(path, crop, rot=0, scale=8):
    """Katalóguslap fekete profilrajzának maszkja (a kék méretvonal és a felirat nélkül), elforgatva, felnagyítva."""
    a = np.asarray(Image.open(ROOT / path).convert("RGB")).astype(np.float32)[crop[1]:crop[3], crop[0]:crop[2]]
    dark = np.clip((110 - a.max(axis=2)) / 60, 0, 1)
    big = cv2.resize(dark, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), scale * 0.3) > 0.5
    if rot:
        big = np.rot90(big, rot // 90)
    n, lab, st, _ = cv2.connectedComponentsWithStats(big.astype(np.uint8), connectivity=8)
    m = lab == 1 + int(np.argmax(st[1:, 4]))
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def trace_mask(path, crop, erode_mm, height_mm, rot=0, erase=(), scale=6, cav=60):
    """Kettős körvonallal rajzolt gyári főnézet maszkja: a kis feliratok (pl. z / x / y sarokjelek) és a vékony
    méret- és részletkörvonalak kiszűrése, a körvonalak közti falak kitöltése (az üregek, ahová cav px-es kör befér,
    üresek), végül a vonalvastagság felének visszavétele (erode_mm), hogy a falak a névleges vastagságúak legyenek."""
    g = np.asarray(Image.open(ROOT / path).convert("L")).astype(np.float32)
    for ex0, ey0, ex1, ey1 in erase:  # a falhoz érő méretnyilak (a forrás koordinátáiban)
        g[ey0:ey1, ex0:ex1] = 255
    a = g[crop[1]:crop[3], crop[0]:crop[2]].copy()
    n, lab, st, _ = cv2.connectedComponentsWithStats((a < 150).astype(np.uint8), connectivity=4)
    for i in range(1, n):
        if st[i, 4] < 90:
            a[lab == i] = 255
    big = cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    el = lambda d: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    ink = cv2.morphologyEx((big < 140).astype(np.uint8), cv2.MORPH_OPEN, el(10))
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    ink = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 2000]).astype(np.uint8)
    white = 1 - np.pad(ink, 20)
    n, lab, _, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    outside = lab == lab[0, 0]
    hole = cv2.morphologyEx(((white > 0) & ~outside).astype(np.uint8), cv2.MORPH_OPEN, el(cav)) > 0
    solid = cv2.morphologyEx((~outside & ~hole).astype(np.uint8), cv2.MORPH_OPEN, el(19))
    n, lab, st, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
    m = (lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(1 - m, connectivity=4)  # apró zárványok (sarokjelek helye) kitöltve
    for i in range(1, n):
        if st[i, 4] < 3000 and lab[0, 0] != i:
            m[lab == i] = 1
    ys, xs = np.where(m)
    r = round(erode_mm * (ys.max() - ys.min() + 1) / height_mm)
    m = cv2.morphologyEx(cv2.erode(m, el(2 * r + 1)), cv2.MORPH_OPEN, el(13)) > 0
    # a hosszú, egyenes falakra tapadt méretnyíl-maradványok (apró pöttyök) kiszűrése: a végek (a részletek) kivételével
    # csak az marad, amibe a fal mentén vagy arra merőlegesen 2 mm-es szakasz befér
    k = (ys.max() - ys.min() + 1) / height_mm
    L = int(2 * k)
    keep = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((L, 1), np.uint8)) | \
        cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((1, L), np.uint8))
    lo, hi = ys.min() + int(26 * k), ys.max() - int(26 * k)
    m[lo:hi] = keep[lo:hi] > 0
    if rot:
        m = np.rot90(m, rot // 90)
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# gyári főnézetből kirajzolt profil (trace_mask): slug -> (forrás, kivágás, visszavétel [mm], magasság a forráson [mm],
# forgatás, szélesség, magasság, falvastagság, a falméret helye)
TRACE = {"227046-ck10-koztes-200-mm-elox-profil": ("data/forras/227046_ck10_rajz.webp", (246, 50, 351, 868), 0.5, 222.03,
                                                   -90, "222,03", "25", "1,2", ("v", 0.5),
                                                   [(230, 602, 255, 608), (264, 602, 300, 608), (300, 623, 342, 629)])}


# a Quadris által küldött gyári rajz önmagában (csak ez a kép; a fejléc a gyártói számmal kivágva, fekete-fehérre
# tisztítva): slug -> (forráskép, kivágás, adatok)
RAW = {"236825-80x80-mm-l-profil-elox": ("data/forras/236825_rajz.png", (16, 170, 656, 718),
                                          {"Méret": "80 × 80 mm", "Falvastagság": "2,5 mm", "Tömeg": "1,027 kg/fm",
                                           "Anyag": "alumínium AlMgSi0,5 F25, eloxált"}),
       "237461-50x260-mm-l-belso-vedoprofil-elox": ("data/forras/237461_rajz.png", (12, 136, 740, 445),
                                                    {"Méret": "50 × 260 mm", "Falvastagság": "2 mm", "Tömeg": "1,962 kg/fm",
                                                     "Anyag": "alumínium 6060, eloxált"}),
       "227046-ck10-koztes-200-mm-elox-profil": ("data/forras/227046_ck10_rajz.webp", (14, 14, 1462, 938),
                                                  {"Falvastagság": "1,2 mm", "Tömeg": "1,903 kg/fm", "Keresztmetszet": "704 mm²",
                                                   "Anyag": "alumínium 6060, eloxált"},
                                                  # a fejléc (gyártó, profilszám) és az X / Y / Z jelmagyarázat, megjegyzések nélkül
                                                  [(762, 0, 1448, 236), (1100, 768, 1448, 924)]),
       "203101-spanner-profil": ("data/forras/203101_rajz.png", (180, 90, 470, 522),
                                  {"Méret": "35 × 70 mm", "Tömeg": "1,53 kg/fm", "Keresztmetszet": "565 mm²",
                                   "Anyag": "alumínium EN AW-6063 T66"}),
       "238645-kulso-l-profil-140x80mm-elox": ("data/forras/238645_rajz.png", (125, 195, 500, 660),
                                               {"Méret": "140 × 80 mm", "Falvastagság": "2,5 mm", "Tömeg": "1,428 kg/fm",
                                                "Anyag": "alumínium 6060, eloxált"},
                                               [(170, 425, 375, 465)]),  # a „NEKÓT.HRANY R 0,3” felirat nélkül
       "238087-70x110-mm-l-kulso-elox": ("data/forras/238087_rajz.png", (226, 245, 600, 672),
                                         {"Méret": "70 × 110 mm", "Falvastagság": "2 mm", "Tömeg": "1,087 kg/fm",
                                          "Anyag": "alumínium 6060, eloxált"}),
       "237905-n-25x35-mm-ives-sarokprofil-r50": ("data/forras/237905_rajz.webp", (150, 292, 770, 724),
                                                  {"Méret": "102 × 92 mm", "Falvastagság": "2,5 mm", "Tömeg": "2,092 kg/fm",
                                                   "Belső nyílás": "25,5 mm", "Ív": "R50", "Anyag": "alumínium 6060"},
                                                  # az R2, R1,5 felirat, az x / y sarokjelek és a jelmagyarázat nélkül
                                                  [(219, 190, 246, 219), (261, 229, 310, 264), (315, 104, 328, 118),
                                                   (342, 105, 356, 121), (315, 202, 328, 216), (341, 198, 355, 215),
                                                   (158, 235, 171, 248), (231, 235, 244, 248), (156, 259, 169, 274),
                                                   (230, 259, 243, 274), (420, 380, 540, 432)]),
       "237461-n-50x260-mm-l-belso-vedoprofil": ("data/forras/237461_rajz.png", (12, 136, 740, 445),
                                                 {"Méret": "50 × 260 mm", "Falvastagság": "2 mm", "Tömeg": "1,962 kg/fm",
                                                  "Anyag": "alumínium 6060"})}


# a gyári lapon lévő szürke (kitöltött) profilnézet feketére színezve, a lap méreteivel; vonalas + kitöltött:
# slug -> (forráskép, kivágás, szélesség, magasság, falvastagság, a falméret helye, render_mask további beállításai)
GRAYVIEW = {"234235-35x35-mm-ives-sarokprofil-elox-d": (
    "data/forras/234235_rajz_forgatott.png", (640, 160, 865, 360), None, "86", "1,5", ("v", 0.75),
    dict(vdims=[(0, 69.7 / 86, "69,7"), (0, 38.9 / 86, "38,9")],
         idims=[("h", 0.66, 0.5736, 0.9553, "34,5")]))}  # a belső nyílás


# kész képek a Quadris kérésére, ebben a sorrendben (a többi kép kikerül): slug -> [(forráskép, utótag)]
IMAGESET = {"237310-20-dupla-alu-zsaner": [("data/forras/alu_zsaner_ab.png", "1"),  # a megszűnt 5000 mm-es változat képe
                                           ("data/forras/alu_zsaner_tiszta.png", "meretrajz")],  # idegen cikkszámok nélkül
            # az eloxált változathoz is csak a natúr (237767/n) méretrajza kell, a korábbi képek és 3D nélkül
            "237767-60x60-l-profil-elox": [("public/termekkepek/237767-n-60x60-l-profil-1.webp", "rajz")],
            # a Quadris által küldött lap rajza változtatás nélkül (csak a gyári kód és a szöveg kivágva)
            "380033-ponyvabeakaszto-alu-profil-60-mm-elox": [("data/forras/380033_rajz.png", "rajz")],
            # a küldött lap mindkét képe változtatás nélkül (a gyári kód és a szöveg kivágva), a rajz elöl
            "380045-34mm-feszito-cso-alu-profil": [("data/forras/380045_rajz.png", "rajz"), ("data/forras/380045_3d.png", "3d-lap")]}


# a rajz mellé a küldött adatlap termékfotója (kivágva, a háttér fehérre): slug -> (forráskép, kivágás)
PHOTOS = {"231381-25-mm-diszlec-alu-3000-mm": ("data/forras/231381_lap.png", (370, 110, 575, 240)),
          "232134-285-mm-i-koptato-profil-elox": ("data/forras/232134_lap.png", (95, 95, 250, 580)),
          "237000-25x25-mm-ives-sarokprofil-elox": ("data/forras/237000_lap.png", (390, 20, 535, 170)),
          "237005-142-mm-i-koptato-profil-elox": ("data/forras/237005_lap.png", (430, 80, 585, 385))}
# a vektoros profilból készült saját 3D render (scripts/profil3d, contours) a rajzok után: slug -> nézetek
RENDER3D = {"388008-27mm-feszito-cso-alu-profil": [2], "388005-ponyvabeakaszto-alu-profil-70-mm-elox": [2]}  # a katalóguslap fotója túl kicsi és elmosódott
# élesítendő termékképek (PHOTOS)
# (slug -> a kivágásban kifehérítendő téglalapok, pl. a ráérő méretfelirat)
SHARPEN = {}
# adatok a küldött adatlapról
SPEC_FIX = {"231381-25-mm-diszlec-alu-3000-mm": {"Tömeg": "0,211 kg/fm", "Anyag": "alumínium EN AW-6060", "Méret": "25 × 5 mm"},
            "232134-285-mm-i-koptato-profil-elox": {"Tömeg": "2,073 kg/fm", "Magasság": "285 mm", "Szálhossz": "6,7 / 7,5 m"},
            "388005-ponyvabeakaszto-alu-profil-70-mm-elox": {"Tömeg": "0,853 kg/fm", "Méret": "70 × 18 mm", "Furat": "Ø14 mm",
                                                             "Anyag": "alumínium EN AW-6060", "Kivitel": "ponyvabeakasztó profil"},
            "388008-27mm-feszito-cso-alu-profil": {"Tömeg": "0,608 kg/fm", "Méret": "26,5 × 27 mm", "Belső furat": "Ø14 mm",
                                                   "Anyag": "alumínium EN AW-6060", "Kivitel": "ponyvafeszítő cső"},
            "237005-142-mm-i-koptato-profil-elox": {"Tömeg": "1,153 kg/fm", "Magasság": "142 mm", "Anyag": "alumínium EN AW-6060, eloxált",
                                                    "Kivitel": "bordázott lapos profil"},
            "234235-35x35-mm-ives-sarokprofil-elox-d": {"Tömeg": "1,412 kg/fm", "Anyag": "alumínium 6060 T6, eloxált", "Belső nyílás": "34,5 mm",
                                                        "Magasság": "86 mm", "Keresztmetszet": "523 mm²"},
            "237000-25x25-mm-ives-sarokprofil-elox": {"Tömeg": "1,99 kg/fm", "Anyag": "alumínium EN AW-6060, eloxált",
                                                      "Méret": "66,5 × 66,5 mm", "Belső méret": "25 mm (mindkét szár)"}}


# új adatlap (eddig nem volt képe): slug -> (forrás, URL, forrás címe)
NEW = {"225040-koztes-250-mm-elox-profil": ("Quadris gyári rajz", "", "Gyári profilrajz (225040)", {"Felület": "eloxált"}),
       "225040-n-koztes-250-mm-profil": ("Quadris gyári rajz", "", "Gyári profilrajz (225040)", {"Felület": "natúr"}),
       "226795-400-mm-peremes-gumis-oldalfal-elox": ("BODEGA", "https://www.bodega.it", "Bodega TB36795 gyári rajz",
                                                     {"Tömeg": "3,956 kg/fm", "Ötvözet": "EN AW-6060 T66", "Felület": "eloxált"}),
       "226671-400-mm-gumis-oldalfal-elox": ("BODEGA", "https://www.bodega.it", "Bodega TB36671 gyári rajz",
                                             {"Tömeg": "3,853 kg/fm", "Ötvözet": "EN AW-6063 T66", "Felület": "eloxált"}),
       "2015290-15-mm-keretprofil-elox": ("BODEGA", "https://www.bodega.it", "Bodega 50290 gyári rajz",
                                          {"Tömeg": "1,763 kg/fm", "Ötvözet": "EN AW-6060 T6", "Felület": "eloxált"}),
       "237005-142-mm-i-koptato-profil-elox": ("Quadris katalóguslap", "", "", {"Felület": "eloxált"}),
       "388008-27mm-feszito-cso-alu-profil": ("Quadris katalóguslap", "", "", {"Felület": "natúr"}),
       "388005-ponyvabeakaszto-alu-profil-70-mm-elox": ("Quadris katalóguslap", "", "", {"Felület": "eloxált"}),
       "203101-spanner-profil": ("Quadris gyári rajz", "", "", {"Felület": "natúr"})}


def profil_6941():
    """Constellium Děčín 6941 (CD 100×30 aláfutásgátló): 30,3 × 100, fal 1,9, felül 3,3 mm-es bordázott fal öt
    horonnyal, jobb oldalt 1 mm-es mélyítés (15°-os átmenetekkel), bal oldalt 8,5 mm-es horony 19 mm magas belső
    zsebbel. Külső sarkok R3, az üreg sarkai R2, a horony sarkai R1 (a rajz z / y / x jelölései szerint)."""
    from shapely.geometry import Polygon, box
    outer = Polygon([(0, 0), (30.3, 0), (30.3, 16.0), (29.22, 18.6), (29.22, 83.6), (30.3, 86.2), (30.3, 100), (0, 100)])
    outer = outer.buffer(-3, join_style=1).buffer(3, join_style=1)
    cav = Polygon([(1.92, 3.32), (28.38, 3.32), (28.38, 15.9), (27.36, 18.5), (27.36, 83.7), (28.38, 86.3), (28.38, 98.13),
                   (1.92, 98.13), (1.92, 61.4), (12.33, 61.4), (12.33, 38.6), (1.92, 38.6)])
    cav = cav.buffer(-2, join_style=1).buffer(2, join_style=1).buffer(1, join_style=1).buffer(-1, join_style=1)
    pocket = box(1.92, 40.4, 10.44, 59.5).buffer(-1, join_style=1).buffer(1, join_style=1)
    mouth = box(-1, 45.8, 3, 54.3)
    slot = pocket.union(mouth).buffer(0.4, join_style=1).buffer(-0.4, join_style=1)
    grooves = [Polygon([(c - 1.05, -1), (c + 1.05, -1), (c + 1.05, 0), (c + 0.75, 1.4), (c - 0.75, 1.4), (c - 1.05, 0)])
               for c in (7.0, 11.15, 15.3, 19.47, 23.63)]
    prof = outer.difference(cav).difference(slot)
    for g in grooves:
        prof = prof.difference(g)
    return prof


def fillet(pts, radii, n=12):
    """Sokszög lekerekítése: minden csúcs a megadott sugarú, mindkét élhez érintő ívvel (domború és homorú is)."""
    out = []
    P = [np.array(p, float) for p in pts]
    for i, (p, r) in enumerate(zip(P, radii)):
        if not r:
            out.append(tuple(p))
            continue
        a, b = P[i - 1], P[(i + 1) % len(P)]
        u, v = (a - p) / np.linalg.norm(a - p), (b - p) / np.linalg.norm(b - p)
        th = math.acos(max(-1.0, min(1.0, float(u @ v))))
        d = r / math.tan(th / 2)
        bis = (u + v) / np.linalg.norm(u + v)
        c = p + bis * (r / math.sin(th / 2))
        t1, t2 = p + u * d, p + v * d
        a1, a2 = math.atan2(*(t1 - c)[::-1]), math.atan2(*(t2 - c)[::-1])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out += [tuple(c + r * np.array([math.cos(a1 + da * k / n), math.sin(a1 + da * k / n)])) for k in range(n + 1)]
    return out


def profil_12225():
    """Constellium Děčín 12225 (első oszlop 90/70): a gyári rajz körvonalának pontjai [pt] mm-re átszámítva
    (a szken vízszintes és függőleges léptéke eltér: 90 mm = 469,3 pt, 70 mm = 330,6 pt). Sarkok a rajz jelölései
    szerint: z = R3, y = R2, x = R1, a többi él R0,5; a 2 mm-es lemez vége lekerekített."""
    from shapely.geometry import Polygon

    def mm(pts):
        return [((x - 104.4) / 5.2144, (y - 105.0) / 4.7229, r) for x, y, r in pts]

    outer = mm([(104.4, 105, 0.5), (127.3, 105, 0.5), (127.3, 155, 0), (125.4, 155, 0), (125.4, 203, 0), (128, 203, 0),
                (128, 269.3, 2), (573.7, 269.3, 0.9), (573.7, 278.5, 0.9), (469.4, 278.5, 1), (469.4, 332.2, 0.5),
                (453.6, 332.2, 0.5), (453.6, 307.8, 0.3), (438, 307.8, 0.5), (438, 301.5, 0.5), (453.6, 301.5, 0.3),
                (453.6, 283.4, 2), (409.7, 283.4, 2), (409.7, 419.6, 2), (453.6, 419.6, 2), (453.6, 401.4, 0.3),
                (438, 401.4, 0.5), (438, 395, 0.5), (453.6, 395, 0.3), (453.6, 370.9, 0.5), (469.4, 370.9, 0.5),
                (469.4, 435.2, 3), (136.5, 435.2, 1.5), (146.0, 388.5, 0.5), (161.5, 388.5, 0.5), (155.2, 421, 1),
                (191.1, 421, 1), (191.1, 350.3, 1), (104.4, 350.3, 3)])
    cav = mm([(120.8, 289, 2), (393.8, 289, 2), (393.8, 420, 2), (206.8, 420, 2), (206.8, 336.1, 1), (120.8, 336.1, 2)])
    shape = Polygon(fillet([(x, y) for x, y, _ in outer], [r for *_, r in outer]))
    return shape.difference(Polygon(fillet([(x, y) for x, y, _ in cav], [r for *_, r in cav])))


def profil_12226():
    """Constellium Děčín 12226 (hátsó oszlop 128/35): a gyári rajz körvonalpontjai [pt] mm-re átszámítva
    (128 mm = 448,2 pt, 35 mm = 110,8 pt). A bal oldali doboz felső fülecskéje a szkenen hiányzik – a méretezetlen
    nézet és a jobb oldali, tükrös doboz szerint pótolva. Sarkok: z = R3, y = R2, x = R1, a többi él R0,5."""
    from shapely.geometry import Polygon

    def mm(pts):
        return [((x - 64.0) / 3.5016, (y - 758.7) / 3.1657, r) for x, y, r in pts]

    outer = mm([(64.0, 758.7, 0.9), (512.2, 758.7, 2),
                (512.2, 800.3, 0.5), (501.7, 800.3, 0.5), (501.7, 784.5, 0.3), (491.2, 784.5, 0.5), (491.2, 779.5, 0.5),
                (501.7, 779.5, 0.3), (501.7, 767.6, 1), (472.0, 767.6, 1), (472.0, 859.1, 1), (501.7, 859.1, 1),
                (501.7, 847.1, 0.3), (491.2, 847.1, 0.5), (491.2, 842.5, 0.5), (501.7, 842.5, 0.3), (501.7, 826.4, 0.5),
                (512.2, 826.4, 0.5), (512.2, 868.6, 3), (325.6, 868.6, 3), (325.6, 774.7, 2), (189.8, 774.7, 2),
                (189.8, 840.0, 1), (216.0, 866.5, 1.2), (207.2, 869.6, 1.2), (192.5, 857.4, 0.5), (179.1, 869.5, 1),
                (135.9, 869.5, 2), (135.9, 827.2, 0.5), (146.4, 827.2, 0.5), (146.4, 843.4, 0.3), (156.7, 843.4, 0.5),
                (156.7, 848.1, 0.5), (146.4, 848.1, 0.3), (146.4, 860.0, 1), (175.8, 860.0, 1), (175.8, 768.6, 1),
                (146.4, 768.6, 1), (146.4, 779.5, 0.3), (156.7, 779.5, 0.5), (156.7, 784.5, 0.5), (146.4, 784.5, 0.3),
                (146.4, 801.5, 0.5), (135.9, 801.5, 0.5), (135.9, 765.6, 0.5), (64.0, 765.6, 0.9)])
    cav = mm([(336.1, 774.0, 2), (461.4, 774.0, 2), (461.4, 859.0, 1), (336.1, 859.0, 1)])
    shape = Polygon(fillet([(x, y) for x, y, _ in outer], [r for *_, r in outer]))
    return shape.difference(Polygon(fillet([(x, y) for x, y, _ in cav], [r for *_, r in cav])))


def profil_50290():
    """Bodega 50290 (15 mm keretprofil): a gyári rajz (data/forras/bodega_50290.png, 7,098 px/mm) körvonalpontjaiból.
    A bal oldali ív R25 (falvastagság 2,4, a vége R1,2), a függőleges fül alján Ø4 gömbölyítés, a jobb oldali horog
    a rajz sugaraival (R5 / R4,5 / R2 / R1 / R0,5), a 30°-os fog és az alsó, keskenyedő láb (alul R0,9)."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union

    pts = [(392, 134.5, 0), (1184, 134.5, 2), (1184, 232.8, 2), (1088.3, 232.8, 4.5), (1088.3, 331.2, 4.5),
           (1183.5, 363.9, 2), (1183.5, 404, 0.5), (1166.5, 418, 0.5), (1155, 378, 0.7), (1145, 378, 0.7),
           (1135, 416.5, 0.5), (1079, 412.5, 0), (1079, 425.5, 0), (1065.5, 616.7, 0.9), (1052, 616.7, 0.9),
           (1052, 394.4, 2), (1118, 397.5, 1), (1129.5, 362.5, 1), (1071.7, 341.9, 5), (1071.7, 215.4, 5),
           (1166.7, 215.4, 1), (1166.7, 151.5, 1), (410.7, 151.5, 1.5), (410.7, 318, 0), (393.3, 318, 0), (393.3, 151.5, 0)]
    K = 7.098
    main = Polygon(fillet([(x, y) for x, y, _ in pts], [r * K for *_, r in pts]))
    c, ro, ri = np.array([392, 134.5 + 25 * K]), 25 * K, 22.6 * K
    a0, a1 = math.atan2(213.3 - c[1], 255.2 - c[0]), -math.pi / 2
    if a0 > 0:
        a0 -= 2 * math.pi
    ang = np.linspace(a0, a1, 80)
    lip = Polygon([tuple(c + ro * np.array([math.cos(a), math.sin(a)])) for a in ang] +
                  [tuple(c + ri * np.array([math.cos(a), math.sin(a)])) for a in ang[::-1]])
    cap = Point(255.2, 213.3).buffer(1.2 * K, 32)
    bulb = Point(396.7, 318.3).buffer(2 * K, 48)
    shape = unary_union([main, lip, cap, bulb]).difference(Point(1078.5, 419).buffer(6.5, 32))
    shape = shape.buffer(0.4 * K).buffer(-0.4 * K)  # a csatlakozások kis lekerekítése
    from shapely import affinity
    return affinity.affine_transform(shape, [1 / K, 0, 0, 1 / K, -247.5 / K, -134.5 / K])


def profil_8477():
    """Constellium (Alusuisse) Děčín 8477 (CD2 100×30 aláfutásgátló): a gyári rajz körvonalpontjaiból [pt]
    (30,2 mm = 97,3 pt, 100 mm = 292 pt). Falvastagság 1,5 (a rajz szerint), külső sarkok R4 / belső R2,5,
    felül két 45°-os horony, jobb oldalt 1,4 mm-es, 20°-os átmenetű mélyítés 15 mm-re a végektől,
    bal oldalt 10,5 mm-es horony 19,8 mm-es belső zsebbel (a zseb falain egy-egy kis félkör bemetszéssel)."""
    from shapely.geometry import Point, Polygon

    def mm(x, y):
        return ((x - 392.0) / 3.222, (y - 517.0) / 2.92)

    pts = [(392, 517, 4), (409.5, 517, 0.5), (413.5, 522, 0.3), (421, 522, 0.3), (425, 517, 0.5), (455, 517, 0.5),
           (458.5, 522.2, 0.3), (466.5, 522.2, 0.3), (470.5, 517, 0.5), (489.3, 517, 4), (489.3, 560.8, 1),
           (484.7, 572, 1), (484.7, 754, 1), (489.3, 765.2, 1), (489.3, 809, 4), (392, 809, 4),
           (392, 678.2, 0.3), (397.6, 678.2, 0.3), (397.6, 691.2, 0.5), (427.1, 691.2, 0.5), (427.1, 633.7, 0.5),
           (397.6, 633.7, 0.5), (397.6, 647.7, 0.3), (392, 647.7, 0.3)]
    outer = Polygon(fillet([mm(x, y) for x, y, _ in pts], [r for *_, r in pts]))
    cav = outer.buffer(-1.5, join_style=1)
    notches = [Point(*mm(410, 633.7)).buffer(0.5, 24), Point(*mm(410, 691.2)).buffer(0.5, 24)]
    prof = outer.difference(cav)
    for n in notches:
        prof = prof.difference(n)
    return prof


def profil_36671():
    """Bodega TB36671 (400 mm-es gumis oldalfal): 400 × 25, falvastagság 1,7. Bal oldalt 18,5 mm-es csatlakozó fej
    (felül lekerekített végű, alul T-horony, belül üreg) és 2,5 mm-es fal, utána a 119,4 mm-es zárt rész, 70°-os
    ferde fallal (kívül R6,7, belül R5) le a középső, egyrétegű 1,7 mm-es lemezre, majd tükrösen a 130,4 mm-es zárt
    rész a jobb véggel (a szaggatott vonal – a gumi – nincs a profil része)."""
    from shapely.geometry import Point, Polygon, box
    t = math.tan(math.radians(70))

    def P(pts):
        return Polygon(fillet([(x, y) for x, y, _ in pts], [r for *_, r in pts]))

    outer = P([(0, 0, 0.5), (119.4, 0, 6.7), (119.4 + 23.3 / t, 23.3, 1), (269.6 - 23.3 / t, 23.3, 1), (269.6, 0, 6.7),
               (400, 0, 1), (400, 25, 1), (0, 25, 0.5)])
    o = 1.7 / math.sin(math.radians(70))
    left = P([(21, 1.7, 1), (119.4 - o + 1.7 / t, 1.7, 5), (119.4 - o + 23.3 / t, 23.3, 1), (21, 23.3, 1)])
    right = P([(269.6 + o - 1.7 / t, 1.7, 5), (398.3, 1.7, 1), (398.3, 23.3, 1), (269.6 + o - 23.3 / t, 23.3, 1)])
    # a fej (a Quadris által küldött nagyított részlet szerint): balra nyitott C – felső kar lefelé nyíló, felül
    # lekerekített (R2) horonnyal, belül üreg, alsó kar balra nyíló T-horonnyal
    head = P([(10.1, 1.8, 1), (18.5, 1.8, 1), (18.5, 23.2, 1), (10.1, 23.2, 1)])
    mouth = box(-1, 8.2, 12, 16.9)  # a fej üregébe nyílik
    slot_top = box(2.85, 4.9, 7.05, 8.6).union(Point(4.95, 4.9).buffer(2.1, 32))
    slot_bot = P([(-1, 19.1, 0), (5.3, 19.1, 0.3), (5.3, 18.6, 0.3), (6.4, 18.6, 0.5), (6.4, 22.3, 0.5), (3.6, 22.3, 0.3),
                  (3.6, 22.7, 0.3), (2.5, 22.7, 0.5), (2.5, 26, 0), (-1, 26, 0)])
    prof = outer.difference(left).difference(right).difference(head.union(mouth)).difference(slot_top).difference(slot_bot)
    return prof.buffer(0.25, join_style=1).buffer(-0.25, join_style=1)


def profil_36795():
    """Bodega TB36795 (400 mm-es peremes gumis oldalfal): 408 (a 8 mm-es peremmel) × 25 (+2,5 mm perem felül),
    falvastagság 1,7. Balra a perem (10,5 × 2,5, vége R1,25) és a fej (a Quadris által küldött
    nagyított részlet szerint): balra nyitott, 3 mm-es ajkakkal, 10 mm-es üreggel és 2 mm-es belső fallal; mellette a
    felső lemez megvastagított részén felfelé szélesedő horony (5,5 → 2, mélység 4) 28 mm-re a perem végétől; két zárt rész alul (128,9 – 142,2 – 128,9), 78°-os ferde falakkal, középen csak a felső lemez."""
    from shapely.geometry import Polygon
    t = math.tan(math.radians(78))
    o = 1.7 / math.sin(math.radians(78))

    def P(pts):
        return Polygon(fillet([(x, y) for x, y, _ in pts], [r for *_, r in pts]))

    xl, xr = 8 + 128.9, 408 - 128.9  # a zárt részek alsó belső sarka
    outer = P([(0, -2.5, 1.2), (10.5, -2.5, 0.5), (10.5, 0, 0.5), (408, 0, 2.5), (408, 25, 2.5), (xr, 25, 3),
               (xr - 23.3 / t, 1.7, 2.5), (xl + 23.3 / t, 1.7, 2.5), (xl, 25, 3), (8, 25, 1), (8, 17.3, 0.5),
               (10.5, 17.3, 0.5), (10.5, 21.3, 1), (21.4, 21.3, 1), (21.4, 2.4, 2.5), (10.5, 2.4, 1), (10.5, 7.2, 0.5),
               (8, 7.2, 0.5), (8, 0, 0.5), (0, 0, 0.5)])
    left = P([(23.9, 5.9, 1), (35, 5.9, 0.5), (38.5, 1.7, 1), (xl + 23.3 / t - o, 1.7, 2.5), (xl + 1.7 / t - o, 23.3, 1.3),
              (23.9, 23.3, 1)])
    right = P([(xr - 23.3 / t + o, 1.7, 2.5), (406.3, 1.7, 1.5), (406.3, 23.3, 1.5), (xr - 1.7 / t + o, 23.3, 1.3)])
    groove = P([(25.8, -0.5, 0), (30.4, -0.5, 0), (30.4, 0.9, 0.3), (32.2, 1.4, 0.4), (32.2, 3.3, 0.5),
                (24, 3.3, 0.5), (24, 1.4, 0.4), (25.8, 0.9, 0.3)])  # fecskefarok: fent szűkebb
    return outer.difference(left).difference(right).difference(groove)


def profil_225040():
    """225040 / 225040/n (köztes 250 mm-es profil) a gyári rajz méreteiből: 25 mm vastag (két 1,7 mm-es fal), a
    hosszirányú méretek 272,2 / 260,5 / 250,2 / 250, a három üreg 65 / 75,5 / 65 mm, a bordák 1,8 mm-esek. Felül
    a bal falon L alakú kar (a hosszabb fal tetején kis fog), alul a jobb fal végén kampó, a bal fal alján
    kissé kiugró talp és egy kis fog. A rajzon függőleges; itt vízszintesen (a rajz teteje balra)."""
    from shapely import affinity
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    def rbox(x0, y0, x1, y1, r=0):
        b = box(x0, y0, x1, y1)
        return b.buffer(-r, join_style=1).buffer(r, join_style=1) if r else b

    parts = [
        rbox(0, 17.3, 1.7, 267.3, 0.8), rbox(1.3, 265.5, 3.3, 272.2, 0.8),  # bal fal és a talp
        Polygon([(1.7, 254.5), (4.0, 257), (1.7, 257.4)]),  # kis fog a bal fal belső oldalán
        box(23.3, 0, 25, 250.2), Polygon([(23.3, 0.3), (21.7, 0.9), (23.3, 4.6)]),  # jobb fal, felül kis fog
        box(1.7, 22.4, 23.3, 24.2), box(1.7, 88.9, 23.3, 90.7), box(1.7, 166.4, 23.3, 168.2), box(1.7, 232.9, 23.3, 234.7),
        rbox(7, 3.3, 9, 23, 0.4), rbox(2, 3.3, 9, 5, 0.8),  # L alakú kar felül
        rbox(18.7, 248.5, 25, 250.2, 0.3), rbox(18.7, 248.5, 20.4, 260.5, 0.8),  # kampó alul
    ]
    g = unary_union(parts).buffer(0.4, join_style=1).buffer(-0.4, join_style=1)
    return affinity.affine_transform(g, [0, 1, 1, 0, 0, 0])  # (x, y) -> (y, x): a hossz vízszintesen


def profil_231381():
    """231381 (25 mm díszléc / ponyvafeszítő rúd profil) a küldött adatlap rajza szerint: 25 × 5, tömör, felül
    lapos ív, alul enyhén homorú, a két vége lekerekített (a végeken kb. 2,2 mm vastag)."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    xs = np.linspace(1.1, 23.9, 60)
    top = [(x, 2.2 + 2.8 * (1 - abs((x - 12.5) / 11.4) ** 2.6)) for x in xs]  # középen laposabb ív
    bot = [(x, 0.45 * (1 - ((x - 12.5) / 11.4) ** 2)) for x in xs[::-1]]
    body = Polygon(top + bot)
    g = unary_union([body, Point(1.1, 1.1).buffer(1.1, 32), Point(23.9, 1.1).buffer(1.1, 32)])
    from shapely import affinity
    return affinity.affine_transform(g, [1, 0, 0, -1, 0, 5])  # y lefelé


def profil_237000():
    """237000 (25×25 mm-es íves sarokprofil): 66,5 × 66,5, két, a végein nyitott U-csatorna 25 mm belső
    szélességgel (a fal kb. 3,2 mm), a belső falak a sarokban keresztezik egymást (zárt négyzetes üreg), a külső
    sarok R15-tel ívelt, a falvégek ferdén letörtek (az Exlabesa / ESAL rajz szerint)."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    t, L, W = 3.2, 66.5, 31.5

    def wall(x0, y0, x1, y1, tip):  # fal ferde véggel (tip: "x" = a jobb vége, "y" = az alsó vége letörve)
        if tip == "x":
            return Polygon([(x0, y0), (x1, y0), (x1 - 1.2, y1), (x0, y1)])
        return Polygon([(x0, y0), (x1, y0), (x1, y1 - 1.2), (x0, y1)])

    parts = [wall(0, 0, L, t, "x"), wall(0, W - t, L, W, "x"), wall(0, 0, t, L, "y"), wall(W - t, 0, W, L, "y")]
    g = unary_union(parts)
    from shapely.geometry import Point
    q = box(0, 0, 15, 15)
    arc = q.intersection(Point(15, 15).buffer(15, 96)).difference(Point(15, 15).buffer(15 - t, 96))
    g = g.difference(q).union(arc)  # a külső sarok R15-tel ívelt, a fal végig egyforma vastag
    return g.buffer(0.3, join_style=1).buffer(-0.3, join_style=1)


def profil_7005():
    """237005 (142 mm-es I koptató profil, bordázott lapos profil, T1 7005): a kiosztás a küldött katalóguslap
    rajzáról (szimmetrikus: két szélén és középen kívül két-két kiemelt sáv, a hátoldalon négy horony, a végek
    elöl ferdén élezve); a katalógusrajz vastagságban nem méretarányos, ezért a vastagság az 1,153 kg/fm tömegből
    (kb. 427 mm²): kiemelt sáv 4, mélyebb rész 2,2 mm."""
    from shapely.geometry import Polygon, box
    hi, lo, e, nw, nd = 4.0, 2.25, 1.0, 2.5, 1.0
    d = hi - lo
    pts = [(0, hi - e), (7.5, 0), (15.5, 0), (15.5 + d, d), (29.8, d), (29.8 + d, 0), (53.8, 0), (53.8 + d, d),
           (88.2 - d, d), (88.2, 0), (112.2 - d, 0), (112.2, d), (126.5 - d, d), (126.5, 0), (134.5, 0), (142, hi - e),
           (142, hi), (0, hi)]
    g = Polygon(pts)
    for c in (10.8, 43.4, 98.6, 131.2):  # hornyok a hátoldalon
        g = g.difference(box(c - nw / 2, hi - nd, c + nw / 2, hi + 1))
    return g.buffer(0.15, join_style=1).buffer(-0.3, join_style=1).buffer(0.15, join_style=1)


def profil_7905():
    """237905 (25×35 mm-es íves sarokprofil R50, Alcan Děčín 7905): 102 × 92, falvastagság 2,5; kívül R50-es ív a bal
    falból a felső perembe, zárt kamra (jobb oldali fal x = 51,5–54, alatta a 38–40,5 magasságú borda 77-ig, a belső
    fal x = 28–30,5 y = 70-ig, a bal alsó borda y = 47,5–50); a 25,5 mm-es nyílás a bal fal és a belső fal között."""
    from shapely.geometry import Point, box
    disk = lambda r: Point(50, 50).buffer(r, 256)
    outer = disk(50).intersection(box(0, 0, 54, 40.5).union(box(0, 0, 30.5, 50))).union(box(50, 0, 54, 40.5))
    hole = disk(47.5).intersection(box(0, 0, 51.5, 38).union(box(0, 0, 28, 47.5))).union(box(50, 2.5, 51.5, 38))
    g = outer.difference(hole).union(box(54, 0, 102, 2.5)).union(box(54, 38, 77, 40.5))
    g = g.union(box(28, 50, 30.5, 70)).union(box(0, 50, 2.5, 92))
    return g.buffer(1.2, join_style=1).buffer(-1.7, join_style=1).buffer(0.5, join_style=1)


def profil_8087():
    """238087 (70×110 mm-es külső L profil, Alcan Děčín 8087): a fal 2 vastag; a sarokban kívül 13,5 mm-en 2,5
    vastag (45°-os átmenettel), a külső sarok R5; a vízszintes szár végén 5 mm hosszú, 4 mm vastag perem 50°-os
    alsó lejtővel; a függőleges száron két borda (a belső oldal 2 mm-rel kifelé, a külső 1,5 mm-rel befelé tolva,
    ott 2,5 vastag, a külső oldalon 90°-os, 0,3 mm-es V-horonnyal): alul a láb 4 mm vastag, 20 mm magas (alsó
    élén letörés és R1), fent 47,5–62,5 mm-nél; a keresztmetszet így 406 mm² (a rajzon 401 mm²)."""
    from shapely.geometry import Polygon
    r50 = 2 / math.tan(math.radians(50))
    y = lambda b: 110 - b  # a rajz alulról mért méreteiből
    P = [(0, 0, 5), (13.5, 0, 0), (14, 0.5, 0), (70, 0.5, 0.3), (70, 4.5, 0.3), (65, 4.5, 0), (65 - r50, 2.5, 0),
         (2.5, 2.5, 0.5), (2.5, y(64.5), 0), (4.5, y(62.5), 0), (4.5, y(47.5), 0), (2.5, y(45.5), 0),
         (2.5, y(22), 0), (4.5, y(20), 0), (4.5, 110, 1), (3.5, 110, 0), (0.5, y(1.8), 0)]
    for lo, hi in ((5, 20), (47.5, 62.5)):  # a külső oldal behúzásai, alulról felfelé
        mid = (lo + 1.5 + hi - 1.5) / 2
        P += [(0.5, y(lo), 0), (2, y(lo + 1.5), 0), (2, y(mid - 0.3), 0), (2.3, y(mid), 0), (2, y(mid + 0.3), 0),
              (2, y(hi - 1.5), 0), (0.5, y(hi), 0)]
    P += [(0.5, 14, 0), (0, 13.5, 0)]
    return Polygon(fillet([(x, yy) for x, yy, _ in P], [r for *_, r in P]))


def profil_8645():
    """238645 (140×80 mm-es külső L profil, Constellium Děčín 8645): mindkét szár 2,5 vastag, a sarok kívül R7,5,
    belül R5 (a rajz szerint; így a keresztmetszet 526 mm², a rajzon 527 mm²); a szárak vége 30°-os élre futó
    letöréssel, a csúcs a belső oldalon (a 80 és a 140 a csúcsig értendő)."""
    from shapely.geometry import Polygon
    c = 2.5 / math.tan(math.radians(30))
    P = [(0, 0, 7.5), (80 - c, 0, 0), (80, 2.5, 0), (2.5, 2.5, 5), (2.5, 140, 0), (0, 140 - c, 0)]
    return Polygon(fillet([(x, y) for x, y, _ in P], [r for *_, r in P]))


def profil_8008():
    """388008 (27 mm-es feszítő cső, T1 8008): Ø27-es kör, a nyitott oldalon 26,5-re levágva; benne a Ø14-es furat
    (4,4 mm-rel a nyílás felé tolva) 7,5 mm-es réssel kifelé, mögötte félhold alakú üreg lekerekített végekkel; a
    falak 2 mm-esek – a keresztmetszet így 224 mm², a lap 0,608 kg/fm tömegéből 225 mm²."""
    from shapely.geometry import Point, box
    O, B, w = (13.5, 13.5), (17.9, 13.5), 2.0
    g = Point(O).buffer(13.5, 256).intersection(box(0, 0, 26.5, 27))
    cres = Point(O).buffer(13.5 - w, 256).difference(Point(B).buffer(7 + w, 256)).buffer(-1.1).buffer(1.1)
    g = g.difference(cres).difference(Point(B).buffer(7, 256)).difference(box(B[0], 13.5 - 3.75, 30, 13.5 + 3.75))
    return g.buffer(0.4, join_style=1).buffer(-0.4, join_style=1)


def profil_8005():
    """388005 (70 mm-es ponyvabeakasztó, T1 8005): 70 × 18; balra a Ø14-es furatú, 2 mm falú, felfelé nyitott C
    (lekerekített véggel), mellette a vele szemben nyitott ív (R9 / R6,2), ebből indul a 2,8 vastag felső lap 70-ig és
    a 2,7 vastag alsó perem 33-ig; a keresztmetszet így 316 mm², a lap 0,853 kg/fm tömegéből 316 mm²."""
    from shapely.geometry import Point, Polygon, box

    def sector(c, r, a0, a1, n=90):
        return Polygon([c] + [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                               c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)])

    L, Rc, tip = (9, 9), (25, 9), -61
    A = Point(L).buffer(9, 256).difference(Point(L).buffer(7, 256)).difference(sector(L, 20, tip, 0))
    B = sector(Rc, 9, 90, 270).difference(Point(Rc).buffer(6.2, 256))
    E = box(9, 9, 25, 18).difference(Point(L).buffer(7, 256)).difference(Point(Rc).buffer(6.2, 256))
    g = A.union(B).union(E).union(box(25, 0, 70, 2.8)).union(box(25, 15.3, 33, 18))
    a = math.radians(tip)
    g = g.union(Point(L[0] + 8 * math.cos(a), L[1] + 8 * math.sin(a)).buffer(1, 64))
    return g.buffer(0.3, join_style=1).buffer(-0.6, join_style=1).buffer(0.3, join_style=1)


def profil_3101():
    """203101 (spanner profil, Kęty B3101): 35 × 70; felül a 2 × R2-es gyöngy (5 × 5,4), a perem felső síkja 3 mm-rel
    lejjebb, 5 mm vastag (10 mm-től 45°-kal), a jobb oldali fal 5 vastag (x = 30–35) 40 mm hosszan, R5-ös belső
    sarkokkal; alul 10°-os egyenesből R20 / R24-es ív fut az R4-es gömbvégbe (R3-mal); a keresztmetszet így 558 mm²,
    a rajzon 565 mm²."""
    from shapely.geometry import Point, Polygon, box
    yt, yb = 2.94, 42.94
    C = np.array([23.984, 65.19])  # az R20 / R24 ív középpontja: érinti a 10°-os egyenest és az R4-es gömböt
    P = np.array([35, yb])
    d = np.array([-math.cos(math.radians(10)), math.sin(math.radians(10))])
    T1 = P + ((C - P) @ d) * d
    a1 = math.degrees(math.atan2(T1[1] - C[1], T1[0] - C[0]))
    arc = lambda r, a0, a1_: [tuple(C + r * np.array([math.cos(math.radians(a)), math.sin(math.radians(a))]))
                              for a in np.linspace(a0, a1_, 40)]
    d2 = np.array([math.cos(math.radians(15)), -math.sin(math.radians(15))])
    Q = np.array([26.1, 39.2])
    T2 = Q + ((C - Q) @ d2) * d2
    a2 = math.degrees(math.atan2(T2[1] - C[1], T2[0] - C[0]))
    inner, outer = arc(20, a1, -165 if a1 < 0 else 195), arc(24, 182, a2 + 360 if a2 < 0 else a2)
    K = Q + ((30 - Q[0]) / d2[0]) * d2
    pts = [(5, yt), (35, yt), (35, yb)] + inner + outer + [tuple(K), (30, yt + 5), (12.6, yt + 5), (10, 5.4), (5, 5.4)]
    rr = [0.5, 0.2, 0.2] + [0] * (len(inner) + len(outer)) + [5, 5, 1, 1, 0]
    g = Polygon(fillet(pts, rr)).buffer(0)
    g = g.union(Polygon(fillet([(0, 0), (5, 0), (5, 5.4), (0, 5.4)], [2, 2, 0, 2]))).union(Point(4, 66).buffer(4, 128))
    g = g.buffer(1.5, join_style=1).buffer(-1.5, join_style=1)
    return g.union(g.buffer(3, join_style=1).buffer(-3, join_style=1).intersection(box(0, 55, 14, 70)))


def profil_7461():
    """237461 (50×260 mm-es L belső védőprofil, Constellium 7461): 50 magas, 260 hosszú, a lemez 2 vastag; a
    sarok kívül R7,5, belül R5; a 3 mm-es függőleges szár a tetejétől 7,5 mm-re 15 mm hosszon 2,5-re vékonyodik, a
    teteje R3; a lemezen három 20 mm-es, felül egyenes kiemelt borda (4 mm-ig, alul 2 db 8,5 mm-es zsebbel)
    57,4 / 119,8 / 182,3 mm-nél, a végén zsebbel és lejtővel záródó perem (a gyári rajz és a Quadris által küldött részletek szerint)."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    # a szár 3 vastag; a tetejétől 7,5 mm-re 15 mm hosszon belül 2,5-re vékonyodik (ferde felső, lekerekített alsó
    # átmenet), a teteje belül R3-mal lekerekített
    pts = [(0, 0, 0.2), (3, 0, 2.8), (3, 7.5, 0), (2.5, 8, 0), (2.5, 22.5, 0.6), (3, 23, 0.6), (3, 48, 5),
           (260, 48, 0), (260, 50, 0), (0, 50, 7.5)]
    base = Polygon(fillet([(x, y) for x, y, _ in pts], [r for *_, r in pts]))
    from shapely.geometry import box

    def pocket(xa, xb):  # alulról nyitott zseb: lekerekített (R1,5) felső sarkok, 2 mm anyag marad felette
        r = 1.5
        return Polygon(fillet([(xa, 50.5), (xa, 48), (xb, 48), (xb, 50.5)], [0, r, r, 0]))

    # a borda felül egyenes, 20 mm-es kiemelt sáv (2 mm-rel feljebb, 45°-os 2 mm-es rámpákkal); alul két 8,5 mm-es
    # zseb, köztük 3 mm-es középső borda a lemez aljáig
    g = base
    for x0 in (57.4, 119.8, 182.3):
        g = g.union(Polygon([(x0 - 2, 48.5), (x0 - 2, 48), (x0, 46), (x0 + 20, 46), (x0 + 22, 48), (x0 + 22, 48.5)]))
        g = g.difference(pocket(x0, x0 + 8.5)).difference(pocket(x0 + 11.5, x0 + 20))
    # záró perem: 2 mm rámpa, 8 mm egyenes, 7 mm lejtő a végéig; alul 8,5 mm-es zseb 2 mm-rel a rámpa kezdete után
    g = g.union(Polygon([(243, 48.5), (243, 48), (245, 46), (253, 46), (260, 48), (260, 48.5)]))
    g = g.difference(pocket(245, 253.5))
    return g.buffer(0.6, join_style=1).buffer(-1.0, join_style=1).buffer(0.4, join_style=1)


def vector_mask(geom, scale=30):
    x0, y0, x1, y1 = geom.bounds
    m = np.zeros((round((y1 - y0) * scale) + 1, round((x1 - x0) * scale) + 1), np.uint8)
    polys = getattr(geom, "geoms", [geom])
    for p in polys:
        cv2.fillPoly(m, [np.round((np.array(p.exterior.coords) - (x0, y0)) * scale).astype(np.int32)], 1)
        for r in p.interiors:
            cv2.fillPoly(m, [np.round((np.array(r.coords) - (x0, y0)) * scale).astype(np.int32)], 0)
    return m > 0


def decin_mask(code, cav_px, r, edits=(), k=None, smooth=0):
    cfg = C.DRAWINGS[code]
    img = np.asarray(_decin_lines(C, code))
    P = 40
    ink = np.pad((img < 128).astype(np.uint8), P)
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    ink = cv2.dilate(ink, se)  # a szkennelt vonalak kis szakadásainak bezárása
    white = (1 - ink).astype(np.uint8)
    n, lab, _, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    dist = cv2.distanceTransform(white, cv2.DIST_L2, 3)
    solid = np.ones_like(ink, bool)
    for i in range(1, n):
        comp = lab == i
        if i == lab[0, 0] or dist[comp].max() > cav_px / 2:  # külső tér vagy üreg
            solid[comp] = False
    m = cv2.erode(solid.astype(np.uint8), se)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))  # kettős vonal maradéka
    k = k or (15 if r > 5 else 13)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))  # jelölések, csonkok
    x0, y0 = cfg["crop"][:2]
    for kind, poly in edits:  # kézi javítás a PDF-oldal koordinátáiban [pt]: ("fill" / "clear", sokszög)
        pts = np.array([[round((x - x0) * C.ZOOM) + P, round((y - y0) * C.ZOOM) + P] for x, y in poly], np.int32)
        cv2.fillPoly(m, [pts], 1 if kind == "fill" else 0, lineType=cv2.LINE_8)
    if smooth:  # a szkennelés recésségének kisimítása
        m = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), smooth) > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    m = lab == 1 + int(np.argmax(st[1:, 4]))
    n, lab, st, _ = cv2.connectedComponentsWithStats((~m).astype(np.uint8), connectivity=4)
    for i in range(1, n):  # apró lyukak (szkennelési pöttyök) a profil anyagában
        if st[i, 4] < 3000:
            m[lab == i] = True
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _decin_lines(C, code):
    """A profil körvonala a constellium.py beállításaival, a megtartott méretek és pótlások nélkül."""
    cfg = C.DRAWINGS[code]
    saved = {k: cfg.get(k) for k in ("keep", "draw", "bold")}
    cfg.update(keep=[], draw=[], bold=1)
    try:
        return C.render(code, trim=False)
    finally:
        for k, v in saved.items():
            if v is None:
                cfg.pop(k, None)
            else:
                cfg[k] = v


# szürke kitöltésű, méret nélküli gyári képből, kitöltött fekete rajz a 227046 mintájára:
# slugok -> (forráskép, szélesség, magasság, alsó szélesség)
GRAY = {
    tuple(f"e-compact-tetoprofil-900407-{n}" for n in (5000, 5600, 6600, 7800, 8000)):
        ("data/forras/e_compact_a.png", "43", "112", "33"),
}


# kettős körvonalas (szürke) Edscha-lapból, kitöltött fekete rajz (227046 mintájára) + a 3D-hez a körvonal:
# slugok -> (forráskép, outline_mask beállításai, szélesség, magasság, alsó szélesség)
OUTLINE = {  # (az E/VOLUMEN a Quadris kérésére a kék profilból készül – EDSCHA_BLUE)
    tuple(f"e-small-tetoprofil-{n}-mm" for n in (6600, 7800, 8200)):
        ("data/forras/edscha_small_sin.png",
         dict(keep=(117, 165, 324, 493), erase=[(117, 150, 128, 327), (150, 150, 162, 192), (313, 150, 326, 167),
                                                (166, 410, 174, 466), (258, 432, 267, 500)], cav=11, r=2, shrink=2),
         "58,5", "95", None),
    # Versus Micro Trike tetősín (V35991, öt hossz): a katalóguslap szürke profilja feketére színezve
    tuple(f"v35991-{n}-mm-tetosin-micro-trike" for n in (6800, 7500, 7800, 8200, 8500)):
        ("data/forras/versus_micro_trike_sin.png", dict(keep=(40, 106, 332, 392), fill=True), "109", "103", "60"),
}


# az Edscha-lap tetőszerkezet-rajzának kék profilja feketére színezve (a Quadris kérésére ez a legjobb forrás):
# slugok -> (forráskép, kivágás, szélesség, magasság, alsó szélesség vagy None)
EDSCHA_BLUE = {
    tuple(f"e-volumen-tetoprofil-900301-{n}" for n in (7800, 8500, 9000, 9400, 9600, 10000)):
        ("data/forras/edscha_volumen_tetoszerkezet.png", (255, 125, 665, 660), "120", "163", "35"),
}


# színes (kék kitöltésű) gyári rajzból: slug -> (forráskép, szélesség, magasság, falvastagság vagy None = mérve, a falméret helye)
BLUE = {
    "207833-100x30-mm-alafutasgatlo-elox-profil": ("data/forras/207833_100x30_kek.png", "100", "30", None, ("v", 0.25)),
}


def outline_mask(path, keep, erase=(), cav=14, holes=(), scale=4, r=0, shrink=0):
    """Vékony, kettős körvonallal rajzolt (szürke kitöltésű) profilkép maszkja: a körvonal a megadott területen
    (keep = x0, y0, x1, y1; erase = kitörlendő méret- / tengelyvonalak), a vonalpárok közti keskeny sáv a fal,
    a széles fehér tartomány üreg; holes = keskeny üregek, amelyeket a szélesség alapján nem lehet felismerni."""
    g = np.asarray(Image.open(ROOT / path).convert("L")).astype(np.uint8)
    m = np.zeros_like(g)
    x0, y0, x1, y1 = keep
    m[y0:y1, x0:x1] = g[y0:y1, x0:x1] < 245
    for ex0, ey0, ex1, ey1 in erase:
        m[ey0:ey1, ex0:ex1] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    ink = np.pad((lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8), 10)
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    if r:
        ink = cv2.dilate(ink, se)  # a körvonal kis szakadásainak bezárása
    white = 1 - ink
    n, lab, _, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    outside = lab == lab[0, 0]
    # üreg csak ott marad, ahová egy cav átmérőjű kör befér: a keskeny rések, falközi csíkok kitöltve
    hole = cv2.morphologyEx(((white > 0) & ~outside).astype(np.uint8), cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (cav, cav))) > 0
    solid = ~outside & ~hole
    if r:
        solid = cv2.erode(solid.astype(np.uint8), se) > 0
    if shrink:  # a körvonal vastagságának fele a fal két oldalán (a fal a vonalak közepéig tart)
        solid = cv2.erode(solid.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * shrink + 1,) * 2)) > 0
    for hx0, hy0, hx1, hy1 in holes:
        solid[hy0 + 10:hy1 + 10, hx0 + 10:hx1 + 10] = False
    big = cv2.resize(solid.astype(np.float32), None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    big = cv2.GaussianBlur(big, (0, 0), scale * 0.6) > 0.5
    n, lab, st, _ = cv2.connectedComponentsWithStats(big.astype(np.uint8), connectivity=8)
    big = lab == 1 + int(np.argmax(st[1:, 4]))
    ys, xs = np.where(big)
    return big[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def fill_mask(path, keep, thr=205, scale=6, blur=0.35):
    """Szürkén kitöltött profilkép (a falak tömören szürkék, az üregek fehérek) maszkja: a küszöbnél sötétebb
    képpontok a megadott területen, felnagyítva és simítva – a feketére színezés egyszerű megfelelője."""
    a = np.asarray(Image.open(ROOT / path).convert("L")).astype(np.float32)
    x0, y0, x1, y1 = keep
    a = 255 - a[y0:y1, x0:x1]
    big = cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), scale * blur) > 255 - thr
    n, lab, st, _ = cv2.connectedComponentsWithStats(big.astype(np.uint8), connectivity=8)
    m = lab == 1 + int(np.argmax(st[1:, 4]))
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def gray_mask(path, scale=6, inset=6):
    """Szürke kitöltésű, sötét körvonalú (méret nélküli) profilkép maszkja: a nem fehér képpontok legnagyobb
    összefüggő tartománya (a lapkeret nélkül), felnagyítva és simítva."""
    a = np.asarray(Image.open(ROOT / path).convert("L")).astype(np.float32)
    a = a[inset:-inset, inset:-inset]
    big = cv2.resize(255 - a, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), scale * 0.4) > 20
    n, lab, st, _ = cv2.connectedComponentsWithStats(big.astype(np.uint8), connectivity=8)
    m = lab == 1 + int(np.argmax(st[1:, 4]))
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def blue_mask(path, scale=4, crop=None, smooth=0):
    """A kék kitöltésű profil maszkja (a fekete méretek, szaggatott vonal és felirat nélkül), felnagyítva;
    crop = (x0, y0, x1, y1) a lap kivágása (pl. a tetőszerkezet-rajz kék profilja a szürke elemek mellett)."""
    a = np.asarray(Image.open(ROOT / path).convert("RGB")).astype(np.float32)
    if crop:
        a = a[crop[1]:crop[3], crop[0]:crop[2]]
    blue = np.clip((a[:, :, 2] - a[:, :, 0] - 20) / 80, 0, 1)
    big = cv2.resize(blue, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if smooth:
        big = cv2.GaussianBlur(big, (0, 0), smooth)
    big = big > 0.5
    n, lab, st, _ = cv2.connectedComponentsWithStats(big.astype(np.uint8), connectivity=8)
    m = lab == 1 + int(np.argmax(st[1:, 4]))
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def body_mask(slug):
    """A profil maszkja az alvaz_rajzok.py lépéseivel (méretek rárajzolása nélkül)."""
    cat, mm = A.PROFILES[slug]
    rgb = A.load(A.CACHE / f"{slug}.png")
    for x0, y0, x1, y1 in A.ERASE.get(slug, []):
        rgb[y0:y1, x0:x1] = 255
    for x0, y0, x1, y1, t in A.REPAIR.get(slug, []):
        cv2.line(rgb, (x0, y0), (x1, y1), (0, 0, 0), t)
    if slug in A.DARKEN:
        L = rgb.mean(axis=2, keepdims=True)
        rgb = np.clip(255 - (255 - L) * 10, 0, 255).repeat(3, axis=2)
    for x0, y0, x1, y1, k in A.CLOSE_BOX.get(slug, []):
        sub = (rgb[y0:y1, x0:x1].mean(axis=2) < 170).astype(np.uint8)
        sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        rgb[y0:y1, x0:x1][sub > 0] = 0
    if slug in A.UPSCALE:
        rgb = cv2.resize(rgb, None, fx=A.UPSCALE[slug], fy=A.UPSCALE[slug], interpolation=cv2.INTER_CUBIC)
    if slug in A.ROTATE:
        rgb = np.ascontiguousarray(np.rot90(rgb, A.ROTATE[slug]))
    if cat in A.WALL_MM:
        _, prof0 = A.normalize(rgb, A.THICK.get(slug, 0.03), A.FILL_ALL.get(slug))
        wall = A.WALL_SLUG.get(slug, A.WALL_MM[cat])
        g, _ = A.normalize(rgb, A.THICK.get(slug, 0.03), A.FILL_ALL.get(slug), rmax=wall / 2 * prof0 / mm, snap=slug in A.SNAP)
    else:
        g, _ = A.normalize(rgb, A.THICK.get(slug, 0.03), A.FILL_ALL.get(slug))
    solid = (g < 110).astype(np.uint8)
    k = max(3, int(max(g.shape) * 0.006) | 1)
    body = cv2.morphologyEx(solid, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(body, connectivity=8)
    areas = st[1:, 4]
    core = np.isin(lab, [i + 1 for i, a in enumerate(areas) if a >= 0.05 * areas.max()])
    mask = (cv2.dilate(core.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & (solid > 0)  # a vékonyabb részek is
    ys, xs = np.where(mask)
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def runs(v):
    out, s = [], None
    for i, x in enumerate(v):
        if x and s is None:
            s = i
        if not x and s is not None:
            out.append((s, i - 1))
            s = None
    if s is not None:
        out.append((s, len(v) - 1))
    return out


def render(slug, wtext, htext, ttext, where, erase, wtop=None, target=1000):
    return render_mask(body_mask(slug), wtext, htext, ttext, where, erase, wtop, target)


def sketch_mask(path, scale=4, wipe=()):
    """Sraffozott falú, méretvonalak nélküli kis vázlatból (pl. a gyári lap sarkában lévő keresztmetszet) a profil:
    a sraffozás bezárása, a vékony tengely- és szaggatott vonalak, jelölések eltávolítása."""
    im = Image.open(ROOT / path).convert("L")
    a = np.asarray(im).copy()
    for x0, y0, x1, y1 in wipe:  # tengelyek, jelölések (a forráskép képpontjaiban)
        a[y0:y1, x0:x1] = 255
    im = Image.fromarray(a)
    g = np.asarray(im.resize((im.width * scale, im.height * scale), Image.LANCZOS))
    ink = (g < 170).astype(np.uint8)
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * scale + 1,) * 2))
    body = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * scale + 3,) * 2))
    n, lab, st, _ = cv2.connectedComponentsWithStats(body, connectivity=8)
    m = lab == 1 + int(np.argmax(st[1:, 4]))
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def render_mask(m, wtext, htext, ttext, where, erase=(), wtop=None, target=1000, outline=False, eps=None, vdims=(), bottom=None,
                hdims=(), walls=(), idims=()):
    H0, W0 = m.shape
    for fx0, fy0, fx1, fy1 in erase:
        m[int(fy0 * H0):int(fy1 * H0), int(fx0 * W0):int(fx1 * W0)] = False
        ys, xs = np.where(m)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        H0, W0 = m.shape
    k = target / max(H0, W0)
    big = cv2.resize(m.astype(np.uint8) * 255, (round(W0 * k), round(H0 * k)), interpolation=cv2.INTER_LINEAR) > 127
    cnts, hier = cv2.findContours(big.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = [cv2.approxPolyDP(c, eps or (2.0 if outline else 1.2), True) for c in cnts]
    ML, MT, MR, MB = 170 + 80 * len(vdims), 170, 150, 150 + (40 if bottom else 0) + 75 * len(hdims)
    h, w = big.shape
    canvas = np.full((h + MT + MB, w + ML + MR, 3), 255, np.uint8)
    shifted = [p + np.array([[ML, MT]]) for p in polys]
    if outline:  # vonalas rajz, mint a gyári lapon: a profil külső és belső körvonala
        cv2.drawContours(canvas, shifted, -1, (0, 0, 0), thickness=4, lineType=cv2.LINE_AA)
    else:
        cv2.drawContours(canvas, shifted, -1, (0, 0, 0), thickness=cv2.FILLED, lineType=cv2.LINE_AA, hierarchy=hier)
    img = Image.fromarray(canvas)
    d = ImageDraw.Draw(img)
    F = ImageFont.truetype(FONT, 36)

    def head(x, y, ang, sz=17):
        d.polygon([(x, y), (x + sz * math.cos(ang + 0.3), y + sz * math.sin(ang + 0.3)),
                   (x + sz * math.cos(ang - 0.3), y + sz * math.sin(ang - 0.3))], fill="black")

    def dim(p, q):  # méretvonal két befelé néző nyílheggyel
        a = math.atan2(q[1] - p[1], q[0] - p[0])
        head(*p, a)
        head(*q, a + math.pi)
        d.line([p, q], fill="black", width=2)

    def pointer(p, q):  # kívülről a q pontra mutató nyíl (vékony falhoz)
        a = math.atan2(p[1] - q[1], p[0] - q[0])
        head(*q, a)
        d.line([p, q], fill="black", width=2)

    x0, y0, x1, y1 = ML, MT, ML + w, MT + h
    xw = x1 if wtop is None else ML + max(np.where(big[: int(wtop * h)].any(axis=0))[0]) + 1
    # szélesség: felül (wtext nélkül elmarad)
    yd = y0 - 75
    if wtext:
        d.line([(x0, y0 - 10), (x0, yd - 16)], fill="black", width=2)
        d.line([(xw, y0 - 10), (xw, yd - 16)], fill="black", width=2)
        dim((x0, yd), (xw, yd))
        d.text(((x0 + xw) / 2, yd - 8), wtext, font=F, fill="black", anchor="mb")
    def vtext(xd, ya, yb, text):
        t = Image.new("RGBA", (220, 60), (255, 255, 255, 0))
        ImageDraw.Draw(t).text((110, 30), text, font=F, fill="black", anchor="mm")
        t = t.rotate(90, expand=True)
        img.paste(t, (int(xd - 48), int((ya + yb) / 2 - t.height / 2)), t)

    # további függőleges méretek (a magasság töredékeként: felső, alsó, felirat), a teljes magasság mellett belül
    for i, (fa, fb, text) in enumerate(vdims):
        xi, ya, yb = x0 - 85 - 80 * i, y0 + fa * h, y0 + fb * h
        for yy in (ya, yb):
            d.line([(x0 - 10, yy), (xi - 16, yy)], fill="black", width=2)
        dim((xi, ya), (xi, yb))
        vtext(xi, ya, yb, text)
    # magasság: balra (htext nélkül elmarad)
    xd = x0 - 85 - 80 * len(vdims)
    if htext:
        d.line([(x0 - 10, y0), (xd - 16, y0)], fill="black", width=2)
        d.line([(x0 - 10, y1), (xd - 16, y1)], fill="black", width=2)
        dim((xd, y0), (xd, y1))
        vtext(xd, y0, y1, htext)
    if bottom:  # alsó szélességméret: a legalsó sor bal szélétől a profil jobb széléig (pl. az alsó doboz)
        cols = np.where(big[-max(2, h // 60):].any(axis=0))[0]
        xa, xb, yb = ML + cols.min(), ML + cols.max(), y1 + 75
        d.line([(xa, y1 + 10), (xa, yb + 16)], fill="black", width=2)
        d.line([(xb, y1 + 10), (xb, yb + 16)], fill="black", width=2)
        dim((xa, yb), (xb, yb))
        d.text(((xa + xb) / 2, yb + 8), bottom, font=F, fill="black", anchor="mt")
    # további vízszintes méretek alul, egymás alatt (a szélesség töredékeként: bal, jobb, felirat)
    for i, (fa, fb, text) in enumerate(hdims):
        xa, xb, yb = x0 + fa * w, x0 + fb * w, y1 + 75 * (i + 1)
        for xx in (xa, xb):
            d.line([(xx, y1 + 10), (xx, yb + 16)], fill="black", width=2)
        dim((xa, yb), (xb, yb))
        d.text(((xa + xb) / 2, yb - 6), text, font=F, fill="black", anchor="mb")
    # további falvastagságok: ("hx", sor-arány, x-arány, felirat) = vízszintes méret az adott sorban, azon a falon át,
    # amely az x-arány helyén van (pl. egy belső, függőleges borda)
    for kind, rf, xf, text in walls:
        row = int(rf * h)
        col = int(xf * w)
        for a, b in runs(big[row]):
            if a - 3 <= col <= b + 3:
                ya = MT + row
                pointer((ML + a - 55, ya), (ML + a, ya))
                pointer((ML + b + 55, ya), (ML + b, ya))
                d.line([(ML + a, ya), (ML + b, ya)], fill="black", width=2)
                d.text((ML + b + 62, ya), text, font=F, fill="black", anchor="lm")
                break
    # belső méretek a profilon belül: ("v", x-arány, y0-arány, y1-arány, felirat) / ("h", y-arány, x0, x1, felirat)
    for kind, f, a0, a1, text in idims:
        if kind == "v":
            xx = x0 + f * w
            dim((xx, y0 + a0 * h), (xx, y0 + a1 * h))
            d.text((xx - 10, y0 + (a0 + a1) / 2 * h), text, font=F, fill="black", anchor="rm")
        else:
            yy = y0 + f * h
            dim((x0 + a0 * w, yy), (x0 + a1 * w, yy))
            d.text((x0 + (a0 + a1) / 2 * w, yy - 8), text, font=F, fill="black", anchor="mb")
    if where is None:
        return img, 0, k, (W0, H0), (xw - x0) / k
    # falvastagság
    kind, frac = where
    if kind == "h":  # a bal oldali falon át, adott magasságban
        row = int(frac * h)
        a, b = runs(big[row])[0]
        ya = MT + row
        pointer((ML + a - 55, ya), (ML + a, ya))
        pointer((ML + b + 55, ya), (ML + b, ya))
        d.line([(ML + a, ya), (ML + b, ya)], fill="black", width=2)
        d.text((ML + b + 62, ya), ttext, font=F, fill="black", anchor="lm")
        px = b - a + 1
    else:  # az alsó falon át, adott vízszintes helyen
        col = int(frac * w)
        a, b = runs(big[:, col])[-1]
        xa = ML + col
        pointer((xa, MT + a - 55), (xa, MT + a))
        pointer((xa, MT + b + 55), (xa, MT + b))
        d.text((xa + 12, MT + a - 40), ttext or "", font=F, fill="black", anchor="lm")
        px = b - a + 1
    return img, px, k, (W0, H0), (xw - x0) / k


def main():
    data = load_enrichment()
    for slug, (wt, ht, tt, where, erase, *opt) in ITEMS.items():
        if slug not in data:
            continue
        wtop = opt[0] if opt else None
        img, px, k, _, wpx = render(slug, wt, ht, tt or "?", where, erase, wtop)
        if tt is None:  # a falvastagság a rajzból mérve (a szélesség méretéhez viszonyítva)
            mm = px / (wpx * k) * float(wt.replace(",", "."))
            tt = f"{mm:.1f}".replace(".", ",")
            img, *_ = render(slug, wt, ht, tt, where, erase, wtop)
        url = save_image(img, slug, "meretrajz")
        e = data[slug]
        e["images"] = [url] + [u for u in e.get("images", []) if u != url]
        e.setdefault("specs", {})["Falvastagság"] = f"{tt} mm"
        print(slug, "falvastagság:", tt)
    for slug, (code, cav, r, edits, wt, ht, tt, where, *opt) in DECIN.items():
        if slug not in data:
            continue
        m = decin_mask(code, cav, r, edits, opt[1] if len(opt) > 1 else None, opt[2] if len(opt) > 2 else 0)
        img, px, k, _, wpx = render_mask(m.copy(), wt, ht, tt, where, wtop=opt[0] if opt else None, outline=True)
        print(slug, "mért fal:", round(px / (wpx * k) * float(wt.replace(",", ".")), 2), "mm")
        url = save_image(img, slug, "meretrajz")
        fill, *_ = render_mask(m.copy(), wt, ht, tt, where, wtop=opt[0] if opt else None)  # kitöltött, mint a 227046
        # csak a Decin-rajz (vonalas + kitöltött): minden korábbi kép (régi rajzok, 3D) törölve
        data[slug]["images"] = [save_image(fill, slug, "kitoltott"), url]  # a fekete az első
        data[slug].setdefault("specs", {})["Falvastagság"] = f"{tt} mm"
    for slug, (fn, wt, ht, tt, where, *vd) in VECTOR.items():
        if slug not in data and slug in NEW:
            data[slug] = {"source": NEW[slug][0], "sourceUrl": NEW[slug][1], "sourceTitle": NEW[slug][2], "specs": {}, "images": []}
        if slug in NEW:
            data[slug]["specs"].update(NEW[slug][3])
        if slug not in data:
            continue
        m = vector_mask(globals()[fn]())
        kw = vd[0] if vd and isinstance(vd[0], dict) else {"vdims": vd[0] if vd else ()}
        img, *_ = render_mask(m.copy(), wt, ht, tt, where, outline=True, eps=0.5, **kw)
        fill, *_ = render_mask(m.copy(), wt, ht, tt, where, eps=0.5, **kw)  # kitöltött, mint a 227046
        data[slug]["images"] = [save_image(fill, slug, "kitoltott"), save_image(img, slug, "meretrajz")]  # a fekete az első
        if slug in PHOTOS:  # a küldött adatlap a forrás (a gyártói cikkszám nem jelenik meg)
            data[slug].update({"source": "Quadris katalóguslap", "sourceUrl": "", "sourceTitle": ""})
            data[slug].pop("matchedCode", None)
            src, box_ = PHOTOS[slug]
            ph = np.asarray(Image.open(ROOT / src).convert("RGB").crop(box_)).astype(np.float32)
            ph = np.clip((ph - 0) * 255 / np.maximum(ph.max(axis=(0, 1)), 1), 0, 255)  # a szürkés háttér fehérre
            if slug in SHARPEN:  # a kis, elmosódott termékkép felnagyítva és élesítve (a Quadris kérésére)
                for ex0, ey0, ex1, ey1 in SHARPEN[slug]:
                    ph[ey0:ey1, ex0:ex1] = 255
                big = Image.fromarray(np.clip(ph, 0, 255).astype(np.uint8)).resize((ph.shape[1] * 5, ph.shape[0] * 5), Image.BICUBIC)
                big = big.filter(ImageFilter.GaussianBlur(1.5)).filter(ImageFilter.UnsharpMask(radius=5, percent=180, threshold=1))
                b = np.asarray(big).astype(np.float32)
                w = np.clip((b.min(axis=2, keepdims=True) - 212) / 30, 0, 1)  # lágy átmenet a fehér háttérbe
                b = b * (1 - w) + 255 * w
                ys, xs = np.where(b.min(axis=2) < 235)
                ph = Image.fromarray(b.astype(np.uint8)).crop((max(xs.min() - 30, 0), max(ys.min() - 30, 0),
                                                               min(xs.max() + 30, b.shape[1]), min(ys.max() + 30, b.shape[0])))
            else:
                ph[ph.min(axis=2) > 232] = 255
                ph = Image.fromarray(ph.astype(np.uint8))
            data[slug]["images"].append(save_image(ph, slug, "foto"))
        for v in RENDER3D.get(slug, []):
            u = f"/termekkepek/3d/{slug}-{v}.webp"
            if (ROOT / "public" / u.lstrip("/")).exists():
                data[slug]["images"].append(u)
        if slug in SPEC_FIX:
            data[slug].setdefault("specs", {}).update(SPEC_FIX[slug])
        if tt:  # tömör profilnál nincs falvastagság
            data[slug].setdefault("specs", {})["Falvastagság"] = f"{tt} mm"
        else:
            data[slug].get("specs", {}).pop("Falvastagság", None)
        print(slug, "vektoros")
    for slug, items in IMAGESET.items():
        if slug not in data and slug in NEW:
            data[slug] = {"source": NEW[slug][0], "sourceUrl": NEW[slug][1], "sourceTitle": NEW[slug][2],
                          "specs": dict(NEW[slug][3]), "images": []}
        if slug in data:
            data[slug]["images"] = [save_image(Image.open(ROOT / src), slug, suf) for src, suf in items]
            print(slug, "képkészlet")
    for slug, (src, keep, wt, ht, tt, where, kw) in GRAYVIEW.items():
        if slug not in data:
            continue
        m = fill_mask(src, keep, thr=215, blur=0.7)
        img, *_ = render_mask(m.copy(), wt, ht, tt, where, outline=True, eps=0.8, **kw)
        fill, *_ = render_mask(m.copy(), wt, ht, tt, where, eps=0.8, **kw)
        data[slug]["images"] = [save_image(fill, slug, "kitoltott"), save_image(img, slug, "meretrajz")]  # a fekete az első
        data[slug].update({"source": "Quadris gyári rajz", "sourceUrl": "", "sourceTitle": ""})
        data[slug].setdefault("specs", {}).update(SPEC_FIX.get(slug, {}))
        data[slug]["specs"]["Falvastagság"] = f"{tt} mm"
        print(slug, "szürke nézetből")
    for slug, (src, crop, ero, hmm, rot, wt, ht, tt, where, er) in TRACE.items():
        if slug not in data:
            continue
        m = trace_mask(src, crop, ero, hmm, rot, er)
        img, *_ = render_mask(m.copy(), wt, ht, tt, where, outline=True, eps=0.8)
        fill, *_ = render_mask(m.copy(), wt, ht, tt, where, eps=0.8)
        data[slug]["images"] = [save_image(fill, slug, "kitoltott"), save_image(img, slug, "meretrajz")]  # a fekete az első
        data[slug].setdefault("specs", {})["Falvastagság"] = f"{tt} mm"
        data[slug]["specs"].pop("Profilszám (gyártói)", None)  # a gyártói profilszám nem jelenik meg
        data[slug].pop("matchedCode", None)
        print(slug, "gyári főnézetből")
    for slug, (src, crop, specs, *er) in RAW.items():
        if slug not in data:
            continue
        g = np.asarray(Image.open(ROOT / src).convert("L").crop(crop)).astype(np.float32)
        g = np.clip((g - 60) * 255 / (200 - 60), 0, 255)  # fekete vonalak, fehér háttér
        for ex0, ey0, ex1, ey1 in (er[0] if er else ()):  # a Quadris kérésére kivett feliratok (a kivágáson belül)
            g[ey0:ey1, ex0:ex1] = 255
        url = save_image(Image.fromarray(g.astype(np.uint8)), slug, "gyari-rajz")
        # ha a méretekből rajzolt (VECTOR) kép is van, a gyári rajz utánuk jön; különben ez az egyetlen kép
        prev = [u for u in data[slug].get("images", []) if u.endswith(("-meretrajz.webp", "-kitoltott.webp"))] if slug in VECTOR or slug in TRACE else []
        data[slug]["images"] = prev + [url]
        data[slug].update({"source": "Quadris gyári rajz", "sourceUrl": "", "sourceTitle": ""})
        data[slug].setdefault("specs", {}).update(specs)
        print(slug, "gyári rajz")
    for slug, (src, crop, rot, wt, ht) in DARK.items():
        if slug not in data:
            continue
        m = dark_mask(src, crop, rot)
        img, *_ = render_mask(m.copy(), wt, ht, "", None, eps=0.8, outline=True)
        fill, *_ = render_mask(m.copy(), wt, ht, "", None, eps=0.8)
        data[slug]["images"] = [save_image(fill, slug, "kitoltott"), save_image(img, slug, "meretrajz")]  # a fekete az első
        data[slug].update({"source": "Quadris katalóguslap", "sourceUrl": "", "sourceTitle": ""})
        data[slug].pop("matchedCode", None)
        if slug in PHOTOS:
            src2, box_ = PHOTOS[slug]
            ph = np.asarray(Image.open(ROOT / src2).convert("RGB").crop(box_)).astype(np.float32)
            ph[ph.min(axis=2) > 232] = 255
            data[slug]["images"].append(save_image(Image.fromarray(ph.astype(np.uint8)), slug, "foto"))
        data[slug].setdefault("specs", {}).update(SPEC_FIX.get(slug, {}))
        print(slug, "sötét profilrajzból")
    for slugs, (src, crop, wt, ht, bt) in EDSCHA_BLUE.items():
        m = blue_mask(src, scale=4, crop=crop, smooth=1.5)
        img, *_ = render_mask(m, wt, ht, "", None, eps=1.0, bottom=bt)
        for slug in slugs:
            if slug in data:
                url = save_image(img, slug, "meretrajz")
                data[slug]["images"] = [url] + [u for u in data[slug].get("images", []) if u != url]
                print(slug, "kék profilból")
    for slugs, (src, cfg, wt, ht, bt) in OUTLINE.items():
        m = fill_mask(src, cfg["keep"]) if cfg.get("fill") else outline_mask(src, **cfg)
        img, *_ = render_mask(m.copy(), wt, ht, "", None, eps=1.0, bottom=bt)
        for slug in slugs:
            if slug in data:
                url = save_image(img, slug, "meretrajz")
                data[slug]["images"] = [url] + [u for u in data[slug].get("images", []) if u != url]
                print(slug, "körvonalas képből")
    for slugs, (src, wt, ht, bt) in GRAY.items():
        m = gray_mask(src)
        m = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8))  # a forrás sötét körvonala kívül van
        m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3) > 0.5  # a kis kép recéinek kisimítása
        img, *_ = render_mask(m, wt, ht, "", None, eps=1.0, bottom=bt)
        for slug in slugs:
            if slug in data:
                url = save_image(img, slug, "meretrajz")
                data[slug]["images"] = [url] + [u for u in data[slug].get("images", []) if u != url]
                print(slug, "szürke képből")
    for slug, (src, wt, ht, tt, where) in BLUE.items():
        if slug not in data:
            continue
        m = blue_mask(src)
        if tt is None:
            _, px, k, _, wpx = render_mask(m.copy(), wt, ht, "", where)
            tt = f"{px / (wpx * k) * float(wt.replace(',', '.')):.1f}".replace(".", ",")
        img, *_ = render_mask(m.copy(), wt, ht, tt, where)
        url = save_image(img, slug, "meretrajz")
        data[slug]["images"] = [url] + [u for u in data[slug].get("images", []) if u != url]
        data[slug].setdefault("specs", {})["Falvastagság"] = f"{tt} mm"
        print(slug, "kék rajzból, fal:", tt)
    for slug, (src, wt, ht, tt, where, wipe) in SKETCH.items():
        data.setdefault(slug, {"source": "Quadris gyári rajz", "sourceUrl": "", "specs": {}, "images": []})
        img, *_ = render_mask(sketch_mask(src, wipe=wipe), wt, ht, tt, where)
        url = save_image(img, slug, "meretrajz")
        data[slug]["images"] = [url] + [u for u in data[slug].get("images", []) if u != url]
        data[slug].setdefault("specs", {})["Falvastagság"] = f"{tt} mm"
        print(slug, "vázlatból")
    update_enrichment({s: data[s] for s in list(ITEMS) + list(DECIN) + list(VECTOR) + [x for k in GRAY for x in k] + [x for k in OUTLINE for x in k] + [x for k in EDSCHA_BLUE for x in k] + list(DARK) + list(RAW) + list(GRAYVIEW) + list(IMAGESET) + list(BLUE) + list(SKETCH) if s in data})


if __name__ == "__main__":
    main()
