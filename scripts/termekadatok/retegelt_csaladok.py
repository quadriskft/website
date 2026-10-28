"""Rétegelt lemezek: a natúr, a csúszásmentes fenolos és a HEXA mintás lemezek egy-egy termékbe (termékcsalád) a
Quadris kérésére; a termékoldalon a rendelhető méretek táblázatban (vastagság × szélesség × hosszúság), a listában
egy kártya. A FILM/FILM és az MDF lemez külön termék marad.

Kimenet: data/termek_csaladok.json „retegelt-…” kulcsai (újragenerálva).

Használat: python3 scripts/termekadatok/retegelt_csaladok.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT  # noqa: E402

OUT = ROOT / "data/termek_csaladok.json"
CATEGORY = "retegelt-lemezek"
# család kulcsa -> (név, megjegyzés, a név feltétele)
FAMILIES = {
    "retegelt-natur": ("Natúr rétegelt lemez", "Natúr, bevonat nélküli rétegelt falemez",
                       lambda n: "natúr" in n),
    "retegelt-fenolos": ("Csúszásmentes fenolos rétegelt lemez", "Rétegelt falemez, egy oldalon csúszásmentes fenolbevonattal",
                         lambda n: "fenol" in n and "hexa" not in n),
    "retegelt-hexa": ("Csúszásmentes fenolos rétegelt lemez – HEXA",
                      "Rétegelt falemez, egy oldalon csúszásmentes, hatszögmintás (HEXA) fenolbevonattal",
                      lambda n: "fenol" in n and "hexa" in n),
}


def num(s):
    return float(s.replace(",", "."))


def hu(x):
    return f"{x:g}".replace(".", ",")


def main():
    products = json.loads((ROOT / "src/data/catalog.json").read_text())["products"]
    deleted = json.loads((ROOT / "data/torolt_termekek.json").read_text())
    fams = json.loads(OUT.read_text())
    fams = {k: v for k, v in fams.items() if not k.startswith("retegelt-")}
    for fid, (name, note, match) in FAMILIES.items():
        sizes = []
        for p in products:
            low = p["name"].lower()
            m = re.match(r"L\s*([\d,.]+)\s*x\s*(\d+)\s*x\s*(\d+)", p["name"], re.I)
            if p.get("category") != CATEGORY or p["slug"] in deleted or not m or not match(low):
                continue
            t, a, b = num(m.group(1)), *sorted((int(m.group(2)), int(m.group(3))))
            sizes.append(((t, a, b), p["slug"]))
        sizes.sort()
        fams[fid] = {
            "name": name, "label": "Méret", "title": "Rendelhető méretek",
            "note": f"{note} – válassza ki a kívánt vastagságot és méretet.",
            "navigate": True, "table": ["Vastagság", "Szélesség", "Hosszúság"],
            "rows": {s: [f"{hu(t)} mm", f"{a} mm", f"{b} mm"] for (t, a, b), s in sizes},
            "members": {s: f"{hu(t)} × {a} × {b} mm" for (t, a, b), s in sizes},
        }
        print(fid, len(sizes))
    OUT.write_text(json.dumps(fams, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
