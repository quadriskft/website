"""Mintás alulemezek fotója a minta szerint (a kloeckner.py és a nevbol.py után futtatandó).

A Klöckner webáruház minden „Warzenblech” változatnál ugyanazt a (Duett) fotót mutatja, ezért a
Quintett (öt csepp, a Quadris-megnevezésben „cseppmintás”) lemezeknél ezt a Quadris által küldött
cseppmintás lemez fotójára (data/forras/cseppmintas_lemez_quadris.webp) cseréljük, a gyémántmintásnál pedig elhagyjuk
(ott a minta a nevbol.py méretrajzán látszik). A Duett lemez fotója marad.

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


def quadris_photo():
    """A Quadris által küldött fotó, a fehér szegély levágásával."""
    img = Image.open(ROOT / "data/forras/cseppmintas_lemez_quadris.webp").convert("RGB")
    a = np.asarray(img.convert("L"))
    rows = np.where((a < 235).mean(axis=1) > 0.3)[0]
    cols = np.where((a < 235).mean(axis=0) > 0.3)[0]
    return img.crop((cols.min() + 2, rows.min() + 2, cols.max() - 2, rows.max() - 2))


def main():
    data = json.loads(ENRICHMENT.read_text())
    dst = ROOT / "public" / QUINTETT_IMG.lstrip("/")
    quadris_photo().save(dst, "WEBP", quality=90)
    n = 0
    for slug, e in data.items():
        if not slug.startswith("s-") or e.get("source") != "Klöckner":
            continue
        pattern = (e.get("specs") or {}).get("Minta", "")
        imgs = e.get("images", [])
        if "Quintett" in pattern:
            e["images"] = [QUINTETT_IMG] + [i for i in imgs if not i.endswith("-f1.webp") and i != QUINTETT_IMG]
            n += 1
        elif pattern == "gyémánt":
            e["images"] = [i for i in imgs if not i.endswith("-f1.webp")]
            n += 1
    ENRICHMENT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"mintás lemezek: {n} termék képe igazítva")


if __name__ == "__main__":
    main()
