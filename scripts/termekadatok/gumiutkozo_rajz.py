"""Görgős gumiütközők (502501 szimpla, 502502 dupla) méretezett rajza vektorosan újrarajzolva (a Quadris kérésére: a
küldött 150 px-es rajzon a méretszámok olvashatatlanok voltak). Csak a megnevezésből biztosan ismert főméretek
szerepelnek: szimpla 118 mm széles, Ø100 mm görgő; dupla 222 × 115 mm, Ø100 mm görgők. Elölnézet + oldalnézet.

Használat: python3 scripts/termekadatok/gumiutkozo_rajz.py   (utána kuldott_termekkepek.py)
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT  # noqa: E402

K = 4.2  # px / mm
INK = (34, 37, 41)
LW = 4


def font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


F = font(40)


def arrow(d, a, b):
    import math
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for p, s in ((a, 1), (b, -1)):
        for t in (0.35, -0.35):
            d.line([p, (p[0] + s * 22 * math.cos(ang + t), p[1] + s * 22 * math.sin(ang + t))], fill=INK, width=3)
    d.line([a, b], fill=INK, width=2)


def hdim(d, x0, x1, y, text, ext_from):
    d.line([(x0, ext_from), (x0, y - 12)], fill=INK, width=2)
    d.line([(x1, ext_from), (x1, y - 12)], fill=INK, width=2)
    arrow(d, (x0, y), (x1, y))
    w = d.textlength(text, font=F)
    d.text(((x0 + x1 - w) / 2, y - 52), text, fill=INK, font=F)


def vdim(img, d, x, y0, y1, text, ext_from):
    d.line([(ext_from, y0), (x - 12, y0)], fill=INK, width=2)
    d.line([(ext_from, y1), (x - 12, y1)], fill=INK, width=2)
    arrow(d, (x, y0), (x, y1))
    w = int(d.textlength(text, font=F)) + 8
    t = Image.new("RGBA", (w, 52), (255, 255, 255, 0))
    ImageDraw.Draw(t).text((4, 0), text, fill=INK, font=F)
    t = t.rotate(90, expand=True)
    img.paste(t, (int(x - 58), int((y0 + y1 - t.height) / 2)), t)


def draw(width_mm, height_mm, rollers, out):
    W, H = int((width_mm + 175) * K + 360), int((height_mm + 70) * K + 260)
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    # elölnézet
    x0, y0 = 150, 170
    x1, y1 = x0 + width_mm * K, y0 + height_mm * K
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, outline=INK, width=LW)
    m = 12 * K
    rw = (width_mm - 24 - (rollers - 1) * 4) / rollers
    for i in range(rollers):
        rx = x0 + m + i * (rw + 4) * K
        d.rounded_rectangle([rx, y0 + 16 * K, rx + rw * K, y1 - 10 * K], radius=26, outline=INK, width=LW)
    d.rectangle([x1, (y0 + y1) / 2 - 10 * K, x1 + 9 * K, (y0 + y1) / 2 + 10 * K], outline=INK, width=LW)  # tengelyvég
    d.rectangle([x0 - 6 * K, (y0 + y1) / 2 - 14 * K, x0, (y0 + y1) / 2 + 14 * K], outline=INK, width=LW)
    for i in range(int(width_mm // 20)):
        cx = x0 + (10 + i * 20) * K
        d.ellipse([cx - 9, y0 + 5 * K - 9, cx + 9, y0 + 5 * K + 9], outline=INK, width=3)  # rögzítőfuratok
    hdim(d, x0, x1, y0 - 70, f"{width_mm}", y0 - 10)
    vdim(img, d, x0 - 90, y0, y1, f"{height_mm}", x0 - 30)
    # oldalnézet
    sx = x1 + 150
    cx, cy, r = sx + 62 * K, y1 - 50 * K, 50 * K
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=LW)
    d.ellipse([cx - 13 * K, cy - 13 * K, cx + 13 * K, cy + 13 * K], outline=INK, width=LW)
    d.ellipse([cx - 7 * K, cy - 7 * K, cx + 7 * K, cy + 7 * K], outline=INK, width=3)
    house = [(sx, y0 + 25 * K), (sx + 22 * K, y0), (sx + 78 * K, y0), (sx + 78 * K, y0 + 14 * K),
             (sx + 72 * K, y0 + 14 * K), (sx + 72 * K, y0 + 6 * K), (sx + 25 * K, y0 + 6 * K), (sx + 6 * K, y0 + 28 * K),
             (sx + 6 * K, y1 - 6 * K), (sx + 18 * K, y1 - 6 * K), (sx + 18 * K, y1), (sx, y1)]
    d.line(house + [house[0]], fill=INK, width=LW, joint="curve")
    d.line([(cx + r * 0.7, cy - r * 0.7), (cx + r + 60, cy - r - 60)], fill=INK, width=2)
    d.text((cx + r + 50, cy - r - 110), "Ø100", fill=INK, font=F)
    a = __import__("numpy").asarray(img.convert("L")) < 235
    ys, xs = a.nonzero()
    img.crop((max(xs.min() - 40, 0), max(ys.min() - 40, 0), min(xs.max() + 40, W), min(ys.max() + 40, H))).save(out)


if __name__ == "__main__":
    draw(118, 118, 1, ROOT / "data/forras/502501_rajz.png")
    draw(222, 115, 2, ROOT / "data/forras/502502_rajz.png")
    print("kész")
