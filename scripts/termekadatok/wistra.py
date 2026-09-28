"""WISTRA GmbH Cargo Control (DE) – a Wistra-tételek a Wistra 2021-es német főkatalógusából
(https://www.wistra.eu/fileadmin/media/products/catalogs/de/Wistra-Hauptkatalog-DE.pdf, 62 MB – a .cache/ mappába töltődik le).

A Quadris-féle beszállítói kód (Termékkód oszlop) pontosan a Wistra-cikkszám:
  140000082100    = Endbeschlag 821 für Anker-Kombi-Zurrschienen (49. o.)
  221808000920    = Sperrb 1808 Alu 09 – állítható alumínium rakományrögzítő rúd, 19 mm-es csappal (56. o.)
  221855-600-1600 = Sperrbalken „Airline-Beam" 1855, 1600 mm, 600 mm teleszkóp-úttal (113. o.)
  221855-600-1800 = ugyanez 1800 mm-es alaphosszal (113. o.)
A kivágások (fotó, ill. a csapkivitel méretrajza) kézzel ellenőrizve.
A www.wistra.eu időnként 521-es (Cloudflare) hibát ad – ilyenkor később újra kell futtatni.

Használat: python3 scripts/termekadatok/wistra.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import CACHE, clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Wistra"
URL = "https://www.wistra.eu/fileadmin/media/products/catalogs/de/Wistra-Hauptkatalog-DE.pdf"

def airline(length, rng, bc):
    return {"Megnevezés (gyári)": f"Sperrb 1855 {length} mm WIS schwarz blank – „Airline-Beam” rakományrögzítő rúd Airline-sínhez",
            "Alaphossz": f"{length} mm", "Teleszkóp-út": "600 mm (kihúzásgátlóval)", "Alkalmazási tartomány": rng,
            "Blokkolóerő (BC)": bc, "Tartócső átmérője": "42 mm", "Bevonat": "fekete PVC-bevonat",
            "Rögzítés": "mindkét végén automata Airline-csap (egy lyukpárba pattan)",
            "Felhasználás": "vízszintesen és függőlegesen is; csúszásgátlóval menetirányban akár 2250 kg rakományhoz"}


# slug -> (Wistra-cikkszám, oldal, kivágások [pt], "trim" = fehér margó levágása, műszaki adatok)
ITEMS = {
    "124821-kombi-sinhez-gyurus-csatlakozo": ("140000082100", 49, [((100, 489, 244, 581), True)],
        {"Megnevezés (gyári)": "Endbeschlag 821 für Anker-Kombi-Zurrschienen – gyűrűs végszerelvény kombi (Anker-Kombi) rögzítősínhez",
         "Rögzítőerő (LC)": "1000 daN", "Gyűrű belső átmérője": "33 mm"}),
    "121824-rakomanyrogzito-rud-alu-elox": ("221808000920", 56, [((43, 257, 281, 391), False), ((38, 62, 112, 128), True)],
        {"Megnevezés (gyári)": "Sperrb 1808 Alu 09 – állítható kerek alumínium rakományrögzítő rúd",
         "Anyag": "alumínium", "Tartócső átmérője": "42 mm", "Végcsap": "09-es kivitel, Ø19 mm-es csap",
         "Blokkolóerő (BC)": "400 daN (egyenletes felületi terhelésnél)", "Alkalmazási tartomány": "2235–2685 mm"}),
    "122185-rakomany-rogzito-rud-airline-sinhez-1600": ("221855-600-1600", 113, [((57, 107, 295, 265), False)],
        airline(1600, "1600–2160 mm", "200–425 daN")),
    "122186-rakomany-rogzito-rud-airline-sinhez-1800": ("221855-600-1800", 113, [((57, 107, 295, 265), False)],
        airline(1800, "1800–2360 mm", "200–375 daN")),
}


def render(page, box, trim):
    zoom = 250 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if not trim:
        return img
    ys, xs = np.where(np.asarray(img.convert("L")) < 235)
    return img.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), min(xs.max() + 12, img.width), min(ys.max() + 12, img.height)))


def main():
    pdf = CACHE / "wistra_hauptkatalog_de.pdf"
    if not pdf.exists():
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(fetch(URL, cache=False, timeout=600))
    doc = pymupdf.open(pdf)
    existing = load_enrichment()
    enrichment = {}
    for p in load_products("Wistra"):
        item = ITEMS.get(p["slug"])
        other = existing.get(p["slug"], {})
        if not item or (other.get("images") and other.get("source") != SOURCE):
            continue
        ref, pno, boxes, specs = item
        clear_images(p["slug"])
        images = [save_image(render(doc[pno - 1], b, trim), p["slug"], i) for i, (b, trim) in enumerate(boxes, 1)]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": f"{URL}#page={pno}", "sourceTitle": f"WISTRA főkatalógus: {ref}",
                                 "matchedCode": ref, "specs": {"Cikkszám (gyártói)": ref, **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
