"""Versus-Omega (BE) – alkatrészrajzok az online Omega-katalógusból
("1 Omega Roof Systems – Catalogue Versus-Omega 2026", Version 2027, FlippingBook:
https://online.flippingbook.com/view/967067615/).

A FlippingBook-nézegető HTML-je tartalmazza a publikáció tárhelyét (ContentRoot / PrivateContentRoot a
CloudFronton) és az aláírt hozzáférési szabályokat (initialPolicies: Policy + Signature + Key-Pair-Id).
Ezekkel letölthető:
  - PrivateContentRoot + common/downloads/publication.pdf  – a teljes PDF (~105 MB, nem tároljuk),
  - PrivateContentRoot + common/pages/src/pageNNNN.pdf      – oldalankénti vektoros PDF (ezt használjuk),
  - ContentRoot + common/search/searchtext.js               – az oldalak szövege (cikkszám-kereséshez).
Az aláírás időkorlátos, ezért a szkript minden futáskor frissen olvassa a nézegető oldalát, és csak a
hiányzó oldalakat tölti le a .cache/letoltes/versus_omega/ mappába.

Csak azokat a Quadris-tételeket párosítjuk, amelyek cikkszáma pontosan szerepel a katalógus lapján; a
kivágásokat kézzel ellenőriztük (csak maga az alkatrész, táblázat/pozíciószám nélkül).
Nincs a katalógusban: 242-14116/-14121/-14128/-14165 (DTL takaró gumik/tömítés), Penta Flex, RTS-002
(a 242-14165 a versus_dtl.py-ban a DTL PVC pelmet rajzát kapja).

Forrásnév: "Versus katalógus" (külön a versus.py / versus_dtl.py bejegyzéseitől). Azokat a termékeket,
amelyeknek már van képe más forrásból, kihagyja.

Használat: python3 scripts/termekadatok/versus_katalogus.py
"""

import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import CACHE, clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Versus"
SOURCE = "Versus katalógus"
VIEWER = "https://online.flippingbook.com/view/967067615/"
PAGE_DIR = CACHE / "versus_omega"

# Versus cikkszám -> (katalógusoldal, kivágás [pt], kitakarandó téglalapok [pt], műszaki adatok a lapról)
ITEMS = {
    "154-03041": (124, (74, 97, 260, 254), [], {"Rendszer": "Micro Trike", "Megnevezés (gyári)": "Set of 4 mounting plates (rögzítőlemez-készlet)",
                                               "Kiszerelés": "4 db-os készlet"}),
    "242-15109": (124, (116, 344, 218, 504), [], {"Rendszer": "Micro Trike", "Megnevezés (gyári)": "PVC pelmet (black) – fekete PVC takaróprofil",
                                                 "Hossz": "9 m", "Szín": "fekete", "Anyag": "PVC"}),
    "242-15114": (124, (116, 344, 218, 504), [], {"Rendszer": "Micro Trike", "Megnevezés (gyári)": "PVC pelmet (black) – fekete PVC takaróprofil",
                                                 "Hossz": "14 m", "Szín": "fekete", "Anyag": "PVC"}),
    "193-11001": (123, (67, 88.5, 542, 162), [], {"Rendszer": "Micro Trike", "Megnevezés (gyári)": "Back beam steel (acél hátsó lezáró gerenda)",
                                                 "Felépítményszélesség": "2550 mm", "Típus": "125Z", "Anyag": "acél",
                                                 "Esővédő léc": "192-01601", "Szerelőkészlet": "144-10022"}),
    "144-10037": (209, (310, 380, 780, 444), [], {"Rendszer": "Micro Trike (Quadris); a katalógusban a Ferro és Pico rendszernél",
                                                 "Megnevezés (gyári)": "Set back beam tube 30x30mm (hátsó lezáró, 30×30 mm-es csővel)",
                                                 "Cső": "30×30×2 mm acélcső (a katalógusban 112-07001)"}),
}


def part_number(p):
    m = re.search(r"\b(\d{3}-\d{5})\b", p["supplierCode"] or "") or re.match(r"V(\d{3}-\d{5})\b", p["name"])
    return m.group(1) if m else None


_policies = None


def signed(path):
    """A FlippingBook privát tárhelyén lévő fájl aláírt URL-je (a nézegető oldalából)."""
    global _policies
    if _policies is None:
        html = fetch(VIEWER, cache=False).decode("utf-8", "replace")
        i = html.index("var initialPolicies = ") + len("var initialPolicies = ")
        _policies, _ = json.JSONDecoder().raw_decode(html[i:])
        _policies = {p["PathPrefix"]: p for p in _policies}
        root = re.search(r"PrivateContentRoot:\s*'([^']+)'", html).group(1)
        _policies["root"] = root
    root = _policies["root"]
    pol = _policies[root.split("https", 1)[1]]
    return f"{root}{path}?Policy={pol['Policy']}&Signature={pol['Signature']}&Key-Pair-Id={pol['KeyId']}"


def page_pdf(n):
    f = PAGE_DIR / f"page{n:04d}.pdf"
    if not f.exists():
        data = fetch(signed(f"common/pages/src/page{n:04d}.pdf"), cache=False)
        PAGE_DIR.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    return pymupdf.open(f)


def render(page, box, blanks=()):
    zoom = 240 / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for x0, y0, x1, y1 in blanks:
        img.paste((255, 255, 255), (int((x0 - box[0]) * zoom), int((y0 - box[1]) * zoom), int((x1 - box[0]) * zoom), int((y1 - box[1]) * zoom)))
    x0, y0, x1, y1 = img.convert("L").point(lambda v: 255 if v < 235 else 0).getbbox()  # fehér szegély levágása
    return img.crop((max(x0 - 16, 0), max(y0 - 16, 0), min(x1 + 16, img.width), min(y1 + 16, img.height)))


def main():
    existing = load_enrichment()
    enrichment, missing = {}, []
    for p in load_products(SUPPLIER):
        slug = p["slug"]
        other = existing.get(slug, {})
        if other.get("images") and other.get("source") != SOURCE:
            continue  # már van képe más forrásból (versus.py, versus_dtl.py, ...)
        nr = part_number(p)
        item = ITEMS.get(nr)
        if not item:
            missing.append(p)
            continue
        pno, box, blanks, specs = item
        clear_images(slug)
        enrichment[slug] = {"source": SOURCE, "sourceUrl": f"{VIEWER}{pno}/", "sourceTitle": f"Versus-Omega katalógus – {nr}", "matchedCode": nr,
                            "specs": {"Cikkszám (gyártói)": nr, **specs},
                            "images": [save_image(render(page_pdf(pno)[0], box, blanks), slug, 1)]}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék a katalógusból, {len(missing)} nincs benne")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>10}  {p['name']}")


if __name__ == "__main__":
    main()
