// Cloudflare Pages Function: POST /api/ajanlatkeres
// Az ajánlatkérést / kapcsolati üzenetet e-mailben továbbítja a Resend szolgáltatáson keresztül.
//
// Beállítás (Cloudflare Pages > Settings > Variables and Secrets):
//   RESEND_API_KEY  – a Resend API kulcs (titkos)
//   QUOTE_TO        – címzett(ek), vesszővel elválasztva
//   QUOTE_FROM      – feladó (opcionális; saját domain hitelesítése után pl. "Quadris weboldal <ajanlat@quadris.hu>")

const MAX_ITEMS = 500;
const DEFAULT_FROM = 'Quadris weboldal <onboarding@resend.dev>';

const json = (status, body) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json; charset=utf-8' } });

const str = (value, max) => String(value ?? '').trim().slice(0, max);

const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function parseRequest(body) {
  const c = body?.customer ?? {};
  const customer = {
    name: str(c.name, 120),
    company: str(c.company, 160),
    email: str(c.email, 160),
    phone: str(c.phone, 40),
  };
  const items = (Array.isArray(body?.items) ? body.items : []).slice(0, MAX_ITEMS).map((i) => ({
    code: str(i?.code, 60),
    name: str(i?.name, 300),
    qty: Math.min(Math.max(Math.round(Number(i?.qty)) || 1, 1), 99999),
    note: str(i?.note, 300),
    cuts: (Array.isArray(i?.cuts) ? i.cuts : []).slice(0, 50).map((c) => ({
      len: Math.min(Math.max(Math.round(Number(c?.len)) || 0, 0), 30000),
      pcs: Math.min(Math.max(Math.round(Number(c?.pcs)) || 1, 1), 99999),
    })).filter((c) => c.len > 0),
    custom: Boolean(i?.custom),
    url: /^https?:\/\//.test(String(i?.url ?? '')) ? str(i.url, 300) : '',
  })).filter((i) => i.name);
  const message = str(body?.message, 3000);

  const errors = [];
  if (!customer.name) errors.push('name');
  if (!EMAIL_RE.test(customer.email)) errors.push('email');
  if (!items.length && !message) errors.push('content');
  return { customer, items, message, errors };
}

const cutsText = (cuts) => (cuts ?? []).map((c) => `${c.pcs} db × ${c.len.toLocaleString('hu-HU')} mm`).join(', ');

export function buildEmail({ customer, items, message }) {
  const isQuote = items.length > 0;
  const who = customer.company || customer.name;
  const subject = isQuote ? `Ajánlatkérés – ${who} (${items.length} tétel)` : `Üzenet a weboldalról – ${who}`;

  const fields = [
    ['Név', customer.name],
    ['Cég', customer.company],
    ['E-mail', customer.email],
    ['Telefon', customer.phone],
  ].filter(([, v]) => v);

  const text = [
    subject,
    '',
    ...fields.map(([k, v]) => `${k}: ${v}`),
    ...(isQuote ? ['', 'Tételek:', ...items.map((i, n) => `${n + 1}. ${i.code ? `[${i.code}] ` : ''}${i.name}${i.custom ? ' (EGYEDI)' : ''} – ${i.qty} db${i.cuts?.length ? ` (${cutsText(i.cuts)})` : ''}${i.note ? ` – ${i.note}` : ''}`)] : []),
    ...(message ? ['', 'Megjegyzés / üzenet:', message] : []),
  ].join('\n');

  const td = 'padding:8px 10px;border-bottom:1px solid #e3e8ef;vertical-align:top;';
  const html = `<!doctype html><html><body style="font-family:Arial,sans-serif;color:#0b1726;">
  <h2 style="margin:0 0 12px;">${escapeHtml(subject)}</h2>
  <table style="border-collapse:collapse;margin-bottom:18px;">${fields.map(([k, v]) => `<tr><td style="${td}color:#5b6776;">${k}</td><td style="${td}"><strong>${escapeHtml(v)}</strong></td></tr>`).join('')}</table>
  ${isQuote ? `<table style="border-collapse:collapse;width:100%;max-width:760px;">
    <tr style="background:#0b1726;color:#fff;"><th style="${td}text-align:left;">#</th><th style="${td}text-align:left;">Cikkszám</th><th style="${td}text-align:left;">Megnevezés</th><th style="${td}text-align:right;">Menny.</th><th style="${td}text-align:left;">Megjegyzés</th></tr>
    ${items.map((i, n) => `<tr><td style="${td}">${n + 1}</td><td style="${td}">${escapeHtml(i.code || '–')}</td><td style="${td}">${i.url ? `<a href="${escapeHtml(i.url)}">${escapeHtml(i.name)}</a>` : escapeHtml(i.name)}${i.custom ? ' <em style="color:#2f6bff;">(egyedi tétel)</em>' : ''}</td><td style="${td}text-align:right;"><strong>${i.qty}</strong> db</td><td style="${td}">${i.cuts?.length ? `<strong>Méretek:</strong> ${escapeHtml(cutsText(i.cuts))}${i.note ? '<br>' : ''}` : ''}${escapeHtml(i.note)}</td></tr>`).join('')}
  </table>` : ''}
  ${message ? `<h3 style="margin:20px 0 6px;">Megjegyzés / üzenet</h3><p style="white-space:pre-wrap;margin:0;">${escapeHtml(message)}</p>` : ''}
  </body></html>`;

  return { subject, text, html };
}

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json(400, { ok: false, error: 'invalid_json' });
  }

  // Spamcsapda: a rejtett mezőt csak robotok töltik ki
  if (str(body?.website, 200)) return json(200, { ok: true });

  const parsed = parseRequest(body);
  if (parsed.errors.length) return json(422, { ok: false, error: 'invalid', fields: parsed.errors });

  if (!env.RESEND_API_KEY || !env.QUOTE_TO) return json(503, { ok: false, error: 'not_configured' });

  const { subject, text, html } = buildEmail(parsed);
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: env.QUOTE_FROM || DEFAULT_FROM,
      to: env.QUOTE_TO.split(',').map((s) => s.trim()).filter(Boolean),
      reply_to: parsed.customer.email,
      subject,
      text,
      html,
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    console.error('Resend hiba', res.status, detail);
    let message = '';
    try {
      message = String(JSON.parse(detail).message ?? '');
    } catch {}
    return json(502, { ok: false, error: 'send_failed', status: res.status, message: message.slice(0, 300) });
  }
  return json(200, { ok: true });
}

// Diagnosztika: GET /api/ajanlatkeres – megmutatja, be vannak-e állítva a változók (értékük nélkül)
export function onRequestGet({ env }) {
  return json(200, {
    ok: true,
    function: 'ajanlatkeres',
    RESEND_API_KEY: env.RESEND_API_KEY ? 'beállítva' : 'HIÁNYZIK',
    QUOTE_TO: env.QUOTE_TO ? 'beállítva' : 'HIÁNYZIK',
    QUOTE_FROM: env.QUOTE_FROM ? 'beállítva' : 'alapértelmezett',
  });
}
