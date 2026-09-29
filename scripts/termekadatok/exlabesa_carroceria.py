"""Exlabesa „Sistemas de carrocerías de aluminio” (CATALOGO CARROCERIA.pdf, a Quadris-tól kapott gyári katalógus) –
azok a padlóprofilok, amelyek a lengyel standard katalógusban (exlabesa.py) nem szerepelnek.

A katalógus lapjai szöveg nélküliek (képek), ezért az adatok kézzel rögzítettek a lapról; a profil rajza a
data/forras/exlabesa_carroceria/<EXL-szám>.png kivágásból kerül a termékhez, ha a fájl megvan.

A Quadris kérésére: 225630/55 (padló profil 250 mm zárt) = EXL-5630; 222910/30 (padló profil 200 mm) = EXL-29100.

Használat: python3 scripts/termekadatok/exlabesa_carroceria.py
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Exlabesa carrocería"
DIR = ROOT / "data/forras/exlabesa_carroceria"
# slug -> (EXL-szám, adatok a katalóguslapról)
ITEMS = {
    "225630-55-padlo-profil-250-mm-zart": ("5630", {
        "Tömeg": "6,359 kg/fm", "Kerület": "1595 mm", "Szélesség": "250 mm", "Magasság": "54,5 mm",
        "Falvastagság": "2,5 / 3,0 / 4,0 mm", "Ix": "119,07 cm⁴", "Iy": "1412,20 cm⁴",
        "Kivitel": "zárt (többkamrás) padlóprofil"}),
}


def main():
    enrichment = {}
    for p in load_products():
        if p["slug"] not in ITEMS:
            continue
        code, specs = ITEMS[p["slug"]]
        clear_images(p["slug"])
        src = DIR / f"{code}.png"
        images = [save_image(Image.open(src).convert("RGB"), p["slug"], 1)] if src.exists() else []
        enrichment[p["slug"]] = {"source": SOURCE, "sourceTitle": f"Exlabesa EXL-{code}", "matchedCode": f"EXL-{code}",
                                 "specs": {"Cikkszám (gyártói)": f"EXL-{code}", **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
