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


# Kézzel ellenőrzött képkivágások (oldal index, téglalap pontban) azokhoz a tételekhez, amelyeknél a
# táblázat–kép automatikus párosítás nem működik (összetett oldalelrendezés, több rajz egymás mellett).
# A téglalapok csak az adott termék rajzát/fotóját fogják közre – szomszédos termék és felirat nélkül.
_CYL = {"Kivitel": "teleszkópos, gömbfejes (S típus)", "Max. üzemi nyomás": "200 bar"}
_CYLD = "Teleszkópos hidraulikus billenőhenger billenős felépítményekhez, homlokfali (kabin mögötti) beépítésre."
_HV = "Acél oldalfal profil billenős és platós felépítmények első/hátsó és oldalfalához."
MANUAL = {
    "hv400-acel-oldalfal-2-mm": ([(203, (193, 560, 252, 700))], {"Típus": "HV 400", "Magasság": "400 mm", "Falvastagság": "2,0 mm", "Tömeg": "10,9 kg/fm"}, _HV),
    "hv500-acel-oldalfal-2-mm": ([(203, (330, 561, 398, 700))], {"Típus": "HV 500", "Magasság": "500 mm", "Falvastagság": "2,0 mm", "Tömeg": "12,8 kg/fm"}, _HV),
    "hv600-acel-oldalfal-2-mm": ([(203, (399, 540, 472, 700))], {"Típus": "HV 600", "Magasság": "600 mm", "Falvastagság": "2,0 mm", "Tömeg": "14,3 kg/fm"}, _HV),
    "acel-oldalfal-2-mm-3": ([(203, (476, 492, 531, 700))], {"Típus": "HVTT 800", "Magasság": "800 mm", "Falvastagság": "2,0 mm", "Tömeg": "18,3 kg/fm"}, _HV),
    "acel-oldalfal-2-mm": ([(204, (238, 522, 287, 692))], {"Típus": "HVAKKT 400", "Magasság": "400 mm", "Falvastagság": "2,0 mm", "Tömeg": "12,0 kg/fm"},
                           "Acél oldalfal profil belső tömítőléccel, billenős és platós felépítményekhez."),
    "hvak600-acel-oldalfal-2-mm": ([(204, (368, 514, 432, 692))], {"Típus": "HVAK 600", "Magasság": "600 mm", "Falvastagság": "2,0 mm", "Tömeg": "15,2 kg/fm"},
                                   "Acél oldalfal profil belső tömítőléccel, billenős és platós felépítményekhez."),
    "acel-oldalfal-2-mm-2": ([(204, (498, 458, 566, 692))], {"Típus": "HVAKTT 800", "Magasság": "800 mm", "Falvastagság": "2,0 mm", "Tömeg": "19,0 kg/fm"},
                             "Acél oldalfal profil belső tömítőléccel, billenős és platós felépítményekhez."),
    "854043-rugos-ajtorogzito-elox-alu": ([(167, (38, 420, 268, 642))], {"Anyag": "alumínium", "Tömeg": "1,890 kg"}, ""),
    "302357-mgr-alafutasgatlo-konzol-710-mm": ([(613, (80, 300, 240, 478))], {"Méret (L×B×H)": "46×136×710 mm", "Felület": "Magnelis", "Tömeg": "2,073 kg"}, ""),
    "302340-viztartaly-18l": ([(578, (398, 98, 508, 198)), (578, (425, 200, 562, 288))],
                              {"Térfogat": "18 l", "Méret": "330×330×332 mm", "Anyag": "fekete műanyag", "Tömeg": "1,900 kg"}, ""),
    "302341-viztartaly-18l-szappan-adagolo": ([(578, (398, 98, 508, 198)), (578, (425, 200, 562, 288))],
                                              {"Térfogat": "18 l", "Méret": "330×330×332 mm", "Anyag": "fekete műanyag", "Tömeg": "1,900 kg"}, ""),
    "502287-3-fokos-letra-thorg-steges-tk": ([(630, (345, 478, 570, 592)), (630, (350, 625, 572, 758))],
                                             {"Fokok száma": "3", "L1": "1366 mm", "L2": "750 mm", "B": "420 mm", "H": "602 mm", "P": "960 mm",
                                              "Felület": "tűzihorganyzott", "Tömeg": "12,250 kg"}, ""),
    "j4535-sarfogo-lap-450x350-mm-felfogatas": ([(528, (152, 278, 250, 352))], {"Méret": "450×350 mm", "Anyag": "PVC, fekete"}, ""),
    "j5337-sarfogo-lap-530x370": ([(528, (390, 275, 498, 352))], {"Méret": "530×370 mm", "Anyag": "PVC, fekete"}, ""),
    "j6530-sarfogo-lap-650x300-felfogatas": ([(528, (380, 562, 507, 628))], {"Méret": "650×300 mm", "Anyag": "PVC, fekete"}, ""),
    "990160-reflex-tabla-565x140x0-8-ece70-01": ([(682, (345, 198, 562, 232))], {"Anyag": "alumínium, 0,8 mm", "Szabvány": "ECE 70-01", "Kiszerelés": "2 tábla"}, ""),
    "3052-munkahenger-11t-05x1230x152": ([(349, (262, 168, 425, 440))],
                                         {"Fokozatok": "5", "Löket": "1230 mm", "Rögzítés": "gömbfej (S típus)", "Max. üzemi nyomás": "200 bar",
                                          "Olajmennyiség": "9 l", "Tömeg": "46 kg"}, ""),
    "770065-n-force-takaro-doboz": ([(449, (150, 440, 262, 545))], {}, ""),
    "771094-n-force-bil-vezerlo": ([(448, (75, 290, 190, 505)), (448, (205, 110, 440, 250))],
                                   {"Működtetés": "pneumatikus, kézi", "Kivitel": "automatikus erőleadó (PTO) lekapcsolással"}, ""),
    "771101-n-force-bil-vezerlo-nem-kapcsolos": ([(448, (75, 290, 190, 505)), (448, (205, 110, 440, 250))],
                                                 {"Működtetés": "pneumatikus, kézi", "Kivitel": "erőleadó (PTO) vezérlés nélkül"}, ""),
    "3521695-billencs-elso-rakonca-400-mm-j": ([(317, (190, 195, 262, 345)), (317, (75, 165, 150, 320))],
                                              {"Magasság": "400 mm", "Oldalfal": "25 mm", "Vastagság": "36 mm", "Kivitel": "első, jobb"}, ""),
    "3521696-billencs-elso-rakonca-400-mm-b": ([(317, (190, 195, 262, 345)), (317, (75, 165, 150, 320))],
                                              {"Magasság": "400 mm", "Oldalfal": "25 mm", "Vastagság": "36 mm", "Kivitel": "első, bal"}, ""),
    "3521698-billencs-hatso-rakonca-400-mm-j-zseb": ([(317, (283, 180, 362, 345)), (317, (100, 595, 215, 705))],
                                                     {"Magasság": "400 mm", "Oldalfal": "25 mm", "Vastagság": "36 mm", "Kivitel": "hátsó, jobb, zsebbel"}, ""),
    "3521699-billencs-hatso-rakonca-400-mm-b-zseb": ([(317, (283, 180, 362, 345)), (317, (100, 595, 215, 705))],
                                                     {"Magasság": "400 mm", "Oldalfal": "25 mm", "Vastagság": "36 mm", "Kivitel": "hátsó, bal, zsebbel"}, ""),
    "352190-billencs-elso-rakonca-400-mm-j-b": ([(319, (48, 568, 106, 738))], {"Magasság": "405 mm", "Vastagság": "36 mm", "Kivitel": "első, kihúzható"}, ""),
    "3520902-billencs-koztes-rakonca-400-mm-zseb": ([(319, (104, 568, 164, 738)), (319, (118, 178, 238, 318))],
                                                    {"Magasság": "405 mm", "Vastagság": "36 mm", "Kivitel": "középső, kihúzható, zsebbel"}, ""),
    "3521903-billencs-hatso-rakonca-400-mm-j-zseb": ([(319, (192, 568, 246, 738)), (319, (118, 178, 238, 318))],
                                                     {"Magasság": "405 mm", "Vastagság": "36 mm", "Kivitel": "hátsó, jobb, kihúzható, zsebbel"}, ""),
    "3521904-billencs-hatso-rakonca-400-mm-b-zseb": ([(319, (192, 568, 246, 738)), (319, (118, 178, 238, 318))],
                                                     {"Magasság": "405 mm", "Vastagság": "36 mm", "Kivitel": "hátsó, bal, kihúzható, zsebbel"}, ""),
    "3092-munkahenger-8t-05x1040x124": ([(348, (262, 165, 462, 455))], {**_CYL, "Fokozatok": "5", "Löket": "1040 mm", "Olajmennyiség": "5 l", "Tömeg": "29 kg"}, _CYLD),
    "3093-munkahenger-8t-05x1190x124": ([(348, (262, 165, 462, 455))], {**_CYL, "Fokozatok": "5", "Löket": "1190 mm", "Olajmennyiség": "6 l", "Tömeg": "31 kg"}, _CYLD),
    "5023-munkahenger-05x1240x112-5t": ([(347, (200, 165, 432, 455))], {**_CYL, "Fokozatok": "5", "Löket": "1230 mm", "Olajmennyiség": "4,7 l", "Tömeg": "26 kg"}, _CYLD),
    "6004-munkahenger-6t-06x1245x124": ([(353, (195, 165, 432, 455))], {**_CYL, "Fokozatok": "6", "Löket": "1245 mm", "Olajmennyiség": "5,5 l", "Tömeg": "28,5 kg"}, _CYLD),
    "6008-munkahenger-9t-06x1470x152": ([(354, (245, 165, 468, 455))], {**_CYL, "Fokozatok": "6", "Löket": "1480 mm", "Olajmennyiség": "8,9 l", "Tömeg": "46 kg"}, _CYLD),
    "352578-sp36-600-mm-bill-elso-rakonca-j-b": ([(320, (96, 582, 143, 752))], {"Magasság": "605 mm", "Vastagság": "36 mm", "Kivitel": "első, jobb/bal, kihúzható"}, ""),
    "352572-sp36-600-mm-bill-kozepso-rakonca": ([(320, (144, 582, 204, 752))], {"Magasság": "605 mm", "Vastagság": "36 mm", "Kivitel": "középső, kihúzható"}, ""),
    "352571-sp33-600-mm-bill-hatso-rakonca-j-b": ([(320, (206, 582, 294, 752))], {"Magasság": "605 mm", "Vastagság": "36 mm", "Kivitel": "hátsó, jobb/bal, kihúzható"}, ""),
    "35800-max-800-koztes-rakonca": ([(52, (446, 288, 562, 408))],
                                     {"H": "800 mm", "H1": "180 mm", "H2": "620 mm", "Kivitel": "középső, zsebbel", "Felület": "kataforézis", "Tömeg": "11,90 kg"}, ""),
    "35880-max-800-elso-rakonca-j-b": ([(52, (438, 88, 564, 272))],
                                       {"H": "800 mm", "H1": "180 mm", "H2": "620 mm", "Kivitel": "első, keskeny, jobb/bal", "Felület": "kataforézis", "Tömeg": "6,80 kg"}, ""),
}


def manual_image(page, rect):
    import numpy as np
    pix = page.get_pixmap(clip=pymupdf.Rect(rect), dpi=220, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # a kivágásba belógó szöveg (pl. a leírás sorvége) eltávolítása – a méretszámok maradnak
    from PIL import ImageDraw
    z, r0 = 220 / 72, pymupdf.Rect(rect)
    draw = ImageDraw.Draw(img)
    for w in [w for w in page.get_text("words") if pymupdf.Rect(w[:4]).intersects(r0)]:
        if len(re.findall(r"[A-Za-zÁ-ž]", w[4])) >= 4:
            draw.rectangle([(w[0] - r0.x0 - 1) * z, (w[1] - r0.y0 - 1) * z, (w[2] - r0.x0 + 4) * z, (w[3] - r0.y0 + 1) * z], fill="white")
    a = np.asarray(img.convert("L")) < 235
    ys, xs = np.where(a)
    pad = 12
    return img.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.width), min(ys.max() + pad, img.height)))


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

    for p in load_products():
        if p["slug"] not in MANUAL:
            continue
        boxes, specs, desc = MANUAL[p["slug"]]
        entry = enrichment.get(p["slug"]) or {"source": SUPPLIER, "matchedCode": p["supplierCode"], "specs": {}}
        entry["sourceUrl"] = CATALOG_URL.format(page=boxes[0][0] + 1)
        entry.setdefault("sourceTitle", f"Ital Accessori katalógus {boxes[0][0] + 1}. oldal")
        entry["specs"] = {**entry.get("specs", {}), **specs}
        if desc:
            entry["description"] = desc
        entry["images"] = [save_image(manual_image(doc[pg], r), p["slug"], n) for n, (pg, r) in enumerate(boxes, 1)]
        if p["slug"] not in enrichment:
            ok += 1
        enrichment[p["slug"]] = entry
        found.setdefault(p["slug"], {})

    update_enrichment(enrichment, SUPPLIER)
    missing = [p for p in products if p["slug"] not in found]
    print(f"{SUPPLIER}: {ok}/{len(products)} termék megtalálva a katalógusban")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>14}  {p['name']}")


if __name__ == "__main__":
    main()
