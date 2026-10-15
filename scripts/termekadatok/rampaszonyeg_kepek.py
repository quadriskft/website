"""Rámpaszőnyegek (gumiszőnyegek csoport) fotója a Quadris kérésére: a normál (bordás, merevítő bordás) rámpaszőnyeg
fotója minden rámpaszőnyeg első képe lesz, kivéve a könnyített G 17-et; a meglévő képek (3D renderek, rajz) utána
maradnak.

Használat: python3 scripts/termekadatok/rampaszonyeg_kepek.py   (utána kep_sorrend.py)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

SRC = "data/forras/rampaszonyeg_foto.png"
KONNYITETT = {"g-17-1750x1550-mm-rampaszonyeg"}


def main():
    data = load_enrichment()
    img = Image.open(ROOT / SRC)
    updates = {}
    for slug, e in data.items():
        if not slug.endswith("rampaszonyeg") or slug in KONNYITETT:
            continue
        url = save_image(img, slug, "foto")
        e["images"] = [url] + [u for u in e.get("images", []) if u != url]
        updates[slug] = e
        print(slug)
    update_enrichment(updates)


if __name__ == "__main__":
    main()
