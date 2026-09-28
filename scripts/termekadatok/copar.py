"""Co.Par. (IT) – műanyag szerszámosládák (Mini Box, Nova Box).

Forrás: a gyártó típuslapjai (data/forras/copar_mini_box_35.jpg, copar_nova_box.jpg – a Quadris-tól kapott
képek): termékfotó, méretrajz és táblázat (kód, L × D × H, anyag, tömeg, űrtartalom).
A Quadris-kód megegyezik a Co.Par. kóddal (pl. ICBEB20000N0 = NOVA BOX 50).

Használat: python3 scripts/termekadatok/copar.py
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "COPAR"
SRC = ROOT / "data/forras"
COMMON = {"Anyag": "polipropilén (PP), fröccsöntött", "Üzemi hőmérséklet": "−45 °C … +60 °C",
          "Megfelelőség": "ECE R73.01 oldalsó aláfutásgátló (Co.Par. tartókkal)"}
# kód -> (típus, forráskép, fotó kivágás [px], rajz kivágás [px], műszaki adatok)
ITEMS = {
    "ICAEA12000N0": ("MINI BOX 35", "copar_mini_box_35.jpg", (215, 24, 485, 160), (200, 468, 492, 620),
                     {"Méret (hossz × mélység × magasság)": "350 × 350 × 350 mm", "Tömeg": "2,2 kg", "Űrtartalom": "26 l",
                      "Tartó": "FSUM4AXXN7 oldalsó tartó (315 × 5 mm)"}),
    "ICBEB20000N0": ("NOVA BOX 50", "copar_nova_box.jpg", (200, 24, 500, 160), (138, 384, 432, 520),
                     {"Méret (hossz × mélység × magasság)": "500 × 400 × 350 mm", "Tömeg": "3,2 kg", "Űrtartalom": "42 l",
                      "Tartó": "FSUM4AXXN7 oldalsó tartó"}),
}


def trim(img, pad=12):
    g = np.asarray(img.convert("L")) < 200
    ys, xs = np.where(g)
    return img.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.width), min(ys.max() + pad, img.height)))


def main():
    enrichment, missing = {}, []
    for p in load_products(SUPPLIER):
        item = ITEMS.get((p["supplierCode"] or "").strip().upper())
        if not item:
            missing.append(p)
            continue
        name, src, photo, drawing, specs = item
        sheet = Image.open(SRC / src).convert("RGB")
        clear_images(p["slug"])
        images = [save_image(sheet.crop(photo), p["slug"], 1), save_image(trim(sheet.crop(drawing)), p["slug"], 2)]
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": "https://www.copar.it", "sourceTitle": f"Co.Par. {name}",
                                 "matchedCode": p["supplierCode"], "specs": {"Típus": name, **specs, **COMMON}, "images": images}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)} termék")
    for p in missing:
        print("  NINCS:", p["supplierCode"], p["name"])


if __name__ == "__main__":
    main()
