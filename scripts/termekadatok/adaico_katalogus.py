"""ADAICO (ES) – a webáruházban nem talált tételek az ADAICO 2025-ös nyomtatott katalógusából
(https://www.adaico.com/en/downloadcatalogues/download?id=ADAICO_2025_EDS.pdf, 343 MB – a .cache/ mappába töltődik le).

A Quadris-kód (a termék slugjának eleje) az ADAICO-kód végét tartalmazza (pl. 821018 = 1601018,
121110 = 2301110, 211086-88 = 0601086 + 0601088). Az 50×52-es acél C-sín régi kódjai (1490003/1490005)
a katalógusban már nem szerepelnek; ugyanaz a szelvény más hosszban 1403010/1403012/1490006 kóddal van benne,
ezért ezeknél a keresztmetszet és a folyóméter-tömeg a katalógusból, a hossz a Quadris-megnevezésből való.
A kivágások (fotó és méretrajz) kézzel ellenőrizve.

Használat: python3 scripts/termekadatok/adaico_katalogus.py
"""

import shutil
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import CACHE, ROOT, clear_images, fetch, is_protected, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "ADAICO katalógus"
URL = "https://www.adaico.com/en/downloadcatalogues/download?id=ADAICO_2025_EDS.pdf"
C_RAIL = ("1403010 / 1403012 / 1490006", 270, [(236, 648, 349, 765), (363, 645, 462, 745)],
          {"Megnevezés (gyári)": "Galvanized Steel Bar Profile – horganyzott acél sínprofil (gumitömítéshez)",
           "Anyag": "acél, tűzihorganyzott", "Falvastagság": "2 mm", "Méret": "52 × 50 mm", "Tömeg": "kb. 2,94 kg/fm"})
# A Quadris kérésére ezek a hosszak ugyanazt a képet kapják, mint a 7800 mm-es változat
SAME_IMAGES = {"214312-5000mm-50x52-mm-acel-c-sin": "214312-7800mm-50x52-mm-acel-c-sin",
               "214312-6600mm-50x52-mm-acel-c-sin": "214312-7800mm-50x52-mm-acel-c-sin"}
# slug -> (ADAICO kód, oldal, kivágások [pt] (esetleg kifehérítendő részekkel), műszaki adatok)
ITEMS = {
    "821018-rugos-ajtokitamaszto-horg-540-425-mm-ad": ("1601018", 396, [(118, 130, 318, 225), (345, 58, 560, 240)],
        {"Megnevezés (gyári)": "Spring Door Retainer (Ø25) Zinc Plated – rugós ajtókitámasztó", "Anyag": "acél, horganyzott",
         "Csőátmérő": "Ø25 mm", "Méret": "540 × 425 mm", "Tömeg": "2,43 kg"}),
    "214312-5000mm-50x52-mm-acel-c-sin": C_RAIL,
    "214312-6600mm-50x52-mm-acel-c-sin": C_RAIL,
    "211086-88-ada-tetokiemelo-hp-lift-kit": ("0601086 + 0601088", 39, [(211, 77, 345, 401), ((20, 515, 372, 720), [(285, 655, 372, 685)])],
        {"Megnevezés (gyári)": "ADA-LIFTER Hydraulic Pump Double Effect + Pillar Extension Set – hidraulikus tetőemelő szivattyú hosszabbító készlettel",
         "Emelés": "450 mm", "Szivattyú tömege": "3,57 kg (0601086)", "Hosszabbító készlet tömege": "8,5 kg (0601088)",
         "Működés": "kettős működésű – a kar fel- és lefelé mozgatásakor is emel"}),
    "212002-adaico-rakonca-zseb-nyers": ("0502002", 35, [(278, 64, 401, 226), (417, 67, 561, 221)],
        {"Megnevezés (gyári)": "Chassishook to weld – hegeszthető rakonca-alvázzseb", "Anyag": "acél, nyers (hegesztéshez)",
         "Méret": "85 × 126 mm, 31 mm mély", "Tömeg": "1,08 kg"}),
    "121110-kombi-rakomanyrogzito-sin-sully-acel": ("2301110", 329, [((278, 437, 560, 643), [(470, 565, 560, 643)]), (221, 651, 553, 789)],
        {"Megnevezés (gyári)": "Encastred COMBI Anchor Track – süllyesztett kombi rakományrögzítő sín", "Anyag": "acél, horganyzott",
         "Méret": "3048 × 130 mm", "Falvastagság": "2,5 mm", "Tömeg": "6,4 kg"}),
    "121128-kombi-rakomanyrogzito-sin-acel": ("2301128", 327, [(29, 247, 355, 401)],
        {"Megnevezés (gyári)": "ADAICO COMBI Anchor Track – kombi rakományrögzítő sín", "Anyag": "acél",
         "Szélesség": "115 mm", "Lyukosztás": "50,8 mm / 101,6 mm"}),
}


def render(page, box):
    """box: (x0, y0, x1, y1) vagy ((x0, y0, x1, y1), [kifehérítendő téglalapok]) – pontban, oldalkoordinátában."""
    box, blanks = (box, []) if isinstance(box[0], (int, float)) else box
    zoom = 250 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for bx0, by0, bx1, by1 in blanks:
        img.paste("white", tuple(int(round((v - o) * zoom)) for v, o in zip((bx0, by0, bx1, by1), (box[0], box[1], box[0], box[1]))))
    ys, xs = np.where(np.asarray(img.convert("L")) < 235)
    return img.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), min(xs.max() + 12, img.width), min(ys.max() + 12, img.height)))


def main():
    pdf = CACHE / "adaico_2025_eds.pdf"
    if not pdf.exists():
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(fetch(URL, cache=False, timeout=600))
    doc = pymupdf.open(pdf)
    existing = load_enrichment()
    enrichment = {}
    for p in load_products("ADAICO"):
        item = ITEMS.get(p["slug"])
        other = existing.get(p["slug"], {})
        if not item or (other.get("images") and other.get("source") != SOURCE):
            continue
        ref, pno, boxes, specs = item
        clear_images(p["slug"])
        if p["slug"] in SAME_IMAGES:  # a Quadris kérésére ugyanazok a képek, mint a másik hosszé (adaico.py webáruházas képei)
            src = existing.get(SAME_IMAGES[p["slug"]], {}).get("images", [])
            images = []
            for i, u in enumerate(src, 1):
                dst = ROOT / f"public/termekkepek/{p['slug']}-{i}.webp"
                if not (is_protected(dst) and dst.exists()):
                    shutil.copyfile(ROOT / "public" / u.lstrip("/"), dst)
                images.append(f"/termekkepek/{p['slug']}-{i}.webp")
        else:
            images = [save_image(render(doc[pno - 1], b), p["slug"], i) for i, b in enumerate(boxes, 1)]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": f"{URL}#page={pno}", "sourceTitle": f"ADAICO katalógus 2025: {ref}",
                                 "matchedCode": ref, "specs": {"Cikkszám (gyártói)": ref, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
