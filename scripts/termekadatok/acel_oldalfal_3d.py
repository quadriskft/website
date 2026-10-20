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


if __name__ == "__main__":
    main()
