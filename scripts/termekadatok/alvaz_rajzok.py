"""Alumínium alváz profilok: egységes keresztmetszet-rajzok (etalon: 207315 „I” 108 kereszttartó).

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
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ENRICHMENT, ROOT  # noqa: E402

W, H, MARGIN = 1200, 840, 50
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
    "202388-15-70-mm-keretprofil-elox-cd": ("keret-profilok", 100),
    "203004-30-mm-keretprofil-elox": ("keret-profilok", 124.5),
    "207318-keret-profil-90-18mm-elox": ("keret-profilok", 117.5),
    "203183-250-25-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 250),
    "206941-cd-100x30-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 100),
    "207833-100x30-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 100),
    "208477-cd2-100x30-mm-alafutasgatlo-elox-profil": ("alafutasgatlo-profilok", 100),
    "205535-ives-alafutasgatlo-vegzaro-elox-profil": ("egyedi", None),  # ívelt végzáró, nem keresztmetszet
    "201094-targonca-utkozo-profil": ("targonca-utkozo", 37.5),
}
# szkennelt rajzok megszakított falvonalai: (x0, y0, x1, y1, vastagság) a forráskép képpontjaiban
REPAIR = {
    "202387-i-70-kereszttarto": [(523, 150, 523, 530, 5), (566, 150, 566, 530, 5)],  # a gerinc törésjele
    "202388-15-70-mm-keretprofil-elox-cd": [(165, 300, 166, 700, 4), (196, 300, 198, 700, 4),  # a hosszú szár törésjele
                                            (665, 317, 978, 319, 4)],  # a vízszintes szár szakadozott felső vonala
}
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


def normalize(rgb, thick=0.03):
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
        if r < thick * size and area / max(r, 1) ** 2 > 10:
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
    else:
        prof = size
    return out.astype(np.uint8), prof


def ink_crop(g, pad=12):
    ys, xs = np.where(g < 235)
    return g[max(ys.min() - pad, 0): ys.max() + pad, max(xs.min() - pad, 0): xs.max() + pad]


def source_image(entry):
    for u in entry.get("images", []):
        if "/3d/" not in u and not u.endswith("-rajz.webp"):
            return u
    return None


def main():
    data = json.loads(ENRICHMENT.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    items = {}
    for slug, (cat, mm) in PROFILES.items():
        e = data.get(slug)
        src = source_image(e or {})
        if not src:
            print("  nincs rajz:", slug)
            continue
        keep = CACHE / f"{slug}.png"
        if not keep.exists():
            Image.open(ROOT / "public" / src.lstrip("/")).save(keep)
        rgb = load(keep)
        for x0, y0, x1, y1, t in REPAIR.get(slug, []):
            cv2.line(rgb, (x0, y0), (x1, y1), (0, 0, 0), t)
        g, prof = normalize(rgb, THICK.get(slug, 0.03))
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
        f = min((W - 2 * MARGIN) / g.shape[1], (H - 2 * MARGIN) / g.shape[0]) if mm is None else scale[cat] * mm / prof
        img = Image.fromarray(g).resize((max(1, round(g.shape[1] * f)), max(1, round(g.shape[0] * f))), Image.LANCZOS)
        canvas = Image.new("L", (W, H), 255)
        canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
        rel = f"/termekkepek/{slug}-rajz.webp"
        canvas.convert("RGB").save(ROOT / "public" / rel.lstrip("/"), "WEBP", quality=90)
        e = data[slug]
        e["images"] = [rel] + [u for u in e["images"] if u != rel]
    ENRICHMENT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"alváz profilok: {len(items)} egységes rajz;", ", ".join(f"{c}: {v:.2f} px/mm" for c, v in scale.items()))


if __name__ == "__main__":
    main()
