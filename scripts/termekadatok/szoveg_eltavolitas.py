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
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
MIN_GLYPHS = 6
KEEP_DRAWING = __import__("os").environ.get("RAJZSZURO", "1") == "1"


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


def ocr_words(img):
    """Tesseract szófelismerés (ha telepítve van): [(x0, y0, x1, y1, szöveg, bizonyosság)]."""
    import shutil
    import subprocess
    import tempfile
    if not shutil.which("tesseract"):
        return []
    scale = 3 if max(img.size) < 900 else 2 if max(img.size) < 1600 else 1
    big = img.convert("L").resize((img.width * scale, img.height * scale), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        big.save(tmp.name)
        out = subprocess.run(["tesseract", tmp.name, "stdout", "-l", "eng", "--psm", "11", "tsv"], capture_output=True, text=True).stdout
    words = []
    for line in out.splitlines()[1:]:
        c = line.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        x, y, w, h, conf = int(c[6]) / scale, int(c[7]) / scale, int(c[8]) / scale, int(c[9]) / scale, float(c[10])
        words.append((x, y, x + w, y + h, c[11].strip(), conf))
    return words


def is_text_word(w):
    """Felirat-e a szó: legalább 3 betű (olasz/angol szöveg, név, bevonat), vagy hosszú cikkszám.
    A méretek (30, Ø15, M8, R5, 2x, 10 mm) megmaradnak."""
    t, conf = w[4], w[5]
    letters = len(re.findall(r"[A-Za-zÀ-ÿ]", t))
    if conf < 40:
        return False
    if re.fullmatch(r"\d+(?:[.,]\d+)?\s*kg", t, re.I) or t.lower() in ("kg", "pcs", "pcs.", "art", "art."):
        return True
    if letters >= 3 and not re.fullmatch(r"\d+(?:[.,]\d+)?mm", t, re.I):
        return True
    return bool(re.fullmatch(r"(?:art\.?)?\d{6,}(?:/\w+)?", t, re.I))


def ocr_clean(img):
    """A felismert feliratszavak kifehérítése (csak fehér/világos háttér előtt)."""
    rgb = np.asarray(img.convert("RGB")).copy()
    gray = np.asarray(img.convert("L"))
    h, w = gray.shape
    hit = np.zeros(gray.shape, bool)
    for x0, y0, x1, y1, t, conf in [x for x in ocr_words(img) if is_text_word(x)]:
        wh = y1 - y0
        if wh > h * 0.12 or (x1 - x0) > w * 0.9:  # túl nagy "szó" – valószínűleg rajzrészlet
            continue
        p = max(2, int(wh * 0.25))
        X0, Y0, X1, Y1 = int(max(x0 - p, 0)), int(max(y0 - p, 0)), int(min(x1 + p, w)), int(min(y1 + p, h))
        ring = np.concatenate([gray[Y0, X0:X1], gray[Y1 - 1, X0:X1], gray[Y0:Y1, X0], gray[Y0:Y1, X1 - 1]])
        if ring.size and (np.median(ring) < 235 or (ring < 150).mean() > 0.12):  # nem tiszta fehér háttéren – a terméken van, marad
            continue
        inner = gray[Y0:Y1, X0:X1]
        if (inner < 120).mean() > 0.45:  # tömör sötét folt, nem szöveg
            continue
        if (inner > 242).mean() < 0.5:  # a felirat hátterének tisztán fehérnek kell lennie (render felülete nem az)
            continue
        rgb[Y0:Y1, X0:X1] = 255
        hit[Y0:Y1, X0:X1] = True
    return Image.fromarray(rgb), hit


def keep_drawing(rgb):
    """Rajzon csak a rajzhoz tartozó tartalmat tartjuk meg: a nagy összefüggő vonalas elemek (termék körvonala,
    méretvonalak) és a közvetlen környezetük (méretszámok) maradnak, a különálló szövegblokkok, címkék törlődnek."""
    gray = np.asarray(Image.fromarray(rgb).convert("L"))
    h, w = gray.shape
    dark = gray < 200
    lab, n = ndimage.label(dark, structure=np.ones((3, 3)))
    if n == 0:
        return rgb, None
    objs = ndimage.find_objects(lab)
    big = np.zeros(n + 1, bool)
    for i, sl in enumerate(objs):
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) >= 0.08 * max(h, w):
            big[i + 1] = True
    if not big.any():
        return rgb, None
    r = max(6, int(0.016 * max(h, w)))
    grown = ndimage.binary_dilation(dark, structure=np.ones((3, 3)), iterations=r)
    cl, _ = ndimage.label(grown)
    keep_ids = np.unique(cl[big[lab]])
    keep = np.isin(cl, keep_ids[keep_ids > 0])
    faint = gray < 242  # a világosszürke feliratok is
    drop = faint & ~keep
    # csak betű/ikon méretű elemet törlünk – nagyobb, különálló rajzrészlet (pl. oldalnézet) marad
    flab, fn = ndimage.label(drop, structure=np.ones((3, 3)))
    if fn:
        limit = 0.05 * max(h, w)
        sizes = np.zeros(fn + 1, bool)
        for i, sl in enumerate(ndimage.find_objects(flab)):
            sizes[i + 1] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) <= limit
        drop = sizes[flab] & drop
    if drop.sum() < 20:
        return rgb, None
    out = rgb.copy()
    gone = ndimage.binary_dilation(drop, iterations=2) & ~keep
    out[gone] = 255
    return out, gone


def grey_labels(rgb):
    """Kis, egyszínű világosszürke címkedobozok (pl. „Capacità utile / Capacity load”) maszkja."""
    gray = np.asarray(Image.fromarray(rgb).convert("L")).astype(int)
    h, w = gray.shape
    m = (gray > 185) & (gray < 238)
    lab, n = ndimage.label(m)
    out = np.zeros(m.shape, bool)
    for i, sl in enumerate(ndimage.find_objects(lab)):
        bh, bw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if bh < 8 or bw < 20 or bh > 0.09 * h or bw > 0.35 * w:
            continue
        own = lab[sl] == i + 1
        y0, y1, x0, x1 = max(sl[0].start - 6, 0), min(sl[0].stop + 6, h), max(sl[1].start - 6, 0), min(sl[1].stop + 6, w)
        ring = np.concatenate([gray[y0, x0:x1], gray[y1 - 1, x0:x1], gray[y0:y1, x0], gray[y0:y1, x1 - 1]])
        if np.median(ring) < 245:  # a címkedoboz fehér háttéren áll – terméken (pl. furat belseje) nem
            continue
        if own.mean() > 0.55 and gray[sl][own].std() < 7:
            out[max(sl[0].start - 3, 0):sl[0].stop + 3, max(sl[1].start - 3, 0):sl[1].stop + 3] = True
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
    photo = (gray < 90).mean() > 0.06 or ((hsv[..., 1] > 90) & (hsv[..., 2] > 60)).mean() > 0.04
    # fotón/renderen a szövegsor-felismerés (betűláncok) nem fut, csak a rajz-szűrés és az OCR
    m = np.zeros(gray.shape, bool) if photo else (text_mask(gray) | colour_labels(rgb))
    if m.any():
        rgb[ndimage.binary_dilation(m, iterations=1)] = 255
    removed = ndimage.binary_dilation(m, iterations=1) if m.any() else np.zeros(gray.shape, bool)
    lbl = grey_labels(rgb)
    if lbl.any():
        rgb[lbl] = 255
        removed |= lbl
    rgb, gone = keep_drawing(rgb) if KEEP_DRAWING else (rgb, None)
    if gone is not None:
        removed |= gone
    out, hits = ocr_clean(Image.fromarray(rgb))
    removed |= hits
    if not removed.any():
        return img, False
    # a törölt feliratok halvány (élsimított) maradványai
    arr = np.asarray(out).copy()
    near = ndimage.binary_dilation(removed, iterations=4)
    arr[near & (np.asarray(out.convert("L")) > 170)] = 255
    out = Image.fromarray(arr)
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
    only = None
    if "--csak" in args:
        only = set(args[args.index("--csak") + 1].split(","))
        args = args[: args.index("--csak")]
    suppliers = set(args)
    data = json.loads((ROOT / "src/data/termekadatok.json").read_text())
    changed = 0
    for slug, e in data.items():
        if e.get("source") not in suppliers:
            continue
        for rel in e.get("images") or []:
            f = ROOT / "public" / rel.lstrip("/")
            if not f.exists() or (only and f.stem not in only):
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
