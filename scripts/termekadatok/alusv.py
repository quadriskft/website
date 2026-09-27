"""ALU-SV (CZ/SK) – keresés rendelési szám alapján, majd a termékoldal adatai és képe.

Használat: python3 scripts/termekadatok/alusv.py
"""

import html
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from common import (clear_images, code_candidates, fetch, hu_value,  # noqa: E402
                    load_products, save_image, update_enrichment)

SUPPLIER = "Alu-SV"
BASE = "https://www.alu-sv.com"
FIELDS = [("Material", "Anyag"), ("Finish", "Felület"), ("Weight", "Tömeg"), ("Length", "Hossz"),
          ("Width", "Szélesség"), ("Height", "Magasság"), ("Diameter", "Átmérő"), ("Thickness", "Vastagság"),
          ("Load capacity", "Teherbírás"), ("Unit of measure", "Mértékegység")]
FINISH = {"without": "natúr", "anodized": "eloxált", "anodised": "eloxált", "galvanized": "horganyzott", "painted": "festett"}


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def lookup(code):
    url = f"{BASE}/en/goods.ep/?action=search&keyword={quote(code)}&issue%5B%5D=number"
    page = fetch(url).decode("utf-8", "ignore")
    link = None
    for m in re.finditer(r'<a href="(/en/goods\.ep/[^"]+)"><strong>(.*?)</strong>\s*([^<]+)</a>', page):
        if m.group(3).strip().upper() == code.upper():
            link = m.group(1)
            title = text(m.group(2))
            break
    if not link:
        return None
    detail = fetch(BASE + link).decode("utf-8", "ignore")
    t = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", detail, flags=re.S))
    start = t.find("Ord. number:")
    block = t[start: t.find("Price", start)] if start >= 0 else ""
    specs = {}
    labels = [f for f, _ in FIELDS] + ["Ord. number"]
    for en, hu in FIELDS:
        m = re.search(rf"{en}:\s*(.+?)(?=\s+(?:{'|'.join(labels)}):|$)", block)
        if m:
            v = m.group(1).strip()
            specs[hu] = FINISH.get(v.lower(), hu_value(v))
    if specs.get("Mértékegység") == "m":
        specs["Mértékegység"] = "méter"
    imgs = []
    for src in re.findall(r'(?:src|href)="(/common/images/product/[^"]+)"', detail):
        if "/thumb/" in src or code.upper() not in src.upper():
            continue
        imgs.append(BASE + src)
    imgs.sort(key=lambda u: (0 if "/full/" in u else 1))
    return {"title": title, "url": BASE + link, "specs": specs, "images": list(dict.fromkeys(imgs))}


def main():
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        info, code = None, None
        for c in code_candidates(p):
            try:
                info = lookup(c)
            except Exception as err:  # noqa: BLE001
                print("  hiba:", c, err)
            if info:
                code = c
                break
        if not info:
            missing.append(p)
            continue
        clear_images(p["slug"])
        images = []
        # a "full" és a normál rajz ugyanaz a kép: csak az elsőt mentjük
        for url in info["images"][:1]:
            try:
                images.append(save_image(fetch(url), p["slug"]))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", url, err)
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": info["url"],
            "sourceTitle": info["title"],
            "matchedCode": code,
            "specs": info["specs"],
            "images": images,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>16}  {p['name']}")


if __name__ == "__main__":
    main()
