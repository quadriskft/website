// Vevői fiókok: regisztráció, bejelentkezés, kijelentkezés, adatok, jelszó-visszaállítás, fióktörlés.
// Cloudflare Pages Function. Tárolás: KV névtér, FIOKOK néven kötve (Settings → Bindings → KV namespace).
//   user:<email>            → { email, name, company, phone, taxNumber, salt, hash, created }
//   session:<sha256(token)> → email            (30 nap)
//   reset:<sha256(token)>   → email            (1 óra)
//   fail:<email>            → hibás belépések száma (15 perc)
// A jelszó PBKDF2-SHA256-tal (100 000 kör, egyedi só) van tárolva; a munkamenet-süti HttpOnly.
// Jelszó-visszaállító e-mail: Resend (RESEND_API_KEY, QUOTE_FROM – ugyanaz, mint az ajánlatkérésnél).

const SESSION_DAYS = 30;
const COOKIE = 'q_session';
const DEFAULT_FROM = 'Quadris weboldal <onboarding@resend.dev>';
const enc = new TextEncoder();

const json = (status, body, headers = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers } });
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
const unhex = (s) => new Uint8Array(s.match(/.{2}/g).map((h) => parseInt(h, 16)));
const sha256 = async (s) => hex(await crypto.subtle.digest('SHA-256', enc.encode(s)));
const randomToken = (bytes = 32) => hex(crypto.getRandomValues(new Uint8Array(bytes)));

async function hashPassword(password, saltHex) {
  const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: unhex(saltHex), iterations: 100000 }, key, 256);
  return hex(bits);
}
// állandó idejű összehasonlítás
function sameString(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

const clean = (v, max) => String(v ?? '').replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max);
const normEmail = (v) => clean(v, 160).toLowerCase();
const validEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);
const validPassword = (p) => typeof p === 'string' && p.length >= 8 && p.length <= 200;
const publicUser = (u) => ({ email: u.email, name: u.name, company: u.company, phone: u.phone, taxNumber: u.taxNumber ?? '' });

function sessionCookie(token, maxAge) {
  return `${COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}
function readCookie(request) {
  const m = (request.headers.get('Cookie') || '').match(new RegExp(`(?:^|;\\s*)${COOKIE}=([a-f0-9]{64})`));
  return m ? m[1] : null;
}
async function currentUser(request, kv) {
  const token = readCookie(request);
  if (!token) return null;
  const email = await kv.get(`session:${await sha256(token)}`);
  if (!email) return null;
  const user = await kv.get(`user:${email}`, 'json');
  return user ? { user, token } : null;
}
async function startSession(kv, email) {
  const token = randomToken();
  await kv.put(`session:${await sha256(token)}`, email, { expirationTtl: SESSION_DAYS * 86400 });
  return sessionCookie(token, SESSION_DAYS * 86400);
}

export async function onRequest({ request, env, params }) {
  const kv = env.FIOKOK;
  const route = (Array.isArray(params.path) ? params.path : [params.path]).filter(Boolean).join('/');
  if (!kv) return json(503, { ok: false, error: 'not_configured' });

  if (request.method === 'GET' && route === 'en') {
    const s = await currentUser(request, kv);
    return s ? json(200, { ok: true, user: publicUser(s.user) }) : json(401, { ok: false, error: 'not_logged_in' });
  }
  if (request.method !== 'POST') return json(405, { ok: false, error: 'method' });

  // CSRF elleni védelem: csak a saját oldalról érkező JSON-kérés
  const origin = request.headers.get('Origin');
  if (origin && origin !== new URL(request.url).origin) return json(403, { ok: false, error: 'origin' });
  if (!(request.headers.get('Content-Type') || '').includes('application/json')) return json(415, { ok: false, error: 'content_type' });
  let body;
  try { body = await request.json(); } catch { return json(400, { ok: false, error: 'bad_json' }); }
  if (!body || typeof body !== 'object') return json(400, { ok: false, error: 'bad_json' });
  if (clean(body.website, 50)) return json(200, { ok: true });  // csapdamező robotoknak

  if (route === 'regisztracio') {
    const email = normEmail(body.email);
    const user = { email, name: clean(body.name, 120), company: clean(body.company, 160), phone: clean(body.phone, 40), taxNumber: clean(body.taxNumber, 20) };
    if (!validEmail(email) || !user.name || !user.company || !user.phone) return json(400, { ok: false, error: 'missing' });
    if (!validPassword(body.password)) return json(400, { ok: false, error: 'weak_password' });
    if (body.consent !== true) return json(400, { ok: false, error: 'consent' });
    if (await kv.get(`user:${email}`)) return json(409, { ok: false, error: 'exists' });
    user.salt = randomToken(16);
    user.hash = await hashPassword(body.password, user.salt);
    user.created = new Date().toISOString();
    await kv.put(`user:${email}`, JSON.stringify(user));
    return json(200, { ok: true, user: publicUser(user) }, { 'Set-Cookie': await startSession(kv, email) });
  }

  if (route === 'belepes') {
    const email = normEmail(body.email);
    const password = typeof body.password === 'string' ? body.password.slice(0, 200) : '';
    if (!validEmail(email) || !password) return json(400, { ok: false, error: 'missing' });
    const fails = Number(await kv.get(`fail:${email}`)) || 0;
    if (fails >= 8) return json(429, { ok: false, error: 'locked' });
    const user = await kv.get(`user:${email}`, 'json');
    // nem létező fióknál is számolunk egy kivonatot, hogy a válaszidő ne árulja el, van-e ilyen e-mail
    const hash = await hashPassword(password, user?.salt ?? '00000000000000000000000000000000');
    if (!user || !sameString(hash, user.hash)) {
      await kv.put(`fail:${email}`, String(fails + 1), { expirationTtl: 900 });
      return json(401, { ok: false, error: 'invalid' });
    }
    if (fails) await kv.delete(`fail:${email}`);
    return json(200, { ok: true, user: publicUser(user) }, { 'Set-Cookie': await startSession(kv, email) });
  }

  if (route === 'kilepes') {
    const token = readCookie(request);
    if (token) await kv.delete(`session:${await sha256(token)}`);
    return json(200, { ok: true }, { 'Set-Cookie': sessionCookie('', 0) });
  }

  if (route === 'jelszo-kero') {
    const email = normEmail(body.email);
    if (!validEmail(email)) return json(400, { ok: false, error: 'missing' });
    const user = await kv.get(`user:${email}`, 'json');
    // a válasz mindig ugyanaz: nem derül ki belőle, hogy létezik-e a fiók
    if (user && env.RESEND_API_KEY) {
      const token = randomToken();
      await kv.put(`reset:${await sha256(token)}`, email, { expirationTtl: 3600 });
      const link = `${new URL(request.url).origin}/fiok?reset=${token}`;
      await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: env.QUOTE_FROM || DEFAULT_FROM,
          to: [email],
          subject: 'Quadris – új jelszó beállítása',
          text: `Tisztelt ${user.name}!\n\nA Quadris weboldalon új jelszó beállítását kérték ehhez az e-mail-címhez. Az új jelszót az alábbi hivatkozáson adhatja meg (1 óráig érvényes):\n\n${link}\n\nHa nem Ön kérte, hagyja figyelmen kívül ezt a levelet – a jelszava változatlan marad.\n\nÜdvözlettel:\nQuadris Kft.`,
        }),
      }).catch(() => {});
    }
    return json(200, { ok: true, mail: Boolean(env.RESEND_API_KEY) });
  }

  if (route === 'jelszo-uj') {
    const token = clean(body.token, 64);
    if (!/^[a-f0-9]{64}$/.test(token)) return json(400, { ok: false, error: 'bad_token' });
    if (!validPassword(body.password)) return json(400, { ok: false, error: 'weak_password' });
    const key = `reset:${await sha256(token)}`;
    const email = await kv.get(key);
    const user = email && (await kv.get(`user:${email}`, 'json'));
    if (!user) return json(400, { ok: false, error: 'bad_token' });
    user.salt = randomToken(16);
    user.hash = await hashPassword(body.password, user.salt);
    await kv.put(`user:${email}`, JSON.stringify(user));
    await kv.delete(key);
    await kv.delete(`fail:${email}`);
    return json(200, { ok: true, user: publicUser(user) }, { 'Set-Cookie': await startSession(kv, email) });
  }

  // innen bejelentkezés szükséges
  const s = await currentUser(request, kv);
  if (!s) return json(401, { ok: false, error: 'not_logged_in' });

  if (route === 'adatok') {
    const next = { ...s.user, name: clean(body.name, 120), company: clean(body.company, 160), phone: clean(body.phone, 40), taxNumber: clean(body.taxNumber, 20) };
    if (!next.name || !next.company || !next.phone) return json(400, { ok: false, error: 'missing' });
    if (body.newPassword) {
      if (!validPassword(body.newPassword)) return json(400, { ok: false, error: 'weak_password' });
      const cur = await hashPassword(typeof body.password === 'string' ? body.password.slice(0, 200) : '', s.user.salt);
      if (!sameString(cur, s.user.hash)) return json(401, { ok: false, error: 'invalid' });
      next.salt = randomToken(16);
      next.hash = await hashPassword(body.newPassword, next.salt);
    }
    await kv.put(`user:${next.email}`, JSON.stringify(next));
    return json(200, { ok: true, user: publicUser(next) });
  }

  if (route === 'torles') {
    const cur = await hashPassword(typeof body.password === 'string' ? body.password.slice(0, 200) : '', s.user.salt);
    if (!sameString(cur, s.user.hash)) return json(401, { ok: false, error: 'invalid' });
    await kv.delete(`user:${s.user.email}`);
    await kv.delete(`session:${await sha256(s.token)}`);
    return json(200, { ok: true }, { 'Set-Cookie': sessionCookie('', 0) });
  }

  return json(404, { ok: false, error: 'not_found' });
}
