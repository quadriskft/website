"""Termékadatok beolvasása a beszállítói Excelből.

Használat:  python3 scripts/import_excel.py [data/forras/termekcsoportok.xlsx]

- Munkalap = fő termékcsoport (az "Összes termék" lapot kihagyjuk, az csak összesítő).
- "(N db)" végű sor = kategória a csoporton belül.
- Minden más sor termék: Megnevezés | Termékkód (beszállítói kód) | Beszállító.
- A megnevezés elején álló szám a Quadris saját cikkszáma.

Kimenet: src/data/catalog.json (a weboldal ebből épül) és
data/beszallitok.csv (beszállítónkénti összesítő a kikereséshez).
A beszállító neve és kódja CSAK belső adat, a weboldalon nem jelenik meg.
"""

import csv
import json
import re
import sys
import unicodedata
from collections import Counter, OrderedDict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/forras/termekcsoportok.xlsx"
SKIP_SHEETS = {"Összes termék"}
# Olyan sorok, amelyek se nem termékek, se nem kategóriák (megjegyzések)
IGNORED_ROWS = {"kinegrip"}

HEADER_RE = re.compile(r"\(\s*\d+\s*db\s*\)\s*$", re.IGNORECASE)
INTERNAL_CODE_RE = re.compile(r"^(\d{3,}(?:/[0-9A-Za-z]+)?)\s+(.*)$")

# A munkalapnevek rövidítéseinek kiírása a weboldalon
GROUP_TITLES = {
    "Ponyva oldalfal prof. és szegők": "Ponyvás oldalfal profilok és szegők",
    "Platós alkatrészek kiegészítők": "Platós alkatrészek és kiegészítők",
    "Hátsóajtók": "Hátsó ajtók és áthajtó rámpák",
    "Dobozos alkatr. és kiegészítők": "Dobozos felépítmény alkatrészek",
    "Speciális felépítmény alkatr.": "Speciális felépítmény alkatrészek",
    "Üvegszálas polyester": "Üvegszálas poliészter",
}
CATEGORY_TITLES = {
    "Aluminíum rakoncák": "Alumínium rakoncák",
    "Név alapján hozzáadva (nem szerepelt a listán)": "Felépítmény készletek",
    "Lowipan": "Rétegelt lemezek",
    "Sandprofil": "Egyéb kéder- és tömítőgumik",
}

# Beszállítónevek egységesítése (kis/nagybetű, elírások)
SUPPLIER_ALIASES = {
    "alcomet": "ALCOMET",
    "alcomat": "ALCOMET",
    "grupa kety": "Grupa Kęty",
    "exlabesa pl": "Exlabesa PL",
    "exlabesa es": "Exlabesa ES",
    "re-all": "RE-ALL",
    "reall": "RE-ALL",
    "takler": "Takler",
    "metra": "Metra",
    "allco": "Allco",
    "alco": "Allco",
    "italacc": "Ital Accessori",
    "ital accessori": "Ital Accessori",
    "alu-sv": "Alu-SV",
    "pommier": "Pommier",
    "pommier furgocar": "Pommier Furgocar",
    "furgocar": "Pommier Furgocar",
    "fudicar": "Pommier Furgocar",
    "cargoframes": "Cargoframes Czech",
    "cargoframes czech": "Cargoframes Czech",
    "dg": "DG",
    "edscha": "Edscha",
    "klöckner": "Klöckner",
    "emepe": "EMEPE",
    "decial alusv": "Alu-SV",
    "industrilas": "Industrilas",
}


def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "termek"


def normalize_supplier(name):
    name = clean(name)
    if not name:
        return ""
    return SUPPLIER_ALIASES.get(name.lower(), name)


def split_name(raw, supplier_code):
    """Quadris cikkszám leválasztása a megnevezés elejéről."""
    match = INTERNAL_CODE_RE.match(raw)
    if match:
        return match.group(1), clean(match.group(2))
    first, _, rest = raw.partition(" ")
    if supplier_code and first == supplier_code and rest:
        return "", clean(rest)
    return "", raw


def category_name(raw):
    name = clean(HEADER_RE.sub("", raw))
    return CATEGORY_TITLES.get(name, name)


def main():
    wb = openpyxl.load_workbook(SOURCE, data_only=True)
    groups = []
    products = []
    used_slugs = Counter()
    supplier_stats = OrderedDict()

    for ws in wb.worksheets:
        if ws.title in SKIP_SHEETS:
            continue
        group_name = GROUP_TITLES.get(clean(ws.title), clean(ws.title))
        group = {"slug": slugify(group_name), "name": group_name, "categories": []}
        current = None

        for row in ws.iter_rows(min_row=3, values_only=True):
            name, code, supplier = (list(row) + [None, None, None])[:3]
            name = clean(name)
            if not name or name.lower() in IGNORED_ROWS:
                continue
            code, supplier = clean(code), normalize_supplier(supplier)

            if not code and not supplier and HEADER_RE.search(name):
                current = {"slug": slugify(category_name(name)), "name": category_name(name), "products": []}
                group["categories"].append(current)
                continue
            if current is None:  # termék kategória nélkül
                current = {"slug": group["slug"], "name": group_name, "products": []}
                group["categories"].append(current)

            internal_code, title = split_name(name, code)
            title = title[:1].upper() + title[1:]
            base = slugify(f"{internal_code} {title}" if internal_code else title)
            used_slugs[base] += 1
            slug = base if used_slugs[base] == 1 else f"{base}-{used_slugs[base]}"

            products.append({
                "slug": slug,
                "code": internal_code,
                "name": title,
                "group": group["slug"],
                "category": current["slug"],
                "supplier": supplier,
                "supplierCode": code,
                "description": "",
                "specs": {},
                "images": [],
                "documents": [],
            })
            current["products"].append(slug)

            stats = supplier_stats.setdefault(supplier or "(nincs megadva)", {"count": 0, "withCode": 0, "groups": set()})
            stats["count"] += 1
            stats["withCode"] += 1 if code else 0
            stats["groups"].add(group_name)

        # üres kategóriák (pl. "4 szárnyú (0 db)") kihagyása
        group["categories"] = [c for c in group["categories"] if c["products"]]
        for c in group["categories"]:
            c["count"] = len(c.pop("products"))
        group["count"] = sum(c["count"] for c in group["categories"])
        groups.append(group)

    out = ROOT / "src/data/catalog.json"
    out.write_text(json.dumps({"groups": groups, "products": products}, ensure_ascii=False, indent=1) + "\n")

    # pontosvesszős, BOM-os CSV: a magyar Excel így helyesen nyitja meg
    with open(ROOT / "data/beszallitok.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Beszállító", "Termékek", "Ebből beszállítói kóddal", "Termékcsoportok"])
        for name, s in sorted(supplier_stats.items(), key=lambda kv: -kv[1]["count"]):
            w.writerow([name, s["count"], s["withCode"], "; ".join(sorted(s["groups"]))])

    print(f"{len(groups)} csoport, {sum(len(g['categories']) for g in groups)} kategória, {len(products)} termék")
    print(f"{len(supplier_stats)} beszállító -> data/beszallitok.csv")


if __name__ == "__main__":
    main()
