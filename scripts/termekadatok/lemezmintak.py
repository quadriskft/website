"""Mintás alulemezek fotója a minta szerint (a kloeckner.py és a nevbol.py után futtatandó).

A Klöckner webáruház minden „Warzenblech” változatnál ugyanazt a (Duett) fotót mutatja, ezért a
Quintett (öt csepp, a Quadris-megnevezésben „cseppmintás”) lemezeknél ezt a Quadris által küldött
cseppmintás lemez fotójára (data/forras/cseppmintas_lemez_quadris.webp) cseréljük, a gyémántmintásnál pedig
a Quadris által küldött gyémántmintás fotóra (data/forras/diamond_lemez_quadris.webp). A Duett lemez fotója marad.
A rizsmintás lemezek (bármely forrásból) első képe a Quadris által küldött rizsmintás fotó (data/forras/rizs_lemez_quadris.webp).

Használat: python3 scripts/termekadatok/lemezmintak.py
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ENRICHMENT, ROOT  # noqa: E402

QUINTETT_IMG = "/termekkepek/minta-quintett.webp"
DIAMOND_IMG = "/termekkepek/minta-diamond.webp"
RIZS_IMG = "/termekkepek/minta-rizs.webp"


def quadris_photo(name="cseppmintas_lemez_quadris.webp"):
    """A Quadris által küldött fotó, a fehér szegély levágásával."""
    img = Image.open(ROOT / "data/forras" / name).convert("RGB")
    a = np.asarray(img.convert("L"))
    rows = np.where((a < 235).mean(axis=1) > 0.3)[0]
    cols = np.where((a < 235).mean(axis=0) > 0.3)[0]
    return img.crop((cols.min() + 2, rows.min() + 2, cols.max() - 2, rows.max() - 2))


def main():
    data = json.loads(ENRICHMENT.read_text())
    dst = ROOT / "public" / QUINTETT_IMG.lstrip("/")
    quadris_photo().save(dst, "WEBP", quality=90)
    Image.open(ROOT / "data/forras/diamond_lemez_quadris.webp").save(ROOT / "public" / DIAMOND_IMG.lstrip("/"), "WEBP", quality=90)
    Image.open(ROOT / "data/forras/rizs_lemez_quadris.webp").save(ROOT / "public" / RIZS_IMG.lstrip("/"), "WEBP", quality=90)
    n = 0
    for slug, e in data.items():
        if slug.startswith("s-") and "rizs-mintas" in slug:
            e["images"] = [RIZS_IMG] + [i for i in e.get("images", []) if i != RIZS_IMG]
            n += 1
            continue
        if not slug.startswith("s-") or e.get("source") != "Klöckner":
            continue
        pattern = (e.get("specs") or {}).get("Minta", "")
        imgs = e.get("images", [])
        if "Quintett" in pattern:
            e["images"] = [QUINTETT_IMG] + [i for i in imgs if not i.endswith("-f1.webp") and i != QUINTETT_IMG]
            n += 1
        elif pattern == "gyémánt":
            e["images"] = [DIAMOND_IMG] + [i for i in imgs if not i.endswith("-f1.webp") and i != DIAMOND_IMG]
            n += 1
    ENRICHMENT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"mintás lemezek: {n} termék képe igazítva")


if __name__ == "__main__":
    main()
