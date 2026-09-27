"""Közös segédfüggvények a beszállítói termékadatok letöltéséhez.

Az eredmény a src/data/termekadatok.json fájlba kerül (termék slug -> adatok),
a képek a public/termekkepek/ mappába WebP formátumban. A weboldal ezeket
automatikusan összefésüli az Excelből jövő alapadatokkal.
"""

import io
import json
import re
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "src/data/catalog.json"
ENRICHMENT = ROOT / "src/data/termekadatok.json"
IMAGE_DIR = ROOT / "public/termekkepek"
CACHE = ROOT / ".cache/letoltes"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

MAX_IMAGE = 1000  # px, a hosszabbik oldal


def load_products(supplier=None):
    products = json.loads(CATALOG.read_text())["products"]
    return [p for p in products if supplier is None or p["supplier"] == supplier]


def load_enrichment():
    return json.loads(ENRICHMENT.read_text()) if ENRICHMENT.exists() else {}


def save_enrichment(data):
    ENRICHMENT.write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + "\n")


def fetch(url, cache=True, timeout=40):
    """URL letöltése (gyorsítótárral), bájtokat ad vissza."""
    key = CACHE / re.sub(r"[^A-Za-z0-9._-]+", "_", url)[-180:]
    if cache and key.exists():
        return key.read_bytes()
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,hu;q=0.8"})
            data = urllib.request.urlopen(req, timeout=timeout).read()
            if cache:
                key.parent.mkdir(parents=True, exist_ok=True)
                key.write_bytes(data)
            return data
        except Exception as err:  # noqa: BLE001
            last = err
            time.sleep(2 * (attempt + 1))
    raise last


def save_image(img, slug, index=1):
    """PIL kép mentése WebP-be, fehér háttérre, max. MAX_IMAGE px. Visszaadja a webes útvonalat."""
    if isinstance(img, (bytes, bytearray)):
        img = Image.open(io.BytesIO(img))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE, MAX_IMAGE), Image.LANCZOS)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{slug}-{index}.webp"
    img.save(IMAGE_DIR / name, "WEBP", quality=82, method=6)
    return f"/termekkepek/{name}"


def code_candidates(product):
    """Lehetséges beszállítói kódok: a Termékkód oszlop és a megnevezésben szereplő kódszerű szavak."""
    out = []
    for c in re.split(r"[,;]\s*|\s+vagy\s+", product.get("supplierCode") or ""):
        c = c.strip()
        if not c:
            continue
        out.append(c)
        parts = [x for x in c.split("/") if x]
        if len(parts) > 1 and parts[0].isdigit():
            base = parts[0]
            out.append(base)
            for x in parts[1:]:
                if x.isdigit():
                    out.append(x if len(x) >= len(base) else base[: len(base) - len(x)] + x)
    for tok in re.findall(r"\b[A-Z]{0,5}\d{3,}[A-Z0-9./-]*\b", product["name"]):
        out.append(tok)
        if re.match(r"^J\d", tok):  # a Quadris "J" előtagja
            out.append(tok[1:])
    seen, result = set(), []
    for c in out:
        for v in (c, re.sub(r"[A-Z]+$", "", c)):
            if v and v not in seen and len(v) >= 3:
                seen.add(v)
                result.append(v)
    return result


# Gyakori idegen nyelvű kifejezések magyarítása a műszaki adatokban
TERMS = [
    (r"\bhliník/alumin\.?", "alumínium"),
    (r"\bhliník\b", "alumínium"),
    (r"\balumin(ium|um)?\b\.?", "alumínium"),
    (r"\belox\./eloxed\b", "eloxált"),
    (r"\beloxed\b", "eloxált"),
    (r"\bnerez/stain\.? ?steel\b", "rozsdamentes acél"),
    (r"\bstainless steel\b", "rozsdamentes acél"),
    (r"\bocel/steel\b", "acél"),
    (r"\bpozink\./galvanized\b", "horganyzott"),
    (r"\bgalvani[sz]ed\b", "horganyzott"),
    (r"\bplast/plastic\b", "műanyag"),
    (r"\bplastic\b", "műanyag"),
    (r"\bguma/rubber\b", "gumi"),
    (r"\bkus/piece\b", "db"),
    (r"\bpiece\b", "db"),
    (r"\bmeter\b", "méter"),
    (r"\bpravý/right\b", "jobb"),
    (r"\bľavý/left\b", "bal"),
    (r"\bnatur(al)?\b", "natúr"),
    (r"\bčierna lakovaná black painted\b", "fekete festett"),
    (r"\blakovan[ýá]/painted\b", "festett"),
    (r"\bpainted\b", "festett"),
    (r"\bčiern[yaá]/black\b", "fekete"),
    (r"\bčerven[áy]/red\b", "piros"),
    (r"\bžlt[áy]/yellow\b", "sárga"),
    (r"\bbiel[aey]/white\b", "fehér"),
    (r"\bstrieborn[áy]/silver\b", "ezüst"),
    (r"\bčierny/black\b", "fekete"),
    (r"\bbiely/white\b", "fehér"),
    (r"\bsivý/grey\b", "szürke"),
]

LABELS = {
    "materiál": "Anyag",
    "material": "Anyag",
    "povrch": "Felületkezelés",
    "surface": "Felületkezelés",
    "váha": "Tömeg",
    "weight": "Tömeg",
    "mj": "Mértékegység",
    "typ": "Típus",
    "type": "Típus",
    "rozmer": "Méret",
    "measure": "Méret",
    "dĺžka": "Hossz",
    "length": "Hossz",
    "farba": "Szín",
    "colour": "Szín",
    "color": "Szín",
    "nosnosť": "Teherbírás",
    "capacity": "Teherbírás",
    "hrúbka": "Vastagság",
    "šírka": "Szélesség",
    "width": "Szélesség",
    "výška": "Magasság",
    "height": "Magasság",
    "priemer": "Átmérő",
    "diameter": "Átmérő",
    "objem": "Térfogat",
    "volume": "Térfogat",
    "thickness": "Vastagság",
}


def hu_value(value):
    v = re.sub(r"\s+", " ", str(value or "")).strip()
    for pat, rep in TERMS:
        v = re.sub(pat, rep, v, flags=re.IGNORECASE)
    return v


def hu_label(label):
    l = re.sub(r"\s+", " ", str(label or "")).strip()
    low = l.lower()
    for key, hu in LABELS.items():
        if low.startswith(key) or f"/{key}" in low or f" {key}" in low:
            return hu
    return l
