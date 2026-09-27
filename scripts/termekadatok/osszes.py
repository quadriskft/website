"""Az összes beszállítói letöltő futtatása egymás után.

Használat: python3 scripts/termekadatok/osszes.py
A letöltött oldalak a .cache/ mappában maradnak, így az újrafuttatás gyors.
Végül törli a már egyik termékhez sem tartozó képeket.
"""

import json
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from common import ENRICHMENT, IMAGE_DIR  # noqa: E402

SCRIPTS = ["ital_accessori", "woocommerce", "pastore", "caralu", "alusv", "adaico", "sandprofile", "sitemap_kereso", "parlok", "jonesco", "gnc", "pommier"]

for name in SCRIPTS:
    print(f"\n=== {name} ===", flush=True)
    sys.argv = [name]
    try:
        runpy.run_path(str(HERE / f"{name}.py"), run_name="__main__")
    except SystemExit:
        pass

used = {img.split("/")[-1] for e in json.loads(ENRICHMENT.read_text()).values() for img in e.get("images", [])}
orphans = [f for f in IMAGE_DIR.glob("*.webp") if f.name not in used]
for f in orphans:
    f.unlink()
print(f"\n{len(orphans)} gazdátlan kép törölve, {len(used)} kép használatban")
