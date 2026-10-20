"""Acél oldalfalak (lézerhegesztett és Heavy Duty, Fuhrmann típusok) – méretezett rajz minden típushoz a gyártó
típusonkénti adatlapjából (PDF, „Datenblatt”), a Quadris kérésére.

A rajz a vektoros adatlapból 300 dpi-vel, sötét antracitszürke, kissé vastagított vonalakkal, a keret és a gyártói fejléc (szövegmező, logó) nélkül kerül kivágásra;
a termék második képe lesz (a 3D kép után). A gyártó neve a képen nem jelenik meg.

Használat: python3 scripts/termekadatok/fuhrmann_rajzok.py   (utána kep_sorrend.py)
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, fetch, load_enrichment, save_image, update_enrichment  # noqa: E402

BASE = "https://www.fuhrmann.at/de/"
PAGES = ["stbw300", "stbw350", "stbw400", "stbw450", "stbw500", "stbw600", "stbw800", "stbw1000",
         "stbwfhd", "stbwfox", "stbwfoxl", "stbwfoxla", "stbwfoxln", "foxrock"]


def clean(c):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ")).replace('"', "").strip()


def datasheets():
    """típuskód -> adatlap URL a táblázatok „Type” és „Datenblatt” soraiból"""
    out = {}
    for page in PAGES:
        raw = fetch(BASE + page + ".php").decode("utf-8", "ignore")
        for table in re.findall(r"<table[^>]*>(.*?)</table>", raw, re.S):
            types, links = [], []
            for r in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
                if not cells:
                    continue
                label = clean(cells[0]).lower()
                if label in ("type", "typ"):
                    types = [clean(c) for c in cells[1:]]
                elif label == "datenblatt":
                    links = [(re.findall(r'href="([^"]+\.pdf)"', c, re.I) or [None])[0] for c in cells[1:]]
            for t, link in zip(types, links):
                if t and link:
                    out.setdefault(re.sub(r"\s+", " ", t), BASE + link)
    return out


# ahol a szelvényrajz és a 3D nézet / a megjegyzés túl közel van egymáshoz: kézi vágás a kész kép arányában
CROP = {"FOXB 700": (0, 0, 0.33, 0.76)}


def landscape_drawing(page):
    """Fekvő (Heavy Duty) adatlap: a bal oldali méretezett szelvényrajz – a jobb oldali 3D nézet, a megjegyzések
    és a fejléc nélkül. Raszteresen: a bal szélről induló tartalom és a 3D nézet közötti üres sávnál vágunk."""
    r = page.rect
    bottom = r.height * 0.86
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        if re.search(r"Durchbiegung|Verdrehung|Maßtoleranz", text) and x0 < r.width * 0.4:
            bottom = min(bottom, y0 - 4)
    clip = pymupdf.Rect(r.x0 + 14, r.y0 + 14, r.width * 0.6, bottom)
    pix = page.get_pixmap(dpi=300, clip=clip)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    dark = np.asarray(img.convert("L")) < 215
    # a keret- és fejlécvonalak (a sáv nagy részén átfutó vízszintes / függőleges vonalak) nem számítanak tartalomnak
    content = dark.copy()
    content[dark.sum(axis=1) > img.width * 0.4, :] = False
    content[:, dark.sum(axis=0) > img.height * 0.6] = False
    colsum = content.sum(axis=0)
    cols = colsum > 2
    # tartalmi sávok (oszlopcsoportok) a köztük lévő ≥ 4%-os üres résekkel; a szelvényrajz az első magas sáv
    gap, clusters, x = int(img.width * 0.04), [], 0
    while x < img.width:
        if not cols[x]:
            x += 1
            continue
        a, run, b = x, 0, x
        while x < img.width and run <= gap:
            if cols[x]:
                b, run = x, 0
            else:
                run += 1
            x += 1
        rows = np.where(content[:, a:b + 1].any(axis=1))[0]
        clusters.append((a, b, rows.max() - rows.min() if len(rows) else 0))
    # az első, a sáv magasságának legalább 40%-át kitöltő csoport (a szélső apró jelek kimaradnak)
    start, end, _ = next(c for c in clusters if c[2] > img.height * 0.4)
    part = content[:, start:end + 1]
    ys = np.where(part.any(axis=1))[0]
    return img.crop((max(start - 40, 0), max(ys.min() - 40, 0), min(end + 40, img.width), min(ys.max() + 40, img.height)))


ANTRACIT = np.array([47, 51, 56], np.float32)  # sötét antracitszürke vonalak (a Quadris kérésére)


def contrast(img):
    """Halvány, vékony vonalak: kissé vastagabbra (a 300 dpi-s képen 3 px-es minimumszűrő) és egységesen sötét
    antracitszürkére – a kicsinyített képen is jól látszanak a kontúrok és a méretszámok."""
    g = np.asarray(img.convert("L").filter(ImageFilter.MinFilter(3))).astype(np.float32)
    a = np.clip((255 - g) / 255 * 2.6, 0, 1)[..., None]
    out = 255 * (1 - a) + ANTRACIT * a
    return Image.fromarray(out.astype(np.uint8))


def drawing(pdf_bytes, code=""):
    img = contrast(page_drawing(pymupdf.open(stream=pdf_bytes, filetype="pdf")[0]))
    if code in CROP:
        x0, y0, x1, y1 = CROP[code]
        img = img.crop((int(x0 * img.width), int(y0 * img.height), int(x1 * img.width), int(y1 * img.height)))
    return img


def page_drawing(page):
    r = page.rect
    if r.width > r.height:
        return landscape_drawing(page)
    # a fejléc (szövegmező) felső vonala: a legfelső hosszú vízszintes vonal az oldal alsó harmadában
    top = r.y1
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] == "l":
                p, q = it[1], it[2]
                if abs(p.y - q.y) < 0.5 and abs(p.x - q.x) > r.width * 0.6 and r.height * 0.6 < p.y < top:
                    top = p.y
            elif it[0] == "re":
                rc = it[1]
                if rc.width > r.width * 0.6 and rc.height < r.height * 0.4 and r.height * 0.6 < rc.y0 < top:
                    top = rc.y0
    clip = pymupdf.Rect(r.x0 + 32, r.y0 + 32, r.x1 - 32, top - 6)
    pix = page.get_pixmap(dpi=300, clip=clip)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    a = np.asarray(img.convert("L")) < 200
    ys, xs = np.where(a)
    m = 40
    return img.crop((max(xs.min() - m, 0), max(ys.min() - m, 0), min(xs.max() + m, img.width), min(ys.max() + m, img.height)))


def main():
    extended = json.loads((ROOT / "src/data/bovitett.json").read_text())["products"]
    fu = {p["code"]: p for p in extended if p.get("source") == "Fuhrmann"}
    sheets = datasheets()
    data = load_enrichment()
    updates, missing = {}, []
    for code, p in fu.items():
        url = sheets.get(code)
        if not url:
            missing.append(code)
            continue
        try:
            img = drawing(fetch(url.replace(" ", "%20")), code)
        except Exception as err:  # noqa: BLE001 – a gyártói szerver időnként bontja a kapcsolatot: újrafuttatáskor folytatja
            missing.append(f"{code} ({err.__class__.__name__})")
            continue
        slug = p["slug"]
        e = data.get(slug) or {"source": "", "sourceUrl": "", "sourceTitle": "", "specs": {}, "images": list(p.get("images", []))}
        rajz = save_image(img, slug, "meretrajz")
        imgs = [u for u in e.get("images", []) if u != rajz]
        e["images"] = imgs[:1] + [rajz] + imgs[1:]
        updates[slug] = e
    update_enrichment(updates)
    print(len(updates), "méretezett rajz;", "adatlap nélkül:", ", ".join(missing) or "–")


if __name__ == "__main__":
    main()
