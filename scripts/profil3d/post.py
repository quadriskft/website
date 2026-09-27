"""A 3D renderek (PNG, átlátszó) vágása, fehér háttérre helyezése és WebP mentése a public/termekkepek/3d mappába."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

src = Path(sys.argv[1])
dst = Path(__file__).resolve().parents[2] / "public/termekkepek/3d"
dst.mkdir(parents=True, exist_ok=True)
for f in sorted(src.glob("*.png")):
    im = Image.open(f)
    ys, xs = np.where(np.asarray(im)[..., 3] > 60)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    m = int(max(im.size) * 0.06)
    bg = Image.new("RGB", (im.width + 2 * m, im.height + 2 * m), "white")
    bg.paste(im, (m, m), im)
    bg.thumbnail((1000, 1000), Image.LANCZOS)
    bg.save(dst / f"{f.stem}.webp", "WEBP", quality=84, method=6)
print("kész")
