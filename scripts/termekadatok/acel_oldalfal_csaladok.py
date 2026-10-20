"""Acél oldalfalak a gyártó típusrendszere szerint termékcsaládokba (a Quadris kérésére): rendszerenként egy termék,
a termékoldalon táblázatban a típusok (alap / magasító / kerettel …) magasság szerint.

Rendeléskor hossz × darab sorok (a gyártói hosszakból választva, ill. a lézerhegesztetteknél 500–13 500 mm).
Csoportok a gyártó katalógusa szerint: lézerhegesztett B, BN / BNS, HV, HVN, BAK / BAKS, HVAK, kiegészítő profilok;
Heavy Duty FOXL B / HV, FOXL BN / HVN, FOXL BAK / HVAK, FHD, FOX B / HV, FOX-ROCK. A Quadris Excel-termékei (HV 400 …, „Acél oldalfal 2 mm”) a saját rendszerükben
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
# a gyártó katalógusa (2016_Prospekt_Stahlbordwaende_GE) szerinti típuscsoportok; a feltétel a szóköz nélküli,
# nagybetűs típuskódot kapja (pl. „BAKSKT400”); a kiegészítő profilokat a katalógus külön oldalon hozza
ZUSATZ = {"BAK300", "HVAK300", "HVKT350", "HV800", "HV900", "HVD400", "HVD500", "HVD600", "BTT600", "HVTT600",
          "HVAKTT600", "BAKTT600", "BTD940", "HVTD940", "HVOS350", "HVOS400"}
SYSTEMS = [  # (azonosító, név, feltétel)
    ("fox-rock", "Acél oldalfal FOX-ROCK (Heavy Duty)", lambda c: c.startswith("FOX-ROCK")),
    ("foxl-bak-hvak", "Acél oldalfal FOXL BAK / HVAK (Heavy Duty)", lambda c: re.match(r"FOXL(BAK|HVAK)\d", c)),
    ("foxl-bn-hvn", "Acél oldalfal FOXL BN / HVN (Heavy Duty)", lambda c: re.match(r"FOXL(BN|HVN)\d", c)),
    ("foxl-b-hv", "Acél oldalfal FOXL B / HV (Heavy Duty)", lambda c: re.match(r"FOXL(B|HV)\d", c)),
    ("fox-b-hv", "Acél oldalfal FOX B / HV (Heavy Duty)", lambda c: re.match(r"FOX(B|HV)\d", c)),
    ("fhd", "Acél oldalfal FHD (Heavy Duty)", lambda c: c.startswith("FHD")),
    ("kiegeszito", "Acél oldalfal – kiegészítő profilok (lézerhegesztett)", lambda c: c in ZUSATZ),
    ("bak-baks", "Acél oldalfal BAK / BAKS (lézerhegesztett)", lambda c: c.startswith("BAK")),
    ("hvak", "Acél oldalfal HVAK (lézerhegesztett)", lambda c: c.startswith("HVAK")),
    ("bn-bns", "Acél oldalfal BN / BNS (lézerhegesztett)", lambda c: c.startswith("BN")),
    ("hvn", "Acél oldalfal HVN (lézerhegesztett)", lambda c: c.startswith("HVN")),
    ("b", "Acél oldalfal B (lézerhegesztett)", lambda c: c.startswith("B")),
    ("hv", "Acél oldalfal HV (lézerhegesztett)", lambda c: c.startswith("HV")),
]


# gyártási hosszak a gyártói katalógus szerint: Heavy Duty 2500 / 5000 / 6000 mm (FHD: 2500 / 5000 mm),
# a lézerhegesztett profilok 0,5–13,5 m között tetszőleges hosszban
LIGHT = {"min": 500, "max": 13500, "hint": "Gyártási hossz: 500–13 500 mm között bármilyen hosszban (±1 mm). Több hossz is megadható."}
HEAVY = {"options": [2500, 5000, 6000], "hint": "Gyártási hosszak: 2500, 5000 vagy 6000 mm. Több hossz is megadható."}
LENGTHS = {"fhd": {"options": [2500, 5000], "hint": "Gyártási hosszak: 2500 vagy 5000 mm. Több hossz is megadható."},
           "fox-b-hv": HEAVY, "foxl-b-hv": HEAVY, "foxl-bn-hvn": HEAVY, "foxl-bak-hvak": HEAVY, "fox-rock": HEAVY}


def usage(code):
    """a gyártói adatlapon nem szereplő felhasználás a típusjelből: AK = ráépítő (magasító) oldalfal"""
    if code.upper().startswith("FOX-ROCK"):
        return "kőszállító billencs"
    return "magasító" if "AK" in code.upper() else "alap"


def dec1(v):
    """kg/m egy tizedesre, ahogy a gyártói katalógusban (10 -> 10,0; 13,4 / 16,8 marad)"""
    return re.sub(r"(?<![\d,])(\d+)(?![\d,])", r"\1,0", v) if v else v


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
    extended = extended + json.loads((ROOT / "data/kezi_termekek.json").read_text())["products"]
    fixes = json.loads((ROOT / "data/termek_javitasok.json").read_text())
    deleted = json.loads((ROOT / "data/torolt_termekek.json").read_text())
    extra = json.loads((ROOT / "src/data/termekadatok.json").read_text())
    items = []  # (rendszer, típuskód, magasság, slug, excel?, specs)
    for src, is_excel in ((excel, True), (extended, False)):
        for p in src:
            cat = (fixes.get(p["slug"], {}).get("move") or moves.get(p["slug"]) or {}).get("category", p["category"])
            if cat not in CATS or p["slug"] in deleted:
                continue
            sp = {**(p.get("specs") or {}), **(extra.get(p["slug"], {}).get("specs") or {}),
                  **(fixes.get(p["slug"], {}).get("specs") or {})}
            sp = {k: v for k, v in sp.items() if v is not None}
            code = (fixes.get(p["slug"], {}).get("code") or p.get("code") or sp.get("Típus") or "").strip()
            m = re.match(r"^([A-Za-z\-]+(?: ?(?:HEAVY|LIGHT))?)\s*(\d{3,4})?$", code)
            if not m:
                print("  nem értelmezhető típus:", p["slug"], code)
                continue
            key = code.replace(" ", "").replace('"', "").upper()
            sysid = next((sid for sid, _, cond in SYSTEMS if cond(key)), None)
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
        rows.sort(key=lambda i: (i[2], i[1].upper()))
        # a kártyán a legkisebb típus élesített 3D képe (a beszállítói termék; az Excel-termék képe rajz)
        leader = next((r[3] for r in rows if not r[4]), rows[0][3])
        fams[f"acel-oldalfal-{sid}"] = {
            "name": name, "label": "Típus", "title": "Rendelhető típusok",
            "note": "A rendszer típusai magasság szerint. Kivitel: alap oldalfal vagy ráépíthető magasító (AK); "
                    "kT / TT: kerettel, zárt profillal. Tömeg kg/folyóméterben.",
            "navigate": True, "table": ["Típus", "Magasság", "Kivitel", "Lemez", "kg/m"],
            "rows": {r[3]: [r[1], f"{r[2]} mm" if r[2] else "–", short(spec(r[5], "Felhasználás")) or usage(r[1]),
                            (spec(r[5], "Lemezvastagság [mm]") + " mm") if spec(r[5], "Lemezvastagság [mm]") else spec(r[5], "Falvastagság") or "–",
                            dec1(spec(r[5], "Tömeg [kg/m]") or spec(r[5], "Tömeg").replace(" kg/fm", "")) or "–"]
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
