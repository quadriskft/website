"""Termékképek élesítése (a Quadris kérésére: az Edscha kategória összes képe).

A kis képeket előbb felnagyítja (Lanczos; a hosszabb oldal legalább TARGET px, legfeljebb MAX_SCALE-szeres),
majd élesítő maszkot (unsharp mask) alkalmaz; a nagy képek csak enyhe élesítést kapnak. Egy képet csak
egyszer élesít: a kész fájl ujjlenyomata a data/elesitett_kepek.json-ba kerül, és ha a fájl azóta nem
változott (nem töltötte le újra egy beszállítói szkript), kimarad. Az osszes.py a végén futtatja.

Használat: python3 scripts/termekadatok/elesites.py
"""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from common import ENRICHMENT, ROOT  # noqa: E402

TARGET, MAX_SCALE = 800, 6
DONE = ROOT / "data/elesitett_kepek.json"
CATEGORIES = {("elhuzhato-roloponyvas-rendszer", "edscha")}


def targets():
    catalog = json.loads((ROOT / "src/data/catalog.json").read_text())
    extended = json.loads((ROOT / "src/data/bovitett.json").read_text())
    deleted = json.loads((ROOT / "data/torolt_termekek.json").read_text())
    enrichment = json.loads(ENRICHMENT.read_text())
    moves = extended.get("moves", {})
    files = []
    for p in catalog["products"] + extended["products"]:
        if p["slug"] in deleted:
            continue
        m = moves.get(p["slug"], {})
        if (m.get("group", p.get("group")), m.get("category", p.get("category"))) not in CATEGORIES:
            continue
        for u in enrichment.get(p["slug"], {}).get("images") or p.get("images") or []:
            files.append(ROOT / "public" / u.lstrip("/"))
    return list(dict.fromkeys(files))


def digest(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def sharpen(path):
    im = Image.open(path).convert("RGB")
    scale = min(MAX_SCALE, max(1.0, TARGET / max(im.size)))
    if scale > 1.05:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=max(1.5, scale * 0.6), percent=140, threshold=2))
    else:
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))
    im.save(path, "WEBP", quality=90, method=6)


def main():
    done = json.loads(DONE.read_text()) if DONE.exists() else {}
    n = 0
    for f in targets():
        if not f.exists() or done.get(f.name) == digest(f):
            continue
        sharpen(f)
        done[f.name] = digest(f)
        n += 1
    DONE.write_text(json.dumps(dict(sorted(done.items())), ensure_ascii=False, indent=1) + "\n")
    print(f"élesítés: {n} kép")


if __name__ == "__main__":
    main()
