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


def no_frame(dark):
    """A keret és a fejléc hosszú vízszintes / függőleges vonalai (és közvetlen környezetük) nem tartalom."""
    out = dark.copy()
    h, w = dark.shape
    for y in np.where(dark.sum(axis=1) > w * 0.85)[0]:  # csak a (majdnem) teljes szélességű vonal keret
        out[max(y - 2, 0):y + 3, :] = False
    for x in np.where(dark.sum(axis=0) > h * 0.85)[0]:
        out[:, max(x - 2, 0):x + 3] = False
    return out


def whiten(img, mask):
    """a keret- és fejlécvonalak (mask) fehérre – a kép többi része változatlan"""
    a = np.asarray(img).copy()
    a[mask] = 255
    return Image.fromarray(a)


def landscape_drawing(page):
    """Fekvő (Heavy Duty) adatlap: a bal oldali méretezett szelvényrajz – a jobb oldali 3D nézet, a megjegyzések
    és a fejléc nélkül. Raszteresen: a bal szélről induló tartalom és a 3D nézet közötti üres sávnál vágunk."""
    r = page.rect
    # A4 fekvő (FOX): a fejléc / megjegyzés a rajz alatt 86%-tól; A3 fekvő (FHD): a rajz lejjebb ér
    bottom = r.height * (0.86 if r.width < 1000 else 0.95)
    for d in page.get_drawings():  # a megjegyzés-doboz (bal alul, keretezett) a rajz alsó határa
        b = d["rect"]
        if b.x0 < r.width * 0.3 and b.y0 > r.height * 0.7 and r.width * 0.15 < b.width < r.width * 0.5 and b.height > 10:
            bottom = min(bottom, b.y0 - 4)
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        if re.search(r"Durchbiegung|Verdrehung|Maßtoleranz", text) and x0 < r.width * 0.4:
            bottom = min(bottom, y0 - 4)
    clip = pymupdf.Rect(r.x0 + 22, r.y0 + 22, r.width * 0.6, bottom)
    pix = page.get_pixmap(dpi=300, clip=clip)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    dark = np.asarray(img.convert("L")) < 215
    # a keret- és fejlécvonalak (a sáv nagy részén átfutó vízszintes / függőleges vonalak) nem számítanak tartalomnak
    content = no_frame(dark)
    img = whiten(img, dark & ~content)
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
    # a rajz alatti, üres sávval elválasztott megjegyzés (pl. „Durchbiegung …”) nem kell: a legmagasabb összefüggő sáv
    segs, a = [], ys[0]
    for p, q in zip(ys, ys[1:]):
        if q - p > img.height * 0.03:
            segs.append((a, p))
            a = q
    segs.append((a, ys[-1]))
    lo, hi = max(segs, key=lambda t: t[1] - t[0])
    ys = ys[(ys >= lo) & (ys <= hi)]
    cols_in = np.where(part[lo:hi + 1].any(axis=0))[0]
    start, end = start + cols_in.min(), start + cols_in.max()
    return img.crop((max(start - 40, 0), max(ys.min() - 40, 0), min(end + 40, img.width), min(ys.max() + 40, img.height)))


ANTRACIT = np.array([30, 33, 37], np.float32)  # sötét antracitszürke vonalak (a Quadris kérésére)


def contrast(img, line):
    """Halvány, vékony vonalak: vastagítva (line px-es minimumszűrő) és egységesen sötét antracitszürkére."""
    g = np.asarray(img.convert("L").filter(ImageFilter.MinFilter(line))).astype(np.float32)
    a = np.clip((255 - g) / 255 * 3.5, 0, 1)[..., None]
    out = 255 * (1 - a) + ANTRACIT * a
    return Image.fromarray(out.astype(np.uint8))


def web_versions(img):
    """(megjelenítési, nagyítási) változat: a termékoldalon kicsinyítve is legalább ~3 px-es vonalak (1000 px),
    a nagyításhoz 2600 px-es, mérsékelten vastagított, éles méretszámokkal."""
    k = 1000 / max(img.size)
    line = max(3, int(round(3.2 / k)) | 1)
    return contrast(img, line), contrast(img, 3)


def drawing(pdf_bytes, code=""):
    img = page_drawing(pymupdf.open(stream=pdf_bytes, filetype="pdf")[0])
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
    # a teljes kereten belül (a keret- és fejlécvonalak kiszűrve), hogy a szélső méretszámok ne vesszenek el
    clip = pymupdf.Rect(r.x0 + 8, r.y0 + 8, r.x1 - 8, top + 1)
    pix = page.get_pixmap(dpi=300, clip=clip)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    dark = np.asarray(img.convert("L")) < 200
    a = no_frame(dark)
    img = whiten(img, dark & ~a)
    ys, xs = np.where(a)
    m = 40
    return img.crop((max(xs.min() - m, 0), max(ys.min() - m, 0), min(xs.max() + m, img.width), min(ys.max() + m, img.height)))


def main():
    extended = json.loads((ROOT / "src/data/bovitett.json").read_text())["products"]
    extended += json.loads((ROOT / "data/kezi_termekek.json").read_text())["products"]  # pl. BKT 400 (kézzel felvett)
    fu = {p["code"]: p for p in extended if p.get("source") == "Fuhrmann"}
    sheets = {**datasheets(), "BKT 400": "https://www.fuhrmann.at/files/stahlbordwaende/BKT400.pdf"}
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
        show, big = web_versions(img)
        rajz = save_image(show, slug, "meretrajz")
        save_image(big, slug, "meretrajz-nagy", max_size=2600)  # a nagyító nézethez (a termékoldal ezt nyitja meg)
        imgs = [u for u in e.get("images", []) if u != rajz]
        e["images"] = imgs[:1] + [rajz] + imgs[1:]
        updates[slug] = e
    update_enrichment(updates)
    print(len(updates), "méretezett rajz;", "adatlap nélkül:", ", ".join(missing) or "–")


if __name__ == "__main__":
    main()
