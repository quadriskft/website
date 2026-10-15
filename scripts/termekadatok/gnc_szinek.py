"""G&C – a színváltozatok képe (a gnc.py után futtatandó).

A G&C honlapján a legtöbb terméknek csak egy színben van fotója, ezért ugyanaz a kép jelenik meg a fehér,
a fekete és a szürke változatnál is. Ez a szkript a Quadris-megnevezésben szereplő szín (fekete / ZW, fehér,
szürke – data/termek_javitasok.json „Szín”) szerint átszínezi a termék képét: a háttértől (a kép széléről
elárasztott fehér terület) elválasztott terméket a cél színtartományába képezi le, a világos–sötét árnyalatok
sorrendjét megtartva (így a formák, élek, csillanások megmaradnak). Részleges átszínezésnél (pl. a „Flower
Power” keret) csak a sötét részek világosodnak.

Használat: python3 scripts/termekadatok/gnc_szinek.py
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, is_protected  # noqa: E402

# slug -> (forráskép slug, cél: 'fekete' | 'feher' | 'szurke' | 'feher_sotet_reszek')
RECOLOR = {
    "tetoventilator-manualis-fekete": ("tetoventilator-manualis-feher", "fekete"),
    "02-2200-zw-le-mans-tetoventilator-12v": ("le-mans-tetoventilator-12v", "fekete"),
    "turbo-iii-tetoventilator-feher": ("turbo-iii-tetoventilator-fekete", "feher", "kontraszt"),  # a Quadris kérésére élesebb
    "turbo-ii-tetoventilator-feher": ("turbo-ii-tetoventilator-fekete", "feher"),
    "ventillator-belso-takaro": ("ventillator-belso-takaro-szurke", "feher"),
    "ventillator-belso-takaro-12-24v-led": ("ventillator-belso-takaro-szurke", "feher"),
    "ventillator-belso-takaro-szurke": ("ventillator-belso-takaro-szurke", "szurke"),
    "manualis-belso-takaro-szurke": ("manualis-belso-takaro-feher", "szurke", "korong"),  # a lágy árnyék nélkül
    "belso-12v-os-led-takaro-flower-power-feher": ("belso-12v-os-led-takaro-flower-power-szurke", "feher_sotet_reszek"),
    "belso-24-v-os-led-vilagitassal-flower-power-feher": ("belso-12v-os-led-takaro-flower-power-szurke", "feher_sotet_reszek"),
}
# célszín-tartományok (sötét, világos) a termék árnyalataihoz
RANGE = {"fekete": (18, 78), "feher": (178, 250), "szurke": (105, 185)}
ORIG = ROOT / ".cache" / "gnc_szinek"  # az eredeti (átszínezés előtti) képek, hogy többszöri futtatás se rontson


def product_mask(a, limit=238):
    """A termék: minden, ami nem a kép széléről elárasztható, közel fehér háttér."""
    lum = a.mean(axis=2)
    bg = Image.fromarray(((lum > limit) * 255).astype(np.uint8)).copy()  # másolat: a tömbből készült kép nem írható
    w, h = bg.size
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if bg.getpixel(seed) == 255:
            ImageDraw.floodfill(bg, seed, 128)
    return np.asarray(bg) != 128


def disk_mask(lum):
    """Lapos, kerek termék (pl. belső takaró) körvonala: a felülnézeti ellipszis a tiszta felső ívből és a sötét
    alsó peremből illesztve (a kettő közti eltolás a korong vastagsága), így a lágy árnyék nem a termék része."""
    H, W = lum.shape
    top, bot = [], []
    for x in range(int(W * 0.09), int(W * 0.92), 4):
        t, b = np.where(lum[:, x] < 246)[0], np.where(lum[:, x] < 200)[0]
        if len(t):
            top.append((x, t.min()))
        if len(b):
            bot.append((x, b.max()))
    top, bot = np.array(top, float), np.array(bot, float)
    cy = (top[:, 1].min() + bot[:, 1].max()) / 2
    top, bot = top[top[:, 1] < cy - 60], bot[bot[:, 1] > cy + 60]
    best = None
    for t in range(0, 60, 2):
        P = np.vstack([top, bot - [0, t]]).astype(np.float32)
        e = cv2.fitEllipse(P.reshape(-1, 1, 2))
        (ex, ey), (w, h), ang = e
        M = cv2.ellipse2Poly((int(ex), int(ey)), (int(w / 2), int(h / 2)), int(ang), 0, 360, 2)
        d = np.mean([np.min(np.hypot(*(M - p).T)) for p in P])
        if best is None or d < best[0]:
            best = (d, t, e)
    _, t, ((ex, ey), (w, h), ang) = best
    mask = np.zeros((H, W), np.uint8)
    for dy in range(t + 1):
        cv2.ellipse(mask, ((ex, ey + dy), (w, h), ang), 255, -1)
    return mask > 0


def white_from_dark(img):
    """Fekete fotóból kontrasztos fehér változat (Turbo III): a termék körvonala a sötét test és a fölötte lévő
    fedélsáv uniója (a világos fedél tónusa átfed a lágy árnyékéval, ezért nem elég a világosság); a körvonalon
    kívül tiszta fehér, belül a tónusok 140–244 közé képezve (a fedél a háttér alatt marad, így a széle látszik)."""
    rgba = img.convert("RGBA")
    a = np.asarray(rgba).astype(float)
    rgb, alpha = a[..., :3], a[..., 3]
    lum = rgb.mean(axis=2)
    el = lambda d: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    body = cv2.morphologyEx((lum < 60).astype(np.uint8), cv2.MORPH_CLOSE, el(31))
    n, lab, st, _ = cv2.connectedComponentsWithStats(body, connectivity=8)
    body = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    ys = np.where(body.any(axis=1))[0]
    lid = ((lum < 205) & (np.arange(lum.shape[0])[:, None] < ys.min() + 25)).astype(np.uint8)
    sil = cv2.morphologyEx(body | lid, cv2.MORPH_CLOSE, el(15)) * 255
    cnts, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(sil, cnts, -1, 255, thickness=-1)
    sil = cv2.GaussianBlur(sil.astype(np.float32) / 255, (0, 0), 1.0)
    p1, p99 = np.percentile(lum[sil > 0.5], [1, 99])
    t = np.clip((lum - p1) / max(p99 - p1, 1), 0, 1) ** 0.8
    new = 140 + t * (244 - 140)
    out = new[..., None] * sil[..., None] + 255 * (1 - sil[..., None])
    res = Image.fromarray(np.dstack([np.repeat(np.clip(out, 0, 255), 3, axis=2), alpha]).astype(np.uint8), "RGBA")
    from PIL import ImageFilter
    sharp = res.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    return Image.merge("RGBA", (*sharp.split(), res.split()[3]))


def recolor(img, target, disk=False, contrast=False):
    if contrast and target == "feher":
        return white_from_dark(img)
    rgba = img.convert("RGBA")
    a = np.asarray(rgba).astype(float)
    rgb, alpha = a[..., :3], a[..., 3]
    lum = rgb.mean(axis=2)
    mask0 = product_mask(rgb, 238) & (alpha > 0)
    light_src = np.median(lum[mask0]) > 150  # világos (fehér) termékből készül a változat
    # világos forrásnál a háttér a tiszta fehér (a termék csillanása ne „folyjon ki” a háttérbe),
    # és csak a legnagyobb összefüggő folt a termék (a lágy árnyék apró foltjai nem)
    mask = product_mask(rgb, 246) & (alpha > 0) if light_src else mask0
    if disk:
        mask = disk_mask(lum)
    elif light_src:
        # a lágy árnyék vékony peremét morfológiai nyitással leválasztjuk, majd a legnagyobb folt a termék
        m8 = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(m8, connectivity=8)
        if n > 1:
            mask = labels == (1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])))
        # a termék belsejének csillanásai (a háttérrel nem érintkező világos foltok) is a termékhez tartoznak
        filled = mask.astype(np.uint8) * 255
        cnts, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(filled, cnts, -1, 255, thickness=-1)
        mask = filled > 0
    out = rgb.copy()
    if target == "feher_sotet_reszek":
        dark = mask & (lum < 160)
        new = 178 + (lum - lum[dark].min()) / max(np.ptp(lum[dark]), 1) * 70
        w = np.clip((170 - lum) / 30, 0, 1)
        out[dark] = rgb[dark] * (1 - w[dark][:, None]) + np.repeat(new[dark][:, None], 3, axis=1) * w[dark][:, None]
    else:
        lo, hi = (105, 250) if contrast and target == "feher" else RANGE[target]  # kontraszt: mélyebb árnyékok
        # sötétből világosba: csak a termék sötét részei (a világos, lágy árnyék a háttéren maradjon)
        body = mask if light_src else mask & (lum < 170)
        vals = lum[body]
        p1, p99 = np.percentile(vals, 1), np.percentile(vals, 99)
        t = np.clip((lum - p1) / max(p99 - p1, 1), 0, 1)
        new = lo + (t if light_src else t ** 0.7) * (hi - lo)
        w = np.ones_like(lum) if light_src else np.clip((200 - lum) / 45, 0, 1)  # átmenet az árnyék felé
        blend = rgb * (1 - w[..., None]) + np.repeat(new[..., None], 3, axis=2) * w[..., None]
        out[mask] = blend[mask]
    if disk:  # a háttér (a lágy árnyékkal együtt) tiszta fehér, a körvonal élsimítva
        soft = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.2)[..., None]
        out = out * soft + 255 * (1 - soft)
    res = np.dstack([np.clip(out, 0, 255), alpha]).astype(np.uint8)
    img = Image.fromarray(res, "RGBA")
    if contrast:  # élesítés
        from PIL import ImageFilter
        rgb_s = img.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=2))
        img = Image.merge("RGBA", (*rgb_s.split(), img.split()[3]))
    return img


def main():
    enrichment = json.loads((ROOT / "src/data/termekadatok.json").read_text())
    ORIG.mkdir(parents=True, exist_ok=True)
    for slug, (src, target, *mode) in RECOLOR.items():
        src_img = enrichment.get(src, {}).get("images", [])
        dst_img = enrichment.get(slug, {}).get("images", [])
        if not src_img or not dst_img:
            print("  nincs kép:", slug)
            continue
        src_path = ROOT / "public" / src_img[0].lstrip("/")
        keep = ORIG / f"{src}.webp"
        if not keep.exists():
            keep.write_bytes(src_path.read_bytes())
        out = recolor(Image.open(keep), target, disk="korong" in mode, contrast="kontraszt" in mode)
        if is_protected(dst_img[0]):  # kézzel feljavított kép: marad
            continue
        out.save(ROOT / "public" / dst_img[0].lstrip("/"), "WEBP", quality=90)
        print(f"  {slug}: {src} → {target}")


if __name__ == "__main__":
    main()
