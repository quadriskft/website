"""ADAICO (ES) – ADA-Slider elhúzható ponyvás oldalfal-rendszer (italszállító kit).

Forrás: az ADA-Slider Classic oldalfal EN 12642:2006 XL szilárdsági vizsgálati jelentése
(AEV Automotive, 19-0429A, 2019 – data/forras/adaico_ada-slider_en12642_xl_vizsgalat.pdf, a Quadris-tól kapott PDF).
A kép a jelentés 4. oldalán lévő robbantott ábra az alkatrész-cikkszámokkal; a műszaki adatok a jelentés
leírásából és eredményeiből valók. Maga a jelentés (harmadik fél dokumentuma) nem kerül ki a weboldalra.

Használat: python3 scripts/termekadatok/adaico_slider.py
"""

import io
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "ADAICO ADA-Slider"
PDF = ROOT / "data/forras/adaico_ada-slider_en12642_xl_vizsgalat.pdf"
SLUGS = ["21-ada-slider-teto-rendszer"]
DESC = ("Elhúzható PVC ponyvás oldalfal-rendszer felső és alsó alumínium profilon futó dupla görgős kocsikkal, "
        "első és hátsó feszítőzárral és biztonsági zárakkal. Az oldalfal EN 12642:2006 szerint XL kódú "
        "(megerősített) felépítményhez vizsgált és megfelelt.")
SPECS = {
    "Rendszer": "ADAICO ADA-Slider Classic",
    "Szabvány": "EN 12642:2006 XL – oldalfal-szilárdság (5.3.4. pont), megfelelt",
    "Vizsgálati terhelés": "0,4 P (10 000 daN hasznos terhelésnél 4 000 daN)",
    "Legnagyobb belső méret": "7 000 × 2 400 mm (hossz × magasság)",
    "Ponyva": "900 g/m² PVC, elhúzható",
    "Függőleges hevederek": "2,4 t, egymástól legfeljebb 550 mm-re",
    "Vízszintes hevederek": "3 db, 1,3 t, egymástól legfeljebb 600 mm-re",
    "Futókocsik": "Ø25 × 27 mm nylon görgős felső és alsó kocsik",
}


def main():
    doc = pymupdf.open(PDF)
    xref = doc[3].get_images()[-1][0]  # a 4. oldal robbantott ábrája
    img = Image.open(io.BytesIO(pymupdf.Pixmap(doc, xref).tobytes("png")))
    enrichment = {}
    for p in load_products("ADAICO"):
        if p["slug"] not in SLUGS:
            continue
        clear_images(p["slug"])
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": "https://www.adaico.com", "sourceTitle": "AEV Automotive 19-0429A (EN 12642 XL)",
                                 "matchedCode": "ADA-SLIDER", "description": DESC, "specs": dict(SPECS),
                                 "images": [save_image(img, p["slug"], 1)]}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
