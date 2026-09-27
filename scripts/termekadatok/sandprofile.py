"""SAND Profile (DE) – a teljes PDF katalógus táblázataiból: profilrajz (Design oszlop),
cikkszám, szín, szorítási tartomány, kiszerelés.

Használat: python3 scripts/termekadatok/sandprofile.py
"""

import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import (clear_images, code_candidates, fetch, hu_value,  # noqa: E402
                    load_products, save_image, update_enrichment)

SUPPLIER = "Sand-Profile"
PDF = "https://www.sandprofile.com/media/gesamtkatalog_en.pdf"
LABELS = {
    "colour": "Szín", "color": "Szín", "clamping": "Szorítási tartomány", "sales unit": "Kiszerelés",
    "material": "Anyag", "hardness": "Keménység", "width": "Szélesség", "height": "Magasság",
    "thickness": "Vastagság", "temperature": "Hőállóság",
}
SKIP = ("design", "article", "minimum", "page")
COLOURS = {"black": "fekete", "white": "fehér", "grey": "szürke", "gray": "szürke", "silver": "ezüst", "red": "piros", "blue": "kék"}


def norm(c):
    return re.sub(r"[\s*]+", "", c or "").upper()


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def label_hu(label):
    low = clean(label).lower()
    unit = re.search(r"\[(.*?)\]", label or "")
    for k, v in LABELS.items():
        if low.startswith(k):
            return v + (f" [{unit.group(1)}]" if unit else "")
    return None


def render(page, rect):
    clip = pymupdf.Rect(rect) + (2, 2, -2, -2)
    zoom = min(6.0, 900 / max(clip.width, clip.height))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # fehér keret levágása
    bbox = Image.eval(img.convert("L"), lambda v: 255 if v < 245 else 0).getbbox()
    if bbox:
        pad = 12
        img = img.crop((max(bbox[0] - pad, 0), max(bbox[1] - pad, 0), min(bbox[2] + pad, img.width), min(bbox[3] + pad, img.height)))
    return img


def index_catalog(doc):
    """kód -> (oldal, design cella téglalap, {oszlop: érték})"""
    index = {}
    for pno, page in enumerate(doc):
        if not re.search(r"Article\s+reference", page.get_text()):
            continue
        for tab in page.find_tables().tables:
            data = tab.extract()
            if not data:
                continue
            header = [clean(h) for h in data[0]]
            if not any("article" in h.lower() for h in header):
                continue
            art_col = next(i for i, h in enumerate(header) if "article" in h.lower())
            for r, row in enumerate(data[1:], start=1):
                cells = tab.rows[r].cells
                design = cells[0] if cells and cells[0] else None
                arts = [a for a in (row[art_col] or "").split("\n") if a.strip()]
                for k, art in enumerate(arts):
                    specs = {}
                    for c, h in enumerate(header):
                        if c == art_col or any(h.lower().startswith(s) for s in SKIP):
                            continue
                        lab = label_hu(h)
                        vals = (row[c] or "").split("\n")
                        v = clean(vals[k] if k < len(vals) else vals[0] if vals else "")
                        if lab and v:
                            specs[lab] = COLOURS.get(v.lower(), hu_value(v))
                    index.setdefault(norm(art), (pno, design, specs))
    return index


def main():
    doc = pymupdf.open(stream=fetch(PDF), filetype="pdf")
    index = index_catalog(doc)
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        hit, code = None, None
        for c in code_candidates(p) + [m for m in re.findall(r"\b[A-E]\d\s?\d{3}(?:/\d)?", p["name"])]:
            if norm(c) in index:
                hit, code = index[norm(c)], c
                break
        if not hit:
            missing.append(p)
            continue
        pno, design, specs = hit
        clear_images(p["slug"])
        images = []
        if design:
            images.append(save_image(render(doc[pno], design), p["slug"]))
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": f"{PDF}#page={pno + 1}",
            "sourceTitle": clean(doc[pno].get_text().split("\n")[5] if doc[pno].get_text() else ""),
            "matchedCode": code,
            "specs": specs,
            "images": images,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(index)} cikk a katalógusban, {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>16}  {p['name']}")


if __name__ == "__main__":
    main()
