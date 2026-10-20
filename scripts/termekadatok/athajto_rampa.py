"""Áthajtó rámpák (Hátsó ajtók és áthajtó rámpák / Áthajtórámpa) képei a Quadris kérésére.

- kezdőkép: a Quadris által küldött fotó (raklapos áthajtás), a gyártói (METALMEC) vízjel alatt levágva, 2x
  Lanczos-nagyítással

Használat: python3 scripts/termekadatok/athajto_rampa.py   (utána kep_sorrend.py)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

SLUGS = ["athajto-rampa", "rampa-040x615x2500"]
FOTO = "data/forras/athajto_rampa_foto.png"


def main():
    data = load_enrichment()
    img = Image.open(ROOT / FOTO)
    updates = {}
    for slug in SLUGS:
        e = data.get(slug, {"source": "Quadris fotó", "sourceUrl": "", "sourceTitle": "", "specs": {}, "images": []})
        url = save_image(img, slug, "foto")
        e["images"] = [url] + [u for u in e.get("images", []) if u != url]
        updates[slug] = e
        print(slug, e["images"])
    update_enrichment(updates)


if __name__ == "__main__":
    main()
