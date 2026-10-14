/**
 * Kichik HTTP yordamchilari — Vercel serverless, tashqi kutubxonasiz.
 */
'use strict';

function json(res, status, obj, extraHeaders) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  if (extraHeaders) {
    for (const [k, v] of Object.entries(extraHeaders)) res.setHeader(k, v);
  }
  res.end(JSON.stringify(obj));
}

function readBody(req) {
  if (req.body !== undefined && req.body !== null) {
    if (typeof req.body === 'string') {
      try { return Promise.resolve(JSON.parse(req.body)); }
      catch (e) { return Promise.reject(new Error('bad_json')); }
    }
    return Promise.resolve(req.body);
  }
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (c) => {
      raw += c;
      if (raw.length > 64 * 1024) { reject(new Error('too_large')); req.destroy(); }
    });
    req.on('end', () => {
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch (e) { reject(new Error('bad_json')); }
    });
    req.on('error', reject);
  });
}

function parseCookies(req) {
  const header = req.headers && req.headers.cookie;
  const out = {};
  if (!header) return out;
  for (const part of header.split(';')) {
    const i = part.indexOf('=');
    if (i === -1) continue;
    const k = part.slice(0, i).trim();
    const v = part.slice(i + 1).trim();
    if (k) out[k] = decodeURIComponent(v);
  }
  return out;
}

function serializeCookie(name, value, opts) {
  opts = opts || {};
  let c = name + '=' + encodeURIComponent(value);
  c += '; Path=' + (opts.path || '/');
  if (opts.maxAge !== undefined) c += '; Max-Age=' + Math.floor(opts.maxAge);
  if (opts.httpOnly) c += '; HttpOnly';
  if (opts.secure) c += '; Secure';
  c += '; SameSite=' + (opts.sameSite || 'Lax');
  return c;
}

function clearCookie(name, opts) {
  opts = opts || {};
  return serializeCookie(name, '', Object.assign({}, opts, { maxAge: 0 }));
}

function isLoopback(req) {
  const host = String((req.headers && req.headers.host) || '');
  return /^localhost(:\d+)?$/.test(host) || /^127\.0\.0\.1(:\d+)?$/.test(host);
}

function readJson(req, res) {
  return readBody(req).catch((e) => {
    const msg = e && e.message;
    const status = msg === 'too_large' ? 413 : 400;
    json(res, status, { error: msg === 'too_large' ? 'Too large' : 'Invalid JSON body' });
    return null;
  });
}

/**
 * API xatolarini xavfsiz kodlab javob beradi (maxfiy ma'lumotsiz).
 */
function handleApiError(res, e) {
  const code = e && e.code;
  if (code === 'SUPABASE_NOT_CONFIGURED') return json(res, 503, { error: 'not_configured' });
  if (code === 'SUPABASE_PUBLISHABLE_KEY_MISSING') return json(res, 503, { error: 'publishable_key_missing' });
  if (code === 'SUPABASE_URL_INVALID') {
    return json(res, 503, { error: 'supabase_url_invalid', message: 'SUPABASE_URL noto\'g\'ri — qiymat https://<ref>.supabase.co ko\'rinishida bo\'lishi kerak.' });
  }
  if (code === 'UPSTREAM_NETWORK') {
    return json(res, 502, { error: 'upstream_unreachable', detail: e.causeCode || 'unknown' });
  }
  return json(res, 500, { error: 'internal' });
}

module.exports = { json, readBody, parseCookies, serializeCookie, clearCookie, isLoopback, readJson, handleApiError };
