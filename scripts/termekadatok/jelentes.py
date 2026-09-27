"""Jelentés a letöltött termékadatokról: data/termekadatok_jelentes.csv (Excelben megnyitható)
és beszállítónkénti összesítő a képernyőre.

Használat: python3 scripts/termekadatok/jelentes.py
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import CATALOG, ENRICHMENT, ROOT  # noqa: E402

OUT = ROOT / "data/termekadatok_jelentes.csv"


def main():
    catalog = json.loads(CATALOG.read_text())
    groups = {g["slug"]: g["name"] for g in catalog["groups"]}
    extra = json.loads(ENRICHMENT.read_text())
    stats = defaultdict(lambda: [0, 0])
    rows = []
    for p in catalog["products"]:
        e = extra.get(p["slug"])
        found = bool(e)
        supplier = p["supplier"] or "(nincs megadva)"
        stats[supplier][0] += 1
        stats[supplier][1] += found
        rows.append([
            groups.get(p["group"], p["group"]), p["code"], p["name"], supplier, p["supplierCode"],
            "MEGVAN" if found else "NINCS", "igen" if e and e.get("images") else "nem",
            len(e.get("specs", {})) if e else 0, e.get("matchedCode", "") if e else "",
            e.get("sourceTitle", "")[:150] if e else "", e.get("sourceUrl", "") if e else "",
        ])
    rows.sort(key=lambda r: (r[3], r[5], r[0], r[2]))
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Termékcsoport", "Quadris cikkszám", "Megnevezés", "Beszállító", "Beszállítói kód", "Állapot",
                    "Kép", "Műszaki adatok száma", "Talált kód", "Beszállítói megnevezés", "Forrás"])
        w.writerows(rows)
    total = sum(s[0] for s in stats.values())
    done = sum(s[1] for s in stats.values())
    print(f"Összesen: {done}/{total} termék ({done * 100 // total}%)")
    for sup, (n, ok) in sorted(stats.items(), key=lambda kv: -kv[1][0]):
        print(f"  {sup:<24} {ok:>4}/{n:<4}")
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
