"""Metra (IT) – felépítmény-profilok a Metra "Profilati per trasporti" katalógusából
(data/forras/metra_katalog_fahrzeugbau.pdf – a Quadris-tól kapott gyári katalógus).

A profillapok vektoros rajzok, a cikkszámok is görbékként vannak rajta (nem kereshető szöveg),
ezért a termékek helyét és adatait a lapokról olvastuk le, a kivágásokat kézzel ellenőriztük.
Minden kép egyetlen profil keresztmetszete a méreteivel és a Metra-jelölésével.

Használat: python3 scripts/termekadatok/metra.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Metra"
PDF = ROOT / "data/forras/metra_katalog_fahrzeugbau.pdf"

# Quadris Excel-kód -> (Metra jelölés, PDF oldal, kivágás [pt], műszaki adatok a lapról)
ITEMS = {
    "R6830": ("R 6830", 21, (110, 135, 250, 690), {"Tömeg": "3,213 kg/fm", "Magasság": "300 mm", "Vastagság": "25 mm",
                                                   "Látható felület": "343 mm", "Kerület": "745 mm", "Kivitel": "monoprofil oldalfal 300 mm"}),
    "R7784": ("R 7784", 22, (305, 125, 420, 720), {"Tömeg": "3,308 kg/fm", "Magasság": "350 mm", "Vastagság": "25 mm",
                                                   "Látható felület": "396 mm", "Kerület": "849 mm", "Kivitel": "monoprofil oldalfal 350 mm, szakállas"}),
    "3367": ("R 3367", 24, (190, 90, 310, 755), {"Tömeg": "4,209 kg/fm", "Magasság": "400 mm", "Vastagság": "25 mm",
                                                 "Látható felület": "449 mm", "Kerület": "947 mm", "Kivitel": "monoprofil oldalfal 400 mm, peremes"}),
    "B0326": ("B 326", 19, (70, 85, 262, 322), {"Tömeg": "0,729 kg/fm", "Belső szélesség": "25,5 mm", "Magasság": "40 mm",
                                                "Kivitel": "U-szegő (végprofil) 25 mm-es oldalfalhoz"}),
    "R1304": ("R 1304", 29, (28, 58, 128, 292), {"Tömeg": "0,700 kg/fm", "Méret": "25 × 50 mm", "Látható felület": "150 mm",
                                                 "Kerület": "150 mm", "Kivitel": "zártszelvény (ponyvatartó)"}),
}
COMMON = {"Ötvözet": "EN AW-6060 / EN AW-6005A", "Állapot": "T5 – T6"}


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
        sigla, pno, box, specs = item
        clear_images(p["slug"])
        img = save_image(render(doc[pno - 1], box), p["slug"], 1)
        elox = "elox" in p["name"].lower()
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": "https://www.metraluminium.it", "sourceTitle": f"Metra {sigla}",
                                 "matchedCode": sigla, "specs": {**specs, **COMMON, "Felület": "eloxált" if elox else "natúr"},
                                 "images": [img]}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)} termék")
    for p in missing:
        print("  NINCS:", p["supplierCode"], p["name"])


if __name__ == "__main__":
    main()
