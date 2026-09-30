"""Főkategória (termékcsoport) képek előállítása a csoportkártyákhoz.

- Profil- és anyagcsoportok: saját 3D renderek (scripts/csoportkepek-3d/, Three.js) -> RENDERS mappa
- A többi csoport: 1–2 jellemző termékfotó a letöltött termékképek közül

Kimenet: public/csoportkepek/<csoport>.webp (800×560, fehér háttér)
Használat: python3 scripts/csoportkepek.py [render_mappa]
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public/csoportkepek"
RENDERS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scripts/csoportkepek-3d/out"
W, H, PAD = 800, 560, 36

# csoport -> termékképek (public/ alatti útvonal); "cover" = kitöltő fotó (saját háttérrel)
PHOTOS = {
    "acel-profilok": ["cover", "../data/forras/cargoframes/cargoframes_kit_keret.jpg"],  # Cargo Frames összeszerelt acél plató-keret
    "platos-alkatreszek-es-kiegeszitok": ["termekkepek/451721-horganyzott-nagykonzol-man-50-mm-1.webp", "termekkepek/m12x140-rugos-felfuggesztes-1.webp"],
    # a Quadris által küldött három kép (narancs jelölőpontok és az ADA vízjel nélkül), azonos magasságban egymás mellett
    "acel-es-alu-rakoncak-es-szegok": ["row", "../data/forras/rakonca_csoportkep_1.png", "../data/forras/rakonca_csoportkep_2.png",
                                       "../data/forras/rakonca_csoportkep_3.png"],
    "elhuzhato-roloponyvas-rendszer": ["small", "../data/forras/roloponyvas_kategoria.png"],  # a Quadris által küldött kép (298×198)
    "ponyvarendszer-kiegeszitok": ["termekkepek/380184-ada-racsnis-feszito-kocka-adapterhez-r-1.webp"],
    "dobozos-felepitmeny-alkatreszek": ["termekkepek/714859-sullyesztett-inox-rudzar-25-16-mm-pl-1.webp"],
    "rakomanyrogzites": ["termekkepek/123412-spanifer-l-8-m-5000-kg-dupla-kampos-1.webp"],
    "sarvedok-szerszamosladak": ["termekkepek/j101620d-ives-sarvedo-450-1350-430-1.webp", "termekkepek/j205042-daken-arka-lada-655x450x470-mm-1.webp"],
    "specialis-felepitmeny-alkatreszek": ["termekkepek/815811-kis-negyszog-zar-1.webp"],
    "billencs-alkatreszek": ["termekkepek/146012-szivattyu-12v-1.webp"],
    "gumiszonyegek": ["cover", "termekkepek/rs-stud-mat-1.webp"],
    "szellozes-tetoablakok-vilagitas": ["termekkepek/gc-le-mans-ll-1.webp", "termekkepek/ledes-lampa-kerek-feher-1.webp"],
    "italszallito-kit": ["termekkepek/212427-ada-s-ajto-profil-2100-mm-elox-1.webp"],
}


def trim(im):
    """Fehér / átlátszó szélek levágása."""
    rgba = im.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(bg, rgba).convert("RGB")
    diff = ImageChops.difference(flat, Image.new("RGB", flat.size, "white")).convert("L").point(lambda v: 255 if v > 12 else 0)
    box = diff.getbbox()
    return flat.crop(box) if box else flat


def compose(images):
    canvas = Image.new("RGB", (W, H), "white")
    n = len(images)
    slot_w = (W - PAD * (n + 1)) // n
    for i, im in enumerate(images):
        im = trim(im)
        scale = min(slot_w / im.width, (H - 2 * PAD) / im.height)  # kicsinyítés és nagyítás is
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        x = PAD + i * (slot_w + PAD) + (slot_w - im.width) // 2
        canvas.paste(im, (x, (H - im.height) // 2))
    return canvas


def row(images, gap=28):
    """Képek egymás mellett, azonos magasságra méretezve (a szélesebbek nem zsugorodnak a keskenyebbek miatt)."""
    ims = [trim(im) for im in images]
    h = H - 2 * PAD
    ims = [im.resize((round(im.width * h / im.height), h), Image.LANCZOS) for im in ims]
    total = sum(im.width for im in ims) + gap * (len(ims) - 1)
    if total > W - 2 * PAD:
        k = (W - 2 * PAD) / total
        ims = [im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS) for im in ims]
        gap, total = round(gap * k), W - 2 * PAD
    canvas = Image.new("RGB", (W, H), "white")
    x = (W - total) // 2
    for im in ims:
        canvas.paste(im, (x, (H - im.height) // 2))
        x += im.width + gap
    return canvas


def cover(im):
    im = im.convert("RGB")
    scale = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    if scale > 1.5:  # erős nagyításnál enyhe élesítés
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    left, top = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((left, top, left + W, top + H))


def small(im, frac=0.72):
    """Saját hátterű fotó kisebb méretben, fehér keretben középen (a kitöltő mód túl nagynak hatott)."""
    im = im.convert("RGB")
    scale = min(W * frac / im.width, H * frac / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    if scale > 1.5:
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    return canvas


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    done = []
    for png in sorted(RENDERS.glob("*.png")):
        compose([Image.open(png)]).save(OUT / f"{png.stem}.webp", "WEBP", quality=84, method=6)
        done.append(png.stem)
    for group, paths in PHOTOS.items():
        if paths[0] == "cover":
            img = cover(Image.open(ROOT / "public" / paths[1]))
        elif paths[0] == "row":
            img = row([Image.open(ROOT / "public" / p) for p in paths[1:]])
        elif paths[0] == "small":
            img = small(Image.open(ROOT / "public" / paths[1]))
        else:
            img = compose([Image.open(ROOT / "public" / p) for p in paths])
        img.save(OUT / f"{group}.webp", "WEBP", quality=84, method=6)
        done.append(group)
    print(f"{len(done)} csoportkép -> {OUT}")


if __name__ == "__main__":
    main()
