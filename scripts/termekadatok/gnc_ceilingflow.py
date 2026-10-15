"""G&C Ceilingflow mennyezeti légelosztó (24-0008 fekete / 24-0009 fehér) – több kép, adat, adatlap és telepítési
videó a G&C honlapjáról és termékadatlapjából (a Quadris kérésére).

Képek: a fekete változat és a távirányító az adatlapból, a fehér változat két fotója és a méretrajz a honlapról.
Az adatlap (PDF) és a telepítési videó (MP4) a public/dokumentumok, ill. public/video mappába kerül.

Használat: python3 scripts/termekadatok/gnc_ceilingflow.py
"""

import io
import sys
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, fetch, load_enrichment, save_image, update_enrichment  # noqa: E402

SLUG = "gc-ceilingflow"
UP = "https://gnc-systems.com/wp-content/uploads/"
SHEET = UP + "2026/04/GC-OK2314194-PAGINA-CEILINGFLOW-2.pdf"
VIDEO = UP + "2024/02/How-to-install-your-ceilingflow.mp4"
WEB = [("feher", "2024/02/plafondventilator-0-scaled.jpg"), ("feher-alulrol", "2024/02/plafondventilator-1-scaled.webp"),
       ("meretrajz", "2024/02/MCU-24.0009-exterior-drawing.jpg")]

SPECS = {
    "Feszültség [V]": "220–230",
    "Teljesítmény [W]": "27 (alacsony) – 41 (magas fokozat)",
    "Zajszint [dB(A)]": "35 (alacsony) – 47 (magas fokozat)",
    "Méret": "595 × 595 mm (álmennyezeti kazetta helyére)",
    "Beépítési magasság": "166 mm",
    "Szín": "fekete (24-0008) / fehér (24-0009)",
    "Anyag": "újrahasznosítható ABS",
    "Motor": "kefe nélküli, rövidzárlat és túlfeszültség elleni védelemmel",
    "Távirányító": "tartozék (távirányító nélkül is működtethető)",
    "Bekötés": "dugaszolható (Plug & Play), szerelési munka nélkül",
    "Tanúsítvány": "CE, RoHS, LVD",
    "Kiegészítő": "keret tömör mennyezethez: 24-0013 (fehér), 24-0113 (fekete)",
}
DESCRIPTION = (
    "Professzionális mennyezeti ventilátor irodákba, műhelyekbe, bemutatótermekbe, üzletekbe, iskolákba, konyhákba, "
    "tárgyalókba és szerverszobákba. Az álmennyezet egy kazettája helyére illeszthető: a lapot kivesszük, a "
    "Ceilingflow-t a helyére tesszük, és csak be kell dugni – nincs szerelési költség. Nyáron kellemes, huzatmentes "
    "légmozgással hűt, télen a mennyezet alatt összegyűlő meleg levegőt egyenletesen elosztja a helyiségben. Halk, "
    "kis fogyasztású, a fokozatok távirányítóval állíthatók; tömör vagy ipari mennyezethez külön keret kapható. "
    "Könnyen áthelyezhető átrendezéskor, költözéskor vagy bérelt helyiségben."
)


def main():
    data = load_enrichment()
    sheet = pymupdf.open(stream=fetch(SHEET), filetype="pdf")
    page = sheet[0]
    by_pos = {}
    for info in page.get_image_info(xrefs=True):
        if info["xref"]:
            pix = pymupdf.Pixmap(sheet, info["xref"])
            if pix.n - pix.alpha > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            by_pos[tuple(round(v) for v in info["bbox"])] = Image.open(io.BytesIO(pix.tobytes("png")))
    # az adatlap képei: a fekete változat (a fehér alatt, jobbra) és a távirányító
    black = next(img for (x0, y0, x1, y1), img in by_pos.items() if x0 > 100 and y0 > 250 and x1 < 320)
    remote = next(img for (x0, y0, x1, y1), img in by_pos.items() if 170 < x0 < 200 and y0 > 190 and x1 < 270)
    images = [save_image(black, SLUG, 1)]
    for suffix, path in WEB:
        images.append(save_image(Image.open(io.BytesIO(fetch(UP + path))), SLUG, suffix))
    images.append(save_image(remote, SLUG, "taviranyito"))

    docs = ROOT / "public/dokumentumok"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ceilingflow-adatlap.pdf").write_bytes(fetch(SHEET))
    video = ROOT / "public/video/ceilingflow-telepites.mp4"
    video.write_bytes(fetch(VIDEO))
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) * 0.15))
    ok, frame = cap.read()
    if ok:
        Image.fromarray(np.ascontiguousarray(frame[..., ::-1])).save(ROOT / "public/video/ceilingflow-telepites.jpg", quality=85)

    e = data.get(SLUG, {"source": "G&C termékek", "sourceUrl": "https://gnc-systems.com/en/products/ceilingflow/", "sourceTitle": ""})
    e.update({"images": images, "specs": {**e.get("specs", {}), **SPECS}, "description": DESCRIPTION,
              "documents": [{"title": "Ceilingflow műszaki adatlap (PDF, angol)", "url": "/dokumentumok/ceilingflow-adatlap.pdf"}],
              "videos": [{"title": "A Ceilingflow beszerelése (videó)", "url": "/video/ceilingflow-telepites.mp4",
                          "poster": "/video/ceilingflow-telepites.jpg"}]})
    update_enrichment({SLUG: e})
    print(SLUG, len(images), "kép")


if __name__ == "__main__":
    main()
