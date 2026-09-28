"""TAKLER (IT) – az MGú aláfutásgátló konzolok (Ital Accessori beszállítónál) a Takler Trucks & Trailers oldaláról.

A Quadris-féle beszállítói kódok a Takler cikkszámai: TK3021 (430 mm), TK3023 (572 mm); a 710 mm-es tételnél
az Excelben "123025" áll, a Takler-kód TK3025 (a hossz egyezik). Mindhárom a „Steel ZM adjustable bracket for side
protection” (ZM bevonatú acél, állítható oldalsó aláfutásgátló konzol) változata:
https://trucksandtrailers.taklergroup.com/product/44/steel-zm-adjustable-bracket-for-side-protection
Kép: a négy hosszt együtt mutató fotóból az adott hosszú konzol kivágva, valamint a méretjelölő rajz. Kézzel ellenőrizve.

Használat: python3 scripts/termekadatok/takler.py
"""

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Takler"
PAGE = "https://trucksandtrailers.taklergroup.com/product/44/steel-zm-adjustable-bracket-for-side-protection"
IMG = "https://takler.anticipa.io/public/uploads/takler/image/product/"
GROUP = IMG + "08_07_2019_17_04_54_TK3021_23_25_29.png"  # balról jobbra: TK3021, TK3023, TK3025, TK3029
SCHEMA = IMG + "TK3021/schema.png"
COMMON = {"Megnevezés (gyári)": "Steel ZM adjustable bracket for side protection – állítható konzol oldalsó aláfutásgátlóhoz",
          "Anyag": "acél, ZM (cink-magnézium) bevonattal", "Szélesség (L)": "54,7 mm", "Konzollap szélessége (B)": "140 mm",
          "Konzollap magassága (S)": "155 mm", "Kialakítás": "csavar és csap nélküli nyitó-záró mechanizmus",
          "Jóváhagyás": "E1173R-011025; E1173R-011027 (ECE R73, max. 3000 mm tengelytáv)"}
# slug -> (Takler-kód, oszlop a csoportképen, magasság, tömeg a Takler táblázatából)
ITEMS = {
    "302321-mgu-alafutasgatlo-konzol-430-mm": ("TK3021", 0, "430 mm", "0,8 kg"),
    "302323-mgu-alafutasgatlo-konzol-572-mm": ("TK3023", 1, "572 mm", "1,8 kg"),
    "302325-mgu-alafutasgatlo-konzol-710-mm": ("TK3025", 2, "710 mm", "2 kg"),
}


def load(url):
    return Image.open(io.BytesIO(fetch(url))).convert("RGBA")


def flatten(img, pad=0.12):
    bg = Image.new("RGB", img.size, "white")
    bg.paste(img, mask=img.split()[-1])
    w, h = bg.size
    m = int(max(w, h) * pad)
    out = Image.new("RGB", (w + 2 * m, h + 2 * m), "white")
    out.paste(bg, (m, m))
    return out


def objects(img):
    """A csoportkép külön álló tárgyai balról jobbra (alfa-csatorna alapján)."""
    a = np.asarray(img)[:, :, 3] > 10
    cols, runs, start = a.any(0), [], None
    for x, v in enumerate(list(cols) + [False]):
        if v and start is None:
            start = x
        elif not v and start is not None:
            ys = np.where(a[:, start:x].any(1))[0]
            runs.append(img.crop((start, ys.min(), x, ys.max() + 1)))
            start = None
    return runs


def main():
    group = objects(load(GROUP))
    assert len(group) == 4, len(group)
    schema = flatten(load(SCHEMA), 0.06)
    existing = load_enrichment()
    enrichment = {}
    for p in load_products():
        item = ITEMS.get(p["slug"])
        other = existing.get(p["slug"], {})
        if not item or (other.get("images") and other.get("source") != SOURCE):
            continue
        code, idx, height, weight = item
        clear_images(p["slug"])
        images = [save_image(flatten(group[idx]), p["slug"], 1), save_image(schema, p["slug"], 2)]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceUrl": PAGE, "sourceTitle": f"Takler: Steel ZM adjustable bracket ({code})",
                                 "matchedCode": code,
                                 "specs": {"Cikkszám (gyártói)": code, **COMMON, "Magasság (H)": height, "Tömeg": weight},
                                 "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
