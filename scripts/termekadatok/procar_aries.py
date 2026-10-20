"""Hátsó ajtó alu elox (2 és 4 szárnyú): a ProCar ARIES hátsóajtó-rendszer adatai a Quadris kérésére
(https://www.procaritalia.eu/procar/Aries.html).

- a gyártói oldal diavetítésének 3 képe (11 fotó) „videószerűen”: áttűnéssel, folyamatosan ismétlődő, hang nélküli
  WebM videóként (public/video/aries-hatso-ajto.webm + poszterkép), a termékoldalon a fő kép helyén; a listákban
  a hátsó nézet fotója a termék képe
- magyar leírás és műszaki adatok a gyártói szöveg alapján
- dokumentumok: termékkatalógus, DEKRA-tanúsítvány (DIN EN 12642 Code XL), szerelési útmutató (PDF)

Használat: python3 scripts/termekadatok/procar_aries.py
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
BASE = "https://www.procaritalia.eu/procar/"
SLIDES = ["images/Aries.jpg", "images/Aries_1.jpg", "images/Aries_2.jpg"]
DOCS = [("2017_Aries_A4_x_PROCAR.pdf", "aries-katalogus.pdf", "ARIES hátsóajtó-rendszer – katalógus (PDF)"),
        ("certificato_web.pdf", "aries-tanusitvany.pdf", "DEKRA-tanúsítvány – DIN EN 12642 Code XL (PDF)"),
        ("PORTA ARIES - ISTRUZIONI DI MONTAGGIO.pdf", "aries-szerelesi-utmutato.pdf", "Szerelési útmutató (PDF, olasz)")]
# a diavetítés képei 2–5 fotóból összeállított sávok: a videó fotónként mutatja őket (4:3, elmosott háttérrel)
PANELS = [[0, 552, 1105, 1650], [0, 572, 1245, 1650], [0, 375, 745, 1053, 1382, 1650]]
W, H = 960, 720
FPS, HOLD, FADE = 25, 2.5, 1.0

DESCRIPTION = (
    "ProCar ARIES alumínium hátsóajtó-rendszer haszonjárművek felépítményeihez. Az ajtólap 7 önhordó, eloxált "
    "alumínium lamellából áll, amelyeket szerkezeti ragasztó köt össze; a lamellák a felső és alsó homloklemezhez "
    "nagy szilárdságú horganyzott acél szegecsekkel kapcsolódnak. A kerület menti keret elhagyásával kisebb tömeg "
    "mellett nagyobb merevséget és igényes megjelenést ad. Az ARIES ajtó a DEKRA által kiadott DIN EN 12642 Code XL "
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
    "Kivitel": "2 vagy 4 szárnyú; összeszerelve vagy könnyen összeszerelhető készletként",
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


def main():
    slides = [cv2.imdecode(np.frombuffer(fetch(BASE + s), np.uint8), cv2.IMREAD_COLOR) for s in SLIDES]
    frames = [framed(sl[:, a:b]) for sl, cuts in zip(slides, PANELS) for a, b in zip(cuts, cuts[1:])]
    vdir = ROOT / "public/video"
    vdir.mkdir(parents=True, exist_ok=True)
    slideshow(frames, vdir / "aries-hatso-ajto.webm")
    cv2.imwrite(str(vdir / "aries-hatso-ajto.jpg"), frames[0], [cv2.IMWRITE_JPEG_QUALITY, 85])
    card = save_image(Image.fromarray(np.ascontiguousarray(slides[2][:, 745:1053][..., ::-1])), SLUG, "aries")
    ddir = ROOT / "public/dokumentumok"
    ddir.mkdir(parents=True, exist_ok=True)
    docs = []
    for src, dst, title in DOCS:
        (ddir / dst).write_bytes(fetch(BASE + src.replace(" ", "%20")))
        docs.append({"title": title, "url": f"/dokumentumok/{dst}"})
    data = load_enrichment()
    e = data.get(SLUG, {"source": "ProCar", "sourceUrl": BASE + "Aries.html", "sourceTitle": "ARIES", "specs": {}, "images": []})
    e.update({"images": [card], "description": DESCRIPTION, "specs": {**e.get("specs", {}), **SPECS}, "documents": docs,
              "videos": [{"title": "ARIES hátsó ajtó – képek a gyártótól", "url": "/video/aries-hatso-ajto.webm",
                          "poster": "/video/aries-hatso-ajto.jpg", "loop": True}]})
    e4 = {**e, "images": [card], "specs": {**e["specs"], "Kivitel": "4 szárnyú (2 + 2 ajtószárny); összeszerelve vagy készletként"},
          "description": DESCRIPTION.replace("hátsóajtó-rendszer", "hátsóajtó-rendszer, 4 szárnyú kivitel,", 1)}
    update_enrichment({SLUG: e, SLUG4: e4})
    print(SLUG, SLUG4, "kész")


if __name__ == "__main__":
    main()
