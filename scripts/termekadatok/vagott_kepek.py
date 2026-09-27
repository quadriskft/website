"""Levágott (a kép szélébe futó) termékképek felderítése.

Egy kép akkor gyanús, ha valamelyik szélén a háttértől eltérő pixelek hosszú, összefüggő sávot
alkotnak – vagyis a tárgy túlnyúlik a képen (félbevágott ábra). Kiírja a gyanús képeket.

Használat: python3 scripts/termekadatok/vagott_kepek.py [--json kimenet.json]
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def edge_runs(img):
    g = np.asarray(img.convert("L"), dtype=np.int16)
    bg = int(np.median(np.concatenate([g[0, :], g[-1, :], g[:, 0], g[:, -1]])))
    out = {}
    for name, line in (("fent", g[1, :]), ("lent", g[-2, :]), ("bal", g[:, 1]), ("jobb", g[:, -2])):
        diff = np.abs(line - bg) > 40
        best = cur = 0
        for v in diff:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        out[name] = best / len(line)
    return out, bg


def is_cut(path):
    img = Image.open(path)
    runs, bg = edge_runs(img)
    # fehér/világos háttérnél egy szélen a hossz 8%-át meghaladó összefüggő tárgysáv = kilógó tárgy
    return bg > 200 and max(runs.values()) > 0.08, runs


def main():
    data = json.loads((ROOT / "src/data/termekadatok.json").read_text())
    ext = json.loads((ROOT / "src/data/bovitett.json").read_text())["products"]
    flagged = []
    for slug, e in list(data.items()) + [(p["slug"], p) for p in ext]:
        for img in e.get("images") or []:
            f = ROOT / "public" / img.lstrip("/")
            if f.exists():
                cut, runs = is_cut(f)
                if cut:
                    flagged.append({"slug": slug, "image": img, "source": e.get("source"), "edges": {k: round(v, 2) for k, v in runs.items()}})
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(flagged, ensure_ascii=False, indent=1))
    from collections import Counter
    print(len(flagged), "gyanús kép", Counter(x["source"] for x in flagged))


if __name__ == "__main__":
    main()
