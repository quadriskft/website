"""ESAL (Forlì, IT) – felépítmény-profilok (aláfutásgátló, mono profil, szegők, ponyvafeszítők, koptatók, húspálya-sín).

Forrás: a gyártó „Catalogo Sponde 2020” katalógusa (esalforli.com, szkennelt PDF:
data/forras/esal_sponde_2020.pdf). A lapok táblázatosak: Codice | Disegno | Peso kg/ml | Descrizione | hosszak.
A szöveget OCR-rel (tesseract) olvassuk ki; a cikkszám sorában a „Disegno” cella rajzát a táblázat
vonalai mentén vágjuk ki, a folyóméter-tömeget ugyanabból a sorból vesszük.

A Quadris-kódok a katalóguskódot tartalmazzák (pl. S02 9629 6 = 9629-es profil 6 m-es szálban,
250535 = 50535), ezért a párosítás kézzel rögzített.

Használat: python3 scripts/termekadatok/esal.py
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import CACHE, clear_images, load_products, save_image, update_enrichment  # noqa: E402

SUPPLIER = "ESAL"
PDF = Path(__file__).resolve().parents[2] / "data/forras/esal_sponde_2020.pdf"
URL = "https://esalforli.com/public/Catalogo-Sponde-2020-Esal-Forli.pdf"
DPI = 150  # OCR és táblázatvonal-keresés (az OCR-gyorsítótár ehhez a felbontáshoz tartozik)
HIRES_DPI = 400  # a végső rajz-kivágás renderelése (a lapok vektorosak, így élesebb, nagyobb kép)
# Quadris slug -> (katalóguskód, szálhossz a Quadris-kódból [m] vagy None)
MAP = {
    "203183-250-25-mm-alafutasgatlo-elox-profil": ("13183", "7,5"),
    # 205535: a Quadris kérésére a Metra R 7297 a forrás (metra.py)
    "227075-200-mm-mono-profil-teli-szakalas-elox": ("8770", "7,5"),
    "222020-h-szego-kiugros-25-mm-elox": ("50020", "6"),
    "245085-bill-u-szego-30-mm-40-60-elox": ("50085", "6"),
    "201092-spanner-profil": ("21092", None),
    "102439-dugo-spitzprofilhoz-150-mm-magas": ("12439", None),
    "231381-25-mm-diszlec-alu-3000-mm": ("MT", None),
    "232134-285-mm-i-koptato-profil-elox": ("2134", None),
    "233837-or-tomiteses-ajtoszego-35-mm-elox": ("13837", None),
    "729629-huspalya-c-sin-elox-6000-mm": ("9629", "6"),
    "729630-huspalya-c-sin-elox-7000-mm": ("9629", "7"),
}


def page_image(doc, pno):
    pix = doc[pno].get_pixmap(dpi=DPI, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def ocr_words(img, pno):
    key = CACHE / f"esal_ocr_{pno:02d}.tsv"
    if not key.exists():
        if not shutil.which("tesseract"):
            raise SystemExit("tesseract szükséges (apt-get install tesseract-ocr)")
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            img.save(tmp.name)
            out = subprocess.run(["tesseract", tmp.name, "stdout", "--psm", "11", "tsv"], capture_output=True, text=True).stdout
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text(out)
    words = []
    for line in key.read_text().splitlines()[1:]:
        c = line.split("\t")
        if len(c) >= 12 and c[11].strip():
            x, y, w, h = map(int, c[6:10])
            words.append((x, y, x + w, y + h, c[11].strip()))
    return words


def h_lines(gray, x0, x1):
    band = gray[:, x0:x1] < 225
    rows = np.where(band.mean(axis=1) > 0.6)[0]
    lines = []
    for r in rows:
        if lines and r - lines[-1][-1] <= 2:
            lines[-1].append(r)
        else:
            lines.append([r])
    return [int(np.mean(g)) for g in lines]


def tight_box(img, pad=10):
    """A rajz befoglaló doboza a cella-képen belül (a 150 dpi-s OCR-képen számolva), vagy None."""
    g = np.asarray(img.convert("L"))
    # ha a cellában még egy táblázatvonal van (szomszéd sor széle), a legtöbb rajzot tartalmazó sávot tartjuk meg
    # szürke táblázatvonal (nem fekete rajzvonal) mentén daraboljuk
    cuts = [0] + [int(r) for r in np.where(((g < 235) & (g > 140)).mean(axis=1) > 0.8)[0]] + [g.shape[0]]
    segs = [(int((g[a:b] < 200).sum()), a, b) for a, b in zip(cuts, cuts[1:]) if b - a > 3]
    a = 0
    if len(segs) > 1:
        _, a, b = max(segs)
        g = g[a:b]
    ys, xs = np.where(g < 200)
    if len(xs) < 20:
        return None
    return (max(xs.min() - pad, 0), a + max(ys.min() - pad, 0), min(xs.max() + pad, img.width), a + min(ys.max() + pad, g.shape[0]))


def hires_crop(doc, pno, box):
    """A (DPI-s koordinátájú) dobozt HIRES_DPI felbontással rendereli ki a PDF-ből."""
    z = HIRES_DPI / DPI
    x0, y0, x1, y1 = box
    clip = pymupdf.Rect(x0, y0, x1, y1) * (72 / DPI)
    pix = doc[pno].get_pixmap(dpi=HIRES_DPI, clip=clip, alpha=False)
    out = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # a pontosan skálázott méretre igazítjuk (a clip kerekítése 1-2 px eltérést adhat)
    out = out.resize((round((x1 - x0) * z), round((y1 - y0) * z)), Image.LANCZOS) if abs(out.width - (x1 - x0) * z) > 3 else out
    if out.height < out.width / 3:  # nagyon lapos rajz: fehér sávval nézhetőbb arányra bővítjük
        canvas = Image.new("RGB", (out.width, int(out.width / 3)), "white")
        canvas.paste(out, (0, (canvas.height - out.height) // 2))
        out = canvas
    return out


def find(doc, code):
    """(rajz-kép, tömeg, oldal) a kód első táblázatsorából."""
    for pno in range(len(doc)):
        img = page_image(doc, pno)
        words = ocr_words(img, pno)
        W = img.width
        hdr = {w[4].lower(): w for w in words if w[4].lower() in ("codice", "disegno", "peso")}
        if "codice" not in hdr or "peso" not in hdr:
            continue
        cands = [w for w in words if w[0] < hdr["codice"][2] + 40 and w[1] > hdr["codice"][3]
                 and (w[4] == code or (code == "MT" and w[4] == "MT"))]
        if not cands:
            continue
        cw = cands[0]
        gray = np.asarray(img.convert("L"))
        lines = h_lines(gray, int(W * 0.08), int(W * 0.92))
        cy = (cw[1] + cw[3]) / 2
        top = max([ln for ln in lines if ln < cy], default=None)
        bot = min([ln for ln in lines if ln > cy], default=None)
        if top is None or bot is None:
            continue
        # a szomszédos sorok kódjai között félúton biztosan sorhatár van
        col = sorted(((w[1] + w[3]) / 2 for w in words if w[0] < hdr["codice"][2] + 40 and w[1] > hdr["codice"][3]
                      and re.fullmatch(r"\d{3,6}|MT", w[4])))
        prev = max([y for y in col if y < cy - 5], default=None)
        nxt = min([y for y in col if y > cy + 5], default=None)
        if prev is not None:
            top = max(top, int((prev + cy) / 2))
        if nxt is not None:
            bot = min(bot, int((cy + nxt) / 2))
        x0, x1 = hdr["codice"][2] + 25, hdr["peso"][0] - 12
        cy0 = top + 4
        box = tight_box(img.crop((x0, cy0, x1, bot - 4)))
        cell = None if box is None else hires_crop(doc, pno, (x0 + box[0], cy0 + box[1], x0 + box[2], cy0 + box[3]))
        wt = next((w[4] for w in sorted(words, key=lambda w: w[0])
                   if top < (w[1] + w[3]) / 2 < bot and w[0] >= hdr["peso"][0] - 20 and re.fullmatch(r"\d+,\d{2,3}", w[4])), None)
        header = " ".join(w[4] for w in words if w[3] < hdr["codice"][1])
        return cell, wt, pno, header
    return None, None, None, ""


def main():
    doc = pymupdf.open(PDF)
    cache = {}
    enrichment = {}
    products = load_products(SUPPLIER)
    for p in products:
        if p["slug"] not in MAP:
            continue
        code, length = MAP[p["slug"]]
        if code not in cache:
            cache[code] = find(doc, code)
        cell, wt, pno, header = cache[code]
        if cell is None:
            print("  nem található a katalógusban:", code)
            continue
        specs = {"Anyag": "alumínium EN AW-6060 T5" if "6060" in header else "alumínium"}
        if "ARS" in header or "nodizz" in header:
            specs["Felület"] = "eloxált (ARS, 10 µm)" if "elox" in p["name"].lower() else "nyers vagy eloxált"
        if wt:
            specs["Tömeg"] = f"{wt} kg/fm"
        if length:
            specs["Szálhossz"] = f"{length} m"
        clear_images(p["slug"])
        enrichment[p["slug"]] = {"source": SUPPLIER, "sourceUrl": f"{URL}#page={pno + 1}", "sourceTitle": f"ESAL {code}", "matchedCode": code,
                                 "specs": specs, "images": [save_image(cell, p["slug"], 1)]}
    update_enrichment(enrichment, SUPPLIER)
    print(f"{SUPPLIER}: {len(enrichment)}/{len(products)} egyezés")
    for p in products:
        if p["slug"] not in enrichment:
            print(f"  NINCS: {p['supplierCode'] or '-':>12}  {p['name']}")


if __name__ == "__main__":
    main()
