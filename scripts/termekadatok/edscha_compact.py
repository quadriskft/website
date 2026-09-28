"""Edscha – Compact tolótető alkatrészei az Edscha „Ersatzteile Planenverdeck Compact” (2018/02) katalógusából
(data/forras/edscha_ersatzteilkatalog_compact_2018.pdf – a Quadris-tól kapott PDF).

Kiegészíti az edscha.py-t azokkal a tételekkel, amelyek a 2024-es nemzetközi katalógusban nem szerepelnek.
A legtöbb alkatrész csak összeállítási rajzon látszik (más elemekkel átfedve), ezért kép csak ott készül,
ahol a rajz önálló (ponyvagörgő), illetve ahol az alkatrész a rajzon hézaggal elválik a szomszédaitól
(végkocsik a 3. és 9. oldalon): ott a kivágásba belógó szomszédos elemeket (tetősín, másik végkocsi,
pozíciószám-karika) fehérrel lefedjük. A többinél a katalógus megnevezése és cikkszáma kerül az adatlapra.

Használat: python3 scripts/termekadatok/edscha_compact.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Edscha Compact"
PDF = ROOT / "data/forras/edscha_ersatzteilkatalog_compact_2018.pdf"
URL = "https://www.edschats.com"
# Quadris beszállítói kód -> (Edscha rendelési szám, oldal, kivágás [pt] vagy None, műszaki adatok)
ITEMS = {
    "735016": ("40 38 085 810", 7, (466, 226.6, 512, 257.5),
               {"Megnevezés (gyári)": "Seitenplanenroller ohne Clip – oldalponyva-görgő klip nélkül", "Rendszer": "Edscha Compact / CS-Lite"}),
    "4069000940": ("40 69 000 940", 9, (248, 215, 477, 390), {"Megnevezés (gyári)": "Endlaufwagen Standard – végkocsi, normál", "Rendszer": "Edscha Compact"}),
    "4069002960": ("40 69 002 960", 3, (167, 194, 376, 357), {"Megnevezés (gyári)": "Endlaufwagen Compact small – végkocsi, keskeny", "Rendszer": "Edscha Compact"}),
    # a 2024-es katalógusban külön képpel szerepel (edscha.py) – ez csak tartalék, ha ott nem találná
    "69004670": ("40 69 004 670", 12, None, {"Megnevezés (gyári)": "Standardspriegel-Festdach inkl. Klammerprofil – fix tetős kereszttartó szorítóprofillal",
                                             "Rendszer": "Edscha Compact Fix", "Felépítményszélesség": "2550 mm"}),
}

# kitakarandó területek [pt]: sokszög (pontlista) vagy kör ("kor", x, y, sugár)
BLANKS = {
    # 9. oldal, 2. poz.: balra-fent a 1. poz. végkocsi rúdja/konzolja és a tetősín vége, jobbra-fent a „2” karika
    "4069000940": [[(240, 205), (402, 205), (402, 226), (250, 300), (240, 300)], ("kor", 455, 209.3, 11.5)],
    # 3. oldal, 1. poz.: a tetősín vége és a keresztrudak (hézaggal elválnak a végkocsitól), a „1” karika
    "4069002960": [[(160, 190), (330, 190), (330, 209.4), (249.5, 195.8), (160, 225)], ("kor", 360, 184.5, 11)],
}


def render(page, box, blanks=()):
    zoom = 400 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(img)
    for b in blanks:
        if b[0] == "kor":
            _, x, y, r = b
            draw.ellipse([((x - r - box[0]) * zoom, (y - r - box[1]) * zoom), ((x + r - box[0]) * zoom, (y + r - box[1]) * zoom)], fill="white")
        else:
            draw.polygon([((x - box[0]) * zoom, (y - box[1]) * zoom) for x, y in b], fill="white")
    ys, xs = np.where(np.asarray(img.convert("L")) < 235)
    return img.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), min(xs.max() + 12, img.width), min(ys.max() + 12, img.height)))


def main():
    doc = pymupdf.open(PDF)
    existing = load_enrichment()
    enrichment, missing = {}, []
    for p in load_products("Edscha"):
        item = ITEMS.get((p["supplierCode"] or "").strip())
        other = existing.get(p["slug"], {})
        if not item or (other.get("images") and other.get("source") != SOURCE):
            if not item:
                missing.append(p)
            continue
        order_no, pno, box, specs = item
        clear_images(p["slug"])
        images = [save_image(render(doc[pno - 1], box, BLANKS.get(p["supplierCode"].strip(), ())), p["slug"], 1)] if box else []
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": f"{URL}#page={pno}", "sourceTitle": f"Edscha Compact alkatrész-katalógus 2018: {order_no}",
                                 "matchedCode": order_no, "specs": {"Cikkszám (gyári)": order_no, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
