"""Cimaplast (IT) – PVC tömítések, sarokprofilok, ütközők, ponyvás profilok.

A cimaplast.it HTML oldalai automatikus lekérést nem szolgálnak ki (a kapcsolatot bontják),
ezért a kategóriaoldalak tartalmát (cikkszám, kategória, kép útvonala) böngészőből olvastuk ki
és alább rögzítjük. A képek HTTP-n letölthetők. Cikkenkénti mérettáblázat a honlapon nincs;
a kategória anyag- és felhasználási leírása minden cikkre érvényes.

Használat: python3 scripts/termekadatok/cimaplast.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Cimaplast"
IMG = "http://www.cimaplast.it/templates/yootheme/cache/"
PAGE = "https://www.cimaplast.it/en/profiles/"

# kategória -> (oldal, anyag, leírás)
CATS = {
    "frigo": ("profiles-for-refrigerated-body", "gumi-PVC (koextrudált, merev PVC talppal)",
              "Hűtős felépítmények ajtótömítő profilja gumi-PVC-ből: alacsony hőmérsékleten is rugalmas, a merev részével együtt koextrudált."),
    "frigo-corner": ("profiles-for-refrigerated-body", "ütésálló PVC",
                     "Sarokprofil hűtős és dobozos felépítményekhez ütésálló PVC-ből."),
    "semi": ("semi-trailer-and-refrigerated-semi-trailer", "gumi-PVC / merev PVC (koextrudált)",
             "Ajtó- és kerettömítő profil félpótkocsikhoz és hűtős félpótkocsikhoz: alacsony hőmérsékleten is rugalmas gumi-PVC tömítőajak merev PVC talpon."),
    "curtain": ("profiles-for-semi-trailers", "gumi-PVC",
                "Ponyvás félpótkocsi profil gumi-PVC-ből: hidegben is rugalmas, biztosítja a vízzárást és az oldalponyva könnyű nyitását."),
    "bumper": ("lateral-bumpers", "", "Oldalfal-ütköző (ütközésvédő léc) az oldal- és hátfalak védelmére rakodáskor."),
    "tipper": ("profiles-for-tipper-and-float", "PVC", "Élvédő profil billenős és platós felépítményekhez a véletlen ütődések ellen."),
}
# cikkszám -> (kategória, kép)
ARTS = {
    "245C": ("frigo", "profili_per_camion_frigo_1-208a8766.png"),
    "246R": ("frigo", "profili_per_camion_frigo_2-22647dbc.png"),
    "253R": ("frigo", "profili_per_camion_frigo_9-2da7cad6.png"),
    "165C": ("frigo-corner", "profili_per_camion_frigo_7-255772d2.png"),
    "440C": ("frigo-corner", "profili_per_camion_frigo_11-c5057ab5.png"),
    "130C": ("frigo-corner", "profili_per_camion_frigo_13-e48b4333.jpg"),
    "156M": ("frigo-corner", "profili_per_camion_frigo_5-261c21be.png"),
    "158C": ("semi", "semirimorchi_e_camion_frigo_9-00e5a855.png"),
    "128C": ("semi", "semirimorchi_e_camion_frigo_3-0e83b689.png"),
    "127C": ("semi", "semirimorchi_e_camion_frigo_7-08151051.png"),
    "36C": ("semi", "semirimorchi_e_camion_frigo_13-7053ed40.png"),
    "115C": ("semi", "semirimorchi_e_camion_frigo_1-0dc8e5e5.png"),
    "111C": ("semi", "semirimorchi_e_camion_frigo_5-0b5e433d.png"),
    "70C": ("semi", "semirimorchi_e_camion_frigo_11-7318be2c.png"),
    "28C": ("semi", "semirimorchi_e_camion_frigo_15-758e18f4.png"),
    "194M": ("curtain", "profili_per_semirimorchi_1-20b53996.jpg"),
    "209M": ("curtain", "profili_per_semirimorchi_3-23fe6afa.jpg"),
    "289M": ("curtain", "profili_per_semirimorchi_5-26239f4e.jpg"),
    "110R": ("bumper", "parasponde_1-45534039.png"),
    "208P": ("bumper", "parasponde_3-46181355.png"),
    "114R": ("bumper", "parasponde_6-63ee76d1.jpg"),
    "86M": ("tipper", "profili_per_cassoni_1-952ba75d.jpg"),
    "131M": ("tipper", "profili_per_cassoni_3-9660f431.jpg"),
}
MATERIAL = {"110R": "merev PVC", "114R": "merev PVC", "208P": "HDPE (újrahasznosítható), kb. 30%-kal könnyebb a PVC változatnál",
            "156M": "gumi-PVC, előre vágott, öntapadós"}
COLOURS = [(r"\bW/B\b", "fehér talp / fekete tömítőajak"), (r"\bB/W\b", "fekete / fehér"), (r"\bN/N\b", "fekete"),
           (r"\bG\b|szürke|\bGR\b", "szürke"), (r"fekete|\bNE\b", "fekete")]


def code_of(p):
    for src in (p["supplierCode"] or "", p["name"]):
        for tok in re.findall(r"\b0*(\d{2,3}[A-Z])\b", src.upper()):
            if tok in ARTS:
                return tok
    if re.search(r"0156\s*(NE|MNH)|156M", p["name"] + (p["supplierCode"] or ""), re.I):
        return "156M"
    return None


def main():
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        art = code_of(p)
        if not art:
            missing.append(p)
            continue
        cat, img = ARTS[art]
        page, material, desc = CATS[cat]
        specs = {"Anyag": MATERIAL.get(art, material)} if MATERIAL.get(art, material) else {}
        w = re.search(r"(\d{2,3})\s*mm", p["name"])
        if w:
            specs["Méret"] = f"{w.group(1)} mm"
        for pat, hu in COLOURS:
            if re.search(pat, p["name"]):
                specs["Szín"] = hu
                break
        if cat in ("frigo", "semi", "curtain"):
            specs["Tulajdonság"] = "alacsony hőmérsékleten is rugalmas"
        clear_images(p["slug"])
        images = []
        try:
            images.append(save_image(fetch(IMG + img), p["slug"], 1))
        except Exception as err:  # noqa: BLE001
            print("  képhiba:", img, err)
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": PAGE + page, "sourceTitle": f"Art. {art}", "matchedCode": art,
                                 "description": desc, "specs": specs, "images": images}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
