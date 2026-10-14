/*!
 * Englify — small UI helpers shared by every page (window.EnglifyUI).
 * No framework, no build step: plain DOM + template strings.
 */
(function () {
  'use strict';

  var MONTHS_UZ = [
    'yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun',
    'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'
  ];
  var WEEKDAYS_UZ = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba'];

  function pad(value) {
    return value < 10 ? '0' + value : String(value);
  }

  function toDate(value) {
    if (!value) return null;
    if (value instanceof Date) return value;
    var text = String(value);
    // Safari/older engines reject "2026-10-14 12:00:00" — normalise to ISO.
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(text)) text = text.replace(' ', 'T');
    if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(text)) text += 'Z';
    var date = new Date(text);
    return isNaN(date.getTime()) ? null : date;
  }

  var UI = {
    // ------------------------------------------------------------- escaping
    escape: function (value) {
      if (value === null || value === undefined) return '';
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },

    // ------------------------------------------------------------- numbers
    number: function (value) {
      var n = Number(value || 0);
      return n.toLocaleString('uz-UZ').replace(/\u00a0/g, ' ');
    },

    initials: function (name) {
      var clean = String(name || '').trim();
      if (!clean) return '?';
      var parts = clean.split(/\s+/);
      if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    },

    /** Inline SVG avatar that always renders, even without an uploaded image. */
    avatar: function (user, size) {
      size = size || 44;
      user = user || {};
      var name = user.name || user.full_name || 'Talaba';
      var emoji = user.avatar_emoji || user.emoji;
      var url = user.avatar_url;

      if (url) {
        return (
          '<img src="' + UI.escape(url) + '" alt="' + UI.escape(name) + '" loading="lazy" ' +
          'style="width:' + size + 'px;height:' + size + 'px;border-radius:50%;object-fit:cover">'
        );
      }
      if (emoji) {
        return (
          '<span aria-hidden="true" style="width:' + size + 'px;height:' + size + 'px;border-radius:50%;' +
          'background:#CFE6FA;display:inline-flex;align-items:center;justify-content:center;' +
          'font-size:' + Math.round(size * 0.5) + 'px">' + UI.escape(emoji) + '</span>'
        );
      }
      return (
        '<span aria-hidden="true" style="width:' + size + 'px;height:' + size + 'px;border-radius:50%;' +
        'background:#0B5AA4;color:#fff;display:inline-flex;align-items:center;justify-content:center;' +
        'font-weight:800;font-size:' + Math.round(size * 0.38) + 'px;letter-spacing:.02em">' +
        UI.escape(UI.initials(name)) +
        '</span>'
      );
    },

    // --------------------------------------------------------------- dates
    date: function (value) {
      var date = toDate(value);
      if (!date) return '';
      return date.getDate() + ' ' + MONTHS_UZ[date.getMonth()] + ' ' + date.getFullYear();
    },

    /** "15:52" for today, "11 may" for this year, "14.10.2026" otherwise. */
    short: function (value) {
      var date = toDate(value);
      if (!date) return '';
      var now = new Date();
      var sameDay =
        date.getDate() === now.getDate() &&
        date.getMonth() === now.getMonth() &&
        date.getFullYear() === now.getFullYear();
      if (sameDay) return pad(date.getHours()) + ':' + pad(date.getMinutes());
      if (date.getFullYear() === now.getFullYear()) {
        return date.getDate() + ' ' + MONTHS_UZ[date.getMonth()].slice(0, 3);
      }
      return pad(date.getDate()) + '.' + pad(date.getMonth() + 1) + '.' + date.getFullYear();
    },

    datetime: function (value) {
      var date = toDate(value);
      if (!date) return '';
      return (
        UI.date(date) + ' ' + pad(date.getHours()) + ':' + pad(date.getMinutes())
      );
    },

    /** "Bugun · 18:00 – 19:30" style label used by the events page. */
    eventLabel: function (startsAt, durationMinutes) {
      var date = toDate(startsAt);
      if (!date) return '';
      var now = new Date();
      var tomorrow = new Date(now.getTime() + 86400000);
      var dayLabel;
      if (date.toDateString() === now.toDateString()) dayLabel = 'Bugun';
      else if (date.toDateString() === tomorrow.toDateString()) dayLabel = 'Ertaga';
      else dayLabel = WEEKDAYS_UZ[date.getDay()];

      var end = new Date(date.getTime() + (durationMinutes || 60) * 60000);
      return (
        dayLabel + ' · ' + pad(date.getHours()) + ':' + pad(date.getMinutes()) +
        ' – ' + pad(end.getHours()) + ':' + pad(end.getMinutes())
      );
    },

    relative: function (value) {
      var date = toDate(value);
      if (!date) return '';
      var diff = Math.floor((Date.now() - date.getTime()) / 1000);
      if (diff < 60) return 'Hozir';
      if (diff < 3600) return Math.floor(diff / 60) + ' daqiqa oldin';
      if (diff < 86400) return Math.floor(diff / 3600) + ' soat oldin';
      if (diff < 604800) return Math.floor(diff / 86400) + ' kun oldin';
      return UI.short(date);
    },

    duration: function (seconds) {
      var total = Math.max(0, Math.round(Number(seconds) || 0));
      var minutes = Math.floor(total / 60);
      var rest = total % 60;
      return minutes + ':' + pad(rest);
    },

    // --------------------------------------------------------------- toasts
    toast: function (message, kind, timeout) {
      var host = document.getElementById('englify-toasts');
      if (!host) {
        host = document.createElement('div');
        host.id = 'englify-toasts';
        host.setAttribute('role', 'status');
        host.setAttribute('aria-live', 'polite');
        host.style.cssText =
          'position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:9999;' +
          'display:flex;flex-direction:column;gap:10px;align-items:center;pointer-events:none';
        document.body.appendChild(host);
      }

      var palette = {
        success: { bg: '#17C877', fg: '#062E1D' },
        error: { bg: '#FF4757', fg: '#fff' },
        info: { bg: '#0B5AA4', fg: '#fff' },
        warn: { bg: '#FFB26F', fg: '#40260C' }
      };
      var tone = palette[kind] || palette.info;

      var node = document.createElement('div');
      node.textContent = message;
      node.style.cssText =
        'pointer-events:auto;max-width:min(92vw,460px);padding:13px 20px;border-radius:16px;' +
        'font-weight:700;font-size:16px;line-height:1.35;box-shadow:0 10px 26px rgba(20,40,120,.22);' +
        'background:' + tone.bg + ';color:' + tone.fg + ';opacity:0;transform:translateY(10px);' +
        'transition:opacity .22s ease,transform .22s ease';
      host.appendChild(node);

      requestAnimationFrame(function () {
        node.style.opacity = '1';
        node.style.transform = 'none';
      });

      var life = timeout || (kind === 'error' ? 5200 : 3200);
      setTimeout(function () {
        node.style.opacity = '0';
        node.style.transform = 'translateY(10px)';
        setTimeout(function () {
          if (node.parentNode) node.parentNode.removeChild(node);
        }, 240);
      }, life);
    },

    // ----------------------------------------------------------- skeletons
    loading: function (container, rows) {
      if (!container) return;
      var count = rows || 3;
      var html = '';
      for (var i = 0; i < count; i += 1) {
        html +=
          '<div style="background:#EEF1F9;border-radius:20px;height:74px;margin-bottom:12px;' +
          'animation:englifyPulse 1.4s ease-in-out infinite"></div>';
      }
      container.innerHTML =
        '<style>@keyframes englifyPulse{0%,100%{opacity:1}50%{opacity:.45}}</style>' + html;
    },

    empty: function (message, hint) {
      return (
        '<div style="text-align:center;padding:38px 20px;background:#fff;border-radius:26px;' +
        'border:2px dashed #D4E2EE">' +
        '<div style="font-size:44px;line-height:1" aria-hidden="true">\uD83D\uDCED</div>' +
        '<div style="font-weight:800;font-size:19px;margin-top:12px">' + UI.escape(message) + '</div>' +
        (hint ? '<div style="color:#486582;font-weight:600;margin-top:6px">' + UI.escape(hint) + '</div>' : '') +
        '</div>'
      );
    },

    errorBox: function (error) {
      var message = (error && error.message) || 'Xatolik yuz berdi.';
      return (
        '<div style="background:#FFF1F2;border:2px solid #FFD0D6;color:#B3121F;border-radius:20px;' +
        'padding:16px 18px;font-weight:700">' + UI.escape(message) + '</div>'
      );
    },

    on: function (root, selector, event, handler) {
      (root || document).addEventListener(event, function (domEvent) {
        var target = domEvent.target.closest(selector);
        if (target && (root || document).contains(target)) handler(domEvent, target);
      });
    },

    qs: function (name) {
      return new URLSearchParams(location.search).get(name);
    },

    debounce: function (fn, wait) {
      var timer;
      return function () {
        var args = arguments;
        var self = this;
        clearTimeout(timer);
        timer = setTimeout(function () {
          fn.apply(self, args);
        }, wait || 300);
      };
    },

    /** Fills every [data-field="name"] element inside `scope` with `data[name]`. */
    fill: function (scope, data) {
      (scope || document).querySelectorAll('[data-field]').forEach(function (node) {
        var key = node.getAttribute('data-field');
        if (!(key in data)) return;
        var value = data[key];
        if (node.hasAttribute('data-attr')) {
          node.setAttribute(node.getAttribute('data-attr'), value === null ? '' : value);
        } else {
          node.textContent = value === null || value === undefined ? '' : value;
        }
      });
    }
  };

  window.EnglifyUI = UI;
})();
