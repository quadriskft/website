"""Profilpol System – rámpaprofilok a „Katalog 2025” katalógusból (data/forras/profilpolsystem_katalog_2025.pdf).
A lapok profilonként egy fotót, egy méretezett keresztmetszet-rajzot és egy adattáblát tartalmaznak, ezért a
kivágás kézzel rögzített (pt-ban, a PDF oldalkoordinátáiban).

A Quadris kérésére: 220192 (alsó rámpa indító profil) = 22.21.88168, 220190 (rámpa felső záró profil) = 22.21.0679.

Használat: python3 scripts/termekadatok/profilpol.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Profilpol katalógus"
PDF = ROOT / "data/forras/profilpolsystem_katalog_2025.pdf"
URL = "https://profilpolsystem.pl/wp-content/uploads/2026/02/Katalog-2025_Profilpolsystem.pdf"
# slug -> (Profilpol kód, oldal, rajz kivágás [pt], fotó kivágás [pt], adatok)
ITEMS = {
    "220192-also-rampa-indito-profil": ("22.21.88168", 121, (428, 228, 526, 274), (300, 140, 440, 232),
        {"Megnevezés (gyári)": "Profil najazdowy zakończeniowy 120 – rámpa indító (felhajtó) záróprofil",
         "Szélesség": "120 mm", "Magasság": "30 mm", "Tömeg": "2,11 kg/fm", "Szálhossz": "4,5 m",
         "Anyag": "alumínium"}),
    "220190-rampa-felso-zaro-profil-225-30-mm": ("22.21.0679", 138, (300, 360, 504, 406), (15, 315, 234, 465),
        {"Megnevezés (gyári)": "Profil trapu zakończeniowy – rámpa záróprofil",
         "Szélesség": "225 mm", "Magasság": "30 mm", "Tömeg": "6,468 kg/fm", "Szálhossz": "5 m",
         "Anyag": "alumínium"}),
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
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": f"{URL}#page={pno}", "sourceTitle": f"Profilpol {code}",
                                 "matchedCode": code, "specs": {"Cikkszám (gyártói)": code, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
