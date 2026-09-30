"""Műszaki adatok a Quadris megnevezésből azoknál a termékeknél, amelyeknek nincs beszállítói adata.

A szabványos félgyártmányok (lemez, rétegelt lemez, gumilemez, zártszelvény, cső, lapos-, L- és
U-profil) megnevezése minden méretet tartalmaz. Ezekből adatlap készül, alumíniumnál elméleti
tömeggel (sűrűség 2,70 g/cm³), a szelvényekhez pedig méretezett keresztmetszet-rajz.

Csak ott ír, ahol a terméknek még nincs beszállítói bejegyzése (vagy a korábbi is ebből a lépésből jött).
Használat: python3 scripts/termekadatok/nevbol.py
"""

import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

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


def drawing(kind, a, b=0, t=0, ro=0, ri=0):
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
    if kind == "rhs":  # ro/ri: külső/belső sarokrádiusz (mm)
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=ro * s, fill="black")
        d.rounded_rectangle([x0 + ts, y0 + ts, x0 + w - ts, y0 + h - ts], radius=ri * s, fill="white")
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


def pattern_face(img, top, pattern):
    """A lemez felső lapjára rajzolja a mintát (sematikusan, felnagyított mintaosztással):
    quintett = 5 csepp / cella, duett = 2 csepp / cella, váltakozó irányban; diamond = gyémánt (rombusz) rács;
    rizs = sűrű, rendezetlen apró szemcsék. A mintát síkban rajzoljuk, majd affin leképezéssel a ferde lapra."""
    import numpy as np
    P, Q = 1400, 700  # a sík minta mérete (hossz × szélesség) képpontban
    tex = Image.new("RGB", (P, Q), (205, 210, 216))
    d = ImageDraw.Draw(tex)
    hi, lo = (246, 248, 250), (132, 138, 146)  # csillanás és árnyék: domború kiemelkedés hatás

    def drop(cx, cy, length, ang, width=12):
        # csepp: kihegyesedő végű lencse, árnyékkal és csillanással
        ca, sa = math.cos(ang), math.sin(ang)
        pts = [(length / 2 * math.cos(t), width / 2 * math.sin(t) ** 1.0) for t in [i * math.pi / 12 for i in range(24)]]
        for off, col in ((4, lo), (0, hi)):
            d.polygon([(cx + x * ca - y * sa + off, cy + x * sa + y * ca + off) for x, y in pts], fill=col)
        d.polygon([(cx + x * ca * 0.8 - y * 0.35 * sa + 1, cy + x * sa * 0.8 + y * 0.35 * ca + 1) for x, y in pts], fill=(214, 219, 225))

    if pattern in ("quintett", "duett"):
        cell = 170 if pattern == "quintett" else 150
        n, gap = (5, 24) if pattern == "quintett" else (2, 38)
        for j, cy in enumerate(range(cell // 2, Q + cell, cell)):
            for i, cx in enumerate(range(cell // 2, P + cell, cell)):
                if pattern == "quintett":  # 5 párhuzamos csepp, a szomszédos cellákban 90°-kal elforgatva
                    ang = 0 if (i + j) % 2 else math.pi / 2
                    for k in range(n):
                        o = (k - (n - 1) / 2) * gap
                        drop(cx + (o if ang else 0), cy + (0 if ang else o), cell * 0.66, ang, 14)
                else:  # duett: 2 csepp ±45°-ban
                    ang = math.radians(28) if (i + j) % 2 else math.radians(-28)  # a ferde vetítés miatt laposabb szög
                    for k in range(n):
                        o = (k - 0.5) * gap
                        drop(cx + o * math.cos(ang + math.pi / 2), cy + o * math.sin(ang + math.pi / 2), cell * 0.72, ang, 18)
    elif pattern == "diamond":
        c = 78
        for j, cy in enumerate(range(0, Q + c, c)):
            for cx in range(-c, P + c, c):
                x = cx + (c // 2 if j % 2 else 0)
                r = c * 0.36
                d.polygon([(x + 2, cy - r + 2), (x + r + 2, cy + 2), (x + 2, cy + r + 2), (x - r + 2, cy + 2)], fill=lo)
                d.polygon([(x, cy - r), (x + r, cy), (x, cy + r), (x - r, cy)], fill=(222, 226, 231), outline=hi)
    elif pattern == "rizs":
        rnd = np.random.default_rng(7)
        for _ in range(1500):
            cx, cy, a = rnd.uniform(0, P), rnd.uniform(0, Q), rnd.uniform(0, math.pi)
            drop(cx, cy, 30, a, 11)
    # affin leképezés: a sík (x, y) -> top[0] + x/P·(top[1]-top[0]) + y/Q·(top[3]-top[0])
    o, u, v = np.array(top[0]), np.array(top[1]) - np.array(top[0]), np.array(top[3]) - np.array(top[0])
    m = np.linalg.inv(np.array([[u[0] / P, v[0] / Q], [u[1] / P, v[1] / Q]]))
    coeffs = (m[0, 0], m[0, 1], -(m[0] @ o), m[1, 0], m[1, 1], -(m[1] @ o))
    warped = tex.transform(img.size, Image.AFFINE, coeffs, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(top, fill=255)
    img.paste(warped, (0, 0), mask)


def sheet(w, l, t, colour, length_label=None, pattern=None):
    """Lemez / tábla / tekercs ferde axonometrikus rajza a méretekkel (hossz, szélesség, vastagság)."""
    W, H = 1000, 750
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fnt = font(34)
    L = l or w * 2.6
    k = 0.9  # a mélységi (szélesség) tengely rövidítése, 30°-os irányban
    dx, dy = math.cos(math.radians(30)) * k, -math.sin(math.radians(30)) * k
    s = min(600 / (L + w * dx), 340 / (w * -dy + 0.001))
    lx, wx, wy = L * s, w * dx * s, w * dy * s
    th = max(min(t * s * 5, 45), 16)  # a vastagság láthatóan eltúlozva
    x0 = 250 + (600 - lx - wx) / 2
    y0 = (H + th - wy) / 2 + 30
    top = [(x0, y0), (x0 + lx, y0), (x0 + lx + wx, y0 + wy), (x0 + wx, y0 + wy)]
    shade = lambda c, f: tuple(int(v * f) for v in c)  # noqa: E731
    d.polygon([(x0, y0), (x0 + lx, y0), (x0 + lx, y0 + th), (x0, y0 + th)], fill=shade(colour, 0.72), outline="black")
    d.polygon([(x0 + lx, y0), (x0 + lx + wx, y0 + wy), (x0 + lx + wx, y0 + wy + th), (x0 + lx, y0 + th)], fill=shade(colour, 0.55), outline="black")
    d.polygon(top, fill=colour, outline="black")
    if pattern:
        pattern_face(img, top, pattern)
        d.polygon(top, outline="black")
    for pts in ([top[0], top[1]], [top[1], top[2]]):
        d.line(pts, fill="black", width=3)
    dim_h(d, x0, x0 + lx, y0 + th + 70, length_label or hu(l), fnt)
    # szélesség: a jobb oldali ferde él mentén
    ox, oy = 40, 10
    a, b = (x0 + lx + ox, y0 + th + oy), (x0 + lx + wx + ox, y0 + wy + th + oy)
    d.line([a, b], fill="black", width=2)
    d.text(((a[0] + b[0]) / 2 + 18, (a[1] + b[1]) / 2 - 10), hu(w), fill="black", font=fnt)
    if not t:
        import numpy as np
        ys, xs = np.where(np.asarray(img.convert("L")) < 250)
        return img.crop((max(xs.min() - 40, 0), max(ys.min() - 40, 0), min(xs.max() + 40, W), min(ys.max() + 40, H)))
    # vastagság
    d.line([(x0 - 30, y0), (x0 - 30, y0 + th)], fill="black", width=2)
    for y in (y0, y0 + th):
        d.line([(x0 - 42, y), (x0 - 18, y)], fill="black", width=2)
    tw = d.textlength(f"s = {hu(t)}", font=fnt)
    d.text((x0 - 50 - tw, y0 + th / 2 - 20), f"s = {hu(t)}", fill="black", font=fnt)
    import numpy as np
    ys, xs = np.where(np.asarray(img.convert("L")) < 250)
    m = 40
    return img.crop((max(xs.min() - m, 0), max(ys.min() - m, 0), min(xs.max() + m, W), min(ys.max() + m, H)))


# ---------------------------------------------------------------- megnevezés-értelmezés

def corner_radii(low, t):
    """Zártszelvény sarokrádiusza a névből: „R7/3”, „R7/R3”, „OR3/IR1” = külső/belső; egyetlen „R5” = külső,
    ekkor a belső a falvastagsággal kisebb (koncentrikus ív). Nincs megadva -> None."""
    m = re.search(r"\bor\s*(\d+(?:[.,]\d+)?)\s*/\s*ir\s*(\d+(?:[.,]\d+)?)", low) or \
        re.search(r"\br\s*(\d+(?:[.,]\d+)?)\s*/\s*r?\s*(\d+(?:[.,]\d+)?)", low)
    if m:
        return f(m.group(1)), f(m.group(2))
    m = re.search(r"\br\s*(\d+(?:[.,]\d+)?)", low)
    if m:
        ro = f(m.group(1))
        return ro, max(ro - t, 0)
    return None


def rhs(specs, low, a, b, t):
    """Zártszelvény rajzadat; ha a névben sarokrádiusz van, azzal lekerekítve (és az adatlapon is)."""
    r = corner_radii(low, t)
    if not r:
        return ("rhs", a, b, t)
    specs["Sarokrádiusz"] = f"külső R{hu(r[0])} / belső R{hu(r[1])}" if r[1] else f"külső R{hu(r[0])}, belső éles"
    return ("rhs", a, b, t, *r)


def parse(p):
    n = p["name"].replace("×", "x")
    low = n.lower()
    elox = "elox" in low
    specs, draw = {}, None
    # lemez: "S 3x1250x3200 mm Alu lemez EN AW-1050A H14/H24"
    m = re.match(rf"S\s*{NUM}(?:\s*/\s*{NUM})?\s*x\s*{NUM}(?:\s*x\s*{NUM})?", n)
    if m and ("lemez" in low or "szalag" in low or "cseppmint" in low):
        t, tp, w, l = m.group(1), m.group(2), m.group(3), m.group(4)
        specs.update({"Vastagság": f"{hu(f(t))} mm" + (f" (mintával {hu(f(tp))} mm)" if tp else ""), "Szélesség": f"{w} mm"})
        if tp:
            specs["Felület"] = "cseppmintás (DUETT: kétirányú csepp)" if "duett" in low else "gyémántmintás" if "diamond" in low else "cseppmintás, csúszásgátló"
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
        elif tp:
            pass
        elif elox:
            specs["Felület"] = "eloxált"
        elif "rízs" in low or "rizs" in low:
            specs["Felület"] = "rizsmintás (csúszásgátló)"
        colour = (243, 243, 240) if r else (205, 210, 216)
        pattern = ("diamond" if "diamond" in low else "duett" if "duett" in low else "rizs" if re.search(r"r[ií]zs", low)
                   else "quintett" if (tp or "cseppmint" in low) else None)
        return specs, ("sheet", f(w), f(l) if l else 0, f(t), colour, None if l else "tekercs", pattern)
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
        colour = (176, 141, 99) if "mdf" in low else (104, 72, 44) if re.search(r"fenol|film", low) else (214, 180, 130)
        a, b = sorted((f(m.group(2)), f(m.group(3))))
        return specs, ("sheet", a, b, f(m.group(1)), colour, None)
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
        colour = (214, 234, 240) if "pvc" in low else (58, 58, 60)
        if a3:
            return specs, ("sheet", *sorted((f(a2), f(a3))), f(a1), colour, None)
        if f(a1) < 40:
            return specs, ("sheet", f(a2), 0, f(a1), colour, f"L = {L.group(1)} m" if L else "tekercs")
        return specs, ("sheet", *sorted((f(a1), f(a2))), 0, colour, None)
    # üvegszálas poliészter (GRP) lemez tekercsben: "POLYDET High Gloss 2000/1,5 Corona"
    m = re.search(rf"POLYDET.*?(\d{{4}})\s*/\s*{NUM}", n, re.I)
    if m:
        specs.update({"Szélesség": f"{m.group(1)} mm", "Vastagság": f"{hu(f(m.group(2)))} mm", "Kiszerelés": "tekercs",
                      "Anyag": "üvegszál-erősítésű poliészter (GRP)"})
        if "gloss" in low:
            specs["Felület"] = "magasfényű gélbevonat"
        if "roughened" in low:
            specs["Hátoldal"] = "érdesített (ragasztáshoz)"
        elif "corona" in low:
            specs["Hátoldal"] = "corona-kezelt (ragasztáshoz)"
        return specs, ("sheet", float(m.group(1)), 0, f(m.group(2)), (246, 247, 248), "tekercs")
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
        specs["Tömeg"] = f"{hu((2 * (a + b) - 4 * t) * t * AL / 1000, 3)} kg/fm (elméleti)"
        return specs, rhs(specs, low, a, b, t)
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
        return specs, rhs(specs, low, a, b, t)
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


def render(draw):
    return sheet(*draw[1:]) if draw[0] == "sheet" else drawing(*draw)


# a saját 3D renderek (scripts/profil3d) – a termékképek elé kerülnek, a rajz a harmadik kép
RENDER_DIR = Path(__file__).resolve().parents[2] / "public/termekkepek/3d"
MANIFEST = Path(__file__).resolve().parents[1] / "profil3d/profilok.json"


def material(specs, name):
    a = (specs.get("Anyag") or "").lower() + " " + name.lower()
    if "acél" in a:
        return "galv" if re.search(r"horg|zn|tűzi", a) else "steel"
    return "elox" if "elox" in a else "alu"


# a Quadris által küldött katalógusrajz első képként (a gyártói cikkszám nélkül kivágva): slug -> (kép, adatok)
CATALOG_FIRST = {
    "227686-50x35x3-5-mm-r4-oszlop-profil-elox": ("data/forras/caralu_1011345_rajz.png", {"Tömeg": "1,609 kg/m"}),  # Car-Alu 1011345
    "223219-100x25-mm-ponyvatarto-zartszelveny-elox": ("data/forras/metra_3219_rajz.png", {"Tömeg": "0,985 kg/m"}),  # Metra R 3219
    "222266-100x25-mm-ponyvatarto-zartszelveny-gk": ("data/forras/kety_w2266_rajz.png", {"Falvastagság": "1,3 mm"}),  # Grupa Kęty W2266
}


def with_renders(slug, drawing_img):
    renders = [f"/termekkepek/3d/{slug}-{i}.webp" for i in (1, 2) if (RENDER_DIR / f"{slug}-{i}.webp").exists()]
    first = []
    if slug in CATALOG_FIRST:
        first = [save_image(Image.open(ROOT / CATALOG_FIRST[slug][0]).convert("RGB"), slug, "meretrajz")]
    return first + renders + [drawing_img]


def main():
    existing = load_enrichment()
    updates, drawn, manifest = {}, 0, []
    for p in load_products():
        prev = existing.get(p["slug"])
        specs, draw = parse(p)
        if not draw and prev and prev.get("rajz"):  # más forrás adta meg a hiányzó méretet (pl. cső falvastagsága)
            draw = tuple(prev["rajz"])
        if prev and prev.get("source") != SOURCE:
            if (prev.get("images") and not prev.get("nevbolRajz")) or not draw:
                continue
            clear_images(p["slug"])
            merged = dict(prev)
            merged["specs"] = {**{k: v for k, v in specs.items() if k != "Anyag"}, **(prev.get("specs") or {})}
            drawing_img = save_image(render(draw), p["slug"], 1)
            if prev.get("fotok"):  # valódi gyártói fotó van – azt követi a rajz, 3D render nem kell
                merged["images"] = prev["fotok"] + [drawing_img]
            else:
                merged["images"] = with_renders(p["slug"], drawing_img)
                manifest.append({"slug": p["slug"], "draw": draw, "mat": material(merged["specs"], p["name"])})
            merged["nevbolRajz"] = True  # a rajz ebből a lépésből jön – újrafuttatáskor frissíthető
            updates[p["slug"]] = merged
            drawn += 1
            continue
        if len(specs) < 2:
            continue
        specs.update(CATALOG_FIRST.get(p["slug"], (None, {}))[1])
        images = []
        if draw:
            clear_images(p["slug"])
            images = with_renders(p["slug"], save_image(render(draw), p["slug"], 1))
            manifest.append({"slug": p["slug"], "draw": draw, "mat": material(specs, p["name"])})
            drawn += 1
        updates[p["slug"]] = {"source": SOURCE, "sourceUrl": "", "sourceTitle": p["name"], "matchedCode": "",
                              "specs": specs, "images": images}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False))
    # a más forrásúakat forrásuk megtartásával írjuk vissza
    update_enrichment({k: v for k, v in updates.items() if v["source"] == SOURCE}, SOURCE)
    update_enrichment({k: v for k, v in updates.items() if v["source"] != SOURCE})
    print(f"{SOURCE}: {len(updates)} termék adatlapja a megnevezésből, ebből {drawn} keresztmetszet-rajzzal")


if __name__ == "__main__":
    main()
