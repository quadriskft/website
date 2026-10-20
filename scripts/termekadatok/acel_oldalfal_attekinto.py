"""Acél oldalfalak – a gyártói katalógus (2016_Prospekt_Stahlbordwaende_GE) típuscsoport-áttekintő rajzai vektorosan,
nagy felbontásban (a Quadris kérésére élesen, nagyítva is olvasható méretszámokkal). A bekezdések és a „Per Klick …”
szövegek kitakarva; a rajzok és a profiltáblázat maradnak. Kimenet: data/forras/acel_oldalfal_<csoport>_attekinto.png
(ezeket az acel_oldalfal_3d.py teszi a termékekhez).

Használat: python3 scripts/termekadatok/acel_oldalfal_attekinto.py
"""

import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, fetch  # noqa: E402

PDF = "https://www.fuhrmann.at/files/stahlbordwaende/2016_Prospekt_Stahlbordwaende_GE_24seitig_interaktiv.pdf"
DPI = 400
# csoport -> (oldal, kivágás pt-ben: x0, y0, x1, y1)
GROUPS = {
    "b": (4, (126, 134, 584, 424)),
    "bn": (4, (664, 128, 1166, 424)),
    "hv": (4, (22, 436, 578, 788)),
    "hvn": (4, (880, 500, 1166, 788)),
    "bak": (5, (60, 142, 572, 422)),
    "hvak": (5, (232, 490, 578, 788)),
    "kiegeszito": (5, (670, 106, 1160, 422)),
}


def is_prose(text):
    t = text.strip()
    return len(t) > 22 or any(w in t for w in ("Klick", "Click", "Profilzeich", "drawing", "Stahlbord", "Steelside"))


def main():
    doc = pymupdf.open(stream=fetch(PDF), filetype="pdf")
    for page_no in {p for p, _ in GROUPS.values()}:
        page = doc[page_no]
        for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
            if is_prose(text):
                page.add_redact_annot(pymupdf.Rect(x0, y0, x1, y1), fill=(1, 1, 1))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    for name, (page_no, clip) in GROUPS.items():
        pix = doc[page_no].get_pixmap(dpi=DPI, clip=pymupdf.Rect(*clip))
        out = ROOT / f"data/forras/acel_oldalfal_{name}_attekinto.png"
        pix.save(out)
        print(name, pix.width, pix.height)


if __name__ == "__main__":
    main()
