"""Ital Accessori (Komárno) – termékadatok és képek a teljes PDF katalógusból.

A katalógus: https://www.ital-accessori.sk/katalog/book/KOMP/
Minden terméknél: táblázat (megnevezés SK/EN, kód, műszaki adatok) és a
termék képe a táblázat vagy a kódfelirat mellett. A képet az oldalról vágjuk ki.

Használat: python3 scripts/termekadatok/ital_accessori.py
"""

import re
import sys

import pymupdf
from PIL import Image

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import (CACHE, IMAGE_DIR, code_candidates, fetch, hu_label, hu_value,  # noqa: E402
                    load_enrichment, load_products, save_enrichment, save_image)

SUPPLIER = "Ital Accessori"
PDF_URL = "https://www.ital-accessori.sk/katalog/book/KOMP/files/assets/common/downloads/publication.pdf"
CATALOG_URL = "https://www.ital-accessori.sk/katalog/book/KOMP/{page}/"


def open_pdf():
    path = CACHE / "ital_accessori_katalog.pdf"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print("PDF letöltése…")
        path.write_bytes(fetch(PDF_URL, cache=False, timeout=600))
    return pymupdf.open(path)


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def norm_code(s):
    return re.sub(r"[\s*]+", "", str(s or "")).upper()


def parse_table(rows):
    """Táblázat -> [(cím, {oszlop: érték}, kód)]"""
    out, title, labels = [], "", None
    for i, row in enumerate(rows):
        cells = [clean(c) if c is not None else None for c in row]
        filled = [c for c in cells if c]
        if not filled:
            continue
        first = cells[0] or ""
        if re.match(r"^k[óo]d", first, re.I):  # fejléc
            labels = [c or "" for c in cells]
            continue
        if labels and cells[0] is None and len(filled) >= 2:  # alfejléc (pl. B, L, R…)
            new = []
            for j, lab in enumerate(labels):
                sub = cells[j] if j < len(cells) else None
                new.append(f"{hu_label(lab) if lab else 'Méret'} {sub}" if sub else lab)
            labels = new
            continue
        if len(filled) == 1 and cells[0] and (len(cells) == 1 or all(c is None for c in cells[1:])):
            title = cells[0]
            continue
        if labels and cells[0]:
            specs = {}
            for j, val in enumerate(cells[1:], start=1):
                if val and j < len(labels) and labels[j]:
                    specs[hu_label(labels[j])] = hu_value(val)
            out.append((title, specs, norm_code(cells[0])))
    return out


def rect_distance(a, b):
    dx = max(b.x0 - a.x1, a.x0 - b.x1, 0)
    dy = max(b.y0 - a.y1, a.y0 - b.y1, 0)
    return (dx * dx + dy * dy) ** 0.5


def pick_image(page, code, table_rect, tables):
    """A termékhez tartozó kép téglalapja az oldalon."""
    W, H = page.rect.width, page.rect.height
    imgs = []
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"]) & page.rect
        if r.is_empty or r.width * r.height < 700:
            continue
        if r.width / max(r.height, 1) > 5:  # vízszintes díszcsík, fejléc
            continue
        if r.y1 < 95 or r.y0 > H - 70:  # fejléc / lábléc sáv
            continue
        if any(pymupdf.Rect(t).contains(r) for t in tables):
            continue
        imgs.append(r)
    if not imgs:
        return None
    # 1) kódfelirat a kép alatt (táblázaton kívül)
    for w in page.get_text("words"):
        if norm_code(w[4]) != code:
            continue
        wr = pymupdf.Rect(w[:4])
        if any(pymupdf.Rect(t).intersects(wr) for t in tables):
            continue
        above = [r for r in imgs if r.y1 <= wr.y0 + 4 and wr.y0 - r.y1 < 45 and min(r.x1, wr.x1) - max(r.x0, wr.x0) > -25]
        if above:
            return min(above, key=lambda r: (wr.y0 - r.y1) + abs((r.x0 + r.x1) / 2 - (wr.x0 + wr.x1) / 2) * 0.3)

    # 2) a táblázat melletti kép: közel legyen, függőlegesen fedje a táblázatot, és inkább nagyobb
    def score(r):
        d = rect_distance(r, table_rect)
        overlap = min(r.y1, table_rect.y1) - max(r.y0, table_rect.y0)
        return d + (0 if overlap > 0 else 35) - min(r.width * r.height, 40000) / 2000

    near = [r for r in imgs if rect_distance(r, table_rect) < 180]
    return min(near, key=score) if near else None


def render(page, rect, pad=1.5):
    clip = pymupdf.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad) & page.rect
    zoom = min(5.0, 1100 / max(clip.width, clip.height))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def main():
    doc = open_pdf()
    products = load_products(SUPPLIER)
    enrichment = load_enrichment()

    # kód -> oldal index (gyors szöveges előszűrés)
    wanted = {}
    for p in products:
        for c in code_candidates(p):
            wanted.setdefault(norm_code(c), []).append(p)
    page_text = [norm_code(" ".join(w[4] for w in pg.get_text("words"))) for pg in doc]
    word_sets = [set(norm_code(w[4]) for w in pg.get_text("words")) for pg in doc]

    found = {}
    for code, plist in wanted.items():
        pages = [i for i, ws in enumerate(word_sets) if code in ws]
        for i in pages:
            page = doc[i]
            tabs = page.find_tables().tables
            rects = [t.bbox for t in tabs]
            for t in tabs:
                for title, specs, row_code in parse_table(t.extract()):
                    if row_code != code:
                        continue
                    for p in plist:
                        if p["slug"] in found:
                            continue
                        found[p["slug"]] = dict(page=i, title=title, specs=specs, code=code, table=pymupdf.Rect(t.bbox), rects=rects)
            if all(p["slug"] in found for p in plist):
                break

    ok = 0
    for p in products:
        for old in IMAGE_DIR.glob(f"{p['slug']}-*.webp"):
            old.unlink()
        enrichment.pop(p["slug"], None) if enrichment.get(p["slug"], {}).get("source") == SUPPLIER else None
        hit = found.get(p["slug"])
        if not hit:
            continue
        page = doc[hit["page"]]
        entry = enrichment.get(p["slug"], {})
        entry.update({
            "source": SUPPLIER,
            "sourceUrl": CATALOG_URL.format(page=hit["page"] + 1),
            "sourceTitle": hit["title"],
            "matchedCode": hit["code"],
            "specs": hit["specs"],
        })
        r = pick_image(page, hit["code"], hit["table"], hit["rects"])
        if r is not None:
            entry["images"] = [save_image(render(page, r), p["slug"])]
        enrichment[p["slug"]] = entry
        ok += 1

    save_enrichment(enrichment)
    missing = [p for p in products if p["slug"] not in found]
    print(f"{SUPPLIER}: {ok}/{len(products)} termék megtalálva a katalógusban")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>14}  {p['name']}")


if __name__ == "__main__":
    main()
