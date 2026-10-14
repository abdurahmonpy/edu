/**
 * MCP (Model Context Protocol) server — edu platformasi kontenti uchun.
 * Transport: Streamable HTTP (stateless). Endpoint: POST /api/mcp
 * Tashqi kutubxona talab qilinmaydi. Faqatma-faqat o'qish (read-only) tool'lar.
 *
 * Ulash: MCP mijozida (Claude / Cursor / Freebuff) quyidagi sozlam:
 *   { "mcpServers": { "edu-platform": { "url": "https://edu-theta-three.vercel.app/api/mcp" } } }
 * yoki CLI: npx @modelcontextprotocol/inspector https://edu-theta-three.vercel.app/api/mcp
 */

const SERVER_INFO = { name: 'edu-platform-mcp', version: '1.0.0' };
const SUPPORTED_PROTOCOLS = ['2025-06-18', '2025-03-26', '2024-11-05'];
const DEFAULT_ORIGIN = 'https://edu-theta-three.vercel.app';

// ===== SAYT KONTENTI (repo fayllaridan) =====

const PAGES = [
  { file: 'index.html', url: '/', title: 'Landing — ro‘yxatdan o‘tish', purpose: 'Marketing sahifasi, kursga ro‘yxatdan o‘tish formasi', features: ['forma (ismla)', 'FAQ akkordeon', 'narxlar'], dataStorage: 'yo‘q — forma hech qayerga yuborilmaydi (demo)', backendStatus: 'backend yo‘q' },
  { file: 'app.html', url: '/app', title: 'Asosiy ilova paneli', purpose: 'Boshqaruv paneli: asosiy bo‘lim, resurslar (#asosiy, #resurslar)', features: ['dashboard', 'resurslar bo‘limi'], dataStorage: 'localStorage (demo)', backendStatus: 'backend yo‘q' },
  { file: 'dars.html', url: '/dars', title: 'Darslar', purpose: 'Video darslar (YouTube embed), vazifalar, mashqlar', features: ['video pleyer', 'uy vazifasi tanlash', 'harf mashqi', 'natija foizi'], dataStorage: "localStorage ('unit1_video_watched', 'unit1_video_percent', 'unit1_hw_percent')", backendStatus: 'backend yo‘q — progress faqat brauzerda' },
  { file: 'lugat.html', url: '/lugat', title: 'Lug‘at', purpose: 'Shaxsiy so‘z daftari: qo‘shish, qidirish, flashcard, talaffuz', features: ['so‘z qo‘shish', 'filtrlash', 'flashcard', 'speechSynthesis talaffuz'], dataStorage: "localStorage ('lugat_words')", backendStatus: 'backend yo‘q — so‘zlar faqat shu brauzerda' },
  { file: 'jang.html', url: '/jang', title: "So'zlar jangi", purpose: "Inglizcha so'zlar bo'yicha jang/o'yin rejimi", features: ['o‘yin mantiqi', 'ballar'], dataStorage: 'demo (localStorage)', backendStatus: 'backend yo‘q' },
  { file: 'oyinlar.html', url: '/oyinlar', title: 'O‘yinlar', purpose: "Speed Match, So'zlar jangi, Sentence Builder (demo)", features: ['speed match', "so'zlar jangi", 'sentence builder (tez orada — alert bilan)'], dataStorage: 'demo', backendStatus: 'backend yo‘q' },
  { file: 'level.html', url: '/level', title: 'Daraja', purpose: 'Daraja tanlash/quyosh tizimi (demo)', features: ['daraja kartalari'], dataStorage: 'demo', backendStatus: 'backend yo‘q' },
  { file: 'kitoblar.html', url: '/kitoblar', title: 'Kitoblar', purpose: 'Kitoblar ro‘yxati (demo)', features: ['kitob kartalari'], dataStorage: 'statik', backendStatus: 'backend yo‘q' },
  { file: 'podcastlar.html', url: '/podcastlar', title: 'Podcastlar', purpose: 'Podcastlar ro‘yxati (demo)', features: ['podcast kartalari'], dataStorage: 'statik', backendStatus: 'backend yo‘q' },
  { file: 'zoom.html', url: '/zoom', title: 'Zoom darslari', purpose: 'Jadval + Zoom ID nusxa olish', features: ['haftalik jadval', 'clipboard nusxa olish'], dataStorage: 'statik', backendStatus: 'backend yo‘q' },
  { file: 'chat.html', url: '/chat', title: 'Chat', purpose: 'Suhbat UI (bot avto-javob)', features: ['xabar yozish', 'bot avto-javob (800ms)'], dataStorage: 'faqat xotira — sahifa yangilansa yo‘qoladi', backendStatus: 'backend yo‘q — xabarlar saqlanmaydi' },
  { file: 'notifications.html', url: '/notifications', title: 'Bildirishnomalar', purpose: 'Bildirishnomalar ro‘yxati (demo)', features: ['o‘qilgan/qilmagan belgilash (alert)'], dataStorage: 'demo', backendStatus: 'backend yo‘q' },
  { file: 'peshqadam.html', url: '/peshqadam', title: 'Peshqadam', purpose: 'Reklama/galereya sahifasi', features: ['galereya'], dataStorage: 'statik', backendStatus: 'backend yo‘q' }
];

const LESSONS = {
  unit: 'Unit 1 — Alphabet',
  lessons: [
    { name: 'Alphabet 1', videoUrl: 'https://www.youtube.com/embed/HQ3APZJj4qY?autoplay=1&rel=0&modestbranding=1' },
    { name: 'Alphabet 2', videoUrl: 'https://www.youtube.com/embed/ccEpTTZXSi8?autoplay=1&rel=0&modestbranding=1' },
    { name: 'Alphabet 3', videoUrl: 'https://www.youtube.com/embed/wpffswm5l9s?autoplay=1&rel=0&modestbranding=1' }
  ],
  flow: 'Video to‘liq ko‘rilgandan keyin uy vazifasi → majburiy vazifa tanlash → mashq (harf kiritish) → natija foizi localStorage ga yoziladi'
};

const VOCAB = [
  { en: 'Hello', uz: 'salom', type: "so'z", ex: 'Hello! How are you?' },
  { en: 'Goodbye', uz: 'xayr', type: "so'z", ex: 'Goodbye, see you tomorrow!' },
  { en: 'Thank you', uz: 'rahmat', type: 'ibora', ex: 'Thank you very much!' },
  { en: 'Please', uz: 'iltimos', type: 'ibora', ex: 'Please help me.' },
  { en: 'Good morning', uz: 'xayrli tong', type: 'ibora', ex: 'Good morning, class!' }
];

const BACKEND_GAPS = [
  { feature: 'Ro‘yxatdan o‘tish formasi (/)', current: 'onsubmit="return false" — hech qayerga yuborilmaydi', needs: 'Serverless API + DB (lead jadvali) + spam himoyasi' },
  { feature: 'Chat (/chat)', current: 'Faqat brauzer xotirasi, bot avto-javob', needs: 'DB (xabar jadvali) + auth + WebSocket/SSE yoki polling' },
  { feature: 'Dars progressi (/dars)', current: "localStorage ('unit1_*')", needs: 'Foydalanuvchi hisobi + serverda progress jadvali' },
  { feature: 'Lug‘at (/lugat)', current: "localStorage ('lugat_words') — boshqa qurilmada yo'qoladi", needs: 'Sync uchun DB + auth' },
  { feature: 'Autentifikatsiya', current: 'yo‘q — hech qanday himoyalangan sahifa yo‘q', needs: 'Auth (masalan Supabase Auth) + sessiya cookie' },
  { feature: 'Ovozli reyting / jang natijalari', current: 'demo, saqlanmaydi', needs: 'Leaderboard tablosi + anti-cheat tekshiruvi' }
];

// ===== TOOL'LAR =====

const TOOL_DEFS = [
  {
    name: 'site_status',
    description: 'Vercel’da joylashgan edu saytining sahifalarini jonli tekshiradi: HTTP holati va javob vaqti.',
    inputSchema: {
      type: 'object',
      properties: { origin: { type: 'string', description: 'Tekshiriladigan origin (default: https://edu-theta-three.vercel.app)' } },
      additionalProperties: false
    }
  },
  {
    name: 'list_pages',
    description: 'Saytdagi barcha sahifalar: maqsadi, funksiyalari, qayerda data saqlanishi va backend holati.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false }
  },
  {
    name: 'get_lessons',
    description: 'Unit 1 darslari: video havolalar va o‘quv oqimi (video → vazifa → mashq → natija).',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false }
  },
  {
    name: 'dictionary_words',
    description: "Lug'at sahifasidagi boshlang'ich so'zlarni qaytaradi (inglizcha/o'zbekcha misollari bilan).",
    inputSchema: {
      type: 'object',
      properties: { query: { type: 'string', description: "So'z bo'yicha filtr (ixtiyoriy)" } },
      additionalProperties: false
    }
  },
  {
    name: 'backend_audit',
    description: "Loyihadagi backend bo'shliqlari ro'yxati: nima demo-rejimda va real backend nima talab qiladi.",
    inputSchema: { type: 'object', properties: {}, additionalProperties: false }
  }
];

async function toolSiteStatus(args) {
  const origin = (args && args.origin) || DEFAULT_ORIGIN;
  const paths = [...new Set(['/', ...PAGES.map(p => p.url)])];
  const results = await Promise.all(paths.map(async (path) => {
    const started = Date.now();
    try {
      const r = await fetch(origin + path, { method: 'GET', redirect: 'follow', signal: AbortSignal.timeout(8000) });
      return { path, status: r.status, ok: r.ok, ms: Date.now() - started };
    } catch (e) {
      return { path, status: 0, ok: false, ms: Date.now() - started, error: String(e && e.message || e) };
    }
  }));
  const allOk = results.every(r => r.ok);
  return { origin, allPagesHealthy: allOk, checkedAt: new Date().toISOString(), results };
}

// ===== JSON-RPC YORDAMCHILARI =====

function makeResult(id, result) { return { jsonrpc: '2.0', id, result }; }
function makeError(id, code, message) { return { jsonrpc: '2.0', id: id === undefined ? null : id, error: { code, message } }; }

async function runTool(name, args) {
  switch (name) {
    case 'site_status': return toolSiteStatus(args);
    case 'list_pages': return { pages: PAGES };
    case 'get_lessons': return LESSONS;
    case 'dictionary_words': {
      const q = args && typeof args.query === 'string' ? args.query.toLowerCase().trim() : '';
      const words = q ? VOCAB.filter(w => w.en.toLowerCase().includes(q) || w.uz.toLowerCase().includes(q)) : VOCAB;
      return { total: words.length, words };
    }
    case 'backend_audit': return { platform: 'Vercel (static + /api serverless)', gaps: BACKEND_GAPS };
    default: return null;
  }
}

async function dispatch(msg) {
  if (!msg || msg.jsonrpc !== '2.0' || typeof msg.method !== 'string') return makeError(msg && msg.id, -32600, 'Invalid Request');
  const id = msg.id;
  const isNotification = id === undefined || id === null;

  if (msg.method.startsWith('notifications/')) return isNotification ? null : makeResult(id, {});

  switch (msg.method) {
    case 'initialize': {
      const requested = msg.params && msg.params.protocolVersion;
      const protocolVersion = SUPPORTED_PROTOCOLS.includes(requested) ? requested : SUPPORTED_PROTOCOLS[0];
      return makeResult(id, {
        protocolVersion,
        capabilities: { tools: { listChanged: false } },
        serverInfo: SERVER_INFO,
        instructions: "edu platformasi kontentini o'qish uchun tool'lar. Sayt Vercel'da statik, backend hali yo'q — backend_audit bilan bo'shliqlarni ko'ring."
      });
    }
    case 'ping':
      return makeResult(id, {});
    case 'tools/list':
      return makeResult(id, { tools: TOOL_DEFS });
    case 'tools/call': {
      const name = msg.params && msg.params.name;
      if (!TOOL_DEFS.some(t => t.name === name)) return makeError(id, -32602, 'Unknown tool: ' + name);
      try {
        const data = await runTool(name, (msg.params && msg.params.arguments) || {});
        return makeResult(id, { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }], isError: false });
      } catch (e) {
        return makeResult(id, { content: [{ type: 'text', text: 'Tool error: ' + (e && e.message || e) }], isError: true });
      }
    }
    default:
      return makeError(id, -32601, 'Method not found: ' + msg.method);
  }
}

function readBody(req) {
  if (req.body !== undefined) return Promise.resolve(req.body);
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', c => { raw += c; if (raw.length > 1e6) { reject(new Error('Payload too large')); req.destroy(); } });
    req.on('end', () => { if (!raw) return resolve(null); try { resolve(JSON.parse(raw)); } catch (e) { reject(new Error('Invalid JSON')); } });
    req.on('error', reject);
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Accept, Mcp-Session-Id, Mcp-Protocol-Version, Last-Event-ID');
  res.setHeader('Cache-Control', 'no-store');

  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (req.method === 'GET' || req.method === 'DELETE') {
    // Stateless server: SSE stream va sessiya yo'q (spec bo'yicha 405).
    res.setHeader('Allow', 'POST');
    res.statusCode = 405;
    return res.end(JSON.stringify({ error: 'Use POST JSON-RPC to /api/mcp' }));
  }
  if (req.method !== 'POST') { res.statusCode = 405; return res.end(); }

  let body;
  try { body = await readBody(req); }
  catch (e) { res.statusCode = 400; return res.end(JSON.stringify(makeError(null, -32700, String(e.message || e)))); }

  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  let messages = Array.isArray(body) ? body : [body];
  if (Array.isArray(body) && body.length === 0) { res.statusCode = 400; return res.end(JSON.stringify(makeError(null, -32600, 'Invalid Request'))); }

  const out = [];
  for (const m of messages) {
    const r = await dispatch(m);
    if (r !== null && r !== undefined) out.push(r);
  }

  if (out.length === 0) { res.statusCode = 202; return res.end(); } // notification(lar) uchun
  res.statusCode = 200;
  return res.end(JSON.stringify(Array.isArray(body) ? out : out[0]));
};
