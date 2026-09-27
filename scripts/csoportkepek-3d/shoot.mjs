// Főkategória 3D renderek: a mappában `npm i three playwright`, `python3 -m http.server 4332`, majd `node shoot.mjs <csoport ...>` -> out/*.png, végül python3 scripts/csoportkepek.py scripts/csoportkepek-3d/out
import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const names = process.argv.slice(2);
for (const n of names) {
  const p = await b.newPage({ viewport: { width: 1200, height: 750 } });
  p.on('pageerror', (e) => console.log(n, 'ERR', e.message));
  p.on('console', (m) => m.type() === 'error' && console.log(n, 'console', m.text()));
  await p.goto(`http://localhost:4332/render.html?s=${n}`);
  try { await p.waitForFunction('window.DONE', null, { timeout: 60000 }); } catch { console.log(n, 'timeout'); }
  await p.locator('canvas').screenshot({ path: `out/${n}.png`, omitBackground: true });
  await p.close();
}
await b.close();
