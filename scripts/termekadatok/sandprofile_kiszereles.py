"""Gumi- és kéderprofilok kiszerelése (karton) és gyártói minimális rendelése a SAND Profile katalógusból
(gesamtkatalog_en.pdf, „Sales unit [m]” és „Minimum order” oszlop).

A Quadris kérése: ezeknél a termékeknél a legkisebb rendelhető mennyiség egy karton (a kartont nem bontjuk meg),
és ahol a gyártó 1000 m vagy afölötti minimumot ad meg, azt is feltüntetjük.

A táblázat sorait a „Sales unit” oszlop értékei határozzák meg; minden sorhoz a hozzá legközelebbi (azonos
magasságú vagy fölötte álló) cikkszám tartozik. A cikkszám lehet két szó („A1 512”) vagy egybeírt („A3432*”).
A termékek a cikkszámuk (code), ennek hiányában a nevük elején álló cikkszám alapján párosulnak; ahol a katalógus
nem ad adatot, a meglévő „Kiszerelés [m]” érték marad.

Kimenet: data/kedergumi_kiszereles.json (slug -> karton, karton_m, gyartoi_min_m)
Használat: python3 scripts/termekadatok/sandprofile_kiszereles.py
"""

import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment  # noqa: E402

PDF = ROOT / ".cache/letoltes/https_www.sandprofile.com_media_gesamtkatalog_en.pdf"
OUT = ROOT / "data/kedergumi_kiszereles.json"
KIVETEL = {"m1-001-c-sin-aluminium"}  # alumínium sín, méterre (a Quadris kérésére kimarad)
# kézi javítások a katalógushoz képest (a D2 230 501 m / 1002 m-es adata a Quadris szerint helyes)
JAVITAS = {}
CODE = re.compile(r"^([A-Z]\d{1,2})\s?(\d{3}(?:/\d+)?)")


def norm(code):
    m = CODE.match(code.upper().replace("*", "").strip())
    return f"{m.group(1)} {m.group(2)}" if m else None


def meters(unit):
    """„2x50” -> 100, „50,1” -> 50.1; értelmezhetetlen -> None."""
    m = re.fullmatch(r"(?:(\d+)\s*x\s*)?(\d+(?:[.,]\d+)?)", (unit or "").strip())
    if not m:
        return None
    return (int(m.group(1)) if m.group(1) else 1) * float(m.group(2).replace(",", "."))


def parse_catalogue():
    res = {}
    for page in pymupdf.open(PDF):
        W = page.get_text("words")
        heads = [w for w in W if w[4] == "Sales"]
        for h in heads:
            mins = [w for w in W if w[4] == "Minimum" and abs(w[1] - h[1]) < 3 and w[0] > h[0]]
            if not mins:
                continue
            sx, mx = (h[0] + h[2]) / 2, (mins[0][0] + mins[0][2]) / 2
            bottom = min([o[1] for o in heads if o[1] > h[1] + 5] + [1e9])
            codes = []  # (y, cikkszám) a táblázat bal oldalán
            for i, w in enumerate(W):
                if not (h[1] < w[1] < bottom and w[2] < h[0] - 40):
                    continue
                text = w[4]
                nxt = [v for v in W if abs(v[1] - w[1]) < 2 and 0 < v[0] - w[2] < 8]
                if re.fullmatch(r"[A-Z]\d{1,2}", text) and nxt:
                    text += " " + nxt[0][4]
                c = norm(text)
                if c and (re.fullmatch(r"[A-Z]\d{1,2}", w[4]) or re.fullmatch(r"[A-Z]\d{4,}.*", w[4])):
                    codes.append(((w[1] + w[3]) / 2, c))
            for v in W:
                cy = (v[1] + v[3]) / 2
                if not (h[3] + 8 < v[1] < bottom and abs((v[0] + v[2]) / 2 - sx) < 22 and meters(v[4])):
                    continue
                mo = [u for u in W if abs((u[0] + u[2]) / 2 - mx) < 24 and abs((u[1] + u[3]) / 2 - cy) < 3]
                near = [c for c in codes if c[0] - 4 <= cy and cy - c[0] < 40]
                if not near:
                    continue
                code = max(near, key=lambda c: c[0])[1]  # a sor magasságában vagy fölötte a legközelebbi
                if code in res:
                    continue
                res[code] = (v[4], mo[0][4] if mo else None)
    return res


def main():
    cat = parse_catalogue()
    data = load_enrichment()
    products = json.loads((ROOT / "src/data/catalog.json").read_text())["products"]
    products += json.loads((ROOT / "src/data/bovitett.json").read_text()).get("products", [])
    torolt = json.loads((ROOT / "data/torolt_termekek.json").read_text())
    javitasok = json.loads((ROOT / "data/termek_javitasok.json").read_text())  # a kézzel pótolt cikkszámok
    out, nincs = {}, []
    for p in products:
        if p["group"] != "kedergumik" or p["slug"] in KIVETEL or p["slug"] in torolt:
            continue
        specs = {**(p.get("specs") or {}), **(data.get(p["slug"], {}).get("specs") or {})}
        code = norm(javitasok.get(p["slug"], {}).get("code") or p.get("code") or "") or norm(p["name"])
        unit, mo = JAVITAS.get(code) or cat.get(code, (None, None))
        if not meters(unit):
            unit, mo = specs.get("Kiszerelés [m]"), specs.get("Minimális rendelés [m]")
        m = meters(unit)
        if not m:
            nincs.append(p["slug"])
            continue
        e = {"karton": unit.replace(" ", ""), "karton_m": m}
        mo_m = meters((mo or "").replace(".", ""))
        if mo_m and mo_m >= 1000:
            e["gyartoi_min_m"] = mo_m
        out[p["slug"]] = e
    OUT.write_text(json.dumps({"_leiras": __doc__.split("\n\n")[1].replace("\n", " "), **out}, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(out)} termék kiszerelése, ebből {sum('gyartoi_min_m' in e for e in out.values())} gyártói minimummal; adat nélkül: {len(nincs)}")
    for s in nincs:
        print("  nincs kiszerelés:", s)


if __name__ == "__main__":
    main()
