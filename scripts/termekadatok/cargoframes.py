"""Cargo Frames (CZ) – acél plató-keret profilok a gyártó által küldött rajzokból (data/forras/cargoframes/).

Forrás: a Quadris e-mailben kapott Cargo Frames profilrajzok (vektoros PDF), a furatkép 3D-nézetei, az
összeszerelt keret fotója, valamint a gyártó műszaki listája (csak típus, méret, anyag, furatkép, folyóméter-tömeg).

A Quadris-kód felépítése: PU00-1152130-00-7500 = U profil, 115/21/3 (magasság / felső rész mélysége /
falvastagság), -00- = furat nélkül, H3 = perforált (dupla furat a rögzítőfülnek), utolsó tag = hossz (mm).

Rajzok:
  - CF-U_2mm-2022-1.pdf: „Obvodový profil typ U 2mm” – 110/15/2
  - profil_U_30_01_2017.pdf: „Profil rámu vozu obvodový – Typ U” – 115/140/160 magasság, 21/24/27 mélység, 3 mm
A rajzokból csak a profil körvonala (és a metszet vonalkázása) és a fő befoglaló méretek maradnak meg
(teljes magasság, teljes szélesség, felső rész mélysége, falvastagság); a szövegmező, keret, rádiuszok, szögek,
tűrések és részméretek kimaradnak. A kivágásokat kézzel ellenőriztük.

Nem párosítva (nincs hozzá gyártói rajz / adat):
  - PUL0 112/24/3 – nem szerepel a műszaki listában és rajz sincs hozzá (csak a keretfotó kerül rá)
  - PF50 140/27/3 „sima” – a típus nem azonosítható biztosan (az FV rajz 160 mm magas), csak a keretfotó
  - ZAS0000001 dugó – nincs róla kép / adat
  - 141265/141266 „ACÉL hossztartó 120/60/5|6” – egyik Cargo Frames rajz sem ilyen, a Quadris-adatok maradnak

Használat: python3 scripts/termekadatok/cargoframes.py
"""

import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Cargo Frames"
URL = "https://cargoframes.eu"
SRC = ROOT / "data/forras/cargoframes"
KIT_PHOTO = SRC / "cargoframes_kit_keret.jpg"

# Rajzok tisztítása: a teljes egészében megtartott útvonalak (indexek a get_drawings() listájában),
# a megtartott méretvonalak/-szövegek téglalapjai (pt; egy vonalelem akkor marad, ha teljesen benne van),
# és a megtartott valódi szövegek.
DRAWINGS = {
    "U2": {  # CF-U_2mm-2022-1.pdf – U 110/15/2
        "file": "CF-U_2mm-2022-1.pdf",
        "paths": [0],  # profil körvonala
        "rects": [
            (200, 105, 416, 112), (412.5, 105, 415, 241), (202.5, 105, 205, 213),  # 74 (szélesség)
            (168, 198, 174, 514), (167, 511, 202, 513.5), (167, 199, 202, 201.5),  # 110 (magasság)
            (437, 180, 444, 262), (333, 199, 444, 201.5), (415, 241.5, 444, 244),  # 15 (felső rész mélysége)
            (255.9, 500, 324, 560),  # 2 (falvastagság)
        ],
        "texts": ["74,00", "110,00", "15,00", "2,00"],
    },
    "U3": {  # profil_U_30_01_2017.pdf – U 115/140/160 × 21/24/27 × 3
        "file": "profil_U_30_01_2017.pdf",
        "paths": list(range(0, 90)) + list(range(114, 150)) + list(range(190, 197)),  # vonalkázás, körvonal, élszerkesztő vonalak
        "rects": [
            (178, 55, 392, 78), (179, 68, 181.5, 226), (389, 68, 391.5, 268),  # 74 (szélesség)
            (100, 210, 124, 542), (114, 212, 193, 214.5), (114, 538, 176, 540.5),  # 115/140/160 (magasság)
            (437, 99, 443, 275), (417, 124, 432, 182), (395, 272, 446, 274.5), (310, 212, 446, 214.5),  # 21/24/27
            (347, 257, 368, 311),  # 3 (falvastagság)
        ],
        "texts": [],
    },
}
# Furatkép: felső profil, dupla Ø15 furat 50 mm-re a rögzítőfülnek (L, Z, X, Y jelölésekkel); csak a szövegmező nélkül
HOLES_TOP = ("prostorovy_nahled_diry_horni_profil_U_12_02_2017_Sheet_1.pdf", (31, 31, 564, 612))

HOLES = {
    "00": "furat nélkül",
    "H3": "dupla furat (2 × Ø15 mm, 50 mm távolság) a rakományrögzítő fülnek, 300 mm osztással (Z 150 / X 300 / Y 150 mm)",
}
# profil (magasság, mélység, vastagság) -> (rajz, tömeg kg/fm a műszaki listából)
PROFILES = {
    (110, 15, 2): ("U2", "3,67"),
    (115, 21, 3): ("U3", "5,63"),
    (115, 27, 3): ("U3", "5,77"),
    (140, 21, 3): ("U3", "6,22"),
    (140, 24, 3): ("U3", "6,29"),
    (140, 27, 3): ("U3", "6,36"),
}


def _item_rect(it):
    pts = [v for v in it[1:] if isinstance(v, pymupdf.Point)]
    if it[0] == "re":
        return pymupdf.Rect(it[1])
    if it[0] == "qu":
        return it[1].rect
    return pymupdf.Rect(min(p.x for p in pts), min(p.y for p in pts), max(p.x for p in pts), max(p.y for p in pts))


def clean_drawing(key, zoom=250 / 72):
    """A rajz újraépítése csak a megtartott elemekkel; PIL képet ad vissza."""
    cfg = DRAWINGS[key]
    doc = pymupdf.open(SRC / cfg["file"])
    page = doc[0]
    drawings = page.get_drawings()
    rects = [pymupdf.Rect(r) for r in cfg["rects"]]
    keep = []
    for i, d in enumerate(drawings):
        items = d["items"] if i in cfg["paths"] else [it for it in d["items"] if any(r.contains(_item_rect(it)) for r in rects)]
        if items:
            keep.append((d, items))
    # minden szöveget, képet és vonalat törlünk, kivéve a megtartott szövegeket
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                if s["text"].strip() and s["text"].strip() not in cfg["texts"]:
                    page.add_redact_annot(pymupdf.Rect(s["bbox"]))
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    page.add_redact_annot(page.rect)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_REMOVE, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                          text=pymupdf.PDF_REDACT_TEXT_NONE)
    for d, items in keep:
        shape = page.new_shape()
        for it in items:
            if it[0] == "l":
                shape.draw_line(it[1], it[2])
            elif it[0] == "c":
                shape.draw_bezier(*it[1:5])
            elif it[0] == "re":
                shape.draw_rect(it[1])
            elif it[0] == "qu":
                shape.draw_quad(it[1])
        shape.finish(color=d.get("color"), fill=d.get("fill"), width=d.get("width") or 0, even_odd=d.get("even_odd", False),
                     lineCap=max(d.get("lineCap") or (0,)), closePath=False)
        shape.commit()
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    return trim(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), 30)


def trim(img, margin=12):
    ys, xs = np.where(np.asarray(img.convert("L")) < 235)
    return img.crop((max(xs.min() - margin, 0), max(ys.min() - margin, 0),
                     min(xs.max() + margin, img.width), min(ys.max() + margin, img.height)))


def render_crop(name, box, zoom=250 / 72):
    page = pymupdf.open(SRC / name)[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    return trim(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))


def parse_code(code):
    """PU00-1152130-00-7500 -> ('PU00', (115, 21, 3), '00', 7500)"""
    parts = code.split("-")
    dims = parts[1] if len(parts) > 1 else ""
    prof = (int(dims[:3]), int(dims[3:5]), int(dims[5:6])) if len(dims) == 7 and dims.isdigit() else None
    holes = parts[2] if len(parts) > 2 else None
    length = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() and int(parts[3]) else None
    return parts[0], prof, holes, length


def main():
    existing = load_enrichment()
    cache = {}
    enrichment = {}
    for p in load_products("Cargoframes Czech"):
        code = p["supplierCode"]
        prefix, prof, holes, length = parse_code(code)
        if prefix not in ("PU00", "PUL0", "PF50") or not prof:
            continue  # dugó és a 120/60-as hossztartók: nincs hozzá Cargo Frames forrás
        other = existing.get(p["slug"], {})
        if other.get("images") and other.get("source") not in (SOURCE, "Quadris adatok"):
            continue
        h, depth, t = prof
        specs = {"Cikkszám (gyártói)": code}
        images = []
        match = PROFILES.get(prof) if prefix == "PU00" else None
        if match:
            key, weight = match
            if key not in cache:
                cache[key] = clean_drawing(key)
            images.append(cache[key])
            specs |= {"Profil típus": f"U {h}/{depth}/{t}", "Anyag": "S355MC acél", "Magasság": f"{h} mm",
                      "Szélesség": "74 mm", "Felső rész mélysége": f"{depth} mm", "Falvastagság": f"{t} mm"}
            if length:
                specs["Hossz"] = f"{length} mm"
            if holes in HOLES:
                specs["Furatkép"] = HOLES[holes]
            specs["Tömeg"] = f"{weight} kg/fm"
            if holes == "H3":
                if "holes" not in cache:
                    cache["holes"] = render_crop(*HOLES_TOP)
                images.append(cache["holes"])
        else:
            specs["Méret (megnevezés szerint)"] = f"{h}/{depth}/{t} mm"
            if length:
                specs["Hossz"] = f"{length} mm"
        if "kit" not in cache:
            cache["kit"] = Image.open(KIT_PHOTO)
        images.append(cache["kit"])
        clear_images(p["slug"])
        paths = [save_image(img, p["slug"], i) for i, img in enumerate(images, 1)]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": URL,
                                 "sourceTitle": f"Cargo Frames profil {specs.get('Profil típus', code)}" if match else f"Cargo Frames acél keret ({code})",
                                 "matchedCode": code, "specs": specs, "images": paths}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
