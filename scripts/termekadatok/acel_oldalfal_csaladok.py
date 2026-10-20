"""Acél oldalfalak a gyártó típusrendszere szerint termékcsaládokba (a Quadris kérésére): rendszerenként egy termék,
a termékoldalon táblázatban a típusok (alap / magasító / kerettel …) magasság szerint.

Rendeléskor hossz × darab sorok (a gyártói hosszakból választva, ill. a lézerhegesztetteknél 500–13 500 mm).
Rendszerek: lézerhegesztett B, BN, HV, HVN, HVD; Heavy Duty FHD, FOX B, FOX HV, FOX L (B / BAK / BN),
FOX L (HV / HVAK / HVN), FOX-ROCK. A Quadris Excel-termékei (HV 400 …, „Acél oldalfal 2 mm”) a saját rendszerükben
a gyártói azonos típus helyén szerepelnek (a beszállítói duplikátum kimarad).
Kimenet: data/termek_csaladok.json „acel-oldalfal-…” kulcsai (újragenerálva).

Használat: python3 scripts/termekadatok/acel_oldalfal_csaladok.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT  # noqa: E402

OUT = ROOT / "data/termek_csaladok.json"
CATS = ("lezerhegesztett-acel-oldalfalak", "heavy-duty-acel-oldalfalak", "acel-oldalfalak")
SYSTEMS = [  # (azonosító, név, a típusbetűk feltétele)
    ("fox-rock", "Acél oldalfal FOX-ROCK (Heavy Duty)", lambda s: s.startswith("FOX-ROCK")),
    ("foxl-hv", "Acél oldalfal FOX L – HV / HVAK / HVN (Heavy Duty)", lambda s: s.startswith("FOXLHV")),
    ("foxl-b", "Acél oldalfal FOX L – B / BAK / BN (Heavy Duty)", lambda s: s.startswith("FOXLB")),
    ("foxhv", "Acél oldalfal FOX HV (Heavy Duty)", lambda s: s.startswith("FOXHV")),
    ("foxb", "Acél oldalfal FOX B (Heavy Duty)", lambda s: s.startswith("FOXB")),
    ("fhd", "Acél oldalfal FHD (Heavy Duty)", lambda s: s.startswith("FHD")),
    ("bn", "Acél oldalfal BN rendszer (lézerhegesztett)", lambda s: s.startswith("BN")),
    ("b", "Acél oldalfal B rendszer (lézerhegesztett)", lambda s: s.startswith("B")),
    ("hvn", "Acél oldalfal HVN rendszer (lézerhegesztett)", lambda s: s.startswith("HVN")),
    ("hvd", "Acél oldalfal HVD rendszer (lézerhegesztett)", lambda s: s.startswith("HVD")),
    ("hv", "Acél oldalfal HV rendszer (lézerhegesztett)", lambda s: s.startswith("HV")),
]


# gyártási hosszak a gyártói prospektus szerint: Heavy Duty 2500 / 5000 / 6000 mm (FHD: 2500 / 5000 mm),
# a lézerhegesztett profilok 0,5–13,5 m között tetszőleges hosszban
LIGHT = {"min": 500, "max": 13500, "hint": "Gyártási hossz: 500–13 500 mm között bármilyen hosszban (±1 mm). Több hossz is megadható."}
HEAVY = {"options": [2500, 5000, 6000], "hint": "Gyártási hosszak: 2500, 5000 vagy 6000 mm. Több hossz is megadható."}
LENGTHS = {"fhd": {"options": [2500, 5000], "hint": "Gyártási hosszak: 2500 vagy 5000 mm. Több hossz is megadható."},
           "foxb": HEAVY, "foxhv": HEAVY, "foxl-b": HEAVY, "foxl-hv": HEAVY, "fox-rock": HEAVY}


def usage(code):
    """a gyártói adatlapon nem szereplő felhasználás a típusjelből: AK = ráépítő (magasító) oldalfal"""
    if code.upper().startswith("FOX-ROCK"):
        return "kőszállító billencs"
    return "magasító" if "AK" in code.upper() else "alap"


def short(v):
    return {"alap oldalfal": "alap", "magasító (ráépítő) oldalfal": "magasító"}.get(v, v)


def spec(sp, *keys):
    for k in keys:
        if sp.get(k):
            return str(sp[k])
    return ""


def main():
    excel = json.loads((ROOT / "src/data/catalog.json").read_text())["products"]
    ext_all = json.loads((ROOT / "src/data/bovitett.json").read_text())
    extended, moves = ext_all["products"], ext_all.get("moves", {})
    fixes = json.loads((ROOT / "data/termek_javitasok.json").read_text())
    deleted = json.loads((ROOT / "data/torolt_termekek.json").read_text())
    extra = json.loads((ROOT / "src/data/termekadatok.json").read_text())
    items = []  # (rendszer, típuskód, magasság, slug, excel?, specs)
    for src, is_excel in ((excel, True), (extended, False)):
        for p in src:
            cat = (fixes.get(p["slug"], {}).get("move") or moves.get(p["slug"]) or {}).get("category", p["category"])
            if cat not in CATS or p["slug"] in deleted:
                continue
            sp = {**(p.get("specs") or {}), **(extra.get(p["slug"], {}).get("specs") or {})}
            code = (p.get("code") or sp.get("Típus") or "").strip()
            m = re.match(r"^([A-Za-z\-]+(?: ?(?:HEAVY|LIGHT))?)\s*(\d{3,4})?$", code)
            if not m:
                print("  nem értelmezhető típus:", p["slug"], code)
                continue
            letters = m.group(1).replace(" ", "").upper()
            sysid = next((sid for sid, _, cond in SYSTEMS if cond(letters)), None)
            height = int(spec(sp, "Magasság [mm]", "Magasság").split()[0] or 0) if spec(sp, "Magasság [mm]", "Magasság") else 0
            items.append((sysid, re.sub(r"\s+", " ", code), height, p["slug"], is_excel, sp))
    fams = {k: v for k, v in json.loads(OUT.read_text()).items() if not k.startswith("acel-oldalfal-")}
    taken = {s for k, f in fams.items() if not k.startswith("_") for s in f["members"]}
    for sid, name, _ in SYSTEMS:
        rows, seen = [], {}
        # az Excel-termék elsőbbséget kap az azonos gyártói típussal szemben
        for it in sorted([i for i in items if i[0] == sid and i[3] not in taken], key=lambda i: (not i[4], i[2], i[1])):
            key = it[1].replace(" ", "").upper()
            if key in seen:
                print("  duplikátum, kimarad a családból:", it[3], "=", seen[key])
                continue
            seen[key] = it[3]
            rows.append(it)
        if len(rows) < 2:
            continue
        rows.sort(key=lambda i: (i[2], i[1]))
        leader = next((r[3] for r in rows if r[4]), rows[0][3])
        fams[f"acel-oldalfal-{sid}"] = {
            "name": name, "label": "Típus", "title": "Rendelhető típusok",
            "note": "A rendszer típusai magasság szerint. Kivitel: alap oldalfal vagy ráépíthető magasító (AK); "
                    "kT / TT: kerettel, zárt profillal. Tömeg kg/folyóméterben.",
            "navigate": True, "table": ["Típus", "Magasság", "Kivitel", "Lemez", "kg/m"],
            "rows": {r[3]: [r[1], f"{r[2]} mm" if r[2] else "–", short(spec(r[5], "Felhasználás")) or usage(r[1]),
                            (spec(r[5], "Lemezvastagság [mm]") + " mm") if spec(r[5], "Lemezvastagság [mm]") else spec(r[5], "Falvastagság") or "–",
                            spec(r[5], "Tömeg [kg/m]") or spec(r[5], "Tömeg").replace(" kg/fm", "") or "–"]
                     for r in rows},
            "lengths": LENGTHS.get(sid, LIGHT),
            "leader": leader,
            "members": {r[3]: f"{r[1]} – {r[2]} mm" if r[2] else r[1] for r in rows},
        }
    OUT.write_text(json.dumps(fams, ensure_ascii=False, indent=1) + "\n")
    n = [k for k in fams if k.startswith("acel-oldalfal-")]
    print(len(n), "acél oldalfal család,", sum(len(fams[k]["members"]) for k in n), "típus")


if __name__ == "__main__":
    main()
