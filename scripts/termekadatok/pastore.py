"""Pastore & Lombardi (IT) – termékoldal a cikkszám alapján (a kereső a termékre irányít át).

Használat: python3 scripts/termekadatok/pastore.py
"""

import html
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, str(Path(__file__).parent))
from common import (clear_images, code_candidates, fetch, hu_value,  # noqa: E402
                    load_products, save_image, update_enrichment)

SUPPLIER = "Pastore"
BASE = "https://www.pastorelombardi.com"


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def lookup(code):
    try:
        page = fetch(f"{BASE}/eng/cerca?chiave={quote(code)}").decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"Product No\.:\s*</?[^>]*>?\s*([0-9A-Z]+)", page) or re.search(r"Product No\.:\s*([0-9A-Z]+)", text(page))
    if not m:
        return None
    t = text(page)
    number = re.search(r"Product No\.:\s*([0-9A-Z]+)", t)
    if not number or number.group(1).upper() != code.upper():
        return None
    title = re.search(r"<title>\s*(.*?)\s*-\s*Pastore", page, re.S)
    info = {
        "title": text(title.group(1)) if title else "",
        "version": (re.search(r"Version:\s*(.+?)\s+Unit weight", t) or [None, ""])[1],
        "weight": (re.search(r"Unit weight in grams:\s*([\d.,]+)", t) or [None, ""])[1],
        "pack": (re.search(r"Units per package:\s*(\d+)", t) or [None, ""])[1],
        "description": (re.search(r"Description:\s*(.+?)\s+Attachments", t) or [None, ""])[1],
        "images": [],
    }
    for pic in re.findall(r"imgresize\.php\?pic=([^&\"]+)", page):
        path = unquote(pic).replace("//", "/")
        if path.split("/")[-1].upper().startswith(code.upper()):
            url = f"{BASE}/scripts/imgresize.php?pic={quote(path)}&q=95&dim=1000"
            if url not in info["images"]:
                info["images"].append(url)
    # fotó (_F) előre, rajz (_D) utána
    info["images"].sort(key=lambda u: 0 if "_F." in u else 1 if "_S." in u else 2)
    return info


VERSIONS = {"S.S.": "rozsdamentes acél", "ZN": "horganyzott", "ZINC": "horganyzott", "BLACK": "fekete", "RAW": "nyers"}


def main():
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        info, code = None, None
        for c in code_candidates(p):
            info = lookup(c)
            if info:
                code = c
                break
        if not info:
            missing.append(p)
            continue
        specs = {}
        if info["version"]:
            specs["Kivitel"] = VERSIONS.get(info["version"].strip().upper(), hu_value(info["version"]))
        if info["weight"]:
            specs["Tömeg"] = f"{info['weight']} g"
        if info["pack"]:
            specs["Kiszerelés"] = f"{info['pack']} db/csomag"
        clear_images(p["slug"])
        images = []
        for n, url in enumerate(info["images"][:3], start=1):
            try:
                images.append(save_image(fetch(url), p["slug"], n))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", url, err)
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": f"{BASE}/eng/cerca?chiave={quote(code)}",
            "sourceTitle": info["title"],
            "sourceDescription": info["description"],
            "matchedCode": code,
            "specs": specs,
            "images": images,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>16}  {p['name']}")


if __name__ == "__main__":
    main()
