"""A Quadris által külön küldött termékképek (fotó, rajz), amelyek a termék képeit váltják – a küldött kis képek
MI-vel (EDSR) 4x nagyítva, enyhén élesítve, a fehér margó levágva: data/forras/<forrás>. A "+" a termék eddigi
(nem küldött) képeit hagyja meg az adott helyen.

Használat: python3 scripts/termekadatok/kuldott_termekkepek.py   (utána kep_sorrend.py)
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_enrichment, save_image, update_enrichment  # noqa: E402

# slug -> a termék képei sorrendben (data/forras/…)
KEPEK = {
    "502501-szimpla-gorgos-gumiutkozo-d100-118": ["502501_foto.png", "502501_rajz.png"],
    "502502-dupla-gorgos-gumiutkozo-222x115": ["502502_foto.png", "502502_rajz.png"],
    "502500-szimpla-gorgos-gumiutkozo-d70-85": ["502500_foto.png", "+"],
    # StopSpray sárvédő lap (logó nélküli kivitel): a gyártói kép a logó és a dombornyomott jelek nélkül, a méretrajz a
    # méretekkel (a logó nélkül), a felület részletfotója
    "jf556045-550-600x450-mm-sarvedo-lap-stopsray": ["stopspray_foto.png", "stopspray_rajz.png", "stopspray_reszlet.png"],
    # gumis zsanér (Eli-Ti): a gyártói adatlap képe nagyítva, a cikkszám-/csomagadat-fejléc és a feliratok nélkül
    **{s: ["gumis_zsaner_eli-ti.png"] for s in ("831245-gumis-zsaner-l-2500-mm", "831230-gumis-zsaner-l-3000-mm",
                                                "831440-gumis-zsaner-l-4000-mm")},
}


def main():
    data = load_enrichment()
    updates = {}
    for slug, files in KEPEK.items():
        e = data.get(slug) or {"source": "Quadris fotó", "sourceUrl": "", "sourceTitle": "", "specs": {}, "images": []}
        regi = [u for u in e.get("images", []) if "-kuldott-" not in u]
        e["images"] = [u for i, f in enumerate(files, 1) for u in
                       (regi if f == "+" else [save_image(Image.open(ROOT / "data/forras" / f), slug, f"kuldott-{i}")])]
        updates[slug] = e
        print(slug, e["images"])
    update_enrichment(updates)


if __name__ == "__main__":
    main()
