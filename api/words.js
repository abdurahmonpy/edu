/**
 * /api/words — shaxsiy lug'at (faqat login qilgan foydalanuvchi).
 * GET                 → so'zlar ro'yxati
 * POST {en, uz, type?, ex?, status?}      → qo'shish
 * PUT ?id= {en?, uz?, type?, ex?, status?} → o'zgartirish
 * DELETE ?id=                             → o'chirish
 */
'use strict';

const { json, readJson, handleApiError } = require('./_lib/http');
const { dbGet, dbPost, dbPatch, dbDelete, readSession, ensureConfigured } = require('./_lib/supabase');
const { str, validText, validId } = require('./_lib/validate');

const STATUSES = ['new', 'learned', 'review'];
const TYPES = ["so'z", 'ibora'];

function wordFields(body, requireAll) {
  const en = validText(body.en, 1, 200);
  const uz = validText(body.uz, 1, 200);
  if (requireAll && (!en || !uz)) return null;
  const out = {};
  if (en) out.en = en;
  if (uz) out.uz = uz;
  if (body.type !== undefined) {
    const t = str(body.type);
    if (!TYPES.includes(t)) return null;
    out.type = t;
  }
  if (body.status !== undefined) {
    const s = str(body.status);
    if (!STATUSES.includes(s)) return null;
    out.status = s;
  }
  if (body.ex !== undefined) {
    const ex = typeof body.ex === 'string' ? body.ex.trim() : '';
    if (ex.length > 500) return null;
    out.ex = ex;
  }
  return out;
}

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (!ensureConfigured(res)) return;

  const session = await readSession(req, res);
  if (!session || !session.user) return json(res, 401, { error: 'unauthorized' });
  const uid = session.user.id;

  try {
    if (req.method === 'GET') {
      const r = await dbGet('words?user_id=eq.' + encodeURIComponent(uid) +
        '&select=id,en,uz,type,ex,status,created_at&order=created_at.desc&limit=500');
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { words: r.data || [] });
    }

    if (req.method === 'POST') {
      const body = await readJson(req, res);
      if (body === null) return;
      const fields = wordFields(body, true);
      if (!fields) return json(res, 400, { error: 'invalid_input', message: "Inglizcha va o'zbekcha so'zlarni to'g'ri kiriting." });
      if (fields.status === undefined) fields.status = 'new';
      if (fields.type === undefined) fields.type = "so'z";
      if (fields.ex === undefined) fields.ex = '';
      const r = await dbPost('words', Object.assign({ user_id: uid }, fields), { Prefer: 'return=representation' });
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { word: Array.isArray(r.data) ? r.data[0] : r.data });
    }

    if (req.method === 'PUT') {
      const id = validId(req.query && req.query.id);
      if (!id) return json(res, 400, { error: 'invalid_id' });
      const body = await readJson(req, res);
      if (body === null) return;
      const fields = wordFields(body, false);
      if (!fields || Object.keys(fields).length === 0) return json(res, 400, { error: 'invalid_input' });
      const r = await dbPatch('words?id=eq.' + id + '&user_id=eq.' + encodeURIComponent(uid), fields, { Prefer: 'return=representation' });
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { word: Array.isArray(r.data) ? (r.data[0] || null) : r.data });
    }

    if (req.method === 'DELETE') {
      const id = validId(req.query && req.query.id);
      if (!id) return json(res, 400, { error: 'invalid_id' });
      const r = await dbDelete('words?id=eq.' + id + '&user_id=eq.' + encodeURIComponent(uid));
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { ok: true });
    }

    return json(res, 405, { error: 'Method not allowed' });
  } catch (e) {
    return handleApiError(res, e);
  }
};
