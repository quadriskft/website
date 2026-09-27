"""FTS (F.T.S. Farina) – kiegészítés a 2024-es katalógusból (a webáruház után fut).

A webáruház csak tömeget és kiszerelést ad, a méretek a katalógus méretrajzain vannak.
A katalógusban minden cikk egy blokk: megnevezés (IT/EN), "Art. <kód>", tömeg, darab/doboz,
méretezett rajz és fotó. A blokkot az "Art." sorok alapján határoljuk (a következő cikk
megnevezéséig; egymás melletti cikkeknél hasábra bontva).

- Kép: a blokk (méretrajz + fotó) – csak akkor, ha más cikk kódja NEM került bele.
  Webes termékképnél a rajz a galéria végére kerül, webes találat nélkül ez lesz a kép.
- Műszaki adat: tömeg, kiszerelés, kivitel (horganyzott/inox…), ha a webről hiányzott.

Használat: python3 scripts/termekadatok/fts_katalogus.py   (a woocommerce.py FTS után)
"""

import re
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "FTS"
PDF = "https://www.fts-farina.it/wp-content/uploads/2023/11/FTS_CATALOGO_2024_low_compressed_compressed.pdf"
CODE = re.compile(r"[0-9]{6,8}(?:/[0-9A-Z]{1,3})?")
FINISH = [(r"zincat[oa] a caldo|hot galvani[sz]ed", "tűzihorganyzott"), (r"zincat[oa]|zinc plated", "horganyzott"),
          (r"inox|stainless", "rozsdamentes acél"), (r"grezz[oa]|raw", "nyers"), (r"verniciat[oa]|painted", "festett"),
          (r"dacromet", "dacromet bevonatú"), (r"cataforesi|cataphoresis", "kataforézis bevonatú"), (r"nero|black", "fekete")]


def arts(page):
    words = page.get_text("words")
    out = []
    for w in words:
        if w[4].startswith("Art"):
            codes = [x[4] for x in words if abs(x[1] - w[1]) < 3 and x[0] > w[0] and x[0] - w[2] < 220 and CODE.fullmatch(x[4])]
            if codes:
                out.append((pymupdf.Rect(w[:4]), codes))
    return out


def title_top(page, r):
    """A cikk megnevezésének (az "Art." fölötti 1–3 sor) teteje."""
    top = r.y0
    for w in page.get_text("words"):
        if r.y0 - 62 < w[1] < r.y0 and r.x0 - 6 < w[0] < r.x0 + 320:
            top = min(top, w[1])
    return top


def block(page, r, all_arts):
    W, H = page.rect.width, page.rect.height
    left, right = 30, W - 20
    for a, _ in all_arts:  # egymás mellett álló cikkek: hasábhatár középen
        if abs(a.x0 - r.x0) > 60 and abs(a.y0 - r.y0) < 260:
            mid = (a.x0 + r.x0) / 2
            if a.x0 < r.x0:
                left = max(left, mid)
            else:
                right = min(right, mid)
    below = [title_top(page, a) - 4 for a, _ in all_arts if a.y0 > r.y0 + 30 and left - 5 < a.x0 < right]
    return pymupdf.Rect(left, max(title_top(page, r) - 4, 96), right, min(below + [H - 28]))


def cuts_through(page, rect):
    """Átvág-e a blokk határa rajzot vagy képet (akkor félbevágott lenne a kép)."""
    for w in page.get_text("words"):  # a határon átlógó szöveg is vágást jelent
        wr = pymupdf.Rect(w[:4])
        if wr.height > wr.width * 1.5 or w[4].startswith("Rev."):  # függőleges lapszéli megjegyzés
            continue
        if wr.intersects(rect) and not pymupdf.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1).contains(wr):
            return True
    boxes = [pymupdf.Rect(d["rect"]) for d in page.get_drawings()] + [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()]
    grown = pymupdf.Rect(rect.x0 - 3, rect.y0 - 3, rect.x1 + 3, rect.y1 + 3)
    for b in boxes:
        if b.width * b.height < 30 or b.width > page.rect.width * 0.8:
            continue  # apró jelek, oldalszéles díszcsíkok
        inter = b & rect
        if inter.is_empty:
            continue
        if not grown.contains(b) and inter.width * inter.height > 0.1 * b.width * b.height:
            return True
    return False


def render(page, rect):
    zoom = 170 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=rect, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    g = np.asarray(img.convert("L")) < 225
    ys, xs = np.where(g)
    if len(xs) < 100:
        return None
    return img.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), min(xs.max() + 12, img.width), min(ys.max() + 12, img.height)))


def block_specs(page, rect, art_rect, code):
    text = page.get_textbox(rect)
    specs = {}
    w = re.search(r"(\d+,\d{2,3})\s*kg", text)
    if w:
        specs["Tömeg"] = f"{w.group(1)} kg"
    pcs = re.search(r"(\d+)\s*Pcs", text, re.I)
    if pcs:
        specs["Kiszerelés"] = f"{pcs.group(1)} db/doboz"
    line = page.get_textbox(pymupdf.Rect(art_rect.x0, art_rect.y0 - 1, rect.x1, art_rect.y1 + 1))
    tail = line.split(code, 1)[-1] if code in line else ""
    for pat, hu in FINISH:
        if re.search(pat, tail, re.I):
            specs["Kivitel"] = hu
            break
    return specs


def main():
    doc = pymupdf.open(stream=fetch(PDF, timeout=600), filetype="pdf")
    index = {}
    for pno, pg in enumerate(doc):
        A = arts(pg)
        for r, codes in A:
            for c in codes:
                index.setdefault(re.sub(r"/.*$", "", c), (pno, r, c, A))
    print(f"  FTS katalógus: {doc.page_count} oldal, {len(index)} cikkszám")

    enrichment = load_enrichment()
    products = load_products(SUPPLIER)
    updates, stats = {}, {"kép": 0, "adat": 0, "új": 0, "kihagyott kép": 0}
    for p in products:
        cands = [re.sub(r"/.*$", "", c.strip()) for c in re.split(r"[,\s]+", p["supplierCode"] or "") if c.strip()]
        hit = next(((c, index[c]) for c in cands if c in index), None)
        if not hit:
            continue
        code, (pno, r, full, A) = hit
        pg = doc[pno]
        rect = block(pg, r, A)
        foreign = [c for _, cs in A for c in cs if c not in cs_of(A, r)]
        inside = pg.get_textbox(rect)
        codes_inside = set(re.findall(r"\b\d{8}\b", inside))
        clean = (not any(f in inside for f in foreign) and not cuts_through(pg, rect)
                 and len(codes_inside - {code}) <= 1          # táblázatos, több cikkes blokk
                 and art_size(pg, r) <= 13
                 and has_graphics(pg, rect))                    # nagybetűs, apró cellás oldalak
        entry = dict(enrichment.get(p["slug"], {}))
        is_new = not entry
        entry.setdefault("source", SUPPLIER)
        entry.setdefault("sourceUrl", f"{PDF}#page={pno + 1}")
        entry.setdefault("matchedCode", code)
        specs = dict(entry.get("specs") or {})
        for k, v in block_specs(pg, rect, r, full).items():
            specs.setdefault(k, v)
        entry["specs"] = specs
        images = list(entry.get("images") or [])
        if clean:
            img = render(pg, rect)
            if img is not None:
                if is_new:
                    clear_images(p["slug"])
                    images = [save_image(img, p["slug"], 1)]
                else:
                    images = [i for i in images if not i.endswith(f"-{9}.webp")] + [save_image(img, p["slug"], 9)]
                stats["kép"] += 1
        else:
            stats["kihagyott kép"] += 1
        entry["images"] = images
        updates[p["slug"]] = entry
        stats["adat"] += 1
        stats["új"] += is_new
    update_enrichment(updates)
    print(f"{SUPPLIER} katalógus: {stats}")


def has_graphics(page, rect):
    """Van-e a blokkban rajz vagy fotó (nem csak a megnevezés)."""
    area = sum((pymupdf.Rect(i["bbox"]) & rect).get_area() for i in page.get_image_info())
    lines = sum(1 for d in page.get_drawings() if rect.contains(pymupdf.Rect(d["rect"])))
    return area > 2000 or lines > 15


def art_size(page, r):
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                if sp["text"].strip().startswith("Art") and pymupdf.Rect(sp["bbox"]).intersects(r):
                    return sp["size"]
    return 0


def cs_of(A, r):
    return next(cs for rr, cs in A if rr == r)


if __name__ == "__main__":
    main()
