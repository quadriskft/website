"""Általános letöltő: a beszállító weboldal-térképéből (sitemap) bejárja az oldalakat,
és megkeresi, melyik oldalon szerepel a termék kódja. Innen a kép (og:image vagy az első
termékkép) és az oldal címe kerül mentésre.

Használat: python3 scripts/termekadatok/sitemap_kereso.py [beszállító ...]
"""

import html
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).parent))
from common import (clear_images, code_candidates, fetch, load_products,  # noqa: E402
                    save_image, update_enrichment)

# beszállító -> (sitemap, az URL-ekre illesztendő minta, legfeljebb ennyi oldal)
SITES = {
    "G&C termékek": ("https://gnc-systems.com/sitemap.xml", r"/en/", 800),
    "COPAR": ("https://www.copar.it/sitemap.xml", r"/en/", 800),
    "Takler": ("https://trucksandtrailers.taklergroup.com/sitemap.xml", r"lang=en|/en/|product", 800),
    "Pommier": ("https://www.pommier.eu/sitemap.xml", r"/en/", 1500),
    "Pommier Furgocar": ("https://www.pommier.eu/sitemap.xml", r"/en/", 1500),
    "Profilpol": ("https://profilpolsystem.pl/sitemap.xml", r"/en/", 800),
    "Cargoframes Czech": ("https://cargoframes.eu/sitemap.xml", r"/en/", 800),
    "RE-ALL": ("https://www.re-all.it/sitemap.xml", r"", 800),
    "BODEGA": ("https://www.bodega.it/sitemap.xml", r"", 800),
}

LOGO_WORDS = re.compile(r"logo|icon|favicon|flag|banner|placeholder|header|footer|sprite", re.I)


def sitemap_urls(url, depth=0):
    xml = fetch(url).decode("utf-8", "ignore")
    locs = [html.unescape(x.strip()) for x in re.findall(r"<loc>(.*?)</loc>", xml, re.S)]
    if "<sitemapindex" in xml and depth < 3:
        out = []
        for loc in locs:
            try:
                out += sitemap_urls(loc, depth + 1)
            except Exception:  # noqa: BLE001
                pass
        return out
    return locs


def page_info(url):
    try:
        raw = fetch(url).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return None
    title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
    og = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', raw) or \
        re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', raw)
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<footer.*?</footer>|<header.*?</header>", " ", raw, flags=re.S)
    imgs = []
    for src in re.findall(r'<img[^>]+(?:data-src|src)="([^"]+)"', body):
        if src.startswith("data:") or LOGO_WORDS.search(src) or src.lower().endswith(".svg"):
            continue
        imgs.append(urljoin(url, html.unescape(src)))
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
    clean = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()  # noqa: E731
    return {
        "url": url,
        "title": clean(title.group(1)) if title else "",
        "h1": clean(h1.group(1)) if h1 else "",
        "og": urljoin(url, html.unescape(og.group(1))) if og else None,
        "imgs": imgs,
        "text": text,
    }


def code_pattern(code):
    parts = [re.escape(ch) for ch in re.sub(r"[\s.\-/]+", "", code)]
    body = r"[\s.\-/]?".join(parts)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)


def run(supplier):
    sitemap, pattern, limit = SITES[supplier]
    urls = [u for u in dict.fromkeys(sitemap_urls(sitemap)) if re.search(pattern, u)][:limit]
    with ThreadPoolExecutor(6) as ex:
        pages = [p for p in ex.map(page_info, urls) if p]
    og_counts = Counter(p["og"] for p in pages if p["og"])
    common_og = {o for o, n in og_counts.items() if n > max(3, len(pages) * 0.2)}
    img_counts = Counter(i for p in pages for i in set(p["imgs"]))
    common_img = {i for i, n in img_counts.items() if n > max(3, len(pages) * 0.2)}

    products = load_products(supplier)
    enrichment, missing = {}, []
    for prod in products:
        best, code = None, None
        for c in code_candidates(prod):
            if len(re.sub(r"\W", "", c)) < 4:
                continue
            rx = code_pattern(c)
            hits = [p for p in pages if rx.search(p["text"]) or rx.search(p["title"])]
            if hits:
                hits.sort(key=lambda p: (not rx.search(p["title"] + " " + p["h1"]), len(p["text"])))
                best, code = hits[0], c
                break
        if not best:
            missing.append(prod)
            continue
        image = best["og"] if best["og"] and best["og"] not in common_og else None
        if not image:
            image = next((i for i in best["imgs"] if i not in common_img), None)
        clear_images(prod["slug"])
        images = []
        if image:
            try:
                images.append(save_image(fetch(image), prod["slug"]))
            except Exception as err:  # noqa: BLE001
                print("  képhiba:", image, err)
        enrichment[prod["slug"]] = {
            "source": supplier,
            "sourceUrl": best["url"],
            "sourceTitle": best["h1"] or best["title"],
            "matchedCode": code,
            "specs": {},
            "images": images,
        }
    update_enrichment(enrichment, supplier)
    print(f"{supplier}: {len(pages)} oldal bejárva, {len(enrichment)}/{len(products)} egyezés")
    for p in missing:
        print(f"  NINCS: {p['supplierCode'] or '-':>16}  {p['name']}")


if __name__ == "__main__":
    for s in sys.argv[1:] or SITES:
        try:
            run(s)
        except Exception as err:  # noqa: BLE001
            print(f"{s}: HIBA {err}")
