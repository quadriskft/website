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

// Más fülön történt változás átvétele
window.addEventListener('storage', (e) => {
  if (e.key === KEY) {
    const items = read();
    listeners.forEach((fn) => fn(items));
    window.dispatchEvent(new CustomEvent('quote:change', { detail: items }));
  }
});
