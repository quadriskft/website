"""A Quadris által küldött gyári rajzlapok (szkennelt PDF-ek) kivágása azokhoz a termékekhez, amelyekhez a
beszállítói katalógusokban nincs rajz. A kivágás kézzel rögzített (pt-ban, a PDF oldalkoordinátáiban); a
kivágott rajz az egységes rajz-pipeline (alvaz_rajzok.py) forrása lesz.

  208755 (talpas hossztartó) = Constellium Děčín 8755 „traverzní profil” – data/forras/constellium_8755_lap.pdf
  226821/21 (padló profil 200 mm) = BODEGA TB48968 műhelyrajz – data/forras/bodega_tb48968_rajz.pdf (elforgatott lap)

Használat: python3 scripts/termekadatok/kuldott_rajzok.py
"""

import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Quadris gyári rajz"
# slug -> (PDF, oldal, kivágás [pt], forrás megnevezése, gyártói szám, adatok)
ITEMS = {
    "208755-hossztarto-talpas-140-6-magas-120-10-60-8-mm": (
        "data/forras/constellium_8755_lap.pdf", 1, (130, 428, 334, 668), "Constellium 8755 – traverzní profil", "8755",
        {"Tömeg": "7,106 kg/fm", "Magasság": "139,5 ± 0,5 mm", "Talpszélesség": "120 mm", "Gerincvastagság": "6 mm",
         "Kivitel": "talpas hossztartó (traverz) profil"}),
    "226821-21-padlo-profil-200-mm": (
        "data/forras/bodega_tb48968_rajz.pdf", 1, (40, 38, 155, 570), "BODEGA TB48968 – műhelyrajz", "TB48968",
        {"Tömeg": "2,686 kg/fm", "Keresztmetszet": "994,6 mm²", "Teljes szélesség": "238 mm", "Magasság": "21 mm",
         "Anyag": "EN AW-6063 T66", "Kivitel": "nyitott, bordás padlóprofil T-talpakkal"}),
}
# a lapon elforgatva (álló helyzetben) rajzolt profilok: a kivágás forgatása fokban (PIL, pozitív = balra)
ROTATE = {"226821-21-padlo-profil-200-mm": -90}


def render(slug):
    """A tétel kivágása 300 dpi-vel (elforgatva, ha kell) – az egységes rajz forrása is ez."""
    pdf, pno, box = ITEMS[slug][:3]
    pix = pymupdf.open(ROOT / pdf)[pno - 1].get_pixmap(dpi=300, clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img.rotate(ROTATE[slug], expand=True) if slug in ROTATE else img


def main():
    enrichment = {}
    for p in load_products():
        if p["slug"] not in ITEMS:
            continue
        pdf, pno, box, title, code, specs = ITEMS[p["slug"]]
        clear_images(p["slug"])
        img = render(p["slug"])
        enrichment[p["slug"]] = {"source": SOURCE, "sourceTitle": title, "matchedCode": code,
                                 "specs": {"Cikkszám (gyártói)": code, **specs}, "images": [save_image(img, p["slug"], 1)]}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
