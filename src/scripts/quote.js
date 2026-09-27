// Ajánlatkérő lista (kosár) – a böngészőben tárolva, szerver nélkül.
const KEY = 'quadris-ajanlatkero-v1';
const listeners = new Set();

function read() {
  try {
    const items = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    return Array.isArray(items) ? items : [];
  } catch {
    return [];
  }
}

let memory = null; // ha a localStorage nem elérhető (pl. privát mód)

function load() {
  return memory ?? read();
}

function save(items) {
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
    memory = null;
  } catch {
    memory = items;
  }
  listeners.forEach((fn) => fn(items));
  window.dispatchEvent(new CustomEvent('quote:change', { detail: items }));
}

export const quote = {
  items: load,
  count: () => load().length,
  has: (slug) => load().some((i) => i.slug === slug),
  add(product, qty = 1) {
    const items = load();
    const existing = items.find((i) => i.slug === product.slug);
    if (existing) existing.qty = clampQty(existing.qty + qty);
    else items.push({ ...product, qty: clampQty(qty), note: '' });
    save(items);
  },
  // Profil: hossz × darab méretsorok (cuts) és megjegyzés; ugyanazon hossz darabszáma összeadódik
  addCuts(product, cuts, note = '') {
    const clean = normalizeCuts(cuts);
    if (!clean.length) return;
    const items = load();
    let item = items.find((i) => i.slug === product.slug);
    if (!item) {
      item = { ...product, qty: 0, note: '', cuts: [] };
      items.push(item);
    }
    item.cuts = normalizeCuts([...(item.cuts ?? []), ...clean]);
    item.qty = totalPcs(item.cuts);
    const n = String(note ?? '').trim();
    if (n) item.note = (item.note ? `${item.note}; ${n}` : n).slice(0, 300);
    save(items);
  },
  addCustom(name, qty = 1, note = '') {
    const items = load();
    items.push({ slug: `egyedi-${Date.now()}`, custom: true, name, code: '', qty: clampQty(qty), note });
    save(items);
  },
  update(slug, changes) {
    const items = load();
    const item = items.find((i) => i.slug === slug);
    if (!item) return;
    Object.assign(item, changes);
    if ('cuts' in changes) {
      item.cuts = normalizeCuts(item.cuts);
      if (item.cuts.length) item.qty = totalPcs(item.cuts);
      else delete item.cuts;
    }
    if ('qty' in changes) item.qty = clampQty(item.qty);
    save(items);
  },
  remove(slug) {
    save(load().filter((i) => i.slug !== slug));
  },
  clear() {
    save([]);
  },
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};

export function clampQty(value) {
  const n = Math.round(Number(value));
  return Number.isFinite(n) ? Math.min(Math.max(n, 1), 99999) : 1;
}

export function clampLen(value) {
  const n = Math.round(Number(String(value).replace(',', '.')));
  return Number.isFinite(n) && n >= 1 ? Math.min(n, 30000) : 0;
}

// Érvényes sorok; az azonos hosszúságú sorok darabszáma összevonva, hossz szerint csökkenő sorrendben
export function normalizeCuts(cuts) {
  const map = new Map();
  for (const c of Array.isArray(cuts) ? cuts : []) {
    const len = clampLen(c?.len);
    if (!len) continue;
    map.set(len, (map.get(len) ?? 0) + clampQty(c?.pcs));
  }
  return [...map].sort((a, b) => b[0] - a[0]).slice(0, 50).map(([len, pcs]) => ({ len, pcs: Math.min(pcs, 99999) }));
}

export const totalPcs = (cuts) => (cuts ?? []).reduce((n, c) => n + c.pcs, 0);

// "3 db × 6000 mm, 2 db × 2500 mm"
export const cutsText = (cuts) => (cuts ?? []).map((c) => `${c.pcs} db × ${c.len.toLocaleString('hu-HU')} mm`).join(', ');

// Más fülön történt változás átvétele
window.addEventListener('storage', (e) => {
  if (e.key === KEY) {
    const items = read();
    listeners.forEach((fn) => fn(items));
    window.dispatchEvent(new CustomEvent('quote:change', { detail: items }));
  }
});
