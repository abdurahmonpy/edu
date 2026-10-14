/**
 * Server-side Supabase klienti — GoTrue (auth) + PostgREST (data).
 * Kalitlar faqat server muhit o'zgaruvchilaridan o'qiladi:
 *   SUPABASE_URL             = https://<ref>.supabase.co
 *   SUPABASE_PUBLISHABLE_KEY = sb_publishable_...  (eski nomi: SUPABASE_ANON_KEY)
 *   SUPABASE_SECRET_KEY      = sb_secret_...       (eski nomi: SUPABASE_SERVICE_ROLE_KEY)
 * Brauzerga hech qanday kalit chiqmaydi.
 */
'use strict';

const { parseCookies, serializeCookie, clearCookie } = require('./http');

const ACCESS_COOKIE = 'edu_at';
const REFRESH_COOKIE = 'edu_rt';
const ACCESS_TTL = 60 * 60;            // 1 saat
const REFRESH_TTL = 60 * 60 * 24 * 30; // 30 kun

function config() {
  const url = (process.env.SUPABASE_URL || '').replace(/\/+$/, '');
  const publishable = process.env.SUPABASE_PUBLISHABLE_KEY || process.env.SUPABASE_ANON_KEY || '';
  const secret = process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';
  if (!url || !secret) {
    const err = new Error('SUPABASE_NOT_CONFIGURED');
    err.code = 'SUPABASE_NOT_CONFIGURED';
    throw err;
  }
  return { url, publishable, secret };
}

function configured() {
  try { config(); return true; } catch (e) { return false; }
}

async function rest(url, opts) {
  const r = await fetch(url, opts);
  const text = await r.text();
  let data = null;
  if (text) { try { data = JSON.parse(text); } catch (e) { data = { raw: text }; } }
  return { status: r.status, ok: r.ok, data };
}

// ---------- GoTrue (Auth) ----------

async function adminCreateUser(email, password, fullName) {
  const c = config();
  return rest(c.url + '/auth/v1/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: c.secret, Authorization: 'Bearer ' + c.secret },
    body: JSON.stringify({ email, password, email_confirm: true, user_metadata: { full_name: fullName } })
  });
}

async function passwordGrant(email, password) {
  const c = config();
  if (!c.publishable) {
    const err = new Error('SUPABASE_PUBLISHABLE_KEY_MISSING');
    err.code = 'SUPABASE_NOT_CONFIGURED';
    throw err;
  }
  return rest(c.url + '/auth/v1/token?grant_type=password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: c.publishable, Authorization: 'Bearer ' + c.publishable },
    body: JSON.stringify({ email, password })
  });
}

async function refreshGrant(refreshToken) {
  const c = config();
  if (!c.publishable) return { status: 401, ok: false, data: null };
  return rest(c.url + '/auth/v1/token?grant_type=refresh_token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: c.publishable, Authorization: 'Bearer ' + c.publishable },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
}

async function getUser(accessToken) {
  const c = config();
  return rest(c.url + '/auth/v1/user', {
    method: 'GET',
    headers: { apikey: c.publishable || c.secret, Authorization: 'Bearer ' + accessToken }
  });
}

async function logout(accessToken) {
  const c = config();
  try {
    await rest(c.url + '/auth/v1/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', apikey: c.publishable || c.secret, Authorization: 'Bearer ' + accessToken }
    });
  } catch (e) { /* sessiya allaqachon o'chgan bo'lishi mumkin */ }
}

// ---------- PostgREST (Ma'lumotlar) ----------

async function db(method, path, body, extraHeaders) {
  const c = config();
  const headers = {
    apikey: c.secret,
    Authorization: 'Bearer ' + c.secret,
    'Content-Type': 'application/json'
  };
  if (extraHeaders) Object.assign(headers, extraHeaders);
  return rest(c.url + '/rest/v1/' + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

const dbGet = (path) => db('GET', path);
const dbPost = (path, body, headers) => db('POST', path, body, headers);
const dbPatch = (path, body, headers) => db('PATCH', path, body, headers);
const dbDelete = (path) => db('DELETE', path);

// ---------- Sessiya (httpOnly cookie) ----------

function setSessionCookies(req, res, tokens) {
  const secure = !require('./http').isLoopback(req);
  const cookies = [
    serializeCookie(ACCESS_COOKIE, tokens.access_token, { httpOnly: true, secure, maxAge: tokens.expires_in || ACCESS_TTL, sameSite: 'Lax' }),
    serializeCookie(REFRESH_COOKIE, tokens.refresh_token, { httpOnly: true, secure, maxAge: REFRESH_TTL, sameSite: 'Lax' })
  ];
  res.setHeader('Set-Cookie', cookies);
}

function clearSessionCookies(req, res) {
  const secure = !require('./http').isLoopback(req);
  res.setHeader('Set-Cookie', [
    clearCookie(ACCESS_COOKIE, { httpOnly: true, secure, sameSite: 'Lax' }),
    clearCookie(REFRESH_COOKIE, { httpOnly: true, secure, sameSite: 'Lax' })
  ]);
}

/**
 * Joriy sessiyani aniqlaydi. Access token yaroqsiz bo'lsa —
 * refresh token bilan avtomatik yangilaydi (cookie'lar qayta yoziladi).
 * Muvaffaqiyatli bo'lsa {user, accessToken}, aks holda null.
 */
async function readSession(req, res) {
  const cookies = parseCookies(req);
  const access = cookies[ACCESS_COOKIE];
  const refresh = cookies[REFRESH_COOKIE];
  if (access) {
    const g = await getUser(access);
    if (g.ok) return { user: g.data, accessToken: access };
    if (g.status !== 401 && g.status !== 403) return null;
  }
  if (refresh) {
    const r = await refreshGrant(refresh);
    if (r.ok && r.data && r.data.access_token) {
      setSessionCookies(req, res, r.data);
      return { user: r.data.user || null, accessToken: r.data.access_token };
    }
    clearSessionCookies(req, res);
  }
  return null;
}

module.exports = {
  config, configured,
  adminCreateUser, passwordGrant, refreshGrant, getUser, logout,
  db, dbGet, dbPost, dbPatch, dbDelete,
  setSessionCookies, clearSessionCookies, readSession,
  ACCESS_COOKIE, REFRESH_COOKIE
};
