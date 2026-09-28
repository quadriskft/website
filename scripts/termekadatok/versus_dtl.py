"""Versus-Omega (BE) – Duo Trike Light alkatrészek a gyári alkatrész-katalógusból
(data/forras/versus_duo_trike_light.pdf, "DUO TRIKE LIGHT", Revision 01-10-19 – a Quadris-tól kapott PDF).

A versus.py a weboldal rendszeroldalairól csak a síneket/teljes rendszereket párosítja; az apró
alkatrészekhez (kereszttartók, csuklók, lezárók, görgők, szerelőkészletek) ez a PDF ad rajzot.
A katalógus lapjain minden alkatrész rajza mellett ott a gyári cikkszám (PART NR.); csak azokat a
Quadris-tételeket párosítjuk, amelyek megnevezésében/kódjában pontosan ez a cikkszám szerepel.
A kivágásokat kézzel ellenőriztük; ahol a rajz mellé nyúlik a cikkszám-táblázat vagy a logó,
azt a „kitakarás” téglalapok fehérrel lefedik. A Micro Trike (MT) saját cikkszámai nincsenek benne.

Forrásnév: "Versus DTL" (külön a versus.py "Versus" bejegyzéseitől, hogy ne töröljék egymást).

Használat: python3 scripts/termekadatok/versus_dtl.py
"""

import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Versus"
SOURCE = "Versus DTL"
PDF = ROOT / "data/forras/versus_duo_trike_light.pdf"
URL = "https://www.versus-omega.com/en/products/2/duo-trike-light"

# Versus cikkszám -> (PDF oldal, kivágás [pt], kitakarandó téglalapok [pt], műszaki adatok a lapról)
ITEMS = {
    "144-01006": (6, (130, 92, 474, 142), [], {"Megnevezés (gyári)": "Pull bar – Telescopic (teleszkópos elhúzó rúd)"}),
    "144-10001": (4, (540, 85, 780, 236), [(668, 200, 790, 240)], {"Megnevezés (gyári)": "Set accessories (alap tartozékkészlet)", "Kiszerelés": "készlet"}),
    "144-10022": (5, (389, 149, 483, 209), [], {"Megnevezés (gyári)": "Mounting set (a 193-14001 hátsó lezáró szerelőkészlete)", "Kiszerelés": "készlet"}),
    "144-10048": (3, (700, 280, 792, 358), [], {"Megnevezés (gyári)": "Mounting set roof stick fix (fix kereszttartó szerelőkészlete)",
                                                "Kiszerelés": "1 készlet / kereszttartó"}),
    "154-03013": (6, (102, 354, 240, 505), [], {"Megnevezés (gyári)": "Set mounting plates (rögzítőlemez-készlet)",
                                               "Kiszerelés": "a képen látható alkatrészek 4-szerese"}),
    "193-14001": (5, (66, 66, 500, 148), [], {"Megnevezés (gyári)": "Back beam (hátsó lezáró gerenda)", "Felépítményszélesség": "2550 mm",
                                              "Típus": "145Z", "Szerelőkészlet": "144-10022"}),
    "214-47201": (4, (46, 94, 482, 242), [(175, 200, 350, 242)], {"Megnevezés (gyári)": "Collapsible backside (összecsukható hátfal-keret)",
                                                                   "Felépítményszélesség": "2550 mm", "Változat": "L=52"}),
    "224-01001": (3, (362, 100, 795, 129), [], {"Megnevezés (gyári)": "Roof stick for sliding roof – Type SP (kereszttartó elhúzható tetőhöz)",
                                               "Felépítményszélesség": "2550 mm"}),
    "224-41211": (3, (362, 428, 795, 458), [], {"Megnevezés (gyári)": "Roof stick for fixed roof with tarpaulin cover – Type SP",
                                                "Felépítményszélesség": "2550 mm", "Rögzítés": "csavarokkal a sínhez (144-10048 készlettel)"}),
    "242-01004": (5, (605, 88, 736, 158), [], {"Megnevezés (gyári)": "Folding plate – Type 400 (csukló)", "Típus": "400"}),
    "242-01007": (5, (605, 88, 736, 158), [], {"Megnevezés (gyári)": "Folding plate – Type 700 (csukló)", "Típus": "700"}),
    "242-01065": (5, (605, 88, 736, 158), [], {"Megnevezés (gyári)": "Folding plate – Type 650 (csukló)", "Típus": "650"}),
    "242-14109": (5, (652, 340, 690, 507), [], {"Megnevezés (gyári)": "PVC pelmet (fekete PVC takaróprofil)", "Hossz": "9 m", "Szín": "fekete",
                                                "Anyag": "PVC"}),
    "262-05007": (6, (628, 159, 700, 306), [(644, 159, 700, 165), (652, 159, 700, 180.5)], {"Megnevezés (gyári)": "Pillar bracket – Plate (oszlopkonzol lemeze)"}),
    "264-01001": (6, (615, 86, 700, 154.5), [(628, 143, 644, 157)], {"Megnevezés (gyári)": "Pillar bracket – Bracket (oszlopkonzol)"}),
    "284-10024": (6, (343, 373, 488, 521), [], {"Megnevezés (gyári)": "Trike roller (görgő)"}),
    "324-47201": (4, (47, 286, 479, 440), [(130, 400, 370, 442)], {"Megnevezés (gyári)": "Collapsible backside for fixed roof with tarpaulin cover",
                                                                    "Felépítményszélesség": "2550 mm", "Változat": "L=100"}),
}


def part_number(p):
    m = re.search(r"\b(\d{3}-\d{5})\b", p["supplierCode"] or "") or re.match(r"V(\d{3}-\d{5})\b", p["name"])
    return m.group(1) if m else None


def render(page, box, blanks=()):
    zoom = 240 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for x0, y0, x1, y1 in blanks:
        img.paste((255, 255, 255), (int((x0 - box[0]) * zoom), int((y0 - box[1]) * zoom), int((x1 - box[0]) * zoom), int((y1 - box[1]) * zoom)))
    x0, y0, x1, y1 = img.convert("L").point(lambda v: 255 if v < 235 else 0).getbbox()  # fehér szegély levágása
    return img.crop((max(x0 - 16, 0), max(y0 - 16, 0), min(x1 + 16, img.width), min(y1 + 16, img.height)))


def main():
    doc = pymupdf.open(PDF)
    existing = load_enrichment()
    enrichment, missing = {}, []
    for p in load_products(SUPPLIER):
        slug = p["slug"]
        other = existing.get(slug, {})
        if other.get("images") and other.get("source") != SOURCE:
            continue  # már van képe más forrásból (pl. versus.py)
        nr = part_number(p)
        item = ITEMS.get(nr)
        if not item:
            missing.append(p)
            continue
        pno, box, blanks, specs = item
        clear_images(slug)
        enrichment[slug] = {"source": SOURCE, "sourceUrl": URL, "sourceTitle": f"Versus-Omega {nr}", "matchedCode": nr,
                            "specs": {"Cikkszám (gyártói)": nr, "Rendszer": "Duo Trike Light", **specs},
                            "images": [save_image(render(doc[pno - 1], box, blanks), slug, 1)]}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék a PDF-ből, {len(missing)} nincs benne")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>10}  {p['name']}")


if __name__ == "__main__":
    main()
