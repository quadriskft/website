"""A Quadris által küldött katalóguslap-képekből (képernyőképek) kivágott termékképek és adatok – azokhoz a
termékekhez, amelyeknek a forrás-katalógusa nincs meg nálunk. A kivágás kézzel rögzített (képpontban).

  e-ponyvagorgo-85810 = Claro RTE-003 ponyvagörgő (Claro catalogue 2019, 131. o.) – data/forras/claro_rte003_lap.png
    (az Edscha Compact-os párosítást – edscha_compact.py – a Quadris kérésére ez váltja)

  E/COMPACT tetőprofil 900407 (mind az öt hossz) – az Edscha Compact sín méretezett rajza (43 × 112 mm) első képként,
    a meglévő (edscha_compact.py) képek elé: data/forras/edscha_compact_sin.png (a küldött lapkép kivágva,
    4× nagyítva, a szürke háttér fehérre cserélve; az eredeti: edscha_compact_sin_lap.png)
  E/Small tetőprofil 900931 (mind a három hossz) és E/VOLUMEN tetőprofil 900301 (mind a hat hossz) – a Volumen sín („Alu-Träger”) méretezett rajza első képként:
    data/forras/edscha_volumen_sin.png (a küldött 900301-es lap bal oldali rajza, 3× nagyítva; eredeti: …_lap.png)

  E69004740 CS-Compact tetőkereszttartó – a küldött két termékfotó második képként (edscha_cs_compact_tetokereszttarto.png)

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


# a meglévő képek elé kerülő rajzok: slug -> ([(kép, képnév-utótag), …], adatok)
COMPACT = [f"e-compact-tetoprofil-900407-{n}" for n in (5000, 5600, 6600, 7800, 8000)]
PREPEND = {slug: ([("data/forras/edscha_compact_sin.png", "meretrajz")],
                  {"Profilméret": "43 × 112 mm (alul 33 mm)", "Tömeg": "2,88 kg/m", "Ix": "112,5 cm⁴", "Iy": "13,3 cm⁴"})
           for slug in COMPACT}
VOLUMEN = [f"e-volumen-tetoprofil-900301-{n}" for n in (7800, 8500, 9000, 9400, 9600, 10000)]
# (a tetőszerkezetes rajz a lap jobb oldaláról, a súly/inercia kerete nélkül: edscha_volumen_tetoszerkezet.png)
PREPEND.update({slug: ([("data/forras/edscha_volumen_sin.png", "meretrajz"),
                        ("data/forras/edscha_volumen_tetoszerkezet.png", "tetoszerkezet")],
                       {"Profilméret": "120 × 163 mm (alul 35 mm)", "Tömeg": "5,65 kg/m", "Ix": "595,0 cm⁴", "Iy": "207,2 cm⁴"})
                for slug in VOLUMEN})
# E/Small tetőprofil (Edscha 900931) – a küldött lapról: profilrajz + tetőszerkezet (edscha_small_*.png)
SMALL = [f"e-small-tetoprofil-{n}-mm" for n in (6600, 7800, 8200)]
PREPEND.update({slug: ([("data/forras/edscha_small_sin.png", "meretrajz"),
                        ("data/forras/edscha_small_tetoszerkezet.png", "tetoszerkezet")],
                       {"Profilméret": "58,5 × 95 mm (alul 44,4 mm)", "Tömeg": "3 kg/m", "Ix": "82,7 cm⁴", "Iy": "33,9 cm⁴",
                        "Rajzszám (gyári)": "900931"})
                for slug in SMALL})


# a meglévő képek közé adott helyre beszúrt képek: slug -> [(kép, képnév-utótag, hely (0 = első))]
INSERT = {"e69004740-cs-compact-tetokereszttarto-2550-mm": [("data/forras/edscha_cs_compact_tetokereszttarto.png", "foto", 1)]}


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
    for slug, (drawings, specs) in PREPEND.items():
        prev = old.get(slug, {})
        front = [save_image(Image.open(ROOT / src).convert("RGB"), slug, suffix) for src, suffix in drawings]
        rest = [u for u in prev.get("images", []) if u not in front]
        enrichment[slug] = {**prev, "source": SOURCE, "specs": {**prev.get("specs", {}), **specs}, "images": front + rest}
    for slug, items in INSERT.items():
        prev = enrichment.get(slug) or old.get(slug, {})
        images = list(prev.get("images", []))
        for src, suffix, pos in items:
            url = save_image(Image.open(ROOT / src).convert("RGB"), slug, suffix)
            images = [u for u in images if u != url]
            images.insert(min(pos, len(images)), url)
        enrichment[slug] = {**prev, "source": SOURCE, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
