"""Gumiszőnyegek fotói a Quadris kérésére: a küldött fotó az érintett termékek első képe lesz, a meglévő képek
(3D renderek, rajz) utána maradnak.

- rámpaszőnyegek: a normál (merevítő bordás) rámpaszőnyeg fotója, a könnyített G 17 kivételével
- általános gumiszőnyegek (sima felületű, S/S): tekercs fotója (MI-vel 4x nagyítva); a mintás Amoeba és
  Diamond nem kapja meg
- Cobra / CBR szőnyegek: mintás tekercs fotója (Lanczos-nagyítással: az MI a finom mintát csíkossá torzította)

Használat: python3 scripts/termekadatok/gumiszonyeg_kepek.py   (utána kep_sorrend.py)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

KONNYITETT = {"g-17-1750x1550-mm-rampaszonyeg"}
# (forráskép, a slug feltétele)
KINDS = [
    ("data/forras/rampaszonyeg_foto.png", lambda s: s.endswith("rampaszonyeg") and s not in KONNYITETT),
    ("data/forras/altalanos_gumiszonyeg_foto.png", lambda s: "-s-s-altalanos-gumi" in s),
    ("data/forras/cobra_gumiszonyeg_foto.png", lambda s: "-cobra-szonyeg-" in s or "-cbr-szonyeg-" in s),
]


def main():
    data = load_enrichment()
    updates = {}
    for src, match in KINDS:
        img = Image.open(ROOT / src)
        for slug, e in data.items():
            if not match(slug):
                continue
            url = save_image(img, slug, "foto")
            e["images"] = [url] + [u for u in e.get("images", []) if u != url]
            updates[slug] = e
            print(slug)
    update_enrichment(updates)


if __name__ == "__main__":
    main()
