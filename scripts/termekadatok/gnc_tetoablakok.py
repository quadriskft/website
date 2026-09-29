"""G&C tetőablakok és vezérlőegység: a gyártói oldalon elérhető összes kép (fotó + méretrajz) a termékekhez.

A G&C terméklapok galériájában a szomszédos termékek képei is szerepelnek, ezért a képek kézzel párosítva
(a fájlnév a gyártói cikkszám: 90-5000-E, 90-5000-DG, 90-6000-E, 90-6000-DG, 30-6000). A 970×530-as
elektromos ablak rajza azonos a kéziével (ugyanaz a keret). Az „uitgeklapt” kép tetőventilátor, kimarad.
A gnc.py után fut (a saját forrásnevével), így annak egyetlen képét váltja.

Használat: python3 scripts/termekadatok/gnc_tetoablakok.py
"""

import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from common import clear_images, fetch, load_enrichment, save_image, update_enrichment  # noqa: E402

SOURCE = "G&C tetőablak képek"
U = "https://gnc-systems.com/wp-content/uploads/2024/01/"
DRAW_530 = {"Külső méret [mm]": "640 × 640", "Beépítési magasság [mm]": "84"}
DRAW_970 = {"Külső méret [mm]": "1080 × 640", "Beépítési magasság [mm]": "84"}
# slug -> (gyártói oldal, képek, adatok)
ITEMS = {
    "elektromos-tetoablak-24v-530x530": ("roof-hatches-manual-small", ["90-5000-E-foto1.jpg", "90-5000-E-tekening.jpg"], DRAW_530),
    "gc-electric-round": ("electric-round", ["90-5000-DG-LUS-foto1-1-rotated.jpg", "90-5000-DG-LUS-tekening.jpg"],
                          {"Nyílásméret [mm]": "530 × 530", **DRAW_530}),
    "elektromos-tetoablak-24v-970x530": ("roof-hatches-electric-large", ["90-6000-E-foto1-1-scaled.jpg", "90-6000-DG-LUS-tekening-1.jpg"], DRAW_970),
    "gc-roof-hatches-manual-big": ("roof-hatches-manual-big", ["90-6000-DG-LUS-foto1-1-scaled.jpg", "90-6000-DG-LUS-tekening-1.jpg"],
                                   {"Nyílásméret [mm]": "970 × 530", **DRAW_970}),
    "tetoablak-vezerloegyseg-24v": ("control-unit", ["30-6000-foto1fc.jpg", "30-6000-foto2-scaled.webp", "30-6000-tekening.jpg"],
                                    {"Beépítési méret [mm]": "87 × 38 × 35"}),
}


def main():
    old = load_enrichment()
    enrichment = {}
    for slug, (page, files, specs) in ITEMS.items():
        clear_images(slug)
        images = [save_image(Image.open(io.BytesIO(fetch(U + f))), slug, i) for i, f in enumerate(files, 1)]
        prev = old.get(slug, {})
        enrichment[slug] = {"source": SOURCE, "sourceUrl": f"https://gnc-systems.com/en/products/{page}/",
                            "specs": {**prev.get("specs", {}), **specs}, "images": images}
    update_enrichment(enrichment, SOURCE)
    print(f"{SOURCE}: {len(enrichment)} termék")


if __name__ == "__main__":
    main()
