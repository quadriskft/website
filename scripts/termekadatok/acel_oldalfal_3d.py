"""Acél oldalfalak 3D képei élesítve (a Quadris kérésére): a gyártói 3D képek (kb. 60×150 px) MI-vel (EDSR) 4x
nagyítva, majd 1000 px-re Lanczos-szal és élesítve – data/forras/acel_oldalfal_3d/<slug>.jpg. A korábbi homályos
3D kép (<slug>-1.webp) helyére, első képként.

Használat: python3 scripts/termekadatok/acel_oldalfal_3d.py   (utána kep_sorrend.py)
"""

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

SRC = ROOT / "data/forras/acel_oldalfal_3d"
# a gyártói katalógus típuscsoport-áttekintő rajza (acel_oldalfal_attekinto.py, vektorosan): a csoport (termékcsalád)
# minden típusánál a 3D kép után, második képként
ATTEKINTO = {"b": "acel-oldalfal-b", "bn": "acel-oldalfal-bn-bns", "hv": "acel-oldalfal-hv", "hvn": "acel-oldalfal-hvn",
             "bak": "acel-oldalfal-bak-baks", "hvak": "acel-oldalfal-hvak", "kiegeszito": "acel-oldalfal-kiegeszito"}


def main():
    extended = {p["slug"]: p for p in json.loads((ROOT / "src/data/bovitett.json").read_text())["products"]}
    data = load_enrichment()
    updates = {}
    for f in sorted(SRC.glob("*.jpg")):
        slug = f.stem
        e = data.get(slug) or {"source": "", "sourceUrl": "", "sourceTitle": "", "specs": {},
                               "images": list(extended.get(slug, {}).get("images", []))}
        url = save_image(Image.open(f), slug, "3d-eles")
        old = f"/termekkepek/{slug}-1.webp"
        e["images"] = [url] + [u for u in e.get("images", []) if u not in (url, old)]
        updates[slug] = e
    update_enrichment(updates)
    print(len(updates), "élesített 3D kép")
    data = load_enrichment()
    over = {}
    families = json.loads((ROOT / "data/termek_csaladok.json").read_text())
    for name, fam in ATTEKINTO.items():
        img = Image.open(ROOT / f"data/forras/acel_oldalfal_{name}_attekinto.png")
        slugs = list(families.get(fam, {}).get("members", {}))
        for slug in slugs:
            e = data.get(slug) or {"source": "", "sourceUrl": "", "sourceTitle": "", "specs": {}, "images": []}
            url = save_image(img, slug, "attekinto", max_size=3100)
            imgs = [u for u in e.get("images", []) if u != url]
            k = 1 if imgs and "3d" in imgs[0] else 0
            e["images"] = imgs[:k] + [url] + imgs[k:]
            over[slug] = e
    update_enrichment(over)
    print(len(over), "áttekintő rajz")


if __name__ == "__main__":
    main()
