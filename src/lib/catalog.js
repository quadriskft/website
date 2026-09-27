import catalog from '../data/catalog.json';
import extra from '../data/termekadatok.json';

// FONTOS: a termékadatokban lévő beszállító (supplier, supplierCode) belső adat,
// a weboldalon soha nem jelenik meg.

export const groups = catalog.groups;

// Az Excelből jövő alapadatok kiegészítése a beszállítói oldalakról letöltött
// képekkel és műszaki adatokkal (scripts/termekadatok/). A forrás adatai
// (sourceUrl, sourceTitle) belső adatok, nem kerülnek ki az oldalra.
export const products = catalog.products.map((p) => {
  const e = extra[p.slug];
  if (!e) return p;
  return {
    ...p,
    images: e.images?.length ? e.images : p.images,
    specs: { ...(e.specs ?? {}), ...p.specs },
    description: p.description || e.description || '',
  };
});

const groupsBySlug = new Map(groups.map((g) => [g.slug, g]));
const productsBySlug = new Map(products.map((p) => [p.slug, p]));

// Csoportonkénti ikon (Lucide) és rövid leírás
export const GROUP_META = {
  'aluminium-alvaz-profilok': { icon: 'Frame', text: 'Hossz- és kereszttartók, keretprofilok, aláfutásgátló profilok alumínium alvázakhoz.' },
  'acel-profilok': { icon: 'Construction', text: 'Acél hossztartók, keretek és oldalfalak nagy terhelésű felépítményekhez.' },
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
  'gumiszonyegek': { icon: 'Grid3x3', text: 'Istálló-, rámpa-, soft és általános gumiszőnyegek, víztiszta PVC.' },
  'kedergumik': { icon: 'Spline', text: 'Kéder- és tömítőgumi profilok felépítményekhez.' },
  'uvegszalas-polieszter': { icon: 'Sheet', text: 'Üvegszálas poliészter (GFK) lemezek és panelek.' },
  'specialis-felepitmeny-alkatreszek': { icon: 'Cog', text: 'Speciális zárak, szerelvények és egyedi felépítmény alkatrészek.' },
  'italszallito-kit': { icon: 'Wine', text: 'Komplett alkatrészkészlet italszállító felépítményekhez.' },
  'billencs-alkatreszek': { icon: 'Forklift', text: 'Munkahengerek, bölcsők, kardánok, billencs rakoncák és vezérlés.' },
};

// Lószállító felépítmény gyártóknak kiemelt kategóriák: [csoport, kategória, felirat]
export const HORSE_SECTIONS = [
  ['gumiszonyegek', 'istallo-szonyeg', 'Istálló szőnyegek'],
  ['gumiszonyegek', 'rampa-szonyeg', 'Rámpa szőnyegek'],
  ['gumiszonyegek', 'soft-gumi', 'Soft gumi lapok'],
  ['aluminium-padlo-profilok', 'rampa-profilok', 'Rámpa profilok'],
  ['hatso-ajtok-es-athajto-rampak', 'athajtorampa', 'Áthajtó rámpák'],
  ['specialis-felepitmeny-alkatreszek', 'g-c-termekek', 'Tetőventilátorok, tetőablakok, világítás'],
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

export function groupIcon(slug) {
  return GROUP_META[slug]?.icon ?? 'Package';
}

export function productTitle(p) {
  return p.code ? `${p.code} ${p.name}` : p.name;
}

// Böngészőnek küldhető termékadat (belső mezők nélkül)
export function publicProduct(p) {
  return { slug: p.slug, code: p.code, name: p.name, group: p.group, image: p.images?.[0] ?? '' };
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
