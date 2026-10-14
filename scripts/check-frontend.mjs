#!/usr/bin/env node
/**
 * Englify — static frontend integration checker.
 *
 * Verifies the wiring between the HTML pages and the shared JS layer without
 * needing a browser:
 *
 *   1. every page loads config.js → ui.js → api.js → auth.js in that order
 *   2. `<body data-auth="…">` is set on every wired page
 *   3. every `assets/js/pages/*.js` parses (node --check)
 *   4. every `getElementById('x')` / `querySelector('#x')` in a page script
 *      resolves to an id that actually exists in that page's HTML
 *   5. no page has been left with a `localStorage` implementation that was
 *      supposed to be replaced by the API
 *   6. no page still contains the bracket placeholders ([%], [ISM], …) that the
 *      API is meant to fill
 *
 * Usage:  node scripts/check-frontend.mjs          (from the repo root)
 * Exit code 1 on any failure — suitable for CI.
 */

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGES_DIR = path.join(ROOT, 'assets', 'js', 'pages');

const failures = [];
const warnings = [];
const notes = [];

function fail(msg) {
  failures.push(msg);
}
function warn(msg) {
  warnings.push(msg);
}

function read(file) {
  return readFileSync(file, 'utf8');
}

/* ------------------------------------------------------------------ 1. pages */
const htmlFiles = readdirSync(ROOT)
  .filter((f) => f.endsWith('.html'))
  .sort();

const REQUIRED_ORDER = ['config.js', 'ui.js', 'api.js', 'auth.js'];

const AUTH_MODES = new Set(['required', 'optional', 'public', 'guest']);

// Pages that intentionally do not use the API layer.
const EXEMPT = new Set(['404.html']);

for (const file of htmlFiles) {
  const html = read(path.join(ROOT, file));
  if (EXEMPT.has(file)) continue;

  const scripts = [...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map((m) => m[1]);
  const shared = REQUIRED_ORDER.map((name) => `assets/js/${name}`);

  const present = shared.filter((src) => scripts.includes(src));
  if (present.length !== shared.length) {
    fail(
      `${file}: missing shared scripts — expected all of ${shared.join(', ')}; found ${present.join(', ') || 'none'}`
    );
  } else {
    const positions = shared.map((src) => scripts.indexOf(src));
    const ordered = positions.every((p, i) => i === 0 || p > positions[i - 1]);
    if (!ordered) {
      fail(`${file}: shared scripts are out of order (must be ${shared.join(' → ')})`);
    }
    const authIndex = scripts.indexOf('assets/js/auth.js');
    const after = scripts.slice(authIndex + 1).filter((s) => s.startsWith('assets/js/'));
    notes.push(`${file}: shared layer ok, page scripts → ${after.join(', ') || '(none)'}`);
  }

  const bodyTag = html.match(/<body[^>]*>/i);
  if (!bodyTag) {
    fail(`${file}: no <body> tag found`);
  } else if (!/\bdata-auth="/.test(bodyTag[0])) {
    fail(`${file}: <body> is missing a data-auth attribute`);
  } else {
    const mode = bodyTag[0].match(/data-auth="([^"]+)"/)[1];
    if (!AUTH_MODES.has(mode)) {
      fail(`${file}: unknown data-auth="${mode}" (expected ${[...AUTH_MODES].join('|')})`);
    }
  }
}

/* --------------------------------------------------- 2. page script syntax */
const pageScripts = existsSync(PAGES_DIR)
  ? readdirSync(PAGES_DIR).filter((f) => f.endsWith('.js')).sort()
  : [];

if (pageScripts.length === 0) {
  fail('assets/js/pages/ contains no page scripts');
}

for (const script of pageScripts) {
  const full = path.join(PAGES_DIR, script);
  try {
    execFileSync(process.execPath, ['--check', full], { stdio: 'pipe' });
  } catch (error) {
    fail(`${script}: syntax error\n${(error.stderr || error.stdout || '').toString().trim()}`);
  }
}

/* ------------------------------- 3. selectors used by a page exist in the HTML */
const GLOBAL_IDS = new Set([
  // Provided by the shared layer at runtime.
  'englify-toasts',
]);

const ID_PATTERNS = [
  /getElementById\(\s*['"]([^'"]+)['"]\s*\)/g,
  /querySelector(?:All)?\(\s*['"]#([A-Za-z0-9_-]+)['"]/g,
];

function htmlForScript(script) {
  const base = script.replace(/\.js$/, '');
  return `${base}.html`;
}

function collectIds(html) {
  const ids = new Set();
  for (const m of html.matchAll(/\bid="([^"]+)"/g)) ids.add(m[1]);
  return ids;
}

for (const script of pageScripts) {
  const page = htmlForScript(script);
  const pagePath = path.join(ROOT, page);
  if (!existsSync(pagePath)) {
    warn(`${script}: no matching ${page} — skipped selector check`);
    continue;
  }

  const html = read(pagePath);
  const ids = collectIds(html);
  const js = read(path.join(PAGES_DIR, script));
  const missing = new Set();

  for (const pattern of ID_PATTERNS) {
    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(js)) !== null) {
      const id = match[1];
      if (!ids.has(id) && !GLOBAL_IDS.has(id) && !js.includes(`id="${id}"`) && !js.includes(`id='${id}'`)) {
        missing.add(id);
      }
    }
  }

  // Ids the script injects into the DOM itself (e.g. via innerHTML templates).
  const injected = new Set();
  for (const m of js.matchAll(/id=\\?["']([A-Za-z0-9_-]+)\\?["']/g)) injected.add(m[1]);

  const reallyMissing = [...missing].filter((id) => !injected.has(id));
  if (reallyMissing.length) {
    fail(`${script} → ${page}: ids not found in HTML: ${reallyMissing.map((i) => '#' + i).join(', ')}`);
  } else {
    notes.push(`${script} → ${page}: all queried ids resolve (${ids.size} ids in page)`);
  }
}

/* ------------------------------- 4. legacy localStorage / placeholder checks */
const LEGACY_LOCALSTORAGE = [
  { file: 'dars.html', keys: ['unit1_video_watched', 'unit1_video_percent', 'unit1_hw_percent'] },
  { file: 'lugat.html', keys: ['lugat_words'] },
];

for (const { file, keys } of LEGACY_LOCALSTORAGE) {
  const full = path.join(ROOT, file);
  if (!existsSync(full)) continue;
  const html = read(full);
  const found = keys.filter((key) => html.includes(key));
  if (found.length) {
    fail(`${file}: still uses localStorage key(s) ${found.join(', ')} — must use the API instead`);
  }
}

const PLACEHOLDER_PATTERNS = [
  { re: /\[%\]/g, label: '[%] percentage placeholder' },
  { re: /\[ISM\]/g, label: '[ISM] name placeholder' },
  { re: /\[NARX\]/g, label: '[NARX] price placeholder' },
  { re: /\[F\.I\.SH\.\]/g, label: '[F.I.SH.] placeholder' },
  { re: /\[000 0000 0000\]/g, label: '[000 0000 0000] meeting-id placeholder' },
];

for (const file of htmlFiles) {
  if (EXEMPT.has(file)) continue;
  const html = read(path.join(ROOT, file));
  const hits = PLACEHOLDER_PATTERNS.filter(({ re }) => {
    re.lastIndex = 0;
    return re.test(html);
  }).map(({ label }) => label);

  if (hits.length) {
    // index.html marketing copy legitimately keeps some placeholders for the
    // client to fill in, so those are warnings rather than failures.
    if (file === 'index.html') {
      warn(`${file}: still contains ${hits.join(', ')}`);
    } else {
      fail(`${file}: still contains ${hits.join(', ')}`);
    }
  }
}

/* --------------------------------------------------------------- 5. report */
console.log('Englify frontend integration check');
console.log('─'.repeat(64));
console.log(`pages: ${htmlFiles.length}   page scripts: ${pageScripts.length}`);
console.log('');

for (const note of notes) console.log(`  ok    ${note}`);
for (const w of warnings) console.log(`  warn  ${w}`);
for (const f of failures) console.log(`  FAIL  ${f}`);

console.log('');
if (failures.length) {
  console.log(`✗ ${failures.length} failure(s), ${warnings.length} warning(s)`);
  process.exit(1);
}
console.log(`✓ all checks passed (${warnings.length} warning(s))`);
