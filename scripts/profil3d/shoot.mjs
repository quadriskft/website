// Profil 3D renderek: a mappában `npm i three playwright`, `python3 -m http.server 4333`,
// majd `node shoot.mjs profilok.json out` -> out/<slug>-1.png, out/<slug>-2.png
import { chromium } from 'playwright';
import fs from 'node:fs';
const [list, out] = process.argv.slice(2);
const items = JSON.parse(fs.readFileSync(list, 'utf8'));
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 1200, height: 900 } });
p.on('pageerror', (e) => console.log('ERR', e.message));
await p.goto('http://localhost:4333/render.html');
await p.waitForFunction('window.READY');
let n = 0;
for (const it of items) {
  if (++n % 15 === 0) { await p.reload(); await p.waitForFunction('window.READY'); }
  for (const v of [1, 2]) {
    const f = `${out}/${it.slug}-${v}.png`;
    if (fs.existsSync(f)) continue;
    const url = await p.evaluate(([it, v]) => window.render(it, v), [it, v]);
    const buf = Buffer.from(url.split(',')[1], 'base64');
    if (buf.length < 5000) { console.log('üres render:', it.slug, v); continue; }
    fs.writeFileSync(f, buf);
  }
}
await b.close();
console.log('kész', items.length);
