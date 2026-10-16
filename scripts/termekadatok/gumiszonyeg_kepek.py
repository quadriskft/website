"""Gumiszőnyegek fotói a Quadris kérésére: a küldött fotó az érintett termékek első képe lesz, a meglévő képek
(3D renderek, rajz) utána maradnak.

- rámpaszőnyegek: a normál (merevítő bordás) rámpaszőnyeg fotója, a könnyített G 17 kivételével
- általános gumiszőnyegek (sima felületű, S/S): tekercs fotója (MI-vel 4x nagyítva); a mintás Amoeba és
  Diamond nem kapja meg
- Amoeba gumiszőnyegek: mintás tekercs fotója (Lanczos-nagyítással)
- istálló szőnyegek: a Quadris által küldött 3 fotó (tekercs, rétegek, kigöngyölt tekercs), Lanczos-nagyítással;
  az utánfutó-/lószállító és az állattartó szőnyeg nem kapja meg
- Diamond mintás gumi (G 3x2200x10000): tekercs fotója (Lanczos-nagyítással)
- víztiszta PVC (G 3/4/5x1000 mm): tekercs fotója (Lanczos-nagyítással)
- Cobra / CBR szőnyegek: mintás tekercs fotója (Lanczos-nagyítással: az MI a finom mintát csíkossá torzította)

Használat: python3 scripts/termekadatok/gumiszonyeg_kepek.py   (utána kep_sorrend.py)
"""

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

KONNYITETT = {"g-17-1750x1550-mm-rampaszonyeg"}
ISTALLO = ["data/forras/istallo_szonyeg_foto_%d.png" % i for i in (1, 2, 3)]
# (forráskép vagy forrásképek listája, a slug feltétele)
KINDS = [
    ("data/forras/rampaszonyeg_foto.png", lambda s: s.endswith("rampaszonyeg") and s not in KONNYITETT),
    ("data/forras/altalanos_gumiszonyeg_foto.png", lambda s: "-s-s-altalanos-gumi" in s),
    ("data/forras/amoeba_gumiszonyeg_foto.png", lambda s: "-amoeba-gumiszonyeg" in s),
    ("data/forras/diamond_gumiszonyeg_foto.png", lambda s: "-diamond-mintas-gumi" in s),
    ("data/forras/pvc_viztiszta_foto.png", lambda s: s.startswith("g-") and "-pvc-attlatszo-viztiszta" in s),
    (ISTALLO, lambda s: "istallo-szonyeg" in s or s.startswith("istallo-gumiszonyeg")),
    ("data/forras/cobra_gumiszonyeg_foto.png", lambda s: "-cobra-szonyeg-" in s or "-cbr-szonyeg-" in s),
]


def main():
    data = load_enrichment()
    # a bővített kínálat termékei (még nincs termékadat-bejegyzésük): a meglévő képeik utána maradnak
    extended = {p["slug"]: p for p in json.loads((ROOT / "src/data/bovitett.json").read_text()).get("products", [])}
    for slug, p in extended.items():
        if slug not in data and any(match(slug) for _, match in KINDS):
            data[slug] = {"source": "Quadris fotó", "sourceUrl": "", "sourceTitle": "", "specs": {}, "images": list(p.get("images", []))}
    updates = {}
    for src, match in KINDS:
        srcs = src if isinstance(src, list) else [src]
        for slug, e in data.items():
            if not match(slug):
                continue
            urls = [save_image(Image.open(ROOT / f), slug, "foto" if len(srcs) == 1 else f"foto-{i}") for i, f in enumerate(srcs, 1)]
            e["images"] = urls + [u for u in e.get("images", []) if u not in urls]
            updates[slug] = e
            print(slug)
    update_enrichment(updates)


if __name__ == "__main__":
    main()
