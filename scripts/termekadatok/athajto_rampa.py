"""Áthajtó rámpák (Hátsó ajtók és áthajtó rámpák / Áthajtórámpa) képei a Quadris kérésére.

- kezdőkép: a Quadris által küldött fotó (raklapos áthajtás), a gyártói (METALMEC) vízjel alatt levágva, 2x
  Lanczos-nagyítással
- második kép: a hosszhoz tartozó méretrajz, harmadik a másik hossz rajza (940 mm: athajto-rampa, 1065 mm: athajto-rampa-1065 – kézzel felvett
  termék, data/kezi_termekek.json); a két hossz egy termékcsaládban, táblázatból választható
- műszaki adatok a rajzról

Használat: python3 scripts/termekadatok/athajto_rampa.py   (utána kep_sorrend.py)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

SLUGS = ["athajto-rampa", "athajto-rampa-1065"]
RAJZ = {"athajto-rampa": ("data/forras/athajto_rampa_rajz_940.png", "940"),
        "athajto-rampa-1065": ("data/forras/athajto_rampa_rajz_1065.png", "1065")}
FOTO = "data/forras/athajto_rampa_foto.png"


def main():
    data = load_enrichment()
    img = Image.open(ROOT / FOTO)
    updates = {}
    for slug in SLUGS:
        e = data.get(slug, {"source": "Quadris fotó", "sourceUrl": "", "sourceTitle": "", "specs": {}, "images": []})
        url = save_image(img, slug, "foto")
        imgs = [url]
        if slug in RAJZ:
            src, hossz = RAJZ[slug]
            imgs.append(save_image(Image.open(ROOT / src), slug, "meretrajz"))
            # 3. képként a másik hossz rajza is (a Quadris kérésére mindkét méretrajz látható)
            other = next(k for k in RAJZ if k != slug)
            imgs.append(save_image(Image.open(ROOT / RAJZ[other][0]), slug, f"meretrajz-{RAJZ[other][1]}"))
            e["specs"] = {**e.get("specs", {}), "Hossz": f"{hossz} mm", "Magasság (profil)": "40 mm",
                          "Felhajtó él": "250 mm (ebből 200 mm lejtős)", "Zsanércsap": "Ø17 mm",
                          "Zsanérosztás": "186 mm", "Anyag": "alumínium, rácsos (üreges) profil, bordázott felület"}
        e["images"] = imgs + [u for u in e.get("images", []) if u not in imgs]
        updates[slug] = e
        print(slug, e["images"])
    update_enrichment(updates)


if __name__ == "__main__":
    main()
