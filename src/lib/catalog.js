import { existsSync } from 'node:fs';
import catalog from '../data/catalog.json';
import extra from '../data/termekadatok.json';
import extended from '../data/bovitett.json';
import deleted from '../../data/torolt_termekek.json';
import fixes from '../../data/termek_javitasok.json';
import families from '../../data/termek_csaladok.json';

// FONTOS: a termékadatokban lévő beszállító (supplier, supplierCode, source…) belső adat,
// a weboldalon soha nem jelenik meg.

// Az Excelből jövő alapadatok kiegészítése a beszállítói oldalakról letöltött
// képekkel és műszaki adatokkal (scripts/termekadatok/).
const excelProducts = catalog.products.map((p) => {
  const e = extra[p.slug];
  // áthelyezés: kézi javítás („move”: {group, category}) vagy a bővített kínálat átsorolása
  const move = fixes[p.slug]?.move ?? extended.moves?.[p.slug];
  const out = move ? { ...p, group: move.group, category: move.category } : p;
  const merged = !e ? out : {
    ...out,
    images: e.images?.length ? e.images : p.images,
    specs: { ...(e.specs ?? {}), ...p.specs },
    description: p.description || e.description || '',
  };
  // kézi javítások (data/termek_javitasok.json): név, (gyártói) cikkszám, műszaki adat
  const f = fixes[p.slug];
  return f ? { ...merged, ...(f.name ? { name: f.name } : {}), ...(f.code ? { code: f.code } : {}), ...(f.codeLabel ? { codeLabel: f.codeLabel } : {}),
    ...(f.orderNote ? { orderNote: f.orderNote } : {}), specs: withoutNull({ ...merged.specs, ...(f.specs ?? {}) }) } : merged;
});

// A beszállítók teljes kínálatából felvett további termékek (scripts/termekadatok/teljes_kinalat.py)
const extendedProducts = (extended.products ?? []).map((p) => {
  const out = {
    slug: p.slug, code: p.code, name: p.name, group: p.group, category: p.category,
    specs: p.specs ?? {}, images: p.images ?? [], description: p.description ?? '', documents: [], supplier: p.source,
    // a G&C teljes kínálatából felvett termékek kódja a gyártói cikkszám, a színe a névből / kódból (ZW = fekete)
    ...(p.source === 'G&C termékek' ? { codeLabel: 'Gyártói cikkszám', specs: { ...(gncColor(p) ? { Szín: gncColor(p) } : {}), ...(p.specs ?? {}) } } : {}),
  };
  // ha egy letöltő szkript képeket / adatokat adott hozzá (termekadatok.json), és a kézi javítások
  const e = extra[p.slug];
  const merged = e ? { ...out, images: e.images?.length ? e.images : out.images, specs: { ...out.specs, ...(e.specs ?? {}) } } : out;
  const f = fixes[p.slug];
  return f ? { ...merged, ...(f.name ? { name: f.name } : {}), ...(f.code ? { code: f.code } : {}),
    ...(f.orderNote ? { orderNote: f.orderNote } : {}), specs: withoutNull({ ...merged.specs, ...(f.specs ?? {}) }) } : merged;
});

// kézi javításban a null értékű műszaki adat törlendő (pl. a darabra adott termék gyári szálhossza)
function withoutNull(specs) {
  return Object.fromEntries(Object.entries(specs).filter(([, v]) => v !== null));
}

function gncColor(p) {
  const s = `${p.name} ${p.code ?? ''}`.toLowerCase();
  if (/fekete|-zw\b|\bzw\b/.test(s)) return 'fekete';
  if (/fehér/.test(s)) return 'fehér';
  if (/szürke/.test(s)) return 'szürke';
  return null;
}

// Egy cikkszám több kivitelben (pl. bal / jobb), a családban „clone”: a hiányzó tagok az első tag másolatai,
// saját képekkel / adatokkal (termekadatok.json a tag slugjával)
const cloneProducts = Object.entries(families).filter(([id, f]) => !id.startsWith('_') && f.clone).flatMap(([, f]) => {
  const [baseSlug, ...rest] = Object.keys(f.members);
  const base = [...excelProducts, ...extendedProducts].find((p) => p.slug === baseSlug);
  if (!base) return [];
  return rest.map((slug) => ({ ...base, slug, images: extra[slug]?.images ?? base.images, specs: { ...base.specs, ...(extra[slug]?.specs ?? {}) } }));
});

// A Quadris által törlésre jelölt termékek (data/torolt_termekek.json) sehol nem jelennek meg
export const products = [...excelProducts, ...extendedProducts, ...cloneProducts].filter((p) => !deleted[p.slug]);

// Alkategóriák átnevezése (a Quadris kérésére a gyártó saját írásmódja szerint)
const CATEGORY_RENAMES = { versus: 'Versus-Omega' };
// Gyártói alkategóriák logója (a gyártó honlapjáról): a címben a név elé / helyett jelenik meg
export const CATEGORY_LOGOS = {
  versus: { src: '/logok/versus-omega.svg', alt: 'Versus-Omega', text: true },
  edscha: { src: '/logok/edscha.png', alt: 'Edscha Trailer Systems', text: false },
};

// Főcsoport logója (a gyártó weboldaláról): a csoport oldalának fejlécében és a katalógus csoportkártyáján
export const GROUP_LOGOS = {
  'szellozes-tetoablakok-vilagitas': { src: '/logok/gnc-systems.png', alt: 'G&C Systems' },
};

// Csoportok és kategóriák: Excel + új csoportok/kategóriák, darabszámok újraszámolva, üresek elhagyva
const groupList = catalog.groups.map((g) => ({
  slug: g.slug,
  name: extended.renameGroups?.[g.slug] ?? g.name,
  categories: g.categories.map((c) => ({ slug: c.slug, name: CATEGORY_RENAMES[c.slug] ?? c.name })),
}));
for (const g of extended.groups ?? []) {
  groupList.push({ slug: g.slug, name: g.name, categories: [] });
}
for (const c of extended.categories ?? []) {
  const g = groupList.find((x) => x.slug === c.group);
  if (g && !g.categories.some((x) => x.slug === c.slug)) g.categories.push({ slug: c.slug, name: c.name });
}
// Egész alkategória megjelenítése egy másik csoportban is (a termékek a helyükön maradnak):
// [forrás "csoport/alkategória", cél "csoport/alkategória", amely alkategória után kerüljön]
const CATEGORY_COPIES = [
  ['platos-alkatreszek-es-kiegeszitok/kotoelemek', 'aluminium-alvaz-profilok/kotoelemek', 'hossztartok'],
  // a ponyvarendszer-profilok a platós és ponyvás oldalfal profilok között is, a billencs oldalfalak előtt
  ['ponyvarendszer-kiegeszitok/ponyvacsovek', 'ponyvas-oldalfal-profilok-es-szegok/ponyvacsovek', 'szego-profilok'],
  ['ponyvarendszer-kiegeszitok/spitzprofilok', 'ponyvas-oldalfal-profilok-es-szegok/spitzprofilok', 'ponyvacsovek'],
  ['ponyvarendszer-kiegeszitok/ponyvatarto-zartszelvenyek', 'ponyvas-oldalfal-profilok-es-szegok/ponyvatarto-zartszelvenyek', 'spitzprofilok'],
  ['ponyvarendszer-kiegeszitok/spanner-profil', 'ponyvas-oldalfal-profilok-es-szegok/spanner-profil', 'ponyvatarto-zartszelvenyek'],
];
for (const [from, to, after] of CATEGORY_COPIES) {
  const [fg, fc] = from.split('/'), [tg, tc] = to.split('/');
  const src = groupList.find((x) => x.slug === fg)?.categories.find((c) => c.slug === fc);
  const g = groupList.find((x) => x.slug === tg);
  if (!src || !g || g.categories.some((c) => c.slug === tc)) continue;
  const j = g.categories.findIndex((c) => c.slug === after);
  g.categories.splice(j < 0 ? g.categories.length : j + 1, 0, { slug: tc, name: src.name });
}
// Alkategóriák kézi sorrendje (a Quadris kérése szerint): [alkategória, amely után kerüljön]; a többi marad
const CATEGORY_MOVES = {
  'platos-alkatreszek-es-kiegeszitok': [['fellepo', 'z-zarak']],
  'acel-es-alu-rakoncak-es-szegok': [['dg', null]],  // null = a végére
};
for (const g of groupList) {
  for (const [slug, after] of CATEGORY_MOVES[g.slug] ?? []) {
    const i = g.categories.findIndex((c) => c.slug === slug);
    if (i < 0) continue;
    const [c] = g.categories.splice(i, 1);
    const j = after ? g.categories.findIndex((x) => x.slug === after) : -1;
    g.categories.splice(j < 0 ? g.categories.length : j + 1, 0, c);
  }
}
// Termékcsaládok (data/termek_csaladok.json): azonos profil több gyári hosszban – a listákban egy kártya
// (az első tag, a család nevével), a termékoldalon hosszválasztó; darabra rendelhető, nem méretre vágva
const familyBySlug = new Map();
for (const [id, f] of Object.entries(families)) {
  if (id.startsWith('_')) continue;
  const members = Object.entries(f.members).map(([slug, value]) => ({ slug, value })).filter((m) => !deleted[m.slug]);
  const fam = { id, name: f.name, label: f.label ?? 'Méret', title: f.title, note: f.note, clone: !!f.clone, members, leader: members[0]?.slug };
  for (const m of members) familyBySlug.set(m.slug, fam);
}
export function familyOf(slug) {
  return familyBySlug.get(slug) ?? null;
}
const hiddenMember = (p) => { const f = familyBySlug.get(p.slug); return f && f.leader !== p.slug; };

// kézi javításban („alsoIn”: ["csoport/alkategória", …]) a termék a saját helye mellett ezekben is megjelenik
const alsoIn = (p) => [
  ...(fixes[p.slug]?.alsoIn ?? []),
  ...CATEGORY_COPIES.filter(([from]) => from === `${p.group}/${p.category}`).map(([, to]) => to),
];
const inPlace = (p, groupSlug, categorySlug) =>
  (p.group === groupSlug && (!categorySlug || p.category === categorySlug)) ||
  alsoIn(p).some((k) => (categorySlug ? k === `${groupSlug}/${categorySlug}` : k.startsWith(`${groupSlug}/`)));

const counts = new Map();
for (const p of products.filter((x) => !hiddenMember(x))) {
  for (const k of [`${p.group}/${p.category}`, ...alsoIn(p)]) counts.set(k, (counts.get(k) ?? 0) + 1);
}
// A termékcsoportok sorrendje (a Quadris kérése szerint); a listában nem szereplők utánuk, ABC sorrendben
const GROUP_ORDER = [
  'aluminium-lemezek', 'ipari-felgyartmanyok', 'aluminium-alvaz-profilok', 'aluminium-padlo-profilok',
  'ponyvas-oldalfal-profilok-es-szegok', 'elhuzhato-roloponyvas-rendszer', 'hatso-ajtok-es-athajto-rampak', 'italszallito-kit',
  'zart-dobozos-es-hutos-profilok', 'acel-profilok', 'platos-alkatreszek-es-kiegeszitok', 'ponyvarendszer-kiegeszitok',
  'acel-es-alu-rakoncak-es-szegok', 'dobozos-felepitmeny-alkatreszek', 'rakomanyrogzites', 'sarvedok-szerszamosladak',
  'kedergumik', 'csuszasmentes-retegelt-padlo', 'gumiszonyegek', 'szellozes-tetoablakok-vilagitas', 'specialis-felepitmeny-alkatreszek',
  'uvegszalas-polieszter',
  'billencs-alkatreszek',
];
const groupRank = (slug) => (GROUP_ORDER.includes(slug) ? GROUP_ORDER.indexOf(slug) : GROUP_ORDER.length);

export const groups = groupList
  .map((g) => {
    const categories = g.categories
      .map((c) => ({ ...c, count: counts.get(`${g.slug}/${c.slug}`) ?? 0 }))
      .filter((c) => c.count > 0);
    return { ...g, categories, count: categories.reduce((n, c) => n + c.count, 0) };
  })
  .filter((g) => g.count > 0)
  .sort((a, b) => groupRank(a.slug) - groupRank(b.slug) || a.name.localeCompare(b.name, 'hu'));

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
  const list = products
    .filter((p) => inPlace(p, groupSlug, categorySlug) && !hiddenMember(p))
    .map((p) => (familyBySlug.has(p.slug) ? { ...p, name: familyBySlug.get(p.slug).name, family: true } : p));
  // kézi sorrend (data/termek_javitasok.json „order”): ezek elöl, a megadott sorrendben; a többi az eredeti sorrendben
  const rank = (p) => fixes[p.slug]?.order ?? Infinity;
  const bySize = SIZE_SORTED.has(groupSlug) || SIZE_SORTED.has(`${groupSlug}/${categorySlug}`);
  const sorted = list
    .map((p, i) => [p, i])
    .sort((a, b) => rank(a[0]) - rank(b[0]) || (bySize && compareSizes(a[0].name, b[0].name)) || a[1] - b[1])
    .map(([p]) => p);
  // kézi javításban „after”: a termék a megadott termék (slug) után áll (több ilyen: a javítások sorrendjében)
  for (const [slug, f] of Object.entries(fixes)) {
    if (!f.after) continue;
    const i = sorted.findIndex((p) => p.slug === slug);
    if (i < 0 || !sorted.some((p) => p.slug === f.after)) continue;
    const [item] = sorted.splice(i, 1);
    let j = sorted.findIndex((p) => p.slug === f.after);
    while (j + 1 < sorted.length && fixes[sorted[j + 1].slug]?.after === f.after) j++;  // a már odatettek mögé
    sorted.splice(j + 1, 0, item);
  }
  return sorted;
}

// Ezekben a főkategóriákban / alkategóriákban a termékek a névben szereplő méret szerint növekvő sorrendben állnak
// (első méret, egyezésnél a második, harmadik …; pl. 20x20x3 < 25x25x2 < 30x20x1,5 < 30x20x2).
const SIZE_SORTED = new Set(['ipari-felgyartmanyok', 'ponyvarendszer-kiegeszitok/ponyvacsovek']);

function sizesOf(name) {
  const m = name.match(/\d+(?:[.,]\d+)?(?:\s*x\s*\d+(?:[.,]\d+)?)*/i);
  return m ? m[0].split(/\s*x\s*/i).map((n) => parseFloat(n.replace(',', '.'))) : [];
}

function compareSizes(a, b) {
  const x = sizesOf(a);
  const y = sizesOf(b);
  if (!x.length || !y.length) return y.length - x.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    const d = (x[i] ?? -1) - (y[i] ?? -1);
    if (d) return d;
  }
  return 0;
}

// Főkategória kép (scripts/csoportkepek.py állítja elő); ha nincs (a Quadris újat küld), null -> ikonos helykitöltő
export function groupImage(slug) {
  return existsSync(`${process.cwd()}/public/csoportkepek/${slug}.webp`) ? `/csoportkepek/${slug}.webp` : null;
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
// darabra (gyári hosszban) adott termékek: nem kapnak méretre vágós rendelőlapot (a Quadris kérése)
// – az alumínium sarokoszlopok is, kivéve a méretre vágva adott profilokat (a slug eleje = a Quadris-cikkszám)
const CORNER_POST_CUT = ['6612225-', '6612226-', '66k0800-', '6639604-', '6639692-'];
const PIECE_ONLY = (p) => (['edscha', 'versus'].includes(p.category) && /kereszt?tartó/i.test(p.name))
  || (p.category === 'aluminium-sarok-oszlopok' && !CORNER_POST_CUT.some((c) => p.slug.startsWith(c)));
export function isProfile(p) {
  if (NO_PROFILE_GROUPS.has(p.group) || HARD_NO.test(p.name) || PIECE_ONLY(p)) return false;
  if (PROFILE_GROUPS.has(p.group) || /profil|hossztartó|kereszttartó|szelvény/i.test(p.name)) return true;
  if (SOFT_NO.test(p.name)) return false;
  return PROFILE_NAME.test(p.name);
}

// Böngészőnek küldhető termékadat (belső mezők nélkül)
export function publicProduct(p) {
  return { slug: p.slug, code: p.code, name: p.name, group: p.group, image: p.images?.[0] ?? '', ...(p.codeLabel ? { codeLabel: p.codeLabel } : {}),
    ...(p.family ? { variants: true } : isProfile(p) ? { profile: true } : {}) };
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
