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
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import alvaz_rajzok as A  # noqa: E402
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
# slug -> (szélesség felirat, magasság felirat, falvastagság felirat,
#          a falméret helye: ("h", y-arány) = vízszintes méret a bal oldali falon át az adott magasságban,
#                             ("v", x-arány) = függőleges méret az alsó falon át az adott vízszintes helyen,
#          törlendő maradványok a profil-maszkon [(x0, y0, x1, y1) arányban],
#          [opcionális: a szélesség mérete csak a felső sávé (a magasság ennyi része) – pl. kinyúló kar nélkül])
ITEMS = {
    "2018652-18-mm-keretprofil-erositett-elox": ("40", "126,5", "3", ("h", 0.72), [], 0.12),  # a 40 a felső részé
    "206941-cd-100x30-mm-alafutasgatlo-elox-profil": ("30,3", "100", "1,9", ("h", 0.80), []),
    "207833-100x30-mm-alafutasgatlo-elox-profil": ("100", "30", None, ("v", 0.25), []),
    "6612225-elso-oszlop-90-70-alu-elox-d": ("90", "70", "3", ("h", 0.20), [(0.968, 0.0, 1.0, 1.0)]),
    "6612226-hatso-oszlop-128-35-alu-elox-d": ("128", "35", "3", ("v", 0.80), []),
}


# a gyári lap kis, sraffozott keresztmetszet-vázlatából (data/forras/…): slug -> (vázlat, szélesség, magasság,
# falvastagság, a falméret helye)
SKETCH = {
    "2018290-18-mm-keretprofil-elox": ("data/forras/bodega_50042_vazlat.png", "68", "135,5", "2,4", ("h", 0.55),
                                       [(120, 231, 162, 236), (169, 231, 190, 236), (127, 236, 134, 292), (146, 320, 158, 347)]),
}


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


def render_mask(m, wtext, htext, ttext, where, erase=(), wtop=None, target=1000):
    H0, W0 = m.shape
    for fx0, fy0, fx1, fy1 in erase:
        m[int(fy0 * H0):int(fy1 * H0), int(fx0 * W0):int(fx1 * W0)] = False
        ys, xs = np.where(m)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        H0, W0 = m.shape
    k = target / max(H0, W0)
    big = cv2.resize(m.astype(np.uint8) * 255, (round(W0 * k), round(H0 * k)), interpolation=cv2.INTER_LINEAR) > 127
    cnts, hier = cv2.findContours(big.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = [cv2.approxPolyDP(c, 1.2, True) for c in cnts]
    ML, MT, MR, MB = 170, 170, 150, 150
    h, w = big.shape
    canvas = np.full((h + MT + MB, w + ML + MR, 3), 255, np.uint8)
    shifted = [p + np.array([[ML, MT]]) for p in polys]
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
    # szélesség: felül
    yd = y0 - 75
    d.line([(x0, y0 - 10), (x0, yd - 16)], fill="black", width=2)
    d.line([(xw, y0 - 10), (xw, yd - 16)], fill="black", width=2)
    dim((x0, yd), (xw, yd))
    d.text(((x0 + xw) / 2, yd - 8), wtext, font=F, fill="black", anchor="mb")
    # magasság: balra
    xd = x0 - 85
    d.line([(x0 - 10, y0), (xd - 16, y0)], fill="black", width=2)
    d.line([(x0 - 10, y1), (xd - 16, y1)], fill="black", width=2)
    dim((xd, y0), (xd, y1))
    t = Image.new("RGBA", (220, 60), (255, 255, 255, 0))
    ImageDraw.Draw(t).text((110, 30), htext, font=F, fill="black", anchor="mm")
    t = t.rotate(90, expand=True)
    img.paste(t, (int(xd - 48), int((y0 + y1) / 2 - t.height / 2)), t)
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
    for slug, (src, wt, ht, tt, where, wipe) in SKETCH.items():
        data.setdefault(slug, {"source": "Quadris gyári rajz", "sourceUrl": "", "specs": {}, "images": []})
        img, *_ = render_mask(sketch_mask(src, wipe=wipe), wt, ht, tt, where)
        url = save_image(img, slug, "meretrajz")
        data[slug]["images"] = [url] + [u for u in data[slug].get("images", []) if u != url]
        data[slug].setdefault("specs", {})["Falvastagság"] = f"{tt} mm"
        print(slug, "vázlatból")
    update_enrichment({s: data[s] for s in list(ITEMS) + list(SKETCH) if s in data})


if __name__ == "__main__":
    main()
