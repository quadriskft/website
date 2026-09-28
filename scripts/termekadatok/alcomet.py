"""ALCOMET (BG) – szabványos alumínium profilok (lapos, L, U, T, Z, H, zártszelvény, cső, rúd).

Forrás: a gyártó 2017-es szabványprofil-katalógusa (data/forras/alcomet_2017_laposprofilok.pdf) –
soronként méret, katalógusszám (500-xxxx) és folyómétertömeg. Párosítás:
1. a Quadris-kód számrésze = a katalógusszám (pl. UPR-02274 -> 500-2274),
2. kód nélkül a megnevezésből kiolvasott méret pontos egyezése azonos profiltípuson belül.
A katalógus méretét és tömegét adjuk a termékadatokhoz; ahol a megnevezésből hiányzott egy méret
(pl. cső falvastagsága), a keresztmetszet-rajz adatait is átadjuk (rajz) a nevbol.py-nak.

Használat: python3 scripts/termekadatok/alcomet.py
"""

import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from common import load_enrichment, load_products, update_enrichment  # noqa: E402
import nevbol  # noqa: E402

SUPPLIER = "ALCOMET"
PDF = Path(__file__).resolve().parents[2] / "data/forras/alcomet_2017_laposprofilok.pdf"
TYPES = [("Flat bars", "flat"), ("Unequal angles", "L"), ("Equal angles", "L"), ("Square tubes", "rhs"), ("Rectangular tubes", "rhs"),
         ("Round tubes", "tube"), ("T-profiles", "T"), ("U-profiles", "U"), ("Round bars", "rod"), ("Square bars", "sqbar"),
         ("Hexagonal bars", "hex"), ("Z-profiles", "Z"), ("H-profiles", "H")]
HU = {"flat": "lapos profil", "L": "L profil", "rhs": "zártszelvény", "tube": "kör cső", "T": "T profil", "U": "U profil",
      "rod": "köralakú rúd", "sqbar": "négyzetes rúd", "hex": "hatszög rúd", "Z": "Z profil", "H": "H profil"}
SIZE = re.compile(r"^(\d+(?:\.\d+)?(?:\s*[xх]\s*\d+(?:\.\d+)?)*)(.*)$")


def nums(s):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]


def catalog():
    doc = pymupdf.open(PDF)
    rows, kind = [], None
    for pno, pg in enumerate(doc):
        text = pg.get_text()
        for label, k in TYPES:
            if label.lower() in text.lower():
                kind = k
                break
        lines = [x.strip().replace("х", "x") for x in text.split("\n")]
        for i, ln in enumerate(lines):
            if not re.fullmatch(r"500-\d{3,4}", ln) or i == 0:
                continue
            size = lines[i - 1]
            m = SIZE.match(size)
            if not m or not re.search(r"\d", size):
                continue
            weight = lines[i + 1] if i + 1 < len(lines) and re.fullmatch(r"\d+\.\d+", lines[i + 1]) else None
            rows.append({"number": ln, "size": size.rstrip("*").strip(), "dims": nums(m.group(1)), "extra": m.group(2).replace("*", "").strip(),
                         "weight": weight, "kind": kind, "page": pno})
    return rows


def dims_match(kind, draw, row):
    if not draw or row["kind"] is None:
        return False
    k, a, b, t = (list(draw) + [0, 0, 0])[:4]
    rd = row["dims"]
    if k == "rhs" and row["kind"] == "rhs" and len(rd) == 3 and len(rd) == 3:
        return sorted(rd[:2]) == sorted([a, b]) and rd[2] == t
    if k == "flat" and row["kind"] == "flat" and len(rd) == 2:
        return sorted(rd) == sorted([a, b])
    if k == "L" and row["kind"] == "L" and len(rd) == 3:
        return sorted(rd[:2]) == sorted([a, b]) and rd[2] == t
    if k == "U" and row["kind"] == "U" and len(rd) == 4:
        return rd[1] == a and rd[0] == b and rd[3] == t
    if k == "tube" and row["kind"] == "tube" and len(rd) == 2:
        return rd[0] == a and (not t or rd[1] == t)
    if k == "rod" and row["kind"] == "rod" and len(rd) == 1:
        return rd[0] == a
    return False


def main():
    rows = catalog()
    by_num = {r["number"].split("-")[1]: r for r in rows}
    existing = load_enrichment()
    products = load_products(SUPPLIER)
    updates, missing = {}, []
    for p in products:
        code = re.sub(r"\D", "", (p["supplierCode"] or "").split("-")[-1]) if re.match(r"^[A-Z]{3}-\d+", p["supplierCode"] or "") else ""
        row = by_num.get(code.lstrip("0")) or by_num.get(code[-4:]) if code else None
        _, draw = nevbol.parse(p)
        if not row:
            cands = [r for r in rows if dims_match(None, draw, r)]
            want_r = re.search(r"\bR\s?\d", p["name"])
            cands.sort(key=lambda r: (bool(r["extra"]) != bool(want_r), r["extra"] != ""))
            row = cands[0] if cands else None
        if not row:
            missing.append(p)
            continue
        prev = existing.get(p["slug"]) or {}
        specs = dict(prev.get("specs") or {})
        specs["Szabványméret"] = f"{row['size']} mm"
        if row["weight"]:
            specs["Tömeg"] = f"{row['weight'].replace('.', ',')} kg/fm"
        specs.setdefault("Profil", HU.get(row["kind"], ""))
        entry = {**prev, "source": SUPPLIER, "sourceUrl": "", "sourceTitle": f"Alcomet {row['number']}", "matchedCode": row["number"],
                 "specs": {k: v for k, v in specs.items() if v}, "nevbolRajz": True}
        # hiányzó méret a rajzhoz (pl. cső falvastagsága)
        if row["kind"] == "tube" and len(row["dims"]) == 2 and (not draw or not draw[3]):
            entry["rajz"] = ["tube", row["dims"][0], 0, row["dims"][1]]
            entry["specs"]["Falvastagság"] = f"{nevbol.hu(row['dims'][1])} mm"
        updates[p["slug"]] = entry
    update_enrichment(updates, SUPPLIER)
    print(f"{SUPPLIER}: {len(updates)}/{len(products)} egyezés a katalógussal ({len(rows)} katalógussor)")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
