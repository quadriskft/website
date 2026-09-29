"""A Quadris által küldött katalóguslap-képekből (képernyőképek) kivágott termékképek és adatok – azokhoz a
termékekhez, amelyeknek a forrás-katalógusa nincs meg nálunk. A kivágás kézzel rögzített (képpontban).

  e-ponyvagorgo-85810 = Claro RTE-003 ponyvagörgő (Claro catalogue 2019, 131. o.) – data/forras/claro_rte003_lap.png
    (az Edscha Compact-os párosítást – edscha_compact.py – a Quadris kérésére ez váltja)

  E/COMPACT tetőprofil 900407 (mind az öt hossz) – az Edscha Compact sín méretezett rajza (43 × 112 mm) első képként,
    a meglévő (edscha_compact.py) képek elé: data/forras/edscha_compact_sin.png (a küldött lapkép kivágva,
    4× nagyítva, a szürke háttér fehérre cserélve; az eredeti: edscha_compact_sin_lap.png)
  E/VOLUMEN tetőprofil 900301 (mind a hat hossz) – a Volumen sín („Alu-Träger”) méretezett rajza első képként:
    data/forras/edscha_volumen_sin.png (a küldött 900301-es lap bal oldali rajza, 3× nagyítva; eredeti: …_lap.png)

Használat: python3 scripts/termekadatok/kuldott_kepek.py
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

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


# a meglévő képek elé kerülő rajz: slug-ok -> (kép, képnév-utótag, adatok)
COMPACT = [f"e-compact-tetoprofil-900407-{n}" for n in (5000, 5600, 6600, 7800, 8000)]
PREPEND = {slug: ("data/forras/edscha_compact_sin.png", "meretrajz",
                  {"Profilméret": "43 × 112 mm (alul 33 mm)", "Tömeg": "2,88 kg/m", "Ix": "112,5 cm⁴", "Iy": "13,3 cm⁴"})
           for slug in COMPACT}
VOLUMEN = [f"e-volumen-tetoprofil-900301-{n}" for n in (7800, 8500, 9000, 9400, 9600, 10000)]
PREPEND.update({slug: ("data/forras/edscha_volumen_sin.png", "meretrajz",
                       {"Profilméret": "120 × 163 mm (alul 35 mm)", "Tömeg": "5,65 kg/m", "Ix": "595,0 cm⁴", "Iy": "207,2 cm⁴"})
                for slug in VOLUMEN})


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
    old = load_enrichment()
    for slug, (src, suffix, specs) in PREPEND.items():
        prev = old.get(slug, {})
        drawing = save_image(Image.open(ROOT / src).convert("RGB"), slug, suffix)
        rest = [u for u in prev.get("images", []) if u != drawing]
        enrichment[slug] = {**prev, "source": SOURCE, "specs": {**prev.get("specs", {}), **specs}, "images": [drawing] + rest}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
