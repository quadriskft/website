"""Rétegelt lemezek: a natúr, a csúszásmentes fenolos és a HEXA mintás lemezek vastagságonként egy-egy termékbe
(termékcsalád) a Quadris kérésére; a termékoldalon a rendelhető méretek táblázatban (szélesség × hosszúság), a listában
vastagságonként egy kártya (natúr, fenolos, HEXA sorrendben, azon belül vastagság szerint). A FILM/FILM és az MDF lemez
külön termék marad, a sor végén.

Kimenet: data/termek_csaladok.json „retegelt-…” kulcsai (újragenerálva) és a kártyák sorrendje
(data/termek_javitasok.json „order”).

Használat: python3 scripts/termekadatok/retegelt_csaladok.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT  # noqa: E402

OUT = ROOT / "data/termek_csaladok.json"
FIXES = ROOT / "data/termek_javitasok.json"
CATEGORY = "retegelt-lemezek"
# család kulcsa -> (név, megjegyzés, a név feltétele)
FAMILIES = {
    "retegelt-natur": ("Natúr rétegelt lemez", "Natúr, bevonat nélküli rétegelt falemez",
                       lambda n: "natúr" in n),
    "retegelt-fenolos": ("Csúszásmentes fenolos rétegelt lemez", "Rétegelt falemez, egy oldalon csúszásmentes fenolbevonattal",
                         lambda n: "fenol" in n and "hexa" not in n),
    "retegelt-hexa": ("Csúszásmentes fenolos rétegelt lemez HEXA",
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
    order = []
    for fid, (name, note, match) in FAMILIES.items():
        by_th = {}
        for p in products:
            low = p["name"].lower()
            m = re.match(r"L\s*([\d,.]+)\s*x\s*(\d+)\s*x\s*(\d+)", p["name"], re.I)
            if p.get("category") != CATEGORY or p["slug"] in deleted or not m or not match(low):
                continue
            t, a, b = num(m.group(1)), *sorted((int(m.group(2)), int(m.group(3))))
            by_th.setdefault(t, []).append(((a, b), p["slug"]))
        for t, sizes in sorted(by_th.items()):
            sizes.sort()
            fams[f"{fid}-{hu(t).replace(',', '-')}"] = {
                "name": f"{name} – {hu(t)} mm", "label": "Méret", "title": "Rendelhető méretek",
                "note": f"{note}, {hu(t)} mm vastag – válassza ki a kívánt méretet.",
                "navigate": True, "table": ["Szélesség", "Hosszúság"],
                "rows": {s: [f"{a} mm", f"{b} mm"] for (a, b), s in sizes},
                "members": {s: f"{a} × {b} mm" for (a, b), s in sizes},
            }
            order.append(sizes[0][1])
            print(fid, hu(t), len(sizes))
    order += [p["slug"] for p in products if p.get("category") == CATEGORY and p["slug"] not in deleted
              and not any(p["slug"] in f["members"] for k, f in fams.items() if k.startswith("retegelt-"))]
    # kártyasorrend: a rétegelt lemezek korábbi „order” értékei helyett
    fixes = json.loads(FIXES.read_text())
    for slug, f in fixes.items():
        if slug.startswith("l-") and "order" in f and ("retegelt" in slug or "mdf" in slug):
            del f["order"]
    for i, slug in enumerate(order, 1):
        fixes.setdefault(slug, {})["order"] = i
    fixes = {k: v for k, v in fixes.items() if v}
    FIXES.write_text(json.dumps(fixes, ensure_ascii=False, indent=1) + "\n")
    OUT.write_text(json.dumps(fams, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
