"""Dost Teknik (TR) – oldalponyvás felépítmények görgői, rakonca-kocsik.

Forrás: a gyártó 2024-es katalógusa (dostteknik.com, szkennelt PDF: data/forras/dost_catalog_2024.pdf).
Minden tételnél a termékfotó és a méretezett rajz külön cellában áll – ezeket a cella határán vágjuk ki.
Csak azokat a tételeket párosítjuk, amelyek cikkszáma a katalógusban szerepel.

Használat: python3 scripts/termekadatok/dost.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Dost"
PDF = Path(__file__).resolve().parents[2] / "data/forras/dost_catalog_2024.pdf"
URL = "https://dostteknik.com/wp-content/uploads/dost-catalog-2024.pdf"
# Quadris kód -> (katalóguskód, oldal, fotó-cella, rajz-cella [pt], műszaki adatok)
ITEMS = {
    "401115": ("401115", 8, (218, 312, 377, 468), (405, 310, 556, 466),
               {"Kivitel": "hajlított tartólemezes ponyvagörgő", "Méretek": "38 × 113 mm", "Rögzítés": "2 × Ø7,2 mm furat, 28,5 mm osztás",
                "Anyag": "horganyzott acél"}),
    "401410": ("401410", 10, (218, 640, 377, 798), (392, 634, 576, 804),
               {"Kivitel": "rakonca-görgő acél sínhez, hajlított", "Méretek": "246 × 240 mm", "Görgőtávolság": "200 mm"}),
}


def cell(page, rect):
    pix = page.get_pixmap(clip=pymupdf.Rect(rect), dpi=250, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    g = np.asarray(img.convert("L"))
    ys, xs = np.where(g < 235)
    if len(xs) < 50:
        return img
    pad = 10
    return img.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.width), min(ys.max() + pad, img.height)))


def main():
    doc = pymupdf.open(PDF)
    enrichment = {}
    products = load_products(SUPPLIER)
    for p in products:
        it = ITEMS.get((p["supplierCode"] or "").strip())
        if not it:
            continue
        code, pno, photo, drawing, specs = it
        clear_images(p["slug"])
        images = [save_image(cell(doc[pno], photo), p["slug"], 1), save_image(cell(doc[pno], drawing), p["slug"], 2)]
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": URL, "sourceTitle": f"Dost {code}", "matchedCode": code,
                                 "specs": specs, "images": images}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in products:
        if p["slug"] not in enrichment:
            print(f"  NINCS: {p['supplierCode'] or '-':>14}  {p['name']}")


if __name__ == "__main__":
    main()
