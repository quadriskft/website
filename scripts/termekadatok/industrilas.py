"""Industrilås (SE) – 68-S1 süllyesztett T-karos zár.

Forrás: a gyártó termékképe (data/forras/industrilas_68-s1.png – a Quadris-tól kapott kép).
A Quadris-kód végén a típusjel (pl. 272063-68-S1), mindkét változat ugyanaz a zártípus.

Használat: python3 scripts/termekadatok/industrilas.py
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Industrilas"
IMG = ROOT / "data/forras/industrilas_68-s1.png"
SPECS = {"Típus": "Industrilås 68-S1", "Kivitel": "süllyesztett (felületbe építhető) T-karos zár, kulccsal zárható",
         "Szín": "fekete ház, krómozott fogantyú"}


def main():
    enrichment, missing = {}, []
    for p in load_products(SUPPLIER):
        code = (p["supplierCode"] or "").upper()
        if not code.endswith("68-S1"):
            missing.append(p)
            continue
        clear_images(p["slug"])
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": "https://industrilas.com", "sourceTitle": "Industrilås 68-S1",
                                 "matchedCode": code, "specs": dict(SPECS), "images": [save_image(Image.open(IMG), p["slug"], 1)]}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)} termék")
    for p in missing:
        print("  NINCS:", p["supplierCode"], p["name"])


if __name__ == "__main__":
    main()
