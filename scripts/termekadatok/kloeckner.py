"""Klöckner Metals Austria – alumínium lemezek, cseppmintás lemezek, zártszelvények, lapos profilok.

Forrás: a shop.kloeckner.at webáruház nyilvános OCC (SAP Commerce) API-ja. Termékcsaládonként lekérjük
az összes méretváltozatot és annak adatait (ötvözet, állapot, felület, minta, mintamagasság, szabvány,
méretek) és fotóit. A Quadris-tételt a megnevezésből kiolvasott méretekkel (és mintával / ötvözettel)
párosítjuk a változathoz; pontos változat hiányában a család fotója és közös adatai kerülnek a termékhez.

A fotók után a nevbol.py a saját méretezett rajzot fűzi a képekhez (a „fotok” mező alapján).

Használat: python3 scripts/termekadatok/kloeckner.py
"""

import io
import json
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import CACHE, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402
import nevbol  # noqa: E402

SUPPLIER = "Klöckner"
BASE = "https://shop.kloeckner.at"
OCC = BASE + "/occ/v2/kloeckner-at"
FAMILIES = {"sheet": "1011070", "elox": "1011071", "tread": "1011072", "square": "1011098", "rect": "1011100", "flat": "1011153"}
LABELS = {"Art des Musters": "Minta", "Zustand": "Állapot", "Oberfläche": "Felület", "Qualität/Güte": "Ötvözet", "Norm": "Szabvány",
          "Warzenhöhe": "Mintamagasság [mm]", "Herstellverfahren": "Gyártás", "Kantenradius": "Élrádiusz [mm]"}
VALUES = {"QUINTETT": "Quintett (öt csepp)", "DUETT": "Duett (két csepp)", "DIAMOND": "gyémánt", "MILL FINISH": "natúr (felületkezelés nélkül)",
          "ROLLED": "hengerelt", "EXTRUDED": "extrudált", "Gebeizt": "pácolt", "eloxiert": "eloxált", "ELOXIERT": "eloxált"}


def get(url):
    """OCC JSON lekérés (Accept: application/json – különben XML jön), gyorsítótárral."""
    key = CACHE / ("kloeckner_" + re.sub(r"[^A-Za-z0-9._-]+", "_", url)[-150:] + ".json")
    if key.exists():
        return json.loads(key.read_text())
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(data)
    return json.loads(data)


def variants(fam):
    d = get(f"{OCC}/products/{fam}/variants?fields=FULL&pageSize=400")
    out = []
    for p in d.get("products", []):
        try:
            v = get(f"{OCC}/products/{p['code']}?fields=FULL&lang=de")
        except Exception:  # noqa: BLE001
            continue
        feats = {}
        for c in v.get("classifications") or []:
            for f in c.get("features") or []:
                feats[f["name"]] = ", ".join(x["value"] for x in f.get("featureValues") or [])
        imgs = []
        for i in sorted(v.get("images") or [], key=lambda i: i.get("imageType") != "PRIMARY"):
            if i.get("format") == "superZoom" and i["url"] not in imgs:
                imgs.append(i["url"])
        out.append({"code": p["code"], "name": v.get("name"), "url": BASE + (v.get("url") or ""), "feats": feats, "images": imgs})
    return out


def f(x):
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return None


def is_photo(img):
    """A vonalas méretvázlatokat kihagyjuk – csak a valódi fotó kell."""
    g = np.asarray(img.convert("L"))
    return g.mean() < 232


def pick(kind, draw, name, fams):
    low = name.lower()
    if kind == "sheet":
        _, w, l, t = draw[:4]
        if "/" in name.split("x")[0]:  # cseppmintás / gyémánt
            pat = "DUETT" if "duett" in low else "DIAMOND" if "diamond" in low else "QUINTETT"
            fam = "tread"
        else:
            pat, fam = None, "elox" if "elox" in low else "sheet"
        alloy = re.search(r"AW-?\s*(\d{4})", name)
        best = None
        for v in fams[fam]:
            ft = v["feats"]
            if f(ft.get("Dicke")) != t or f(ft.get("Breite")) != w or f(ft.get("Länge")) != l:
                continue
            if pat and pat not in (ft.get("Art des Musters") or "").upper():
                continue
            if alloy and alloy.group(1) not in (ft.get("Qualität/Güte") or ""):
                continue
            best = v
            break
        family_rep = next((v for v in fams[fam] if not pat or pat in (v["feats"].get("Art des Musters") or "").upper()), None)
        return best, family_rep
    if kind == "rhs":
        _, a, b, t = draw[:4]
        fam = "square" if a == b else "rect"
        for v in fams[fam]:
            ft = v["feats"]
            dims = sorted(x for x in (f(ft.get(k)) for k in ("Kantenlänge", "Breite", "Höhe", "Kantenlänge1", "Kantenlänge2")) if x)
            if f(ft.get("Stärke") or ft.get("Wandstärke") or ft.get("Dicke")) == t and (dims == sorted([a, b]) or dims == [a]):
                return v, fams[fam][0] if fams[fam] else None
        return None, fams[fam][0] if fams[fam] else None
    if kind == "flat":
        _, a, b, _t = draw[:4]
        for v in fams["flat"]:
            ft = v["feats"]
            if sorted(x for x in (f(ft.get("Breite")), f(ft.get("Dicke") or ft.get("Stärke"))) if x) == sorted([a, b]):
                return v, fams["flat"][0]
        return None, fams["flat"][0] if fams["flat"] else None
    return None, None


def main():
    fams = {k: variants(c) for k, c in FAMILIES.items()}
    print("  Klöckner változatok:", {k: len(v) for k, v in fams.items()})
    existing = load_enrichment()
    updates, missing = {}, []
    for p in load_products(SUPPLIER):
        _, draw = nevbol.parse(p)
        if not draw:
            missing.append(p)
            continue
        exact, rep = pick(draw[0], draw, p["name"], fams)
        src = exact or rep
        if not src:
            missing.append(p)
            continue
        photos = []
        for u in src["images"]:
            try:
                img = Image.open(io.BytesIO(fetch(BASE + u))).convert("RGB")
            except Exception:  # noqa: BLE001
                continue
            if is_photo(img):
                photos.append(save_image(img, p["slug"], f"f{len(photos) + 1}"))
            if len(photos) == 2:
                break
        prev = existing.get(p["slug"]) or {}
        specs = dict(prev.get("specs") or {})
        feats = src["feats"]
        for de, hu in LABELS.items():
            val = feats.get(de)
            if not val or (not exact and de not in ("Norm", "Herstellverfahren", "Art des Musters")):
                continue
            val = VALUES.get(val, VALUES.get(val.upper(), val))
            if re.fullmatch(r"\d+\.\d+", val):
                val = val.replace(".", ",")
            if de == "Qualität/Güte" and re.fullmatch(r"\d{4}\w?", val):
                val = f"EN AW-{val}"
            specs[hu] = val
        updates[p["slug"]] = {**prev, "source": SUPPLIER, "sourceUrl": src["url"], "sourceTitle": f"{src['name']} {src['code']}",
                              "matchedCode": src["code"] if exact else "", "specs": specs, "fotok": photos, "images": photos + prev.get("images", [])[-1:],
                              "nevbolRajz": True}
    update_enrichment(updates, SUPPLIER)
    exact_n = sum(1 for u in updates.values() if u["matchedCode"])
    print(f"{SUPPLIER}: {len(updates)} termék fotóval ({exact_n} pontos méretváltozattal)")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
