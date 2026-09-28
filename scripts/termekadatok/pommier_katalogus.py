"""Pommier / Furgocar (FR) – kiegészítés a hivatalos Pommier nyomtatott katalógusból
(POMMIER_Catalogue_DE-EN_2023-24_BD_0.pdf, https://www.pommier.eu/sites/default/files/catalogs/,
a letöltött példány a gitignore-olt .cache/ mappában – kb. 60 MB, ezért nincs a data/forras/ alatt).

Csak azokat a Pommier / Pommier Furgocar termékeket egészíti ki, amelyeknek a pommier.eu webes
feldolgozásából (pommier.py) nem jutott kép. A párosítás a katalógus referenciaszáma alapján:
  - 1636731DR/GA „Lezáró csiga zsanérhoz”: a katalógusban az 1636731-es alu zsanérprofilhoz
    („Für / For 1636731”) tartozó szürke műanyag zsanérvég 1636765DR (jobbos) / 1636765GA (balos),
    a DR/GA a jobb/bal változat – ez az egyetlen 1636731-hez tartozó jobb/bal alkatrész (329. oldal).
  - 70/90 mm-es gumi tömítés PFG (kód nélkül): a testvértermék 50/70-es tömítése 580611207, a
    katalógus ugyanebben a sorozatban a 70–90 mm-es panelhez a 580611208-at adja (523. oldal);
    a Quadris-kód (511208) vége is egyezik.
Nincs a katalógusban: 22.21.88168 (alsó rámpa indító profil), 1703150 (ütközőgumi 310×35×60).

A kép a katalógusból kézzel kijelölt, szorosan vágott termékfotó / méretezett rajz (PDF pontban
megadott kivágás, 240 dpi, fehér szél levágva). Az oldalszám a PDF oldalszáma (a nyomtatott +2).

Használat: python3 scripts/termekadatok/pommier_katalogus.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Pommier katalógus"
SUPPLIERS = ["Pommier", "Pommier Furgocar"]
URL = "https://www.pommier.eu/sites/default/files/catalogs/POMMIER_Catalogue_DE-EN_2023-24_BD_0.pdf"
PDF = ROOT / ".cache/pommier_katalog_2023-24.pdf"
ITEMS = {  # slug -> (Pommier referencia, cím, PDF-oldal, [kivágások pt-ben], műszaki adatok)
    "106731-lezaro-csiga-zsanerhoz": (
        "1636765DR/GA", "Hinge stop, gray plastic (for 1636731 / 1636761)", 331,
        [(88, 110, 155, 222)],
        {"Pommier cikkszám": "1636765DR (jobbos) / 1636765GA (balos)", "Anyag": "szürke műanyag",
         "Tömeg [kg]": "0,035", "Illeszkedik": "1636731 / 1636761 alu zsanérprofilhoz"}),
    "511208-70-90-mm-es-gumi-tomites-pfg": (
        "580611208", "Gasket in 20 m rolls for panel width from 70 to 90 mm", 525,
        [(306, 328, 462, 446)],
        {"Pommier cikkszám": "580611208", "Anyag": "EPDM gumi", "Panelvastagság [mm]": "70–90",
         "Méret": "45 × 80 mm (teljes magasság 92 mm)", "Tömeg [kg]": "0,647", "Kiszerelés": "20 m-es tekercs",
         "Rögzítőprofil": "741209031 alumínium", "Hézag [mm]": "16/18"}),
}


def render(page, box):
    zoom = 240 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    g = np.asarray(img.convert("L")) < 225
    ys, xs = np.where(g)
    return img.crop((max(xs.min() - 16, 0), max(ys.min() - 16, 0), min(xs.max() + 16, img.width), min(ys.max() + 16, img.height)))


def main():
    if not PDF.exists():
        PDF.parent.mkdir(parents=True, exist_ok=True)
        PDF.write_bytes(fetch(URL, cache=False, timeout=300))
    doc = pymupdf.open(PDF)
    current = load_enrichment()
    enrichment, skipped = {}, []
    for supplier in SUPPLIERS:
        for p in load_products(supplier):
            item = ITEMS.get(p["slug"])
            if not item:
                continue
            old = current.get(p["slug"], {})
            if old.get("images") and old.get("source") != SOURCE:
                skipped.append((p, f"már van képe ({old.get('source')})"))
                continue
            ref, title, pno, boxes, specs = item
            clear_images(p["slug"])
            images = [save_image(render(doc[pno - 1], box), p["slug"], n) for n, box in enumerate(boxes, start=1)]
            enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": f"{URL}#page={pno}", "sourceTitle": f"Pommier katalógus 2023–24, {pno - 2}. o.: {title}",
                                     "matchedCode": ref, "specs": specs, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék kiegészítve")
    for p, why in skipped:
        print(f"  KIHAGYVA: {p['slug']} – {why}")


if __name__ == "__main__":
    main()
