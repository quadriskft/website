"""SAND Profile (DE) – kiegészítés a sandprofile.py-hoz: azok a termékek, amelyeket az
automatikus cikkszám-egyeztetés nem talál (pl. „A1 549 EPDM” cella, a 25. oldal E2-es
rajzrácsa, illetve a méret szerint azonosított moosgumi vierkant profilok).

Kézzel ellenőrzött hozzárendelés: termék slug -> katalógusoldal + cikkszám + adatok.
A már képpel rendelkező (pl. a sandprofile.py által kitöltött) termékeket kihagyja.

Használat: python3 scripts/termekadatok/sandprofile_kiegeszites.py
"""

import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402
from sandprofile import PDF, render  # noqa: E402

SUPPLIER = "Sand-Profile"
SOURCE = "Sand-Profile kiegészítés"

KOEXTRUDALT = "EPDM tömör gumi / moosgumi (szivacsgumi) koextrudált, beágyazott acélhuzal betéttel"
MOOS_E2 = "EPDM moosgumi (szivacsgumi, cellás gumi)"
VIERKANT = "EPDM moosgumi (cellás gumi), zárt külső bőrrel"
AF = "igen – tartósan öntapadó (AF) kivitel"

# slug -> (oldal, cikkszám a katalógusban, rajz helye: "table" | "grid" | None, adatok)
ITEMS = {
    "a1-549-mini-gobos-kedergumi-13x11-8-2-mm": (40, "A1 549 EPDM", "table", {
        "Cikkszám (gyári)": "A1 549 EPDM",
        "Anyag": KOEXTRUDALT,
        "Méret": "13 x 11,8 mm",
        "Szín": "fekete",
        "Szorítási tartomány [mm]": "2,0",
        "Kiszerelés [m]": "2x50",
        "Minimális rendelés [m]": "100",
    }),
    "a2-513-felso-gobos-keder-21-5x11-mm": (36, "A2 513 EPDM", "table", {
        "Cikkszám (gyári)": "A2 513 EPDM",
        "Anyag": KOEXTRUDALT,
        "Méret": "21,5 x 11 mm (tömlő: 10,7 mm)",
        "Szín": "fekete",
        "Szorítási tartomány [mm]": "1,0–3,0",
        "Kiszerelés [m]": "2x50",
        "Minimális rendelés [m]": "100",
    }),
    "e2-546-af-moos-gumi-ontapados": (25, "E2 546", "grid", {
        "Cikkszám (gyári)": "E2 546 (AF: öntapadós kivitel)",
        "Anyag": MOOS_E2,
        "Méret": "20,6 x 13,6 mm",
        "Szín": "fekete",
        "Öntapadós": AF,
    }),
    "e2-701-af-moos-gumi-epdm-ontapados": (25, "E2 701", "grid", {
        "Cikkszám (gyári)": "E2 701 (AF: öntapadós kivitel)",
        "Anyag": MOOS_E2,
        "Méret": "13 x 16 mm",
        "Szín": "fekete",
        "Öntapadós": AF,
    }),
    # Moosgummi vierkant (négyszög keresztmetszetű) profilok – a katalógusban csak táblázat van, rajz nincs
    "epdm-1030-moosgumi": (72, "10x30", None, {
        "Méret": "10 x 30 mm",
        "Anyag": VIERKANT,
        "Keresztmetszet": "négyszög (vierkant)",
        "Szín": "fekete (világosszürke is rendelhető)",
        "Kiszerelés [m]": "25",
        "Öntapadós": "rendelhető a szélesebb oldalon (SK / AF)",
    }),
    "epdm-1530-moosgumi": (73, "15x30", None, {
        "Méret": "15 x 30 mm",
        "Anyag": VIERKANT,
        "Keresztmetszet": "négyszög (vierkant)",
        "Szín": "fekete (világosszürke is rendelhető)",
        "Kiszerelés [m]": "25",
        "Öntapadós": "rendelhető a szélesebb oldalon (SK / AF)",
    }),
    "epdm-3030-af-moosgumi": (73, "30x30", None, {
        "Méret": "30 x 30 mm",
        "Anyag": VIERKANT,
        "Keresztmetszet": "négyzet (vierkant)",
        "Szín": "fekete (világosszürke is rendelhető)",
        "Kiszerelés [m]": "20",
        "Öntapadós": AF,
    }),
}


def table_design(page, code):
    """A táblázat azon sorának Design cellája, amelynek cikkszám cellája a kóddal kezdődik."""
    for tab in page.find_tables().tables:
        data = tab.extract()
        for r, row in enumerate(data):
            if any((c or "").strip().startswith(code) for c in row[1:2]):
                cell = tab.rows[r].cells[0]
                # a rajz alatti „Drawing matches to …” felirat levágása
                note = [w for w in page.search_for("Drawing matches") if pymupdf.Rect(cell).contains(w)]
                rect = pymupdf.Rect(cell)
                if note:
                    rect.y1 = min(n.y0 for n in note) - 1
                return rect
    return None


def grid_design(page, code):
    """A rajzrács cellája a cikkszám felirata fölött (a felirat nélkül)."""
    label = page.search_for(code)
    if not label:
        return None
    label = label[0]
    for tab in page.find_tables().tables:
        for row in tab.rows:
            for cell in row.cells:
                if cell and pymupdf.Rect(cell).contains(label):
                    rect = pymupdf.Rect(cell) + (1, 1, -2, 0)  # a cellakeret vonalai nélkül
                    rect.y1 = label.y0 - 1
                    return rect
    return None


def main():
    doc = pymupdf.open(stream=fetch(PDF), filetype="pdf")
    enrichment = load_enrichment()
    products = {p["slug"]: p for p in load_products(SUPPLIER)}
    updates, missing = {}, []
    for slug, (pno, code, kind, specs) in ITEMS.items():
        if slug not in products:
            missing.append(f"{slug} (nincs a katalógusban)")
            continue
        old = enrichment.get(slug)
        if old and old.get("source") != SOURCE and old.get("images"):
            continue  # más forrásból már van kép
        page = doc[pno - 1]
        if code not in page.get_text().replace("\n", " "):
            missing.append(f"{slug} ({code} nem található a {pno}. oldalon)")
            continue
        images = []
        if kind:
            rect = table_design(page, code) if kind == "table" else grid_design(page, code)
            if rect is None:
                missing.append(f"{slug} ({code} rajza nem található)")
                continue
            clear_images(slug)
            images.append(save_image(render(page, rect), slug))
        updates[slug] = {
            "source": SOURCE,
            "sourceUrl": f"{PDF}#page={pno}",
            "sourceTitle": f"SAND Profile összkatalógus, {pno}. oldal",
            "matchedCode": code,
            "specs": specs,
            "images": images,
        }
    update_enrichment(updates, SOURCE)
    print(f"{SOURCE}: {len(updates)}/{len(ITEMS)} termék kiegészítve")
    for m in missing:
        print(f"  NINCS: {m}")


if __name__ == "__main__":
    main()
