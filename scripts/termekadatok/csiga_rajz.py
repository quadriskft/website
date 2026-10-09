"""106731 lezáró csiga (bal / jobb): a Quadris által küldött kis balos rajzból (data/forras/106731_bal_rajz.png, MI-vel
4x nagyítva, a gyári kód nélkül) éles rajz. A térbeli nézet háromtónusú (fehér / szürke kitöltés / fekete vonal)
simított maszkokból újraépítve, a méretezett oldalnézet és a méretvonalak vektorosan újrarajzolva, a számok
betűtípussal. A jobbos kivitel a balos tükörképe (a feliratok nem tükrözve).

Használat: python3 scripts/termekadatok/csiga_rajz.py   (utána tiszta_rajzok.py)
"""

import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT  # noqa: E402

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
K = 2  # a 4x-es forrás további nagyítása
PX = 4.05 * K  # px / mm az oldalnézetben (a forrás méretaránya)
W, H = 960 * K, 700 * K
OX, OY = 645 * K, 255 * K  # az oldalnézet origója: a lemez bal felső sarka


def iso():
    """A térbeli nézet a vonalak és a szürke kitöltés simított maszkjából, éles szélekkel (a méretvonalak nélkül)."""
    g = np.asarray(Image.open(ROOT / "data/forras/106731_bal_rajz.png").convert("L")).astype(np.float32)
    g = g[:, :560].copy()
    g[494:600, 230:317] = 255  # a 25-ös méret vonalai és száma (újrarajzolva)
    g[468:494, 304:317] = 255
    # a lap alja, ahol a gyári kód mutatóvonala keresztezte: a szürke kitöltés és a két körvonal folytonosan
    g[485:489, 198:240] = 200
    g[492:503, 186:246] = 255
    cv2.line(g, (200, 482), (228, 482), 60, 4)
    cv2.polylines(g, [np.array([(184, 494), (226, 493), (240, 490), (250, 484)], np.int32)], False, 60, 5)
    g = cv2.resize(g, None, fx=K, fy=K, interpolation=cv2.INTER_CUBIC)

    def alpha(mask, sigma):
        b = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
        return np.clip((b - 0.5) * 2.2 + 0.5, 0, 1)

    dark = alpha(g < 165, 1.5)
    fill = alpha(g < 228, 2.0)
    out = 255 - (255 - 205) * fill
    out = out * (1 - dark) + 40 * dark
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def P(x, y):
    return (OX + x * PX, OY + y * PX)


def head(d, x, y, ang, sz=16):
    d.polygon([(x, y), (x + sz * math.cos(ang + 0.32), y + sz * math.sin(ang + 0.32)),
               (x + sz * math.cos(ang - 0.32), y + sz * math.sin(ang - 0.32))], fill="black")


def dim(d, p, q):
    a = math.atan2(q[1] - p[1], q[0] - p[0])
    d.line([p, q], fill="black", width=2)
    head(d, *p, a)
    head(d, *q, a + math.pi)


def graphics():
    """A balos rajz feliratok nélkül; visszaadja a feliratok helyét is: (szöveg, (x, y), horgony, forgatás)."""
    img = Image.new("L", (W, H), 255)
    img.paste(iso(), (0, 0))
    d = ImageDraw.Draw(img)
    texts = []

    def line(x0, y0, x1, y1, w=3, fill=40):
        d.line([P(x0, y0), P(x1, y1)], fill=fill, width=w)

    def rect(x0, y0, x1, y1, fill=None, w=3):
        d.rectangle([P(x0, y0), P(x1, y1)], outline=40, width=w, fill=fill)

    rect(0, 0, 10, 47)  # a lemez
    line(1, 0, 1, 47, 2, 110)  # a lemez élének letörése
    rect(10, 0, 55, 25)  # a felső, zsanérba illő rész
    line(10, 3.7, 55, 3.7, 2, 110)
    line(10, 4.9, 55, 4.9, 2, 110)
    rect(20, 9.3, 55, 11.5, fill=150, w=2)  # a 0,5 × 90°-os letörés sávja
    line(20, 0, 20, 11.5)
    line(10, 16.4, 55, 16.4, 2, 110)
    line(10, 17.4, 55, 17.4)
    rect(10, 33.5, 35, 40.5)  # az alsó fül
    line(10, 37.9, 35, 37.9, 2, 110)

    def hdim(xa, xb, y, text, ext_from):
        up = y < ext_from
        (pa, py), (pb, _) = P(xa, y), P(xb, y)
        for xx in (xa, xb):
            ex, ey = P(xx, ext_from)
            d.line([(ex, ey + (-10 if up else 10)), (ex, py + (-14 if up else 14))], fill="black", width=2)
        dim(d, (pa, py), (pb, py))
        texts.append((text, ((pa + pb) / 2, py - 6 if up else py + 6), "mb" if up else "mt", 0))

    hdim(0, 55, -14, "55", 0)
    hdim(20, 55, -6, "35", 0)
    hdim(0, 10, 54, "10", 47)
    hdim(10, 35, 54, "25", 40.5)
    (xv, ya), (_, yb) = P(-9, 0), P(-9, 47)  # magasság a lemez mellett
    for yy in (0, 47):
        ex, ey = P(0, yy)
        d.line([(ex - 10, ey), (xv - 14, ey)], fill="black", width=2)
    dim(d, (xv, ya), (xv, yb))
    texts.append(("47", (xv - 26, (ya + yb) / 2), "mm", 90))
    p0, p1 = P(40, 11.5), P(52, 30)  # a letörés mutatója
    d.line([p0, p1], fill="black", width=2)
    texts.append(("0,5×90°", (p1[0] + 4, p1[1] + 4), "lt", 0))
    # a térbeli nézet 25-ös mérete (a fül hossza): függőleges segédvonalak, a térbeli tengellyel párhuzamos méretvonal
    a, b = (257 * K, 490 * K), (311 * K, 474 * K)
    da, db = (257 * K, 588 * K), (311 * K, 560 * K)
    d.line([a, (da[0], da[1] + 10)], fill="black", width=2)
    d.line([b, (db[0], db[1] + 10)], fill="black", width=2)
    dim(d, da, db)
    ang = -math.degrees(math.atan2(db[1] - da[1], db[0] - da[0]))
    r = math.atan2(db[1] - da[1], db[0] - da[0]) + math.pi / 2  # a méretvonalra merőlegesen, alatta
    texts.append(("25", ((da[0] + db[0]) / 2 + 26 * math.cos(r), (da[1] + db[1]) / 2 + 26 * math.sin(r)), "mm", ang))
    return img, texts


def put_texts(img, texts, mirror):
    F = ImageFont.truetype(FONT, 34)
    d = ImageDraw.Draw(img)
    for text, (x, y), anchor, rot in texts:
        if mirror:
            x = W - x
            anchor = {"lt": "rt", "rt": "lt"}.get(anchor, anchor)
            rot = -rot if rot not in (90, -90) else rot
        if rot:
            t = Image.new("L", (200, 60), 0)
            ImageDraw.Draw(t).text((100, 30), text, font=F, fill=255, anchor="mm")
            t = t.rotate(rot, expand=True, resample=Image.BICUBIC)
            img.paste(Image.new("L", t.size, 0), (int(x - t.width / 2), int(y - t.height / 2)), t)
        else:
            d.text((x, y), text, font=F, fill="black", anchor=anchor)


def main():
    img, texts = graphics()
    bal = img.copy()
    put_texts(bal, texts, False)
    jobb = ImageOps.mirror(img)
    put_texts(jobb, texts, True)
    for name, im in (("bal", bal), ("jobb", jobb)):
        g = np.asarray(im) < 250
        ys, xs = np.where(g)
        m = 40
        im.crop((max(xs.min() - m, 0), max(ys.min() - m, 0), min(xs.max() + m, W), min(ys.max() + m, H))).convert("RGB") \
          .save(ROOT / f"data/forras/106731_{name}_rajz_tiszta.png")


if __name__ == "__main__":
    main()
