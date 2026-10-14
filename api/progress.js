/**
 * /api/progress — darslar progressi (faqat login qilgan foydalanuvchi).
 * GET                    → barcha darslar progressi
 * PUT {lesson, video_watched?, video_percent?, hw_percent?} → upsert
 */
'use strict';

const { json, readJson } = require('./_lib/http');
const { dbGet, dbPost, readSession, configured } = require('./_lib/supabase');
const { str, validText, validPercent } = require('./_lib/validate');

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (!configured()) return json(res, 503, { error: 'not_configured' });

  const session = await readSession(req, res);
  if (!session || !session.user) return json(res, 401, { error: 'unauthorized' });
  const uid = session.user.id;

  try {
    if (req.method === 'GET') {
      const r = await dbGet('lesson_progress?user_id=eq.' + encodeURIComponent(uid) +
        '&select=lesson,video_watched,video_percent,hw_percent,updated_at&order=updated_at.asc');
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { progress: r.data || [] });
    }

    if (req.method === 'PUT') {
      const body = await readJson(req, res);
      if (body === null) return;
      const lesson = validText(body.lesson, 1, 120);
      if (!lesson) return json(res, 400, { error: 'invalid_input', message: 'Dars nomi kerak.' });

      const videoPercent = validPercent(body.video_percent);
      const hwPercent = validPercent(body.hw_percent);
      if (videoPercent === null || hwPercent === null) {
        return json(res, 400, { error: 'invalid_input', message: 'Foiz 0..100 oralig‘ida bo‘lishi kerak.' });
      }

      const row = {
        user_id: uid,
        lesson,
        video_watched: body.video_watched === true || videoPercent >= 100,
        video_percent: videoPercent,
        hw_percent: hwPercent,
        updated_at: new Date().toISOString()
      };

      const r = await dbPost('lesson_progress', row, { Prefer: 'resolution=merge-duplicates,return=representation' });
      if (!r.ok) return json(res, 502, { error: 'upstream_error' });
      return json(res, 200, { progress: Array.isArray(r.data) ? r.data[0] : r.data });
    }

    return json(res, 405, { error: 'Method not allowed' });
  } catch (e) {
    if (e && e.code === 'SUPABASE_NOT_CONFIGURED') return json(res, 503, { error: 'not_configured' });
    return json(res, 500, { error: 'internal' });
  }
};
