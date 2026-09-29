"""Alumínium alváz és padló profilok: egységes keresztmetszet-rajzok (etalon: 207315 „I” 108 kereszttartó).

A beszállítói rajzok (Constellium, Exlabesa, Ital Accessori, Alu-SV, ESAL, BODEGA, RE-ALL, nevbol.py …)
stílusa vegyes: körvonalas, szürkével vagy kékkel kitöltött, szkennelt. Ez a szkript mindegyiket az etalon
stílusára hozza:
  * a profil fala tömör fekete (a zárt, vékony falrészek kitöltése – a nagy üregek fehérek maradnak;
    a szkennelt rajzok megszakított (töréssel ábrázolt) falvonalait előbb meghosszabbítjuk, így zárt a körvonal),
  * szürkeárnyalatos, fehér hátterű rajz, a méretvonalak és méretszámok megmaradnak,
  * egységes 1200 × 840-es vászon, középre igazítva,
  * méretarányosan: egy alkategórián belül minden profil ugyanazzal a mm → képpont aránnyal jelenik meg
    (a legnagyobb profil tölti ki a vásznat), így a képeken a profilok egymáshoz mért nagysága valós.
A kész rajz a termék első képe lesz (<slug>-rajz.webp); a 3D képek utána következnek.

Használat: python3 scripts/termekadatok/alvaz_rajzok.py
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import ENRICHMENT, ROOT  # noqa: E402
from profil_vektor import VECTOR, rasterize  # noqa: E402

W, H, MARGIN = 1200, 840, 50
CLEAN_SECOND = {}
# slug -> (alkategória, a profil legnagyobb befoglaló mérete mm-ben – a rajz méretszámai alapján)
PROFILES = {
    "202274-u-100x50x50x5-mm-profil": ("hossztartok", 100),
    "202386-u-130-hossztarto": ("hossztartok", 130),
    "202850-u-130-hossztarto-k": ("hossztartok", 130),
    "202869-u-160x80x80x8-mm-profil": ("hossztartok", 160),
    "203432-u-90x50x50x5-mm-profil": ("hossztartok", 90),
    "203548-u-140x60x60x7-mm-profil": ("hossztartok", 140),
    "205162-u-80x60x5-mm-aluprofil": ("hossztartok", 80),
    "207316-u-90-hossztarto": ("hossztartok", 90),
    "207317-u-108-hossztarto": ("hossztartok", 108),
    "207327-tl-110-60-60-hossztarto-ex": ("hossztartok", 110),
    "209695-u-110-60-hossztarto-duplanutolt-ex": ("hossztartok", 110),
    "200392-i-90-60-kereszttarto-ex": ("kereszttartok", 90),
    "202387-i-70-kereszttarto": ("kereszttartok", 70),
    "207315-i-108-kereszttarto": ("kereszttartok", 108),
    "207319-i-90-kereszttarto": ("kereszttartok", 90),
    "2073902-i-90-csavarozhato-kereszttarto": ("kereszttartok", 90),
    "206441-i-gerenda-profil-80x60-50x8-6-mm": ("kereszttartok", 80),
    "2018652-18-mm-keretprofil-erositett-elox": ("keret-profilok", 126.5),
    "202388-15-70-mm-keretprofil-elox-cd": ("keret-profilok", 109),
    "203004-30-mm-keretprofil-elox": ("keret-profilok", 124.5),
    "207318-keret-profil-90-18mm-elox": ("keret-profilok", 117.5),
    "203183-250-25-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 250),
    "206941-cd-100x30-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 100),
    "207833-100x30-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 100),
    "208477-cd2-100x30-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 100),
    "205535-ives-alafutasgatlo-vegzaro-elox-profil": ("alafutasgatlo-profilok", 100),  # Metra R 7297
    "201094-targonca-utkozo-profil": ("targonca-utkozo", 37.5),
    # Alumínium padló profilok (a kulcs első tagja az alkategória, a lépték alkategóriánként közös)
    "221902-bordazott-padlo-profil-200-40-mm": ("padlo-profilok", 200),
    "226001-zart-padlo-profil-30-200-mm": ("padlo-profilok", 200),  # ESAL 11258
    "227543-30-padlo-profil-200-mm": ("padlo-profilok", 200),
    "227543-30-padlo-profil-200-mm-elox": ("padlo-profilok", 200),
    "222233-rampa-szego-g-profil": ("rampa-profilok", 80),
    "203492-autoszallito-padlo-keret-profil-30-mm": ("autoszallito-profilok", 130),
    "207776-30-padlo-profil-220-mm-ex": ("autoszallito-profilok", 233.5),
}
# szkennelt rajzok megszakított falvonalai: (x0, y0, x1, y1, vastagság) a forráskép képpontjaiban
REPAIR = {
    "202387-i-70-kereszttarto": [(523, 150, 523, 530, 5), (566, 150, 566, 530, 5)],  # a gerinc törésjele
    "202388-15-70-mm-keretprofil-elox-cd": [(165, 300, 166, 1218, 4), (196, 300, 198, 1218, 4),  # a hosszú szár (nyújtás után)
                                            (665, 317, 978, 319, 4)],  # a vízszintes szár szakadozott felső vonala
}
# méretezés nélküli forrásrajzok: a fő befoglaló méretek (szélesség, magasság) felrajzolása – a profil
# befoglalója a forrásképen (x0, y0, x1, y1) és a méretszámok; 203183: ESAL 13183 „Parabici da 250 mm”, 250 × 25
DIMS = {"203183-250-25-mm-alafutasgatlo-elox-profil": ((26, 119, 974, 214), "250", "25")}
# régi segédvonalas szkennelt rajzok tisztán újrarajzolva a gyártói méretekből (profil_vektor.py) és a fő
# méretek; mindkét kép (tömör és körvonalas) így készül. (szélesség mm, magasság mm, a szélesség csak a felső részé)
CLEAN = {"202388-15-70-mm-keretprofil-elox-cd": ("40", "109", 40)}
# apró, olvashatatlan méretezésű rajzok: csak a profil marad meg (a régi méretvonalak nélkül), és az etalon
# stílusában új fő méretek kerülnek rá: (szélesség mm, magasság mm)
# (szélesség, magasság, a szélesség-méret jobb végének távolsága a profil jobb szélétől mm-ben)
REDIM = {"227543-30-padlo-profil-200-mm": ("200", "30", 5), "227543-30-padlo-profil-200-mm-elox": ("200", "30", 5),
         "226001-zart-padlo-profil-30-200-mm": ("200", "30", 15)}
# Constellium rajzok: a forrás a constellium.py profilkiválasztása (csak a profil körvonala, a méretek nélkül)
CONSTELLIUM = {"227543-30-padlo-profil-200-mm": "7543", "227543-30-padlo-profil-200-mm-elox": "7543"}
# törésvonallal rövidítve rajzolt profilok valós arányra nyújtása: (sor, beszúrt sorok száma) – a beszúrt
# sorok a megadott sor másolatai; 202388: a [40] szélesség 498 px (12,45 px/mm), így a [109] magasság 1357 px
STRETCH = {"202388-15-70-mm-keretprofil-elox-cd": (620, 518)}
# a gerincbe lógó régi méretszám törlése (fehérrel), mielőtt a falvonalakat meghúzzuk: (x0, y0, x1, y1)
ERASE = {"202387-i-70-kereszttarto": [(498, 222, 590, 256)],
         # 206941: a jobb fal mélyítése mellett futó felesleges vonal, a bal fal és a horony kívülre lógó jelölései
         "206941-cd-100x30-mm-alafutasgatlo-elox-profil": [(273, 372, 282, 500), (8, 480, 27, 510), (133, 598, 150, 616),
                                                           (138, 226, 186, 237), (248, 226, 272, 237)]}  # + a bordázat fölötti körjelölés
# a falrészeket apró jelölések darabolják, ezért itt minden vékony zárt rész kitöltendő (a számjegyek belseje nincs benne)
FILL_ALL = {"206941-cd-100x30-mm-alafutasgatlo-elox-profil": (20, 230, 285, 990)}  # a profil területe (x0, y0, x1, y1)
# a kitöltés által eltakart méretszámok újraírása: (szöveg, x, y közép) a forráskép képpontjaiban
LABELS = {
    "202387-i-70-kereszttarto": [("[50]", 700, 245)],  # eredetileg a gerincen belül állt
}
# az etalon (eredeti) rajz marad: a méretaránynál számít, de nem készül belőle új kép
KEEP_ORIGINAL = {"207315-i-108-kereszttarto"}
CACHE = ROOT / ".cache" / "alvaz_rajzok"  # a forrásrajzok másolata (a kimenet külön fájl, de biztos, ami biztos)


def load(path):
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        img = bg
    return np.asarray(img.convert("RGB")).astype(np.float32)


# a nagyobb felbontású szkennelt rajzok vastagabb falúak (képpontban) – itt nagyobb falvastagságig töltünk
THICK = {"202387-i-70-kereszttarto": 0.05, "202388-15-70-mm-keretprofil-elox-cd": 0.05}


def normalize(rgb, thick=0.03, fill_all=None):
    """Szürkeárnyalatos, tömör fekete falú rajz + a profil (vastag részek) befoglaló mérete képpontban."""
    L = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    ink = (L < 170) | ((sat > 60) & (L < 235))  # vonal vagy színes kitöltés
    ys, xs = np.where(ink)
    size = max(xs.max() - xs.min(), ys.max() - ys.min())
    # zárt fehér/világos területek: a vékonyak (profilfal) kitöltendők, a nagyok (üreg, méretvonal-keret) nem
    if thick > 0.03:  # szkennelt rajz: az 1–2 képpontos szakadások bezárása
        ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
    free = (~ink).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(free, connectivity=4)
    dist = cv2.distanceTransform(free, cv2.DIST_L2, 3)
    fill = np.zeros_like(ink)
    h, w = ink.shape
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if x == 0 or y == 0 or x + bw >= w or y + bh >= h:
            continue  # a háttér
        comp = lab == i
        r = dist[comp].max()
        inside = fill_all and fill_all[0] <= x and x + bw <= fill_all[2] and fill_all[1] <= y and y + bh <= fill_all[3]
        if r < thick * size and (area / max(r, 1) ** 2 > 10 or (inside and area > 8)):
            fill |= comp
    out = L.copy()
    out = np.clip((out - 40) * 255 / (215 - 40), 0, 255)  # világos szürke háttér -> fehér, vonalak sötétebbre
    out[fill] = 0
    out[ink & (sat > 60)] = np.minimum(out[ink & (sat > 60)], 60)  # színes (kék) kitöltés/vonal -> sötét
    solid = ((out < 110).astype(np.uint8))
    k = max(3, int(size * 0.008) | 1)
    body = cv2.morphologyEx(solid, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(body, connectivity=8)
    if n > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        keep = [i + 1 for i, a in enumerate(areas) if a >= 0.2 * areas.max()]
        x0 = min(stats[i, 0] for i in keep)
        y0 = min(stats[i, 1] for i in keep)
        x1 = max(stats[i, 0] + stats[i, 2] for i in keep)
        y1 = max(stats[i, 1] + stats[i, 3] for i in keep)
        prof = max(x1 - x0, y1 - y0)
        out = straighten(out, np.isin(lab, keep), size)
    else:
        prof = size
    return out.astype(np.uint8), prof


def polygonize(mask, eps):
    """A profil (maszk) körvonalai egyenes szakaszokból álló sokszögként (Douglas–Peucker, eps képpont tűrés):
    a recés, szkennelt élek helyett precíz egyenesek; az ívek sűrű töréspontokkal maradnak simák."""
    cnts, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    return [cv2.approxPolyDP(c, eps, True) for c in cnts], hier


def straighten(out, core, size):
    """A profilfalak újrarajzolása precíz, élsimított sokszögként. A falhoz tartozó sötét terület: a tömör
    részek, amelyek a profil fő részével összefüggnek (a vékony méretvonalak – 1–2 px – nem)."""
    solid = (out < 110).astype(np.uint8)
    thick = cv2.morphologyEx(solid, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    n, lab = cv2.connectedComponents(thick, connectivity=8)
    ids = np.unique(lab[core & (thick > 0)])
    mask = np.isin(lab, ids[ids > 0])
    eps = max(0.8, size / 1000)  # kis tűrés: az egyenesek kiegyenesednek, az ívek simák maradnak
    polys, hier = polygonize(mask, eps)
    res = out.astype(np.float32).copy()
    res[cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0] = 255
    canvas = np.full(out.shape, 255, np.uint8)
    cv2.drawContours(canvas, polys, -1, 0, thickness=cv2.FILLED, lineType=cv2.LINE_AA, hierarchy=hier)
    return np.minimum(res, canvas)


def add_dims(rgb, box, wtext, htext, wspan=None, top=False, fsize=46, lw=2, wx=None):
    """Etalon-stílusú méretvonalak nyilakkal: szélesség a profil alatt (top: fölött; wspan: csak a profil egy
    részének szélessége, képpontban), magasság a profil bal oldalán."""
    pad = int(max(160, fsize * 3.5))
    img = Image.fromarray(rgb.astype(np.uint8)).convert("RGB")
    canvas = Image.new("RGB", (img.width + 2 * pad, img.height + 2 * pad), "white")
    canvas.paste(img, (pad, pad))
    d = ImageDraw.Draw(canvas)
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", fsize)
    x0, y0, x1, y1 = (v + pad for v in box)
    col, a = (0, 0, 0), 16 * fsize / 46
    off = 70 * fsize / 46

    def arrow(p, q):  # nyílhegy p-ben, q felé mutató vonal irányából
        vx, vy = q[0] - p[0], q[1] - p[1]
        n = (vx * vx + vy * vy) ** 0.5 or 1
        ux, uy = vx / n, vy / n
        d.polygon([p, (p[0] + ux * a - uy * a / 3, p[1] + uy * a + ux * a / 3), (p[0] + ux * a + uy * a / 3, p[1] + uy * a - ux * a / 3)], fill=col)

    wx0 = x0 if wx is None else wx[0] + pad
    wx1 = (wx[1] + pad) if wx is not None else (x0 + wspan if wspan else x1)
    edge, yd = (y0, y0 - off) if top else (y1, y1 + off)  # szélesség
    sgn = -1 if top else 1
    d.line([(wx0, edge + 8 * sgn), (wx0, yd + 14 * sgn)], fill=col, width=lw)
    d.line([(wx1, edge + 8 * sgn), (wx1, yd + 14 * sgn)], fill=col, width=lw)
    d.line([(wx0, yd), (wx1, yd)], fill=col, width=lw)
    arrow((wx0, yd), (wx1, yd)); arrow((wx1, yd), (wx0, yd))
    d.text(((wx0 + wx1) / 2, yd - 8), wtext, fill=col, font=fnt, anchor="mb")
    xd = x0 - off  # magasság
    d.line([(x0 - 8, y0), (xd - 14, y0)], fill=col, width=lw)
    d.line([(x0 - 8, y1), (xd - 14, y1)], fill=col, width=lw)
    d.line([(xd, y0), (xd, y1)], fill=col, width=lw)
    arrow((xd, y0), (xd, y1)); arrow((xd, y1), (xd, y0))
    t = Image.new("L", (int(fsize * 4), int(fsize * 1.5)), 0)
    ImageDraw.Draw(t).text((t.width / 2, t.height / 2), htext, fill=255, font=fnt, anchor="mm")
    t = t.rotate(90, expand=True)
    canvas.paste(Image.new("RGB", t.size, col), (int(xd - t.width - 6), int((y0 + y1) / 2 - t.height / 2)), t)
    return np.asarray(canvas).astype(np.float32)


def ink_crop(g, pad=12):
    ys, xs = np.where(g < 235)
    return g[max(ys.min() - pad, 0): ys.max() + pad, max(xs.min() - pad, 0): xs.max() + pad]


def source_image(entry, slug=""):
    for u in entry.get("images", []):
        if "/3d/" not in u and not u.endswith(("-rajz.webp", "-korvonal.webp")):
            return u
    # a CLEAN rajzoknál az eredeti szkennelt rajz már nincs a képek között, de a fájl megvan
    orig = f"/termekkepek/{slug}-1.webp"
    return orig if (ROOT / "public" / orig.lstrip("/")).exists() else None


def main():
    data = json.loads(ENRICHMENT.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    items = {}
    CLEAN_SECOND.clear()
    for slug, (cat, mm) in PROFILES.items():
        e = data.get(slug)
        src = source_image(e or {}, slug)
        if not src:
            print("  nincs rajz:", slug)
            continue
        keep = CACHE / f"{slug}.png"
        if slug in CONSTELLIUM and not keep.exists():
            import constellium
            cfg = constellium.DRAWINGS[CONSTELLIUM[slug]]
            saved = {k: cfg.pop(k) for k in ("keep", "draw") if k in cfg}  # méretek nélkül
            try:
                constellium.render(CONSTELLIUM[slug]).save(keep)
            finally:
                cfg.update(saved)
        if not keep.exists():
            Image.open(ROOT / "public" / src.lstrip("/")).save(keep)
        rgb = load(keep)
        if slug in DIMS:
            rgb = add_dims(rgb, *DIMS[slug])
        if slug in STRETCH:
            y, n = STRETCH[slug]
            rgb = np.concatenate([rgb[:y], np.repeat(rgb[y:y + 1], n, axis=0), rgb[y:]], axis=0)
        for x0, y0, x1, y1 in ERASE.get(slug, []):
            rgb[y0:y1, x0:x1] = 255
            if slug.startswith("202387"):
                rgb[257:260, x0:x1] = 0  # a méretvonal folytatása a törölt szám alatt (a 202387 méretvonala a 258. sorban)
        for x0, y0, x1, y1, t in REPAIR.get(slug, []):
            cv2.line(rgb, (x0, y0), (x1, y1), (0, 0, 0), t)
        g, prof = normalize(rgb, THICK.get(slug, 0.03), FILL_ALL.get(slug))
        if slug in LABELS:
            im = Image.fromarray(g)
            d = ImageDraw.Draw(im)
            fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
            for text, x, y in LABELS[slug]:
                d.text((x, y), text, fill=0, font=fnt, anchor="mb")
            g = np.asarray(im)
        if slug in CLEAN:
            wt, ht, wmm = CLEAN[slug]
            ppm = 12.0
            # vektoros szerkesztés a gyártói méretek alapján (profil_vektor.py): precíz egyenesek és ívek
            geom = VECTOR[slug]()
            body, _ = rasterize(geom, ppm, 2)
            polys, hier = polygonize(body, 0.6)
            gx0, gy0, _, _ = geom.bounds
            box = (int((0 - gx0 + 2) * ppm), int((0 - gy0 + 2) * ppm), int((wmm - gx0 + 2) * ppm), int((float(ht) - gy0 + 2) * ppm))
            g = np.full(body.shape, 255, np.uint8)
            base = np.full(g.shape + (3,), 255, np.float32)
            filled = base.copy()
            cv2.drawContours(filled, polys, -1, (0, 0, 0), thickness=cv2.FILLED, lineType=cv2.LINE_AA, hierarchy=hier)
            outline = base.copy()
            cv2.drawContours(outline, polys, -1, (0, 0, 0), max(3, int(ppm / 2.5)), lineType=cv2.LINE_AA)
            fs, lw = int(ppm * 7), max(2, int(ppm / 3))
            g = add_dims(filled, box, wt, ht, wmm * ppm, top=True, fsize=fs, lw=lw).mean(axis=2).astype(np.uint8)
            second = add_dims(outline, box, wt, ht, wmm * ppm, top=True, fsize=fs, lw=lw).mean(axis=2).astype(np.uint8)
            prof = float(ht) * ppm
            CLEAN_SECOND[slug] = ink_crop(second)
        if slug in REDIM:
            wt, ht, roff = REDIM[slug]
            solid = (g < 110).astype(np.uint8)
            # a vékony méret- és segédvonalak (2–3 px) nyitással eltűnnek, a 2,5 mm-es falak (≈18 px) maradnak
            body = cv2.morphologyEx(solid, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
            n, lab, st, _ = cv2.connectedComponentsWithStats(body, connectivity=8)
            body = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            ys, xs = np.where(body)
            box = (xs.min(), ys.min(), xs.max(), ys.max())
            ppm = (ys.max() - ys.min()) / float(ht)
            polys, hier = polygonize(body, 0.8)
            base = np.full(g.shape + (3,), 255, np.float32)
            cv2.drawContours(base, polys, -1, (0, 0, 0), thickness=cv2.FILLED, lineType=cv2.LINE_AA, hierarchy=hier)
            wx = (box[2] - (roff + float(wt)) * ppm, box[2] - roff * ppm)  # a 200-as méret a padló felső lapjáé
            g = add_dims(base, box, wt, ht, fsize=int(ppm * 7), lw=max(2, int(ppm / 3)), wx=wx).mean(axis=2).astype(np.uint8)
            prof = max(box[2] - box[0], box[3] - box[1]) + 0.0
        g = ink_crop(g)
        items[slug] = (cat, mm, g, prof)
    # alkategóriánként közös arány: px / mm = a legszűkebb (a vászonra épp ráférő) érték
    scale = {}
    for slug, (cat, mm, g, prof) in items.items():
        if mm is None:
            continue
        fit = min((W - 2 * MARGIN) / g.shape[1], (H - 2 * MARGIN) / g.shape[0])  # a rajz nagyítása, ha kitölti
        ppm = fit * prof / mm  # ennél a nagyításnál ennyi képpont jut 1 mm-re
        scale[cat] = min(scale.get(cat, 1e9), ppm)
    for slug, (cat, mm, g, prof) in items.items():
        if slug in KEEP_ORIGINAL:
            rel = f"/termekkepek/{slug}-rajz.webp"
            (ROOT / "public" / rel.lstrip("/")).unlink(missing_ok=True)
            data[slug]["images"] = [u for u in data[slug]["images"] if u != rel]
            continue
        f = min((W - 2 * MARGIN) / g.shape[1], (H - 2 * MARGIN) / g.shape[0]) if mm is None else scale[cat] * mm / prof
        img = Image.fromarray(g).resize((max(1, round(g.shape[1] * f)), max(1, round(g.shape[0] * f))), Image.LANCZOS)
        canvas = Image.new("L", (W, H), 255)
        canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
        rel = f"/termekkepek/{slug}-rajz.webp"
        if slug in CLEAN_SECOND:  # a második (körvonalas) kép ugyanazzal a nagyítással, az eredeti szkennelt rajz helyett
            s2 = CLEAN_SECOND[slug]
            im2 = Image.fromarray(s2).resize((max(1, round(s2.shape[1] * f)), max(1, round(s2.shape[0] * f))), Image.LANCZOS)
            c2 = Image.new("L", (W, H), 255)
            c2.paste(im2, ((W - im2.width) // 2, (H - im2.height) // 2))
            rel2 = f"/termekkepek/{slug}-korvonal.webp"
            c2.convert("RGB").save(ROOT / "public" / rel2.lstrip("/"), "WEBP", quality=90)
            data[slug]["images"] = [rel, rel2]
        canvas.convert("RGB").save(ROOT / "public" / rel.lstrip("/"), "WEBP", quality=90)
        e = data[slug]
        e["images"] = [rel] + [u for u in e["images"] if u != rel]
    ENRICHMENT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"alváz profilok: {len(items)} egységes rajz;", ", ".join(f"{c}: {v:.2f} px/mm" for c, v in scale.items()))


if __name__ == "__main__":
    main()
