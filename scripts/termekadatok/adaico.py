"""ADAICO (ES) – Magento webáruház: keresés a cikkszámra, majd a találatok termékoldalán
a változattáblában (Ref) vagy a termék SKU-jában keressük a kódot.

Használat: python3 scripts/termekadatok/adaico.py
"""

import html
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from common import (IMAGE_DIR, code_candidates, fetch, hu_label, hu_value,  # noqa: E402
                    load_products, save_image, update_enrichment)

SUPPLIER = "ADAICO"
BASE = "https://www.adaico.com/en"
SKIP_COLS = {"ref", "min. lot"}
UNITS = {"Weight": " kg", "Tömeg": " kg"}


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def variants(code):
    c = code.strip()
    out = [c, c.lstrip("0")]
    if c.isdigit() and len(c) < 8:
        out.append(c.zfill(8))
    return list(dict.fromkeys(out))


def search_page(query):
    return fetch(f"{BASE}/catalogsearch/result/?q={quote(query)}").decode("utf-8", "ignore")


def product_links(page):
    links = re.findall(r'href="(https://www\.adaico\.com/en/[^"]+\.html)" class="product photo product-item-photo"', page)
    return list(dict.fromkeys(links))[:8]


def parse_product(url, codes, page=None):
    page = page if page is not None else fetch(url).decode("utf-8", "ignore")
    sku = re.search(r'data-product-sku="([^"]+)"', page)
    title = re.search(r'<span class="base" data-ui-id="page-title-wrapper"[^>]*>(.*?)</span>', page, re.S)
    specs, matched = {}, None
    for row in re.findall(r"<tr id=\"row-\d+\".*?</tr>", page, re.S):
        ref = re.search(r'class="product-item-sku">\s*([^<\s]+)', row)
        if not ref or ref.group(1) not in codes:
            continue
        matched = ref.group(1)
        for label, cell in re.findall(r'<td data-th="([^"]+)"[^>]*>(.*?)</td>', row, re.S):
            if label.lower() in SKIP_COLS:
                continue
            alt = re.search(r'alt="([^"]+)"', cell)
            val = alt.group(1) if alt else text(cell)
            if val:
                lab = hu_label(label)
                specs[lab] = hu_value(val) + (UNITS.get(label, "") if not alt else "")
        break
    if not matched and sku and sku.group(1) in codes:
        matched = sku.group(1)
    if not matched:
        return None
    imgs = [u.replace("\\/", "/") for u in re.findall(r'"full":"([^"]+)"', page)]
    if not imgs:
        imgs = re.findall(r'og:image" content="([^"]+)"', page)
    return {"url": url, "title": text(title.group(1)) if title else "", "specs": specs,
            "images": list(dict.fromkeys(imgs)), "code": matched}


def lookup(code):
    codes = set(variants(code))
    page = search_page(code)
    # pontos találatnál a kereső maga a termékoldal
    canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', page)
    info = parse_product(canonical.group(1) if canonical else f"{BASE}/catalogsearch/result/?q={quote(code)}", codes, page)
    if info:
        return info
    for link in product_links(page):
        info = parse_product(link, codes)
        if info:
            return info
    return None


def main():
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        info = None
        for c in code_candidates(p):
            try:
                info = lookup(c)
            except Exception as err:  # noqa: BLE001
                print("  hiba:", c, err)
            if info:
                break
        if not info:
            missing.append(p)
            continue
        for old in IMAGE_DIR.glob(f"{p['slug']}-*.webp"):
            old.unlink()
        images = []
        for n, url in enumerate(info["images"][:3], start=1):
            try:
                images.append(save_image(fetch(url), p["slug"], n))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", url, err)
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": info["url"],
            "sourceTitle": info["title"],
            "matchedCode": info["code"],
            "specs": info["specs"],
            "images": images,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>16}  {p['name']}")


if __name__ == "__main__":
    main()
