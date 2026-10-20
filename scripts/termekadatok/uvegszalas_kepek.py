"""Üvegszálas poliészter lemezek képei a Quadris kérésére.

- POLYDET: a Quadris által küldött lemezfotó az első kép (Lanczos 2x); utána a kontúrozott 3D render
  (scripts/profil3d/kontur.py) és a méretrajz; második képként a felhasználási fotó (dobozos felépítmény,
  a teherautóra vágva, enyhén élesítve); a második 3D nézet a Quadris kérésére kikerül

Használat: python3 scripts/termekadatok/uvegszalas_kepek.py   (utána kep_sorrend.py)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

POLYDET_FOTO = "data/forras/polydet_lemez_foto.png"
POLYDET_ALKALMAZAS = "data/forras/polydet_alkalmazas_foto.jpg"


def main():
    data = load_enrichment()
    updates = {}
    img, app = Image.open(ROOT / POLYDET_FOTO), Image.open(ROOT / POLYDET_ALKALMAZAS)
    for slug, e in data.items():
        if slug.startswith("polydet-"):
            url, app_url = save_image(img, slug, "foto"), save_image(app, slug, "alkalmazas")
            rest = [u for u in e.get("images", []) if u not in (url, app_url, f"/termekkepek/3d/{slug}-2.webp")]
            e["images"] = [url, app_url] + rest
        else:
            continue
        updates[slug] = e
        print(slug, len(e["images"]), "kép")
    update_enrichment(updates)


if __name__ == "__main__":
    main()
