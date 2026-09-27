"""Versus-Omega (BE) – tolótető rendszerek és tetősínek.

A versus-omega.com-on rendszerenként (Micro Trike, Duo Trike Light, Pico …) van termékoldal:
leírás, tömeg, gyári hosszak, méretek, valamint a sín 3D-s képe és méretezett keresztmetszet-rajza.
Cikkszámonkénti oldal nincs, ezért csak azokat a tételeket párosítjuk, amelyek megnevezése
egyértelműen az adott rendszert (tetősín vagy teljes rendszer) nevezi meg; az apró alkatrészek
(lezárók, csavarkészletek, tömítések) így kimaradnak.

Használat: python3 scripts/termekadatok/versus.py
"""

import html
import io
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Versus"
BASE = "https://www.versus-omega.com"
IMG = BASE + "/assets/images/pictures/shop_product/s_c/800x600/"
# rendszer -> (termékoldal, minta a Quadris-megnevezésre)
SYSTEMS = {
    "micro-trike": ("/en/products/18/micro-trike", r"MICRO\s*TRIKE"),
    "duo-trike-light": ("/en/products/2/duo-trike-light", r"DUO\s*TRIKE\s*(L\b|Light)"),
    "pico": ("/en/products/20/pico", r"\bPICO\b"),
}
DESC = {
    "micro-trike": "Könnyű, kompakt tetősín kisebb teherbírású haszongépjárművekhez és kis pótkocsikhoz, a Trike tolótető-rendszer minden előnyével.",
    "duo-trike-light": "A szabványos Trike sín karcsúsított változata rövidebb, könnyebb járművekhez, legfeljebb 8500 mm hosszig.",
    "pico": "Tolótető-sín fix oldalfalú felépítményekhez: legfeljebb 40 mm vastag oldalfalra egyszerűen felszerelhető.",
}


def page_specs(t):
    txt = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", "", t, flags=re.S)))
    txt = re.sub(r"\s+", " ", txt)
    specs = {}
    m = re.search(r"Weight: ca\. ([\d.]+) kg/m", txt)
    if m:
        specs["Tömeg"] = f"kb. {m.group(1).replace('.', ',')} kg/fm"
    m = re.search(r"Available in lengths?: ([\d ,and()*]+?) mm", txt)
    if m:
        lens = re.findall(r"\d{4,5}", m.group(1))
        specs["Gyári hosszak [mm]"] = " / ".join(lens)
    m = re.search(r"Measurements: (\d+) mm high, (\d+) mm wide", txt)
    if m:
        specs["Magasság"] = f"{m.group(1)} mm"
        specs["Talpszélesség"] = f"{m.group(2)} mm"
    m = re.search(r"Width between the rails: (\d+) mm \(at standard width (\d+) mm\)", txt)
    if m:
        specs["Sínek közötti távolság"] = f"{m.group(1)} mm ({m.group(2)} mm felépítményszélességnél)"
    specs["Anyag"] = "extrudált alumínium"
    return specs


def trim_frame(img):
    """A méretrajz körüli szürke keret levágása, majd szoros vágás a rajzra."""
    a = np.asarray(img.convert("L"))
    white = a > 235
    rows, cols = np.where(white.mean(axis=1) > 0.5)[0], np.where(white.mean(axis=0) > 0.5)[0]
    if len(rows) and len(cols):
        img = img.crop((cols.min(), rows.min(), cols.max() + 1, rows.max() + 1))
        a = np.asarray(img.convert("L"))
    ys, xs = np.where(a < 200)
    pad = 16
    return img.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.width), min(ys.max() + pad, img.height)))


def main():
    pages = {}
    for key, (path, _) in SYSTEMS.items():
        t = fetch(BASE + path).decode("utf-8", "ignore")
        imgs = sorted(set(re.findall(r"/s_c/800x600/([^\"' )]+\.jpg)", t)), key=lambda n: n.startswith("bemating"))
        pages[key] = (path, page_specs(t), imgs)
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        key = next((k for k, (_, pat) in SYSTEMS.items() if re.search(pat, p["name"], re.I)), None)
        if not key:
            missing.append(p)
            continue
        path, specs, imgs = pages[key]
        specs = dict(specs)
        if key == "pico":  # a honlap szövege 47 mm-t ír, a gyári méretrajz 41 mm-t – a rajzot tekintjük mérvadónak
            specs.pop("Talpszélesség", None)
        m = re.search(r"/(\d{4,5})\s*mm", p["name"])
        if m:
            specs["Hossz"] = f"{m.group(1)} mm"
        clear_images(p["slug"])
        images = []
        for i, name in enumerate(imgs, 1):
            img = Image.open(io.BytesIO(fetch(IMG + name)))
            if name.startswith("bemating"):
                img = trim_frame(img)
            images.append(save_image(img, p["slug"], i))
        system = "Tolótető rendszer" in p["name"]
        desc = DESC[key] + (" A rendszer a tetősíneket és a hozzájuk tartozó szerelvényeket tartalmazza." if system else "")
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": BASE + path, "sourceTitle": key, "matchedCode": key,
                                 "description": desc, "specs": specs, "images": images}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
