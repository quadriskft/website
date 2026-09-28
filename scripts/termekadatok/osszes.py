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

SCRIPTS = ["ital_accessori", "woocommerce", "fts_katalogus", "pastore", "caralu", "alusv", "adaico", "adaico_katalogus", "sandprofile", "sandprofile_kiegeszites", "sitemap_kereso", "parlok", "jonesco", "gnc", "pommier", "pommier_katalogus", "reall", "cimaplast", "metra", "bodega", "exlabesa", "kety", "polser", "versus", "versus_dtl", "versus_katalogus", "edscha", "bmc", "alcomet", "kloeckner", "dost", "plasticpadana", "copar", "industrilas", "edscha_compact", "adaico_slider", "mpsteel", "cargoframes", "wistra", "miederhoff", "takler", "nevbol"]

for name in SCRIPTS + ["szoveg_eltavolitas"]:
    print(f"\n=== {name} ===", flush=True)
    sys.argv = [name] + (["FTS"] if name == "szoveg_eltavolitas" else [])
    try:
        runpy.run_path(str(HERE / f"{name}.py"), run_name="__main__")
    except SystemExit:
        pass

used = {img.split("/")[-1] for e in json.loads(ENRICHMENT.read_text()).values() for img in e.get("images", [])}
orphans = [f for f in IMAGE_DIR.glob("*.webp") if f.name not in used]
for f in orphans:
    f.unlink()
print(f"\n{len(orphans)} gazdátlan kép törölve, {len(used)} kép használatban")
