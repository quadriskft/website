"""BMC Flexpar (IT) – műanyag sárvédők és szerszámosládák.

Forrás: a gyártó termékoldalainak fő képe (og:image) és a 2025-ös termékkatalógus (PDF) méret- és
tömegtáblázata. A Quadris-tételeket a méretek (B szélesség, L ívhossz, S húr) alapján párosítjuk a katalógus
cikkszámaival; a „fehér csíkkal” változat a White Line család.

Használat: python3 scripts/termekadatok/bmc.py
"""

import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "BMC Flexpar"
BASE = "https://www.bmcflexpar.com"
PDF = BASE + "/wp-content/uploads/2025/12/BMC-catalogo-prodotti.pdf"
PAGES = {"C": "/flex-par-c-2/", "CW": "/flex-par-c-white-line/", "FT": "/flex-par-ft/", "FTW": "/flex-par-ft/",
         "EVO": "/toolbox-evolution/", "PIO": "/toolbox-pioneer/"}
# Quadris slug -> (család, katalógus-cikkszám)
MAP = {
    "j50001-ives-sarvedo-1380-880-400": ("C", "PM400.000"),
    "j50002-ives-sarvedo-1380-880-450": ("C", "PM450.030"),
    "j50002-b-ives-sarvedo-feher-csikkal-1380-880-450": ("CW", "PM450.130"),
    "j50003-ives-sarvedo-1380-880-270": ("C", "PM270.000"),
    "j50003-b-ives-sarvedo-feher-csikkal-1380-880-270": ("CW", "PM270.100"),
    "j50019-450ft-csapott-teteju-sarvedo": ("FT", "PM450.020"),
    "j50019-b-450ft-csapott-teteju-sarvedo-feher-csikkal": ("FTW", "PM450.120"),
    "j50027-280ft-csapott-teteju-sarvedo": ("FT", "PM280.000"),
    "j50027-b-280ft-csapott-teteju-sarvedo-feher-csikkal": ("FTW", "PM280.100"),
    "j504335-szerszamos-lada-500x430x350-mm": ("EVO", "PT500.100"),
    "j605040-szerszamos-lada-600x500x400-mm": ("EVO", "PT600.100"),
    "j804550-szerszamos-lada-800x450x500-mm": ("PIO", "PT800.000"),
}
MUDGUARD = ("Egytengelyes sárvédő fröccsöntött kopolimer polipropilénből: sima felület, magas és alacsony hőmérsékleten is "
            "ellenálló, vegyszer- és gázolajálló, UV-stabilizált. Kis tömege egyszerűsíti a szállítást és a szerelést.")
DESC = {
    "C": MUDGUARD, "CW": MUDGUARD + " Elegáns fehér szegéllyel.",
    "FT": MUDGUARD.replace("Egytengelyes sárvédő", "Lapos tetejű sárvédő"),
    "FTW": MUDGUARD.replace("Egytengelyes sárvédő", "Lapos tetejű sárvédő") + " Fehér szegéllyel.",
    "EVO": "Szerszámosláda fröccsöntött kopolimer polipropilénből: rezgésálló fogantyú kettős zárással, kulccsal és porvédő sapkával; "
           "körbefutó fedél és vízzáró tömítés, megerősített zsanér, hidegben is nagy mechanikai szilárdság, UV-stabilizált.",
    "PIO": "Szerszámosláda fröccsöntött kopolimer polipropilénből, több ponton záródó fogantyúval; körbefutó fedél és vízzáró tömítés, "
           "megerősített zsanér, UV-stabilizált. Megfelel az ECE R73.01 oldalvédelmi előírásnak.",
}


def catalog_rows():
    doc = pymupdf.open(stream=fetch(PDF), filetype="pdf")
    rows = {}
    for pg in doc:
        t = [x.strip() for x in pg.get_text().split("\n")]
        for j, x in enumerate(t):
            if re.fullmatch(r"P[MT]\d{3}\.\d{3}", x):
                rows[x] = t[j + 1:j + 5]
    return rows


def main():
    rows = catalog_rows()
    imgs = {}
    for fam, path in PAGES.items():
        html = fetch(BASE + path).decode("utf-8", "ignore")
        m = re.search(r'og:image" content="([^"]+)', html)
        imgs[fam] = m.group(1) if m else None
    enrichment = {}
    for p in load_products(SUPPLIER):
        if p["slug"] not in MAP:
            continue
        fam, art = MAP[p["slug"]]
        a, b, c, kg = rows[art]
        if fam in ("EVO", "PIO"):
            specs = {"Méret (H × M × Ma)": f"{a} × {b} × {c} mm"}
        else:
            specs = {"Szélesség (B)": f"{a} mm", "Ívhossz (L)": f"{b} mm", "Húr (S)": f"{c} mm (±50 mm)"}
        specs.update({"Anyag": "kopolimer polipropilén (PP)", "Szín": "matt fekete" + (", fehér szegéllyel" if fam.endswith("W") else ""),
                      "Tömeg": f"{kg} kg"})
        clear_images(p["slug"])
        images = [save_image(fetch(imgs[fam]), p["slug"], 1)] if imgs.get(fam) else []
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": BASE + PAGES[fam], "sourceTitle": art, "matchedCode": art,
                                 "description": DESC[fam], "specs": specs, "images": images}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(MAP)} egyezés")


if __name__ == "__main__":
    main()
