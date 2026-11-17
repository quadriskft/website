import { groups, products, publicProduct, familyOf, isWholeBar, DEFAULT_STOCK_LENGTH } from '../lib/catalog.js';

// gyári szálhossz (mm) a profilokhoz: a keresőből közvetlenül felvett tétel alapértelmezett mérete
function stockOf(p) {
  const raw = String(Object.entries(p.specs ?? {}).find(([k]) => /szálhossz|gyártási hossz|^hossz/i.test(k))?.[1]
    ?? p.name.match(/(\d{1,2} ?\d{3})\s*mm\b(?!.*mm)/)?.[1] ?? '').replace(/\s/g, '').replace(',', '.');
  return (/^\d+(\.\d+)?m$/.test(raw) ? Math.round(parseFloat(raw) * 1000) : Number(raw.match(/\d{4,5}/)?.[0])) || DEFAULT_STOCK_LENGTH;
}

// A keresőhöz és az ajánlatkérőhöz szükséges nyilvános adatok (beszállító nélkül!)
export function GET() {
  const categoryNames = new Map(groups.flatMap((g) => g.categories.map((c) => [`${g.slug}/${c.slug}`, c.name])));
  const body = {
    groups: groups.map((g) => ({ slug: g.slug, name: g.name })),
    products: products.map((p) => ({
      slug: p.slug,
      code: p.code,
      ...(p.codeLabel ? { codeLabel: p.codeLabel } : {}),
      name: p.name,
      group: p.group,
      categoryName: categoryNames.get(`${p.group}/${p.category}`) ?? '',
      image: p.images?.[0] ?? '',
      // az ajánlatkérőbe tételhez: változatos termék (termékoldalon választható), profil (hossz × darab), mértékegység
      ...(({ variants, profile, unit, cartonM }) => ({
        ...(variants ? { variants } : {}),
        ...(profile ? { profile, stock: stockOf(p), ...(isWholeBar(p) ? { bar: true } : {}) } : {}),
        ...(unit ? { unit, cartonM } : {}),
      }))(publicProduct(familyOf(p.slug) ? { ...p, family: true } : p)),
    })),
  };
  return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
