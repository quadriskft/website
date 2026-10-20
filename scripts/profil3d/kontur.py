"""Kontúrozott 3D renderek: a post.py helyett a nagyon világos (fehér) lemezeknél – az átlátszó PNG alfacsatornájából
sötét körvonal és enyhe élkiemelés, fehér háttérre vágva, WebP-ként.

Használat: python3 kontur.py <png-mappa> ../../public/termekkepek/3d
"""
import sys, cv2, numpy as np
from pathlib import Path
from PIL import Image
for f in sorted(Path(sys.argv[1]).glob("*.png")):
    im = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
    a = im[..., 3]; rgb = im[..., :3].astype(np.float32)
    m = (a > 60).astype(np.uint8) * 255
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    gray = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2GRAY)
    e = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 6, 18)
    e = cv2.bitwise_and(e, cv2.erode(m, np.ones((7, 7), np.uint8)))
    alpha = a.astype(np.float32)[..., None] / 255
    out = (rgb * alpha + 255 * (1 - alpha))
    out[e > 0] *= 0.6
    out = out.astype(np.uint8)
    cv2.drawContours(out, cs, -1, (95, 95, 95), 2, cv2.LINE_AA)
    ys, xs = np.where(m > 0); out = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    p = int(max(out.shape[:2]) * 0.06)
    out = cv2.copyMakeBorder(out, p, p, p, p, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    pil = Image.fromarray(out[..., ::-1]); pil.thumbnail((1000, 1000), Image.LANCZOS)
    pil.save(Path(sys.argv[2]) / f"{f.stem}.webp", "WEBP", quality=84, method=6)
