# Quadrisk weboldal – termékkatalógus

Statikus termékkatalógus [Astro](https://astro.build) alapon, Cloudflare Pages tárhelyre.

## Felépítés

| Hely | Tartalom |
|---|---|
| `src/data/categories.json` | Kategóriák listája |
| `src/data/products.json` | Termékek (gyártó, cikkszám, leírás, műszaki adatok, képek, dokumentumok) |
| `src/pages/` | Oldalak: főoldal, kategória, termék, keresés, kapcsolat |
| `src/layouts/Base.astro` | Közös fejléc, lábléc, stílusok |
| `public/images/` | Képek |

A jelenlegi termékek és kategóriák csak minták, a valódi adatok a beszállítói Excel és a gyártói oldalak alapján kerülnek be.

## Futtatás helyben (opcionális)

Node.js 22 szükséges.

```sh
npm install
npm run dev      # fejlesztői szerver: http://localhost:4321
npm run build    # éles változat a dist/ mappába
```

## Cloudflare Pages beállítás

- Production branch: `main`
- Framework preset: Astro
- Build command: `npm run build`
- Build output directory: `dist`
