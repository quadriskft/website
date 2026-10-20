"""ADAICO vízjel (halvány „ADAICO” felirat és háromszög a kép közepén) eltávolítása a termékképekről, a Quadris
kérésére.

A vízjel a 600×400-as gyártói képeken mindig ugyanott, ugyanakkora: a mintája (data/forras/adaico_vizjel_minta.png)
sok vízjeles kép 80. percentiliséből készült (a fehér háttéren a vízjel maga). Eltávolítás: a kép osztása a mintával
(a vízjel áttetsző sötétítés), majd a vízjel helyén maradt halvány kontúrok fehérre a majdnem fehér háttérben.
Csak a vízjeles képek változnak (a bal szélső háromszög sávja alapján), így többször is futtatható.

Használat: python3 scripts/termekadatok/adaico_vizjel.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import IMAGE_DIR, ROOT  # noqa: E402

MINTA = ROOT / "data/forras/adaico_vizjel_minta.png"
NAGY = ["215014-adaico-rakonca-oszlop-3000-mm-2.webp", "381074-feszito-kocka-szogletes-adap-60x30x30-10-3.webp"]


def has_mark(g, k=1.0):
    strip = g[int(205 * k):int(255 * k), int(5 * k):int(35 * k)]
    return ((strip < 253) & (strip > 215)).mean() > 0.25


def main():
    minta = Image.open(MINTA).convert("RGB")
    cache = {}
    n = 0
    for f in sorted(IMAGE_DIR.glob("*.webp")):
        im = Image.open(f)
        w, h = im.size
        if im.size != (600, 400):
            continue
        k = w / 600
        J = np.asarray(im.convert("RGB")).astype(np.float32)
        if not has_mark(J.mean(axis=2), k):
            continue
        if im.size not in cache:
            T = np.asarray(minta.resize(im.size, Image.LANCZOS)).astype(np.float32)
            mask = cv2.dilate((T.min(axis=2) < 252).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            cache[im.size] = (T, mask)
        T, mask = cache[im.size]
        out = np.clip(J * 255 / np.maximum(T, 1), 0, 255)
        out[(out.min(axis=2) > 222) & mask] = 255
        Image.fromarray(out.astype(np.uint8)).save(f, "WEBP", quality=88, method=6)
        n += 1
    # nagyított, levágott vízjelű képek (fehér háttér, rajz / termék): a halvány háttérpixelek fehérre
    for name in NAGY:
        f = IMAGE_DIR / name
        if not f.exists():
            continue
        a = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
        light = (a.min(axis=2) > 222) & ((a.max(axis=2) - a.min(axis=2)) < 24)
        if ((a[light] < 250).any(axis=1)).sum() > a.shape[0] * a.shape[1] * 0.01:  # még van halvány vízjel
            a[light] = 255
            Image.fromarray(a.astype(np.uint8)).save(f, "WEBP", quality=88, method=6)
            n += 1
    print(n, "képről eltávolítva az ADAICO vízjel")


if __name__ == "__main__":
    main()
