// Logó generálása: npm run logo  (a Michroma betűtípust görbékké alakítja, így a logó bárhol ugyanúgy jelenik meg)
const opentype = require('opentype.js');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const font = opentype.loadSync(ROOT + '/node_modules/@fontsource/michroma/files/michroma-latin-400-normal.woff');
const out = ROOT + '/public/brand/';

// Wordmark as paths (letter-spaced)
function word(text, size, x, y, spacing) {
  let d = '', cx = x;
  for (const ch of text) {
    const g = font.charToGlyph(ch);
    d += g.getPath(cx, y, size).toPathData(2);
    cx += g.advanceWidth * size / font.unitsPerEm + spacing;
  }
  return { d, width: cx - spacing - x };
}

// Emblem: four corner brackets (the "quad") forming a Q, with a diagonal tail.
// Drawn in a 64x64 box.
function emblem(stroke) {
  return `
  <g fill="none" stroke="${stroke}" stroke-width="7" stroke-linecap="butt" stroke-linejoin="miter">
    <path d="M4 26V4h22"/>
    <path d="M38 4h22v34"/>
    <path d="M4 38v22h34"/>
  </g>
  <path d="M32 32 L64 64" stroke="url(#qa)" stroke-width="8" stroke-linecap="butt"/>`;
}
const defs = `<defs><linearGradient id="qa" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3ee0ff"/><stop offset="1" stop-color="#2f6bff"/></linearGradient></defs>`;

function full(textColor, strokeColor, subColor) {
  const w = word('QUADRIS', 34, 84, 45, 6);
  const sub = word('FELÉPÍTMÉNY ALKATRÉSZEK', 9.2, 86, 62, 2.35);
  const width = Math.ceil(84 + Math.max(w.width, sub.width) + 4);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} 66" role="img" aria-label="Quadris Kft.">${defs}${emblem(strokeColor)}<path d="${w.d}" fill="${textColor}"/><path d="${sub.d}" fill="${subColor}"/></svg>\n`;
}
fs.writeFileSync(out + 'quadris-logo-light.svg', full('#ffffff', '#ffffff', '#8fb3d9'));
fs.writeFileSync(out + 'quadris-logo-dark.svg', full('#0b1726', '#0b1726', '#4a6380'));
const mark = (bg) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 -8 80 80">${defs}${bg ? '<rect x="-8" y="-8" width="80" height="80" rx="16" fill="#0b1726"/>' : ''}${emblem('#ffffff')}</svg>\n`;
fs.writeFileSync(out + 'quadris-jel.svg', mark(true));
fs.writeFileSync(ROOT + '/public/favicon.svg', mark(true));
