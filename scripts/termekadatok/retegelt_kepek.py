"""Rétegelt lemezek (csúszásmentes rétegelt padló csoport) fotói a Quadris kérésére: a lemezfajtánként közös fotó
minden érintett termék első képe lesz, a meglévő képek (3D renderek) utána maradnak.

- HEXA (hexa mintás, fenolos): a Quadris által küldött 3 fotó (a 2. zöld háttere fehérre cserélve); a korábbi
  kezdőkép (barna render) a Quadris kérésére kikerült
- fenolos (nem HEXA): a Quadris által küldött fotó (MI-vel 4x nagyítva)
- film-film: a Quadris által küldött fotó (MI-vel 4x nagyítva)
- natúr: a Quadris által küldött fotó (MI-vel 4x nagyítva)

Használat: python3 scripts/termekadatok/retegelt_kepek.py   (utána kep_sorrend.py)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

# lemezfajta -> (forráskép, a slug feltétele, a kép utótagja)
KINDS = [
    (["data/forras/retegelt_hexa_foto_1.png", "data/forras/retegelt_hexa_foto_2.png", "data/forras/retegelt_hexa_foto_3.jpg"],
     lambda s: s.endswith("-hexa"), "hexa"),
    ("data/forras/retegelt_fenolos_lemez.png", lambda s: "fenol" in s and not s.endswith("-hexa"), "fenolos"),
    ("data/forras/retegelt_film_film_lemez.png", lambda s: "film-film" in s, "film-film"),
    ("data/forras/retegelt_natur_lemez.png", lambda s: "natur" in s, "natur"),
]


def main():
    data = load_enrichment()
    updates = {}
    for src, match, suffix in KINDS:
        srcs = src if isinstance(src, list) else [src]
        imgs = [Image.open(ROOT / f) for f in srcs]
        for slug, e in data.items():
            if "retegelt" not in slug or not match(slug):
                continue
            urls = [save_image(img, slug, suffix if len(imgs) == 1 else f"{suffix}-{i}") for i, img in enumerate(imgs, 1)]
            old = f"/termekkepek/{slug}-{suffix}.webp"
            e["images"] = urls + [u for u in e.get("images", []) if u not in urls and u != old]
            updates[slug] = e
            print(slug, suffix)
    update_enrichment(updates)


if __name__ == "__main__":
    main()
