"""Franz Miederhoff GmbH & Co. KG (DE) – a Sarolta-féle „Direktspanner” a Miederhoff 2026-os főkatalógusából
(https://www.miederhoff.de/wp-content/uploads/2026/09/Mi-HK_2026_Basis_24_DE_screen_kompr.pdf – a .cache/ mappába töltődik le).

A megrendelő „niederhoff honlapján keresd” megjegyzése a Miederhoffra vonatkozik (a niederhoff.de nem elérhető /
nem kapcsolódik; a „Direktspanner 2000®” ponyvafeszítő a Miederhoff terméke, shop.miederhoff.de).
A katalógusban két változat van, azonos méretekkel (L 160 × B 60 × H 21 mm, rozsdamentes acél):
31.0048.20 (35 mm állítási út) és 31.0448.20 (25 mm állítási út, 10 kN, CURTSEC-tanúsított).
A Quadris-tételnél nincs kód, ezért mindkét cikkszámot feltüntetjük, és csak a közös adatokat adjuk meg.
Kép: a katalógus vonalas rajza (a webes fotók vízjelesek). Kézzel ellenőrizve.

Használat: python3 scripts/termekadatok/miederhoff.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import CACHE, clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Miederhoff"
URL = "https://www.miederhoff.de/wp-content/uploads/2026/09/Mi-HK_2026_Basis_24_DE_screen_kompr.pdf"
PAGE_URL = "https://shop.miederhoff.de/de/produkte/side_curtain_zubehoer/direktspanner/"
# slug -> (cikkszám(ok), oldal, kivágás [pt], műszaki adatok)
ITEMS = {
    "383148-direktspanner": ("31.0048.20 / 31.0448.20", 104, (30, 105, 105, 255),
        {"Megnevezés (gyári)": "Direktspanner 2000® – direkt ponyvafeszítő (csúszóponyvás rendszerhez)",
         "Változatok": "31.0048.20: 35 mm állítási út; 31.0448.20: 25 mm állítási út, 10 kN terhelhetőség (CURTSEC-tanúsított)",
         "Anyag": "rozsdamentes acél", "Méret": "160 × 60 × 21 mm (H × Sz × M)", "Furatátmérő": "7,0 mm",
         "Furattávolság": "28 mm"}),
}


def render(page, box):
    zoom = 300 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ys, xs = np.where(np.asarray(img.convert("L")) < 235)
    return img.crop((max(xs.min() - 16, 0), max(ys.min() - 16, 0), min(xs.max() + 16, img.width), min(ys.max() + 16, img.height)))


def main():
    pdf = CACHE / "miederhoff_katalog_2026.pdf"
    if not pdf.exists():
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(fetch(URL, cache=False, timeout=600))
    doc = pymupdf.open(pdf)
    existing = load_enrichment()
    enrichment = {}
    for p in load_products():
        item = ITEMS.get(p["slug"])
        other = existing.get(p["slug"], {})
        if not item or (other.get("images") and other.get("source") != SOURCE):
            continue
        ref, pno, box, specs = item
        clear_images(p["slug"])
        images = [save_image(render(doc[pno - 1], box), p["slug"])]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": PAGE_URL, "sourceTitle": f"Miederhoff Direktspanner 2000® ({ref})",
                                 "matchedCode": ref, "specs": {"Cikkszám (gyártói)": ref, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
