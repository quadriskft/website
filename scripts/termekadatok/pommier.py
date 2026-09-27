"""Pommier / Furgocar (FR) – zsanérok, zárak, tömítések, kilincsek, fogantyúk.

A pommier.eu termékoldalain egy "Reference" oszlopos táblázat sorolja fel a változatokat
(tömeg, kivitel, hossz…), a képek fájlneve a referencia. Csak akkor párosítunk, ha az Excel kódja a
REFERENCE oszlopban szerepel – a "For" (illeszkedik ehhez) oszlopban lévő kód egy másik termék.

Használat: python3 scripts/termekadatok/pommier.py
"""

import html
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, code_candidates, fetch, hu_label, hu_value, load_products, save_image, update_enrichment  # noqa: E402
from sitemap_kereso import sitemap_urls  # noqa: E402

BASE = "https://www.pommier.eu"
SUPPLIERS = ["Pommier", "Pommier Furgocar"]
SKIP_COLS = {"reference", "drawings", "for", "for use with", "compatible with"}
LABELS = {
    "weight": "Tömeg [kg]", "hand": "Kivitel", "length": "Hossz", "width": "Szélesség [mm]", "height": "Magasság [mm]",
    "thickness": "Vastagság [mm]", "diameter": "Átmérő [mm]", "material": "Anyag", "finish": "Felület", "colour": "Szín",
    "color": "Szín", "treatment": "Felületkezelés", "packaging": "Kiszerelés", "load": "Teherbírás", "hardness": "Keménység",
    "panel thickness": "Panelvastagság [mm]", "panel width": "Panelvastagság [mm]", "key": "Kulcs", "type": "Típus",
}
VALUES = [(r"\bRight\b", "jobbos"), (r"\bLeft\b", "balos"), (r"\bZinc[- ]plated\b", "horganyzott"), (r"\bStainless steel\b", "rozsdamentes acél"),
          (r"\bAluminium\b", "alumínium"), (r"\bBlack\b", "fekete"), (r"\bGr[ae]y\b", "szürke"), (r"\bWhite\b", "fehér"),
          (r"\bSteel\b", "acél"), (r"\bBrass\b", "sárgaréz"), (r"\bChrome[- ]plated\b", "krómozott"), (r"\bPolyurethane\b", "poliuretán")]


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def hu(v):
    for pat, rep in VALUES:
        v = re.sub(pat, rep, v, flags=re.I)
    return hu_value(v)


def label(h):
    low = h.lower().strip()
    return LABELS.get(low) or next((v for k, v in LABELS.items() if low.startswith(k)), None) or hu_label(h)


def parse(url):
    try:
        raw = fetch(url).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return {}
    m = re.search(r'<table[^>]*id="table-characteristics".*?</table>', raw, re.S)
    if not m:
        return {}
    table = m.group(0)
    heads = []
    for th in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S):
        tip = re.search(r'class="tooltip[^"]*">(.*?)</span>', th, re.S)
        heads.append(text(tip.group(1) if tip else th))
    title = text((re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S) or [None, ""])[1])
    imgs = [urljoin(url, s) for s in dict.fromkeys(re.findall(r'(?:src|data-src)="(/sites/default/files/pim/[^"]+\.(?:jpg|png|webp))"', raw))]
    out = {}
    for tr in re.findall(r'<tr data-id="([^"]+)">(.*?)</tr>', table, re.S):
        ref, row = tr
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        specs = {}
        for h, v in zip(heads, cells):
            if h.lower() in SKIP_COLS or not v or v.lower() in ("pdf", "stp", "pdf stp"):
                continue
            lab = label(h)
            if len(h.strip()) <= 2 or len(v.strip(" *")) == 0 or (lab == "Típus" and len(v) <= 2):
                continue  # rajzjelölés-oszlopok (A, B…) és üres jelölések
            if lab == "Hossz" and re.fullmatch(r"[\d.,]+", v):
                v = f"{v} m" if float(v.replace(",", ".")) < 50 else f"{v} mm"
            if lab:
                specs[lab] = hu(v)
        own = [u for u in imgs if ref.upper() in u.upper() and "LOGO" not in u.upper()]
        out[ref.upper()] = {"url": url, "title": title, "specs": specs, "images": own or [u for u in imgs if "LOGO" not in u.upper()][:2]}
    return out


def main():
    urls = [u for u in dict.fromkeys(sitemap_urls(f"{BASE}/sitemap.xml")) if "/en/en/all-our-products/" in u]
    index = {}
    with ThreadPoolExecutor(6) as ex:
        for part in ex.map(parse, urls):
            for ref, item in part.items():
                index.setdefault(ref, item)
    print(f"  Pommier: {len(urls)} oldal, {len(index)} referencia")
    for supplier in SUPPLIERS:
        products = load_products(supplier)
        enrichment, missing = {}, []
        for p in products:
            hit, code = None, None
            for c in code_candidates(p):
                c = re.sub(r"\s+", "", c).upper()
                cand = [c] + [r for r in index if re.fullmatch(re.escape(c) + r"[A-Z]{1,3}", r)]
                hit = next((index[r] for r in cand if r in index), None)
                if hit:
                    code = c
                    break
            if not hit:
                missing.append(p)
                continue
            clear_images(p["slug"])
            images = []
            for n, u in enumerate(hit["images"][:3], start=1):
                big = u.replace("/thumbs_380_380/", "/")
                for cand_u in (big, u):
                    try:
                        images.append(save_image(fetch(cand_u), p["slug"], n))
                        break
                    except Exception:  # noqa: BLE001
                        continue
            enrichment[p["slug"]] = {"source": supplier, "sourceUrl": hit["url"], "sourceTitle": hit["title"],
                                     "matchedCode": code, "specs": hit["specs"], "images": images}
        update_enrichment(enrichment, supplier)
        print(f"{supplier}: {len(enrichment)}/{len(products)} egyezés")
        for p in missing:
            print(f"  NINCS: {p['supplierCode'] or '-':>14}  {p['name']}")


if __name__ == "__main__":
    main()
