/*!
 * Englify — "Bildirishnoma" (notifications.html) page logic.
 * ---------------------------------------------------------------------------
 * REST only: /notifications, /notifications/unread-count, /notifications/{id},
 * /notifications/{id}/read, /notifications/read-all.
 *
 * Requires (loaded before this file): config.js, ui.js, api.js, auth.js.
 */
(function () {
  'use strict';

  var api = window.EnglifyApi;
  var UI = window.EnglifyUI;
  var Auth = window.EnglifyAuth;

  if (!api || !UI || !Auth) {
    console.error('[Englify] notifications.js requires config.js, ui.js, api.js and auth.js');
    return;
  }

  var PAGE_LIMIT = 30;
  var UNREAD_CARD_SHADOW = 'inset 3px 0 0 #0A93F5, 0 4px 18px rgba(34,8,70,0.03)';
  var READ_CARD_SHADOW = '0 4px 18px rgba(34,8,70,0.03)';
  var FILTER_ACTIVE =
    'background: #0A93F5; color: #fff; border: 1.5px solid #0A93F5; border-radius: 999px;' +
    'padding: 7px 18px; font-weight: 800; font-size: 14.5px; cursor: pointer';
  var FILTER_IDLE =
    'background: #fff; color: #220846; border: 1.5px solid #E8EBF5; border-radius: 999px;' +
    'padding: 7px 18px; font-weight: 800; font-size: 14.5px; cursor: pointer';

  var state = {
    items: [],
    total: 0,
    unread: 0,
    filter: 'all'
  };

  function el(id) {
    return document.getElementById(id);
  }

  function findItem(id) {
    for (var i = 0; i < state.items.length; i += 1) {
      if (state.items[i].id === id) return state.items[i];
    }
    return null;
  }

  function listQuery() {
    var query = '/notifications?limit=' + PAGE_LIMIT + '&offset=0';
    if (state.filter === 'unread') query += '&unread_only=true';
    return query;
  }

  // ---------------------------------------------------------------- badge
  function paintBadge() {
    var count = Math.max(0, Number(state.unread) || 0);
    document.querySelectorAll('[data-badge="notifications"]').forEach(function (node) {
      node.textContent = count > 99 ? '99+' : String(count);
      node.hidden = count <= 0;
    });
  }

  function refreshAuthBadges() {
    if (Auth.refreshBadges) Auth.refreshBadges();
  }

  // ---------------------------------------------------------------- banner
  function gradientValue(value) {
    if (!value) return null;
    if (typeof value === 'string') return value;
    if (typeof value === 'object' && value.from && value.to) {
      return 'linear-gradient(135deg, ' + value.from + ', ' + value.to + ')';
    }
    return null;
  }

  function bannerNode(banner) {
    if (!banner || typeof banner !== 'object') return null;

    var node = document.createElement('div');
    node.className = 'notif-banner';
    node.style.background = gradientValue(banner.gradient) || 'linear-gradient(135deg, #421C16, #78351B)';

    var left = document.createElement('div');

    if (banner.badge) {
      var badge = document.createElement('span');
      badge.textContent = banner.badge;
      badge.style.cssText =
        'background:#fff;color:#220846;font-size:10px;font-weight:800;padding:2px 6px;' +
        'border-radius:4px;display:inline-block;margin-bottom:6px';
      left.appendChild(badge);
    }

    var chips = banner.chips;
    if (chips && chips.length) {
      var row = document.createElement('div');
      row.style.cssText = 'display:flex;gap:6px;margin-bottom:6px';
      Array.prototype.slice.call(chips).forEach(function (chip) {
        var label = typeof chip === 'string' ? chip : chip && chip.label;
        if (!label) return;
        var chipNode = document.createElement('span');
        chipNode.textContent = label;
        chipNode.style.cssText =
          'background:' + ((chip && chip.color) || '#0A93F5') + ';color:#fff;font-size:9px;' +
          'font-weight:800;padding:2px 6px;border-radius:4px';
        row.appendChild(chipNode);
      });
      if (row.childNodes.length) left.appendChild(row);
    }

    if (banner.headline) {
      var headline = document.createElement('div');
      headline.textContent = banner.headline;
      headline.style.cssText = 'font-weight:800;font-size:17px;line-height:1.25';
      left.appendChild(headline);
    }

    if (banner.subline) {
      var subline = document.createElement('div');
      subline.textContent = banner.subline;
      subline.style.cssText = 'font-size:11.5px;opacity:.85;margin-top:4px';
      left.appendChild(subline);
    }

    node.appendChild(left);

    if (banner.emoji) {
      var emoji = document.createElement('div');
      emoji.textContent = banner.emoji;
      emoji.style.fontSize = '48px';
      node.appendChild(emoji);
    }

    return node;
  }

  // ---------------------------------------------------------------- cards
  function cardNode(item) {
    var isRead = !!item.is_read;

    var card = document.createElement('div');
    card.className = 'notif-card';
    card.setAttribute('data-notification-id', item.id);
    card.setAttribute('data-read', isRead ? 'true' : 'false');
    card.style.cssText = 'position:relative;box-shadow:' + (isRead ? READ_CARD_SHADOW : UNREAD_CARD_SHADOW);

    var remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'notif-delete';
    remove.setAttribute('data-action', 'delete-notification');
    remove.setAttribute('aria-label', "O'chirish");
    remove.title = "O'chirish";
    remove.textContent = '\u2715';
    remove.style.cssText =
      'position:absolute;top:10px;right:12px;width:26px;height:26px;border:0;border-radius:999px;' +
      'background:#F3F5FB;color:#6C7A9C;font-size:13px;font-weight:800;line-height:1;cursor:pointer';
    card.appendChild(remove);

    var date = document.createElement('div');
    date.className = 'notif-date';
    if (isRead) {
      date.textContent = UI.datetime(item.created_at);
    } else {
      date.style.cssText = 'display:flex;align-items:center;gap:8px';
      var dot = document.createElement('span');
      dot.style.cssText =
        'width:8px;height:8px;border-radius:50%;background:#0A93F5;display:inline-block;flex-shrink:0';
      date.appendChild(dot);
      var stamp = document.createElement('span');
      stamp.textContent = UI.datetime(item.created_at);
      date.appendChild(stamp);
    }
    card.appendChild(date);

    var banner = bannerNode(item.banner);
    if (banner) card.appendChild(banner);

    if (item.title) {
      var title = document.createElement('div');
      title.className = 'notif-title';
      title.textContent = item.title;
      card.appendChild(title);
    }

    if (item.body) {
      var desc = document.createElement('div');
      desc.className = 'notif-desc';
      desc.textContent = item.body;
      card.appendChild(desc);
    }

    if (item.cta_label && item.link) {
      var wrap = document.createElement('div');
      wrap.style.overflow = 'hidden';
      var link = document.createElement('a');
      link.className = 'notif-action-btn';
      link.setAttribute('href', item.link);
      link.textContent = item.cta_label;
      wrap.appendChild(link);
      card.appendChild(wrap);
    }

    return card;
  }

  function render() {
    var list = el('notifList');
    if (!list) return;

    if (!state.items.length) {
      list.innerHTML = UI.empty("Bildirishnomalar yo'q", "Yangi xabarlar shu yerda ko'rinadi");
      return;
    }

    list.innerHTML = '';
    state.items.forEach(function (item) {
      list.appendChild(cardNode(item));
    });
  }

  function paintFilters() {
    document.querySelectorAll('#notifFilters [data-filter]').forEach(function (node) {
      node.style.cssText = node.getAttribute('data-filter') === state.filter ? FILTER_ACTIVE : FILTER_IDLE;
    });
  }

  // ---------------------------------------------------------------- loading
  function load() {
    var list = el('notifList');
    if (list) UI.loading(list, 3);

    return Promise.all([
      api.get(listQuery()),
      api.get('/notifications/unread-count').catch(function () {
        return null;
      })
    ])
      .then(function (results) {
        var page = results[0] || {};
        state.items = Array.isArray(page.items) ? page.items : [];
        state.total = typeof page.total === 'number' ? page.total : state.items.length;

        var counts = results[1];
        if (counts && typeof counts.unread === 'number') {
          state.unread = counts.unread;
        } else {
          state.unread = state.items.filter(function (item) {
            return !item.is_read;
          }).length;
        }

        render();
        paintBadge();
        return state.items;
      })
      .catch(function (error) {
        if (list) list.innerHTML = UI.errorBox(error);
        UI.toast(error.message, 'error');
        return [];
      });
  }

  // --------------------------------------------------------------- actions
  function markRead(id) {
    var item = findItem(id);
    if (!item || item.is_read) return Promise.resolve();

    return api
      .post('/notifications/' + encodeURIComponent(id) + '/read', {})
      .then(function (updated) {
        item.is_read = updated && typeof updated.is_read === 'boolean' ? updated.is_read : true;
        state.unread = Math.max(0, state.unread - 1);
        render();
        paintBadge();
        refreshAuthBadges();
      })
      .catch(function (error) {
        UI.toast(error.message, 'error');
      });
  }

  function removeNotification(id) {
    return api
      .del('/notifications/' + encodeURIComponent(id))
      .then(function () {
        var item = findItem(id);
        state.items = state.items.filter(function (entry) {
          return entry.id !== id;
        });
        state.total = Math.max(0, state.total - 1);
        if (item && !item.is_read) state.unread = Math.max(0, state.unread - 1);
        render();
        paintBadge();
        refreshAuthBadges();
        UI.toast("Bildirishnoma o'chirildi.", 'success');
      })
      .catch(function (error) {
        UI.toast(error.message, 'error');
      });
  }

  /** Replaces the old alert(): marks every notification read on the server. */
  function markAllRead() {
    return api
      .post('/notifications/read-all', {})
      .then(function () {
        UI.toast("Barcha bildirishnomalar o'qilgan deb belgilandi! \u2713\u2713", 'success');
        return load();
      })
      .then(function () {
        refreshAuthBadges();
      })
      .catch(function (error) {
        UI.toast(error.message, 'error');
      });
  }

  // ------------------------------------------------------------------- bind
  function bind() {
    var list = el('notifList');
    if (list) {
      UI.on(list, '.notif-card', 'click', function (event, node) {
        if (event.target.closest && event.target.closest('a, button')) return;
        var id = node.getAttribute('data-notification-id');
        if (id) markRead(id);
      });

      UI.on(list, '[data-action="delete-notification"]', 'click', function (event, node) {
        event.preventDefault();
        event.stopPropagation();
        var card = node.closest('.notif-card');
        var id = card && card.getAttribute('data-notification-id');
        if (id) removeNotification(id);
      });
    }

    document.querySelectorAll('#notifFilters [data-filter]').forEach(function (node) {
      node.addEventListener('click', function () {
        var value = node.getAttribute('data-filter');
        if (value === state.filter) return;
        state.filter = value;
        paintFilters();
        load();
      });
    });

    document.addEventListener('englify:realtime', function (event) {
      var frame = event.detail;
      if (frame && (frame.type === 'notification.created' || frame.type === 'notification')) load();
    });
  }

  function init() {
    bind();
    paintFilters();
    load();
  }

  window.markAllRead = markAllRead;

  function boot() {
    Auth.require()
      .then(function (user) {
        if (user) init();
      })
      .catch(function () {
        /* not authenticated: auth.js already redirected */
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
