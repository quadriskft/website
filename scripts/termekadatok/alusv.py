"""ALU-SV (CZ/SK) – keresés rendelési szám alapján, majd a termékoldal adatai és képe.

Használat: python3 scripts/termekadatok/alusv.py
"""

import html
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from common import (clear_images, code_candidates, fetch, hu_value,  # noqa: E402
                    load_products, save_image, update_enrichment)

SUPPLIER = "Alu-SV"
BASE = "https://www.alu-sv.com"
FIELDS = [("Material", "Anyag"), ("Finish", "Felület"), ("Weight", "Tömeg"), ("Length", "Hossz"),
          ("Width", "Szélesség"), ("Height", "Magasság"), ("Diameter", "Átmérő"), ("Thickness", "Vastagság"),
          ("Load capacity", "Teherbírás"), ("Unit of measure", "Mértékegység")]
FINISH = {"without": "natúr", "anodized": "eloxált", "anodised": "eloxált", "galvanized": "horganyzott", "painted": "festett"}


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def lookup(code):
    url = f"{BASE}/en/goods.ep/?action=search&keyword={quote(code)}&issue%5B%5D=number"
    page = fetch(url).decode("utf-8", "ignore")
    link = None
    for m in re.finditer(r'<a href="(/en/goods\.ep/[^"]+)"><strong>(.*?)</strong>\s*([^<]+)</a>', page):
        if m.group(3).strip().upper() == code.upper():
            link = m.group(1)
            title = text(m.group(2))
            break
    if not link:
        return None
    detail = fetch(BASE + link).decode("utf-8", "ignore")
    t = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", detail, flags=re.S))
    start = t.find("Ord. number:")
    block = t[start: t.find("Price", start)] if start >= 0 else ""
    specs = {}
    labels = [f for f, _ in FIELDS] + ["Ord. number"]
    for en, hu in FIELDS:
        m = re.search(rf"{en}:\s*(.+?)(?=\s+(?:{'|'.join(labels)}):|$)", block)
        if m:
            v = m.group(1).strip()
            specs[hu] = FINISH.get(v.lower(), hu_value(v))
    if specs.get("Mértékegység") == "m":
        specs["Mértékegység"] = "méter"
    imgs = []
    for src in re.findall(r'(?:src|href)="(/common/images/product/[^"]+)"', detail):
        if "/thumb/" in src or code.upper() not in src.upper():
            continue
        imgs.append(BASE + src)
    imgs.sort(key=lambda u: (0 if "/full/" in u else 1))
    return {"title": title, "url": BASE + link, "specs": specs, "images": list(dict.fromkeys(imgs))}


# Quadris-cikkszám -> Alu-SV cikkszám: a Constellium Děčín Eurolock 25 mm-es oldalfal-rendszer, amelyet
# az Alu-SV forgalmaz (az Excelben a gyártó szerepel). elox = "66111…", natúr (/n) = "66110…".
EXTRA = {
    "227045": "6611127045", "227045/n": "6611007045",
    "227046": "6611121777", "227046/n": "6611007046",
    "227047": "6611128196", "227047/n": "6611008196",
    "227783": "6611127783", "227784": "6611127784", "227785": "6611127785", "227948": "6611127948",
    "228197": "6611128197", "228240": "6611128240",
    # Constellium Děčín alvázprofilok: az Alu-SV kód vége a Constellium-szám (6600… natúr, 6612… eloxált)
    "207315": "6600007315", "207318": "6612007318", "207319": "6600007319",
    "237460": "6600007460", "237460/n": "6600007460",
    # a Quadris kérésére: 6613576 (MINI első FLAT oszlop) = „Pillar CS MINI profile head-on 2023 anod”
    "6613576": "6612014347",
}
# a Quadris kérésére minden MAX-os első oszlop a „Pillar pr. CS MAX front 3000mm, Al anod” (662AP17730) részletesen
# méretezett rajzát
# kapja; a többi adat (tömeg, hossz, felület) az azonos hosszúságú, eloxált MAX front tételé (None: csak az anyag)
# ugyanígy a MAX-os hátsó oszlopok (3000 és 3300 mm) a 3150 mm-es „Pillar profile CS MAX rear” (66OZ035255) rajzát
IMAGE_ONLY = {"66177137": "662AP17730", "66177147": "662AP17730", "66177300": "662AP17730",
              "6635245": "66OZ035255", "6635300": "66OZ035255"}
DATA_FROM = {"66177147": "662AP17730", "66177137": "662AP17714", "66177300": "662AP17712",
             "6635245": "662AZ03025", "6635300": "662AZ03526"}
# a profil befoglaló méretei a rajz szerint (a hosszváltozatok adatlapján nem mindig szerepelnek)
PROFILE_SIZE = {"662AP17730": {"Szélesség": "127,0 mm", "Magasság": "177,0 mm"},
                "66OZ035255": {"Szélesség": "265,0 mm", "Magasság": "35,0 mm"}}


def remove_badge(data):
    """Az Alu-SV rajzain lévő sárgászöld „N” (natúr) jelölés eltávolítása: a kör és a benne lévő betű fehér lesz."""
    import io

    import cv2
    import numpy as np
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "LA", "P"):  # átlátszó háttér -> fehér
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.split()[-1])
        img = bg
    a = np.asarray(img.convert("RGB")).copy()
    r, g, b = (a[..., i].astype(int) for i in range(3))
    badge = ((r > 150) & (g > 190) & (b < 120) & (g - b > 100)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(badge, connectivity=8)
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < 150 or not 0.6 < w / h < 1.6:
            continue
        mask = np.zeros(badge.shape, np.uint8)
        cv2.ellipse(mask, (x + w // 2, y + h // 2), (w // 2 + 3, h // 2 + 3), 0, 0, 360, 1, -1)
        a[mask > 0] = 255
    return Image.fromarray(a)


def image_only_specs(code, info):
    """A rajzot adó tétel helyett az azonos hosszúságú tétel adatai (ha van), a profil befoglaló méreteivel."""
    data = lookup(DATA_FROM[code]) if DATA_FROM.get(code) else None
    if not data:
        return {k: v for k, v in info["specs"].items() if k == "Anyag"}
    specs = {**data["specs"]}
    for k, v in PROFILE_SIZE.get(IMAGE_ONLY[code], {}).items():
        specs.setdefault(k, v)
    return specs


def main():
    products = load_products(SUPPLIER)
    products += [p for p in load_products() if (p["code"] in EXTRA or p["code"] in IMAGE_ONLY) and p not in products]
    enrichment, missing = {}, []
    for p in products:
        info, code = None, None
        forced = EXTRA.get(p["code"]) or IMAGE_ONLY.get(p["code"])
        for c in ([forced] if forced else []) + ([] if p["code"] in IMAGE_ONLY else code_candidates(p)):
            try:
                info = lookup(c)
            except Exception as err:  # noqa: BLE001
                print("  hiba:", c, err)
            if info:
                code = c
                break
        if not info:
            missing.append(p)
            continue
        clear_images(p["slug"])
        images = []
        # a "full" és a normál rajz ugyanaz a kép: csak az elsőt mentjük
        for url in info["images"][:1]:
            try:
                images.append(save_image(remove_badge(fetch(url)), p["slug"]))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", url, err)
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": info["url"],
            "sourceTitle": info["title"],
            "matchedCode": code,
            "specs": (image_only_specs(p["code"], info) if p["code"] in IMAGE_ONLY else
                      {**info["specs"], **({"Felület": "eloxált"} if "elox" in p["name"].lower() and info["specs"].get("Felület") == "natúr" else {})}),
            "images": images,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>16}  {p['name']}")


if __name__ == "__main__":
    main()
