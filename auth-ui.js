/**
 * eduAuth — sayt bo'ylab umumiy sessiya + Kirish/Ro'yxatdan o'tish modali.
 * Backend: /api/auth (httpOnly cookie). Kalitlar brauzerga chiqmaydi.
 * Ishlatish:  <script src="auth-ui.js"></script>  keyin:
 *   eduAuth.getSession()          -> Promise<user|null>
 *   eduAuth.onChange(fn)          -> sessiya o'zgarsa chaqiriladi
 *   eduAuth.openModal('login')    -> modallni ochish ('login'|'signup')
 *   eduAuth.mountAuthBar()        -> burchakda Kirish/Chiqish chipi
 */
window.eduAuth = (function () {
  'use strict';

  var state = { user: null, loaded: false, promise: null, listeners: [] };
  var API = '/api/auth';

  function call(method, body) {
    return fetch(method === 'GET' ? API + '?action=me' : API, {
      method: method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: method === 'GET' ? undefined : JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        return { status: r.status, data: data };
      });
    });
  }

  function getSession() {
    if (state.loaded) return Promise.resolve(state.user);
    if (state.promise) return state.promise;
    state.promise = call('GET').then(function (r) {
      state.user = r.status === 200 && r.data.user ? r.data.user : null;
      state.loaded = true;
      return state.user;
    }).catch(function () {
      state.loaded = true; state.user = null; return null;
    });
    return state.promise;
  }

  function notify() {
    state.listeners.forEach(function (fn) { try { fn(state.user); } catch (e) {} });
    refreshBar();
  }
  function onChange(fn) {
    state.listeners.push(fn);
    getSession().then(function () { try { fn(state.user); } catch (e) {} });
    refreshBar();
  }
  function setUser(u) { state.user = u; state.loaded = true; notify(); }
  function getUser() { return state.user; }

  // ---------------- Modal ----------------

  function ensureModal() {
    if (document.getElementById('edu-auth-overlay')) return;
    var wrap = document.createElement('div');
    wrap.id = 'edu-auth-overlay';
    wrap.style.cssText = 'position:fixed;inset:0;background:rgba(10,20,50,.55);z-index:9999;display:none;align-items:center;justify-content:center;padding:16px';
    wrap.innerHTML =
      '<div style="position:relative;background:#fff;color:#14172B;border-radius:28px;padding:26px 24px 22px;width:min(420px,94vw);box-shadow:0 18px 50px rgba(10,40,120,.35)">' +
      '<button id="edu-auth-close" aria-label="Yopish" style="position:absolute;top:14px;right:14px;border:0;background:#EEF1FA;border-radius:999px;width:34px;height:34px;font-size:17px;font-weight:800;color:#6A5A92;cursor:pointer">&times;</button>' +
      '<div style="display:flex;gap:8px;margin-bottom:18px">' +
      '<button id="edu-auth-tab-login" style="flex:1;height:46px;border:0;border-radius:14px;font-weight:800;font-size:15px;cursor:pointer;background:#0A93F5;color:#fff">Kirish</button>' +
      '<button id="edu-auth-tab-signup" style="flex:1;height:46px;border:2px solid #D6DCF0;border-radius:14px;font-weight:800;font-size:15px;cursor:pointer;background:#fff;color:#6A5A92">Ro‘yxatdan o‘tish</button>' +
      '</div>' +
      '<div id="edu-auth-name-row" style="display:none;flex-direction:column;gap:6px;margin-bottom:12px">' +
      '<label style="font-weight:700;font-size:14px">Ismingiz</label>' +
      '<input id="edu-auth-name" type="text" autocomplete="name" maxlength="120" style="height:52px;border:2px solid #D6DCF0;border-bottom-width:4px;border-radius:14px;padding:0 14px;font-size:16px;font-weight:600;box-sizing:border-box;width:100%">' +
      '</div>' +
      '<div style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px">' +
      '<label style="font-weight:700;font-size:14px">Email</label>' +
      '<input id="edu-auth-email" type="email" autocomplete="email" style="height:52px;border:2px solid #D6DCF0;border-bottom-width:4px;border-radius:14px;padding:0 14px;font-size:16px;font-weight:600;box-sizing:border-box;width:100%">' +
      '</div>' +
      '<div style="display:flex;flex-direction:column;gap:6px;margin-bottom:10px">' +
      '<label style="font-weight:700;font-size:14px">Parol <span id="edu-auth-hint" style="display:none;font-weight:600;color:#8A88B3">(kamida 8 belgi)</span></label>' +
      '<input id="edu-auth-password" type="password" autocomplete="current-password" style="height:52px;border:2px solid #D6DCF0;border-bottom-width:4px;border-radius:14px;padding:0 14px;font-size:16px;font-weight:600;box-sizing:border-box;width:100%">' +
      '</div>' +
      '<div id="edu-auth-error" style="display:none;color:#D93025;font-weight:700;font-size:14px;margin-bottom:10px"></div>' +
      '<button id="edu-auth-submit" style="width:100%;height:56px;border:0;border-bottom:5px solid #0B8A57;border-radius:16px;background:linear-gradient(115deg,#35F59A 0 30px,#55FFB0 30px 60px);color:#14172B;font-weight:800;font-size:17px;cursor:pointer">Kirish</button>' +
      '</div>';
    document.body.appendChild(wrap);

    var mode = 'login';
    function setMode(m) {
      mode = m;
      var isSignup = m === 'signup';
      document.getElementById('edu-auth-name-row').style.display = isSignup ? 'flex' : 'none';
      document.getElementById('edu-auth-hint').style.display = isSignup ? 'inline' : 'none';
      document.getElementById('edu-auth-password').setAttribute('autocomplete', isSignup ? 'new-password' : 'current-password');
      document.getElementById('edu-auth-submit').textContent = isSignup ? 'Ro‘yxatdan o‘tish' : 'Kirish';
      var tl = document.getElementById('edu-auth-tab-login');
      var ts = document.getElementById('edu-auth-tab-signup');
      tl.style.background = isSignup ? '#fff' : '#0A93F5';
      tl.style.color = isSignup ? '#6A5A92' : '#fff';
      tl.style.border = isSignup ? '2px solid #D6DCF0' : '0';
      ts.style.background = isSignup ? '#0A93F5' : '#fff';
      ts.style.color = isSignup ? '#fff' : '#6A5A92';
      ts.style.border = isSignup ? '0' : '2px solid #D6DCF0';
      hideError();
    }
    function showError(msg) {
      var el = document.getElementById('edu-auth-error');
      el.textContent = msg;
      el.style.display = 'block';
    }
    function hideError() { document.getElementById('edu-auth-error').style.display = 'none'; }

    document.getElementById('edu-auth-tab-login').addEventListener('click', function () { setMode('login'); });
    document.getElementById('edu-auth-tab-signup').addEventListener('click', function () { setMode('signup'); });
    document.getElementById('edu-auth-close').addEventListener('click', closeModal);
    wrap.addEventListener('click', function (e) { if (e.target === wrap) closeModal(); });

    document.getElementById('edu-auth-submit').addEventListener('click', function () {
      var btn = this;
      var name = document.getElementById('edu-auth-name').value.trim();
      var email = document.getElementById('edu-auth-email').value.trim();
      var password = document.getElementById('edu-auth-password').value;
      hideError();

      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return showError('To‘g‘ri email kiriting.');
      if (password.length < 8) return showError('Parol kamida 8 belgi bo‘lishi kerak.');
      if (mode === 'signup' && name.length < 2) return showError('Ismingizni kiriting (kamida 2 belgi).');

      btn.disabled = true;
      btn.textContent = 'Yuborilmoqda...';
      call('POST', { action: mode, name: name, email: email, password: password })
        .then(function (r) {
          btn.disabled = false;
          setMode(mode);
          if (r.status === 200 && r.data.user) {
            document.getElementById('edu-auth-password').value = '';
            setUser(r.data.user);
            closeModal();
            return;
          }
          showError((r.data && r.data.message) || 'Xatolik yuz berdi. Qayta urinib ko‘ring.');
        })
        .catch(function () {
          btn.disabled = false;
          setMode(mode);
          showError('Tarmoq xatosi. Internetni tekshiring.');
        });
    });

    setMode('login');
  }

  function openModal(mode) {
    ensureModal();
    document.getElementById('edu-auth-overlay').style.display = 'flex';
    var tabId = mode === 'signup' ? 'edu-auth-tab-signup' : 'edu-auth-tab-login';
    var t = document.getElementById(tabId);
    if (t) t.click();
    setTimeout(function () {
      var f = document.getElementById(mode === 'signup' ? 'edu-auth-name' : 'edu-auth-email');
      if (f) f.focus();
    }, 50);
  }

  function closeModal() {
    var o = document.getElementById('edu-auth-overlay');
    if (o) o.style.display = 'none';
  }

  function logout() {
    call('POST', { action: 'logout' }).catch(function () {}).then(function () {
      setUser(null);
    });
  }

  // ---------------- Burchak chipi ----------------

  var barEl = null;
  function refreshBar() {
    if (!barEl || !document.body.contains(barEl)) return;
    if (state.user) {
      var name = String(state.user.name || 'Hisob').split(' ')[0];
      barEl.innerHTML = '';
      var label = document.createElement('span');
      label.textContent = name;
      label.style.cssText = 'font-weight:800;font-size:13px;color:#14172B';
      var btn = document.createElement('button');
      btn.textContent = 'Chiqish';
      btn.style.cssText = 'border:0;background:#FFE3E3;color:#C62828;border-radius:999px;padding:6px 12px;font-weight:800;font-size:12px;cursor:pointer;margin-left:8px';
      btn.addEventListener('click', function () { logout(); });
      barEl.appendChild(label);
      barEl.appendChild(btn);
    } else {
      barEl.innerHTML = '';
      var b2 = document.createElement('button');
      b2.textContent = 'Kirish';
      b2.style.cssText = 'border:0;background:#0A93F5;color:#fff;border-radius:999px;padding:8px 16px;font-weight:800;font-size:13px;cursor:pointer;box-shadow:0 6px 16px rgba(10,147,245,.4)';
      b2.addEventListener('click', function () { openModal('login'); });
      barEl.appendChild(b2);
    }
  }

  function mountAuthBar() {
    if (barEl && document.body.contains(barEl)) return;
    barEl = document.createElement('div');
    barEl.id = 'edu-auth-bar';
    barEl.style.cssText = 'position:fixed;left:14px;bottom:14px;z-index:9000;display:flex;align-items:center;background:#fff;border:2px solid #E6E8F2;border-radius:999px;padding:6px 10px;box-shadow:0 8px 22px rgba(10,40,120,.18)';
    document.body.appendChild(barEl);
    refreshBar();
    getSession().then(refreshBar);
  }

  return {
    getSession: getSession,
    getUser: getUser,
    onChange: onChange,
    openModal: openModal,
    closeModal: closeModal,
    logout: logout,
    mountAuthBar: mountAuthBar
  };
})();
