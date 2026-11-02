"""„Platós és ponyvás oldalfal profilok, szegő profilok” csoport fő képe (a Quadris kérésére): felül a Quadris által
küldött oldalfal-katalóguskép (MI-vel 4x nagyítva, élesítve, a jobb széle elhalványítva), alatta (nem rá) a küldött műszaki
rajzok szerinti öt szegő profil saját 3D renderje (scripts/profil3d: szego_sor.json, renderRow), élénkebb kontraszttal.

Bemenet: data/forras/oldalfal_katalogus.png, a profilsor renderje (argumentum, átlátszó PNG)
Kimenet: public/csoportkepek/ponyvas-oldalfal-profilok-es-szegok.webp (1200 × 840)
Használat: python3 scripts/oldalfal_csoportkep.py <szego_row.png>
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 840


def profile_row(path):
    src = Image.open(path).convert("RGBA")
    ys, xs = np.where(np.array(src)[..., 3] > 40)
    src = src.crop((xs.min() - 10, ys.min() - 10, xs.max() + 10, ys.max() + 10))
    rgb, al = src.convert("RGB"), src.split()[3]
    # lágy, matt hatás (a Quadris mintafotója szerint): a tárgy átlagos tónusa ~185, a felső lapok sem égnek ki
    a = np.array(rgb).astype(np.float32)
    obj = np.array(al) > 128
    gam = np.log(185 / 255) / np.log(max(a[obj].mean(), 1) / 255)
    rgb = Image.fromarray((255 * (a / 255) ** gam).clip(0, 255).astype(np.uint8))
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    a = np.array(rgb).astype(np.float32)
    e = cv2.Canny(cv2.GaussianBlur(a.astype(np.uint8), (0, 0), 0.9), 35, 100).astype(np.float32) / 255
    e = np.maximum(e, cv2.Canny((np.array(al) > 128).astype(np.uint8) * 255, 50, 150).astype(np.float32) / 255)
    a = a * (1 - 0.22 * cv2.GaussianBlur(e, (0, 0), 0.6)[..., None])  # vékony sötét kontúr, mint a katalógusképen
    row = Image.fromarray(a.clip(0, 255).astype(np.uint8)).filter(ImageFilter.UnsharpMask(1.0, 40, 2)).convert("RGBA")
    row.putalpha(al)
    return row


def side_walls():
    top = Image.open(ROOT / "data/forras/oldalfal_katalogus.png").convert("RGB")
    t = np.array(ImageEnhance.Contrast(top).enhance(1.1)).astype(np.float32)
    obj = (np.array(top).min(2) < 244)[..., None]
    t = np.where(obj, t + np.array([-2, 0, 3], np.float32), 255)  # enyhe hideg fémes tónus, mint a renderen
    top = Image.fromarray(t.clip(0, 255).astype(np.uint8)).filter(ImageFilter.UnsharpMask(1.2, 60, 2))
    m = (np.array(top).min(2) < 246).astype(np.float32)
    w = m.shape[1]
    m = cv2.GaussianBlur(m, (0, 0), 1.0) * np.clip((w - np.arange(w)) / (w * 0.12), 0, 1)[None, :]
    out = top.convert("RGBA")
    out.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
    return out


def match_colors(row, walls):
    """A profilsor színe és tónusa az oldalfalakéhoz igazítva (Lab-színtérben átlag és szórás szerint)."""
    def lab(img):
        return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    ra, wa = np.array(row)[..., 3] > 128, np.array(walls)[..., 3] > 128
    rl, wl = lab(row), lab(walls)
    out = rl.copy()
    for c in range(3):
        rm, rs = rl[..., c][ra].mean(), rl[..., c][ra].std() + 1e-3
        wm, ws = wl[..., c][wa].mean(), wl[..., c][wa].std()
        out[..., c] = (rl[..., c] - rm) / rs * ws + wm
    rgb = cv2.cvtColor(out.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
    res = Image.fromarray(rgb).convert("RGBA")
    res.putalpha(row.split()[3])
    return res


def main():
    row, walls = profile_row(sys.argv[1]), side_walls()
    row = match_colors(row, walls)
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    th, rh, gap = 470, 330, 14
    tw = round(walls.width * th / walls.height)
    canvas.alpha_composite(walls.resize((tw, th), Image.LANCZOS), ((W - tw) // 2, 8))
    rw = min(W - 40, round(row.width * rh / row.height))
    rh = round(row.height * rw / row.width)
    canvas.alpha_composite(row.resize((rw, rh), Image.LANCZOS), ((W - rw) // 2, 8 + th + gap))
    canvas.convert("RGB").save(ROOT / "public/csoportkepek/ponyvas-oldalfal-profilok-es-szegok.webp", "WEBP", quality=88, method=6)


if __name__ == "__main__":
    main()
