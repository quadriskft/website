"""Plastic Padana (IT) – sárfogó gumik, StopSpray sárvédő lapok.

A gyártó honlapjának (plasticpadana.it) termékképei a mintadarabot a saját logójukkal mutatják;
a Quadris logó nélküli, sima fekete lapokat forgalmaz, ezért a képről a logót eltávolítjuk
(a logó pixeleit a lap saját színével töltjük ki). A méreteket a Quadris-megnevezés adja,
az anyagot és a keménységet a gyártói termékoldal.

Használat: python3 scripts/termekadatok/plasticpadana.py
"""

import io
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "Plastic Padana"
UP = "https://plasticpadana.it/wp-content/uploads/2024/12/"
PAGE = "https://plasticpadana.it/prodotto/"
FAMILIES = {
    "truck": (UP + "PARASPRUZZI-autocarri-furgoni.png", "paraspruzzi-per-autocarri-logo-liscio/",
              "Sárfogó gumi tehergépkocsikhoz és pótkocsikhoz, sima fekete PVC, felső rögzítőfuratokkal.", {"Vastagság": "3,8 mm"}),
    "trailer": (UP + "Paraspruzzi-carrelli-furgoni03.png", "i/",
                "Sárfogó gumi utánfutókhoz és kisteherautókhoz, sima fekete PVC, bordázott szélekkel.", {"Vastagság": "5,5 mm"}),
    "reducible": (UP + "PARASPRUZZI-autocarri-rimorchi07.png", "paraspruzzi-serie-riducibile-per-autocarri-logo-rilievo/",
                  "Méretre vágható („riducibile”) sárfogó lap tehergépkocsikhoz és pótkocsikhoz, fekete PVC, rögzítőlécekkel.",
                  {"Vastagság": "6 mm", "Kivitel": "szélessége méretre vágható"}),
    "stopspray": (UP + "codice470.png", "stop-spray-per-parafango-logo-liscio-cod-470/",
                  "StopSpray sárvédő lap: a felcsapódó permetet megfogó, felül bővülő fekete PVC lap a sárvédő alá.", {"Kivitel": "StopSpray (permetgátló)"}),
}
MAP = {"J24300": "trailer", "J260260": "trailer", "J450300": "truck", "J504530": "reducible", "JF556045": "stopspray"}


def remove_logo(img, side=0.04):
    """A lap belsejében lévő világos (fehér/szürke) és piros logó-pixelek kitöltése a lap színével."""
    rgba = img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    bg.alpha_composite(rgba)
    rgb = np.asarray(bg.convert("RGB")).astype(int)
    gray = rgb.mean(axis=2)
    flap = gray < 110
    ys, xs = np.where(flap)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    h, w = y1 - y0, x1 - x0
    inner = np.zeros(flap.shape, bool)
    inner[y0 + int(h * 0.1):y1 - int(h * 0.04), x0 + int(w * side):x1 - int(w * side)] = True
    base = np.median(rgb[inner & flap], axis=0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    sat = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    # minden, ami a lap színétől érdemben eltér (fehér/szürke/piros logó és élsimítása)
    logo = inner & ((np.abs(gray - base.mean()) > 7) | (sat > 25))
    logo = ndimage.binary_opening(logo, iterations=1) | (inner & (sat > 40))
    lab, n = ndimage.label(ndimage.binary_dilation(logo, iterations=2))
    keep = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndimage.find_objects(lab)):
        # a lap szélén futó bordák / furatok hosszú, keskeny elemek – azok maradnak
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        keep[i + 1] = not (hh > 0.6 * h and ww < 0.05 * w)
    logo = keep[lab] & inner
    logo = ndimage.binary_dilation(logo, iterations=3) & inner
    fill = rgb.astype(float).copy()
    fill[logo] = base
    for c in range(3):
        fill[..., c] = ndimage.gaussian_filter(fill[..., c], 18)
    out = rgb.astype(float)
    noise = np.random.default_rng(1).normal(0, 1.2, out.shape)
    out[logo] = np.clip(fill[logo] + noise[logo], 0, 255)
    im = Image.fromarray(out.astype(np.uint8))
    return im.crop((max(x0 - 12, 0), max(y0 - 12, 0), min(x1 + 12, im.width), min(y1 + 12, im.height)))


def main():
    imgs = {k: remove_logo(Image.open(io.BytesIO(fetch(v[0]))), 0.16 if k == "reducible" else 0.04) for k, v in FAMILIES.items()}
    enrichment = {}
    products = load_products(SUPPLIER)
    for p in products:
        m = re.match(r"(J[F]?\d+)", p["name"])
        fam = MAP.get(m.group(1)) if m else None
        if not fam:
            continue
        _, page, desc, extra = FAMILIES[fam]
        size = re.search(r"(\d{3}(?:/\d{3})?)\s*x\s*(\d{3})", p["name"])
        specs = {"Méret": f"{size.group(1)} × {size.group(2)} mm"} if size else {}
        specs.update({"Anyag": "PVC, fekete", "Keménység": "80 ± 5 Shore A", **extra, "Felület": "sima, logó nélkül"})
        clear_images(p["slug"])
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": PAGE + page, "sourceTitle": fam, "matchedCode": "",
                                 "description": desc, "specs": specs, "images": [save_image(imgs[fam], p["slug"], 1)]}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)}")


if __name__ == "__main__":
    main()
