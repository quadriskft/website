// Quadris hero – valós idejű 3D platós felépítmény (three.js).
// A jármű alapja áll, a kamera lassan körbejárja, a felépítmény 7 alkatrészcsoportja
// sorban a helyére ereszkedik, majd a ciklus újraindul.
// Használat: QuadrisTruck.mount(canvas, { onStep(i) {} }) -> { dispose() }
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

const LOOP = 17;             // mp
const STEP0 = 1.2, STEP = 1.45, DROP = 0.9;
const HOLD_END = 13.6, LIFT = 1.1;
const ORBIT = 48;            // mp / teljes kör

function tex(w, h, draw, srgb) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
let s = 11; const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
const brushedTex = (base, spread) => tex(512, 4, (g, w, h) => { for (let x = 0; x < w; x++) { const v = base + (rnd() - 0.5) * spread; g.fillStyle = `rgb(${v},${v},${v})`; g.fillRect(x, 0, 1, h); } });
const ribTex = (n) => tex(8, 256, (g, w, h) => { const p = h / n; for (let i = 0; i < n; i++) { const gr = g.createLinearGradient(0, i * p, 0, (i + 1) * p); gr.addColorStop(0, '#000'); gr.addColorStop(0.12, '#fff'); gr.addColorStop(0.88, '#fff'); gr.addColorStop(1, '#000'); g.fillStyle = gr; g.fillRect(0, i * p, w, p); } });
const plyTex = () => tex(256, 256, (g) => { g.fillStyle = '#4b2f1c'; g.fillRect(0, 0, 256, 256); g.strokeStyle = 'rgba(0,0,0,0.25)'; g.lineWidth = 2; const r = 14, hh = Math.sqrt(3) * r; for (let row = -1; row < 12; row++) for (let col = -1; col < 13; col++) { const cx = col * 1.5 * r, cy = row * hh + (col % 2 ? hh / 2 : 0); g.beginPath(); for (let k = 0; k < 6; k++) { const a = Math.PI / 3 * k; g.lineTo(cx + r * 0.8 * Math.cos(a), cy + r * 0.8 * Math.sin(a)); } g.closePath(); g.stroke(); } }, true);

function materials() {
  const bAlu = brushedTex(90, 50); bAlu.repeat.set(3, 1);
  return {
    paint: () => new THREE.MeshPhysicalMaterial({ color: 0xf4f6f9, roughness: 0.32, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.06 }),
    glass: () => new THREE.MeshPhysicalMaterial({ color: 0x1d2733, roughness: 0.05, metalness: 0.2, clearcoat: 1, envMapIntensity: 1.6 }),
    black: () => new THREE.MeshPhysicalMaterial({ color: 0x1c1f24, roughness: 0.55, metalness: 0, clearcoat: 0.3 }),
    plastic: () => new THREE.MeshPhysicalMaterial({ color: 0x16181c, roughness: 0.42, metalness: 0, clearcoat: 0.5, clearcoatRoughness: 0.3 }),
    rubber: () => new THREE.MeshStandardMaterial({ color: 0x141518, roughness: 0.88 }),
    steel: () => new THREE.MeshPhysicalMaterial({ color: 0x2a2f36, roughness: 0.5, metalness: 0.7 }),
    rim: () => new THREE.MeshPhysicalMaterial({ color: 0xd9dde2, roughness: 0.22, metalness: 1 }),
    alu: () => new THREE.MeshPhysicalMaterial({ color: 0xd3d8de, roughness: 1, roughnessMap: bAlu, metalness: 1, envMapIntensity: 1.2 }),
    elox: (rib) => { const m = new THREE.MeshPhysicalMaterial({ color: 0xdfe3e8, roughness: 0.28, metalness: 1, clearcoat: 0.3, envMapIntensity: 1.25 }); if (rib) { m.bumpMap = ribTex(rib); m.bumpScale = 3; } return m; },
    ply: () => { const t = plyTex(); t.repeat.set(6, 2.4); return new THREE.MeshPhysicalMaterial({ map: t, roughness: 0.7, metalness: 0, clearcoat: 0.15 }); },
    light: (c) => new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: 1.4, roughness: 0.2 }),
    lens: () => new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.02, transmission: 0.6, thickness: 0.02, metalness: 0, clearcoat: 1 }),
  };
}

function mesh(geo, mat, x = 0, y = 0, z = 0) { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; return m; }
const RB = (x, y, z, r = 0.04, seg = 3) => new RoundedBoxGeometry(x, y, z, seg, r);

function wheel(M, dual) {
  const g = new THREE.Group();
  const w = dual ? 0.46 : 0.26, R = 0.43, r = 0.28;
  const pts = [];
  const hw = w / 2, rr = 0.06;
  pts.push(new THREE.Vector2(r, -hw));
  for (let i = 0; i <= 8; i++) { const a = -Math.PI / 2 + (i / 8) * (Math.PI / 2); pts.push(new THREE.Vector2(R - rr + Math.cos(a) * rr, -hw + rr + Math.sin(a) * rr)); }
  for (let i = 0; i <= 8; i++) { const a = (i / 8) * (Math.PI / 2); pts.push(new THREE.Vector2(R - rr + Math.cos(a) * rr, hw - rr + Math.sin(a) * rr)); }
  pts.push(new THREE.Vector2(r, hw));
  const tire = mesh(new THREE.LatheGeometry(pts, 64), M.rubber());
  tire.rotation.x = Math.PI / 2; g.add(tire);
  const rim = mesh(new THREE.CylinderGeometry(r, r, w * 0.9, 48), M.rim()); rim.rotation.x = Math.PI / 2; g.add(rim);
  const hub = mesh(new THREE.CylinderGeometry(0.11, 0.13, w * 0.95, 32), M.steel()); hub.rotation.x = Math.PI / 2; g.add(hub);
  for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2; const n = mesh(new THREE.CylinderGeometry(0.02, 0.02, w * 0.98, 10), M.rim(), Math.cos(a) * 0.16, Math.sin(a) * 0.16, 0); n.rotation.x = Math.PI / 2; g.add(n); }
  return g;
}

function buildBase(M) {
  const g = new THREE.Group();
  const H0 = 0.43; // kerék tengely magassága
  // alváz
  for (const z of [-0.46, 0.46]) g.add(mesh(RB(6.9, 0.22, 0.08, 0.015), M.steel(), -0.35, 0.78, z));
  for (const x of [-3.2, -2.2, -1.2, -0.2, 0.8]) g.add(mesh(new THREE.BoxGeometry(0.07, 0.14, 0.92), M.steel(), x, 0.8, 0));
  // kerekek
  for (const [x, dual] of [[2.35, false], [-1.95, true]]) for (const side of [-1, 1]) { const w = wheel(M, dual); w.position.set(x, H0, side * (dual ? 0.78 : 0.86)); g.add(w); }
  for (const x of [2.35, -1.95]) { const ax = mesh(new THREE.CylinderGeometry(0.06, 0.06, 1.6, 12), M.steel(), x, H0, 0); ax.rotation.x = Math.PI / 2; g.add(ax); }
  // fülke
  const cab = new THREE.Group(); cab.position.set(2.55, 0, 0); g.add(cab);
  cab.add(mesh(RB(1.55, 1.25, 2.02, 0.16, 5), M.paint(), 0.05, 1.5, 0));            // alsó test
  cab.add(mesh(RB(1.47, 0.74, 1.98, 0.18, 5), M.paint(), 0.01, 2.34, 0));            // felső test
  cab.add(mesh(RB(0.03, 0.6, 1.74, 0.02), M.glass(), 0.745, 2.32, 0));                // szélvédő
  cab.add(mesh(RB(0.03, 0.05, 1.9, 0.02), M.black(), 0.75, 2.66, 0));                 // napellenző
  for (const z of [-1.015, 1.015]) { cab.add(mesh(RB(0.72, 0.52, 0.02, 0.01), M.glass(), -0.05, 2.3, z)); }                  // oldalablak
  cab.add(mesh(RB(0.16, 0.36, 2.06, 0.05), M.black(), 0.78, 0.94, 0));              // lökhárító
  cab.add(mesh(RB(0.06, 0.34, 1.2, 0.03), M.black(), 0.83, 1.4, 0));               // hűtőrács
  for (const z of [-0.78, 0.78]) { cab.add(mesh(RB(0.06, 0.16, 0.34, 0.03), M.lens(), 0.82, 1.7, z)); cab.add(mesh(RB(0.02, 0.1, 0.26, 0.02), M.light(0xfff1c9), 0.8, 1.7, z)); }
  for (const z of [-1, 1]) { const arm = mesh(new THREE.BoxGeometry(0.05, 0.05, 0.28), M.black(), 0.45, 2.15, z * 1.12); cab.add(arm); cab.add(mesh(RB(0.06, 0.42, 0.16, 0.03), M.black(), 0.45, 2.02, z * 1.28)); }
  for (const z of [-1.012, 1.012]) cab.add(mesh(RB(1.5, 0.3, 0.02, 0.01), M.black(), 0.05, 1.0, z));   // alsó sötét sáv
  for (const z of [-1.02, 1.02]) cab.add(mesh(new THREE.BoxGeometry(0.14, 0.03, 0.01), M.black(), -0.2, 1.7, z)); // kilincs
  // kerékjárat íve a fülkén
  { const sh = new THREE.Shape(); sh.absarc(0, 0, 0.56, 0.05, Math.PI - 0.05, false); sh.absarc(0, 0, 0.5, Math.PI - 0.05, 0.05, true); const geo = new THREE.ExtrudeGeometry(sh, { depth: 0.1, bevelEnabled: false, curveSegments: 40 }); geo.translate(0, 0, -0.05); for (const z of [-0.99, 0.99]) cab.add(mesh(geo, M.black(), -0.2, 0.43, z)); }
  // hátsó aláfutásgátló + lámpák
  g.add(mesh(RB(0.12, 0.12, 2.0, 0.02), M.steel(), -3.72, 0.46, 0));
  for (const z of [-0.5, 0.5]) g.add(mesh(new THREE.BoxGeometry(0.06, 0.34, 0.06), M.steel(), -3.72, 0.63, z));
  for (const z of [-0.85, 0.85]) g.add(mesh(RB(0.06, 0.12, 0.3, 0.02), M.light(0xd4282c), -3.8, 0.7, z));
  return g;
}

// A felépítmény 7 alkatrészcsoportja – a sorrend megegyezik az oldalon lévő kártyákkal
function buildParts(M) {
  const X0 = -3.78, X1 = 1.62, L = X1 - X0, XC = (X0 + X1) / 2, FY = 0.98, Z = 1.08;
  const parts = [];
  const P = () => { const g = new THREE.Group(); parts.push(g); return g; };
  // 1 padló: alumínium padlóprofilok + rétegelt lemez teteje
  { const g = P(); g.add(mesh(new THREE.BoxGeometry(L, 0.1, 2 * Z), M.alu(), XC, FY - 0.05, 0)); g.add(mesh(new THREE.BoxGeometry(L - 0.04, 0.012, 2 * Z - 0.08), M.ply(), XC, FY + 0.006, 0)); for (const x of [-3.2, -2.3, -1.4, -0.5, 0.4, 1.2]) g.add(mesh(new THREE.BoxGeometry(0.06, 0.08, 2 * Z - 0.1), M.alu(), x, FY - 0.13, 0)); }
  // 2 oldalfalak: bordás, eloxált oldalfal profilok (3-3 mező + hátfal)
  { const g = P(); const bays = [[X0 + 0.05, -2.0], [-1.94, -0.12], [-0.06, X1 - 0.05]];
    for (const side of [-1, 1]) for (const [a, b] of bays) g.add(mesh(RB(b - a, 0.5, 0.045, 0.012), M.elox(5), (a + b) / 2, FY + 0.27, side * (Z - 0.02)));
    g.add(mesh(RB(0.045, 0.5, 2 * Z - 0.1, 0.012), M.elox(5), X0 + 0.02, FY + 0.27, 0)); }
  // 3 rakoncák
  { const g = P(); for (const x of [X0 + 0.03, -1.97, -0.09, X1 - 0.03]) for (const side of [-1, 1]) g.add(mesh(RB(0.07, 0.62, 0.07, 0.012), M.alu(), x, FY + 0.3, side * (Z - 0.01))); }
  // 4 homlokfal: keret + rács
  { const g = P(); const hx = X1 + 0.02, top = 2.45;
    for (const z of [-Z + 0.04, Z - 0.04]) g.add(mesh(RB(0.08, top - FY, 0.08, 0.015), M.alu(), hx, (top + FY) / 2, z));
    g.add(mesh(RB(0.08, 0.08, 2 * Z, 0.015), M.alu(), hx, top, 0));
    g.add(mesh(RB(0.08, 0.5, 2 * Z - 0.1, 0.012), M.elox(5), hx, FY + 0.27, 0));
    const rod = new THREE.CylinderGeometry(0.008, 0.008, 1, 6);
    for (let i = 0; i <= 18; i++) { const z = -Z + 0.1 + i * (2 * Z - 0.2) / 18; const m = mesh(rod, M.alu(), hx, (top + FY + 0.52) / 2, z); m.scale.y = top - FY - 0.52; g.add(m); }
    for (let i = 0; i <= 8; i++) { const y = FY + 0.56 + i * (top - FY - 0.6) / 8; const m = mesh(rod, M.alu(), hx, y, 0); m.rotation.x = Math.PI / 2; m.scale.y = 2 * Z - 0.12; g.add(m); } }
  // 5 sárvédők a hátsó ikerkerekek felett
  { const g = P(); const sh = new THREE.Shape(); const a0 = 0.18, a1 = Math.PI - 0.18; sh.absarc(0, 0, 0.58, a0, a1, false); sh.absarc(0, 0, 0.53, a1, a0, true);
    const geo = new THREE.ExtrudeGeometry(sh, { depth: 0.56, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.01, bevelSegments: 2, curveSegments: 48 }); geo.translate(0, 0, -0.28);
    for (const side of [-1, 1]) g.add(mesh(geo, M.plastic(), -1.95, 0.43, side * 0.8)); }
  // 6 oldalsó aláfutásgátló
  { const g = P(); for (const side of [-1, 1]) { for (const y of [0.42, 0.66]) g.add(mesh(RB(1.55, 0.09, 0.035, 0.012), M.elox(2), -0.55, y, side * 1.02)); for (const x of [-1.2, 0.1]) g.add(mesh(new THREE.BoxGeometry(0.05, 0.36, 0.5), M.steel(), x, 0.66, side * 0.78)); } }
  // 7 szerszámosláda
  { const g = P(); const b = mesh(RB(0.62, 0.46, 0.5, 0.05, 4), M.plastic(), 0.85, 0.56, 0.72); g.add(b); g.add(mesh(RB(0.63, 0.02, 0.51, 0.01), M.black(), 0.85, 0.7, 0.72)); for (const x of [0.7, 1.0]) g.add(mesh(RB(0.1, 0.05, 0.02, 0.01), M.rim(), x, 0.66, 0.975)); }
  return parts;
}

const easeOut = (t) => 1 - Math.pow(1 - t, 3);
const easeOutBack = (t) => { const c1 = 1.4, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };

export function mount(canvas, opts = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.VSMShadowMap;
  const scene = new THREE.Scene();
  const pm = new THREE.PMREMGenerator(renderer);
  const env = new RoomEnvironment();
  for (const [x, y, z, w, h, k] of [[0, 12, 0, 18, 6, 7], [-14, 5, 4, 3, 14, 5], [13, 6, -5, 3, 14, 4]]) { const p = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(k, k, k), side: THREE.DoubleSide })); p.position.set(x, y, z); p.lookAt(0, 0, 0); env.add(p); }
  scene.environment = pm.fromScene(env, 0.03).texture;

  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(4, 9, 5); key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 12; key.shadow.blurSamples = 16; key.shadow.bias = -0.0005;
  Object.assign(key.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7, near: 1, far: 30 }); scene.add(key);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xdfe6f0, 0.5));
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.22 })); ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
  const ct = tex(256, 256, (g) => { const gr = g.createRadialGradient(128, 128, 8, 128, 128, 128); gr.addColorStop(0, 'rgba(11,31,58,0.5)'); gr.addColorStop(0.6, 'rgba(11,31,58,0.14)'); gr.addColorStop(1, 'rgba(11,31,58,0)'); g.fillStyle = gr; g.fillRect(0, 0, 256, 256); });
  const contact = new THREE.Mesh(new THREE.PlaneGeometry(9, 3.6), new THREE.MeshBasicMaterial({ map: ct, transparent: true, depthWrite: false })); contact.rotation.x = -Math.PI / 2; contact.position.set(-0.4, 0.002, 0); scene.add(contact);

  const M = materials();
  const truck = new THREE.Group(); scene.add(truck);
  truck.add(buildBase(M));
  const parts = buildParts(M);
  parts.forEach((p) => { truck.add(p); p.userData.mats = []; p.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); p.userData.mats.push(o.material); o.material.userData.e = o.material.emissive ? o.material.emissive.clone() : null; } }); });

  const cam = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
  const target = new THREE.Vector3(-0.6, 1.2, 0);
  function resize() { const w = canvas.clientWidth || canvas.width, h = canvas.clientHeight || canvas.height; renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); }
  resize();

  const reduce = opts.static || (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  let last = -2, raf = 0, t0 = performance.now(), running = true;
  const hi = new THREE.Color(0x0a6cff);

  function frame(now) {
    const T = opts.time != null ? opts.time : (now - t0) / 1000;
    const t = reduce ? HOLD_END - 0.5 : T % LOOP;
    const ang = reduce ? 0.62 : 0.62 + (T / ORBIT) * Math.PI * 2;
    const R = 14.2;
    cam.position.set(target.x + Math.cos(ang) * R, 3.9 + Math.sin(T * 0.25) * 0.15, target.z + Math.sin(ang) * R);
    cam.lookAt(target);
    let step = -1;
    parts.forEach((p, i) => {
      const start = STEP0 + i * STEP;
      let y = 0, op = 1, vis = true, glow = 0;
      if (t < start) { vis = false; }
      else if (t < start + DROP) { const k = (t - start) / DROP; y = (1 - easeOutBack(k)) * 1.8; op = Math.min(1, k * 2.2); }
      else if (t < HOLD_END) { const k = (t - start - DROP) / 0.9; glow = Math.max(0, 1 - k); }
      else { const k = Math.min(1, (t - HOLD_END - i * 0.06) / LIFT); y = easeOut(Math.max(0, k)) * 2.2; op = 1 - Math.max(0, k); vis = op > 0.01; }
      if (t >= start + DROP * 0.6 && t < HOLD_END) step = i;
      p.visible = vis; p.position.y = y;
      for (const m of p.userData.mats) {
        m.transparent = op < 1; m.opacity = op; m.depthWrite = op > 0.6;
        if (m.emissive && m.userData.e) m.emissive.copy(m.userData.e).lerp(hi, glow * 0.35);
      }
    });
    if (step !== last) { last = step; opts.onStep && opts.onStep(step); }
    renderer.render(scene, cam);
    if (running && !reduce && opts.time == null) raf = requestAnimationFrame(frame);
  }
  let io = null;
  if ('IntersectionObserver' in window) { io = new IntersectionObserver((es) => { const v = es[0].isIntersecting; if (v && !running) { running = true; raf = requestAnimationFrame(frame); } else if (!v) { running = false; cancelAnimationFrame(raf); } }); io.observe(canvas); }
  const onResize = () => { resize(); if (reduce) frame(performance.now()); };
  window.addEventListener('resize', onResize);
  raf = requestAnimationFrame(frame);
  return {
    renderAt(sec) { opts.time = sec; frame(0); },
    dispose() { running = false; cancelAnimationFrame(raf); io && io.disconnect(); window.removeEventListener('resize', onResize); renderer.dispose(); },
  };
}
