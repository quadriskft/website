"""Beszállítók TELJES kínálatának felvétele (nem csak az Excelben szereplő termékek).

Kimenet: src/data/bovitett.json – új termékcsoportok/kategóriák, termékek és az Excel
termékeinek átsorolása (moves). A weboldal (src/lib/catalog.js) összefésüli a
katalógussal. A képek a public/termekkepek alá kerülnek.

Használat: python3 scripts/termekadatok/teljes_kinalat.py [fuhrmann rubberselect gnc sandprofile]
"""

import html
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, fetch, save_image  # noqa: E402

OUT = ROOT / "src/data/bovitett.json"


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def load():
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {"groups": [], "categories": [], "renameGroups": {}, "products": [], "moves": {}}


def save(data):
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def replace_supplier(data, supplier, groups=(), categories=(), products=(), moves=None, rename=None):
    """Egy beszállító korábbi bejegyzéseinek cseréje az újakra."""
    data["products"] = [p for p in data["products"] if p.get("source") != supplier]
    data["groups"] = [g for g in data["groups"] if g.get("source") != supplier]
    data["categories"] = [c for c in data["categories"] if c.get("source") != supplier]
    data["moves"] = {k: v for k, v in data["moves"].items() if v.get("source") != supplier}
    for g in groups:
        data["groups"].append({**g, "source": supplier})
    for c in categories:
        data["categories"].append({**c, "source": supplier})
    data["products"] += [{**p, "source": supplier} for p in products]
    for k, v in (moves or {}).items():
        data["moves"][k] = {**v, "source": supplier}
    data["renameGroups"].update(rename or {})


def download_images(slug, urls, limit=3):
    clear_images(slug)
    out = []
    for n, url in enumerate(urls[:limit], start=1):
        try:
            out.append(save_image(fetch(url), slug, n))
        except Exception as err:  # noqa: BLE001
            print("  képhiba:", url, err)
    return out


def excel_products():
    return json.loads((ROOT / "src/data/catalog.json").read_text())["products"]


# ---------------------------------------------------------------- Fuhrmann

FU_BASE = "https://www.fuhrmann.at/de/"
FU_PAGES = ["stbw300", "stbw350", "stbw400", "stbw450", "stbw500", "stbw600", "stbw800", "stbw1000",
            "stbwfhd", "stbwfox", "stbwfoxl", "stbwfoxla", "stbwfoxln", "foxrock"]
FU_LABELS = {
    "blechstärke": "Lemezvastagság [mm]", "stärke": "Lemezvastagság [mm]",
    "breite oben": "Felső szélesség [mm]", "breite unten": "Alsó szélesség [mm]",
    "kg / m": "Tömeg [kg/m]", "gewicht": "Tömeg [kg/m]", "einsatzgebiet": "Felhasználás",
    "materialgüte": "Anyagminőség", "material": "Anyag", "produktionslängen": "Gyártási hossz",
    "längen": "Gyártási hossz [mm]", "höhe": "Magasság [mm]", "ausführung": "Kivitel",
}
FU_VALUES = {"Grundwand": "alap oldalfal", "Aufsatzwand": "magasító (ráépítő) oldalfal", "verzinkt": "horganyzott",
             "roh": "nyers", "grundiert": "alapozott", "bis": "–"}


def fu_desc(type_name):
    t = type_name.upper()
    if t.startswith("FOX-ROCK"):
        return "Extra erős acél oldalfal kőszállító billencsekhez, a legkeményebb igénybevételre."
    if t.startswith("FHD"):
        return "Heavy Duty acél oldalfal nehéz építőipari felépítményekhez."
    if t.startswith("FOX"):
        return "Heavy Duty acél oldalfal építőipari billencsekhez és platós felépítményekhez, nagy igénybevételre."
    if "HV" in t:
        return "Lézerhegesztett acél oldalfal homlok- és hátfalnak billencs és platós felépítményekhez, valamint oldalfalnak utánfutókhoz és könnyű teherautókhoz."
    return "Lézerhegesztett acél oldalfal nagy oldalnyomásra: billencs és platós teherautó-felépítményekhez, mezőgazdasági billencsekhez."


def fuhrmann():
    products, seen = [], set()
    for page in FU_PAGES:
        raw = fetch(FU_BASE + page + ".php").decode("utf-8", "ignore")
        heavy = not page.startswith("stbw") or page in ("stbwfhd", "stbwfox", "stbwfoxl", "stbwfoxla", "stbwfoxln")
        heavy = heavy and page != "stbw300"
        for table in re.findall(r"<table[^>]*>(.*?)</table>", raw, re.S):
            if "stahlbordwand/profile" not in table and "Type" not in table:
                continue
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
            imgs, types, attrs = [], [], []
            for r in rows:
                cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
                if not cells:
                    continue
                if "stahlbordwand/profile" in r:
                    imgs = [(re.search(r'src="([^"]+)"', c).group(1) if re.search(r'src="([^"]+)"', c) else None) for c in cells[1:]]
                    continue
                label = clean(cells[0])
                vals = [clean(c) for c in cells[1:]]
                if label.lower() in ("type", "typ"):
                    types = vals
                elif label and label.lower() not in ("datenblatt", "link", "beschreibung", "fotos"):
                    attrs.append((label, vals))
            for i, t in enumerate(types):
                t = t.replace('"', "").strip()
                if not t or not re.search(r"\d", t) and "ROCK" not in t.upper():
                    continue
                code = re.sub(r"\s+", " ", t)
                if code in seen:
                    continue
                seen.add(code)
                specs = {}
                for label, vals in attrs:
                    if i < len(vals) and vals[i]:
                        key = next((v for k, v in FU_LABELS.items() if label.lower().startswith(k)), label)
                        specs[key] = FU_VALUES.get(vals[i], vals[i])
                height = re.search(r"(\d{3,4})\s*$", code)
                if height and "Magasság [mm]" not in specs:
                    specs["Magasság [mm]"] = height.group(1)
                img = imgs[i] if i < len(imgs) else None
                slug = "acel-oldalfal-" + slugify(code)
                products.append({
                    "slug": slug, "code": code, "name": f"Acél oldalfal {code}" + (" mm" if height else ""),
                    "group": "acel-profilok",
                    "category": "heavy-duty-acel-oldalfalak" if heavy else "lezerhegesztett-acel-oldalfalak",
                    "specs": specs, "description": fu_desc(code),
                    "imageUrls": [FU_BASE + img] if img else [], "sourceUrl": FU_BASE + page + ".php",
                })
    for p in products:
        p["images"] = download_images(p["slug"], p.pop("imageUrls"))
    # az Excel HV/HVAK stb. oldalfalai ugyanezek a Fuhrmann típusok -> kategória áthelyezés
    moves = {}
    for ep in excel_products():
        if re.match(r"^(HV|HVAK|HVTT|HVAKKT|HVAKTT|B|BAK)\d*", ep["name"]) and ep["category"] == "acel-oldalfalak":
            moves[ep["slug"]] = {"group": "acel-profilok", "category": "lezerhegesztett-acel-oldalfalak"}
    cats = [
        {"group": "acel-profilok", "slug": "lezerhegesztett-acel-oldalfalak", "name": "Lézerhegesztett acél oldalfalak"},
        {"group": "acel-profilok", "slug": "heavy-duty-acel-oldalfalak", "name": "Heavy Duty acél oldalfalak"},
    ]
    return {"categories": cats, "products": products, "moves": moves}


RUNNERS = {"fuhrmann": ("Fuhrmann", fuhrmann)}


def main(names):
    data = load()
    for name in names or RUNNERS:
        supplier, fn = RUNNERS[name]
        res = fn()
        replace_supplier(data, supplier, res.get("groups", ()), res.get("categories", ()), res.get("products", ()),
                         res.get("moves"), res.get("rename"))
        print(f"{supplier}: {len(res.get('products', []))} termék, {len(res.get('moves') or {})} áthelyezés")
    save(data)


if __name__ == "__main__":
    main(sys.argv[1:])
