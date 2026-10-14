/**
 * /api/chat — xona bo'yicha xabarlar (faqat login qilgan foydalanuvchi).
 * GET ?room=  → xabarlar ro'yxati
 * POST {room, body} → xabar yuborish
 * DELETE ?id= → o'z xabarini o'chirish
 */
'use strict';

const { json, readJson } = require('./_lib/http');
const { dbGet, dbPost, dbDelete, readSession, configured } = require('./_lib/supabase');
const { str, validRoom, validMessage, validId } = require('./_lib/validate');

async function authorName(session) {
  const r = await dbGet('profiles?id=eq.' + encodeURIComponent(session.user.id) + '&select=full_name');
  if (r.ok && Array.isArray(r.data) && r.data[0] && r.data[0].full_name) return r.data[0].full_name;
  return String((session.user.email && session.user.email.split('@')[0]) || 'Foydalanuvchi');
}

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (!configured()) return json(res, 503, { error: 'not_configured' });

  const session = await readSession(req, res);
  if (!session || !session.user) return json(res, 401, { error: 'unauthorized' });
  const uid = session.user.id;

  try {
    if (req.method === 'GET') {
      const room = str(req.query && req.query.room);
      if (!validRoom(room)) return json(res, 400, { error: 'invalid_room' });
      const r = await dbGet(
        'messages?room=eq.' + encodeURIComponent(room) +
        '&select=id,room,user_id,author_name,body,created_at' +
        '&order=created_at.asc&limit=200'
      );
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { messages: r.data || [] });
    }

    if (req.method === 'POST') {
      const body = await readJson(req, res);
      if (body === null) return;
      const room = validRoom(body.room) ? str(body.room) : null;
      const text = validMessage(body.body) ? String(body.body).trim() : null;
      if (!room || !text) return json(res, 400, { error: 'invalid_input', message: 'Xona nomi yoki xabar noto‘g‘ri.' });

      const name = await authorName(session);
      const r = await dbPost('messages',
        { room, user_id: uid, author_name: name, body: text },
        { Prefer: 'return=representation' });
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { message: Array.isArray(r.data) ? r.data[0] : r.data });
    }

    if (req.method === 'DELETE') {
      const id = validId(req.query && req.query.id);
      if (!id) return json(res, 400, { error: 'invalid_id' });
      const r = await dbDelete('messages?id=eq.' + id + '&user_id=eq.' + encodeURIComponent(uid));
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { ok: true });
    }

    return json(res, 405, { error: 'Method not allowed' });
  } catch (e) {
    if (e && e.code === 'SUPABASE_NOT_CONFIGURED') return json(res, 503, { error: 'not_configured' });
    return json(res, 500, { error: 'internal' });
  }
};
