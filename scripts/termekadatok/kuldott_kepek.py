"""A Quadris által küldött katalóguslap-képekből (képernyőképek) kivágott termékképek és adatok – azokhoz a
termékekhez, amelyeknek a forrás-katalógusa nincs meg nálunk. A kivágás kézzel rögzített (képpontban).

  e-ponyvagorgo-85810 = Claro RTE-003 ponyvagörgő (Claro catalogue 2019, 131. o.) – data/forras/claro_rte003_lap.png
    (az Edscha Compact-os párosítást – edscha_compact.py – a Quadris kérésére ez váltja)

  E/COMPACT tetőprofil 900407 (mind az öt hossz) – az Edscha Compact sín méretezett rajza (43 × 112 mm) első képként,
    a meglévő (edscha_compact.py) képek elé: data/forras/edscha_compact_sin.png (a küldött lapkép kivágva,
    4× nagyítva, a szürke háttér fehérre cserélve; az eredeti: edscha_compact_sin_lap.png)
  E/Small tetőprofil 900931 (mind a három hossz) és E/VOLUMEN tetőprofil 900301 (mind a hat hossz) – a Volumen sín („Alu-Träger”) méretezett rajza első képként:
    data/forras/edscha_volumen_sin.png (a küldött 900301-es lap bal oldali rajza, 3× nagyítva; eredeti: …_lap.png)

  E69004740 CS-Compact és E69004670 Compact FIX tetőkereszttartó – a küldött termékfotó második képként
    (edscha_cs_compact_tetokereszttarto.png, edscha_compact_fix_tetokereszttarto.png)

Használat: python3 scripts/termekadatok/kuldott_kepek.py
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, clear_images, load_enrichment, load_products, save_image, update_enrichment  # noqa: E402

SOURCE = "Quadris katalóguslap"
# slug -> (lapkép, [kivágások (x0, y0, x1, y1)], forrás megnevezése, gyártói cikkszám, adatok)
ITEMS = {
    "e-ponyvagorgo-85810": (
        "data/forras/claro_rte003_lap.png", [(115, 190, 470, 468), (640, 445, 1205, 818)],
        "Claro catalogue 2019, 131. oldal – RTE-003", "RTE-003",
        {"Gyártó": "Claro", "Kivitel": "kétgörgős ponyvagörgő, hosszlyukas rögzítőlappal",
         "Méret": "75 × 52 mm", "Görgőátmérő": "31,5 mm", "Teljes vastagság": "17 mm", "Lapvastagság": "5 mm",
         "Hosszlyuk": "52 × 8 mm", "Tömeg": "176 g/db", "Kiszerelés": "110 db/karton", "Minősítés": "DEKRA approved"}),
}


# a meglévő képek elé kerülő rajzok: slug -> ([(kép, képnév-utótag), …], adatok)
COMPACT = [f"e-compact-tetoprofil-900407-{n}" for n in (5000, 5600, 6600, 7800, 8000)]
PREPEND = {slug: ([("data/forras/edscha_compact_sin.png", "meretrajz")],
                  {"Profilméret": "43 × 112 mm (alul 33 mm)", "Tömeg": "2,88 kg/m", "Ix": "112,5 cm⁴", "Iy": "13,3 cm⁴"})
           for slug in COMPACT}
VOLUMEN = [f"e-volumen-tetoprofil-900301-{n}" for n in (7800, 8500, 9000, 9400, 9600, 10000)]
# (a tetőszerkezetes rajz a lap jobb oldaláról, a súly/inercia kerete nélkül: edscha_volumen_tetoszerkezet.png)
PREPEND.update({slug: ([("data/forras/edscha_volumen_sin.png", "meretrajz"),
                        ("data/forras/edscha_volumen_tetoszerkezet.png", "tetoszerkezet")],
                       {"Profilméret": "120 × 163 mm (alul 35 mm)", "Tömeg": "5,65 kg/m", "Ix": "595,0 cm⁴", "Iy": "207,2 cm⁴"})
                for slug in VOLUMEN})
# E/Small tetőprofil (Edscha 900931) – a küldött lapról: profilrajz + tetőszerkezet (edscha_small_*.png)
SMALL = [f"e-small-tetoprofil-{n}-mm" for n in (6600, 7800, 8200)]
PREPEND.update({slug: ([("data/forras/edscha_small_sin.png", "meretrajz"),
                        ("data/forras/edscha_small_tetoszerkezet.png", "tetoszerkezet")],
                       {"Profilméret": "58,5 × 95 mm (alul 44,4 mm)", "Tömeg": "3 kg/m", "Ix": "82,7 cm⁴", "Iy": "33,9 cm⁴",
                        "Rajzszám (gyári)": "900931"})
                for slug in SMALL})


# a meglévő képek közé adott helyre beszúrt képek: slug -> [(kép, képnév-utótag, hely (0 = első))]
INSERT = {"e69004740-cs-compact-tetokereszttarto-2550-mm": [("data/forras/edscha_cs_compact_tetokereszttarto.png", "foto", 1)],
          "e69004670-compact-fix-tetokereszttarto-2550-mm": [("data/forras/edscha_compact_fix_tetokereszttarto.png", "foto", 1)],
          # TailWing: a katalógusoldal két fotója a zöld felirattal, a német sor nélkül (edscha_tailwing.png)
          "e-tailwing-1200-mm": [("data/forras/edscha_tailwing.png", "foto", 1)],
          "e-tailwing-400-900-mm": [("data/forras/edscha_tailwing.png", "foto", 1)],
          # a Compact CS tolótető áttekintő rajza a fő alkatrészekkel (a meglévő fotók után)
          "e-compact-cs-toloteto-rendszer": [("data/forras/edscha_compact_cs_attekinto.png", "attekinto", 99)],
          "e-compact-fix-teto-rendszer": [("data/forras/edscha_compact_fix_attekinto.png", "attekinto", 99)],
          "e422552-tetokereszttarto-2550-mm": [("data/forras/edscha_tetokereszttarto_422552.png", "foto", 1)],
          # a 130-as és a 190-es lezáró ugyanazt a fotót kapja (a kék keret nélkül)
          "e69000690-130-as-lezaro-2550-mm": [("data/forras/edscha_lezaro_2550.png", "foto", 1)],
          "e69001370-190-es-lezaro-2550-mm": [("data/forras/edscha_lezaro_2550.png", "foto", 1)],
          # Versus Omega MICRO TRIKE: az alkatrész-áttekintő rajz első képként (a PDF-néző kiemelése, fejléc és
          # oldalszám nélkül; eredeti: versus_micro_trike_lap.png)
          "versus-micro-trike-toloteto-rendszer": [("data/forras/versus_micro_trike.png", "attekinto", 0)],
          "versus-duo-trike-l-toloteto-rendszer": [("data/forras/versus_duo_trike_light.png", "attekinto", 0)],
          "e38067930-compact-csuklopant-650-mm": [("data/forras/edscha_csuklopant_650_1.png", "foto1", 1),
                                                  ("data/forras/edscha_csuklopant_650_2.png", "foto2", 2)],
          "e42587-csuklopant-700-mm": [("data/forras/edscha_csuklopant_700_1.png", "foto1", 1),
                                       ("data/forras/edscha_csuklopant_700_2.png", "foto2", 2)]}
# 222139 és 222139/n („h” szegő 25 mm): a Quadris által küldött katalógusrajz (a gyártói kód nélkül kivágva)
PREPEND.update({slug: ([("data/forras/h_szego_2139_rajz.png", "meretrajz")],
                       {"Magasság": "60 mm", "Szélesség": "25,5 mm", "Tömeg": "0,923 kg/m"})
                for slug in ("222139-h-szego-25-mm-elox", "222139-n-h-szego-25-mm")})
# 222020 „h” szegő kiugrós 25 mm elox (ESAL 50020): a Sponde 2020 katalógus 59. oldaláról a fotó és a méretezett
# rajz (33 × 61 mm) a meglévő képek elé
INSERT["222020-h-szego-kiugros-25-mm-elox"] = [("data/forras/esal_50020_foto.png", "foto", 0),
                                               ("data/forras/esal_50020_rajz.png", "meretrajz", 1)]
# 222137 és 222137/n („u” szegő 25 mm, Allco VZ2137SP): a Quadris által küldött katalógusrajz (a gyártói kód nélkül)
PREPEND.update({slug: ([("data/forras/u_szego_2137_rajz.png", "meretrajz")],
                       {"Magasság": "40 mm", "Szélesség": "25,5 mm", "Tömeg": "0,788 kg/m"})
                for slug in ("222137-u-25-mm-szego-profil-elox", "222137-n-u-25-mm-szego-profil")})
# 221746 H toldó – szegő profil elox (Car-Alu 1011414): a Quadris által küldött katalógusrajz (a cikkszámok nélkül)
PREPEND["221746-h-toldo-szego-profil-elox"] = ([("data/forras/caralu_1011414_rajz.png", "meretrajz")],
                                               {"Szélesség": "77,8 mm", "Magasság": "25,5 mm", "Tömeg": "1,2 kg/m"})
# 223085 „h” szegő kiugrós 30 mm elox (Fudicar 30907): a Quadris által küldött katalógusrajz (a cikkszám nélkül)
PREPEND["223085-h-szego-kiugros-30-mm-elox"] = ([("data/forras/fudicar_30907_rajz.png", "meretrajz")],
                                                {"Falvastagság": "3 mm", "Tömeg": "0,97 kg/m"})
# 226215 „u” 40 mm szegő profil (Fudicar 40215): a Quadris által küldött katalógusrajz (a cikkszám és a felirat nélkül)
PREPEND["226215-u-40-mm-szego-profil"] = ([("data/forras/fudicar_40215_rajz.png", "meretrajz")],
                                          {"Szélesség": "50 mm", "Magasság": "50,5 mm", "Belső nyílás": "40,5 mm",
                                           "Tömeg": "2,53 kg/m"})
# 226240 tömítéses „u” szegő 40 mm (Fudicar 40738): a Quadris által küldött katalógusrajz (a cikkszám nélkül)
PREPEND["226240-tomiteses-u-szego-40-mm"] = ([("data/forras/fudicar_40738_rajz.png", "meretrajz")],
                                             {"Szélesség": "85 mm", "Belső nyílás": "40,5 mm", "Tömeg": "2,71 kg/m"})
# 226701 tömítés 40 „u” szegőhöz (Fudicar 63738): a Quadris által küldött katalógusrajz (a felirat nélkül), a szegőben
PREPEND["226701-tomites-40-u-szegohoz"] = ([("data/forras/fudicar_63738_tomites.png", "rajz")], {})
# 245005 Bill. 400/30 mm mono profil elox (Takler T1 5005): a Quadris által küldött katalóguslap fotója és méretrajza
PREPEND["245005-bill-400-30-mm-mono-profil-elox"] = ([("data/forras/takler_t15005_foto.png", "foto"),
                                                     ("data/forras/takler_t15005_rajz.png", "meretrajz")],
                                                    {"Magasság": "400 mm", "Vastagság": "30 mm", "Ötvözet": "EN AW-6060",
                                                     "Tömeg": "5,513 kg/m"})
# 245085 Bill. „u” szegő 30 mm (40/60) elox: a RE-ALL katalógus méretezett rajza első képként (a táblázat nélkül)
INSERT["245085-bill-u-szego-30-mm-40-60-elox"] = [("data/forras/reall_245085_rajz.png", "meretrajz", 0)]
# 729629 / 729630 húspálya C-sín: a Quadris által küldött katalógusrajz (a gyártói cikkszám nélkül) első képként
for _slug in ("729629-huspalya-c-sin-elox-6000-mm", "729630-huspalya-c-sin-elox-7000-mm"):
    INSERT[_slug] = [("data/forras/huspalya_8543_rajz.png", "meretrajz", 0)]
# 222005 Spitz profil 150 mm magas T (Allco VZ2180UN): a Quadris által küldött katalógusrajz (a gyártói kód nélkül)
PREPEND["222005-spitz-profil-150-mm-magas-t"] = ([("data/forras/allco_2180_rajz.png", "meretrajz")],
                                                 {"Magasság": "150 mm", "Szélesség": "25 mm", "Tömeg": "1,547 kg/m"})
# 223032 Spitz profil 100 mm (Bodega 53032): a Quadris által küldött szkennelt gyári rajz alapján újrarajzolva –
# csak a profil (1,4 mm fal) és a befoglaló méretek (110 × 25); a többi méret- és segédvonal nélkül
PREPEND["223032-spitz-profil-100-mm"] = ([("data/forras/bodega_53032_rajz.png", "meretrajz")],
                                         {"Szélesség": "110 mm", "Magasság": "25 mm", "Falvastagság": "1,4 mm",
                                          "Tömeg": "1,028 kg/m", "Ötvözet": "EN AW-6060 T66"})
# 226915 és 226915/n (30 mm U szegő): a Quadris kérésére csak az Alu-SV 6600006915 rajza (a korábbi RE-ALL /
# Constellium-rajzok a kezi_kepsorrend.json „kizart” listáján)
INSERT.update({slug: [("data/forras/alusv_6600006915_rajz.png", "alusv", 0)]
               for slug in ("226915-30-mm-szego-profil-elox", "226915-n-30-mm-u-szego-profil")})
# a normál (peremes és nem peremes) Z-zárak utolsó képe: a jobb (R) és bal (L) zárak helye a platón – a Quadris
# által küldött vázlat feljavítva (nagyítva, tisztított vonalak, kiemelt oszlopok, R/L jelvény; eredeti: …_eredeti.png)
INSERT.update({slug: [("data/forras/z_zar_beepites_rl.png", "beepites", 99)] for slug in (
    "354400-nem-peremes-400-z-zar-r-l", "354500-nem-peremes-500-mm-z-zar-r-l", "354600-nem-peremes-600-mm-z-zar-r-l",
    "354800-nem-peremes-800-mm-z-zar-r-l", "357400-peremes-z-zar-400-mm-r-l", "357500-peremes-z-zar-500-mm-r-l",
    "357401-peremes-z-zar-600-mm-r-l")})


def main():
    enrichment = {}
    for p in load_products():
        if p["slug"] not in ITEMS:
            continue
        src, boxes, title, code, specs = ITEMS[p["slug"]]
        clear_images(p["slug"])
        im = Image.open(ROOT / src).convert("RGB")
        images = [save_image(im.crop(b), p["slug"], i) for i, b in enumerate(boxes, 1)]
        enrichment[p["slug"]] = {"source": SOURCE, "sourceTitle": title, "matchedCode": code,
                                 "specs": {"Cikkszám (gyártói)": code, **specs}, "images": images}
    old = load_enrichment()
    for slug, (drawings, specs) in PREPEND.items():
        prev = old.get(slug, {})
        front = [save_image(Image.open(ROOT / src).convert("RGB"), slug, suffix) for src, suffix in drawings]
        rest = [u for u in prev.get("images", []) if u not in front]
        enrichment[slug] = {**prev, "source": SOURCE, "specs": {**prev.get("specs", {}), **specs}, "images": front + rest}
    for slug, items in INSERT.items():
        prev = enrichment.get(slug) or old.get(slug, {})
        images = list(prev.get("images", []))
        for src, suffix, pos in items:
            url = save_image(Image.open(ROOT / src).convert("RGB"), slug, suffix)
            images = [u for u in images if u != url]
            images.insert(min(pos, len(images)), url)
        enrichment[slug] = {**prev, "source": SOURCE, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
