"""Feliratok eltávolítása a termékképekről – csak a termék és a méretek maradjanak.

A beszállítói rajzokon a termék neve, cikkszáma, tömege, darabszáma stb. szövegsorokban áll.
A felismerés: a sötét pixelek összefüggő foltjai közül a "betű méretűek" (kicsi, közel álló,
hasonló magasságú foltok) sorokba rendeződnek. Egy sor akkor felirat, ha legalább MIN_GLYPHS
betűből áll – a méretszámok (pl. "30", "Ø15", "M5", "185") ennél rövidebbek, így megmaradnak.
A színes címkéket (pl. sárga "Maniglia zincata" doboz) és a piros "Dx-R / Sx-L" jelöléseket is
eltávolítjuk. Végül a képet a megmaradt tartalomra vágjuk, kis margóval.

Használat: python3 scripts/termekadatok/szoveg_eltavolitas.py FTS [más beszállító ...] [--proba kimenet_mappa]
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
MIN_GLYPHS = 6


def text_mask(gray):
    """Visszaadja a feliratnak ítélt pixelek maszkját."""
    h, w = gray.shape
    dark = gray < 200
    lab, n = ndimage.label(dark, structure=np.ones((3, 3)))
    if n == 0:
        return np.zeros_like(dark)
    objs = ndimage.find_objects(lab)
    sizes = ndimage.sum(dark, lab, index=np.arange(1, n + 1))
    scale = max(h, w)
    gmin, gmax = 3, max(10, scale * 0.035)  # betűmagasság tartomány
    glyphs = []
    for i, sl in enumerate(objs):
        gh, gw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if not (gmin <= gh <= gmax and sizes[i] >= 3):
            continue
        if gw <= gh * 2.2:
            glyphs.append((sl[0].start, sl[0].stop, sl[1].start, sl[1].stop, i + 1, 1))
        elif gw <= gh * 18 and sizes[i] / (gh * gw) < 0.55 and \
                ((dark[sl] & (lab[sl] == i + 1)).sum(axis=1) >= 0.15 * gw).sum() >= 0.4 * gh:
            # egybefolyó betűkből álló szó (dőlt, apró betű): kitöltése ritka, betűszáma a szélességből becsülve
            glyphs.append((sl[0].start, sl[0].stop, sl[1].start, sl[1].stop, i + 1, max(2, round(gw / (gh * 0.6)))))
    # sorokba rendezés: függőleges középpont közel, vízszintesen szomszédos (rés < 1,2 × betűmagasság)
    glyphs.sort(key=lambda g: (g[0] + g[1]) / 2)
    rows = []
    for g in glyphs:
        cy, gh = (g[0] + g[1]) / 2, g[1] - g[0]
        for r in rows:
            if abs(r["cy"] - cy) < max(r["h"], gh) * 0.45 and abs(r["h"] - gh) < max(r["h"], gh) * 0.6:
                r["items"].append(g)
                break
        else:
            rows.append({"cy": cy, "h": gh, "items": [g]})
    mask = np.zeros_like(dark)
    # csak akkor dolgozunk, ha a képen van valódi szövegsor (legalább 2 lánc, egyenként ≥ 8 külön betűvel)
    strong = 0
    for r in rows:
        its = sorted([g for g in r["items"] if g[5] == 1], key=lambda g: g[2])
        run = 1
        for a, b2 in zip(its, its[1:]):
            run = run + 1 if b2[2] - a[3] < r["h"] * 1.3 else 1
            if run == 8:
                strong += 1
    if strong < 2:
        return mask
    for r in rows:
        items = sorted(r["items"], key=lambda g: g[2])
        # vízszintes láncokra bontás
        chains, cur = [], [items[0]]
        for g in items[1:]:
            if g[2] - cur[-1][3] < r["h"] * 1.3:
                cur.append(g)
            else:
                chains.append(cur)
                cur = [g]
        chains.append(cur)
        letters = lambda ch: sum(g[5] for g in ch)  # noqa: E731
        long_chain = any(letters(ch) >= MIN_GLYPHS for ch in chains)
        for ch in chains:
            near = long_chain and len(ch) >= 2 and any(
                abs(ch[0][2] - o[-1][3]) < r["h"] * 4 or abs(o[0][2] - ch[-1][3]) < r["h"] * 4 for o in chains if letters(o) >= MIN_GLYPHS)
            if letters(ch) >= MIN_GLYPHS or near:
                for g in ch:
                    mask |= lab == g[4]
                # a lánc teljes sávja (ékezetek, pontok, aláhúzás nélkül)
                y0, y1 = min(g[0] for g in ch), max(g[1] for g in ch)
                x0, x1 = min(g[2] for g in ch), max(g[3] for g in ch)
                pad = int(r["h"] * 0.3)
                mask[max(y0 - pad, 0):y1 + pad, max(x0 - pad, 0):x1 + pad] |= dark[max(y0 - pad, 0):y1 + pad, max(x0 - pad, 0):x1 + pad]
    # üressé vált keretek (pl. "Capacità utile / Capacity load" doboz) eltávolítása
    if mask.any():
        mlab, _ = ndimage.label(mask)
        for i, sl in enumerate(objs):
            bh, bw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if bh * bw > 0.06 * h * w or bh < gmin * 2:
                continue
            inner = mask[sl].sum()
            own = (lab[sl] == i + 1).sum()
            if inner > 0 and own < (bh + bw) * 2 * 4 and inner > own * 0.3:
                mask[sl] |= lab[sl] == i + 1
    return mask


def colour_labels(rgb):
    """Élénk színű címkék (sárga dobozok, piros jelölések) maszkja."""
    r, g, b = [rgb[..., i].astype(int) for i in range(3)]
    yellow = (r > 200) & (g > 180) & (b < 120)
    m = yellow  # piros nem: a termékeken is lehet piros rész (pl. kupak)
    if m.sum() < 30:
        return np.zeros(m.shape, bool)
    lab, n = ndimage.label(m)
    out = np.zeros(m.shape, bool)
    for i, sl in enumerate(ndimage.find_objects(lab)):
        area = (lab[sl] == i + 1).sum()
        if area > 150:  # a címke + a benne lévő szöveg téglalapja
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            out[max(y0 - 3, 0):y1 + 3, max(x0 - 3, 0):x1 + 3] = True
    return out


def clean(img):
    rgb = np.asarray(img.convert("RGB")).copy()
    gray = np.asarray(img.convert("L"))
    # csak fehér hátterű rajzokon dolgozunk (fotókon, rendereken nincs felirat)
    border = np.concatenate([gray[0], gray[-1], gray[:, 0], gray[:, -1]])
    if np.median(border) < 230:
        return img, False
    # fotó / render (nagy sötét vagy színes felületek): nem nyúlunk hozzá
    hsv = np.asarray(img.convert("HSV"))
    if (gray < 90).mean() > 0.06 or ((hsv[..., 1] > 90) & (hsv[..., 2] > 60)).mean() > 0.04:
        return img, False
    m = text_mask(gray) | colour_labels(rgb)
    if not m.any():
        return img, False
    rgb[ndimage.binary_dilation(m, iterations=1)] = 255
    out = Image.fromarray(rgb)
    g = np.asarray(out.convert("L")) < 248
    ys, xs = np.where(g)
    if len(xs) < 50:
        return img, False
    pad = max(8, int(max(out.size) * 0.02))
    out = out.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, out.width), min(ys.max() + pad, out.height)))
    return out, True


def main():
    args = sys.argv[1:]
    probe = None
    if "--proba" in args:
        probe = Path(args[args.index("--proba") + 1])
        args = args[: args.index("--proba")]
        probe.mkdir(parents=True, exist_ok=True)
    suppliers = set(args)
    data = json.loads((ROOT / "src/data/termekadatok.json").read_text())
    changed = 0
    for slug, e in data.items():
        if e.get("source") not in suppliers:
            continue
        for rel in e.get("images") or []:
            f = ROOT / "public" / rel.lstrip("/")
            if not f.exists():
                continue
            img = Image.open(f)
            out, did = clean(img)
            if not did:
                continue
            changed += 1
            if probe:
                both = Image.new("RGB", (img.width + out.width + 20, max(img.height, out.height)), (210, 210, 210))
                both.paste(img.convert("RGB"), (0, 0))
                both.paste(out, (img.width + 20, 0))
                both.save(probe / f.name.replace(".webp", ".png"))
            else:
                out.save(f, "WEBP", quality=82, method=6)
    print(f"{changed} kép {'tisztítandó' if probe else 'megtisztítva'} ({', '.join(sorted(suppliers))})")


if __name__ == "__main__":
    main()
