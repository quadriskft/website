// Kereső: a katalógus index egyszeri letöltése és ékezetfüggetlen keresés.
let indexPromise = null;

export function normalize(text) {
  return (text ?? '')
    .toString()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[„”"]/g, '');
}

export function loadIndex() {
  indexPromise ??= fetch('/kereso-index.json')
    .then((r) => r.json())
    .then((data) => {
      const groups = new Map(data.groups.map((g) => [g.slug, g.name]));
      return data.products.map((p) => ({
        ...p,
        groupName: groups.get(p.group) ?? '',
        haystack: normalize(`${p.code} ${p.name} ${p.categoryName} ${groups.get(p.group) ?? ''}`),
      }));
    })
    .catch((err) => {
      indexPromise = null;
      throw err;
    });
  return indexPromise;
}

export function search(index, query, limit = Infinity) {
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  if (!terms.length) return [];
  const results = [];
  for (const p of index) {
    if (!terms.every((t) => p.haystack.includes(t))) continue;
    // Pontszám: cikkszám egyezés > név eleje > egyéb
    const code = normalize(p.code);
    const name = normalize(p.name);
    let score = 0;
    for (const t of terms) {
      if (code === t) score += 100;
      else if (code.startsWith(t)) score += 40;
      if (name.startsWith(t)) score += 20;
      else if (name.includes(t)) score += 10;
    }
    results.push({ p, score });
  }
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, limit).map((r) => r.p);
}
