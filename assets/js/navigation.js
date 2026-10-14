(function () {
  'use strict';
  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clearTransition() {
    if (document.body) document.body.classList.remove('page-enter', 'page-leave');
  }
  function navigate(url, replace) {
    var target;
    try { target = new URL(url, window.location.href); } catch (_) { return; }
    if (target.origin !== window.location.origin) return;
    if (reducedMotion || !document.body) {
      if (replace) window.location.replace(target.href);
      else window.location.assign(target.href);
      return;
    }
    document.body.classList.remove('page-enter');
    document.body.classList.add('page-leave');
    window.setTimeout(function () {
      if (replace) window.location.replace(target.href);
      else window.location.assign(target.href);
    }, 180);
  }
  window.SultanNavigate = navigate;
  if (reducedMotion) return;
  function initialize() {
    document.body.classList.add('page-enter');
    window.addEventListener('pageshow', function (event) {
      if (event.persisted) clearTransition();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
  window.addEventListener('pagehide', clearTransition);

  document.addEventListener('click', function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var link = event.target.closest('a[href]');
    if (!link || link.target || link.hasAttribute('download') || link.dataset.noTransition !== undefined) return;
    var url;
    try { url = new URL(link.href, window.location.href); } catch (_) { return; }
    if (url.origin !== window.location.origin || url.pathname === window.location.pathname && url.search === window.location.search) return;
    event.preventDefault();
    navigate(url.href, false);
  });
})();
