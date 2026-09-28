"""MP Steel / Emepe Steel S.L. (ES) – rozsdamentes rúdzárak, zárkampók, rúdvezetők és zsanérok
a gyártó "Catalogo MP Steel 12/2016 r2" katalógusából (data/forras/mpsteel_katalogus_2016.pdf,
https://mpsteel.es/wp-content/uploads/2026/06/Catalogo-MP_Steel-12_2016_r2.pdf). A Quadris-nál "EMEPE" a beszállító.

A termékeket a gyártói cikkszám pontos egyezése alapján párosítottuk; a KIT/szett termékeknél a katalógus
kit-tételét, ill. az összetevők tételeit használtuk. A kivágások (fotó és méretrajz) kézzel ellenőrizve.
A katalógus szerint minden fémtermék anyaga AISI 304 (1.4301) rozsdamentes acél.

Nem szerepel a 2016-os katalógusban (ezért kimaradt): KLC-EX41, KLCB-EX41E, FEX27002
(a FEX27 002 + KLC-EX11 + KB1G szett főeleme).

Használat: python3 scripts/termekadatok/mpsteel.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "EMEPE"
SOURCE = "MP Steel"
PDF = ROOT / "data/forras/mpsteel_katalogus_2016.pdf"
URL = "https://mpsteel.es/wp-content/uploads/2026/06/Catalogo-MP_Steel-12_2016_r2.pdf"
INOX = {"Anyag": "rozsdamentes acél (AISI 304)"}

LEM1 = ("LEM1", 11, [(78, 108, 152, 158), (192, 136, 276, 220)],
        {"Megnevezés (gyári)": "Leva empotrar LEM1 / Recessed cam – zárkampó süllyesztett rúdzárhoz", **INOX,
         "Rúdfurat": "Ø16,1 mm (Ø16 mm-es rúdhoz)", "Méret": "61 × 23,5 mm", "Vastagság": "9,7 mm", "Tömeg": "47 g"})
CEM1 = ("CEM1", 11, [(316, 94, 446, 178), (450, 128, 560, 230)],
        {"Megnevezés (gyári)": "Cremona empotrar CEM1 / Recessed keeper – zárfészek (ellendarab) süllyesztett rúdzárhoz", **INOX,
         "Méret": "110 × 30 mm", "Magasság": "14 mm", "Rögzítő furatok": "2 × Ø8,5 mm, 90 mm osztással", "Tömeg": "189 g"})
KLC_EM1 = ("KLC-EM1", 11, [(318, 570, 572, 725)],
           {"Megnevezés (gyári)": "Kit levas – cremonas empotrar KLC-EM1 / Kit recessed cams + keepers – zárkampó + zárfészek készlet", **INOX,
            "Tartalom": "LEM1 zárkampó (61 × 23,5 mm, rúdfurat Ø16,1 mm) + CEM1 zárfészek (110 × 30 mm)", "Tömeg": "473 g (készlet)"})
FEX16001 = ("FEX16001", 12, [(24, 98, 262, 265), (310, 95, 548, 272)],
            {"Megnevezés (gyári)": "Falleba exterior 16 FEX16001 / External lock 16 – külső nyomólapos rúdzár", **INOX,
             "Rúdátmérő": "Ø16 mm (rúdfurat Ø16,3 mm)", "Méret": "270 × 115 mm", "Magasság": "42 mm",
             "Rögzítő furatok": "Ø8,5 mm", "Tömeg": "1365 g"})
KB3A = ("KB3A", 14, [(70, 594, 136, 666), (163, 610, 286, 716)],
        {"Megnevezés (gyári)": "Kit brida con casquillo 31-16 KB3A / Kit tube clamp with bush 31-16 – rúdvezető bilincs nylon persellyel", **INOX,
         "Rúdátmérő": "Ø16 mm (furat Ø16,3 mm)", "Méret": "76 × 31 mm", "Magasság": "38,7 mm",
         "Rögzítő furatok": "2 × Ø8,5 mm, 55 mm osztással", "Tömeg": "81 g"})
KLC_EX31 = ("KLC-EX31", 14, [((40, 335, 332, 522), [(20, 478, 222, 530)]), (355, 378, 560, 515)],
            {"Megnevezés (gyári)": "Kit levas – cremonas 16 KLC-EX31 / Kit cams and keepers 16 – zárkampó + ellendarab készlet", **INOX,
             "Tartalom": "2 × LEX31 zárkampó (242 g) + 2 × CEX3 zárfészek (280 g)", "Rúdátmérő": "Ø16 mm",
             "Zárfészek mérete": "99 × 35,5 mm, magasság 38,5 mm", "Rögzítő furatok": "Ø8,5 mm, 79,5 mm osztással",
             "Tömeg": "1044 g (készlet)"})

# slug -> (MP Steel cikkszám, PDF oldal (1-től), kivágások [pt] (esetleg kifehérítendő részekkel), műszaki adatok)
ITEMS = {
    "8bt1mb-rm-hatsoajto-zsanerlap-bak-260-3mm-mp": ("BT1MB", 34, [(40, 360, 292, 505), (308, 342, 562, 512)],
        {"Megnevezés (gyári)": "Bisagra trasera BT1MB con soporte U 25 / Rear hinge BT1MB with \"U\" bracket 25 – hátsóajtó-zsanér U-bakkal", **INOX,
         "Teljes hossz": "274 mm", "Zsanérlap szélessége": "86 mm", "Lemezvastagság": "3 mm", "Bak": "U-alakú, 25 mm, 79 × 50 mm",
         "Rögzítő furatok": "Ø8,5 mm", "Tömeg": "862 g"}),
    "mp-cem-inox-feszek": CEM1,
    "mp-lem-inox-kampo": LEM1,
    "mp-cem-inox-feszek-mp-lem-kampo-kit": KLC_EM1,
    "mp-klc-em2-inox-feszek-kampo": ("KLC-EM2", 11, [(12, 570, 308, 725)],
        {"Megnevezés (gyári)": "Kit levas – cremonas empotrar KLC-EM2 / Kit recessed cams + keepers – zárkampó + zárfészek készlet", **INOX,
         "Tartalom": "LEM1 zárkampó (61 × 23,5 mm, rúdfurat Ø16,1 mm) + CEM2 és CEM3 zárfészek (75 × 30 mm, magasság 16 mm)",
         "Tömeg": "355 g (készlet)"}),
    "mp-cfem003-alatet-a-zarhoz": ("CFEM003", 9, [((34, 588, 272, 748), [(260, 598, 276, 616), (260, 686, 276, 704)]), (266.5, 583, 582, 760)],
        {"Megnevezés (gyári)": "Junta falleba de empotrar CFEM003 / Gasket for recessed handle – tömítés a süllyesztett rúdzárhoz (FEM16003)",
         "Anyag": "elasztomer", "Méret": "325 × 159 mm", "Vastagság": "3,2 mm", "Rögzítő furatok": "Ø5 mm", "Tömeg": "17 g"}),
    "mp-fem16003-25-sullyesztett-rudzar-inox": ("FEM16003-25", 9, [(36, 100, 282, 262), (305, 90, 573, 282)],
        {"Megnevezés (gyári)": "Falleba empotrar 16 FEM16003-25 / Recessed handle 16 – süllyesztett rúdzár", **INOX,
         "Rúdátmérő": "Ø16 mm (rúdfurat Ø16,3 mm)", "Méret": "320 × 154 mm", "Beépítési mélység": "33 mm",
         "Rögzítő furatok": "Ø5 mm", "Tömeg": "1626 g"}),
    "mp-fem16003-29-sullyesztett-rudzar-inox": ("FEM16003-29", 9, [(36, 330, 282, 508), (305, 333, 573, 526)],
        {"Megnevezés (gyári)": "Falleba empotrar 16 FEM16003-29 / Recessed handle 16 – süllyesztett rúdzár", **INOX,
         "Rúdátmérő": "Ø16 mm (rúdfurat Ø16,3 mm)", "Méret": "320 × 154 mm", "Beépítési mélység": "33 mm",
         "Rögzítő furatok": "Ø5 mm", "Tömeg": "1670 g"}),
    "mp-fex16-001-nyomolapos-rudzar": FEX16001,
    "mp-fex16-001-klcex31-kb3a-nyomolapos-rudzar-szett": ("FEX16001 + KLC-EX31 + KB3A", 12,
        [FEX16001[2][0], (14, KLC_EX31[2][0]), (14, KB3A[2][0])],
        {"Megnevezés (gyári)": "External lock 16 FEX16001 + Kit cams and keepers 16 KLC-EX31 + Kit tube clamp with bush 31-16 KB3A – nyomólapos rúdzár szett", **INOX,
         "Tartalom": "FEX16001 külső nyomólapos rúdzár (270 × 115 mm, 1365 g); KLC-EX31 zárkampó + zárfészek készlet (1044 g); "
                     "KB3A rúdvezető bilincs nylon persellyel (81 g)",
         "Rúdátmérő": "Ø16 mm"}),
    "mp-kb2a-22-mm-omega-lefogato-33-22": ("KB2A", 19, [(40, 606, 116, 686), (145, 606, 268, 716)],
        {"Megnevezés (gyári)": "Kit brida con casquillo 33-22 KB2A / Kit tube clamp with bush – rúdvezető (omega) bilincs nylon persellyel", **INOX,
         "Rúdátmérő": "Ø22 mm (furat Ø22,3 mm)", "Méret": "82 × 33 mm", "Magasság": "41,5 mm",
         "Rögzítő furatok": "2 × Ø8,5 mm, 61 mm osztással", "Tömeg": "91 g"}),
    "mp-kb2b-22-mm-nagy-omega-130-22": ("KB2B", 19, [(283, 584, 408, 692), ((424, 572, 580, 750), [(418, 724, 468, 752)])],
        {"Megnevezés (gyári)": "Kit brida con casquillo 130-22 KB2B / Kit tube clamp with bush 130-22 – hosszú rúdvezető (omega) bilincs nylon persellyel", **INOX,
         "Rúdátmérő": "Ø22 mm (furat Ø22,3 mm)", "Méret": "130 × 82 mm", "Magasság": "41,5 mm",
         "Rögzítő furatok": "4 × Ø8,5 mm, 61 mm osztással", "Tömeg": "312 g"}),
    "mp-kb2e-kit-omega-lefogato-22-mm": ("KB2E", 20, [(24, 572, 300, 716), (304, 642, 548, 704)],
        {"Megnevezés (gyári)": "Kit de bridas con casquillo (2×130+1×33) – 22 KB2E / Kit tube clamps with bush – rúdvezető bilincs készlet", **INOX,
         "Tartalom": "2 × KB2B (130-22) + 1 × KB2A (33-22) rúdvezető bilincs nylon persellyel", "Rúdátmérő": "Ø22 mm",
         "Tömeg": "715 g (készlet)"}),
    "mp-kb3a-omega-lefogato-16-mm": KB3A,
    "mp-klc-ex31-kit-16-zarkampo-ellendarab": KLC_EX31,
    "mp22-fex22001-rm-nyomolapos-rudzar": ("FEX22001", 18, [(24, 98, 272, 262), ((270, 95, 552, 276), [(266, 98, 276.5, 205)])],
        {"Megnevezés (gyári)": "Falleba exterior 22 FEX22001 / External lock 22 – külső nyomólapos rúdzár", **INOX,
         "Rúdátmérő": "Ø22 mm (rúdfurat Ø22,3 mm)", "Méret": "293 × 137 mm", "Magasság": "43,5 mm",
         "Rögzítő furatok": "Ø8,5 mm", "Tömeg": "1846 g"}),
}


def render(page, box):
    """box: (x0, y0, x1, y1) vagy ((x0, y0, x1, y1), [kifehérítendő téglalapok]) – pontban, oldalkoordinátában."""
    box, blanks = (box, []) if isinstance(box[0], (int, float)) else box
    zoom = 250 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for bx0, by0, bx1, by1 in blanks:
        img.paste("white", tuple(max(0, int(round((v - o) * zoom))) for v, o in zip((bx0, by0, bx1, by1), (box[0], box[1], box[0], box[1]))))
    ys, xs = np.where(np.asarray(img.convert("L")) < 235)
    return img.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), min(xs.max() + 12, img.width), min(ys.max() + 12, img.height)))


def main():
    doc = pymupdf.open(PDF)
    existing = load_enrichment()
    enrichment = {}
    for p in load_products(SUPPLIER):
        item = ITEMS.get(p["slug"])
        other = existing.get(p["slug"], {})
        if not item or (other.get("images") and other.get("source") != SOURCE):
            continue
        ref, pno, boxes, specs = item
        clear_images(p["slug"])
        images = []
        for i, b in enumerate(boxes, 1):
            bp, b = b if isinstance(b[0], int) and len(b) == 2 else (pno, b)  # (oldal, kivágás): másik oldalról
            images.append(save_image(render(doc[bp - 1], b), p["slug"], i))
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": f"{URL}#page={pno}", "sourceTitle": f"MP Steel katalógus 12/2016: {ref}",
                                 "matchedCode": ref, "specs": {"Cikkszám (gyártói)": ref, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
