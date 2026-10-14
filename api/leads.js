/**
 * POST /api/leads — index.html ro'yxatdan o'tish formasidan lead qabul qilish.
 * Autentifikatsiya talab qilinmaydi. Honeypot + kengaytirilgan rate-limit bilan himoyalangan.
 */
'use strict';

const { json, readJson } = require('./_lib/http');
const { dbPost, configured } = require('./_lib/supabase');
const { validName, validPhone, str } = require('./_lib/validate');

// Best-effort in-memory rate limit (Vercel serverless: har bir instance uchun alohida).
const hits = new Map();
function rateLimited(key) {
  const now = Date.now();
  const win = 10 * 60 * 1000;
  const arr = (hits.get(key) || []).filter((t) => now - t < win);
  if (arr.length >= 5) { hits.set(key, arr); return true; }
  arr.push(now);
  hits.set(key, arr);
  return false;
}

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (req.method !== 'POST') return json(res, 405, { error: 'Only POST' });

  if (!configured()) return json(res, 503, { error: 'not_configured' });

  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown').split(',')[0].trim();
  if (rateLimited(ip)) return json(res, 429, { error: 'too_many_requests' });

  const body = await readJson(req, res);
  if (body === null) return;

  // Honeypot: bot forma "company" maydonini to'ldiradi — sukut bilan qabul qilamiz.
  if (str(body.company)) return json(res, 200, { ok: true });

  const fullName = validName(body.full_name) ? str(body.full_name) : null;
  const phone = validPhone(body.phone) ? str(body.phone) : null;
  if (!fullName || !phone) return json(res, 400, { error: 'invalid_input', message: "Ism (2-120 belgi) va to'g'ri telefon kiriting." });

  const r = await dbPost('leads', { full_name: fullName, phone }, { Prefer: 'return=minimal' });
  if (!r.ok) return json(res, 502, { error: 'upstream_error' });
  return json(res, 200, { ok: true });
};
