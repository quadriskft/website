"""Beszállítók TELJES kínálatának felvétele (nem csak az Excelben szereplő termékek).

Kimenet: src/data/bovitett.json – új termékcsoportok/kategóriák, termékek és az Excel
termékeinek átsorolása (moves). A weboldal (src/lib/catalog.js) összefésüli a
katalógussal. A képek a public/termekkepek alá kerülnek.

Használat: python3 scripts/termekadatok/teljes_kinalat.py [fuhrmann rubberselect gnc sandprofile dg]
"""

import html
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, fetch, save_image  # noqa: E402

OUT = ROOT / "src/data/bovitett.json"


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def load():
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {"groups": [], "categories": [], "renameGroups": {}, "products": [], "moves": {}}


def save(data):
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def replace_supplier(data, supplier, groups=(), categories=(), products=(), moves=None, rename=None):
    """Egy beszállító korábbi bejegyzéseinek cseréje az újakra."""
    data["products"] = [p for p in data["products"] if p.get("source") != supplier]
    data["groups"] = [g for g in data["groups"] if g.get("source") != supplier]
    data["categories"] = [c for c in data["categories"] if c.get("source") != supplier]
    data["moves"] = {k: v for k, v in data["moves"].items() if v.get("source") != supplier}
    for g in groups:
        data["groups"].append({**g, "source": supplier})
    for c in categories:
        data["categories"].append({**c, "source": supplier})
    data["products"] += [{**p, "source": supplier} for p in products]
    for k, v in (moves or {}).items():
        data["moves"][k] = {**v, "source": supplier}
    data["renameGroups"].update(rename or {})


def download_images(slug, urls, limit=3):
    clear_images(slug)
    out = []
    for n, url in enumerate(urls[:limit], start=1):
        try:
            out.append(save_image(fetch(url), slug, n))
        except Exception as err:  # noqa: BLE001
            print("  képhiba:", url, err)
    return out


def excel_products():
    return json.loads((ROOT / "src/data/catalog.json").read_text())["products"]


# ---------------------------------------------------------------- Fuhrmann

FU_BASE = "https://www.fuhrmann.at/de/"
FU_PAGES = ["stbw300", "stbw350", "stbw400", "stbw450", "stbw500", "stbw600", "stbw800", "stbw1000",
            "stbwfhd", "stbwfox", "stbwfoxl", "stbwfoxla", "stbwfoxln", "foxrock"]
FU_LABELS = {
    "blechstärke": "Lemezvastagság [mm]", "stärke": "Lemezvastagság [mm]",
    "breite oben": "Felső szélesség [mm]", "breite unten": "Alsó szélesség [mm]",
    "kg / m": "Tömeg [kg/m]", "gewicht": "Tömeg [kg/m]", "einsatzgebiet": "Felhasználás",
    "materialgüte": "Anyagminőség", "material": "Anyag", "produktionslängen": "Gyártási hossz",
    "längen": "Gyártási hossz [mm]", "höhe": "Magasság [mm]", "ausführung": "Kivitel",
}
FU_VALUES = {"Grundwand": "alap oldalfal", "Aufsatzwand": "magasító (ráépítő) oldalfal", "verzinkt": "horganyzott",
             "roh": "nyers", "grundiert": "alapozott", "bis": "–"}


def fu_desc(type_name):
    t = type_name.upper()
    if t.startswith("FOX-ROCK"):
        return "Extra erős acél oldalfal kőszállító billencsekhez, a legkeményebb igénybevételre."
    if t.startswith("FHD"):
        return "Heavy Duty acél oldalfal nehéz építőipari felépítményekhez."
    if t.startswith("FOX"):
        return "Heavy Duty acél oldalfal építőipari billencsekhez és platós felépítményekhez, nagy igénybevételre."
    if "HV" in t:
        return "Lézerhegesztett acél oldalfal homlok- és hátfalnak billencs és platós felépítményekhez, valamint oldalfalnak utánfutókhoz és könnyű teherautókhoz."
    return "Lézerhegesztett acél oldalfal nagy oldalnyomásra: billencs és platós teherautó-felépítményekhez, mezőgazdasági billencsekhez."


def fuhrmann():
    products, seen = [], set()
    for page in FU_PAGES:
        raw = fetch(FU_BASE + page + ".php").decode("utf-8", "ignore")
        heavy = not page.startswith("stbw") or page in ("stbwfhd", "stbwfox", "stbwfoxl", "stbwfoxla", "stbwfoxln")
        heavy = heavy and page != "stbw300"
        for table in re.findall(r"<table[^>]*>(.*?)</table>", raw, re.S):
            if "stahlbordwand/profile" not in table and "Type" not in table:
                continue
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
            imgs, types, attrs = [], [], []
            for r in rows:
                cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
                if not cells:
                    continue
                if "stahlbordwand/profile" in r:
                    imgs = [(re.search(r'src="([^"]+)"', c).group(1) if re.search(r'src="([^"]+)"', c) else None) for c in cells[1:]]
                    continue
                label = clean(cells[0])
                vals = [clean(c) for c in cells[1:]]
                if label.lower() in ("type", "typ"):
                    types = vals
                elif label and label.lower() not in ("datenblatt", "link", "beschreibung", "fotos"):
                    attrs.append((label, vals))
            for i, t in enumerate(types):
                t = t.replace('"', "").strip()
                if not t or not re.search(r"\d", t) and "ROCK" not in t.upper():
                    continue
                code = re.sub(r"\s+", " ", t)
                if code in seen:
                    continue
                seen.add(code)
                specs = {}
                for label, vals in attrs:
                    if i < len(vals) and vals[i]:
                        key = next((v for k, v in FU_LABELS.items() if label.lower().startswith(k)), label)
                        specs[key] = FU_VALUES.get(vals[i], vals[i])
                height = re.search(r"(\d{3,4})\s*$", code)
                if height and "Magasság [mm]" not in specs:
                    specs["Magasság [mm]"] = height.group(1)
                img = imgs[i] if i < len(imgs) else None
                slug = "acel-oldalfal-" + slugify(code)
                products.append({
                    "slug": slug, "code": code, "name": f"Acél oldalfal {code}" + (" mm" if height else ""),
                    "group": "acel-profilok",
                    "category": "heavy-duty-acel-oldalfalak" if heavy else "lezerhegesztett-acel-oldalfalak",
                    "specs": specs, "description": fu_desc(code),
                    "imageUrls": [FU_BASE + img] if img else [], "sourceUrl": FU_BASE + page + ".php",
                })
    for p in products:
        p["images"] = download_images(p["slug"], p.pop("imageUrls"))
    # az Excel HV/HVAK stb. oldalfalai ugyanezek a Fuhrmann típusok -> kategória áthelyezés
    moves = {}
    for ep in excel_products():
        if re.match(r"^(HV|HVAK|HVTT|HVAKKT|HVAKTT|B|BAK)\d*", ep["name"]) and ep["category"] == "acel-oldalfalak":
            moves[ep["slug"]] = {"group": "acel-profilok", "category": "lezerhegesztett-acel-oldalfalak"}
    cats = [
        {"group": "acel-profilok", "slug": "lezerhegesztett-acel-oldalfalak", "name": "Lézerhegesztett acél oldalfalak"},
        {"group": "acel-profilok", "slug": "heavy-duty-acel-oldalfalak", "name": "Heavy Duty acél oldalfalak"},
    ]
    return {"categories": cats, "products": products, "moves": moves}


# ---------------------------------------------------------------- Rubber Select

RS_BASE = "https://www.rubberselect.com/en/products/"
G = "gumiszonyegek"
RS_TYPES = {  # slug: (magyar név, kategória)
    "matting/trailermat": ("Utánfutó- és lószállító gumiszőnyeg", "istallo-szonyeg"),
    "matting/stablemat": ("Istálló gumiszőnyeg", "istallo-szonyeg"),
    "matting/cowmat": ("Állattartó gumiszőnyeg", "istallo-szonyeg"),
    "matting/stud-mat": ("Noppos gumiszőnyeg", "noppos-gumi"),
    "matting/stud-mat-4012": ("Noppos gumiszőnyeg 4012", "noppos-gumi"),
    "matting/stud-mat-in45": ("Noppos gumiszőnyeg IN45", "noppos-gumi"),
    "matting/stud-mat-nobra": ("Noppos gumiszőnyeg NOBRA", "noppos-gumi"),
    "matting/mini-stud": ("Mini noppos gumiszőnyeg", "noppos-gumi"),
    "matting/square-stud-mat": ("Négyzetes noppos gumiszőnyeg", "noppos-gumi"),
    "matting/fine-rib-mat": ("Finombordás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/combi-rib-mat": ("Kombi bordás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/broad-rib-mat": ("Széles bordás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/wide-rib-mat": ("Nagybordás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/fishbone-mat": ("Halszálkamintás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/checker-mat": ("Kockamintás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/diamond-mat": ("Gyémántmintás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/hammerblow-mat": ("Kalapácsütés-mintás gumiszőnyeg", "bordas-es-mintas-gumiszonyegek"),
    "matting/standard-ringmat": ("Lyukacsos (gyűrűs) gumiszőnyeg", "lyukacsos-gumiszonyegek"),
    "matting/standard-ringmat-roll": ("Lyukacsos gumiszőnyeg tekercsben", "lyukacsos-gumiszonyegek"),
    "matting/ringmat-roll-light": ("Könnyű lyukacsos gumiszőnyeg tekercsben", "lyukacsos-gumiszonyegek"),
    "matting/entrance-ringmat": ("Bejárati lyukacsos gumiszőnyeg", "lyukacsos-gumiszonyegek"),
    "matting/connective-ringmat": ("Összekapcsolható lyukacsos gumiszőnyeg", "lyukacsos-gumiszonyegek"),
    "matting/heavy-duty-ring-mat": ("Nagy teherbírású lyukacsos gumiszőnyeg", "lyukacsos-gumiszonyegek"),
    "matting/ring-mat-connector": ("Összekötő elem lyukacsos gumiszőnyeghez", "lyukacsos-gumiszonyegek"),
    "matting/workplace-mat": ("Munkahelyi gumiszőnyeg", "munkahelyi-szonyegek"),
    "matting/workplace-mat-roll": ("Munkahelyi gumiszőnyeg tekercsben", "munkahelyi-szonyegek"),
    "matting/workplace-mat-yellow-border": ("Munkahelyi gumiszőnyeg sárga szegéllyel", "munkahelyi-szonyegek"),
    "matting/workplace-mat-yellow-border-roll": ("Munkahelyi gumiszőnyeg sárga szegéllyel, tekercsben", "munkahelyi-szonyegek"),
    "nrsbr-rubber-sheets/allpac": ("Gumilemez NR/SBR", "gumilemezek"),
    "nrsbr-rubber-sheets/allpac-insertions": ("Szövetbetétes gumilemez NR/SBR", "gumilemezek"),
    "nrsbr-rubber-sheets/allpac-plate": ("Gumilap NR/SBR", "gumilemezek"),
    "pu/premium-pu": ("Prémium poliuretán (PU) lemez", "pu-lemezek"),
    "pu/high-wear-resistant-pu": ("Kopásálló poliuretán (PU) lemez", "pu-lemezek"),
    "pu/pu-70-shore": ("Poliuretán (PU) lemez 70 Shore A", "pu-lemezek"),
    "pu/pu-80-shore": ("Poliuretán (PU) lemez 80 Shore A", "pu-lemezek"),
    "pu/pu-90-shore": ("Poliuretán (PU) lemez 90 Shore A", "pu-lemezek"),
    "pvc/pvc-sheeting": ("Víztiszta PVC lemez", "viztiszta-pvc"),
    "pvc/pvc-strips": ("PVC függönycsík", "pvc-fuggonyok"),
    "pvc/hanging-set": ("Felfüggesztő készlet PVC függönyhöz", "pvc-fuggonyok"),
    "pvc/suspension-rail": ("Felfüggesztő sín PVC függönyhöz", "pvc-fuggonyok"),
    "sponge-rubber/epdm-sponge-rubber": ("EPDM moosgumi (szivacsgumi)", "moosgumi"),
    "granulate/protection-mat-standard": ("Gumigranulátum védőlap", "granulatum-lapok"),
    "granulate/protection-mat-strong": ("Erősített gumigranulátum védőlap", "granulatum-lapok"),
    "granulate/sportsflooring": ("Gumigranulátum padlólap", "granulatum-lapok"),
}
RS_CATS = [
    ("bordas-es-mintas-gumiszonyegek", "Bordás és mintás gumiszőnyegek"),
    ("lyukacsos-gumiszonyegek", "Lyukacsos (gyűrűs) gumiszőnyegek"),
    ("munkahelyi-szonyegek", "Munkahelyi gumiszőnyegek"),
    ("gumilemezek", "Gumilemezek (NR/SBR)"),
    ("pu-lemezek", "Poliuretán (PU) lemezek"),
    ("pvc-fuggonyok", "PVC függönycsíkok és tartozékok"),
    ("moosgumi", "Moosgumi (szivacsgumi)"),
    ("granulatum-lapok", "Gumigranulátum lapok"),
]
RS_DESC = {
    "istallo-szonyeg": "Csúszásmentes, könnyen tisztítható gumiszőnyeg lószállító felépítményekbe, utánfutókba és istállókba.",
    "noppos-gumi": "Noppos felületű, csúszásgátló gumiszőnyeg rakterek, rámpák és járófelületek burkolására.",
    "bordas-es-mintas-gumiszonyegek": "Mintázott, csúszásgátló gumiszőnyeg rakterek, járófelületek és munkaterületek burkolására.",
    "lyukacsos-gumiszonyegek": "Vízelvezető, lyukacsos gumiszőnyeg nedves vagy szennyezett felületekre, bejáratokhoz és rámpákhoz.",
    "munkahelyi-szonyegek": "Ergonomikus, csúszásmentes gumiszőnyeg álló munkahelyekre és műhelyekbe.",
    "gumilemezek": "Általános célú természetes és szintetikus gumi (NR/SBR) lemez tömítéshez, kopás- és ütésvédelemhez.",
    "pu-lemezek": "Nagy kopásállóságú poliuretán lemez erős igénybevételű felületek védelmére.",
    "viztiszta-pvc": "Átlátszó, rugalmas PVC lemez védőfalakhoz, takarásokhoz és függönyökhöz.",
    "pvc-fuggonyok": "PVC csíkfüggöny és tartozékai hűtött és dobozos felépítmények hőszigetelő ajtófüggönyéhez.",
    "moosgumi": "Zártcellás EPDM szivacsgumi tömítésekhez, rezgés- és zajcsillapításhoz.",
    "granulatum-lapok": "Gumigranulátumból préselt, ütéscsillapító védő- és padlólap.",
}
RS_LABELS = {"quality": "Anyagminőség", "colour": "Szín", "color": "Szín", "min. temperature": "Min. hőmérséklet",
             "max. temperature": "Max. hőmérséklet", "specific gravity": "Fajsúly", "hardness": "Keménység",
             "tensile strength": "Szakítószilárdság", "elongation at break": "Szakadási nyúlás",
             "thickness": "Vastagság [mm]", "width": "Szélesség [mm]", "length": "Hossz [mm]", "weight": "Tömeg",
             "roll length": "Tekercshossz [m]", "diameter": "Átmérő [mm]", "size": "Méret"}
RS_COLOURS = {"black": "fekete", "grey": "szürke", "gray": "szürke", "red": "piros", "green": "zöld", "blue": "kék",
              "yellow": "sárga", "white": "fehér", "transparent": "átlátszó", "natural": "natúr", "brown": "barna"}


def rs_value(v):
    v = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", v)  # holland ezres elválasztó: 1.550 -> 1550
    return v.replace("grs/cm", "g/cm").replace("Mpa", "MPa")


def rs_label(label):
    low = label.lower().strip()
    for k, v in RS_LABELS.items():
        if low.startswith(k):
            return v
    return None


def rubberselect():
    products = []
    for path, (hu_name, cat) in RS_TYPES.items():
        try:
            raw = fetch(RS_BASE + path).decode("utf-8", "ignore")
        except Exception as err:  # noqa: BLE001
            print("  hiba:", path, err)
            continue
        body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
        text = clean(body)
        common_specs = {}
        for key in ["Quality", "Colour", "Min. temperature", "Max. temperature", "Specific gravity", "Hardness",
                    "Tensile strength", "Elongation at break"]:
            m = re.search(rf"{re.escape(key)}\s+(.+?)(?=\s+(?:Quality|Colour|Min\. temperature|Max\. temperature|Specific gravity|Hardness|Tensile strength|Elongation at break|Article number|Features|Application|Thickness|Width)\b)", text)
            if m:
                v = m.group(1).strip()
                if key == "Colour":
                    v = ", ".join(RS_COLOURS.get(x.strip().lower(), x.strip()) for x in re.split(r"[/,]| and ", v))
                common_specs[RS_LABELS[key.lower()]] = rs_value(v)
        img = re.search(r'src="(/sites/default/files/styles/product_afbeelding/[^"]+)"', raw)
        img_url = "https://www.rubberselect.com" + html.unescape(img.group(1)) if img else None
        rows = []
        for table in re.findall(r"<table.*?</table>", raw, re.S):
            heads = [clean(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)]
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
                cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
                if cells and len(cells) == len(heads):
                    rows.append(dict(zip(heads, cells)))
        if not rows:
            rows = [{}]
        base_slug = "rs-" + slugify(path.split("/")[-1])
        imgs = download_images(base_slug, [img_url] if img_url else [], 1)
        for row in rows:
            code = next((v for k, v in row.items() if "article" in k.lower() or "code" in k.lower()), "")
            specs = dict(common_specs)
            dims = {}
            for k, v in row.items():
                lab = rs_label(k)
                if lab and v and "article" not in k.lower():
                    specs[lab] = rs_value(v)
                    dims[lab] = rs_value(v)
            name = hu_name
            th = dims.get("Vastagság [mm]")
            w, l = dims.get("Szélesség [mm]"), dims.get("Hossz [mm]")
            if th:
                name += f" {th} mm"
            if w and l:
                name += f", {w}×{l} mm"
            elif w:
                name += f", {w} mm széles"
            slug = slugify(f"{hu_name} {code or th or ''} {w or ''} {l or ''}")
            products.append({"slug": slug, "code": code, "name": name, "group": G, "category": cat, "specs": specs,
                             "description": RS_DESC.get(cat, ""), "images": imgs, "sourceUrl": RS_BASE + path})
    # egyedi slugok
    seen = {}
    for p in products:
        n = seen.get(p["slug"], 0)
        seen[p["slug"]] = n + 1
        if n:
            p["slug"] = f"{p['slug']}-{n + 1}"
    cats = [{"group": G, "slug": s, "name": n} for s, n in RS_CATS]
    return {"categories": cats, "products": products, "rename": {G: "Gumiszőnyegek és gumilemezek"}}


# ---------------------------------------------------------------- G&C Systems

GC_GROUP = "szellozes-tetoablakok-vilagitas"
GC_CATS = {  # gyártói kategória -> (slug, név, leírás)
    "roofto-ventilators": ("tetoventilatorok", "Tetőventilátorok", "Tetőventilátor lószállító, dobozos és személyszállító felépítményekhez: hatékony légcsere, 12/24 V-os és motor nélküli kivitelben."),
    "roof-hatches": ("tetoablakok", "Tetőablakok", "Kézi és elektromos tetőablak felépítményekhez: természetes fény és szellőzés, vészkijáratként is."),
    "internal-ventilation-valve": ("belso-szellozok-es-racsok", "Belső szellőzők és rácsok", "Belső szellőzőszelepek, rácsok és takarók a légáram szabályozásához."),
    "axial-radial-ventilators": ("axial-es-radial-ventilatorok", "Axiál- és radiálventilátorok", "Beépíthető axiál- és radiálventilátorok kényszerszellőzéshez."),
    "lighting": ("vilagitas", "Belső világítás", "LED belső világítás felépítményekbe, 12/24 V."),
    "ceiling-flow": ("mennyezeti-legelosztok", "Mennyezeti légelosztók", "Mennyezeti légelosztó egyenletes, huzatmentes szellőzéshez."),
    "air-purifier": ("legtisztitok", "Légtisztítók", "Légtisztító állatszállító és személyszállító felépítményekbe."),
    "various": ("szelloztetes-kiegeszitok", "Kiegészítők és vezérlés", "Kapcsolók, fordulatszám-szabályzók, hószűrők és egyéb kiegészítők szellőzőrendszerekhez."),
}
GC_NAMES = {
    "control-unit": "Tetőablak vezérlőegység", "electric-round": "Elektromos tetőablak, kerek",
    "roof-hatches-electric-large": "Elektromos tetőablak, nagy", "roof-hatches-manual-big": "Kézi tetőablak, nagy",
    "roof-hatches-manual-small": "Kézi tetőablak, kicsi", "exhaust-ventilator": "Elszívó tetőventilátor",
    "le-mans": "Le Mans tetőventilátor", "le-mans-ll": "Le Mans LL alacsony tetőventilátor",
    "rooftop_ventilators": "Tetőventilátor", "turbo-ii": "Turbo II tetőventilátor", "turbo-iii": "Turbo III tetőventilátor",
    "winglet": "Winglet tetőventilátor", "flower-power": "Flower Power belső szellőző", "grill-big": "Szellőzőrács, nagy",
    "grill-small": "Szellőzőrács, kicsi", "light-metal-rotary-valve": "Könnyűfém forgószelep", "rotary-valve": "Forgószelep",
    "rotating-valve": "Állítható szellőzőszelep", "v12-2": "V12 belső szellőzőszelep", "axial-ventilator": "Axiálventilátor",
    "axialventilator": "Axiálventilátor, kompakt", "radial-ventilator": "Radiálventilátor",
    "lighting-rectangle": "LED lámpa, szögletes", "lighting-round": "LED lámpa, kerek",
    "ceilingflow": "Ceilingflow mennyezeti légelosztó", "floor-ventilator": "Padlószellőző",
    "floor-ventilator-2": "Padlószellőző, nagy", "snowfilter": "Hószűrő tetőventilátorhoz",
    "speedcontrol": "Fordulatszám-szabályzó ventilátorhoz", "switch-fan": "Ventilátorkapcsoló",
    "switch-round": "Kapcsoló, kerek", "switch-square": "Kapcsoló, szögletes",
    "air-purifier-large": "Légtisztító, nagy", "air-purifier-small": "Légtisztító, kicsi",
}


def gc_move_category(name):
    n = name.lower()
    if "tetőablak" in n:
        return "tetoablakok"
    if "lámpa" in n:
        return "vilagitas"
    if "takaró" in n or "flower" in n or "rács" in n:
        return "belso-szellozok-es-racsok"
    if "kapcsoló" in n or "vezérlő" in n:
        return "szelloztetes-kiegeszitok"
    return "tetoventilatorok"


def gnc():
    base = "https://gnc-systems.com/en/"
    excel = [p for p in excel_products() if p["supplier"] == "G&C termékek"]
    excel_codes = {re.sub(r"\W", "", (p["supplierCode"] or "")).upper() for p in excel}
    products = []
    for mcat, (cat, _, desc) in GC_CATS.items():
        raw = fetch(f"{base}product-category/{mcat}/").decode("utf-8", "ignore")
        for slug in sorted(set(re.findall(r'href="https://gnc-systems.com/en/products/([^"/]+)/"', raw))):
            page = fetch(f"{base}products/{slug}/").decode("utf-8", "ignore")
            text = clean(re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S))
            codes = list(dict.fromkeys(re.findall(r"\b\d{2}-\d{4}(?:-[A-Z]{1,3})?\b", text)))
            if codes and any(re.sub(r"\W", "", c).upper() in excel_codes for c in codes):
                continue  # az Excel már tartalmazza
            specs = {}
            if codes:
                import gnc as gnc_mod
                for pdf in re.findall(r'href="([^"]+\.pdf)"', page):
                    s_pdf, _ = gnc_mod.pdf_specs(pdf, codes[0])
                    specs.update({k: v for k, v in s_pdf.items() if k not in specs})
                if len(codes) > 1:
                    specs["Változatok"] = ", ".join(codes[:8])
            if re.search(r"Black\s*/\s*White|White\s*/\s*Black", text, re.I):
                specs["Szín"] = "fekete / fehér"
            v = re.search(r"\b(12\s*/\s*24|12|24)\s*V\b", text)
            if v:
                specs["Feszültség"] = v.group(1).replace(" ", "") + " V"
            if re.search(r"EMC approved", text, re.I):
                specs["Tanúsítás"] = "EMC jóváhagyott"
            og = re.search(r'og:image" content="([^"]+)"', page)
            name = GC_NAMES.get(slug, slug.replace("-", " ").title())
            pslug = "gc-" + slugify(slug)
            products.append({"slug": pslug, "code": codes[0] if codes else "", "name": name, "group": GC_GROUP,
                             "category": cat, "specs": specs, "description": desc,
                             "images": download_images(pslug, [og.group(1)] if og else [], 1),
                             "sourceUrl": f"{base}products/{slug}/"})
    moves = {p["slug"]: {"group": GC_GROUP, "category": gc_move_category(p["name"])} for p in excel}
    group = {"slug": GC_GROUP, "name": "Szellőzés, tetőablakok, világítás", "icon": "Fan",
             "text": "Tetőventilátorok, tetőablakok, belső szellőzők és LED világítás – lószállító és dobozos felépítményekhez is."}
    cats = [{"group": GC_GROUP, "slug": c[0], "name": c[1]} for c in GC_CATS.values()]
    return {"groups": [group], "categories": cats, "products": products, "moves": moves}


# ---------------------------------------------------------------- SAND Profile (teljes katalógus)

SP_GROUP = "kedergumik"
SP_SECTIONS = [  # (kulcsszó a lapszélen, kategória slug, név, egyes számú típusnév, leírás)
    ("edge protector", "elvedo-profilok", "Élvédő profilok", "Élvédő profil", "Fémbetétes élvédő profil lemezélek, peremek takarására és védelmére."),
    ("sponge rubber", "moosgumi-profilok", "Moosgumi profilok", "Moosgumi profil", "Szivacsgumi (moosgumi) tömítőprofil ajtókhoz, szervizajtókhoz, burkolatokhoz."),
    ("gista", "gista-kederprofilok", "Kéder- és ablakgumi profilok (Gista)", "Kéderprofil", "Kéder- és ablakgumi profil üvegek, panelek rögzítéséhez és tömítéséhez."),
    ("filler", "kitolto-profilok", "Kitöltő (zár) profilok", "Kitöltő profil", "Kitöltő (zár) profil kéderprofilokhoz."),
    ("glass run", "uvegvezeto-profilok", "Üvegvezető profilok", "Üvegvezető profil", "Üvegvezető profil tolóablakokhoz és ajtóüvegekhez."),
    ("monoprofile", "mono-profilok", "Mono tömítőprofilok", "Mono profil", "Egyanyagú tömítőprofil."),
    ("finger guard", "ujjvedo-profilok", "Ujjvédő profilok", "Ujjvédő profil", "Ujjbecsípődés elleni védőprofil ajtókhoz."),
    ("special", "specialis-gumiprofilok", "Speciális gumiprofilok", "Gumiprofil", "Speciális gumiprofil egyedi felhasználásra."),
    ("sealing", "tomitoprofilok", "Élvédő tömítőprofilok", "Élvédő tömítőprofil", "Fémbetétes élvédő tömítőprofil ajtókhoz, szervizajtókhoz és rakterekhez: élvédelem és tömítés egyben."),
]


def sandprofile_full():
    import pymupdf
    import sandprofile as spm
    doc = pymupdf.open(stream=fetch(spm.PDF), filetype="pdf")
    index = spm.index_catalog(doc)
    # lapok fejezete a lapszéli függőleges feliratból (ha nincs, az előző lapé)
    section_of, current = {}, None
    for i, pg in enumerate(doc):
        side = []
        for b in pg.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                if abs(ln["dir"][0]) < 0.5:
                    side.append("".join(sp["text"] for sp in ln["spans"]).replace("ﬁ ", "fi").replace("ﬁ", "fi").lower())
        for key, *_ in SP_SECTIONS:
            if any(key in x for x in side):
                current = key
                break
        section_of[i] = current
    meta = {k: rest for k, *rest in SP_SECTIONS}
    excel = [p for p in excel_products() if p["supplier"] == "Sand-Profile"]
    excel_codes = {}
    for p in excel:
        for c in [p["supplierCode"]] + re.findall(r"\b[A-E]\d\s?\d{3}(?:/\d)?", p["name"]):
            if c:
                excel_codes[spm.norm(c)] = p
    products, moves, used_cats = [], {}, set()
    for code_norm, (pno, design, specs) in index.items():
        key = section_of.get(pno) or "special"
        cat, cat_name, singular, desc = meta[key]
        if code_norm in excel_codes:
            moves[excel_codes[code_norm]["slug"]] = {"group": SP_GROUP, "category": cat}
            used_cats.add(key)
            continue
        code = re.sub(r"^([A-Z]\d)(\d{3})", r"\1 \2", code_norm)
        extra = []
        if specs.get("Szín"):
            extra.append(specs["Szín"])
        rng = next((v for k, v in specs.items() if k.startswith("Szorítási")), None)
        if rng:
            extra.append(f"{rng} mm")
        name = f"{singular} {code}" + (f" – {', '.join(extra)}" if extra else "")
        slug = "sp-" + slugify(code)
        img = []
        if design:
            clear_images(slug)
            img = [save_image(spm.render(doc[pno], design), slug)]
        products.append({"slug": slug, "code": code, "name": name, "group": SP_GROUP, "category": cat, "specs": specs,
                         "description": desc, "images": img, "sourceUrl": f"{spm.PDF}#page={pno + 1}"})
        used_cats.add(key)
    cats = [{"group": SP_GROUP, "slug": meta[k][0], "name": meta[k][1]} for k, *_ in SP_SECTIONS if k in used_cats]
    return {"categories": cats, "products": products, "moves": moves, "rename": {SP_GROUP: "Gumi- és kéderprofilok"}}


# ---------------------------------------------------------------- DG TS (Officina De Giambattista, IT)
# A gyártó oldala (en.dg-ts.it) sorozatonként (BB2…BB10) mutatja be a rakoncákat, cikkszámok nélkül.
# Az oldal SiteGround-captchával védett: gyakori kérésnél 202-es "captcha" választ ad, ezért
# türelmesen újrapróbáljuk, és csak a valódi választ tesszük a gyorsítótárba.

DG_UP = "https://dg-ts.it/wp-content/uploads/"
DG_PDF = "https://en.dg-ts.it/wp-content/uploads/2025/07/DG-TS_Brochure-2024.pdf"
DG_CAT = "dg"  # az Excel "DG" kategóriája (acel-es-alu-rakoncak-es-szegok csoport)
DG_GROUP = "acel-es-alu-rakoncak-es-szegok"
DG_IMAGES = {
    "BB2": ["2025/06/serie-BB2-1-1024x1024.png", "2025/10/BB2_1°Foto-683x1024.jpg", "2025/10/BB2_2°-Foto-683x1024.jpg"],
    "BB3": ["2025/06/serie-BB3-1-1024x1024.png", "2025/10/BB3_1°-Foto-683x1024.jpg", "2025/10/BB3_2°-Foto-683x1024.jpg"],
    "BB4": ["2025/06/serie-BB4-1-1024x1024.png", "2025/10/BB4_1°-Foto-683x1024.jpg", "2025/10/Screenshot-2025-10-24-at-11.34.14-1024x903.png"],
    "BB5": ["2025/07/serie-BB5-1-1024x1024.png", "2025/10/BB5_1°-Foto-683x1024.jpg", "2025/10/Screenshot-2025-10-24-at-11.34.24-1024x582.png"],
    "BB7": ["2025/07/serie-BB7-1-1024x1024.png", "2025/10/BB7_1°-Foto-683x1024.jpg", "2025/10/BB7_2°-Foto-683x1024.jpg"],
    "BB10": ["2025/07/serie-BB10-1-1024x1024.png", "2025/10/Screenshot-2025-10-24-at-11.34.46-1024x528.png", "2025/10/1-1-1024x1024.png"],
}
# a prospektus (DG_PDF) képrészletei: (lap indexe, téglalap pontban)
DG_CROPS = {
    "lift": (6, (273, 277)),  # itt a beágyazott fotók (xref) kellenek, a háttérben szürke minta van
    "slider": (6, (292, 612, 566, 842)),
    "acc24": (3, (404, 630, 570, 842)),
    "acc105": (4, (200, 704, 560, 842)),
}

LIGHT = "Kisteherautók, könnyű platós felépítmények (max. 3,5 t össztömeg)"
DG_PRODUCTS = [
    # (slug, név, sorozat, specifikáció, leírás, extra kép)
    ("dg-alu-rakonca-acel-karral-90", "Alumínium rakonca acél zárókarral, 90°-os nyitással", "BB2",
     {"Anyag": "eloxált alumínium, acél zárókar", "Nyitási szög": "90°", "Magasság": "310–810 mm", "Tömeg": "0,73–1,42 kg",
      "Kivitel": "első, hátsó jobb/bal; ütközővel vagy anélkül; egy- vagy kétkamrás", "Csap": "vízszintes vagy függőleges", "Felhasználás": LIGHT},
     "Kisteherautók oldalfalzárásának klasszikus, bevált megoldása: az oldalfalba épül, egy ujjal működtethető, a rugós zárócsap nyitáskor erőt ad, záráskor megfogja az oldalfalat. Kiálló részek nélküli, szennyeződés ellen védett csapház. Egyedi hossz és profil kérésre.", None),
    ("dg-alu-oldalfalzar-fuggoleges-acel-karral", "Alumínium oldalfalzár függőleges acél karral", "BB2",
     {"Anyag": "eloxált alumínium, acél kar", "Magasság": "310–610 mm", "Tömeg": "0,76–1,06 kg",
      "Kivitel": "jobb / bal; ütközővel vagy anélkül", "Csap": "vízszintes", "Felhasználás": LIGHT},
     "Függőleges karos alumínium oldalfalzár kisteherautók platójára – egyszerű, biztonságos, korrózióálló.", "acc24"),
    ("dg-alu-rakonca-muanyag-karral-170", "Alumínium rakonca lehajtható műanyag karral és biztonsági kampóval, 170°", "BB3",
     {"Anyag": "eloxált alumínium, PA66 műanyag kar", "Nyitási szög": "170°", "Nyitott helyzetben kiáll": "20 mm", "Magasság": "310–810 mm",
      "Tömeg": "0,5–1,16 kg", "Kivitel": "vízszintes vagy függőleges csap; ütközővel vagy anélkül; egy- vagy kétkamrás",
      "Felhasználás": "max. 3,5 t (kérésre 6 t-ig)"},
     "A legkönnyebb és legkompaktabb alumínium rakonca: a beépített biztonsági kampó és a lehajtható kar megakadályozza a véletlen nyitást, kesztyűben is jól kezelhető. Háromfázisú, sima nyitás–zárás.", None),
    ("dg-alu-oldalfalzar-muanyag-karral", "Alumínium oldalfalzár lehajtható műanyag karral", "BB3",
     {"Anyag": "eloxált alumínium, PA66 műanyag kar", "Magasság": "310–810 mm", "Tömeg": "0,5–1,2 kg",
      "Kivitel": "jobb / bal; vízszintes vagy függőleges csap; ütközővel vagy anélkül", "Felhasználás": LIGHT},
     "Könnyű, biztonsági kampós alumínium oldalfalzár kisteherautók platójára.", "acc24"),
    ("dg-alu-rakonca-lehajthato-acel-karral-170", "Alumínium rakonca lehajtható acél karral, 170°", "BB4",
     {"Anyag": "eloxált alumínium, acél kar", "Nyitási szög": "170°", "Nyitott helyzetben kiáll": "30 mm", "Magasság": "310–810 mm",
      "Tömeg": "0,62–1,34 kg", "Kivitel": "első, hátsó, jobb/bal; ütközővel vagy anélkül; vízszintes vagy függőleges csap", "Felhasználás": LIGHT},
     "A 90°-os acél karos rakonca továbbfejlesztett változata: lehajtható acél kar beépített ütközővel, minimális erővel nyitható és zárható, nagy terhelésnél is stabil.", None),
    ("dg-alu-oldalfalzar-lehajthato-acel-karral", "Alumínium oldalfalzár lehajtható acél karral", "BB4",
     {"Anyag": "eloxált alumínium, acél kar", "Magasság": "310–810 mm", "Tömeg": "0,50–1,17 kg",
      "Kivitel": "jobb / bal; ütközővel vagy anélkül", "Felhasználás": LIGHT},
     "Lehajtható acél karos alumínium oldalfalzár beépített zárónyelvvel kisteherautók platójára.", "acc24"),
    ("dg-acel-rakonca-konnyu-plato", "Acél rakonca platós felépítményekhez (5 t alatt)", "BB5",
     {"Anyag": "acél, KTL (kataforézis) fekete bevonat; kérésre rozsdamentes", "Magasság": "400–800 mm (szabvány 400–600 mm)", "Tömeg": "3,5–6,2 kg",
      "Kivitel": "első, középső, hátsó; 1 vagy 2 karos", "Rögzítés": "csavarozható vagy hegeszthető talp", "Oldalfal": "25 mm",
      "Felhasználás": "fix platók, ponyvás és billenős felépítmények, 5 t alatt"},
     "Kompakt, könnyű acél rakonca a plató oldalára: kétfokozatú oldalfal-kioldás, földről kezelhető, kevés karbantartást igényel. Az összeszerelés után teljes KTL-bevonatot kap. Ponyvás felépítményhez is kapható.", "acc105"),
    ("dg-acel-rakonca-nehez-plato", "Acél rakonca nehéz platós felépítményekhez (5 t felett)", "BB10",
     {"Anyag": "2,5 mm nagyszilárdságú acél, KTL (kataforézis) fekete bevonat; kérésre rozsdamentes", "Magasság": "400–1000 mm",
      "Tömeg": "3,5 kg (első 400 mm) – 12,6 kg (középső 1000 mm)", "Kivitel": "első, középső, hátsó; fix vagy kivehető, 180°-ban elforgatható; két karos",
      "Rögzítés": "csavarozható vagy hegeszthető talp (0,52–0,59 kg)", "Oldalfal": "25 mm", "Felhasználás": "fix platók 5 t felett"},
     "Átlagosan 20%-kal könnyebb a hagyományos acél rakoncáknál, teljesítménybeli kompromisszum nélkül. Kivehető vagy 180°-ban elforgatható – teljesen szabad rakfelület. A zárószerkezet a rakoncába integrált, kétfokozatú kioldással.", "acc105"),
    ("dg-ponyvas-oszlop-kozepso", "Elhúzható középső oszlop ponyvás félpótkocsihoz", "BB7",
     {"Anyag": "2,5 mm nagyszilárdságú acél vagy 2 mm S700MC (tömegoptimalizált)", "Felület": "KTL (kataforézis) fekete; alumíniumból is",
      "Magasság": "2400 mm-től (szabvány 2800–3000 mm)", "Tömeg": "21,5–23,8 kg", "Kivitel": "1 vagy 2 karos; francia vagy oldalsó bordához (H600/800/1000)",
      "Kocsi": "csuklós vagy fix, rugós vagy gumis biztosítással"},
     "Curtainsider (ponyvás) félpótkocsik középső oszlopa könnyű oldalirányú mozgatással: a csuklós, beépített kampós rendszer egy kézzel, a földről is kioldható. Moduláris kialakítás, csavarozható vagy hegeszthető zsebekkel.", None),
    ("dg-ponyvas-oszlop-elso-hatso", "Első és hátsó oszlop ponyvás félpótkocsihoz", "BB7",
     {"Anyag": "nagyszilárdságú acél", "Felület": "KTL (kataforézis) fekete; alumíniumból is", "Magasság": "2400 mm-től",
      "Kivitel": "egyedi formákkal, fix vagy teleszkópos tetővel"},
     "Első és hátsó oszlopok curtainsider félpótkocsikhoz, a középső oszlopokkal egységes rendszerben.", None),
    ("dg-rugos-oszlopemelo-gazrugoval", "Rugós oszlopemelő gázrugóval ponyvás oszlophoz", None,
     {"Kivitel": "kézi mechanikus emelő gázrugóval", "Gázrugó": "900 N vagy 1300 N", "Felület": "KTL (kataforézis) fekete", "Magasság": "2400 mm-től"},
     "Mechanikus oszlopemelő gázrugóval a ponyvás félpótkocsik középső oszlopához – megkönnyíti az oszlop kiemelését és áthelyezését.", "lift"),
    ("dg-rugos-csuszka-kozepso-oszlophoz", "Rugós csúszka ponyvás középső oszlophoz", None,
     {"Kivitel": "komplett, szegecselhető készlet", "Felület": "horganyzott"},
     "Rugós csúszókocsi curtainsider középső oszlophoz: az oszlop gyors, könnyű oldalirányú mozgatására.", "slider"),
]
# Excel DG termékek: a Quadris / DG kódból a sorozat
DG_EXCEL_SERIES = [(r"^12-", "BB10"), (r"^06-", "BB5"), (r"^30-05", "BB10")]


def dg_fetch(url):
    """Letöltés a captcha-védett DG oldalról: csak valódi választ fogad el és gyorsítótáraz."""
    import time
    import urllib.request
    from urllib.parse import quote
    from common import CACHE, UA
    key = CACHE / re.sub(r"[^A-Za-z0-9._-]+", "_", url)[-180:]
    if key.exists():
        return key.read_bytes()
    for attempt in range(8):
        req = urllib.request.Request(quote(url, safe=":/%"), headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data, status = r.read(), r.status
        except Exception:  # noqa: BLE001
            data, status = b"", 0
        if status == 200 and len(data) > 2000 and b"sgcaptcha" not in data[:3000]:
            key.parent.mkdir(parents=True, exist_ok=True)
            key.write_bytes(data)
            return data
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"nem sikerült letölteni: {url}")


def dg_images(slug, series, crop):
    import pymupdf
    clear_images(slug)
    out = []
    for rel in DG_IMAGES.get(series, [])[:3 if not crop else 2]:
        try:
            out.append(save_image(dg_fetch(DG_UP + rel), slug, len(out) + 1))
        except Exception as err:  # noqa: BLE001
            print("  képhiba:", rel, err)
    if crop:
        import io
        from PIL import Image
        pno, rect = DG_CROPS[crop]
        doc = pymupdf.open(stream=dg_fetch(DG_PDF), filetype="pdf")
        if len(rect) == 2:  # beágyazott képek egymás mellé, fehér háttérre
            parts = [Image.open(io.BytesIO(doc.extract_image(x)["image"])).convert("RGB") for x in rect]
            h = max(i.height for i in parts)
            img = Image.new("RGB", (sum(i.width for i in parts) + 80 * (len(parts) + 1), h + 80), "white")
            x = 80
            for i in parts:
                img.paste(i, (x, 40))
                x += i.width + 80
        else:
            pix = doc[pno].get_pixmap(dpi=220, clip=pymupdf.Rect(*rect))
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        out.append(save_image(img, slug, len(out) + 1))
    return out


def dg():
    products = []
    for slug, name, series, specs, desc, crop in DG_PRODUCTS:
        products.append({"slug": slug, "code": "", "name": name, "group": DG_GROUP, "category": DG_CAT, "specs": specs,
                         "description": desc, "images": dg_images(slug, series, crop),
                         "sourceUrl": f"https://en.dg-ts.it/serie-{series.lower()}/" if series else DG_PDF})
    # az Excel DG termékeinek képe és leírása a sorozat alapján (termekadatok.json)
    from common import update_enrichment
    by_series = {p["slug"]: p for p in products}
    enrichment = {}
    for p in excel_products():
        if p["supplier"] != "DG":
            continue
        code = (p["supplierCode"] or "").strip()
        series = next((s for rx, s in DG_EXCEL_SERIES if re.match(rx, code)), "BB10")
        base = by_series["dg-acel-rakonca-konnyu-plato" if series == "BB5" else "dg-acel-rakonca-nehez-plato"]
        is_counter = code.startswith("30-")
        imgs = dg_images(p["slug"], series, "acc105" if is_counter else None)
        if is_counter:
            imgs = imgs[-1:] + imgs[:-1]
        size = re.search(r"(\d{3,4})\s*mm|DG\s*(\d{3,4})\b|KDG\s*(\d{3})", p["name"])
        specs = {k: v for k, v in base["specs"].items() if k in ("Anyag", "Rögzítés", "Oldalfal")}
        if size:
            specs["Magasság"] = f"{next(g for g in size.groups() if g)} mm"
        enrichment[p["slug"]] = {"source": "DG", "sourceUrl": base["sourceUrl"], "sourceTitle": series, "matchedCode": code,
                                 "description": ("Rakonca ellendarab / rögzítő zseb a plató oldalára, a rakoncához illesztve." if is_counter
                                                 else base["description"]),
                                 "specs": specs, "images": imgs}
    update_enrichment(enrichment, "DG")
    print(f"  DG Excel-termékek kiegészítve: {len(enrichment)}")
    return {"products": products}


RUNNERS = {"fuhrmann": ("Fuhrmann", fuhrmann), "rubberselect": ("Rubber Select", rubberselect), "gnc": ("G&C termékek", gnc), "sandprofile": ("Sand-Profile", sandprofile_full), "dg": ("DG", dg)}


def main(names):
    data = load()
    for name in names or RUNNERS:
        supplier, fn = RUNNERS[name]
        res = fn()
        replace_supplier(data, supplier, res.get("groups", ()), res.get("categories", ()), res.get("products", ()),
                         res.get("moves"), res.get("rename"))
        print(f"{supplier}: {len(res.get('products', []))} termék, {len(res.get('moves') or {})} áthelyezés")
    save(data)


if __name__ == "__main__":
    main(sys.argv[1:])
