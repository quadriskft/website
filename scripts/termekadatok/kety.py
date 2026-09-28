"""Grupa Kęty (PL) – profilok a gyártó saját profilrajzáról
(data/forras/kety_w2850.pdf – a W2850 profil gyári műszaki rajza, a Quadris-tól kapott másolat).

A rajz vektoros; a kivágás a méretezett (bal oldali) keresztmetszet, a jobb oldali 1:1 kontúr és
a rajzi szövegmező nélkül. A tömeg, kerület és ötvözet a rajz szövegmezőjéből (Masa, Obwód, Materiał).

Használat: python3 scripts/termekadatok/kety.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Grupa Kęty"
# Quadris-kód -> (PDF, oldal, kivágás [pt], műszaki adatok a rajzról)
ITEMS = {
    "W2850": (ROOT / "data/forras/kety_w2850.pdf", 1, (66, 100, 325, 543),
              {"Tömeg": "3,44 kg/fm", "Magasság": "130 mm", "Szélesség": "50 mm", "Falvastagság": "5 / 6 mm",
               "Kerület": "444 mm", "Ötvözet": "EN AW-6005A T6", "Tűrés": "EN 755-9", "Kivitel": "U-profil (hossztartó)"}),
}


def render(page, box):
    zoom = 240 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    g = np.asarray(img.convert("L")) < 225
    ys, xs = np.where(g)
    return img.crop((max(xs.min() - 16, 0), max(ys.min() - 16, 0), min(xs.max() + 16, img.width), min(ys.max() + 16, img.height)))


def main():
    enrichment, missing = {}, []
    for p in load_products(SUPPLIER):
        code = (p["supplierCode"] or "").replace(" ", "").upper()
        item = ITEMS.get(code)
        if not item:
            missing.append(p)
            continue
        pdf, pno, box, specs = item
        clear_images(p["slug"])
        elox = "elox" in p["name"].lower()
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": "https://www.grupakety.com", "sourceTitle": f"Grupa Kęty profilrajz {code}",
                                 "matchedCode": code, "specs": {**specs, "Felület": "eloxált" if elox else "natúr"},
                                 "images": [save_image(render(pymupdf.open(pdf)[pno - 1], box), p["slug"], 1)]}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)} termék, {len(missing)} nincs rajz")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>10}  {p['name']}")


if __name__ == "__main__":
    main()
