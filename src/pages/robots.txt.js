// robots.txt – a tesztoldal (SITE.indexable = false) nem kerül be a keresőkbe; élesítéskor minden engedélyezett.
import { SITE, abs } from '../lib/site.js';

export function GET() {
  const rules = SITE.indexable
    ? ['User-agent: *', 'Allow: /', 'Disallow: /api/']
    : ['User-agent: *', 'Disallow: /'];
  return new Response([...rules, '', `Sitemap: ${abs('/sitemap.xml')}`, ''].join('\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}
