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
from common import (CACHE, clear_images, code_candidates, fetch, hu_label, hu_value,  # noqa: E402
                    load_products, save_image, update_enrichment)

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


def image_clusters(page, tables):
    """Az oldal beágyazott képei; az egymáshoz érő (csempézett) képdarabok egy csoportba kerülnek.
    Visszaad: [(befoglaló téglalap, [(xref, bbox), ...])]"""
    H = page.rect.height
    parts = []
    for info in page.get_image_info(xrefs=True):
        r = pymupdf.Rect(info["bbox"]) & page.rect
        if r.is_empty or r.width * r.height < 40:
            continue
        if r.y1 < 95 or r.y0 > H - 70:  # fejléc / lábléc sáv
            continue
        if any(pymupdf.Rect(t).contains(r) for t in tables):
            continue
        parts.append((r, info["xref"], pymupdf.Rect(info["bbox"])))
    def tile_of(a, b):
        """Egy kép darabjai-e: érdemben átfedik egymást, vagy élben illeszkedő, azonos sávú csempék."""
        inter = a & b
        if not inter.is_empty and inter.width * inter.height > 0.2 * min(a.width * a.height, b.width * b.height):
            return True
        side_by_side = abs(a.y0 - b.y0) < 1.5 and abs(a.y1 - b.y1) < 1.5 and min(abs(a.x1 - b.x0), abs(b.x1 - a.x0)) < 1.5
        stacked = abs(a.x0 - b.x0) < 1.5 and abs(a.x1 - b.x1) < 1.5 and min(abs(a.y1 - b.y0), abs(b.y1 - a.y0)) < 1.5
        return side_by_side or stacked

    clusters = []
    for r, xref, bbox in parts:
        hit = [c for c in clusters if any(tile_of(r, m[1] & page.rect) for m in c[1])]
        rect, members = pymupdf.Rect(r), [(xref, bbox)]
        for c in hit:
            rect |= c[0]
            members += c[1]
            clusters.remove(c)
        clusters.append((rect, members))
    out = []
    for rect, members in clusters:
        if rect.width * rect.height < 700 or rect.width / max(rect.height, 1) > 5:
            continue
        out.append((rect, members))
    return out


def pick_image(page, code, table_rect, tables):
    """A termékhez tartozó kép (csoport) az oldalon: (téglalap, tagok) vagy None."""
    imgs = image_clusters(page, tables)
    if not imgs:
        return None
    # 1) kódfelirat a kép alatt (táblázaton kívül)
    for w in page.get_text("words"):
        if norm_code(w[4]) != code:
            continue
        wr = pymupdf.Rect(w[:4])
        if any(pymupdf.Rect(t).intersects(wr) for t in tables):
            continue
        above = [c for c in imgs if c[0].y1 <= wr.y0 + 4 and wr.y0 - c[0].y1 < 45 and min(c[0].x1, wr.x1) - max(c[0].x0, wr.x0) > -25]
        if above:
            return min(above, key=lambda c: (wr.y0 - c[0].y1) + abs((c[0].x0 + c[0].x1) / 2 - (wr.x0 + wr.x1) / 2) * 0.3)

    # 2) a táblázat melletti kép: közel legyen, függőlegesen fedje a táblázatot, és inkább nagyobb
    def score(c):
        r = c[0]
        d = rect_distance(r, table_rect)
        overlap = min(r.y1, table_rect.y1) - max(r.y0, table_rect.y0)
        return d + (0 if overlap > 0 else 35) - min(r.width * r.height, 40000) / 2000

    near = [c for c in imgs if rect_distance(c[0], table_rect) < 180]
    return min(near, key=score) if near else None


def pixmap_image(doc, xref):
    pix = pymupdf.Pixmap(doc, xref)
    if pix.colorspace and pix.colorspace.n not in (1, 3):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    mode = "RGBA" if pix.alpha else ("L" if pix.n == 1 else "RGB")
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    smask = doc.xref_get_key(xref, "SMask")
    if not pix.alpha and smask[0] == "xref":
        mask = pymupdf.Pixmap(doc, int(smask[1].split()[0]))
        m = Image.frombytes("L", (mask.width, mask.height), mask.samples).resize(img.size)
        img = img.convert("RGB")
        img.putalpha(m)
    return img


def extract(page, cluster):
    """A kép(ek) közvetlenül a PDF-ből: a rárajzolt méretvonalak, feliratok és szomszédos
    termékek nem kerülnek bele. Csempézett képnél a darabokat a helyükre illesztjük.
    Ha valamelyik darab nem kinyerhető (inline kép), marad a kivágás."""
    rect, members = cluster
    doc = page.parent
    if any(x <= 0 for x, _ in members):
        return render(page, rect)
    if len(members) == 1:
        return pixmap_image(doc, members[0][0])
    scale = min(5.0, 1100 / max(rect.width, rect.height))
    canvas = Image.new("RGBA", (round(rect.width * scale), round(rect.height * scale)), (255, 255, 255, 0))
    for xref, bbox in members:
        im = pixmap_image(doc, xref).convert("RGBA").resize((max(1, round(bbox.width * scale)), max(1, round(bbox.height * scale))))
        canvas.alpha_composite(im, (round((bbox.x0 - rect.x0) * scale), round((bbox.y0 - rect.y0) * scale)))
    return canvas


def render(page, rect, pad=1.5):
    clip = pymupdf.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad) & page.rect
    zoom = min(5.0, 1100 / max(clip.width, clip.height))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def main():
    doc = open_pdf()
    products = load_products(SUPPLIER)
    enrichment = {}

    # kód -> oldal index (gyors szöveges előszűrés)
    wanted = {}
    for p in products:
        for c in code_candidates(p):
            wanted.setdefault(norm_code(c), []).append(p)
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
        clear_images(p["slug"])
        hit = found.get(p["slug"])
        if not hit:
            continue
        page = doc[hit["page"]]
        entry = {}
        entry.update({
            "source": SUPPLIER,
            "sourceUrl": CATALOG_URL.format(page=hit["page"] + 1),
            "sourceTitle": hit["title"],
            "matchedCode": hit["code"],
            "specs": hit["specs"],
        })
        c = pick_image(page, hit["code"], hit["table"], hit["rects"])
        if c is not None:
            entry["images"] = [save_image(extract(page, c), p["slug"])]
        enrichment[p["slug"]] = entry
        ok += 1

    update_enrichment(enrichment, SUPPLIER)
    missing = [p for p in products if p["slug"] not in found]
    print(f"{SUPPLIER}: {ok}/{len(products)} termék megtalálva a katalógusban")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>14}  {p['name']}")


if __name__ == "__main__":
    main()
