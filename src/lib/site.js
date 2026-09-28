// A cég adatai. Az üresen hagyott mezők nem jelennek meg az oldalon.
export const SITE = {
  name: 'Quadris Kft.',
  shortName: 'Quadris',
  tagline: 'Felépítmény alkatrészek gyártóknak',
  legalName: 'QUADRIS Korlátolt Felelősségű Társaság',
  email: 'quadris@quadris.hu',
  phone: '+36 30 246 6071',
  address: '2220 Vecsés, Tengely utca 8.',
  openingHours: 'H–Cs 7:30–16:30, P 7:30–14:00, Szo–V zárva',
  companyRegNo: '13-09-230949',
  taxNumber: '14892057-2-13',
  registryCourt: 'Budapest Környéki Törvényszék Cégbírósága',
  foundingYear: 2009,
  seat: { postalCode: '2220', city: 'Vecsés', street: 'Tengely utca 8.' },
  // tárhelyszolgáltató (Eker. tv. 4. § – impresszum)
  hosting: { name: 'Cloudflare, Inc.', address: '101 Townsend St, San Francisco, CA 94107, USA', web: 'https://www.cloudflare.com' },
  // e-mail kézbesítés az ajánlatkérő űrlaphoz (adatfeldolgozó)
  mailer: { name: 'Resend', web: 'https://resend.com' },
  // Élesítéskor: a saját domain (pl. 'https://www.quadris.hu') és indexable: true,
  // addig a tesztoldal nem kerül be a keresőkbe.
  url: '',
  indexable: false,
  // a tesztoldal címe – amíg nincs saját domain, az abszolút linkek (megosztási kép, oldaltérkép) ezt használják
  previewUrl: 'https://website-9ib.pages.dev',
};

// Abszolút webcím (canonical, megosztás, oldaltérkép)
export const ORIGIN = SITE.url || SITE.previewUrl;
export const abs = (path) => new URL(path, ORIGIN).href;
// Oldal-cím a Cloudflare által használt záró „/” formában (a kanonikus alak)
export const absPage = (path) => abs(path === '/' || path.endsWith('/') || path.includes('#') ? path : `${path}/`);
