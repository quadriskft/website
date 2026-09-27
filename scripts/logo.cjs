// Logó generálása: npm run logo
// Szöveges logó (Russo One betűkből, görbékké alakítva). A betűkön átfutó vízszintes
// horony az alumínium felépítmény-profilokat idézi. Kimenet: public/brand/ és public/favicon.svg
const opentype = require('opentype.js');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'public/brand');
const RUSSO = opentype.loadSync(path.join(ROOT, 'node_modules/@fontsource/russo-one/files/russo-one-latin-400-normal.woff'));
const SAIRA = opentype.loadSync(path.join(ROOT, 'node_modules/@fontsource/saira/files/saira-latin-700-normal.woff'));

function word(font, text, size, x, y, spacing) {
  let d = '';
  let cx = x;
  for (const ch of text) {
    const g = font.charToGlyph(ch);
    d += g.getPath(cx, y, size).toPathData(2);
    cx += (g.advanceWidth * size) / font.unitsPerEm + spacing;
  }
  return { d, width: cx - spacing - x };
}

const SIZE = 100;
const BASE = 100; // alapvonal
const CAP = (RUSSO.tables.os2.sCapHeight || 700) * SIZE / RUSSO.unitsPerEm; // nagybetű magasság
const main = word(RUSSO, 'QUADRIS', SIZE, 0, BASE, 5);
const W = main.width;
// horony a nagybetűk 58%-ánál
const grooveY = BASE - CAP * 0.42;
const grooveH = CAP * 0.085;

function tagline() {
  const text = 'FELÉPÍTMÉNY ALKATRÉSZEK';
  const size = 17;
  const probe = word(SAIRA, text, size, 0, 0, 0);
  const letters = [...text].length;
  const spacing = (W - probe.width) / (letters - 1);
  return word(SAIRA, text, size, 0, BASE + 34, spacing);
}

const colors = {
  color: { fill: 'url(#qg)', sub: '#5b7089', defs: '<linearGradient id="qg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0b3a8c"/><stop offset="1" stop-color="#0a7cff"/></linearGradient>' },
  white: { fill: '#ffffff', sub: '#b9cde6', defs: '' },
  dark: { fill: '#0b1f3a', sub: '#5b7089', defs: '' },
};

function logo(scheme, withTag) {
  const c = colors[scheme];
  const top = BASE - CAP - 4;
  const bottom = withTag ? BASE + 40 : BASE + 22; // a Q farka lelóg
  const mask = `<mask id="groove" maskUnits="userSpaceOnUse"><rect x="-10" y="${top - 10}" width="${W + 20}" height="${bottom - top + 20}" fill="#fff"/><rect x="-10" y="${grooveY.toFixed(1)}" width="${W + 20}" height="${grooveH.toFixed(1)}" fill="#000"/></mask>`;
  const tag = withTag ? `<path d="${tagline().d}" fill="${c.sub}"/>` : '';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 ${top.toFixed(1)} ${(W + 4).toFixed(1)} ${(bottom - top).toFixed(1)}" role="img" aria-label="Quadris Kft."><defs>${c.defs}${mask}</defs><path d="${main.d}" fill="${c.fill}" mask="url(#groove)"/>${tag}</svg>\n`;
}

fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) if (f.endsWith('.svg')) fs.unlinkSync(path.join(OUT, f));
fs.writeFileSync(path.join(OUT, 'quadris-logo.svg'), logo('color', true));
fs.writeFileSync(path.join(OUT, 'quadris-logo-feher.svg'), logo('white', true));
fs.writeFileSync(path.join(OUT, 'quadris-logo-sotet.svg'), logo('dark', true));
fs.writeFileSync(path.join(OUT, 'quadris-felirat.svg'), logo('color', false));
fs.writeFileSync(path.join(OUT, 'quadris-felirat-feher.svg'), logo('white', false));

// ikon: "Q" betű kék lekerekített négyzetben, ugyanazzal a horonnyal
const q = word(RUSSO, 'Q', 76, 0, 0, 0);
const qx = (100 - q.width) / 2;
const qPath = word(RUSSO, 'Q', 76, qx, 78, 0).d;
const qCap = (RUSSO.tables.os2.sCapHeight || 700) * 76 / RUSSO.unitsPerEm;
const icon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="ig" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b3a8c"/><stop offset="1" stop-color="#0a7cff"/></linearGradient><mask id="ig2" maskUnits="userSpaceOnUse"><rect width="100" height="100" fill="#fff"/><rect x="0" y="${(78 - qCap * 0.42).toFixed(1)}" width="100" height="${(qCap * 0.09).toFixed(1)}" fill="#000"/></mask></defs><rect width="100" height="100" rx="22" fill="url(#ig)"/><path d="${qPath}" fill="#fff" mask="url(#ig2)"/></svg>\n`;
fs.writeFileSync(path.join(OUT, 'quadris-ikon.svg'), icon);
fs.writeFileSync(path.join(ROOT, 'public/favicon.svg'), icon);
console.log('Logók elkészültek:', fs.readdirSync(OUT).join(', '));
