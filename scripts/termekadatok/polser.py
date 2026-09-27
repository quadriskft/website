"""Polser (TR) – Frigoser üvegszálas poliészter (GRP) lemezek.

Forrás: polser.com Frigoser termékoldal + Frigoser-ENG.pdf adatlap. Az adatlap vastagságonként
adja a tömeget, üvegszál-tartalmat és a szilárdsági értékeket; a lemez szélessége és felülete a
Quadris megnevezéséből jön. A Polydet és POL/Panel termékek nem a Polser kínálatából valók
(a honlapon nem szerepelnek) – ezekhez csak a megnevezésben lévő méretek kerülnek.

Használat: python3 scripts/termekadatok/polser.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "POLSER"
PAGE = "https://polser.com/en/products/automotive-industry/frigoser"
IMAGES = ["https://polser.com/media/k2/items/cache/frigoser-anaresim_595caf4e5e2ad_XL.jpg",
          "https://polser.com/images/FRIGOSER/frigoser002.jpg"]
# vastagság -> (tömeg g/m², üvegszál g/m², hajlítószilárdság MPa, szakítószilárdság MPa) – Frigoser-ENG.pdf
TABLE = {"1,3": ("1860", "465", "150", "70"), "1,5": ("2000", "500", "160", "75"),
         "1,8": ("2400", "600", "165", "80"), "2,0": ("2700", "675", "170", "85")}
COMMON = {
    "Anyag": "üvegszálas poliészter (GRP), gélbevonatos",
    "Üvegszál-tartalom": "≥ 25%",
    "Barcol-keménység": "45",
    "Sűrűség": "1,4–1,5 g/cm³",
    "Vízfelvétel": "0,3%",
    "Hőállóság": "-40 °C … +120 °C",
    "Szállítási forma": "tábla max. 12 m, tekercs 60–300 m",
    "Szín": "RAL színek szerint",
    "Megfelelőség": "ATP (élelmiszerrel érintkezhet), TÜV SÜD, HACCP",
}
DESC = ("Frigoser üvegszálas poliészter burkolólemez száraz és hűtős felépítményekhez, buszokhoz, lakóautókhoz: "
        "ütésálló, rugalmas, korrózió- és vegyszerálló, könnyű, higiénikus és könnyen tisztítható felület.")


def main():
    enrichment, skipped = {}, []
    for p in load_products(SUPPLIER):
        name = p["name"]
        specs = {}
        m = re.search(r"(\d+[,.]\d)\s*x\s*(\d{3,4})", name) or re.search(r"(\d{3,4})\s*/\s*(\d+[,.]\d)", name)
        if m:
            a, b = m.groups()
            thick, width = (a, b) if "," in a or "." in a else (b, a)
            thick = thick.replace(".", ",")
            specs["Vastagság"] = f"{thick} mm"
            specs["Szélesség"] = f"{width} mm"
        surf = re.search(r"High Gloss|High Impact|Corona|Roughened|Performance Plus", name, re.I)
        if "Frigoser" not in name:
            if specs:
                enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": "", "sourceTitle": name, "matchedCode": "",
                                         "specs": {**specs, **({"Felület": surf.group(0)} if surf else {})}, "images": []}
            skipped.append(p)
            continue
        t = TABLE.get(specs.get("Vastagság", "").replace(" mm", ""))
        if t:
            specs.update({"Tömeg": f"{t[0]} g/m²", "Üvegszál": f"{t[1]} g/m²", "Hajlítószilárdság": f"{t[2]} MPa",
                          "Szakítószilárdság": f"{t[3]} MPa"})
        specs["Felület"] = "High Gloss (magasfényű gélbevonat)" if "gloss" in name.lower() else "High Impact (fokozott ütésállóság)"
        specs.update(COMMON)
        clear_images(p["slug"])
        imgs = []
        for n, u in enumerate(IMAGES, 1):
            try:
                imgs.append(save_image(fetch(u), p["slug"], n))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", u, err)
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": PAGE, "sourceTitle": "Frigoser", "matchedCode": "",
                                 "description": DESC, "specs": specs, "images": imgs}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)} termék ({len(skipped)} nem Frigoser – csak méretadat)")


if __name__ == "__main__":
    main()
