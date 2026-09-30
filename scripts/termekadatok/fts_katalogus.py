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
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "FTS"
PDF = "https://www.fts-farina.it/wp-content/uploads/2023/11/FTS_CATALOGO_2024_low_compressed_compressed.pdf"
CODE = re.compile(r"[0-9]{6,8}(?:/[0-9A-Z]{1,3})?")
FINISH = [(r"zincat[oa] a caldo|hot galvani[sz]ed", "tűzihorganyzott"), (r"zincat[oa]|zinc plated", "horganyzott"),
          (r"inox|stainless", "rozsdamentes acél"), (r"grezz[oa]|raw", "nyers"), (r"verniciat[oa]|painted", "festett"),
          (r"dacromet", "dacromet bevonatú"), (r"cataforesi|cataphoresis", "kataforézis bevonatú"), (r"nero|black", "fekete")]


# TIR zsanér-alkatrészek a katalógusban: (fotó, méretrajz)
TIR = {
    "aluhaz": (("foto", 71, (294, 166, 400, 271)), ("rajz", 71, (364, 224, 552, 308), [(294, 166, 394, 247)])),       # 15275101
    "csap12": (("foto", 72, (356, 183, 552, 273)), ("rajz", 72, (328, 324, 568, 512))),       # 15276110
    "lapka30": (("foto", 72, (295, 593, 404, 667)), ("rajz", 72, (100, 656, 248, 732))),      # 15270110
    "bm_anya": (("foto", 76, (86, 215, 278, 356)), ("rajz", 76, (44, 352, 300, 444))),        # 1528…10 könnyű BM zsanér
    "bm_apa": (("foto", 76, (87, 554, 271, 688)), ("rajz", 76, (44, 692, 288, 808))),         # 1528…10 könnyű BM csap
    "lapka50": (("foto", 76, (383, 242, 513, 326)), ("rajz", 76, (372, 364, 542, 432))),      # 15279110
    "lapka70": (("foto", 76, (363, 573, 521, 675)), ("rajz", 76, (352, 696, 528, 780))),      # 15278110
    "nehez_anya": (("foto", 77, (207, 540, 457, 712)), ("rajz", 77, (48, 714, 304, 808))),    # 15291110 (H=20)
    "nehez_apa": (("foto", 78, (75, 185, 296, 348)), ("rajz", 78, (56, 352, 320, 464))),      # 15290110
    "lapka95": (("foto", 78, (363, 192, 544, 306)), ("rajz", 78, (340, 320, 580, 416))),      # 15284110
}


def garnitura(*parts):
    """Garnitúra képei: előbb az alkatrészek fotói, utána a méretrajzaik (a katalógus sorrendjében)."""
    return [TIR[k][0] for k in parts] + [TIR[k][1] for k in parts]


# a garnitúrák a zsanérral (anya), a csappal (apa) és a hozzájuk tartozó menetes lapkákkal (a katalógus párosítása szerint)
GARN_BM = garnitura("bm_anya", "lapka50", "bm_apa", "lapka70")

# Kézzel ellenőrzött kivágások (oldal, [x0, y0, x1, y1] pontban) azokhoz a termékekhez, amelyeknek a
# webáruházban nincs ép képe (pl. a Z-zárak beépítési rajza a webshopban a szélén le van vágva).
MANUAL = {  # ("foto", oldal, kép befoglaló téglalapja) = beágyazott fotó; ("rajz", oldal, téglalap) = vektoros méretrajz
    "357400-peremes-z-zar-400-mm-r-l": [("foto", 145, (332, 127, 567, 391)), ("rajz", 145, (48, 170, 142, 372))],
    "357401-peremes-z-zar-600-mm-r-l": [("foto", 148, (309, 127, 544, 391))],
    "357500-peremes-z-zar-500-mm-r-l": [("foto", 148, (309, 127, 544, 391))],
    "354400-nem-peremes-400-z-zar-r-l": [("foto", 146, (306, 127, 544, 399))],
    "354500-nem-peremes-500-mm-z-zar-r-l": [("foto", 146, (306, 127, 544, 399))],
    "354600-nem-peremes-600-mm-z-zar-r-l": [("foto", 146, (306, 127, 544, 399))],
    "354800-nem-peremes-800-mm-z-zar-r-l": [("foto", 146, (306, 127, 544, 399))],
    "351501-z-zar-ellendarab-csavarozhato": [("foto", 146, (181, 643, 247, 735))],
    "351502-z-zar-ellendarab-hegesztheto-nagy-30": [("foto", 146, (453, 451, 516, 533))],
    "351503-z-zar-ellendarab-hegesztheto-kicsi-20": [("foto", 146, (184, 468, 247, 534))],
    "352202-egymasbazarodo-zar-ellendarab": [("foto", 139, (442, 375, 567, 493))],
    "307155-alafutasgatlo-konzol-572-mm": [("foto", 268, (400, 147, 507, 547)), ("rajz", 268, (55, 192, 215, 345))],
    "308155-th-alafutasgatlo-konzol-710-mm": [("rajz", 268, (60, 503, 215, 805))],
    "828010-nyers-zsaner-bak-csavar": [("foto", 315, (358, 555, 473, 653))],
    "145010-50-mm-es-gombcsuklo-keszlet-3-5t": [("foto", 111, (51, 165, 292, 320))],
    # a Quadris kérésére: 352540 = TL35 alumínium oszlop (Art. 35250400), 352240 = TL35 sarokoszlop (Art. 35220400)
    "352540-egymasba-zarodo-z-zar-400": [("foto", 139, (303, 133, 431, 351))],
    "352240-ellendarabos-szego-400mm-r-l": [("foto", 139, (244, 363, 328, 589))],
    # TIR zsanérok (3-16 … 3-23. oldal): fotó + méretrajz; a garnitúra = zsanér (anya) + csap (apa)
    "152711-menetes-lapka-30mm": [TIR["lapka30"][0], TIR["lapka30"][1]],
    "152751-tir-zsaner-alu-haz": list(TIR["aluhaz"]),
    "152760-tir-zsaner-apa-resz-alu-hoz": list(TIR["csap12"]),
    "152761-tir-zsaner-garnitura-alu-hazas": garnitura("aluhaz", "csap12", "lapka30"),
    "152791-tir-zsaner-lapka-50mm": list(TIR["lapka50"]),
    "152781-tir-zsaner-lapka-70mm": list(TIR["lapka70"]),
    "152811-tir-zsaner-garnitura-horg": GARN_BM,
    "152814-tir-zsaner-garnitura-th": GARN_BM,
    "152815-tir-zsaner-garnitura-dc": GARN_BM,
    "152823-tir-zsaner-garnitura-rm": GARN_BM,
    "152815-1-tir-zsaner-anya": list(TIR["bm_anya"]),
    "152815-2-tir-zsaner-apa": list(TIR["bm_apa"]),
    "152901-tir-zsaner-garnitura-nagy-horg": garnitura("nehez_anya", "lapka70", "nehez_apa", "lapka95"),
}
GARN_BM_TXT = "BM könnyű TIR zsanér + 50 mm osztású menetes lapka, csap + 70 mm osztású menetes lapka"
# a katalógus adatai azokhoz, amelyeket a webáruház nem ad (a garnitúránál: zsanér + csap)
MANUAL_SPECS = {
    "152751-tir-zsaner-alu-haz": {"Anyag": "alumínium", "Kivitel": "eloxált, letört éllel", "Tömeg": "0,055 kg"},
    "152761-tir-zsaner-garnitura-alu-hazas": {"Tartalom": "alumínium zsanérház + horganyzott csap Ø12 + menetes lapka (30 mm osztás)"},
    "152811-tir-zsaner-garnitura-horg": {"Tartalom": GARN_BM_TXT, "Kivitel": "horganyzott"},
    "152815-tir-zsaner-garnitura-dc": {"Tartalom": GARN_BM_TXT, "Kivitel": "dacromet bevonatú"},
    "152814-tir-zsaner-garnitura-th": {"Tartalom": GARN_BM_TXT},
    "152823-tir-zsaner-garnitura-rm": {"Tartalom": GARN_BM_TXT},
    "152901-tir-zsaner-garnitura-nagy-horg": {"Tartalom": "BM nehéz TIR zsanér (H=20) + 70 mm osztású menetes lapka, csap + 95 mm osztású menetes lapka", "Kivitel": "horganyzott"},
    "352540-egymasba-zarodo-z-zar-400": {"Magasság": "400 mm", "Anyag": "alumínium (TL35)", "Kivitel": "jobb/bal"},
    "352240-ellendarabos-szego-400mm-r-l": {"Magasság": "400 mm", "Anyag": "alumínium (TL35 sarokoszlop)", "Kivitel": "jobb/bal"},
}
SKIP_SLUGS = set()


def manual_images(doc, slug):
    import ital_accessori as ia
    out = []
    for n, (kind, pno, box, *mask) in enumerate(MANUAL[slug], start=1):
        pg, rect = doc[pno - 1], pymupdf.Rect(*box)
        img = None
        if kind == "foto":
            cl = next((c for c in ia.image_clusters(pg, []) if abs(c[0].x0 - rect.x0) < 3 and abs(c[0].y0 - rect.y0) < 3), None)
            img = ia.extract(pg, cl) if cl else None
        if img is None:
            img = render(pg, rect, mask[0] if mask else ())
        if img is not None:
            out.append(save_image(img, slug, n))
    return out


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


def photo(page, rect, art_rect):
    """A blokkban lévő legnagyobb termékfotó, közvetlenül a PDF-ből. A katalógus a fotókat vízszintes
    csíkokban tárolja: a csíkokat összeillesztjük (ital_accessori.image_clusters / extract)."""
    import ital_accessori as ia
    best = None
    for cl in ia.image_clusters(page, []):
        b = cl[0]
        if b.width < 60 or b.height < 40 or (b & rect).get_area() < 0.8 * b.get_area():
            continue
        if best is None or b.get_area() > best[0].get_area():
            best = cl
    if not best:
        return None
    img = ia.extract(page, best)
    return img


def render(page, rect, mask=()):
    """A téglalap renderelése; a mask téglalapjai (pl. a rajzba belógó szomszédos fotó) fehérek lesznek."""
    zoom = 220 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=rect, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for m in mask:
        ImageDraw.Draw(img).rectangle([(m[0] - rect.x0) * zoom, (m[1] - rect.y0) * zoom, (m[2] - rect.x0) * zoom, (m[3] - rect.y0) * zoom], fill="white")
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
    products += [p for p in load_products() if p["slug"] in MANUAL and p not in products]  # pl. Ital Accessori-ként felvett TIR alkatrész
    updates, stats = {}, {"kép": 0, "adat": 0, "új": 0, "kihagyott kép": 0}
    for p in products:
        if p["slug"] in SKIP_SLUGS:
            continue
        if p["slug"] in MANUAL:
            entry = dict(enrichment.get(p["slug"], {}))
            entry.setdefault("source", SUPPLIER)
            entry.setdefault("sourceUrl", PDF)
            entry["specs"] = {**MANUAL_SPECS.get(p["slug"], {}), **(entry.get("specs") or {})}
            clear_images(p["slug"])
            entry["images"] = manual_images(doc, p["slug"])
            updates[p["slug"]] = entry
            stats["kép"] += 1
            continue
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
        images = [i for i in (entry.get("images") or []) if not i.endswith("-9.webp")]
        if not images:
            img = photo(pg, rect, r) if not any(f in inside for f in foreign) else None
            if img is not None and img.width >= 150:
                clear_images(p["slug"])
                images = [save_image(img, p["slug"], 1)]
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
