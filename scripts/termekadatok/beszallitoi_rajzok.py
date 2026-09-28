"""E-mailben kapott beszállítói rajzok és képek feldolgozása (data/forras/beszallitoi_rajzok/).

- D. La Porte: méretezett gyári rajzok (PDF) – a 3D nézet és a méretezett nézetek kivágva,
  a szövegmező, a szerzői jogi szöveg és a gyári cikkszámok kitakarva. A PDF-ek „bizalmas”
  jelöléssel érkeztek, ezért nincsenek a git tárolóban (.gitignore); ha hiányoznak, a korábban
  előállított bejegyzések megmaradnak.
- Cargo Frames: U-típusú padlókeret-profilok keresztmetszete, méretezett rajza és a lyukasztás
  nézete, tömeg a beszállítói árlistából (kg/m, kg/db); csavarozott acél segédkeret KIT fotó
  (új termék a bovitett.json-ban, a csoport elején).
- Industrilas: 68-S1 T-karos süllyesztett zár fotója.

Használat: python3 scripts/termekadatok/beszallitoi_rajzok.py
"""

import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, save_enrichment, save_image  # noqa: E402

SOURCE = "Beszállítói rajz"
SRC = ROOT / "data/forras/beszallitoi_rajzok"


def page_image(pdf, width):
    """A PDF első oldala a `width` px széles nézet kétszeresére renderelve; visszaadja a képet és a szorzót."""
    page = pymupdf.open(pdf)[0]
    zoom = 2 * width / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples), 2


def crop(pdf, width, box, blank=()):
    """Kivágás `width` px széles nézet koordinátáiban; a `blank` téglalapok fehérre törölve."""
    img, k = page_image(pdf, width)
    d = ImageDraw.Draw(img)
    for x0, y0, x1, y1 in blank:
        d.rectangle([x0 * k, y0 * k, x1 * k, y1 * k], fill="white")
    x0, y0, x1, y1 = box
    return img.crop((x0 * k, y0 * k, x1 * k, y1 * k))


# ------------------------------------------------------------------ D. La Porte

DLP = SRC / "dlp"
LOCK_61_5101 = {
    "pdf": "61.5101.0003.pdf", "w": 2000,
    "images": [
        ((320, 870, 1520, 1375), [(1040, 955, 1170, 1020), (705, 1200, 840, 1270), (1280, 860, 1530, 1005)]),   # 3D, cikkszám-feliratok nélkül
        ((40, 170, 1540, 1060), [(600, 880, 1540, 1060), (320, 990, 600, 1060), (1475, 205, 1540, 290), (1475, 655, 1540, 695)]),                              # felül- és oldalnézet
        ((1555, 90, 1975, 530), [(1722, 370, 1752, 418), (1555, 200, 1600, 300)]),                                                    # zártest oldalnézet
    ],
    "specs": {
        "Traverz (kar) hossza": "500 mm",
        "Kar rögzítése": "fokozatmentesen állítható szögben",
        "Zártest magassága": "84 mm",
        "Kioldási löket": "7,5 mm",
        "Rögzítés": "M8 süllyesztett fejű csavar (ISO 10642)",
        "Biztosítás": "igen, reteszelő karral",
        "Felület": "Cr(VI)-mentes bevonat",
        "Tartozék": "bal és jobb takarósapka tolókával",
    },
}
DLP_PRODUCTS = {
    "615003-belsozarszerk-oldalajtohoz-500-mm-kar-b": {
        **LOCK_61_5101,
        "description": "Forgócsapdás (Drehfallen-) oldalajtózár belső, 500 mm-es kilincskarral és biztosítással, bal oldali kivitel. "
                       "Dobozos felépítmények és fülkék oldalajtóihoz.",
        "specs": {**LOCK_61_5101["specs"], "Kivitel": "bal"},
    },
    "615104-oldalajtozar-belso-500-mm-kar-jobb": {
        **LOCK_61_5101,
        "description": "Forgócsapdás (Drehfallen-) oldalajtózár belső, 500 mm-es kilincskarral és biztosítással, jobb oldali kivitel "
                       "(a bal oldali tükörképe). Dobozos felépítmények és fülkék oldalajtóihoz.",
        "specs": {**LOCK_61_5101["specs"], "Kivitel": "jobb (a rajz a bal oldalit mutatja)"},
    },
    "614602-j-oldalajto-zarszerkezet": {
        "pdf": "61.4600.0002.pdf", "w": 2000,
        "images": [
            ((1580, 170, 1965, 960), [(1580, 580, 1730, 640)]),                         # 3D nézetek
            ((170, 265, 1505, 1185), []),                                               # méretezett nézetek
        ],
        "description": "Kabinzár (forgócsapdás oldalajtózár) biztosítással és erősítőlemezzel, jobb oldali kivitel. "
                       "Dobozos felépítmények, fülkék és szerszámosládák ajtóihoz.",
        "specs": {
            "Kivitel": "jobb, biztosítással, erősítőlemezzel",
            "Méret (sz × m)": "65,4 × 74 mm",
            "Zártest szélessége": "45 mm",
            "Zárcsap átmérő": "Ø10 mm",
            "Erősítőlemez vastagsága": "2,5 mm",
            "Nyitási szög": "90°",
            "Felület": "Cr(VI)-mentes bevonat",
            "Tömeg": "0,53 kg",
        },
    },
    "615102-kulso-oldalajto-kilincs": {
        "pdf": "53.4560.0004.pdf", "w": 1654,
        "images": [((90, 80, 1480, 960), [(1125, 650, 1480, 960)])],
        "description": "Nyomógombos külső fogantyú zárhengerrel oldalajtókhoz; a nyomógomb a belső zárat oldja. 2 kulccsal szállítjuk.",
        "specs": {
            "Hossz": "180 mm",
            "Szélesség": "36 mm",
            "Magasság": "34 mm",
            "Furattávolság": "120 mm",
            "Rögzítés": "2 db M6×12 menetes persely (max. 10 Nm)",
            "Kioldási löket": "13,5 mm",
            "Zárhenger": "igen, 180°-os zárási mozgás, 2 kulccsal",
            "Felület": "Cr(VI)-mentes",
        },
    },
    "615000-zarcsap": {
        "pdf": "05.0007.2122.pdf", "w": 827,
        "images": [((110, 140, 745, 560), [])],
        "description": "Zárcsap a forgócsapdás oldalajtózárakhoz, M12×1 menetes ellenlappal.",
        "specs": {
            "Menetes ellenlap": "M12×1",
            "Ellenlap mérete": "39 × 31 × 8 mm",
            "Ellenlap anyaga": "St37-2 (DIN 174) acél",
            "Felület": "horganyzott",
        },
    },
}

# ------------------------------------------------------------------ Cargo Frames

CF = SRC / "cargoframes"
CF_DESC = ("Hidegen hengerelt acél padlókeret-profil (U típus) teherautó- és pótkocsi-felépítmények alvázkeretéhez. "
           "A felső horony a süllyesztett kikötőfülek fogadására szolgál, a padló rétegelt lemeze a lépcsőre fekszik fel.")
# slug: (magasság, lépcső, vastagság, hossz, kg/m, kg/db, lyukasztás)
CF_U = {
    "141520-pu00-acel-keret-110-15-2-5000": (110, 15, 2, 5000, "3,67", "18,4", None),
    "141520-perf-pu00-acel-keret-110-15-2-5100": (110, 15, 2, 5100, "3,67", "18,7", "dupla furat kikötőfülhöz 300 mm-enként"),
    "141521-pu00-acel-keret-115-21-3-mm": (115, 21, 3, 7500, "5,63", "42,2", None),
    "141527-pu00-acel-keret-115-27-3-7500": (115, 27, 3, 7500, "5,77", "43,3", None),
    "142130-pu00-acel-keret-140-21-3-7500": (140, 21, 3, 7500, "6,22", "46,7", None),
    "142430-pu00-acel-keret-140-24-3-7500": (140, 24, 3, 7500, "6,29", "47,2", None),
    "142730-pu00-acel-keret-140-27-3-7500": (140, 27, 3, 7500, "6,36", "47,7", None),
    "142730-pu00-acel-keret-140-27-3-8000": (140, 27, 3, 8000, "6,36", "50,9", None),
}
KIT = {
    "slug": "csavarozott-acel-segedkeret-kit", "code": "", "name": "Csavarozott acél segédkeret KIT",
    "group": "acel-profilok", "category": "acel-keret", "first": True,
    "description": "Horganyzott, csavarozott acél segédkeret (alvázkeret) készlet teherautó-felépítményekhez: U-típusú "
                   "padlókeret-profilok, hossz- és kereszttartók, konzolok. Hegesztés nélkül szerelhető, a felépítmény "
                   "méretére összeállítva.",
    "specs": {"Anyag": "S355MC acél", "Felület": "horganyzott", "Kivitel": "csavarozott, hegesztés nélkül",
              "Elemek": "padlókeret-profilok, hossz- és kereszttartók, konzolok", "Méret": "egyedi, a felépítmény szerint"},
}

INDUSTRILAS = {
    "615363-68-s1-t-karos-sully-zar": "68-S1 T-karos süllyesztett zár, zárhengerrel.",
    "615263-68-s1-t-karos-sully-zar-f": "68-S1 T-karos süllyesztett zár, zárhengerrel.",
}


def entry(slug, images, specs, description, title):
    return {"source": SOURCE, "sourceUrl": "", "sourceTitle": title, "matchedCode": "",
            "description": description, "specs": specs, "images": images}


def main():
    data = load_enrichment()
    updates = {}

    for slug, cfg in DLP_PRODUCTS.items():
        pdf = DLP / cfg["pdf"]
        if not pdf.exists():
            print(f"  hiányzik: {pdf.name} – {slug} marad a korábbi")
            continue
        clear_images(slug)
        imgs = [save_image(crop(pdf, cfg["w"], box, blank), slug, i) for i, (box, blank) in enumerate(cfg["images"], 1)]
        updates[slug] = entry(slug, imgs, cfg["specs"], cfg["description"], cfg["pdf"])

    u3 = crop(CF / "profil_U_3mm.pdf", 827, (60, 45, 783, 840))
    u2 = crop(CF / "profil_U_2mm.pdf", 827, (150, 110, 700, 800))
    holes = crop(CF / "profil_U_dupla_furat.pdf", 827, (46, 50, 783, 845))
    silhouette = Image.open(CF / "U140_27.png")
    for slug, (h, step, t, length, kgm, kgdb, perf) in CF_U.items():
        clear_images(slug)
        imgs = [save_image(silhouette, slug, 1), save_image(u2 if t == 2 else u3, slug, 2)]
        if perf:
            imgs.append(save_image(holes, slug, 3))
        specs = {"Profil típus": "U", "Magasság": f"{h} mm", "Padlólemez-lépcső": f"{step} mm", "Lemezvastagság": f"{t} mm",
                 "Szélesség": "74 mm", "Hossz": f"{length} mm", "Tömeg": f"{kgm} kg/m ({kgdb} kg/db)",
                 "Lyukasztás": perf or "nincs", "Anyag": "S355MC acél", "Tűrés": "EN 10162"}
        updates[slug] = entry(slug, imgs, specs, CF_DESC, "Cargo Frames U profil")

    slug = "142730-pf50-acel-keret-140-27-3-2500-sima"
    clear_images(slug)
    updates[slug] = entry(slug, [save_image(Image.open(CF / "F140_27.png"), slug, 1)],
                          {"Profil típus": "F (sima felső rész, horony nélkül)", "Magasság": "140 mm", "Padlólemez-lépcső": "27 mm",
                           "Lemezvastagság": "3 mm", "Hossz": "2500 mm", "Anyag": "S355MC acél"},
                          "Hidegen hengerelt acél padlókeret-profil sima felső résszel (hegesztett kikötőfülekhez vagy a "
                          "felépítmény homlok- és hátsó keretéhez).", "Cargo Frames F profil")

    for slug, desc in INDUSTRILAS.items():
        clear_images(slug)
        updates[slug] = entry(slug, [save_image(Image.open(SRC / "industrilas/68-S1.png"), slug, 1)],
                              {"Működtetés": "T-kar", "Beépítés": "süllyesztett", "Zárhenger": "igen", "Ház": "fekete"},
                              desc, "Industrilas 68-S1")

    # korábbi, most nem előállított bejegyzések törlése (a hiányzó forrású DLP termékek maradnak)
    keep = {s for s in DLP_PRODUCTS if not (DLP / DLP_PRODUCTS[s]["pdf"]).exists()}
    for s in [s for s, e in data.items() if e.get("source") == SOURCE and s not in updates and s not in keep]:
        del data[s]
    data.update(updates)
    save_enrichment(data)
    print(f"  {len(updates)} termék kiegészítve")

    # KIT: új termék a bővített kínálatban
    from teljes_kinalat import load, replace_supplier, save
    clear_images(KIT["slug"])
    kit = {**KIT, "images": [save_image(Image.open(CF / "segedkeret_kit.jpg"), KIT["slug"], 1)]}
    ext = load()
    replace_supplier(ext, SOURCE, products=[kit])
    save(ext)
    print("  KIT termék felvéve")


if __name__ == "__main__":
    main()
