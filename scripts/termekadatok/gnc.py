"""G&C Systems (NL) – tetőventilátorok, tetőablakok, szellőzők, LED világítás.

Minden termékoldal fejlécében ott vannak a termék cikkszámai (pl. "35-2700 / 35-2710 / 35-2720"),
és minden termékhez tartozik egy műszaki adatlap PDF (a G&C prospektus egy oldala) táblázattal.
Az Excel-termék ahhoz az oldalhoz tartozik, amelynek FEJLÉCÉBEN szerepel a kódja (a szövegben
említett kód nem elég: pl. a rács leírása megemlíti a hozzá illő ventilátort). A műszaki adatok a
PDF-táblázat pontosan a kódhoz tartozó sorából jönnek.

Használat: python3 scripts/termekadatok/gnc.py
"""

import html
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "G&C termékek"
BASE = "https://gnc-systems.com"
CODE = re.compile(r"\b\d{2}-\d{4}(?:-[A-Z0-9]{1,4})?\b")

HEADERS = [  # (a fejléc kezdete kisbetűvel, magyar címke)
    ("part", None), ("description", None),
    ("voltage", "Feszültség [V]"), ("air flow", "Légszállítás [m³/h]"), ("air\nflow", "Légszállítás [m³/h]"),
    ("watt", "Teljesítmény [W]"), ("nominal speed", "Fordulatszám [1/perc]"), ("noise", "Zajszint [dB(A)]"),
    ("function", "Működés"), ("rooftop opening", "Tetőkivágás [mm]"), ("roof opening", "Tetőkivágás [mm]"),
    ("material\nroofring", "Anyag (tetőgyűrű)"), ("material\ncover", "Anyag (fedél)"), ("material", "Anyag"),
    ("dimensions", "Méret"), ("dimension", "Méret"), ("size", "Méret"), ("aperture", "Nyílásméret [mm]"),
    ("radius", "Sarokrádiusz"), ("glass", "Üveg"), ("colour", "Szín"), ("color", "Szín"),
    ("current", "Áramfelvétel"), ("power", "Teljesítmény"), ("lumen", "Fényáram [lm]"), ("led", "LED-ek száma"),
    ("weight", "Tömeg"), ("roof thickness", "Tetővastagság [mm]"), ("thickness", "Vastagság"),
    ("length", "Hossz"), ("width", "Szélesség"), ("height", "Magasság"), ("diameter", "Átmérő"),
    ("ip", "IP védettség"), ("light colour", "Fényszín"),
]
VALUES = [
    (r"Suction\s*/\s*Blowing", "szívó / fúvó"), (r"\bSuction\b", "szívó"), (r"\bBlowing\b", "fúvó"),
    (r"without motor", "motor nélkül"), (r"Light Grey", "világosszürke"), (r"\bGrey\b", "szürke"),
    (r"\bWhite\b", "fehér"), (r"\bBlack\b", "fekete"), (r"\bClear\b", "víztiszta"), (r"\bSmoke\b", "füstszínű"),
    (r"UV Transmission", "UV-áteresztés"), (r"Heat Transmission", "hőáteresztés"), (r"Light Transmission", "fényáteresztés"),
    (r"(\d)\+\s*-\s*\d+\s*\d+", r"\1"),  # "530+ -5 0" tűrésjelölés
    (r"\bwarm white\b", "melegfehér"), (r"\bcold white\b", "hidegfehér"),
]


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def hu(v):
    v = re.sub(r"\s+", " ", str(v or "")).strip()
    for pat, rep in VALUES:
        v = re.sub(pat, rep, v, flags=re.I)
    return v


def tidy(lab, v):
    """A PDF-táblázat tipikus kiolvasási hibáinak javítása."""
    if lab.startswith("Nyílásméret"):
        nums = [n for n in re.findall(r"\d+", v) if int(n) >= 100]
        return " × ".join(nums[:2]) if len(nums) >= 2 else v
    if lab.startswith("Feszültség"):
        v = re.sub(r"^(\d+(?:/\d+)?)\s+\d$", r"\1", v.replace("*", "").strip())
    if lab == "Tömeg" and re.fullmatch(r"[\d.,]+", v):
        v = v.replace(".", ",") + " kg"
    return v


def label(head):
    h = (head or "").strip().lower()
    for key, hu_l in HEADERS:
        if h.startswith(key) or h.replace("\n", " ").startswith(key.replace("\n", " ")):
            return hu_l
    return None


def product_urls():
    urls = set()
    index = fetch(f"{BASE}/sitemap.xml").decode("utf-8", "ignore")
    for sm in re.findall(r"<loc>([^<]+)</loc>", index):
        if sm.endswith(".xml"):
            for u in re.findall(r"<loc>([^<]+)</loc>", fetch(sm).decode("utf-8", "ignore")):
                if "/en/products/" in u and u.rstrip("/").count("/") >= 5:
                    urls.add(u)
    return sorted(urls)


def parse_page(url):
    page = fetch(url).decode("utf-8", "ignore")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S)
    title = text((re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S) or [None, ""])[1])
    t = text(body)
    # a fejléc: a cím után közvetlenül álló kódlista (pl. "Grill Large 35-2700 / 35-2710 / 35-2720 Home")
    m = re.search(re.escape(title) + r"\s+((?:\d{2}-\d{4}(?:-[A-Z0-9]{1,4})?\s*/?\s*)+)", t) if title else None
    head_codes = CODE.findall(m.group(1)) if m else []
    pdfs = list(dict.fromkeys(re.findall(r'href="([^"]+\.pdf)"', page)))
    og = re.search(r'og:image" content="([^"]+)"', page)
    parts = set()
    for pdf in pdfs:
        try:
            doc = pymupdf.open(stream=fetch(pdf), filetype="pdf")
        except Exception:  # noqa: BLE001
            continue
        for pg in doc:
            for tab in pg.find_tables().tables:
                rows = tab.extract()
                if rows and rows[0] and (rows[0][0] or "").lower().startswith("part"):
                    parts |= {(r[0] or "").strip().upper() for r in rows[1:] if r and r[0]}
    return {"url": url, "title": title, "codes": head_codes, "parts": parts, "all_codes": set(CODE.findall(t)), "pdfs": pdfs,
            "image": og.group(1) if og else None}


def pdf_specs(pdf_url, code):
    """A PDF táblázataiból a kódhoz tartozó sor(ok) adatai + a REMARKS / OPTIONAL felsorolás."""
    specs, extras = {}, []
    try:
        doc = pymupdf.open(stream=fetch(pdf_url), filetype="pdf")
    except Exception:  # noqa: BLE001
        return specs, extras
    for pg in doc:
        for tab in pg.find_tables().tables:
            rows = tab.extract()
            if not rows or not rows[0] or not (rows[0][0] or "").lower().startswith("part"):
                continue
            heads = rows[0]
            for row in rows[1:]:
                if not row or (row[0] or "").strip().upper() != code.upper():
                    continue
                for h, v in zip(heads[1:], row[1:]):
                    lab = label(h)
                    if lab and v and v.strip() and lab not in specs:
                        specs[lab] = tidy(lab, hu(v))
        for m in re.finditer(r"(?:REMARKS|OPTIONAL)\s*\n(.*?)(?:\n[A-Z][A-Z ]{5,}\n|\Z)", pg.get_text(), re.S):
            extras += [x.strip(" \tn") for x in re.split(r"\n\s*n\s", "\n" + m.group(1)) if len(x.strip()) > 3]
    return specs, extras


def excel_code(p):
    for src in (p["supplierCode"] or "", p["name"], p["slug"].upper()):
        m = CODE.search(src.upper())
        if m:
            return re.sub(r"-DARK$", "-DG", m.group(0))  # Quadris "DARK" = G&C "DG" (sötétített üveg)
    return ""


def main():
    pages = [parse_page(u) for u in product_urls()]
    print(f"  G&C termékoldalak: {len(pages)}")
    products = load_products(SUPPLIER)
    enrichment, missing = {}, []
    for p in products:
        code = excel_code(p)
        base = re.sub(r"-[A-Z]{1,3}$", "", code)
        hit = (next((x for x in pages if code in x["codes"]), None)
               or next((x for x in pages if code in x["parts"]), None)
               or next((x for x in pages if base and (base in x["codes"] or base in x["parts"])), None))
        if not hit:
            missing.append((p, code))
            continue
        specs, extras = {}, []
        for pdf in hit["pdfs"]:
            s, ex = pdf_specs(pdf, code)
            if not s and base != code:
                s, _ = pdf_specs(pdf, base)
            specs.update({k: v for k, v in s.items() if k not in specs})
            extras += ex
        clear_images(p["slug"])
        images = []
        if hit["image"]:
            try:
                images.append(save_image(fetch(hit["image"]), p["slug"], 1))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", hit["image"], err)
        enrichment[p["slug"]] = {
            "source": SUPPLIER, "sourceUrl": hit["url"], "sourceTitle": hit["title"], "matchedCode": code,
            "sourceDescription": "; ".join(dict.fromkeys(extras)), "specs": specs, "images": images,
        }
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p, code in missing:
        print(f"  NINCS: {code or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
