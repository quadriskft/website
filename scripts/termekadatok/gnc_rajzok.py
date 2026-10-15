"""G&C tetőventilátorok és belső szellőzők – méretezett műszaki rajz minden cikkszámhoz (a Quadris kérésére).

Forrás: a G&C honlapjának méretrajzai („…-tekening”), ahol ezek méretszámok nélküliek vagy hiányoznak, ott a
G&C termékkatalógus (GC-PRODUCTBROCHURE-06-2013) ill. a termékadatlap vektoros rajza 400 dpi-vel kivágva.
A rajz a termék fotója után, második képként kerül a listába (a meglévő képek maradnak).

Használat: python3 scripts/termekadatok/gnc_rajzok.py   (utána kep_sorrend.py)
"""

import io
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, fetch, load_enrichment, save_image, update_enrichment  # noqa: E402

UP = "https://gnc-systems.com/wp-content/uploads/"
BROCHURE = UP + "2024/01/GC-PRODUCTBROCHURE-06-2013-LR-{}.pdf"
# rajz -> forrás: ("web", útvonal) vagy ("pdf", url, kivágás [pt])
DRAWINGS = {
    "le-mans": ("web", "2023/12/02-2200-tekening-scaled.jpg"),
    "le-mans-ll": ("web", "2024/01/02-4200-tekening.jpg"),
    "manualis": ("pdf", BROCHURE.format("11"), (292, 192, 596, 305)),
    "turbo-ii": ("pdf", BROCHURE.format("10-1"), (290, 168, 563, 300)),
    "turbo-iii": ("pdf", UP + "2024/01/GC-PRODUCTSHEET-02-6000-02-6100-zonder-label.pdf", (300, 145, 570, 335)),
    "belso-takaro": ("web", "2024/01/35-2120-tekening.jpg"),
    "manualis-takaro": ("web", "2024/01/35-2400-tekening-scaled.jpg"),
    "flower-power": ("web", "2024/01/35-2820-tekening-scaled.jpg"),
}
PRODUCTS = {
    "le-mans": ["le-mans-tetoventilator-12v", "02-2200-zw-le-mans-tetoventilator-12v", "le-mans-tetoventilator-24v",
                "tetoventillator-motor-nelkul-abs-feher"],
    "le-mans-ll": ["gc-le-mans-ll"],
    "manualis": ["tetoventilator-manualis-feher", "tetoventilator-manualis-fekete"],
    "turbo-ii": ["turbo-ii-tetoventilator-feher", "turbo-ii-tetoventilator-fekete"],
    "turbo-iii": ["turbo-iii-tetoventilator-feher", "turbo-iii-tetoventilator-fekete"],
    "belso-takaro": ["ventillator-belso-takaro-szurke", "ventillator-belso-takaro", "ventillator-belso-takaro-12-24v-led",
                     "12v-led-ventillator-belso-takaro"],
    "manualis-takaro": ["manualis-belso-takaro-feher", "manualis-belso-takaro-szurke", "ventillator-also-takaro-elem-12-24v-feher"],
    "flower-power": ["belso-takaro-flower-power-szurke", "belso-12v-os-led-takaro-flower-power-feher",
                     "belso-24-v-os-led-vilagitassal-flower-power-feher", "belso-12v-os-led-takaro-flower-power-szurke",
                     "belso-24-v-os-led-vilagitassal-flower-power-szurke"],
}


def trim(img, margin=24):
    a = np.asarray(img.convert("L")) < 235
    ys, xs = np.where(a)
    return img.crop((max(xs.min() - margin, 0), max(ys.min() - margin, 0),
                     min(xs.max() + margin, img.width), min(ys.max() + margin, img.height)))


def drawing(src):
    if src[0] == "web":
        img = Image.open(io.BytesIO(fetch(UP + src[1]))).convert("RGB")
    else:
        page = pymupdf.open(stream=fetch(src[1]), filetype="pdf")[0]
        pix = page.get_pixmap(dpi=400, clip=pymupdf.Rect(*src[2]))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return trim(img)


def main():
    data = load_enrichment()
    extended = json.loads((ROOT / "src/data/bovitett.json").read_text()).get("products", [])
    extended += json.loads((ROOT / "src/data/catalog.json").read_text())["products"]  # a képtelen Excel-termékek is
    updates = {}
    for key, src in DRAWINGS.items():
        img = drawing(src)
        for slug in PRODUCTS[key]:
            e = data.get(slug)
            if e is None:  # a bővített kínálatból jött termék: a meglévő fotója marad elöl
                ext = next((p for p in extended if p["slug"] == slug), None)
                if ext is None:
                    print("  nincs termék:", slug)
                    continue
                e = {"source": "G&C rajz", "sourceUrl": "", "sourceTitle": "", "specs": {}, "images": list(ext.get("images", []))}
            url = save_image(img, slug, "meretrajz")
            imgs = [u for u in e.get("images", []) if u != url]
            e["images"] = imgs[:1] + [url] + imgs[1:]  # a fotó után
            updates[slug] = e
            print(slug, key)
    update_enrichment(updates)


if __name__ == "__main__":
    main()
