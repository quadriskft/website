"""Bodega (IT) – oldalfal-profilok a Bodega "Bordwände" katalógusából
(data/forras/bodega_bordwaendekatalog_30.pdf, 03/2010 – a Quadris-tól kapott gyári katalógus).

A katalógus a 2010-es kódokat tartalmazza; az Excel Bodega-kódjai közül csak ezek szerepelnek benne.
A rajz a profil saját keresztmetszete a méretekkel (kivágás kézzel ellenőrizve), a tömeg a rajz alól.

Használat: python3 scripts/termekadatok/bodega.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "BODEGA"
PDF = ROOT / "data/forras/bodega_bordwaendekatalog_30.pdf"
ITEMS = {  # kód -> (oldal, kivágás [pt], műszaki adatok)
    "TB25549": (7, (145, 95, 252, 785), {"Tömeg": "4,116 kg/fm", "Magasság": "400 mm", "Vastagság": "25 mm", "Kivitel": "peremes oldalfal-profil"}),
    "TB28153": (10, (50, 520, 178, 745), {"Tömeg": "0,724 kg/fm", "Belső szélesség": "29,5 mm", "Magasság": "40 mm", "Kivitel": "U-szegő 25 mm-es oldalfalhoz"}),
    "TB27833": (15, (42, 505, 367, 680), {"Tömeg": "1,246 kg/fm", "Méret": "100 × 30 mm", "Kivitel": "aláfutásgátló profil"}),
}


def render(page, box):
    zoom = 240 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    g = np.asarray(img.convert("L")) < 225
    ys, xs = np.where(g)
    return img.crop((max(xs.min() - 16, 0), max(ys.min() - 16, 0), min(xs.max() + 16, img.width), min(ys.max() + 16, img.height)))


def main():
    doc = pymupdf.open(PDF)
    enrichment, missing = {}, []
    for p in load_products(SUPPLIER):
        item = ITEMS.get((p["supplierCode"] or "").replace(" ", "").upper())
        if not item:
            missing.append(p)
            continue
        pno, box, specs = item
        clear_images(p["slug"])
        elox = "elox" in p["name"].lower()
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": "https://www.bodega.it", "sourceTitle": f"Bodega {p['supplierCode']}",
                                 "matchedCode": p["supplierCode"], "specs": {**specs, "Felület": "eloxált" if elox else "natúr"},
                                 "images": [save_image(render(doc[pno - 1], box), p["slug"], 1)]}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)} termék a katalógusból, {len(missing)} nincs benne")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>10}  {p['name']}")


if __name__ == "__main__":
    main()
