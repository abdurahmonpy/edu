/*!
 * Englify — HTTP client.
 * ---------------------------------------------------------------------------
 * Responsibilities:
 *   - keep the access/refresh token pair in localStorage
 *   - attach `Authorization: Bearer <token>` automatically
 *   - transparently refresh an expired access token once per request
 *   - normalise errors into `ApiError` with a human readable Uzbek message
 *   - expose small `on()/emit()` hooks so pages can react to logout/login
 *
 * Public surface (window.EnglifyApi):
 *   .get(path, opts) .post(path, body, opts) .patch(path, body, opts) .del(path, opts)
 *   .request(path, opts)
 *   .session()            -> {access_token, refresh_token, user} | null
 *   .setSession(payload)  .clearSession()  .user()  .isLoggedIn()
 *   .authHeaders()        .on(event, handler)
 *   .url(path)            .wsUrl(path)
 *   .ApiError
 */
(function () {
  'use strict';

  var cfg = window.EnglifyConfig || { prefix: '/api/v1', wsPrefix: '' };
  var STORAGE_KEY = 'englify.session.v1';

  function ApiError(message, status, body) {
    var error = Error.call(this, message);
    this.name = 'ApiError';
    this.message = message || 'Xatolik yuz berdi.';
    this.status = status || 0;
    this.body = body || null;
    this.detail = (body && body.detail) || null;
    this.errors = (body && body.errors) || null;
    this.stack = error.stack;
  }
  ApiError.prototype = Object.create(Error.prototype);
  ApiError.prototype.constructor = ApiError;

  // ---------------------------------------------------------------- session
  function readSession() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || !parsed.access_token) return null;
      return parsed;
    } catch (error) {
      return null;
    }
  }

  function writeSession(payload) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch (error) {
      /* private mode / quota — the session simply won't survive a reload */
    }
  }

  var listeners = {};
  function emit(event, payload) {
    (listeners[event] || []).forEach(function (handler) {
      try {
        handler(payload);
      } catch (error) {
        console.error('[Englify] listener error for "' + event + '"', error);
      }
    });
  }

  var api = {
    ApiError: ApiError,

    url: function (path) {
      if (/^https?:\/\//i.test(path)) return path;
      var clean = String(path || '').replace(/^\/+/, '');
      if (clean.indexOf('api/v1/') === 0 || clean === 'api/v1') {
        return cfg.base + '/' + clean;
      }
      return cfg.prefix + '/' + clean;
    },

    wsUrl: function (path, token) {
      var clean = String(path || '').replace(/^\/+/, '');
      var url = cfg.wsPrefix + '/' + clean;
      var value = token || (readSession() || {}).access_token;
      if (value) url += (url.indexOf('?') === -1 ? '?' : '&') + 'token=' + encodeURIComponent(value);
      return url;
    },

    session: readSession,

    setSession: function (payload) {
      var previous = readSession();
      var next = {
        access_token: payload.access_token,
        refresh_token: payload.refresh_token,
        expires_in: payload.expires_in,
        user: payload.user || (previous && previous.user) || null
      };
      writeSession(next);
      if (!previous) emit('login', next);
      emit('session', next);
      return next;
    },

    clearSession: function (reason) {
      var previous = readSession();
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch (error) {
        /* ignore */
      }
      if (previous) emit('logout', { reason: reason || 'manual' });
      emit('session', null);
    },

    user: function () {
      var session = readSession();
      return session ? session.user : null;
    },

    isLoggedIn: function () {
      return !!readSession();
    },

    authHeaders: function () {
      var session = readSession();
      return session && session.access_token
        ? { Authorization: 'Bearer ' + session.access_token }
        : {};
    },

    on: function (event, handler) {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(handler);
      return function off() {
        listeners[event] = listeners[event].filter(function (item) {
          return item !== handler;
        });
      };
    },

    // ------------------------------------------------------------------ core
    request: function (path, options) {
      options = options || {};
      var method = (options.method || 'GET').toUpperCase();
      var headers = Object.assign({ Accept: 'application/json' }, options.headers || {});
      var body = options.body;

      if (body !== undefined && body !== null && !(body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(body);
      }

      if (options.auth !== false) {
        Object.assign(headers, api.authHeaders());
      }

      var init = {
        method: method,
        headers: headers,
        body: body === undefined ? undefined : body,
        credentials: cfg.isCrossOrigin ? 'omit' : 'same-origin',
        mode: 'cors'
      };

      return fetch(api.url(path), init)
        .catch(function (networkError) {
          throw new ApiError(
            'Serverga ulanib bo\u2019lmadi. Internet aloqasini tekshiring.',
            0,
            { detail: String(networkError && networkError.message) }
          );
        })
        .then(function (response) {
          if (response.status === 204) return null;

          return response
            .text()
            .then(function (text) {
              var data = null;
              if (text) {
                try {
                  data = JSON.parse(text);
                } catch (error) {
                  data = { detail: text.slice(0, 400) };
                }
              }
              return { response: response, data: data };
            })
            .then(function (result) {
              var response = result.response;
              var data = result.data;

              // Token expired -> refresh once and replay the request.
              if (
                response.status === 401 &&
                options.auth !== false &&
                !options._retried &&
                path.indexOf('/auth/refresh') === -1 &&
                api.session()
              ) {
                return api.refresh().then(function (ok) {
                  if (!ok) throw new ApiError('Sessiya muddati tugagan. Qaytadan kiring.', 401, data);
                  var replayed = Object.assign({}, options, { _retried: true });
                  return api.request(path, replayed);
                });
              }

              if (!response.ok) {
                var message =
                  (data && (data.detail || (data.errors && data.errors[0]))) ||
                  'Xatolik yuz berdi (' + response.status + ').';
                throw new ApiError(message, response.status, data);
              }
              return data;
            });
        });
    },

    get: function (path, options) {
      return api.request(path, Object.assign({ method: 'GET' }, options));
    },
    post: function (path, body, options) {
      return api.request(path, Object.assign({ method: 'POST', body: body }, options));
    },
    patch: function (path, body, options) {
      return api.request(path, Object.assign({ method: 'PATCH', body: body }, options));
    },
    put: function (path, body, options) {
      return api.request(path, Object.assign({ method: 'PUT', body: body }, options));
    },
    del: function (path, options) {
      return api.request(path, Object.assign({ method: 'DELETE' }, options));
    },

    // --------------------------------------------------------------- refresh
    _refreshing: null,

    refresh: function () {
      if (api._refreshing) return api._refreshing;

      var session = readSession();
      if (!session || !session.refresh_token) {
        api.clearSession('expired');
        return Promise.resolve(false);
      }

      api._refreshing = fetch(api.url('/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ refresh_token: session.refresh_token }),
        credentials: cfg.isCrossOrigin ? 'omit' : 'same-origin',
        mode: 'cors'
      })
        .then(function (response) {
          if (!response.ok) return false;
          return response.json().then(function (data) {
            api.setSession(data);
            return true;
          });
        })
        .catch(function () {
          return false;
        })
        .then(function (ok) {
          api._refreshing = null;
          if (!ok) api.clearSession('expired');
          return ok;
        });

      return api._refreshing;
    }
  };

  window.EnglifyApi = api;
})();
