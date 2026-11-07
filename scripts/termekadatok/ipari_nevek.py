"""Ipari félgyártmányok: egységes terméknevek a Quadris kérésére.

Minden név a mérettel kezdődik, utána (ha van) a sarok-rádiusz (R5, R7/3 …), majd „Alu <típus>”, eloxáltnál a végén
„, eloxált”; a cikkszám nem része a névnek. Pl. „60x30x2,5 mm R2,5 Alu zártszelvény, eloxált”.
A 6000 mm-es szálhosszt a névből kivesszük, és a műszaki adatokba (Szálhossz) tesszük.

Kimenet: data/termek_javitasok.json („name”, szükség esetén „specs.Szálhossz”).
Használat: python3 -I scripts/termekadatok/ipari_nevek.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXES = ROOT / "data/termek_javitasok.json"
GROUP = "ipari-felgyartmanyok"
TYPES = {"zartszelveny": "zártszelvény", "u-profil": "U profil", "l-profil": "L profil", "lapos-profil": "lapos profil"}


def rename(p):
    n = p["name"]
    low = n.lower()
    size = re.search(r"\d+(?:[,.]\d+)?(?:\s*x\s*\d+(?:[,.]\d+)?)*", n)
    if not size:
        return None
    size_s = re.sub(r"\s*x\s*", "x", size.group(0)).replace(".", ",")
    rest = n[size.end():]
    # sarok-rádiusz: R5, R2,5, R7/3, OR3/IR1 (külső/belső) vagy önálló „R”
    r = ""
    m = re.search(r"\bOR\s*([\d,.]+)\s*/\s*IR\s*([\d,.]+)", rest, re.I)
    if m:
        r = f"R{m.group(1)}/{m.group(2)}"
    else:
        m = re.search(r"\bR\s*([\d,.]+(?:/[\d,.]+)?)", rest)
        if m:
            r = "R" + m.group(1).replace(".", ",")
        elif re.search(r"\bR\b", rest):
            r = "R"
    if p["category"] == "cso-rud":
        kind = "rúd" if "rúd" in low else "cső"
    else:
        kind = TYPES[p["category"]]
    elox = "elox" in low
    name = f"{size_s} mm{(' ' + r) if r else ''} Alu {kind}{', eloxált' if elox else ''}"
    length = "6000 mm" if re.search(r"\b6000\s*mm", low) else None
    return name, length


def main():
    products = json.loads((ROOT / "src/data/catalog.json").read_text())["products"]
    fixes = json.loads(FIXES.read_text())
    for p in products:
        if p.get("group") != GROUP:
            continue
        res = rename(p)
        if not res:
            print("?", p["slug"])
            continue
        name, length = res
        f = fixes.setdefault(p["slug"], {})
        f["name"] = name
        if length:
            f.setdefault("specs", {})["Szálhossz"] = length
        print(f"{p['name']!r:60} -> {name}")
    FIXES.write_text(json.dumps(fixes, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
