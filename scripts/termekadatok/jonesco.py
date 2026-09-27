"""Jonesco (UK) – sárvédők, sárfogók, felfogatások, szerszámosládák.

A Quadris-kódok a Jonesco régi / rövidített jelöléseit használják, ezért átírjuk őket:
  J09, J27, J43B …  -> HL09, HL27, HL43B   (HighGard egyíves sárvédő)
  JVG47, JVG26A     -> HL47, HL26A         (a HighGard régi neve VG volt)
  JHLS47            -> HLS47               (HighGard szekció)
  J27F, JX06F, JF4070, JF61122           -> változatlan (J-Wing / XGard / sárfogó)
  J4030, J6540, JF6092 -> 214030, 216540, 216092 (sima sárfogó: 21 + szélesség + magasság)
  JBX45, JBX80, JBZ60 … -> JBZ450, JBZ800, JBZ600 (szerszámosláda: szélesség cm -> mm)
  JBX400-D          -> JBC40               (400 mm-es kompakt tárolóláda)
  KITXP42 -> KITXPF42, JS43EB -> JS43E (festett fekete kivitel)

Használat: python3 scripts/termekadatok/jonesco.py
"""

import html
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "JONESCO"
BASE = "https://jonesco-plastics.com"
SECTIONS = ["mudguards", "mudflaps", "fixing-systems", "on-board-storage"]

HEADERS = {
    "internal width": "Belső szélesség [mm]",
    "external width": "Külső szélesség [mm]",
    "radius": "Ívsugár [mm]",
    "length": "Hossz [mm]",
    "span": "Fesztáv [mm]",
    "height": "Magasság [mm]",
    "valance": "Oldalperem [mm]",
    "width": "Szélesség [mm]",
    "depth": "Mélység [mm]",
    "h x w x d": "Méret (M×Sz×Mé) [mm]",
    "aperture": "Nyílás [mm]",
    "weight": "Tömeg [kg]",
    "max. load": "Max. terhelés [kg]",
    "max load": "Max. terhelés [kg]",
    "capacity": "Űrtartalom [l]",
    "stay": "Tartócső átmérő [mm]",
    "diameter": "Átmérő [mm]",
    "fixing kit": "Szerelőkészlet",
}

DESCRIPTIONS = {
    "single-arch-highgard": "HighGard egyíves sárvédő mintázott, strukturált felülettel és ezüst láthatósági csíkkal. Könnyű, ütésálló, extrém időjárásban is bevált; ZPA és XPF felfogató rendszerekkel kompatibilis.",
    "section-highgard": "HighGard sárvédő szekció (rövid / részleges ív) mintázott felülettel, ezüst láthatósági csíkkal.",
    "single-arch-xgard": "XGard nehéz kivitelű, rotációs öntésű MDPE sárvédő bordázott, matt felülettel – billencsekhez, mixerekhez, erdészeti járművekhez.",
    "flat-top-xgard": "XGard lapos tetejű (csapott) sárvédő, nehéz kivitelű rotációs öntésű MDPE-ből.",
    "flat-top-j-wing": "J-Wing lapos tetejű (csapott) sárvédő fényes, ütésálló felülettel, extrém időjárási körülményekre.",
    "plain-mudflaps": "Sima gumi sárfogó lap, a sárvédő szélességére vágható.",
    "antispray-mudflaps": "Permetcsökkentő (anti-spray) sárfogó lap: a belső oldali szálak megtörik a vízpermetet, javítva a mögöttes forgalom látási viszonyait. EU-típusjóváhagyással.",
    "xpf-fixing-kit": "XPF felső bilincses sárvédő felfogató készlet (4 db, egy sárvédőhöz, két tartócsőre), korrózióálló kötőelemekkel.",
    "stay-with-hexagonal-flange": "Horganyzott acél sárvédő tartócső központi hatlapfejes csavaros rögzítéssel, műanyag végsapkával.",
    "stay-with-triangular-flange": "Horganyzott acél sárvédő tartócső háromlyukas (háromszög) karimával, műanyag végsapkával.",
    "storage": "Zárható műanyag szerszámosláda vízálló tömítéssel, 180°-ban nyíló fedéllel és süllyesztett fogantyúkkal. UTAC-jóváhagyás (E2 73 R): az oldalvédőbe is beépíthető.",
    "compact-storage-box": "Zárható kompakt tárolóláda vízálló tömítéssel, 180°-ban nyíló fedéllel – kerékívek közé is ideális.",
}


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def label(head):
    h = head.lower().replace("(mm)", "").replace("(kg)", "").replace("(l)", "").replace(")", "").strip()
    for key, hu in HEADERS.items():
        if h.startswith(key):
            return hu
    return ""


def family_pages():
    for section in SECTIONS:
        page = fetch(f"{BASE}/products/commercial-vehicle/{section}").decode("utf-8", "ignore")
        for href in sorted(set(re.findall(rf'href="(/products/commercial-vehicle/{section}/[^"]+)"', page))):
            yield href.rsplit("/", 1)[-1], BASE + href


def parse_family(name, url):
    page = fetch(url).decode("utf-8", "ignore")
    images = []
    for src in re.findall(r'src="(/img/http/products/commercial-vehicle/[^"]+)"', page):
        # /img/http/<eredeti útvonal>.jpg/<hash>/<név>.webp -> az eredeti (nagyobb) kép a tárhelyen
        orig = unquote(src.split("/img/http/", 1)[1].rsplit("/", 2)[0])
        u = f"https://jonesco-website-bucket.ams3.digitaloceanspaces.com/{orig}"
        if all(u != x[0] for x in images):
            images.append((u, BASE + src))
    items = {}
    for table in re.findall(r"<table.*?</table>", page, re.S):
        heads = [text(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(cells) < 2 or not re.fullmatch(r"[A-Z0-9/-]{3,}", cells[0]):
                continue
            specs = {}
            for h, v in zip(heads[1:], cells[1:]):
                if label(h) and v and v != "-":
                    specs[label(h)] = v.replace(" x ", "×")
            items[cells[0]] = {"specs": specs, "images": images, "url": url, "family": name}
    return items


def candidates(p):
    toks = [t.upper() for t in re.split(r"[,\s]+", p["supplierCode"] or "") if t]
    toks.append(p["slug"].split("-")[0].upper())
    out = []
    for t in toks:
        out.append(t)
        if m := re.fullmatch(r"KITXP(\d+)", t):
            out.append(f"KITXPF{m[1]}")
        if m := re.fullmatch(r"JS(\w+?)B", t):
            out.append(f"JS{m[1]}")
        if m := re.fullmatch(r"JHLS(\w+)", t):
            out.append(f"HLS{m[1]}")
        if m := re.fullmatch(r"J?VG(\w+)", t):
            out.append(f"HL{m[1]}")
        if m := re.fullmatch(r"J(\d{2}[A-Z]?)", t):
            out.append(f"HL{m[1]}")
        if m := re.fullmatch(r"JF?(\d{4})", t):
            out.append(f"21{m[1]}")
        if m := re.fullmatch(r"JB[XZ](\d+)", t):
            out.append(f"JBZ{int(m[1]) * 10}")
        if re.fullmatch(r"JBX400(-?D)?", t):
            out.append("JBC40")
    return out


def pick_images(item, code):
    """A kódhoz tartozó kép előre, utána a család általános képei."""
    imgs = item["images"]
    own = [x for x in imgs if re.search(rf"[-_(/]{re.escape(code)}[_.]", x[0], re.I)]
    rest = [x for x in imgs if x not in own]
    return (own + rest)[:3]


def main():
    catalog = {}
    for name, url in family_pages():
        try:
            for code, item in parse_family(name, url).items():
                catalog.setdefault(code, item)
        except Exception as err:  # noqa: BLE001
            print("  oldalhiba:", url, err)
    print(f"  Jonesco webes táblázatok: {len(catalog)} cikkszám")

    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        code = next((c for c in candidates(p) if c in catalog), None)
        if not code:
            missing.append(p)
            continue
        item = catalog[code]
        clear_images(p["slug"])
        saved = []
        for n, (orig, small) in enumerate(pick_images(item, code), start=1):
            for u in (orig, small):
                try:
                    saved.append(save_image(fetch(u), p["slug"], n))
                    break
                except Exception:  # noqa: BLE001
                    continue
        fam = item["family"]
        desc = DESCRIPTIONS.get(fam) or (DESCRIPTIONS["storage"] if fam.endswith("toolbox") else "")
        enrichment[p["slug"]] = {
            "source": SUPPLIER,
            "sourceUrl": item["url"],
            "sourceTitle": f"{code} ({fam})",
            "matchedCode": code,
            "description": desc,
            "specs": item["specs"],
            "images": saved,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>10}  {p['slug']}")


if __name__ == "__main__":
    main()
