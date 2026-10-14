/**
 * Kirish ma'lumotlarini tekshirish (validatsiya) yordamchilari.
 */
'use strict';

function str(v) { return typeof v === 'string' ? v.trim() : ''; }

function validName(v) { const s = str(v); return s.length >= 2 && s.length <= 120; }
function validEmail(v) {
  const s = str(v);
  return s.length >= 5 && s.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s);
}
function validPassword(v) { return typeof v === 'string' && v.length >= 8 && v.length <= 72; }
function validPhone(v) {
  const s = str(v);
  return /^\+?[0-9][0-9 ()-]{6,19}$/.test(s);
}
function validRoom(v) {
  const s = str(v);
  return s.length >= 2 && s.length <= 60 && /^[\p{L}\p{N} ()'_.\-]+$/u.test(s);
}
function validMessage(v) { const s = typeof v === 'string' ? v : ''; return s.trim().length >= 1 && s.length <= 2000; }
function validPercent(v) {
  if (v === undefined || v === null || v === '') return 0;
  const n = Number(v);
  if (!Number.isFinite(n) || n < 0 || n > 100) return null;
  return Math.round(n);
}
function validId(v) {
  const s = str(v);
  return /^\d{1,18}$/.test(s) ? s : null;
}
function validText(v, min, max) {
  const s = str(v);
  return s.length >= min && s.length <= max ? s : null;
}

module.exports = { str, validName, validEmail, validPassword, validPhone, validRoom, validMessage, validPercent, validId, validText };
