"""Mintás alulemezek fotója a minta szerint (a kloeckner.py és a nevbol.py után futtatandó).

A Klöckner webáruház minden „Warzenblech” változatnál ugyanazt a (Duett) fotót mutatja, ezért a
Quintett (öt csepp, a Quadris-megnevezésben „cseppmintás”) lemezeknél ezt a RE-ALL katalógus
(02-12 fejezet, „Rilievi – a 5 mandorle”) mintafotójára cseréljük, a gyémántmintásnál pedig elhagyjuk
(ott a minta a nevbol.py méretrajzán látszik). A Duett lemez fotója marad.

Használat: python3 scripts/termekadatok/lemezmintak.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ENRICHMENT, ROOT, fetch  # noqa: E402

PDF = "https://www.re-all.it/images/catalogo-pdf/2026/02-12.pdf"
QUINTETT_IMG = "/termekkepek/minta-quintett-reall.webp"


def quintett_photo():
    doc = pymupdf.open(stream=fetch(PDF), filetype="pdf")
    page = doc[6]  # 7. oldal: „Rilievi”
    pix = pymupdf.Pixmap(doc, page.get_images(full=True)[0][0])
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    k = pix.width / page.rect.width
    # a „a 5 mandorle” mintakép környéke (pt), majd a szürke fotó pontos határa
    box = img.crop((int(190 * k), int(440 * k), int(300 * k), int(525 * k)))
    a = np.asarray(box.convert("L"))
    rows = np.where((a < 200).mean(axis=1) > 0.3)[0]  # a fotó sorai (a felirat sorai ritkák)
    cols = np.where((a < 200).mean(axis=0) > 0.3)[0]
    ys, xs = rows, cols
    return box.crop((xs.min() + 4, ys.min() + 4, xs.max() - 4, ys.max() - 4))


def main():
    data = json.loads(ENRICHMENT.read_text())
    dst = ROOT / "public" / QUINTETT_IMG.lstrip("/")
    quintett_photo().save(dst, "WEBP", quality=90)
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
