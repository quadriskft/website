import { groups, products } from '../lib/catalog.js';

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
    })),
  };
  return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
