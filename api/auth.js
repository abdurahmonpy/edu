/**
 * /api/auth — hisob: signup, login, logout, me (httpOnly cookie sessiyalar).
 * POST {action:'signup'|'login'|'logout'} yoki GET ?action=me
 */
'use strict';

const { json, readJson } = require('./_lib/http');
const {
  adminCreateUser, passwordGrant, logout, dbGet, dbPost,
  setSessionCookies, clearSessionCookies, readSession, configured
} = require('./_lib/supabase');
const { str, validName, validEmail, validPassword } = require('./_lib/validate');

function publicUser(authUser, fullName) {
  return {
    id: authUser && authUser.id,
    email: authUser && authUser.email,
    name: fullName || (authUser && authUser.user_metadata && authUser.user_metadata.full_name) || (authUser && String(authUser.email || '').split('@')[0]) || 'Foydalanuvchi'
  };
}

async function getProfileName(userId) {
  const r = await dbGet('profiles?id=eq.' + encodeURIComponent(userId) + '&select=full_name');
  if (r.ok && Array.isArray(r.data) && r.data[0]) return r.data[0].full_name;
  return null;
}

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }

  let action = req.method === 'GET' ? str((req.query && req.query.action) || '') : null;
  let body = {};
  if (req.method === 'POST') {
    body = await readJson(req, res);
    if (body === null) return;
    action = str(body.action);
  } else if (req.method !== 'GET') {
    return json(res, 405, { error: 'Only GET/POST' });
  }

  if (!action) return json(res, 400, { error: 'missing_action' });
  if (!configured()) return json(res, 503, { error: 'not_configured' });

  try {
    if (action === 'me') {
      const session = await readSession(req, res);
      if (!session || !session.user) return json(res, 401, { error: 'unauthorized' });
      const name = await getProfileName(session.user.id);
      return json(res, 200, { user: publicUser(session.user, name) });
    }

    if (action === 'signup') {
      const name = validName(body.name) ? str(body.name) : null;
      const email = validEmail(body.email) ? str(body.email).toLowerCase() : null;
      const password = validPassword(body.password) ? body.password : null;
      if (!name || !email || !password) {
        return json(res, 400, { error: 'invalid_input', message: "Ism (2-120), to'g'ri email va kamida 8 belgili parol kerak." });
      }

      const created = await adminCreateUser(email, password, name);
      if (!created.ok) {
        const msg = JSON.stringify(created.data || {}).toLowerCase();
        if (msg.includes('already registered') || msg.includes('already been registered') || created.status === 422) {
          return json(res, 409, { error: 'email_taken', message: 'Bu email allaqachon ro‘yxatdan o‘tgan.' });
        }
        return json(res, 502, { error: 'upstream_error' });
      }

      const uid = created.data && created.data.id;
      if (uid) {
        await dbPost('profiles', { id: uid, full_name: name }, { Prefer: 'resolution=merge-duplicates,return=minimal' })
          .catch(() => null);
      }

      const session = await passwordGrant(email, password);
      if (!session.ok) return json(res, 200, { user: publicUser(created.data, name), needsLogin: true });

      setSessionCookies(req, res, session.data);
      return json(res, 200, { user: publicUser(session.data.user || created.data, name) });
    }

    if (action === 'login') {
      const email = validEmail(body.email) ? str(body.email).toLowerCase() : null;
      const password = typeof body.password === 'string' && body.password.length ? body.password : null;
      if (!email || !password) return json(res, 400, { error: 'invalid_input', message: 'Email va parol kiriting.' });

      const session = await passwordGrant(email, password);
      if (!session.ok) {
        if (session.status === 400 || session.status === 401 || session.status === 403) {
          return json(res, 401, { error: 'bad_credentials', message: 'Email yoki parol noto‘g‘ri.' });
        }
        return json(res, 502, { error: 'upstream_error' });
      }

      setSessionCookies(req, res, session.data);
      const name = session.data.user ? await getProfileName(session.data.user.id) : null;
      return json(res, 200, { user: publicUser(session.data.user, name) });
    }

    if (action === 'logout') {
      const cookies = req.headers.cookie || '';
      const m = cookies.match(/(?:^|;\s*)edu_at=([^;]+)/);
      if (m) await logout(decodeURIComponent(m[1]));
      clearSessionCookies(req, res);
      return json(res, 200, { ok: true });
    }

    return json(res, 400, { error: 'unknown_action' });
  } catch (e) {
    if (e && e.code === 'SUPABASE_NOT_CONFIGURED') return json(res, 503, { error: 'not_configured' });
    return json(res, 500, { error: 'internal' });
  }
};
