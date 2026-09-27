"""Parlok (FI) – sárvédők, szerszámosládák, konzolok.

A Quadris-kód "J" + a Parlok RÉGI cikkszáma + "P" (pl. J5110185P -> 5110185).
A Parlok 2021-ben új cikkszámokra váltott; a régi->új átváltás a gyártó táblázatából jön
(New item numbers_Conversion list.xlsx), a termékcsaládok oldalain az új szám szerepel.

Használat: python3 scripts/termekadatok/parlok.py
"""

import html
import io
import re
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "PARLOK"
BASE = "https://www.parlok.com"
CONVERSION = f"{BASE}/assets/files/New%20item%20numbers_Conversion%20list.xlsx"
SECTIONS = ["mudguards", "supra-anti-spray", "brackets", "toolboxes", "tube-stays-and-bushings"]

# táblázat fejléce -> magyar műszaki adat
HEADERS = {
    "B": "Szélesség [mm]", "L": "Hossz [mm]", "R": "Ívsugár [mm]", "S": "Fesztáv [mm]", "H": "Magasság [mm]",
    "Width": "Szélesség [mm]", "Height": "Magasság [mm]", "Depth": "Mélység [mm]",
}

DESCRIPTIONS = {
    "mudguards": "Finn gyártású, nagy sűrűségű polietilén (PE-HD) sárvédő: kopásálló, vegyszerálló, könnyű, széles hőmérséklet-tartományban használható.",
    "supra-anti-spray": "Supra permetcsökkentő kivitelű PE-HD sárvédő: a belső kefesor csökkenti a felverődő vízpermetet (EU-típusjóváhagyás).",
    "toolboxes": "Zárható műanyag szerszámosláda tehergépjárműre és pótkocsira, vízálló tömítéssel. Szerelőkészlet külön rendelhető.",
    "brackets": "Sárvédő tartókonzol / felfogatás műszaki hőre lágyuló műanyagból, csőtartóhoz.",
    "tube-stays-and-bushings": "Sárvédő tartócső és persely a sárvédők felfogatásához.",
}
KIT_TEXT = "Szerelőkészlet a műanyag szerszámosláda alvázra / oldalvédőre rögzítéséhez."


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def conversion():
    wb = openpyxl.load_workbook(io.BytesIO(fetch(CONVERSION)), data_only=True)
    out = {}
    for row in wb.worksheets[0].iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            out[str(row[0]).strip()] = {"new": str(row[1]).strip(), "title": " ".join(str(x).strip() for x in row[2:4] if x)}
    return out


def family_pages():
    pages = []
    for section in SECTIONS:
        page = fetch(f"{BASE}/products/commercial-vehicles/{section}/").decode("utf-8", "ignore")
        for href in sorted(set(re.findall(rf'href="/?(products/commercial-vehicles/{section}/[^"\s]+)\s*"', page))):
            pages.append((section, f"{BASE}/{href.strip('/')}"))
    return pages


def parse_family(section, url):
    """Egy termékcsalád oldala: {új cikkszám: {specs, images, url, family}}."""
    page = fetch(url).decode("utf-8", "ignore")
    family = text((re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or [None, ""])[1])
    images = []
    for src in re.findall(r'src="/?(assets/images/tuotteet/[^"]+\.(?:png|jpe?g|webp))"', page):
        u = f"{BASE}/{src}"
        if u not in images:
            images.append(u)
    # fotó elöl, méretrajz (mittakuvat) a végén
    images.sort(key=lambda u: 1 if "mittakuva" in u.lower() else 0)
    items = {}
    # a táblázaton kívül, szövegben említett cikkszámok (pl. SL4 változat, szerelőkészlet)
    for code in set(re.findall(r"\b(1\d{5})\b", text(page))):
        items[code] = {"specs": {}, "images": images, "url": url, "family": family, "section": section}
    for table in re.findall(r"<table.*?</table>", page, re.S):
        heads = [text(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if not cells or not re.fullmatch(r"\d{6}", cells[0]):
                continue
            specs = {}
            for h, v in zip(heads[1:], cells[1:]):
                if h in HEADERS and v:
                    specs[HEADERS[h]] = v
            items[cells[0]] = {"specs": specs, "images": images, "url": url, "family": family, "section": section}
    return items


def main():
    conv = conversion()
    catalog = {}
    for section, url in family_pages():
        try:
            for code, item in parse_family(section, url).items():
                catalog.setdefault(code, item)
        except Exception as err:  # noqa: BLE001
            print("  oldalhiba:", url, err)
    print(f"  Parlok webes táblázatok: {len(catalog)} cikkszám")

    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        m = re.match(r"j(\d{7})p", p["slug"])
        old = m.group(1) if m else ""
        new = conv.get(old, {}).get("new") or (p["supplierCode"] if re.fullmatch(r"\d{6}", p["supplierCode"] or "") else "")
        item = catalog.get(new)
        title = conv.get(old, {}).get("title", "")
        dims = re.match(r"Mudguard (\d+)x(\d+) R(\d+)", title)
        if not item and dims:
            # a honlapról már lekerült méret: a White Line család adatai + a méret a megnevezésből
            base = next((v for v in catalog.values() if v["url"].endswith("/white-line-v")), None)
            if base:
                item = {**base, "specs": {"Szélesség [mm]": dims[1], "Hossz [mm]": dims[2], "Ívsugár [mm]": dims[3]}}
        box = re.match(r"Toolbox (\d+)", title)
        if not item and box:
            item = next((v for v in catalog.values() if v["url"].endswith(f"/{box[1]}-sl")), None)
        if item and not item["specs"] and dims:
            item = {**item, "specs": {"Szélesség [mm]": dims[1], "Hossz [mm]": dims[2], "Ívsugár [mm]": dims[3]}}
        if not item:
            missing.append((p, old, new))
            continue
        clear_images(p["slug"])
        saved = []
        for n, u in enumerate(item["images"][:3], start=1):
            try:
                saved.append(save_image(fetch(u), p["slug"], n))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", u, err)
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": item["url"],
            "sourceTitle": conv.get(old, {}).get("title") or item["family"],
            "matchedCode": new,
            "description": KIT_TEXT if title.startswith("Installation kit") else DESCRIPTIONS.get(item["section"], ""),
            "specs": item["specs"],
            "images": saved,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p, old, new in missing:
        print(f"  NINCS: régi {old or '-':>8} új {new or '-':>7}  {p['name']}")


if __name__ == "__main__":
    main()
