// Oldaltérkép a keresőknek: minden statikus oldal, termékcsoport és termékoldal.
import { groups, products } from '../lib/catalog.js';
import { absPage } from '../lib/site.js';

const STATIC = [
  ['/', '1.0', 'weekly'],
  ['/termekek', '0.9', 'weekly'],
  ['/loszallito-felepitmenyek', '0.8', 'monthly'],
  ['/ajanlatkeres', '0.6', 'monthly'],
  ['/kapcsolat', '0.6', 'monthly'],
  ['/impresszum', '0.2', 'yearly'],
  ['/adatkezeles', '0.2', 'yearly'],
];

export function GET() {
  const today = new Date().toISOString().slice(0, 10);
  const urls = [
    ...STATIC,
    ...groups.map((g) => [`/termekek/${g.slug}`, '0.8', 'weekly']),
    ...products.map((p) => [`/termek/${p.slug}`, '0.6', 'monthly']),
  ];
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(([u, pr, cf]) => `  <url><loc>${absPage(u)}</loc><lastmod>${today}</lastmod><changefreq>${cf}</changefreq><priority>${pr}</priority></url>`).join('\n')}
</urlset>
`;
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
