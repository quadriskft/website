"""RE-ALL (IT) – felépítmény- és kereskedelmi alumínium profilok.

A RE-ALL-nak nincs cikkszámonkénti termékoldala: a honlap termékcsoport-oldalai a katalógus
megfelelő fejezetét (PDF) adják. A lapok szkenneltek, minden termék saját keretes cellában van
(felül a keresztmetszet-rajz, alatta a táblázat: cikkszám, szálhossz, kg/fm).

A kép kivágása: a szkennelt lapon megkeressük a keret vonalait, a cikkszámot tartalmazó cellában
a legnagyobb vonalak közötti sáv a rajz – csak ezt vágjuk ki, így szomszédos termék nem kerül bele.

Ahol az automatikus cellakeresés nem ad rajzot (vagy a honlap nem érhető el), a MANUAL táblázat
kézzel ellenőrzött kivágást ad a Quadris-tól kapott katalógusfejezetekből (data/forras/reall_19_pedane.pdf,
data/forras/reall_21_furgoni.pdf); ezek adatai a lapokról leolvasva (Art., kg/ml, ötvözet a lap fejlécéből).

Használat: python3 scripts/termekadatok/reall.py
"""

import re
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "RE-ALL"
BASE = "https://www.re-all.it"
START = ["/it/prodotti/profili-alluminio-carrozzerie-veicoli-industriali.html", "/it/prodotti/profili-alluminio-commerciali-speciali.html",
         "/it/prodotti/accessori-alluminio.html", "/it/prodotti/lamiere-piastre-alluminio.html", "/it/prodotti/prodotti-alluminio.html"]
DPI = 200

# RE-ALL cikkszám (normalizálva) -> (helyi PDF, oldal, kivágás [pt], webes fejezet, műszaki adatok a lapról)
MANUAL = {
    "1900002": (ROOT / "data/forras/reall_19_pedane.pdf", 3, (84, 175, 364, 276), "/images/catalogo-pdf/2026/19.pdf",
                {"Ötvözet": "EN AW-6005 T6", "Tömeg [kg/fm]": "5,950", "Gyári szálhossz [mm]": "5000", "Szélesség": "200 mm", "Magasság": "40 mm"}),
    "2100025": (ROOT / "data/forras/reall_21_furgoni.pdf", 5, (84, 507, 364, 670), "/images/catalogo-pdf/2026/21.pdf",
                {"Ötvözet": "EN AW-6060 T6", "Tömeg [kg/fm]": "1,390", "Gyári szálhossz [mm]": "7500", "Magasság": "130 mm", "Szélesség": "58 mm"}),
}


def manual_drawing(pdf, pno, box):
    zoom = 240 / 72
    pix = pymupdf.open(pdf)[pno - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ys, xs = np.where(np.asarray(img.convert("L")) < 200)
    return img.crop((max(xs.min() - 16, 0), max(ys.min() - 16, 0), min(xs.max() + 16, img.width), min(ys.max() + 16, img.height)))


def norm(s):
    return re.sub(r"[\s.\-/]", "", s or "").upper()


def catalog_pdfs():
    seen, queue, pdfs = set(), list(START), []
    while queue and len(seen) < 150:
        u = queue.pop()
        if u in seen:
            continue
        seen.add(u)
        try:
            t = fetch(BASE + u).decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001
            continue
        for p in re.findall(r'href="(/images/catalogo-pdf/2026/[^"]+\.pdf)"', t):
            if p not in pdfs:
                pdfs.append(p)
        for h in set(re.findall(r'href="(/it/[^"#?]+\.html)"', t)):
            if re.search(r"profili-in-alluminio|profilati|accessori|lamiere|prodotti", h) and h not in seen:
                queue.append(h)
    return pdfs


def thin_lines(dark, min_run, max_width=3):
    """Vékony (≤ max_width px), hosszú egybefüggő sötét vonalak oszlop-pozíciói.
    A keretvonalak vékonyak; a profilrajz falai vastagok, azokat így kiszűrjük."""
    h, w = dark.shape
    best, cur = np.zeros(w, int), np.zeros(w, int)
    for y in range(h):
        cur = np.where(dark[y], cur + 1, 0)
        best = np.maximum(best, cur)
    cols = [x for x in range(w) if best[x] >= min_run]
    groups = []
    for x in cols:
        if groups and x - groups[-1][-1] <= 1:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [int(np.mean(g)) for g in groups if len(g) <= max_width]


def cell_drawing(page, word_rect):
    """A cikkszámot tartalmazó cella rajz-része (kép), vagy None."""
    zoom = DPI / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    dark = np.asarray(img.convert("L")) < 170
    cx, cy = (word_rect.x0 + word_rect.x1) / 2 * zoom, (word_rect.y0 + word_rect.y1) / 2 * zoom
    vx = thin_lines(dark, 300)
    left = max([x for x in vx if x < cx - 5], default=None)
    right = min([x for x in vx if x > cx + 5], default=None)
    if left is None or right is None or right - left < 120:
        return None
    band = dark[:, left + 4:right - 4]
    hy = thin_lines(band.T, int(band.shape[1] * 0.85))
    above = [y for y in hy if y < cy - 5]
    if len(above) < 2:
        return None
    # a kód fölötti keretvonalak között a legnagyobb rés a rajz
    h, top, bottom = max((above[i + 1] - above[i], above[i], above[i + 1]) for i in range(len(above) - 1))
    if h < 80:
        return None
    crop = img.crop((left + 5, top + 5, right - 5, bottom - 5))
    g = np.asarray(crop.convert("L")) < 200
    ys, xs = np.where(g)
    if len(xs) < 50 or ys.max() - ys.min() < 160:  # csak fejléc / táblázatsor került bele – nem rajz
        return None
    pad = 14
    return crop.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, crop.width), min(ys.max() + pad, crop.height)))


def row_specs(page, word_rect):
    """kg/fm a kóddal egy sorban; szálhossz(ak) a cellában a kód fölötti/alatti sorban."""
    words = page.get_text("words")
    specs = {}
    same = [w for w in words if abs((w[1] + w[3]) / 2 - (word_rect.y0 + word_rect.y1) / 2) < 4 and w[0] > word_rect.x1 and w[0] - word_rect.x1 < 140]
    kg = next((w[4] for w in sorted(same, key=lambda w: w[0]) if re.fullmatch(r"\d{1,2},\d{2,3}", w[4])), None)
    if kg:
        specs["Tömeg [kg/fm]"] = kg
    near = [w for w in words if abs(w[1] - word_rect.y0) < 40 and w[0] > word_rect.x0 - 10 and w[0] - word_rect.x1 < 90 and re.fullmatch(r"\d{4,5}", w[4])]
    lens = sorted({int(w[4]) for w in near if 1000 <= int(w[4]) <= 15000})
    if lens:
        specs["Gyári szálhossz [mm]"] = " / ".join(str(x) for x in lens)
    return specs


def main():
    pdfs = catalog_pdfs()
    docs = []
    for rel in pdfs:
        try:
            docs.append((rel, pymupdf.open(stream=fetch(BASE + rel), filetype="pdf")))
        except Exception as err:  # noqa: BLE001
            print("  pdf hiba:", rel, err)
    print(f"  RE-ALL katalógus: {len(docs)} fejezet")
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        code = norm(p["supplierCode"])
        if len(code) < 6:
            missing.append(p)
            continue
        hit = None
        for rel, doc in docs:
            for pno, pg in enumerate(doc):
                for w in pg.get_text("words"):
                    if norm(w[4]) == code:
                        hit = (rel, pno, pg, pymupdf.Rect(w[:4]))
                        break
                if hit:
                    break
            if hit:
                break
        if not hit:
            missing.append(p)
            continue
        rel, pno, pg, wr = hit
        clear_images(p["slug"])
        images = []
        drawing = cell_drawing(pg, wr)
        if drawing is not None:
            images.append(save_image(drawing, p["slug"], 1))
        specs = {"Ötvözet": "EN AW-6060 T6"} if "LEGA 6060" in pg.get_text() else {}
        specs.update(row_specs(pg, wr))
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": f"{BASE}{rel}#page={pno + 1}", "sourceTitle": f"RE-ALL katalógus {rel.rsplit('/', 1)[-1]}",
                                 "matchedCode": p["supplierCode"], "specs": specs, "images": images}
    for p in products:  # kézi kivágás a helyi katalógusból, ha az automatikus nem adott képet
        man = MANUAL.get(norm(p["supplierCode"]))
        if not man or enrichment.get(p["slug"], {}).get("images"):
            continue
        pdf, pno, box, rel, specs = man
        clear_images(p["slug"])
        e = enrichment.get(p["slug"]) or {"source": SUPPLIER, "sourceUrl": f"{BASE}{rel}#page={pno}", "sourceTitle": f"RE-ALL katalógus {rel.rsplit('/', 1)[-1]}",
                                          "matchedCode": p["supplierCode"], "specs": {}}
        e["specs"] = {**e["specs"], **specs}
        e["images"] = [save_image(manual_drawing(pdf, pno, box), p["slug"], 1)]
        enrichment[p["slug"]] = e
        if p in missing:
            missing.remove(p)
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés, {sum(1 for e in enrichment.values() if e['images'])} képpel")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
