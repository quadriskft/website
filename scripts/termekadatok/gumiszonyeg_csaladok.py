"""Gumiszőnyegek csoport: az azonos típusú és azonos vastagságú termékek egy termékbe (termékcsalád) a Quadris
kérésére; a termékoldalon a rendelhető méretek (szélesség × hossz) táblázatban, a listában egy kártya.

A család kulcsa: alkategória + típus + vastagság.
- a bővített kínálat (Gummitrading-adatok): a típus a cikkszám első szava (pl. SM, SMM, 4012G, PU70), a név a
  vastagság előtti rész; a méret a név végéről (a ≤ 3 számú szélesség méterben értendő)
- a Quadris Excel-termékei (G …): a név a méretek nélkül, a vastagság az első szám
Csak a legalább 2 tagú csoportokból lesz család; a már családba sorolt és a törölt termékek kimaradnak.
Kimenet: data/termek_csaladok.json „gumi-…” kulcsai (újragenerálva).

Használat: python3 scripts/termekadatok/gumiszonyeg_csaladok.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT  # noqa: E402

GROUP = "gumiszonyegek"
COLORS = {"Black": "fekete", "Black with blue dots": "fekete, kék pöttyös", "Black with grey dots": "fekete, szürke pöttyös",
          "fekete": "fekete", "Grey": "szürke"}
OUT = ROOT / "data/termek_csaladok.json"


def num(s):
    return float(s.replace(",", "."))


def hu(x):
    return f"{x:g}".replace(".", ",")


def extended_key(p):
    m = re.match(r"^(.*?) (\d+(?:,\d+)?) mm, ([\d,]+)×([\d,/]+) mm$", p["name"])
    if not m:
        return None
    base, th, w, l = m.groups()
    typ = (p.get("code") or "").split("-")[0]  # pl. „SM 3/0”, „SBR 3/2” (a szövetbetétek száma is)
    wv = num(w)
    if wv <= 3:  # méterben megadott tekercs / tábla
        size, sort = f"{w} × {l} m", (wv * 1000, l)
    else:
        size, sort = f"{w} × {l} mm" if l else f"{w} mm", (wv, l)
    return (p["category"], typ, base, th), f"{base} {th} mm", size, sort, th


def excel_key(p):
    name = p["name"]
    r = re.match(r"^G (?:(\d+)/)?(\d+)x(\d+)(?: mm)? R[aá]mpasz[őo]nyeg$", name)
    if r:  # rámpaszőnyeg: a név nem ad vastagságot (G 17/…, G 27/… külön típus)
        th, w, l = r.groups()
        return ("rampa", "G", th or ""), "Rámpaszőnyeg" + (f" {th} mm" if th else ""), f"{w} × {l} mm", (num(w), l), th or ""
    m = re.match(r"^G (\d+(?:[.,]\d+)?)[x/](\d+)(?:x(\d+))?\s*(?:mm)?\s+(.*)$", name)
    if not m:
        return None
    th, w, l, rest = m.groups()
    rest = re.sub(r"\s+", " ", rest).strip()
    rest = re.sub(r"^(2T S/S|S/S) (.*)$", r"\2 \1", rest)  # „2T S/S Általános gumiszőnyeg” -> „Általános gumiszőnyeg 2T S/S”
    rest = re.sub(r" L:\s*(\d+) m RS$", r" RS (\1 m-es tekercs)", rest)
    size = f"{w} × {l} mm" if l else f"{w} mm"
    return (p["category"], "G", rest, th), f"{rest} {th} mm", size, (num(w), l or ""), th


def main():
    products = json.loads((ROOT / "src/data/catalog.json").read_text())["products"]
    extended = json.loads((ROOT / "src/data/bovitett.json").read_text()).get("products", [])
    deleted = json.loads((ROOT / "data/torolt_termekek.json").read_text())
    fams = json.loads(OUT.read_text())
    fams = {k: v for k, v in fams.items() if not k.startswith("gumi-")}
    taken = {s for k, f in fams.items() if not k.startswith("_") for s in f["members"]}
    groups = {}
    for src, keyf in ((products, excel_key), (extended, extended_key)):
        for p in src:
            if p["group"] != GROUP or p["slug"] in deleted or p["slug"] in taken:
                continue
            k = keyf(p)
            if k is None:
                print("  nem értelmezhető név:", p["name"])
                continue
            key, name, size, sort, th = k
            color = COLORS.get((p.get("specs") or {}).get("Szín", ""), "")
            groups.setdefault(key, {"name": name, "th": th, "ext": keyf is extended_key, "members": []})["members"].append((sort, p["slug"], size, color))
    names = {}
    for key, g in groups.items():
        names.setdefault(g["name"], []).append(key)
    n = 0
    for key, g in groups.items():
        mem, values = sorted(g["members"]), {}
        sizes = [m[2] for m in mem]
        for _, slug, size, color in mem:
            same = [m[3] for m in mem if m[2] == size]
            v = f"{size} – {color}" if len(set(same)) > 1 and color else size
            if v in values.values():
                print("  azonos kivitel kétszer, a második külön marad:", slug)
                continue
            values[slug] = v
        if len(values) < 2:
            continue
        ins = re.fullmatch(r"SBR \d+/(\d)", key[1])
        tag = f"{ins.group(1)} szövetbetéttel" if ins else key[1]
        name = g["name"] + (f" ({tag})" if len(names[g["name"]]) > 1 else "")
        fid = "gumi-" + re.sub(r"[^a-z0-9]+", "-", f"{key[0]} {key[1]} {name}".lower()).strip("-")
        fams[fid] = {
            "name": name, "label": "Méret", "title": "Rendelhető méretek",
            "note": (f"{hu(num(g['th']))} mm vastag – az" if g["th"] else "Az") + " alábbi méretekben rendelhető.",
            "navigate": True,
            "table": ["Méret", "Vastagság [mm]"] if g["ext"] else ["Méret", "Vastagság"] if g["th"] else ["Méret"],
            "members": values,
        }
        n += 1
    OUT.write_text(json.dumps(fams, ensure_ascii=False, indent=1) + "\n")
    print(n, "gumiszőnyeg-család,", sum(len(f["members"]) for k, f in fams.items() if k.startswith("gumi-")), "termék")


if __name__ == "__main__":
    main()
