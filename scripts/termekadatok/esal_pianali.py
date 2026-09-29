"""ESAL (Forlì) – padlóprofilok (Pianali) a „Catalogo Sponde 2020” katalógus képes oldalairól
(data/forras/esal_sponde_2020.pdf). Ezek a lapok nem táblázatosak (esal.py), hanem profilonként egy fotó és
egy méretezett keresztmetszet-rajz, alatta a kód és az adatok – ezért a kivágás kézzel rögzített.

A Quadris kérésére: 226001 (zárt padló profil 30/200 mm) = ESAL 11258 „Pianale da 30 mm rigato scatolato”.

Használat: python3 scripts/termekadatok/esal_pianali.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "ESAL padlóprofil"
PDF = ROOT / "data/forras/esal_sponde_2020.pdf"
URL = "https://esalforli.com/public/Catalogo-Sponde-2020-Esal-Forli.pdf"
# slug -> (ESAL kód, oldal, rajz kivágás [pt], fotó kivágás [pt], adatok)
ITEMS = {
    "226001-zart-padlo-profil-30-200-mm": ("11258", 69, (165, 250, 424, 318), (128, 76, 476, 214),
        {"Megnevezés (gyári)": "Pianale da 30 mm rigato scatolato – zárt (dobozos), bordázott padlóprofil",
         "Szélesség": "200 mm", "Magasság": "30 mm", "Tömeg": "3,870 kg/fm", "Szálhossz": "7,5 m",
         "Anyag": "alumínium EN AW-6060 T5"}),
}


def render(page, box, dpi=400):
    zoom = dpi / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ys, xs = np.where(np.asarray(img.convert("L")) < 235)
    return img.crop((max(xs.min() - 16, 0), max(ys.min() - 16, 0), min(xs.max() + 16, img.width), min(ys.max() + 16, img.height)))


def main():
    doc = pymupdf.open(PDF)
    enrichment = {}
    for p in load_products():
        if p["slug"] not in ITEMS:
            continue
        code, pno, dbox, pbox, specs = ITEMS[p["slug"]]
        clear_images(p["slug"])
        page = doc[pno - 1]
        images = [save_image(render(page, dbox), p["slug"], 1), save_image(render(page, pbox, 200), p["slug"], 2)]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": f"{URL}#page={pno}", "sourceTitle": f"ESAL {code}",
                                 "matchedCode": code, "specs": {"Cikkszám (gyártói)": code, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
