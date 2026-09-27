# Quadris Kft. – weboldal és termékkatalógus

Statikus termékkatalógus ajánlatkérő kosárral, [Astro](https://astro.build) alapon, Cloudflare Pages tárhelyen.

## Felépítés

| Hely | Tartalom |
|---|---|
| `data/forras/termekcsoportok.xlsx` | A beszállítói Excel (forrás) |
| `scripts/import_excel.py` | Excelből → `src/data/catalog.json` és `data/beszallitok.csv` |
| `src/data/catalog.json` | Termékcsoportok, kategóriák, termékek (ebből épül az oldal) |
| `src/lib/site.js` | Cégadatok (cím, telefon, e-mail), élesítési beállítások |
| `src/lib/catalog.js` | Csoport ikonok, leírások, lószállító oldal válogatása |
| `src/pages/` | Oldalak: főoldal, termékek, termék, keresés, ajánlatkérés, kapcsolat, lószállító |
| `functions/api/ajanlatkeres.js` | Cloudflare függvény: ajánlatkérés e-mailben (Resend) |
| `scripts/logo.cjs`, `public/brand/` | Logó generálása és logó fájlok |

**A beszállító neve és kódja belső adat** – a `catalog.json`-ban benne van, de a weboldalon
és a keresőindexben soha nem jelenik meg.

## Termékadatok frissítése

```sh
pip install openpyxl
python3 scripts/import_excel.py            # vagy: python3 scripts/import_excel.py uj.xlsx
```

## Futtatás helyben (opcionális)

Node.js 22 szükséges.

```sh
npm install
npm run dev      # http://localhost:4321
npm run build    # éles változat a dist/ mappába
```

## Cloudflare Pages

- Production branch: `main`, Framework preset: Astro, Build command: `npm run build`, Output: `dist`
- Ajánlatkérés e-mail küldéshez (Settings → Variables and Secrets):
  - `RESEND_API_KEY` – [Resend](https://resend.com) API kulcs (titkosítva)
  - `QUOTE_TO` – címzett e-mail cím(ek), vesszővel elválasztva
  - `QUOTE_FROM` – opcionális feladó, saját domain hitelesítése után

## Élesítés előtt

- `src/lib/site.js`: cégadatok kitöltése, `url` = saját domain, `indexable: true`
