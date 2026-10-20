"""Hátsó ajtó alu elox (2 és 4 szárnyú) a Quadris kérésére: a gyártó honlapjának (.cache/procar, belső forrás)
diavetítés-képei „videószerűen” – a gyártó neve a weboldalon sehol nem jelenik meg (a leírásban, a fájlnevekben
sem; a gyártói dokumentumok nem kerülnek fel).

- a diavetítés 3 sávja fotókra bontva: az 1–2. sáv fotói és a 3. sáv első fotója a 2 szárnyú, a 3. sáv többi fotója
  a 4 szárnyú ajtót mutatja; mindkét
  termék csak a saját fotóiból kap áttűnéses, folyamatosan ismétlődő, hang nélküli WebM videót (a fő kép helyén)
- kártyakép: a 2 szárnyúnál a hátulnézet (1. sáv, 1. fotó), a 4 szárnyúnál a 4 lamellás hátulnézet (3. sáv, 3. fotó)
- magyar leírás és műszaki adatok

Használat: python3 scripts/termekadatok/hatso_ajto.py
"""

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, fetch, load_enrichment, save_image, update_enrichment  # noqa: E402

SLUG = "hatso-ajto-alu-elox"
SLUG4 = "hatso-ajto-alu-elox-4-szarnyu"  # kézzel felvett termék (data/kezi_termekek.json)
BASE = "https://www.procaritalia.eu/procar/"  # csak letöltéshez; a weboldalon nem jelenik meg
SLIDES = ["images/Aries.jpg", "images/Aries_1.jpg", "images/Aries_2.jpg"]
# a diavetítés képei 2–5 fotóból összeállított sávok: a videó fotónként mutatja őket (4:3, elmosott háttérrel)
PANELS = [[0, 552, 1105, 1650], [0, 572, 1245, 1650], [0, 375, 745, 1053, 1382, 1650]]
W, H = 960, 720
FPS, HOLD, FADE = 25, 2.5, 1.0

DESCRIPTION = (
    "Alumínium hátsóajtó-rendszer haszonjárművek felépítményeihez. Az ajtólap 7 önhordó, eloxált "
    "alumínium lamellából áll, amelyeket szerkezeti ragasztó köt össze; a lamellák a felső és alsó homloklemezhez "
    "nagy szilárdságú horganyzott acél szegecsekkel kapcsolódnak. A kerület menti keret elhagyásával kisebb tömeg "
    "mellett nagyobb merevséget és igényes megjelenést ad. Az ajtó a DEKRA által kiadott DIN EN 12642 Code XL "
    "rakományrögzítési tanúsítvánnyal rendelkezik. A zárórúd a panelbe süllyesztve, kívülről nem látható; a zsanérok "
    "az ajtóval egy síkban, a felépítmény teljes szélességét kihasználva szerelhetők."
)
SPECS = {
    "Ajtólap": "7 önhordó alumínium lamella, szerkezeti ragasztással",
    "Felület": "eloxált alumínium",
    "Szélesség": "2550 mm (fix)",
    "Magasság": "igény szerint",
    "Tanúsítvány": "DIN EN 12642 Code XL (DEKRA)",
    "Zsanérok": "eloxált alumínium, horganyzott acél csap, kopásálló PE persely; 4 vagy 5 db 100 mm-es",
    "Zárak": "2 vagy 4 felső/alsó zár horganyzott acélból (kérésre AISI 304 rozsdamentes)",
    "Tömítés": "EPDM, körbefutó; középen háromajkú tömítés eloxált alu takaróléccel",
    "Opció": "dupla zárás, alumínium zsanérpánt",
}


# a Playwright-hoz telepített ffmpeg (VP8 kódoló, MJPEG bemenet) – kis méretű, minden böngészőben lejátszható WebM
FFMPEG = "/opt/pw-browsers/ffmpeg-1011/ffmpeg-linux"


def slideshow(frames, out):
    n = len(frames)
    seq = []
    for i in range(n):
        a, b = frames[i], frames[(i + 1) % n]
        seq += [a] * int(HOLD * FPS)
        seq += [cv2.addWeighted(a, 1 - (k + 1) / (FADE * FPS), b, (k + 1) / (FADE * FPS), 0) for k in range(int(FADE * FPS))]
    data = b"".join(cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tobytes() for f in seq)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(FPS), "-i", "pipe:0",
                    "-c:v", "libvpx", "-b:v", "600k", "-crf", "10", "-an", str(out)], input=data, check=True)


def framed(img):
    """A fotó a 4:3-as képkockában teljes magasságban, a két oldalon a saját elmosott, kinagyított képével."""
    h, w = img.shape[:2]
    k = max(W / w, H / h)
    bg = cv2.resize(img, (int(w * k) + 1, int(h * k) + 1))
    y, x = (bg.shape[0] - H) // 2, (bg.shape[1] - W) // 2
    bg = cv2.GaussianBlur(bg[y:y + H, x:x + W], (0, 0), 25)
    bg = cv2.addWeighted(bg, 0.7, np.full_like(bg, 30), 0.3, 0)
    k = min(W / w, H / h)
    fg = cv2.resize(img, (int(w * k), int(h * k)), interpolation=cv2.INTER_CUBIC)
    y, x = (H - fg.shape[0]) // 2, (W - fg.shape[1]) // 2
    bg[y:y + fg.shape[0], x:x + fg.shape[1]] = fg
    return bg


def video(frames, name):
    vdir = ROOT / "public/video"
    vdir.mkdir(parents=True, exist_ok=True)
    slideshow(frames, vdir / f"{name}.webm")
    cv2.imwrite(str(vdir / f"{name}.jpg"), frames[0], [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {"title": "Képek a hátsó ajtóról", "url": f"/video/{name}.webm", "poster": f"/video/{name}.jpg", "loop": True}


def main():
    slides = [cv2.imdecode(np.frombuffer(fetch(BASE + s), np.uint8), cv2.IMREAD_COLOR) for s in SLIDES]
    photos = [[sl[:, a:b] for a, b in zip(cuts, cuts[1:])] for sl, cuts in zip(slides, PANELS)]
    # a 3. sáv első fotója (kinyitott egy nagy ajtószárny) a 2 szárnyú ajtót mutatja (a Quadris jelzése szerint)
    two, four = photos[0] + photos[1] + photos[2][:1], photos[2][1:]
    rgb = lambda a: Image.fromarray(np.ascontiguousarray(a[..., ::-1]))  # noqa: E731
    data = load_enrichment()
    out = {}
    for slug, ph, card, name, kivitel in (
        (SLUG, two, two[0], "hatso-ajto-2-szarnyu", "2 szárnyú"),
        (SLUG4, four, four[1], "hatso-ajto-4-szarnyu", "4 szárnyú (2 + 2 ajtószárny)"),
    ):
        e = data.get(slug, {})
        e.update({"source": "", "sourceUrl": "", "sourceTitle": "",
                  "images": [save_image(rgb(card), slug, "foto")],
                  "description": DESCRIPTION if slug == SLUG else DESCRIPTION.replace("hátsóajtó-rendszer", "hátsóajtó-rendszer, 4 szárnyú kivitel,", 1),
                  "specs": {**SPECS, "Kivitel": f"{kivitel}; összeszerelve vagy könnyen összeszerelhető készletként"},
                  "videos": [video([framed(p) for p in ph], name)]})
        e.pop("documents", None)
        out[slug] = e
    update_enrichment(out)
    print(SLUG, SLUG4, "kész")


if __name__ == "__main__":
    main()
