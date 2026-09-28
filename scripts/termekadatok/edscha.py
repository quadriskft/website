"""Edscha Trailer Systems / SESAM (DE) – tolótetők, tetőprofilok, alkatrészek.

Forrás:
- a gyártó hivatalos alkatrész-katalógusai (Edscha TS és SESAM, 2024/04, PDF az edschats.com-ról):
  minden alkatrész saját keretes képpel és cikkszámmal, megnevezéssel, tömeggel szerepel –
  a képet a katalógusba ágyazott keret pontos határán vágjuk ki, így szomszédos tétel nem kerül rá;
- a rendszer-termékoldalak (Compact, SESAM CS-Slimliner FIX) képei és leírása a teljes rendszerekhez;
- a honlap profil-keresztmetszet képei a tetőprofilokhoz (Compact, Small, Volumen).

Használat: python3 scripts/termekadatok/edscha.py
"""

import io
import re
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Edscha"
BASE = "https://www.edschats.com"
CATALOGS = {
    "Edscha TS": "/globalassets/documents/pdfs/edscha/einzelersatzteilkatalog_international/09_24/edschats_ersatzteilkatalog_de-en_04-2024.pdf",
    "SESAM": "/globalassets/documents/pdfs/sesam/new_25/sesam_komponenten-u-ersatzteilkatalog_04-2024.pdf",
}
COMPACT = "/en/products/edscha-ts/commercial-vehicle-roof-systems/curtain-sider-verdecke/compact-neu/"
SLIM_FIX = "/en/products/sesam/sesam-cs-slimliner-fix/"
PROFILE_IMG = BASE + "/globalassets/content/update_umstrukturierung_2025/b2/"
COMPACT_IMG = BASE + "/globalassets/content/products/nutzfahrzeug_verdecksysteme/compact-neu/"
COMPACT_DESC = ("A Compact tetőrendszer-család kisebb, legfeljebb 8 m hosszú felépítményekhez készült: karcsú, rendkívül könnyű, "
                "mégis csavarásmerev alumínium profil, műanyag görgős kocsik, hosszú élettartamú acélgörgők és 650 mm-es műanyag csuklók. "
                "Tolótetőként és fix tetőként is kapható.")
# megnevezés-minta -> (oldal, képek, leírás, műszaki adatok)
SYSTEMS = [
    (r"E/COMPACT CS", COMPACT, [COMPACT_IMG + "edschats-compact_0002_schiebedach.jpg", COMPACT_IMG + "edschats-compact_0001_kleines-dachpaket.jpg"],
     COMPACT_DESC, {"Kivitel": "tolótető", "Jármű": "legfeljebb 8 m felépítményhossz", "Tetőív": "szegecselt, 30 × 30 mm keresztmetszet", "Csukló": "650 mm, műanyag"}),
    (r"E/COMPACT FIX", COMPACT, [COMPACT_IMG + "edschats-compact_0003_festdach.jpg"],
     COMPACT_DESC, {"Kivitel": "fix tető", "Jármű": "legfeljebb 8 m felépítményhossz", "Tetőív": "szegecselt alumínium konzollal"}),
    (r"E/COMPACT tetőprofil", COMPACT, [PROFILE_IMG + "profil_compact_300x400px_18-02-25.jpg", COMPACT_IMG + "edschats-compact_0000_alu-einzelschienen.jpg"],
     "A Compact tolótető karcsú, könnyű, csavarásmerev alumínium tetősín-profilja, legfeljebb 8 m hosszú felépítményekhez.",
     {"Anyag": "extrudált alumínium", "Rendszer": "Compact"}),
    (r"E/Small tetőprofil", SLIM_FIX, [PROFILE_IMG + "profile_text/profil_small.jpg"],
     "„Small” tetősín-profil könnyű tehergépkocsikhoz (legfeljebb 8 m), a CS-Slimliner Small / FIX tetőrendszerekhez.",
     {"Anyag": "extrudált alumínium", "Profil": "Small"}),
    (r"E/VOLUMEN tetőprofil", SLIM_FIX, [PROFILE_IMG + "profile_text/profil_volumen.jpg"],
     "„Volumen” tetősín-profil maximális belmagassághoz, oldalponyvás tolótető-rendszerekhez.",
     {"Anyag": "extrudált alumínium", "Profil": "Volumen"}),
    (r"SESAM FIX Volumen", SLIM_FIX, [BASE + "/globalassets/content/products/nutzfahrzeug_verdecksysteme/sesam-slimliner-fix/fix_1.jpg",
                                      PROFILE_IMG + "profile_text/profil_volumen.jpg"],
     "Kedvező árú, könnyű fix ponyvatető oldalponyvás felépítményhez, ha felülről rakodás nem szükséges. Egyszerű szerelés: a tetőíveket felülről kell szegecselni; fix portálgerenda és fix véglezáró ív.",
     {"Kivitel": "fix tető", "Profil": "Volumen"}),
]


# Quadris-kód -> (katalógus-cikkszám, kiegészítő műszaki adatok), ahol a Quadris kódja eltér a gyáritól
# (a megrendelő útmutatása: az „E” előtag nélkül, a gyári 40-es előtaggal keresve)
ALIASES = {
    "4138067930": ("4038067930", {"Rendszer": "Edscha Compact", "Megnevezés (gyári)": "Gelenk VP-UL – csukló (Compact, 650 mm)"}),
    "69004670": ("4069004670", {"Rendszer": "Edscha Compact Fix", "Felépítményszélesség": "2550 mm",
                                "Megnevezés (gyári)": "Standardspriegel-Festdach inkl. Klammerprofil – fix tetős kereszttartó szorítóprofillal"}),
}


def norm(s):
    return re.sub(r"\D", "", s or "")


def catalog_items():
    """cikkszám -> (katalógus, oldal, kép-keret, sorok)"""
    items = {}
    for brand, rel in CATALOGS.items():
        doc = pymupdf.open(stream=fetch(BASE + rel), filetype="pdf")
        for pno, pg in enumerate(doc):
            frames = [pymupdf.Rect(i["bbox"]) for i in pg.get_image_info()]
            blocks = pg.get_text("blocks")
            for b in blocks:
                m = re.search(rf"{brand}:\s*([\d ]+)", b[4])
                if not m:
                    continue
                code = norm(m.group(1))
                y = b[1]
                # a kód alatti szövegsorok (megnevezés DE / EN), a következő tételig
                # a tételhez tartozó kép: bal oldali keret, amely függőlegesen a kód sorát tartalmazza
                fr = [r for r in frames if r.x1 <= b[0] + 2 and r.y0 - 8 <= y <= r.y1 and r.width < pg.rect.width * 0.6]
                left = fr[0].x1 if fr else b[0] - 5
                lines = [bb[4].strip() for bb in sorted(blocks, key=lambda bb: bb[1])
                         if bb[0] >= left and y < bb[1] < y + 60 and not re.search(r"Pos\.|SESAM:|Edscha TS:|Stück", bb[4])]
                items.setdefault(code, (brand, rel, pno, pg, fr[0] if fr else None, lines))
    return items


def frame_image(pg, rect):
    pix = pg.get_pixmap(clip=rect + (2, 2, -2, -2), dpi=220, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    a = np.asarray(img.convert("L")) < 235
    ys, xs = np.where(a)
    pad = 12
    return img.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.width), min(ys.max() + pad, img.height)))


def tight(img):
    a = np.asarray(img.convert("L")) < 235
    ys, xs = np.where(a)
    pad = 10
    return img.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, img.width), min(ys.max() + pad, img.height)))


def main():
    items = catalog_items()
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        code, extra = ALIASES.get(norm(p["supplierCode"]), (norm(p["supplierCode"]), {}))
        hit = items.get(code)
        if hit and len(code) >= 8:
            brand, rel, pno, pg, rect, lines = hit
            specs = {}
            en = next((ln for ln in lines if re.search(r"[a-z]", ln) and ln == lines[-1]), None)
            de = lines[0] if lines else ""
            m = re.search(r";\s*([\d,]+)\s*kg", de)
            if m:
                specs["Tömeg"] = f"{m.group(1)} kg"
            m = re.search(r"(\d{3,4}(?:-\d{3,4})?)\s*mm", de)
            if m:
                specs["Méret"] = f"{m.group(1).replace('-', '–')} mm"
            if extra:
                specs = {"Cikkszám (gyári)": f"{code[:2]} {code[2:4]} {code[4:7]} {code[7:]}", **extra, **specs}
            clear_images(p["slug"])
            images = [save_image(frame_image(pg, rect), p["slug"], 1)] if rect else []
            enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": f"{BASE}{rel}#page={pno + 1}",
                                     "sourceTitle": f"{brand} alkatrész-katalógus 2024/04: {(en or de).split(';')[0]}",
                                     "matchedCode": code if extra else p["supplierCode"], "specs": specs, "images": images}
            continue
        sysm = next((s for s in SYSTEMS if re.search(s[0], p["name"], re.I)), None)
        if not sysm:
            missing.append(p)
            continue
        _, page, imgs, desc, specs = sysm
        specs = dict(specs)
        m = re.search(r"(?:/|\s)(\d{4,5})(?:\s*mm)?\b", p["name"])
        if m and "tetőprofil" in p["name"]:
            specs["Hossz"] = f"{m.group(1)} mm"
        clear_images(p["slug"])
        images = []
        for i, u in enumerate(imgs, 1):
            img = Image.open(io.BytesIO(fetch(u))).convert("RGB")
            if "profil" in u:
                img = tight(img)
            images.append(save_image(img, p["slug"], i))
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": BASE + page, "sourceTitle": sysm[0], "matchedCode": sysm[0],
                                 "description": desc, "specs": specs, "images": images}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
