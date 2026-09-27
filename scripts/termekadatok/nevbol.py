"""Műszaki adatok a Quadris megnevezésből azoknál a termékeknél, amelyeknek nincs beszállítói adata.

A szabványos félgyártmányok (lemez, rétegelt lemez, gumilemez, zártszelvény, cső, lapos-, L- és
U-profil) megnevezése minden méretet tartalmaz. Ezekből adatlap készül, alumíniumnál elméleti
tömeggel (sűrűség 2,70 g/cm³), a szelvényekhez pedig méretezett keresztmetszet-rajz.

Csak ott ír, ahol a terméknek még nincs beszállítói bejegyzése (vagy a korábbi is ebből a lépésből jött).
Használat: python3 scripts/termekadatok/nevbol.py
"""

import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Quadris adatok"
AL = 2.70  # g/cm³
NUM = r"(\d+(?:[.,]\d+)?)"


def f(x):
    return float(str(x).replace(",", "."))


def hu(x, d=2):
    s = f"{x:.{d}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ---------------------------------------------------------------- keresztmetszet-rajzok

def dim_h(d, x0, x1, y, label, fnt):
    d.line([(x0, y), (x1, y)], fill="black", width=2)
    for x, s in ((x0, 1), (x1, -1)):
        d.polygon([(x, y), (x + 14 * s, y - 6), (x + 14 * s, y + 6)], fill="black")
    tw = d.textlength(label, font=fnt)
    d.text(((x0 + x1) / 2 - tw / 2, y - 38), label, fill="black", font=fnt)


def dim_v(img, d, x, y0, y1, label, fnt):
    d.line([(x, y0), (x, y1)], fill="black", width=2)
    for y, s in ((y0, 1), (y1, -1)):
        d.polygon([(x, y), (x - 6, y + 14 * s), (x + 6, y + 14 * s)], fill="black")
    tw = int(d.textlength(label, font=fnt)) + 4
    t = Image.new("RGBA", (tw, 40), (255, 255, 255, 0))
    ImageDraw.Draw(t).text((2, 0), label, fill="black", font=fnt)
    t = t.rotate(90, expand=True)
    img.paste(t, (int(x + 10), int((y0 + y1) / 2 - t.height / 2)), t)


def drawing(kind, a, b=0, t=0, c=0):
    """Méretezett keresztmetszet (fekete kitöltés, mint a gyári katalógusokban)."""
    W, H, M = 1000, 750, 150
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fnt = font(34)
    if kind == "tube":  # kör cső: a = külső átmérő, t = falvastagság
        s = (H - 2 * M) / a
        r, ri = a * s / 2, (a / 2 - t) * s
        cx, cy = W / 2, H / 2 + 20
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="black")
        if ri > 0:
            d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill="white")
        dim_h(d, cx - r, cx + r, cy - r - 40, f"Ø{hu(a)}", fnt)
        if t:
            d.text((cx + r + 30, cy - 20), f"s = {hu(t)}", fill="black", font=fnt)
        return img
    if kind == "rod":
        s = (H - 2 * M) / a
        r = a * s / 2
        cx, cy = W / 2, H / 2 + 20
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="black")
        dim_h(d, cx - r, cx + r, cy - r - 40, f"Ø{hu(a)}", fnt)
        return img
    s = min((W - 2 * M) / a, (H - 2 * M) / b)
    w, h = a * s, b * s
    x0, y0 = (W - w) / 2, (H - h) / 2 + 20
    ts = max((t or min(a, b) * 0.06) * s, 4)
    if kind == "rhs":
        d.rectangle([x0, y0, x0 + w, y0 + h], fill="black")
        d.rectangle([x0 + ts, y0 + ts, x0 + w - ts, y0 + h - ts], fill="white")
    elif kind == "flat":
        d.rectangle([x0, y0, x0 + w, y0 + h], fill="black")
    elif kind == "L":
        d.rectangle([x0, y0, x0 + ts, y0 + h], fill="black")
        d.rectangle([x0, y0 + h - ts, x0 + w, y0 + h], fill="black")
    elif kind == "U":  # a = gerinc (szélesség), b = szár (magasság)
        d.rectangle([x0, y0 + h - ts, x0 + w, y0 + h], fill="black")
        d.rectangle([x0, y0, x0 + ts, y0 + h], fill="black")
        d.rectangle([x0 + w - ts, y0, x0 + w, y0 + h], fill="black")
    elif kind == "C":  # hossztartó: függőleges gerinc (b), vízszintes szárak (a)
        d.rectangle([x0, y0, x0 + ts, y0 + h], fill="black")
        d.rectangle([x0, y0, x0 + w, y0 + ts], fill="black")
        d.rectangle([x0, y0 + h - ts, x0 + w, y0 + h], fill="black")
    elif kind == "I":  # a = szélesség (öv), b = magasság
        d.rectangle([x0, y0, x0 + w, y0 + ts], fill="black")
        d.rectangle([x0, y0 + h - ts, x0 + w, y0 + h], fill="black")
        d.rectangle([x0 + w / 2 - ts / 2, y0, x0 + w / 2 + ts / 2, y0 + h], fill="black")
    elif kind == "arc":  # íves sarokprofil: két szár, lekerekített külső sarok
        R = min(w, h) * 0.55
        d.pieslice([x0, y0 + h - 2 * R, x0 + 2 * R, y0 + h], 90, 180, fill="black")
        d.pieslice([x0 + ts, y0 + h - 2 * R + ts, x0 + 2 * R - ts, y0 + h - ts], 90, 180, fill="white")
        d.rectangle([x0, y0, x0 + ts, y0 + h - R], fill="black")
        d.rectangle([x0 + R, y0 + h - ts, x0 + w, y0 + h], fill="black")
    dim_h(d, x0, x0 + w, y0 - 40, hu(a), fnt)
    dim_v(img, d, x0 + w + 40, y0, y0 + h, hu(b), fnt)
    if t and kind not in ("flat", "arc"):
        if kind == "C":
            d.text((x0 + ts + 12, y0 + h / 2 - 20), f"s = {hu(t)}", fill="black", font=fnt)
            return img
        d.text((x0 + ts + 12 if kind != "rhs" else x0 + w / 2 - 40, y0 + h / 2 - 20), f"s = {hu(t)}", fill="black", font=fnt)
    return img


# ---------------------------------------------------------------- megnevezés-értelmezés

def parse(p):
    n = p["name"].replace("×", "x")
    low = n.lower()
    elox = "elox" in low
    specs, draw = {}, None
    # lemez: "S 3x1250x3200 mm Alu lemez EN AW-1050A H14/H24"
    m = re.match(rf"S\s*{NUM}\s*x\s*{NUM}(?:\s*x\s*{NUM})?", n)
    if m and ("lemez" in low or "szalag" in low):
        t, w, l = m.group(1), m.group(2), m.group(3)
        specs.update({"Vastagság": f"{hu(f(t))} mm", "Szélesség": f"{w} mm"})
        if l:
            specs["Hossz"] = f"{l} mm"
            specs["Tömeg / tábla"] = f"{hu(f(t) * f(w) * f(l) * AL / 1e6, 1)} kg (elméleti)"
        else:
            specs["Kiszerelés"] = "szalag (tekercs)"
        specs["Tömeg / m²"] = f"{hu(f(t) * AL, 2)} kg (elméleti)"
        a = re.search(r"EN\s*AW-?\s*(\d{4}[A-Z]?)", n)
        if a:
            specs["Ötvözet"] = f"EN AW-{a.group(1)}"
        elif "Al-Mg" in n:
            specs["Ötvözet"] = "EN AW-5754 (AlMg3) / Al-Mg-1 csoport"
        h = re.search(r"\b(H\d{2}(?:/H\d{2})*)\b", n)
        if h:
            specs["Állapot"] = h.group(1)
        r = re.search(r"RAL\s?(\d{4})", n)
        if r:
            specs["Felület"] = f"festett, RAL {r.group(1)}"
        elif elox:
            specs["Felület"] = "eloxált"
        elif "rízs" in low:
            specs["Felület"] = "rízsmintás (csúszásgátló)"
        return specs, None
    # rétegelt lemez: "L 12x1500x2500 mm rétegelt lemez fenolos"
    m = re.match(rf"L\s*(?:MDF\s*)?{NUM}\s*[xX]\s*{NUM}\s*[xX]\s*{NUM}", n)
    if m and ("rétegelt" in low or "mdf" in low):
        specs.update({"Vastagság": f"{hu(f(m.group(1)))} mm", "Méret": f"{m.group(2)} × {m.group(3)} mm"})
        if "mdf" in low:
            specs["Anyag"] = "MDF lap"
        else:
            specs["Anyag"] = "rétegelt falemez"
            specs["Felület"] = ("fenolfilm bevonatos" if re.search(r"fenol|film", low) else "natúr (bevonat nélkül)")
            if "hexa" in low:
                specs["Felület"] += ", csúszásmentes hatszögmintás (HEXA)"
        return specs, None
    # gumilemez / szőnyeg: "G 8x1000x2000 Soft gumi lap", "G 6x2000mm COBRA szőnyeg"
    m = re.match(rf"G\s*{NUM}\s*[x/]\s*{NUM}(?:\s*x\s*{NUM}(?![\d.,]*\s*m\b))?", n)
    if m:
        a1, a2, a3 = m.groups()
        if a3:
            specs.update({"Vastagság": f"{hu(f(a1))} mm", "Méret": f"{a2} × {a3} mm"})
        elif f(a1) < 40:
            specs.update({"Vastagság": f"{hu(f(a1))} mm", "Szélesség": f"{a2} mm"})
        else:
            specs["Méret"] = f"{a1} × {a2} mm"
        L = re.search(r"L\s*:?\s*(\d+)\s*m\b", n) or re.search(r"x\s*(\d+)\s*m\b", n)
        if L:
            specs["Tekercshossz"] = f"{L.group(1)} m"
        if "pvc" in low:
            specs["Anyag"] = "víztiszta PVC"
        elif "nylon" in low:
            layers = re.search(r"(\d)\s*nylon", low).group(1)
            specs["Anyag"] = f"gumi, {layers} rétegű nylon betéttel"
        else:
            specs["Anyag"] = "gumi"
        return specs, None
    # szelvények
    mat = ("acél" if re.search(r"acél", low) else
           "alumínium" if re.search(r"alu|elox", low) or p["group"] in ("ipari-felgyartmanyok", "aluminium-alvaz-profilok", "zart-dobozos-es-hutos-profilok", "ponyvarendszer-kiegeszitok") else "")
    if not mat:
        return specs, None
    specs["Anyag"] = mat + (", eloxált" if elox else "")
    m = re.search(rf"{NUM}\s*x\s*{NUM}\s*x\s*{NUM}(?:\s*mm)?\s*(?:R\s*([\d,/.]+))?.*(zártszelv|zártszelvány)", low)
    if m:
        a, b, t = f(m.group(1)), f(m.group(2)), f(m.group(3))
        specs.update({"Méret": f"{hu(a)} × {hu(b)} mm", "Falvastagság": f"{hu(t)} mm"})
        if m.group(4):
            specs["Sarokrádiusz"] = f"R{m.group(4)}"
        specs["Tömeg"] = f"{hu((2 * (a + b) - 4 * t) * t * AL / 1000, 3)} kg/fm (elméleti)"
        return specs, ("rhs", a, b, t)
    m = re.search(rf"{NUM}\s*x\s*{NUM}\s*(?:mm)?\s*alu\s*lapos", low)
    if m:
        a, b = f(m.group(1)), f(m.group(2))
        specs.update({"Szélesség": f"{hu(a)} mm", "Vastagság": f"{hu(b)} mm", "Tömeg": f"{hu(a * b * AL / 1000, 3)} kg/fm (elméleti)"})
        return specs, ("flat", a, b, b)
    m = re.search(rf"(?:d\s*)?{NUM}\s*x\s*{NUM}\s*(?:mm)?\s*(?:alu\s*)?(?:cső|ponyvacső|húspálya cső)", low) or \
        re.search(rf"{NUM}\s*x\s*{NUM}\s*alu\s*cső", low)
    if m:
        d_, t = f(m.group(1)), f(m.group(2))
        specs.update({"Külső átmérő": f"{hu(d_)} mm", "Falvastagság": f"{hu(t)} mm",
                      "Tömeg": f"{hu(math.pi * (d_ - t) * t * AL / 1000, 3)} kg/fm (elméleti)"})
        return specs, ("tube", d_, 0, t)
    m = re.search(rf"d\s*{NUM}\s*mm\s*alu\s*cső", low)
    if m:
        specs["Külső átmérő"] = f"{m.group(1)} mm"
        return specs, None  # falvastagság nélkül nincs rajz
    m = re.search(rf"{NUM}\s*mm\s*alu\s*rúd", low)
    if m:
        d_ = f(m.group(1))
        specs.update({"Átmérő": f"{hu(d_)} mm", "Tömeg": f"{hu(math.pi * d_ * d_ / 4 * AL / 1000, 3)} kg/fm (elméleti)"})
        return specs, ("rod", d_)
    m = re.search(rf"{NUM}\s*x\s*{NUM}\s*x\s*{NUM}\s*(?:mm)?\s*alu\s*\"?l\"?\s*profil", low)
    if m:
        a, b, t = f(m.group(1)), f(m.group(2)), f(m.group(3))
        specs.update({"Méret": f"{hu(a)} × {hu(b)} mm", "Falvastagság": f"{hu(t)} mm",
                      "Tömeg": f"{hu((a + b - t) * t * AL / 1000, 3)} kg/fm (elméleti)"})
        return specs, ("L", a, b, t)
    m = re.search(rf"\"?u\"?\s*{NUM}\s*x\s*{NUM}(?:\s*x\s*{NUM})?\s*x\s*{NUM}", low) or \
        re.search(rf"{NUM}\s*x\s*{NUM}\s*x\s*{NUM}\s*x\s*{NUM}\s*mm\s*\"u\"", low) or \
        re.search(rf"{NUM}\s*x\s*{NUM}\s*x\s*{NUM}\s*mm\s*u\s*profil", low)
    if m:
        g = [f(x) for x in m.groups() if x]
        if len(g) == 4:
            web, fl, _, t = g
        else:
            web, fl, t = g
        specs.update({"Gerinc": f"{hu(web)} mm", "Szár": f"{hu(fl)} mm", "Falvastagság": f"{hu(t)} mm",
                      "Tömeg": f"{hu((web + 2 * fl - 2 * t) * t * AL / 1000, 3)} kg/fm (elméleti)"})
        return specs, ("U", web, fl, t)
    m = re.search(rf"zártszelvény\s*{NUM}\s*x\s*{NUM}\s*x\s*{NUM}", low)
    if m:
        a, b, t = f(m.group(1)), f(m.group(2)), f(m.group(3))
        specs.update({"Méret": f"{hu(a)} × {hu(b)} mm", "Falvastagság": f"{hu(t)} mm",
                      "Tömeg": f"{hu((2 * (a + b) - 4 * t) * t * AL / 1000, 3)} kg/fm (elméleti)"})
        return specs, ("rhs", a, b, t)
    m = re.search(rf"{NUM}\s*x\s*{NUM}\s*(?:mm)?\s*ponyvatartó zártszelvény", low)
    if m:
        a, b = f(m.group(1)), f(m.group(2))
        specs["Méret"] = f"{hu(a)} × {hu(b)} mm"
        return specs, ("rhs", a, b, 0)
    m = re.search(rf"{NUM}\s*x\s*{NUM}\s*x\s*{NUM}\s*mm\s*r[\d,]*\s*oszlop", low)
    if m:
        a, b, t = f(m.group(1)), f(m.group(2)), f(m.group(3))
        specs.update({"Méret": f"{hu(a)} × {hu(b)} mm", "Falvastagság": f"{hu(t)} mm"})
        return specs, ("rhs", a, b, t)
    m = re.search(rf"(?:ponyvacső\s*{NUM}\s*x\s*{NUM}|{NUM}\s*x\s*{NUM}\s*mm\s*ponyvacső)", low)
    if m:
        g = [x for x in m.groups() if x]
        d_, t = f(g[0]), f(g[1])
        specs.update({"Külső átmérő": f"{hu(d_)} mm", "Falvastagság": f"{hu(t)} mm",
                      "Tömeg": f"{hu(math.pi * (d_ - t) * t * AL / 1000, 3)} kg/fm (elméleti)"})
        return specs, ("tube", d_, 0, t)
    m = re.search(rf"{NUM}\s*x\s*{NUM}(?:\s*x\s*{NUM})?\s*(?:mm)?\s*(?:belső\s*(?:bokaléc\s*)?védőprofil|\"?l\"?\s*(?:profil|belső))", low) or \
        re.search(rf"\"?l\"?\s*profil\s*{NUM}\s*x\s*{NUM}", low) or re.search(rf"külső\s*\"?l\"?\s*profil\s*{NUM}\s*x\s*{NUM}", low) or \
        re.search(rf"{NUM}\s*x\s*{NUM}\s*(?:mm)?\s*l\s", low)
    if m:
        g = [f(x) for x in m.groups() if x]
        a, b = g[0], g[1]
        t = g[2] if len(g) > 2 else 0
        specs["Méret"] = f"{hu(a)} × {hu(b)} mm"
        if t:
            specs["Falvastagság"] = f"{hu(t)} mm"
            specs["Tömeg"] = f"{hu((a + b - t) * t * AL / 1000, 3)} kg/fm (elméleti)"
        return specs, ("L", a, b, t)
    m = re.search(rf"{NUM}\s*x\s*{NUM}\s*mm\s*(?:íves|utánfutó)\s*sarokprofil", low)
    if m:
        a, b = f(m.group(1)), f(m.group(2))
        specs["Szárak"] = f"{hu(a)} × {hu(b)} mm"
        return specs, ("arc", a, b, 0)
    m = re.search(rf"\"i\"\s*gerenda profil\s*{NUM}\s*x\s*{NUM}\s*/\s*{NUM}\s*x\s*{NUM}", low)
    if m:
        h_, b_, _, t = (f(x) for x in m.groups())
        specs.update({"Magasság": f"{hu(h_)} mm", "Övszélesség": f"{hu(b_)} mm", "Falvastagság": f"{hu(t)} mm"})
        return specs, ("I", b_, h_, t)
    m = re.search(rf"\"i\"\s*{NUM}\s*/\s*{NUM}\s*kereszttartó", low)
    if m:
        h_, b_ = f(m.group(1)), f(m.group(2))
        specs.update({"Magasság": f"{hu(h_)} mm", "Övszélesség": f"{hu(b_)} mm"})
        return specs, ("I", b_, h_, 0)
    m = re.search(rf"\"u\"\s*{NUM}\s*/\s*{NUM}\s*hossztartó", low) or re.search(rf"hossztartó\s*{NUM}\s*/\s*{NUM}\s*/\s*{NUM}", low)
    if m:
        g = [f(x) for x in m.groups()]
        h_, fl = g[0], g[1]
        t = g[2] if len(g) > 2 else 0
        specs.update({"Magasság": f"{hu(h_)} mm", "Szár": f"{hu(fl)} mm"})
        if t:
            specs["Falvastagság"] = f"{hu(t)} mm"
        return specs, ("C", fl, h_, t)
    return {}, None


def main():
    existing = load_enrichment()
    updates, drawn = {}, 0
    for p in load_products():
        prev = existing.get(p["slug"])
        specs, draw = parse(p)
        if prev and prev.get("source") != SOURCE:
            if (prev.get("images") and not prev.get("nevbolRajz")) or not draw:
                continue
            clear_images(p["slug"])
            merged = dict(prev)
            merged["specs"] = {**{k: v for k, v in specs.items() if k != "Anyag"}, **(prev.get("specs") or {})}
            merged["images"] = [save_image(drawing(*draw), p["slug"], 1)]
            merged["nevbolRajz"] = True  # a rajz ebből a lépésből jön – újrafuttatáskor frissíthető
            updates[p["slug"]] = merged
            drawn += 1
            continue
        if len(specs) < 2:
            continue
        images = []
        if draw:
            clear_images(p["slug"])
            images = [save_image(drawing(*draw), p["slug"], 1)]
            drawn += 1
        updates[p["slug"]] = {"source": SOURCE, "sourceUrl": "", "sourceTitle": p["name"], "matchedCode": "",
                              "specs": specs, "images": images}
    # a más forrásúakat forrásuk megtartásával írjuk vissza
    update_enrichment({k: v for k, v in updates.items() if v["source"] == SOURCE}, SOURCE)
    update_enrichment({k: v for k, v in updates.items() if v["source"] != SOURCE})
    print(f"{SOURCE}: {len(updates)} termék adatlapja a megnevezésből, ebből {drawn} keresztmetszet-rajzzal")


if __name__ == "__main__":
    main()
