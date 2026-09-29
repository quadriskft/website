"""A termékképlisták végső rendbetétele – az osszes.py-ban minden letöltő / képfeldolgozó szkript után fut.

1. A védett, kézzel készített 3D kép (<slug>-3d.webp, data/vedett_kepek.json) mindig elöl marad: első kép,
   kivéve, ha a lista egységes méretezett rajzzal (-rajz.webp) kezdődik – ott a rajz után, 2. képként
   (sarokoszlopok). A letöltő szkriptek újrafuttatáskor csak a saját képeiket írják a listába.
   A méretezett rajz lehet -rajz.webp (sarokoszlopok) vagy -meretrajz.webp (Edscha tetőprofilok).
2. A már nem létező képfájlokra mutató hivatkozások kikerülnek (pl. egy lecserélt, törölt forráskép).
3. Kézi sorrend és kizárt képek (data/kezi_kepsorrend.json): a "sorrend"-ben megadott képek kerülnek előre
   ebben a sorrendben, a "kizart" fájlnevek kikerülnek (a Quadris kérésére törölt képek).

Használat: python3 scripts/termekadatok/kep_sorrend.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ENRICHMENT, ROOT, is_protected  # noqa: E402


KEZI = ROOT / "data" / "kezi_kepsorrend.json"


def main():
    data = json.loads(ENRICHMENT.read_text())
    kezi = json.loads(KEZI.read_text()) if KEZI.exists() else {}
    sorrend, kizart = kezi.get("sorrend", {}), set(kezi.get("kizart", []))
    moved = missing = 0
    for slug, e in data.items():
        images = e.get("images") or []
        exists = [u for u in images if (ROOT / "public" / u.lstrip("/")).exists() and u.rsplit("/", 1)[-1] not in kizart]
        for u in images:
            if u not in exists:
                print(f"  hiányzó kép kivéve: {slug}: {u}")
                missing += 1
        d3 = f"/termekkepek/{slug}-3d.webp"
        if (ROOT / "public" / d3.lstrip("/")).exists() and is_protected(d3):
            rest = [u for u in exists if u != d3]
            pos = 1 if rest and rest[0].endswith(("-rajz.webp", "-meretrajz.webp")) else 0
            new = rest[:pos] + [d3] + rest[pos:]
            moved += new != exists
            exists = new
        if slug in sorrend:
            elore = [u for u in sorrend[slug] if u in exists]
            exists = elore + [u for u in exists if u not in elore]
        if exists != images:
            e["images"] = exists
    ENRICHMENT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"képsorrend: {moved} 3D kép a helyére téve, {missing} hiányzó hivatkozás kivéve")


if __name__ == "__main__":
    main()
