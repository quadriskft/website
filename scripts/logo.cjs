// Logó generálása: npm run logo
// QUADRIS: kék Q (farka az alvázba fut), fémes csiszolt UADRIS betűk, kék alváz, 3 kerék.
// Vektoros, a betűk (Russo One) görbékké alakítva.
const opentype = require('opentype.js');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'public/brand');
const R1 = opentype.loadSync(path.join(ROOT, 'node_modules/@fontsource/russo-one/files/russo-one-latin-400-normal.woff'));
const f = (n) => n.toFixed(1);
// betűk vízszintesen szélesítve
function word(text, size, x, y, sp, sx) {
  let d = '', cx = x;
  for (const ch of text) {
    const g = R1.charToGlyph(ch);
    const p = g.getPath(0, 0, size);
    for (const c of p.commands) { for (const k of ['x', 'x1', 'x2']) if (c[k] !== undefined) c[k] = c[k] * sx + cx; for (const k of ['y', 'y1', 'y2']) if (c[k] !== undefined) c[k] = c[k] + y; }
    d += p.toPathData(2);
    cx += g.advanceWidth * size / R1.unitsPerEm * sx + sp;
  }
  return { d, w: cx - sp - x };
}
const SIZE = 120, CAP = R1.tables.os2.sCapHeight * SIZE / R1.unitsPerEm; // ~84
const BASE = 120, TOP = BASE - CAP;
// Q: lekerekített négyzet gyűrű + átlós farok
const qx = 10, qw = CAP * 0.98, qh = CAP, t = CAP * 0.25, r = CAP * 0.22;
const rr = (x, y, w, h, r) => `M${f(x + r)},${f(y)}H${f(x + w - r)}Q${f(x + w)},${f(y)} ${f(x + w)},${f(y + r)}V${f(y + h - r)}Q${f(x + w)},${f(y + h)} ${f(x + w - r)},${f(y + h)}H${f(x + r)}Q${f(x)},${f(y + h)} ${f(x)},${f(y + h - r)}V${f(y + r)}Q${f(x)},${f(y)} ${f(x + r)},${f(y)}Z`;
const qOuter = rr(qx, TOP, qw, qh, r), qInner = rr(qx + t, TOP + t, qw - 2 * t, qh - 2 * t, r * 0.45);
const letters = word('UADRIS', SIZE, qx + qw + 6, BASE, 3, 1.04);
const W = letters.w + qx + qw + 6 + 10;
// alváz sáv
const barY = BASE + 10, barH = 9, barX0 = qx + qw * 0.62, barX1 = W - 6;
// Q farka: a belső jobb alsó sarokból le a sávig
const tail = `M${f(qx + qw * 0.46)},${f(TOP + qh * 0.52)}L${f(qx + qw * 0.72)},${f(TOP + qh * 0.52)}L${f(barX0 + 26)},${f(barY + barH)}L${f(barX0)},${f(barY + barH)}Z`;
function wheel(cx, cy, R, id) {
  let s = `<g filter="url(#wsh)">`;
  s += `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(R)}" fill="url(#tire)"/>`;
  s += `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(R * 0.86)}" fill="none" stroke="#2b3139" stroke-width="${f(R * 0.06)}"/>`;
  s += `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(R * 0.6)}" fill="url(#rim)" stroke="#6c7682" stroke-width="0.8"/>`;
  s += `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(R * 0.42)}" fill="none" stroke="#8a95a2" stroke-width="1"/>`;
  for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; s += `<circle cx="${f(cx + Math.cos(a) * R * 0.32)}" cy="${f(cy + Math.sin(a) * R * 0.32)}" r="${f(R * 0.045)}" fill="#3a424c"/>`; }
  s += `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(R * 0.2)}" fill="url(#hub)" stroke="#4b545f" stroke-width="0.8"/>`;
  s += `<ellipse cx="${f(cx - R * 0.25)}" cy="${f(cy - R * 0.35)}" rx="${f(R * 0.35)}" ry="${f(R * 0.14)}" fill="#fff" opacity="0.18" transform="rotate(-30 ${f(cx - R * 0.25)} ${f(cy - R * 0.35)})"/>`;
  return s + '</g>';
}
const WR = 20, WY = barY + barH * 0.5 + 9;
const wheels = wheel(qx + qw * 0.45, WY, WR) + wheel(W - 118, WY, WR) + wheel(W - 64, WY, WR);
const defs = `<defs>
 <linearGradient id="metal" x1="0" y1="${f(TOP)}" x2="0" y2="${f(BASE)}" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#ffffff"/><stop offset="0.22" stop-color="#eef1f5"/><stop offset="0.48" stop-color="#b9c0c9"/>
  <stop offset="0.52" stop-color="#8e97a2"/><stop offset="0.62" stop-color="#d7dce2"/><stop offset="0.85" stop-color="#f4f6f8"/><stop offset="1" stop-color="#aab2bc"/>
 </linearGradient>
 <pattern id="brush" width="4" height="3.2" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#6c7682" opacity="0.28"/></pattern>
 <linearGradient id="blueQ" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3a9bff"/><stop offset="0.55" stop-color="#1667e6"/><stop offset="1" stop-color="#0a3fb0"/></linearGradient>
 <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5fb0ff"/><stop offset="0.45" stop-color="#1a78ff"/><stop offset="1" stop-color="#0b46c4"/></linearGradient>
 <radialGradient id="tire" cx="0.4" cy="0.35" r="0.75"><stop offset="0" stop-color="#4a525d"/><stop offset="0.7" stop-color="#1d2229"/><stop offset="1" stop-color="#0b0e12"/></radialGradient>
 <radialGradient id="rim" cx="0.38" cy="0.32" r="0.8"><stop offset="0" stop-color="#ffffff"/><stop offset="0.5" stop-color="#cfd6de"/><stop offset="1" stop-color="#7d8894"/></radialGradient>
 <radialGradient id="hub" cx="0.4" cy="0.35" r="0.8"><stop offset="0" stop-color="#f6f8fa"/><stop offset="1" stop-color="#8793a0"/></radialGradient>
 <filter id="glow" x="-10%" y="-200%" width="120%" height="500%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <filter id="lsh" x="-5%" y="-10%" width="110%" height="130%"><feDropShadow dx="0" dy="3" stdDeviation="2.2" flood-color="#000" flood-opacity="0.45"/></filter>
 <filter id="wsh" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="2" stdDeviation="1.6" flood-color="#000" flood-opacity="0.5"/></filter>
 <clipPath id="lclip"><path d="${letters.d}"/></clipPath>
</defs>`;
const body = `
 <rect x="${f(barX0)}" y="${f(barY)}" width="${f(barX1 - barX0)}" height="${barH}" rx="3" fill="url(#bar)" filter="url(#glow)"/>
 <g filter="url(#lsh)">
  <path d="${qOuter}${qInner}" fill-rule="evenodd" fill="url(#blueQ)"/>
  <path d="${tail}" fill="url(#blueQ)"/>
  <path d="${qOuter}" fill="none" stroke="#9fd0ff" stroke-opacity="0.5" stroke-width="1.2"/>
  <path d="${letters.d}" fill="url(#metal)"/>
 </g>
 <g clip-path="url(#lclip)"><rect x="0" y="${f(TOP)}" width="${f(W)}" height="${f(CAP)}" fill="url(#brush)"/></g>
 <path d="${letters.d}" fill="none" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1"/>
 ${wheels}`;
const vbTop = TOP - 8, vbH = WY + WR + 8 - vbTop;
const svg = (bg) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 ${f(vbTop)} ${f(W + 4)} ${f(vbH)}" role="img" aria-label="Quadris Kft.">${defs}${bg ? `<rect x="0" y="${f(vbTop)}" width="${f(W + 4)}" height="${f(vbH)}" fill="#0b1733"/>` : ''}${body}</svg>\n`;
fs.mkdirSync(OUT, { recursive: true });
for (const fl of fs.readdirSync(OUT)) if (fl.endsWith('.svg')) fs.unlinkSync(path.join(OUT, fl));
// átlátszó háttér (sötét felületre), és sötétkék hátterű változat (világos felületre)
fs.writeFileSync(path.join(OUT, 'quadris-logo.svg'), svg(false));
fs.writeFileSync(path.join(OUT, 'quadris-logo-hatterrel.svg'), svg(true));
// ikon: a kék Q sötétkék lekerekített négyzetben
const s = 100 / (qw + 24);
const icon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">${defs}<rect width="100" height="100" rx="22" fill="#0b1733"/><g transform="translate(${f(12 * s - qx * s)} ${f(50 - (TOP + qh / 2) * s)}) scale(${f(s)})"><path d="${qOuter}${qInner}" fill-rule="evenodd" fill="url(#blueQ)"/><path d="M${f(qx + qw * 0.46)},${f(TOP + qh * 0.52)}L${f(qx + qw * 0.72)},${f(TOP + qh * 0.52)}L${f(qx + qw * 1.02)},${f(TOP + qh * 1.08)}L${f(qx + qw * 0.76)},${f(TOP + qh * 1.08)}Z" fill="url(#blueQ)"/></g></svg>
`;
fs.writeFileSync(path.join(OUT, 'quadris-ikon.svg'), icon);
fs.writeFileSync(path.join(ROOT, 'public/favicon.svg'), icon);
console.log('Logók elkészültek:', fs.readdirSync(OUT).join(', '));
