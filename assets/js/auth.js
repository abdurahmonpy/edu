/*!
 * Englify — session, route guarding and shared chrome (window.EnglifyAuth).
 * ---------------------------------------------------------------------------
 * Load AFTER config.js, api.js and ui.js.
 *
 * Page contract
 * -------------
 *   <body data-auth="required">   redirect to kirish.html when logged out
 *   <body data-auth="optional">   never redirect (landing page)
 *   <body data-auth="public">     never redirect, never fetch the profile
 *   <body data-auth="guest">      redirect to app.html when ALREADY logged in
 *
 * Elements it fills automatically when present:
 *   [data-user-name] [data-user-email] [data-user-points] [data-user-level]
 *   [data-user-streak] [data-user-initials] [data-user-avatar]
 *   [data-auth="user"]  -> hidden while logged out
 *   [data-auth="login"] -> hidden while logged in
 *   [data-badge="notifications"] [data-badge="chat"]
 */
(function () {
  'use strict';

  var api = window.EnglifyApi;
  var UI = window.EnglifyUI;
  if (!api || !UI) {
    console.error('[Englify] auth.js requires config.js, api.js and ui.js');
    return;
  }

  var LEVEL_TITLES = {
    starter: 'Starter',
    beginner: 'Beginner',
    elementary: 'Elementary',
    'pre-intermediate': 'Pre-Intermediate',
    intermediate: 'Intermediate',
    'upper-intermediate': 'Upper-Intermediate',
    advanced: 'Advanced'
  };

  var state = {
    user: api.user(),
    stats: null,
    notifications: 0,
    chats: 0,
    ready: null
  };

  function loginUrl() {
    var next = location.pathname.split('/').pop() + location.search + location.hash;
    return 'kirish.html?next=' + encodeURIComponent(next || 'app.html');
  }

  function setLoggedInChrome(isLoggedIn) {
    document.querySelectorAll('[data-auth="user"]').forEach(function (node) {
      node.hidden = !isLoggedIn;
    });
    document.querySelectorAll('[data-auth="login"]').forEach(function (node) {
      node.hidden = isLoggedIn;
    });
    document.querySelectorAll('[data-auth="guest"]').forEach(function (node) {
      node.hidden = isLoggedIn;
    });
  }

  function levelTitle(level) {
    return LEVEL_TITLES[level] || (level ? level[0].toUpperCase() + level.slice(1) : 'Starter');
  }

  function paintUser(user) {
    if (!user) return;
    var initials = UI.initials(user.full_name);
    document.querySelectorAll('[data-user-name]').forEach(function (node) {
      node.textContent = user.full_name;
    });
    document.querySelectorAll('[data-user-email]').forEach(function (node) {
      node.textContent = user.email;
    });
    document.querySelectorAll('[data-user-points]').forEach(function (node) {
      node.textContent = UI.number(user.points);
    });
    document.querySelectorAll('[data-user-level]').forEach(function (node) {
      node.textContent = user.level_title || levelTitle(user.level);
    });
    document.querySelectorAll('[data-user-streak]').forEach(function (node) {
      node.textContent = UI.number(user.streak_days);
    });
    document.querySelectorAll('[data-user-initials]').forEach(function (node) {
      node.textContent = initials;
    });
    document.querySelectorAll('[data-user-avatar]').forEach(function (node) {
      node.innerHTML = UI.avatar(user, Number(node.getAttribute('data-size')) || 44);
    });
    document.querySelectorAll('[data-user-goal]').forEach(function (node) {
      node.textContent = UI.number(user.daily_goal_minutes);
    });
  }

  function paintBadges() {
    document.querySelectorAll('[data-badge="notifications"]').forEach(function (node) {
      var count = state.notifications;
      node.textContent = count > 99 ? '99+' : String(count);
      node.hidden = count <= 0;
    });
    document.querySelectorAll('[data-badge="chat"]').forEach(function (node) {
      var count = state.chats;
      node.textContent = count > 99 ? '99+' : String(count);
      node.hidden = count <= 0;
    });
  }

  // ------------------------------------------------------------------ socket
  var socket = null;
  var socketRetry = 0;

  function connectNotifications() {
    if (!api.isLoggedIn() || typeof WebSocket === 'undefined') return;
    if (socket && socket.readyState <= 1) return;

    try {
      socket = new WebSocket(api.wsUrl('/ws/notifications'));
    } catch (error) {
      return;
    }

    socket.onopen = function () {
      socketRetry = 0;
    };

    socket.onmessage = function (event) {
      var frame;
      try {
        frame = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      if (frame.type === 'message.notification') {
        state.chats += 1;
        paintBadges();
        UI.toast(
          (frame.data && frame.data.title ? frame.data.title + ': ' : '') +
            ((frame.data && frame.data.body) || 'Yangi xabar'),
          'info'
        );
      } else if (frame.type === 'notification.created') {
        state.notifications += 1;
        paintBadges();
        UI.toast((frame.data && frame.data.title) || 'Yangi bildirishnoma', 'info');
      } else if (frame.type === 'notification') {
        state.notifications += 1;
        paintBadges();
      }
      document.dispatchEvent(new CustomEvent('englify:realtime', { detail: frame }));
    };

    socket.onclose = function () {
      socket = null;
      if (!api.isLoggedIn()) return;
      socketRetry = Math.min(socketRetry + 1, 6);
      setTimeout(connectNotifications, 1500 * socketRetry);
    };

    socket.onerror = function () {
      /* onclose handles the retry */
    };
  }

  // ------------------------------------------------------------------- API
  var Auth = {
    state: state,

    on: function (event, handler) {
      document.addEventListener('englify:' + event, handler);
      return Auth;
    },

    levelTitle: levelTitle,

    /** Loads the profile from the server (and refreshes cached user data). */
    me: function (force) {
      if (state.user && !force) return Promise.resolve(state.user);
      return api.get('/auth/me').then(function (user) {
        state.user = user;
        var session = api.session();
        if (session) {
          session.user = user;
          api.setSession(session);
        }
        paintUser(user);
        return user;
      });
    },

    stats: function (force) {
      if (state.stats && !force) return Promise.resolve(state.stats);
      return api.get('/users/me/stats').then(function (stats) {
        state.stats = stats;
        document.dispatchEvent(new CustomEvent('englify:stats', { detail: stats }));
        return stats;
      });
    },

    refreshBadges: function () {
      if (!api.isLoggedIn()) return Promise.resolve();
      return Promise.all([
        api.get('/notifications/unread-count').catch(function () {
          return { unread: 0 };
        }),
        api.get('/chat/unread-count').catch(function () {
          return { unread: 0 };
        })
      ]).then(function (results) {
        state.notifications = (results[0] && results[0].unread) || 0;
        state.chats = (results[1] && results[1].unread) || 0;
        paintBadges();
      });
    },

    logout: function (options) {
      options = options || {};
      var session = api.session();
      var request = session
        ? api
            .post('/auth/logout', {
              refresh_token: session.refresh_token,
              all_devices: !!options.allDevices
            })
            .catch(function () {
              /* logging out locally must work even if the server is unreachable */
            })
        : Promise.resolve();

      return request.then(function () {
        api.clearSession('logout');
        window.location.href = options.redirect || 'kirish.html';
      });
    },

    /** Boots the page according to its `data-auth` mode. */
    boot: function () {
      var mode = document.body.getAttribute('data-auth') || 'optional';
      var loggedIn = api.isLoggedIn();
      setLoggedInChrome(loggedIn);

      if (mode === 'guest' && loggedIn) {
        window.location.replace(UI.qs('next') || 'app.html');
        return Promise.resolve(null);
      }

      if (mode === 'required' && !loggedIn) {
        window.location.replace(loginUrl());
        return Promise.resolve(null);
      }

      if (!loggedIn) {
        document.dispatchEvent(new CustomEvent('englify:guest'));
        return Promise.resolve(null);
      }

      paintUser(state.user);

      state.ready = Auth.me()
        .then(function (user) {
          document.dispatchEvent(new CustomEvent('englify:user', { detail: user }));
          if (mode !== 'public') {
            Auth.refreshBadges();
            connectNotifications();
          }
          return user;
        })
        .catch(function (error) {
          if (error && error.status === 401) {
            api.clearSession('unauthorized');
            if (mode === 'required') window.location.replace(loginUrl());
            return null;
          }
          console.warn('[Englify] profile load failed:', error && error.message);
          return state.user;
        });

      return state.ready;
    },

    require: function () {
      if (!api.isLoggedIn()) {
        window.location.replace(loginUrl());
        return Promise.reject(new Error('not authenticated'));
      }
      return state.ready || Auth.boot();
    },

    optional: function () {
      return state.ready || Auth.boot();
    },

    /** Wires every [data-action="logout"] control on the page. */
    bindLogout: function () {
      document.querySelectorAll('[data-action="logout"]').forEach(function (node) {
        node.addEventListener('click', function (event) {
          event.preventDefault();
          Auth.logout({ allDevices: node.getAttribute('data-all-devices') === 'true' });
        });
      });
    }
  };

  api.on('logout', function () {
    if (socket) {
      try {
        socket.close();
      } catch (error) {
        /* ignore */
      }
      socket = null;
    }
    state.user = null;
    state.stats = null;
  });

  window.EnglifyAuth = Auth;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      Auth.boot();
      Auth.bindLogout();
    });
  } else {
    Auth.boot();
    Auth.bindLogout();
  }
})();
