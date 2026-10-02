"""Kis felbontású katalóguslap-rajzok (RE-ALL 380034, 380035) élesítése: a fekete profil élsimítva marad, a méret-
és segédvonalak, a nyílhegyek és a számok a lap szerinti helyükön vektorosan, élesen újrarajzolva.
Kimenet: data/forras/<kód>_rajz.png (a tiszta_rajzok.py IMAGESET innen veszi).

Használat: python3 scripts/termekadatok/meretvonal_ujrarajz.py
"""
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT  # noqa: E402

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SS = 3  # túlmintavételezés az élsimításhoz


def crisp(src, box, S=4):
    """A lap rajzrésze (keret nélkül) felnagyítva, éles kontrasztgörbével."""
    a = np.asarray(Image.open(ROOT / src).convert("L")).astype(np.float32)[box[1]:box[3], box[0]:box[2]]
    ink = a < 200
    a[:, ink.mean(axis=0) > 0.8] = 255
    a[ink.mean(axis=1) > 0.8, :] = 255
    ys, xs = np.where(a < 200)
    a = a[max(ys.min() - 12, 0):ys.max() + 12, max(xs.min() - 12, 0):xs.max() + 12]
    d = cv2.resize(a, None, fx=S, fy=S, interpolation=cv2.INTER_CUBIC)
    d = cv2.GaussianBlur(d, (0, 0), S * 0.3)
    return (255 / (1 + np.exp(-(d - 190) / 12))).astype(np.uint8)


def profile_only(d):
    """Csak a legnagyobb sötét folt (a profil) marad, élsimított széllel."""
    n, lab, st, _ = cv2.connectedComponentsWithStats((d < 128).astype(np.uint8), connectivity=8)
    keep = cv2.dilate((lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    out = np.full_like(d, 255)
    out[keep] = d[keep]
    return out


def draw(d, lines, dims, texts):
    """lines: segédvonalak [(x0, y0, x1, y1)]; dims: méretvonalak nyíllal mindkét végén [(x0, y0, x1, y1, rés-közép, rés)];
    texts: [(x, y, szöveg)]."""
    H, W = d.shape
    im = Image.fromarray(d).resize((W * SS, H * SS), Image.LANCZOS)
    g = ImageDraw.Draw(im)
    s = lambda *p: [v * SS for v in p]
    lw = 2 * SS
    for x0, y0, x1, y1 in lines:
        g.line(s(x0, y0, x1, y1), fill=0, width=lw)
    for x0, y0, x1, y1, gap in dims:
        L = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        if gap:  # szakadás a szám helyén
            c, h = gap
            g.line(s(x0, y0, x0 + ux * (c - h), y0 + uy * (c - h)), fill=0, width=lw)
            g.line(s(x0 + ux * (c + h), y0 + uy * (c + h), x1, y1), fill=0, width=lw)
        else:
            g.line(s(x0, y0, x1, y1), fill=0, width=lw)
        for (tx, ty), sgn in (((x0, y0), 1), ((x1, y1), -1)):  # a nyíl hegye a segédvonalon, befelé nyitva
            al, aw = 16, 5
            bx, by = tx + sgn * ux * al, ty + sgn * uy * al
            g.polygon(s(tx, ty, bx - uy * aw, by + ux * aw, bx + uy * aw, by - ux * aw), fill=0)
    f = ImageFont.truetype(FONT, 34 * SS)
    for x, y, t in texts:
        g.text((x * SS, y * SS), t, font=f, fill=0, anchor="mm")
    return im.resize((W, H), Image.LANCZOS)


ITEMS = {
    # 380034: 80 × 28, csillag furat 15,3 (három irányban)
    "380034": ("data/forras/380034_lap.png", (6, 10, 362, 172),
               [(60, 170, 205, 170), (60, 405, 205, 405), (135, 225, 205, 225), (135, 345, 205, 345),
                (175, 50, 290, 160), (100, 140, 205, 245), (60, 445, 205, 330), (165, 525, 290, 405),
                (218, 405, 218, 552), (322, 405, 322, 505), (876, 322, 876, 560)],
               [(72, 170, 72, 405, (117, 22)), (148, 225, 148, 345, (60, 22)), (180, 68, 103, 140, None),
                (95, 440, 178, 520, None), (218, 494, 322, 494, None), (322, 494, 876, 494, (233, 40)),
                (218, 545, 876, 545, (337, 40))],
               [(70, 290, "28"), (148, 290, "15,3"), (100, 80, "15,3"), (85, 505, "15,3"), (270, 470, "14"),
                (555, 494, "66"), (555, 545, "80")]),
    # 380035: 55 × 20, furat Ø14
    "380035": ("data/forras/380035_lap.png", (6, 14, 330, 166),
               [(178, 62, 178, 122), (625, 62, 625, 122), (62, 147, 205, 147), (62, 312, 205, 312),
                (115, 178, 178, 178), (115, 290, 178, 290)],
               [(178, 75, 625, 75, (223, 50)), (70, 147, 70, 312, (90, 20)), (130, 178, 130, 290, (58, 20))],
               [(408, 75, "55"), (70, 239, "20"), (132, 236, "ø14")]),
}


def main():
    for code, (src, box, lines, dims, texts) in ITEMS.items():
        im = draw(profile_only(crisp(src, box)), lines, dims, texts)
        im.save(ROOT / f"data/forras/{code}_rajz.png")
        print(code, "kész")


if __name__ == "__main__":
    main()
