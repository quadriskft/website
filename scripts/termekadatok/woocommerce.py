"""WooCommerce webáruházas beszállítók (FTS, IndesCar) – a teljes termékadatbázis letöltése
a nyilvános Store API-n keresztül, majd egyeztetés a cikkszámok alapján.

Használat: python3 scripts/termekadatok/woocommerce.py [beszállító ...]
"""

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (clear_images, code_candidates, fetch, hu_value,  # noqa: E402
                    load_products, save_image, update_enrichment)

SITES = {
    "FTS": "https://www.fts-farina.it",
    "IndesCar": "https://indescar.com",
}

LABELS = {
    "peso": "Tömeg",
    "quantità per scatola": "Kiszerelés",
    "quantita per scatola": "Kiszerelés",
    "cantidad por caja": "Kiszerelés",
    "materiale": "Anyag",
    "material": "Anyag",
    "finitura": "Felület",
    "acabado": "Felület",
    "dimensioni": "Méret",
    "medidas": "Méret",
    "dimensiones": "Méret",
    "portata": "Teherbírás",
    "carga": "Teherbírás",
    "lunghezza": "Hossz",
    "longitud": "Hossz",
    "diametro": "Átmérő",
    "diámetro": "Átmérő",
    "spessore": "Vastagság",
    "espesor": "Vastagság",
}

WORDS = [
    (r"\bgrezzo\b", "nyers"), (r"\bzincat[oa]\b", "horganyzott"), (r"\bgalvanizad[oa]\b", "horganyzott"),
    (r"\bverniciat[oa]\b", "festett"), (r"\bpintad[oa]\b", "festett"), (r"\bner[oa]\b", "fekete"),
    (r"\bnegr[oa]\b", "fekete"), (r"\binox\b", "rozsdamentes"), (r"\bacciaio\b", "acél"), (r"\bacero\b", "acél"),
    (r"\balluminio\b", "alumínium"), (r"\baluminio\b", "alumínium"), (r"\bpz\b", "db"), (r"\buds?\b", "db"),
    (r"\bdestra\b", "jobb"), (r"\bsinistra\b", "bal"), (r"\bderech[oa]\b", "jobb"), (r"\bizquierd[oa]\b", "bal"),
]


def text(s):
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s or "")
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")


def hu(s):
    s = re.sub(r"[ \t]+", " ", s).strip(" :–-")
    for pat, rep in WORDS:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)
    return hu_value(s)


def all_products(base):
    items, page = [], 1
    while True:
        raw = fetch(f"{base}/wp-json/wc/store/v1/products?per_page=100&page={page}")
        batch = json.loads(raw)
        if not batch:
            break
        items += batch
        page += 1
    return items


def norm(c):
    return re.sub(r"[\s.]+", "", str(c)).upper()


def item_codes(item):
    """A webáruház termék összes kódja: SKU (több kód kötőjellel), a névben és a leírásban szereplő kódok."""
    codes = set()
    for part in re.split(r"[\s,;/]+|(?<=\d)-(?=\d)", item.get("sku") or ""):
        if len(part) >= 3:
            codes.add(norm(part))
    blob = f"{item.get('name', '')} {item.get('short_description', '')} {item.get('description', '')}"
    for tok in re.findall(r"\b[A-Z]{0,4}\d{4,}[A-Z0-9]*\b", html.unescape(re.sub(r"<[^>]+>", " ", blob))):
        codes.add(norm(tok))
    return codes


def parse_specs(item, code):
    specs = {}
    short = item.get("short_description") or ""
    for m in re.finditer(r"<strong>\s*([^<:]+?)\s*:?\s*</strong>\s*:?\s*([^<\n]+)", short):
        label, value = m.group(1).strip(), text(m.group(2)).strip(" :–-")
        low = label.lower()
        if re.fullmatch(r"[A-Z0-9./-]+", label):  # változat sor: "<strong>45172110</strong> – Zincato"
            if norm(label) == code and value:
                specs["Kivitel"] = hu(value)
            continue
        key = next((hu_l for k, hu_l in LABELS.items() if low.startswith(k)), None)
        if key and value:
            specs[key] = hu(value)
    for attr in item.get("attributes") or []:
        name = (attr.get("name") or "").lower()
        key = next((hu_l for k, hu_l in LABELS.items() if name.startswith(k)), None)
        vals = ", ".join(t.get("name", "") for t in attr.get("terms") or [])
        if key and vals and key not in specs:
            specs[key] = hu(text(vals))
    return specs


# a webáruház katalógusoldal-képei / táblázatai (nem termékfotók) – ezeket nem vesszük át
SKIP_IMAGE = re.compile(r"-00(-\d+)?\.|-tab(-\d+)?\.|catalog|catalogo|listino|^Tipo-", re.I)  # Tipo-*: beépítési rajz, a kép szélén levágva
# ellenőrzötten hibás párosítások (az Excel kódja egy másik webáruház-termékre mutat)
WRONG = {"25350100", "15270110"}
NOT_MATCH_SLUGS = {"152811-tir-zsaner-garnitura-horg"}


def run(supplier):
    base = SITES[supplier]
    items = all_products(base)
    index = {}
    for it in items:
        for c in item_codes(it):
            index.setdefault(c, it)

    products = load_products(supplier)
    enrichment = {}
    ok, missing = 0, []
    for p in products:
        hit, code = None, None
        if p["slug"] in NOT_MATCH_SLUGS:
            missing.append(p)
            continue
        for c in code_candidates(p):
            if len(norm(c)) < 6 or norm(c) in WRONG:  # rövid számok (pl. "2500", "3000") téves egyezést adnak
                continue
            if norm(c) in index:
                hit, code = index[norm(c)], norm(c)
                break
        if not hit:
            missing.append(p)
            continue
        clear_images(p["slug"])
        images = []
        srcs = [img for img in (hit.get("images") or []) if not SKIP_IMAGE.search(img["src"].rsplit("/", 1)[-1])]
        for n, img in enumerate(srcs[:4], start=1):
            try:
                images.append(save_image(fetch(img["src"]), p["slug"], n))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", img.get("src"), err)
        enrichment[p["slug"]] = {
            "source": supplier,
            "sourceUrl": hit.get("permalink"),
            "sourceTitle": html.unescape(hit.get("name", "")),
            "sourceDescription": re.sub(r"\s+", " ", text(hit.get("description"))).strip()[:2000],
            "matchedCode": code,
            "specs": parse_specs(hit, code),
            "images": images,
        }
        ok += 1
    update_enrichment(enrichment, supplier)
    print(f"{supplier}: {len(items)} webáruház termék, {ok}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>16}  {p['name']}")


if __name__ == "__main__":
    for s in sys.argv[1:] or SITES:
        run(s)
