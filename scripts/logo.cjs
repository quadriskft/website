// Logó generálása: npm run logo
// A QUADRIS felirat egy teherautó felépítményének oldalán áll, a Q betű kerék.
// A betűk (Russo One) görbékké alakítva, így a logó bárhol ugyanúgy jelenik meg.
const opentype = require('opentype.js');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'public/brand');
const R1 = opentype.loadSync(path.join(ROOT, 'node_modules/@fontsource/russo-one/files/russo-one-latin-400-normal.woff'));
const SA = opentype.loadSync(path.join(ROOT, 'node_modules/@fontsource/saira/files/saira-latin-700-normal.woff'));
const f = (n) => n.toFixed(1);
function word(font, text, size, x, y, sp) { let d = '', cx = x; for (const ch of text) { const g = font.charToGlyph(ch); d += g.getPath(cx, y, size).toPathData(2); cx += g.advanceWidth * size / font.unitsPerEm + sp; } return { d, w: cx - sp - x }; }
const SIZE = 100, CAP = R1.tables.os2.sCapHeight * SIZE / R1.unitsPerEm;

const PAL = {
  color: { panel: '#f1f6fe', frame: '#0b3a8c', letters: 'url(#lg)', tire: '#0b1f3a', rim: '#d5e3f7', hub: '#0b1f3a', tail: '#0a6cff', cab: 'url(#cg)', glass: '#e3eeff', chassis: '#0b1f3a', sub: '#5b7089', light: '#ffb020' },
  white: { panel: 'rgba(255,255,255,0.08)', frame: '#ffffff', letters: '#ffffff', tire: '#ffffff', rim: '#0b1f3a', hub: '#ffffff', tail: '#5aa2ff', cab: '#ffffff', glass: '#0b1f3a', chassis: '#ffffff', sub: '#b9cde6', light: '#ffb020' },
};
const DEFS = '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0b3a8c"/><stop offset="1" stop-color="#0a7cff"/></linearGradient><linearGradient id="cg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a86ff"/><stop offset="1" stop-color="#0b3a8c"/></linearGradient></defs>';

function wheel(cx, cy, r, c, tail) {
  const t = r * 0.34;
  let s = `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(r - t / 2)}" fill="none" stroke="${c.tire}" stroke-width="${f(t)}"/>`;
  s += `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(r - t + 0.5)}" fill="${c.rim}"/>`;
  s += `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(r * 0.2)}" fill="${c.hub}"/>`;
  for (let i = 0; i < 6; i++) { const a = i * Math.PI / 3; s += `<circle cx="${f(cx + Math.cos(a) * r * 0.4)}" cy="${f(cy + Math.sin(a) * r * 0.4)}" r="${f(r * 0.06)}" fill="${c.hub}"/>`; }
  if (tail) {
    const a = Math.PI / 4, x1 = cx + Math.cos(a) * r * 0.62, y1 = cy + Math.sin(a) * r * 0.62, x2 = cx + Math.cos(a) * r * 1.34, y2 = cy + Math.sin(a) * r * 1.34;
    s += `<path d="M${f(x1)},${f(y1)}L${f(x2)},${f(y2)}" stroke="${c.tail}" stroke-width="${f(t * 0.9)}" stroke-linecap="square"/>`;
  }
  return s;
}

// type: 'box' (dobozos) vagy 'flat' (platós, oldalfalas)
function truck(scheme, type, withTag) {
  const c = PAL[scheme];
  const pad = 16, r = CAP / 2;
  const qcx = pad + r, base = 100, qcy = base - r;
  const letters = word(R1, 'UADRIS', SIZE, qcx + r + 7, base, 5);
  const bodyX1 = qcx + r + 7 + letters.w + pad;
  const top = base - CAP - pad, bottom = base + pad;
  let s = '';
  if (type === 'box') {
    s += `<rect x="0" y="${f(top)}" width="${f(bodyX1)}" height="${f(bottom - top)}" rx="9" fill="${c.panel}" stroke="${c.frame}" stroke-width="5.5"/>`;
    for (const k of [0.3, 0.7]) s += `<path d="M8,${f(top + (bottom - top) * k)}H${f(bodyX1 - 8)}" stroke="${c.frame}" stroke-opacity="0.14" stroke-width="3"/>`;
  } else {
    // platós: alsó oldalfal-sáv, hornyok, fejfal
    s += `<rect x="0" y="${f(top + 6)}" width="${f(bodyX1)}" height="${f(bottom - top - 6)}" rx="4" fill="${c.panel}" stroke="${c.frame}" stroke-width="5"/>`;
    for (const k of [0.33, 0.66]) s += `<path d="M6,${f(top + 6 + (bottom - top - 6) * k)}H${f(bodyX1 - 6)}" stroke="${c.frame}" stroke-opacity="0.18" stroke-width="3"/>`;
    s += `<rect x="${f(bodyX1 - 8)}" y="${f(top - 16)}" width="8" height="${f(bottom - top + 16)}" fill="${c.frame}"/>`;
    for (let i = 0; i < 4; i++) s += `<path d="M${f(bodyX1 - 8)},${f(top - 12 + i * 6)}h8" stroke="${c.panel}" stroke-width="1.5"/>`;
  }
  s += wheel(qcx, qcy, r, c, true);
  s += `<path d="${letters.d}" fill="${c.letters}"/>`;
  // fülke
  const cabX = bodyX1 + 6, cabW = CAP * 1.05, cTop = top + CAP * 0.22, cBot = bottom + 8;
  s += `<path d="M${f(cabX)},${f(cBot)}V${f(cTop + 8)}Q${f(cabX)},${f(cTop)} ${f(cabX + 8)},${f(cTop)}H${f(cabX + cabW * 0.5)}L${f(cabX + cabW * 0.9)},${f(cTop + CAP * 0.52)}L${f(cabX + cabW + 6)},${f(cTop + CAP * 0.62)}Q${f(cabX + cabW + 12)},${f(cTop + CAP * 0.66)} ${f(cabX + cabW + 12)},${f(cTop + CAP * 0.76)}V${f(cBot)}Z" fill="${c.cab}"/>`;
  s += `<path d="M${f(cabX + 12)},${f(cTop + 7)}H${f(cabX + cabW * 0.47)}L${f(cabX + cabW * 0.78)},${f(cTop + CAP * 0.46)}H${f(cabX + 12)}Z" fill="${c.glass}"/>`;
  s += `<rect x="${f(cabX + cabW + 4)}" y="${f(cTop + CAP * 0.8)}" width="8" height="6" rx="2" fill="${c.light}"/>`;
  // alváz és kerekek
  const chY = bottom + 3;
  s += `<rect x="-6" y="${f(chY)}" width="${f(cabX + cabW + 18)}" height="8" rx="4" fill="${c.chassis}"/>`;
  const wr = CAP * 0.36, wy = chY + 8 + wr * 0.55;
  s += wheel(bodyX1 * 0.2, wy, wr, c, false) + wheel(bodyX1 * 0.2 + wr * 2.15, wy, wr, c, false) + wheel(cabX + cabW * 0.55, wy, wr, c, false);
  let H = wy + wr + 6;
  if (withTag) {
    const tag = 'FELÉPÍTMÉNY ALKATRÉSZEK', size = 17;
    const probe = word(SA, tag, size, 0, 0, 0);
    const x0 = bodyX1 * 0.2 + wr * 3.4, x1 = cabX + cabW * 0.55 - wr * 1.25;
    const t = word(SA, tag, size, x0, wy + 6, (x1 - x0 - probe.w) / (tag.length - 1));
    s += `<path d="${t.d}" fill="${c.sub}"/>`;
  }
  const W = cabX + cabW + 22;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 ${f(top - 22)} ${f(W + 10)} ${f(H - top + 24)}" role="img" aria-label="Quadris Kft.">${DEFS}${s}</svg>\n`;
}
// Kimenetek
fs.mkdirSync(OUT, { recursive: true });
for (const fl of fs.readdirSync(OUT)) if (fl.endsWith('.svg')) fs.unlinkSync(path.join(OUT, fl));
fs.writeFileSync(path.join(OUT, 'quadris-logo.svg'), truck('color', 'box', true));
fs.writeFileSync(path.join(OUT, 'quadris-logo-feher.svg'), truck('white', 'box', true));
fs.writeFileSync(path.join(OUT, 'quadris-felirat.svg'), truck('color', 'box', false));
fs.writeFileSync(path.join(OUT, 'quadris-felirat-feher.svg'), truck('white', 'box', false));
// ikon: a Q-kerék kék lekerekített négyzetben
const icon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="ig" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a86ff"/><stop offset="1" stop-color="#0b3a8c"/></linearGradient></defs><rect width="100" height="100" rx="22" fill="url(#ig)"/>${wheel(47, 46, 30, { tire: '#ffffff', rim: '#0b3a8c', hub: '#ffffff', tail: '#7fc0ff' }, true)}</svg>
`;
fs.writeFileSync(path.join(OUT, 'quadris-ikon.svg'), icon);
fs.writeFileSync(path.join(ROOT, 'public/favicon.svg'), icon);
console.log('Logók elkészültek:', fs.readdirSync(OUT).join(', '));
