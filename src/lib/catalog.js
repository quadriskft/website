import catalog from '../data/catalog.json';
import extra from '../data/termekadatok.json';
import extended from '../data/bovitett.json';

// FONTOS: a termékadatokban lévő beszállító (supplier, supplierCode, source…) belső adat,
// a weboldalon soha nem jelenik meg.

// Az Excelből jövő alapadatok kiegészítése a beszállítói oldalakról letöltött
// képekkel és műszaki adatokkal (scripts/termekadatok/).
const excelProducts = catalog.products.map((p) => {
  const e = extra[p.slug];
  const move = extended.moves?.[p.slug];
  const out = move ? { ...p, group: move.group, category: move.category } : p;
  if (!e) return out;
  return {
    ...out,
    images: e.images?.length ? e.images : p.images,
    specs: { ...(e.specs ?? {}), ...p.specs },
    description: p.description || e.description || '',
  };
});

// A beszállítók teljes kínálatából felvett további termékek (scripts/termekadatok/teljes_kinalat.py)
const extendedProducts = (extended.products ?? []).map((p) => ({
  slug: p.slug, code: p.code, name: p.name, group: p.group, category: p.category,
  specs: p.specs ?? {}, images: p.images ?? [], description: p.description ?? '', documents: [], supplier: p.source,
}));

export const products = [...excelProducts, ...extendedProducts];

// Csoportok és kategóriák: Excel + új csoportok/kategóriák, darabszámok újraszámolva, üresek elhagyva
const groupList = catalog.groups.map((g) => ({
  slug: g.slug,
  name: extended.renameGroups?.[g.slug] ?? g.name,
  categories: g.categories.map((c) => ({ slug: c.slug, name: c.name })),
}));
for (const g of extended.groups ?? []) {
  groupList.push({ slug: g.slug, name: g.name, categories: [] });
}
for (const c of extended.categories ?? []) {
  const g = groupList.find((x) => x.slug === c.group);
  if (g && !g.categories.some((x) => x.slug === c.slug)) g.categories.push({ slug: c.slug, name: c.name });
}
const counts = new Map();
for (const p of products) counts.set(`${p.group}/${p.category}`, (counts.get(`${p.group}/${p.category}`) ?? 0) + 1);
export const groups = groupList
  .map((g) => {
    const categories = g.categories
      .map((c) => ({ ...c, count: counts.get(`${g.slug}/${c.slug}`) ?? 0 }))
      .filter((c) => c.count > 0);
    return { ...g, categories, count: categories.reduce((n, c) => n + c.count, 0) };
  })
  .filter((g) => g.count > 0);

const groupsBySlug = new Map(groups.map((g) => [g.slug, g]));
const productsBySlug = new Map(products.map((p) => [p.slug, p]));

// Csoportonkénti ikon (Lucide) és rövid leírás
export const GROUP_META = {
  'aluminium-alvaz-profilok': { icon: 'Frame', text: 'Hossz- és kereszttartók, keretprofilok, aláfutásgátló profilok alumínium alvázakhoz.' },
  'acel-profilok': { icon: 'Construction', text: 'Acél hossztartók, keretek, lézerhegesztett és Heavy Duty acél oldalfalak nagy terhelésű felépítményekhez.' },
  'aluminium-padlo-profilok': { icon: 'Rows3', text: 'Padló-, rámpa- és autószállító profilok alumíniumból.' },
  'ponyvas-oldalfal-profilok-es-szegok': { icon: 'Columns3', text: 'Oldalfal rendszerek, monó profilok, szegők és billencs oldalfalak.' },
  'platos-alkatreszek-es-kiegeszitok': { icon: 'Truck', text: 'Alváz konzolok, TIR zsanérok, Z-zárak, fellépők és pótkerék tartók.' },
  'acel-es-alu-rakoncak-es-szegok': { icon: 'PanelsTopLeft', text: 'Köztes, első és hátsó rakoncák acélból és alumíniumból.' },
  'elhuzhato-roloponyvas-rendszer': { icon: 'Blinds', text: 'Elhúzható tető- és oldalponyva rendszerek, sarokoszlopok, C-sínek.' },
  'ponyvarendszer-kiegeszitok': { icon: 'Tent', text: 'Ponyvacsövek, spitzprofilok, ponyvatartók és ponyvafeszítők.' },
  'hatso-ajtok-es-athajto-rampak': { icon: 'DoorOpen', text: 'Alumínium hátsó ajtók és áthajtó rámpák.' },
  'zart-dobozos-es-hutos-profilok': { icon: 'Snowflake', text: 'Profilok zárt dobozos és hűtős felépítményekhez, komplett készletek.' },
  'dobozos-felepitmeny-alkatreszek': { icon: 'Lock', text: 'Zsanérok, zárak, tömítések, létrák, ütközők, ajtórögzítők, húspálya.' },
  'rakomanyrogzites': { icon: 'Anchor', text: 'Rakományrögzítő sínek, rudak, hevederek és tartozékok.' },
  'sarvedok-szerszamosladak': { icon: 'Package', text: 'Sárvédők, szerszámosládák, sárfogók, poroltó- és víztartályok.' },
  'ipari-felgyartmanyok': { icon: 'Ruler', text: 'Zártszelvények, U- és L-profilok, csövek, rudak, laposprofilok.' },
  'aluminium-lemezek': { icon: 'SquareStack', text: 'Sima, cseppmintás és festett alumínium lemezek.' },
  'csuszasmentes-retegelt-padlo': { icon: 'Layers', text: 'Csúszásmentes és fenolos rétegelt lemezek padlónak és falnak.' },
  'gumiszonyegek': { icon: 'Grid3x3', text: 'Istálló-, utánfutó-, rámpa- és munkahelyi gumiszőnyegek, gumi-, PU- és PVC lemezek, moosgumi.' },
  'kedergumik': { icon: 'Spline', text: 'Élvédő, tömítő-, kéder-, üvegvezető és moosgumi profilok felépítményekhez.' },
  'uvegszalas-polieszter': { icon: 'Sheet', text: 'Üvegszálas poliészter (GFK) lemezek és panelek.' },
  'specialis-felepitmeny-alkatreszek': { icon: 'Cog', text: 'Speciális zárak, szerelvények és egyedi felépítmény alkatrészek.' },
  'italszallito-kit': { icon: 'Wine', text: 'Komplett alkatrészkészlet italszállító felépítményekhez.' },
  'billencs-alkatreszek': { icon: 'Forklift', text: 'Munkahengerek, bölcsők, kardánok, billencs rakoncák és vezérlés.' },
};

// Lószállító felépítmény gyártóknak kiemelt kategóriák: [csoport, kategória, felirat]
for (const g of extended.groups ?? []) {
  if (!GROUP_META[g.slug]) GROUP_META[g.slug] = { icon: g.icon ?? 'Package', text: g.text ?? '' };
}

export const HORSE_SECTIONS = [
  ['gumiszonyegek', 'istallo-szonyeg', 'Istálló- és utánfutó szőnyegek'],
  ['gumiszonyegek', 'rampa-szonyeg', 'Rámpa szőnyegek'],
  ['gumiszonyegek', 'soft-gumi', 'Soft gumi lapok'],
  ['aluminium-padlo-profilok', 'rampa-profilok', 'Rámpa profilok'],
  ['hatso-ajtok-es-athajto-rampak', 'athajtorampa', 'Áthajtó rámpák'],
  ['szellozes-tetoablakok-vilagitas', 'tetoventilatorok', 'Tetőventilátorok'],
  ['szellozes-tetoablakok-vilagitas', 'tetoablakok', 'Tetőablakok'],
  ['szellozes-tetoablakok-vilagitas', 'vilagitas', 'Belső világítás'],
  ['csuszasmentes-retegelt-padlo', 'lowipan', 'Csúszásmentes padlólemezek'],
  ['dobozos-felepitmeny-alkatreszek', 'zsanerok', 'Zsanérok'],
  ['dobozos-felepitmeny-alkatreszek', 'zarak', 'Zárak'],
  ['dobozos-felepitmeny-alkatreszek', 'ajtorogzitok', 'Ajtórögzítők'],
  ['dobozos-felepitmeny-alkatreszek', 'gumiutkozok', 'Gumiütközők'],
  ['dobozos-felepitmeny-alkatreszek', 'tomitesek', 'Tömítések'],
  ['uvegszalas-polieszter', 'uvegszalas-polyester', 'Üvegszálas poliészter lemezek'],
];

export function getGroup(slug) {
  return groupsBySlug.get(slug);
}

export function getProduct(slug) {
  return productsBySlug.get(slug);
}

export function getCategory(groupSlug, categorySlug) {
  return getGroup(groupSlug)?.categories.find((c) => c.slug === categorySlug);
}

export function productsIn(groupSlug, categorySlug) {
  return products.filter((p) => p.group === groupSlug && (!categorySlug || p.category === categorySlug));
}

// Főkategória kép (scripts/csoportkepek.py állítja elő)
export function groupImage(slug) {
  return `/csoportkepek/${slug}.webp`;
}

export function groupIcon(slug) {
  return GROUP_META[slug]?.icon ?? 'Package';
}

export function productTitle(p) {
  return p.code ? `${p.code} ${p.name}` : p.name;
}

// Hosszra rendelhető (szálas) termékek: profilok, csövek, sínek, gumiprofilok.
// Ezeknél a termékoldalon hossz × darab méretsorokat lehet megadni az ajánlatkéréshez.
const PROFILE_GROUPS = new Set([
  'aluminium-alvaz-profilok', 'acel-profilok', 'aluminium-padlo-profilok', 'ponyvas-oldalfal-profilok-es-szegok',
  'zart-dobozos-es-hutos-profilok', 'ipari-felgyartmanyok', 'kedergumik',
]);
const NO_PROFILE_GROUPS = new Set(['sarvedok-szerszamosladak', 'gumiszonyegek', 'szellozes-tetoablakok-vilagitas']);
const HARD_NO = /dugó|végz[aá]r|kupak|(^|\s)csavar(\s|ok|$)|bilincs|adapter|készlet|(^|\s)kit(\s|$)|szett|garnitúra|kurbli|kulcs/i;
const PROFILE_NAME = /profil|hossztartó|kereszttartó|szelvény|laposrúd|(^|\s)sín(\s|$)|sínek|tetősín|"c" sín|(^|\s)cső(\s|$)|csövek|kéder|(^|[\s-])léc(\s|$)|oszlop|tömítés|takarógumi|zsanér \d{4}/i;
const SOFT_NO = /(^|[\s"(])(tartó|konzol|kengyel|lapka|sarokelem|összekötő|elem|zár|zsanér|görgő|kocsi|rúd|szegő)(\s|$)/i;
export function isProfile(p) {
  if (NO_PROFILE_GROUPS.has(p.group) || HARD_NO.test(p.name)) return false;
  if (PROFILE_GROUPS.has(p.group) || /profil|hossztartó|kereszttartó|szelvény/i.test(p.name)) return true;
  if (SOFT_NO.test(p.name)) return false;
  return PROFILE_NAME.test(p.name);
}

// Böngészőnek küldhető termékadat (belső mezők nélkül)
export function publicProduct(p) {
  return { slug: p.slug, code: p.code, name: p.name, group: p.group, image: p.images?.[0] ?? '', ...(isProfile(p) ? { profile: true } : {}) };
}

export const stats = {
  products: products.length,
  groups: groups.length,
  categories: groups.reduce((n, g) => n + g.categories.length, 0),
  suppliers: new Set(products.map((p) => p.supplier).filter(Boolean)).size,
};

// "1293" -> "1 250+" jellegű kerekített kijelzés
export function roundedCount(n, step = 50) {
  return `${(Math.floor(n / step) * step).toLocaleString('hu-HU')}+`;
}
