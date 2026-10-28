"""Alumínium lemezek: a natúr (korábban „sima”) és az eloxált lemezek vastagságonként egy-egy termékbe (termékcsalád)
a Quadris kérésére; a termékoldalon a rendelhető méretek táblázatban (szélesség × hosszúság, ötvözet), a listában vastagságonként
egy kártya, vastagság szerint növekvő sorrendben.

Kimenet: data/termek_csaladok.json „alu-natur-…” és „alu-elox-…” kulcsai (újragenerálva) és a kártyák sorrendje
(data/termek_javitasok.json „order”).

Használat: python3 scripts/termekadatok/alu_lemez_csaladok.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment  # noqa: E402

OUT = ROOT / "data/termek_csaladok.json"
FIXES = ROOT / "data/termek_javitasok.json"
CATEGORY = "sima-lemez"  # az eloxált lemezek is innen kerülnek át az „Eloxált lemez” alkategóriába
# család-előtag -> (név, megjegyzés, eloxált-e)
KINDS = {
    "alu-natur": ("Natúr alumínium lemez", "Natúr (felületkezelés nélküli) alumínium lemez", False),
    "alu-elox": ("Eloxált alumínium lemez", "Eloxált alumínium lemez", True),
}


def num(s):
    return float(s.replace(",", "."))


def hu(x):
    return f"{x:g}".replace(".", ",")


def main():
    products = json.loads((ROOT / "src/data/catalog.json").read_text())["products"]
    deleted = json.loads((ROOT / "data/torolt_termekek.json").read_text())
    data = load_enrichment()
    fixes = json.loads(FIXES.read_text())
    fams = {k: v for k, v in json.loads(OUT.read_text()).items() if not k.startswith(tuple(f"{k}-" for k in KINDS))}
    order = []
    for prefix, (name, note, elox) in KINDS.items():
        by_th = {}
        for p in products:
            if p.get("category") != CATEGORY or p["slug"] in deleted or ("elox" in p["name"].lower()) != elox:
                continue
            if fixes.get(p["slug"], {}).get("move"):  # máshová áthelyezett termék
                continue
            m = re.match(r"S\s*([\d,.]+)\s*x\s*(\d+)\s*x\s*(\d+)", p["name"], re.I)
            if not m:
                continue
            sp = (data.get(p["slug"]) or {}).get("specs") or {}
            # rövid ötvözetjelölés a táblázatba (zárójeles kiegészítés és alternatív jelölés nélkül)
            base = re.sub(r"\s*\(.*?\)", "", sp.get("Ötvözet") or "").split(" / ")[0].strip()
            alloy = " ".join(x for x in (base, sp.get("Állapot")) if x)
            t, a, b = num(m.group(1)), int(m.group(2)), int(m.group(3))
            by_th.setdefault(t, []).append(((a, b, alloy), p["slug"]))
        for t, sizes in sorted(by_th.items()):
            sizes.sort()
            fams[f"{prefix}-{hu(t).replace(',', '-')}"] = {
                "name": f"{name} – {hu(t)} mm", "label": "Méret", "title": "Rendelhető méretek",
                "note": f"{note}, {hu(t)} mm vastag – válassza ki a kívánt méretet és ötvözetet.",
                "navigate": True, "table": ["Szélesség", "Hosszúság", "Ötvözet"],
                "rows": {s: [f"{a} mm", f"{b} mm", al or "–"] for (a, b, al), s in sizes},
                "members": {s: f"{a} × {b} mm" + (f" ({al})" if al else "") for (a, b, al), s in sizes},
            }
            order.append(sizes[0][1])
            print(prefix, hu(t), len(sizes))
    for slug, f in fixes.items():
        if isinstance(f, dict) and slug.startswith("s-") and "alu-lemez" in slug:
            f.pop("order", None)
    for i, slug in enumerate(order, 1):
        fixes.setdefault(slug, {})["order"] = i
    fixes = {k: v for k, v in fixes.items() if v}
    FIXES.write_text(json.dumps(fixes, ensure_ascii=False, indent=1) + "\n")
    OUT.write_text(json.dumps(fams, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
