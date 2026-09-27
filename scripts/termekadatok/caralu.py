"""Caralu (NL) – a nyilvános webshop katalógus bejárása és egyeztetés cikkszám alapján.

Katalógus: https://www.caralushop.nl/en/catalog/categories
A kategórialapokon csoportonként egy kép és alatta a változatok
(cikkszám, leírás, felület, hossz). A régi Caralu kódok ("1320 090-011")
a cikkszám helyett a modellszámot (1320.090) tartalmazzák.

Használat: python3 scripts/termekadatok/caralu.py
"""

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (clear_images, fetch, hu_value, load_products,  # noqa: E402
                    save_image, update_enrichment)

SUPPLIER = "Car-Alu"
BASE = "https://www.caralushop.nl"
ROOT_URL = f"{BASE}/en/catalog/categories"


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


TILES = {}  # régi modellszám (pl. "1245.000") -> (kép, kategória oldal, kategória neve)


def crawl():
    seen, queue, rows = set(), [ROOT_URL], []
    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        page = fetch(url).decode("utf-8", "ignore")
        crumbs = text(page[page.find("Catalogue"): page.find("Catalogue") + 300]) if "Catalogue" in page else ""
        for m in re.finditer(r'href="(https://www\.caralushop\.nl/en/catalog/categories/\d+)"', page):
            if m.group(1) not in seen:
                queue.append(m.group(1))
        for m in re.finditer(r'data-href="([^"]+/categories/\d+)".*?src="(/storage/\d+/(\d{4}\.\d{3})[^"]*\.png)".*?class="card-title">([^<]+)<', page, re.S):
            TILES.setdefault(m.group(3), (BASE + m.group(2), m.group(1), text(m.group(4))))
        # csoportok
        for block in re.split(r'<div id="\d+" class="row catalog-row', page)[1:]:
            img = re.search(r'href="(/storage/article_images/[^"]+)"', block)
            for art in re.split(r'<div id="article_\d+"', block)[1:]:
                cols = re.findall(r'<div class="col-sm-[^"]*border-end[^"]*">(.*?)</div>', art, re.S)
                cols = [text(c) for c in cols]
                if not cols or not re.match(r"^\d{6,}", cols[0]):
                    continue
                rows.append({
                    "article": cols[0],
                    "cols": cols[1:],
                    "image": BASE + img.group(1) if img else None,
                    "url": url,
                    "category": crumbs,
                })
    return rows


def norm(s):
    return re.sub(r"[\s._-]+", "", s or "").upper()


# Régi Caralu kódok (a webshopban már nem szerepelnek) -> mai cikkszám, megnevezés és méret alapján
# kiválasztva. Csak az egyértelmű eseteket párosítjuk.
MANUAL = {
    "1165 000-001": "1010477-TZ1-5000",   # lépcső sarokprofil 20 mm, eloxált (TRAPKANT 20mm + NEUS)
    "1305 115-000": "1011218-ONB-5000",   # esőcsatorna mini (GOOTLIJST 23x5x18x12,5)
    "1317 250-000": "1011356-ONB-7000",   # belga "h" szegő 25 mm natúr (az eloxált párja 1011356-TZ2)
    "1317 260-011": "1011357-TZ2-7000",   # tömítéses ajtószegő 25 mm eloxált (AANSLAGPROFIEL 25mm)
    "2460 060-000": "1021543-R50",        # tömítés az ajtószegő profilhoz (RUBBER TBV AANSLAGPROFIEL)
    "Q8037": "1012515-ZWART-3000",        # 25 mm kefe (STRIPBORSTEL 25mm) – a profil a Q8033
}


def main():
    rows = crawl()
    by_article = {norm(r["article"]): r for r in rows}
    products = load_products(SUPPLIER)
    enrichment = {}
    ok, missing = 0, []
    for p in products:
        code = p["supplierCode"] or ""
        manual = MANUAL.get(code) or next((v for k, v in MANUAL.items() if p["name"].startswith(k)), None)
        hit = by_article.get(norm(manual)) if manual else by_article.get(norm(code))
        if not hit and code:
            # részleges egyezés: azonos alapszám (pl. 1012515-zwart-3000 -> 1012515-…)
            base = re.match(r"^(\d{7})", code.replace(" ", ""))
            if base:
                hit = next((r for r in rows if r["article"].startswith(base.group(1))), None)
        if not hit and code:
            # régi kódformátum: "1245 000-000" -> modell 1245.000 kategóriaképe
            old = re.match(r"^(\d{4})\s?(\d{3})", code.strip())
            tile = TILES.get(f"{old.group(1)}.{old.group(2)}") if old else None
            if tile:
                hit = {"article": code, "cols": [tile[2]], "image": tile[0], "url": tile[1]}
        if not hit:
            missing.append(p)
            continue
        desc = " ".join(c for c in hit["cols"] if c)
        specs = {}
        m = re.search(r"L\s*=\s*([\d,.]+)\s*m", desc)
        if m:
            specs["Hossz"] = f"{m.group(1)} m"
        if re.search(r"anodi[sz]ed|TZ2|zilver", hit["article"] + desc, re.I):
            specs["Felület"] = "eloxált"
        elif re.search(r"mill finished|ONB|raw", hit["article"] + desc, re.I):
            specs["Felület"] = "natúr (nyers)"
        specs["Anyag"] = "alumínium" if re.search(r"alumin|profiel|profile", desc, re.I) else specs.get("Anyag", "")
        specs = {k: hu_value(v) for k, v in specs.items() if v}
        clear_images(p["slug"])
        images = []
        if hit["image"]:
            try:
                images.append(save_image(fetch(hit["image"]), p["slug"]))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", hit["image"], err)
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": hit["url"],
            "sourceTitle": desc[:300],
            "matchedCode": hit["article"],
            "specs": specs,
            "images": images,
        }
        ok += 1
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(rows)} webshop cikk, {ok}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>20}  {p['name']}")


if __name__ == "__main__":
    main()
