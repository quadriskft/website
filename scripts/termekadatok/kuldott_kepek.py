"""A Quadris által küldött katalóguslap-képekből (képernyőképek) kivágott termékképek és adatok – azokhoz a
termékekhez, amelyeknek a forrás-katalógusa nincs meg nálunk. A kivágás kézzel rögzített (képpontban).

  e-ponyvagorgo-85810 = Claro RTE-003 ponyvagörgő (Claro catalogue 2019, 131. o.) – data/forras/claro_rte003_lap.png
    (az Edscha Compact-os párosítást – edscha_compact.py – a Quadris kérésére ez váltja)

Használat: python3 scripts/termekadatok/kuldott_kepek.py
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Quadris katalóguslap"
# slug -> (lapkép, [kivágások (x0, y0, x1, y1)], forrás megnevezése, gyártói cikkszám, adatok)
ITEMS = {
    "e-ponyvagorgo-85810": (
        "data/forras/claro_rte003_lap.png", [(115, 190, 470, 468), (640, 445, 1205, 818)],
        "Claro catalogue 2019, 131. oldal – RTE-003", "RTE-003",
        {"Gyártó": "Claro", "Kivitel": "kétgörgős ponyvagörgő, hosszlyukas rögzítőlappal",
         "Méret": "75 × 52 mm", "Görgőátmérő": "31,5 mm", "Teljes vastagság": "17 mm", "Lapvastagság": "5 mm",
         "Hosszlyuk": "52 × 8 mm", "Tömeg": "176 g/db", "Kiszerelés": "110 db/karton", "Minősítés": "DEKRA approved"}),
}


def main():
    enrichment = {}
    for p in load_products():
        if p["slug"] not in ITEMS:
            continue
        src, boxes, title, code, specs = ITEMS[p["slug"]]
        clear_images(p["slug"])
        im = Image.open(ROOT / src).convert("RGB")
        images = [save_image(im.crop(b), p["slug"], i) for i, b in enumerate(boxes, 1)]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceTitle": title, "matchedCode": code,
                                 "specs": {"Cikkszám (gyártói)": code, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
