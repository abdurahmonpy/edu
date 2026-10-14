/*!
 * Englify — student dashboard page logic (app.html).
 * ---------------------------------------------------------------------------
 * Loaded last, AFTER config.js, ui.js, api.js and auth.js.
 *
 * Owns every dynamic value on the dashboard:
 *   - five skill bars        GET /users/me/stats
 *   - streak / points pills  GET /users/me/stats
 *   - level card             GET /levels
 *   - battle counters        GET /battles/stats
 *   - vocabulary card        GET /vocabulary/stats + /vocabulary?limit=1&status=new
 *
 * Everything is defensive: a failed request only shows a toast and leaves the
 * hardcoded fallback markup in place. Nothing here touches the tab switching
 * (data-go / history.replaceState) implemented in app.html itself.
 */
(function () {
  'use strict';

  var api = window.EnglifyApi;
  var UI = window.EnglifyUI;
  var Auth = window.EnglifyAuth;

  if (!api || !UI) {
    console.error('[Englify] app.js requires config.js, api.js and ui.js');
    return;
  }

  /** Order of the five skill bars in the hero card. */
  var SKILL_ORDER = ['vocabulary', 'writing', 'reading', 'listening', 'grammar'];

  // ------------------------------------------------------------- tiny utils
  function all(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function setText(selector, value) {
    all(selector).forEach(function (node) {
      node.textContent = value;
    });
  }

  function clampPercent(value) {
    var n = Number(value);
    if (!isFinite(n)) return 0;
    return Math.max(0, Math.min(100, n));
  }

  function pad3(value) {
    var text = String(Math.max(1, Math.round(Number(value) || 1)));
    while (text.length < 3) text = '0' + text;
    return text;
  }

  function fail(error) {
    UI.toast((error && error.message) || 'Xatolik yuz berdi.', 'error');
  }

  // -------------------------------------------------------------- rendering
  function paintSkills(skills) {
    if (!skills || !skills.length) return;

    SKILL_ORDER.forEach(function (name, index) {
      var card = document.querySelector('[data-skill="' + name + '"]');
      if (!card) return;

      var entry = null;
      skills.forEach(function (item) {
        if (!entry && String(item && item.skill || '').trim().toLowerCase() === name) entry = item;
      });
      if (!entry) entry = skills[index];
      if (!entry) return;

      var percent = clampPercent(entry.percent);

      var label = card.querySelector('[data-skill-percent]');
      if (label) label.textContent = Math.round(percent) + '%';

      // Only the height changes — the inline animation-delay is preserved.
      var bar = card.querySelector('.bar');
      if (bar) bar.style.height = percent + '%';
    });
  }

  function paintStats(stats) {
    if (!stats) return;

    var points = Number(stats.points) || 0;
    var streak = Number(stats.streak_days) || 0;

    // Streak pill (🔥 n) and the "n ball" / "n tanga" pills.
    setText('[data-stat-streak]', UI.number(streak));
    setText('[data-stat-points]', UI.number(points));
    setText('[data-stat-coins]', UI.number(points));

    // The five skill bars.
    paintSkills(stats.skills);

    // auth.js already paints [data-user-streak]; keep it in sync with stats.
    all('[data-user-streak]').forEach(function (node) {
      node.textContent = UI.number(streak);
    });
  }

  /** Picks the level the student is currently on and its successor. */
  function currentLevel(levels) {
    var sorted = levels.slice().sort(function (a, b) {
      return (Number(a.order) || 0) - (Number(b.order) || 0);
    });
    var unlocked = sorted.filter(function (level) {
      return !!level.unlocked;
    });
    var active = unlocked.filter(function (level) {
      return clampPercent(level.progress_percent) < 100;
    });
    var current = active.length
      ? active[active.length - 1]
      : unlocked.length
        ? unlocked[unlocked.length - 1]
        : sorted[0];
    var index = sorted.indexOf(current);
    return { current: current, next: sorted[index + 1] || null };
  }

  function paintLevels(levels) {
    if (!levels || !levels.length) return;

    var picked = currentLevel(levels);
    var current = picked.current;
    if (!current) return;

    var percent = clampPercent(current.progress_percent);
    var title = current.title || (Auth && Auth.levelTitle ? Auth.levelTitle(current.slug) : 'Starter');

    // Level name (page header + sidebar card).
    setText('[data-level-title]', title);
    // Percentage text and the progress bar are driven by the SAME value.
    setText('[data-level-percent]', Math.round(percent) + '%');
    all('[data-level-bar]').forEach(function (bar) {
      bar.style.width = percent + '%';
    });
    // "Keyingi daraja: X" — the next entry in the array.
    setText('[data-level-next]', picked.next ? picked.next.title || '—' : '—');
  }

  function paintBattles(stats) {
    if (!stats) return;
    setText('[data-battle="played"]', UI.number(stats.played || 0));
    setText('[data-battle="won"]', UI.number(stats.won || 0));
    setText('[data-battle="lost"]', UI.number(stats.lost || 0));
  }

  function paintVocabulary(stats, sample) {
    var total = stats ? Number(stats.total) || 0 : 0;
    var summary = document.querySelector('[data-vocab-summary]');

    if (summary && total > 0) summary.textContent = UI.number(total) + " so'z";

    var items = (sample && sample.items) || [];
    var item = items[0];
    if (!item) return;

    var offset = Number(sample && sample.offset) || 0;
    var index = pad3(offset + 1);

    var meta = document.querySelector('[data-vocab-meta]');
    if (meta) {
      meta.textContent = index + ' \u00b7 [' + (item.part_of_speech || 'word') + ']';
    }

    var word = document.querySelector('[data-vocab-word]');
    if (word) word.textContent = item.word || '';

    var example = document.querySelector('[data-vocab-example]');
    if (example) example.textContent = item.example || item.translation || '';
  }

  // ------------------------------------------------------------------ boot
  function load() {
    api.get('/users/me/stats').then(paintStats).catch(fail);
    api.get('/levels').then(paintLevels).catch(fail);
    api.get('/battles/stats').then(paintBattles).catch(fail);

    var statsRequest = api.get('/vocabulary/stats').catch(function (error) {
      fail(error);
      return null;
    });
    var sampleRequest = api.get('/vocabulary?limit=1&status=new').catch(function (error) {
      fail(error);
      return null;
    });

    Promise.all([statsRequest, sampleRequest]).then(function (results) {
      paintVocabulary(results[0], results[1]);
    });
  }

  function start() {
    if (!Auth || typeof Auth.require !== 'function') {
      load();
      return;
    }
    Auth.require()
      .then(function () {
        load();
      })
      .catch(function () {
        /* not authenticated — auth.js owns the redirect */
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
