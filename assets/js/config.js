/*!
 * Englify — API endpoint configuration.
 * ---------------------------------------------------------------------------
 * By default every page talks to the SAME ORIGIN, because Railway serves the
 * static HTML and the FastAPI backend from one service (`/api/v1/...`).
 *
 * If the frontend is hosted somewhere else (for example Vercel) point it at the
 * backend by adding ONE of these before the other scripts load:
 *
 *   <meta name="englify-api" content="https://englify-production.up.railway.app">
 *
 * or
 *
 *   <script>window.ENGLIFY_API_BASE = 'https://englify-production.up.railway.app';</script>
 */
(function () {
  'use strict';

  var meta = document.querySelector('meta[name="englify-api"]');
  var configured = (window.ENGLIFY_API_BASE || (meta && meta.getAttribute('content')) || '').trim();

  var base = configured || location.origin;
  base = base.replace(/\/+$/, '');

  var isLocal = /^(localhost|127\.0\.0\.1|\[::1\]|)$/.test(location.hostname);
  var looksLikeVercel = /\.vercel\.app$/.test(location.hostname);
  var isCrossOrigin = base.indexOf(location.origin) !== 0;

  if (looksLikeVercel && !configured) {
    console.error(
      '[Englify] Frontend is on Vercel but no API base is configured. ' +
        'Add <meta name="englify-api" content="https://<your-app>.up.railway.app"> to the page ' +
        'or set window.ENGLIFY_API_BASE.'
    );
    // Make the misconfiguration impossible to miss instead of failing silently.
    var showBanner = function () {
      if (document.getElementById('englify-config-warning')) return;
      var banner = document.createElement('div');
      banner.id = 'englify-config-warning';
      banner.style.cssText =
        'position:fixed;left:0;right:0;top:0;z-index:10000;background:#FF4757;color:#fff;' +
        'font:700 15px/1.4 system-ui,sans-serif;padding:12px 18px;text-align:center';
      banner.textContent =
        'Sozlamada xatolik: API manzili ko\u2019rsatilmagan. <meta name="englify-api"> tegiga ' +
        'Railway domenini yozing.';
      document.body.appendChild(banner);
    };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  }

  window.EnglifyConfig = {
    base: base,
    prefix: base + '/api/v1',
    wsPrefix: base.replace(/^http/, 'ws') + '/api/v1',
    isLocal: isLocal,
    isCrossOrigin: isCrossOrigin,
    appName: 'Englify',
    version: '1.0.0'
  };
})();
