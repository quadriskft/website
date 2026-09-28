"""Exlabesa (PL/ES) – profilok az Exlabesa lengyel standard katalógusából
(data/forras/exlabesa_pl_katalog_2023.pdf, "Katalog profile", 2023. december – a Quadris-tól kapott gyári katalógus).

A katalógus kereshető szövegű, minden profil saját keretes cellában van: "EXL-xxxxx" cím, a méretezett
keresztmetszet-rajz és alatta a tömeg (masa [kg/m]) és a kerület (obwód [mm]). A Quadris-kódok az
Exlabesa profilszámai (néha vezető nulla nélkül/vele), ezért csak pontos számegyezést fogadunk el.
A kivágások kézzel ellenőrzöttek: csak a profil rajza a méretekkel, a cella kerete és a táblázat nélkül.
A katalógusban nem szereplő kódok (pl. 29100, 05630, 06887) kimaradnak.

Használat: python3 scripts/termekadatok/exlabesa.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Exlabesa"
SUPPLIERS = ("Exlabesa PL", "Exlabesa ES")
PDF = ROOT / "data/forras/exlabesa_pl_katalog_2023.pdf"

# Exlabesa profilszám (vezető nullák nélkül) -> (PDF oldal, kivágás [pt], műszaki adatok a lapról)
ITEMS = {
    "37327": (23, (60, 98, 203, 180), {"Tömeg": "3,198 kg/fm", "Kerület": "447 mm", "Méret": "110 × 60 × 60 mm",
                                        "Falvastagság": "5 / 6 mm", "Kivitel": "TL hossztartó-profil"}),
    "39695": (23, (445, 276, 548, 418), {"Tömeg": "3,897 kg/fm", "Kerület": "548 mm", "Magasság": "110 mm",
                                          "Övszélesség": "60 mm", "Falvastagság": "5 / 5,2 / 6,2 mm", "Kivitel": "U hossztartó-profil, dupla nútos gerinccel"}),
    "50392": (23, (92, 497, 226, 690), {"Tömeg": "2,027 kg/fm", "Kerület": "462 mm", "Magasság": "90 mm",
                                         "Övszélesség": "60 mm", "Falvastagság": "3 mm", "Kivitel": "I kereszttartó-profil, alsó nútos övvel"}),
    "37776": (24, (52, 658, 282, 730), {"Tömeg": "3,378 kg/fm", "Kerület": "837 mm", "Hasznos szélesség": "220 mm",
                                         "Teljes szélesség": "233,5 mm", "Magasság": "30 mm", "Kivitel": "bordázott padlóprofil"}),
    "39604": (25, (104, 648, 512, 737), {"Tömeg": "6,363 kg/fm", "Kerület": "795 mm", "Szélesség": "257,5 mm",
                                          "Magasság": "35 mm", "Kivitel": "MAX oszlopprofil"}),
    "39692": (26, (144, 115, 450, 340), {"Tömeg": "5,987 kg/fm", "Kerület": "782 mm", "Magasság": "133,5 mm",
                                          "Szélesség": "175 mm", "Kivitel": "MAX oszlopprofil"}),
    "37712": (32, (386, 98, 468, 178), {"Tömeg": "1,104 kg/fm", "Kerület": "331 mm", "Szélesség": "60,2 mm",
                                         "Belső méret (U)": "25,1 mm", "Kivitel": "csigás zsanérprofil 25 mm-es falhoz"}),
    "38209": (63, (150, 470, 462, 545), {"Tömeg": "2,383 kg/fm", "Kerület": "412 mm", "Szélesség": "200 mm",
                                          "Vastagság": "34 mm", "Kivitel": "lamella (fénytörő) profil"}),
    "38210": (64, (120, 157, 214, 320), {"Tömeg": "1,706 kg/fm", "Kerület": "318 mm", "Szög": "45°",
                                          "Kompatibilis": "EXL-38209, EXL-38266", "Kivitel": "lamellatartó profil"}),
}


def render(page, box):
    zoom = 240 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    g = np.asarray(img.convert("L")) < 235  # a profilok világosszürke kitöltésűek
    ys, xs = np.where(g)
    return img.crop((max(xs.min() - 16, 0), max(ys.min() - 16, 0), min(xs.max() + 16, img.width), min(ys.max() + 16, img.height)))


def renders(slug):
    """A profil3d-vel készült 3D képek (ha vannak) a katalógusrajz után maradnak."""
    return [f"/termekkepek/3d/{slug}-{i}.webp" for i in (1, 2) if (ROOT / f"public/termekkepek/3d/{slug}-{i}.webp").exists()]


def main():
    doc = pymupdf.open(PDF)
    enrichment, missing = {}, []
    for p in [p for s in SUPPLIERS for p in load_products(s)]:
        code = (p["supplierCode"] or "").replace(" ", "").lstrip("0")
        item = ITEMS.get(code)
        if not item:
            missing.append(p)
            continue
        pno, box, specs = item
        clear_images(p["slug"])
        elox = "elox" in p["name"].lower()
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": "https://www.exlabesa.com", "sourceTitle": f"Exlabesa katalógus EXL-{code}",
                                 "matchedCode": f"EXL-{code}", "specs": {**specs, "Felület": "eloxált" if elox else "natúr"},
                                 "images": [save_image(render(doc[pno - 1], box), p["slug"], 1)] + renders(p["slug"])}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék a katalógusból, {len(missing)} nincs benne")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>10}  {p['name']}")


if __name__ == "__main__":
    main()
