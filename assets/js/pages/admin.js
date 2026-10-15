(function () {
  'use strict';

  var Auth = window.EnglifyAuth;
  var Api = window.EnglifyApi;
  var UI = window.EnglifyUI;
  if (!Auth || !Api || !UI) return;

  var view = 'overview';
  var leadStatus = 'all';
  var leadQuery = '';
  var leadPage = 0;
  var userPage = 0;
  var userQuery = '';
  var leads = [];
  var recentLeads = [];
  var leadsLoaded = false;
  var users = [];
  var leadTotal = 0;
  var stageCounts = { new: 0, contacted: 0, converted: 0, closed: 0 };
  var userTotal = 0;
  var toastTimer = null;
  var PAGE_SIZE = 25;
  var STATUS = {
    new: { label: 'Yangi', tone: 'blue' },
    contacted: { label: 'Bog‘lanildi', tone: 'blue' },
    converted: { label: 'Mijoz bo‘ldi', tone: 'blue' },
    closed: { label: 'Yopildi', tone: 'blue' }
  };

  function el(id) { return document.getElementById(id); }
  function escape(value) { return UI.escape(value == null ? '' : value); }
  function showToast(message, error) {
    var node = el('toast');
    node.textContent = message;
    node.style.background = error ? '#8f3047' : '#08264D';
    node.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { node.hidden = true; }, 3200);
  }
  function setLoading(message) {
    var node = el('pageState');
    node.textContent = message || '';
    node.hidden = !message;
    node.classList.toggle('error', Boolean(message));
  }
  function apiError(error) {
    if (error && error.status === 403) return 'Admin huquqi yetarli emas.';
    if (error && error.status === 401) return 'Sessiya tugagan. Qaytadan kiring.';
    return (error && error.message) || 'Ma’lumot yuklanmadi.';
  }
  function initials(value) { return UI.initials(value); }
  function getPage(items, page) { return items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE); }
  function setView(next) {
    view = next;
    document.querySelectorAll('[data-view]').forEach(function (section) {
      section.hidden = section.getAttribute('data-view') !== view;
    });
    document.querySelectorAll('[data-view-link]').forEach(function (button) {
      if (button.getAttribute('data-view-link') === view) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    el('pageTitle').textContent = view === 'overview' ? 'Umumiy ko‘rinish' : view === 'leads' ? 'Lidlar · CRM' : 'Foydalanuvchilar';
    setLoading('');
    if (view === 'leads' && !leadsLoaded) loadLeads();
    if (view === 'users') loadUsers();
  }
  function renderPipeline() {
    var stages = ['new', 'contacted', 'converted', 'closed'];
    el('pipeline').innerHTML = stages.map(function (status) {
      var count = stageCounts[status] || 0;
      return '<div class="stage"><div class="stage-name">' + STATUS[status].label + '</div><div class="stage-count">' + UI.number(count) + '</div></div>';
    }).join('');
  }
  function renderRecent() {
    var list = recentLeads.slice(0, 5);
    el('recentLeads').innerHTML = list.length ? list.map(function (lead) {
      return '<div class="lead-mini"><div><div class="lead-mini-name">' + escape(lead.name) + '</div><div class="lead-mini-phone">' + escape(lead.phone) + '</div></div><span class="status-badge">' + escape((STATUS[lead.status] || STATUS.new).label) + '</span></div>';
    }).join('') : '<div class="empty">Hozircha murojaatlar yo‘q.</div>';
  }
  function loadOverview() {
    var stageRequests = ['new', 'contacted', 'converted', 'closed'].map(function (status) {
      return Api.get('/admin/leads?status=' + status + '&limit=1&offset=0');
    });
    return Promise.all([Api.get('/admin/overview'), Api.get('/admin/leads?limit=5&offset=0')].concat(stageRequests)).then(function (results) {
      var stats = results[0];
      recentLeads = results[1].items || [];
      ['new', 'contacted', 'converted', 'closed'].forEach(function (status, index) {
        stageCounts[status] = results[index + 2].total || 0;
      });
      el('metricUsers').textContent = UI.number(stats.users_total);
      el('metricActive').textContent = UI.number(stats.users_active);
      el('metricNewUsers').textContent = 'Oxirgi 7 kunda: ' + UI.number(stats.users_new_7d);
      el('metricLeads').textContent = UI.number(stats.leads_total);
      el('metricNewLeads').textContent = UI.number(stats.leads_new);
      renderPipeline();
      renderRecent();
    });
  }
  function statusOptions(selected) {
    return Object.keys(STATUS).map(function (key) {
      return '<option value="' + key + '"' + (selected === key ? ' selected' : '') + '>' + STATUS[key].label + '</option>';
    }).join('');
  }
  function renderLeadTable() {
    var items = leads;
    var table = '<table class="data-table"><thead><tr><th>Mijoz</th><th>Aloqa</th><th>Manba</th><th>Sana</th><th>CRM holati</th></tr></thead><tbody>';
    table += items.map(function (lead) {
      var contact = '<a class="phone-link" href="tel:' + escape(lead.phone) + '">' + escape(lead.phone) + '</a>';
      if (lead.email) contact += '<span class="subtext">' + escape(lead.email) + '</span>';
      return '<tr><td><span class="person">' + escape(lead.name) + '</span><span class="subtext">ID: ' + escape(lead.id).slice(0, 8) + '</span></td><td>' + contact + '</td><td>' + escape(lead.source || 'Sayt') + '</td><td>' + escape(UI.date(lead.created_at)) + '</td><td><select class="status-select" data-lead-status="' + escape(lead.id) + '" aria-label="' + escape(lead.name) + ' holati">' + statusOptions(lead.status) + '</select></td></tr>';
    }).join('');
    table += '</tbody></table>';
    el('leadTable').innerHTML = items.length ? table : '<div class="empty">Bu qidiruv bo‘yicha lid topilmadi.</div>';
    el('leadCount').textContent = UI.number(leadTotal) + ' ta';
    el('leadPageInfo').textContent = leadTotal ? (leadPage + 1) + ' / ' + Math.ceil(leadTotal / PAGE_SIZE) + '-sahifa' : '';
    el('leadPrev').disabled = leadPage <= 0;
    el('leadNext').disabled = (leadPage + 1) * PAGE_SIZE >= leadTotal;
  }
  function loadLeads() {
    setLoading('Lidlar yuklanmoqda…');
    var query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(leadPage * PAGE_SIZE) });
    if (leadStatus !== 'all') query.set('status', leadStatus);
    if (leadQuery) query.set('q', leadQuery);
    return Api.get('/admin/leads?' + query.toString()).then(function (result) {
      leads = result.items || [];
      leadTotal = result.total || 0;
      leadsLoaded = true;
      renderLeadTable();
      setLoading('');
    }).catch(function (error) {
      setLoading(apiError(error));
    });
  }
  function updateLead(leadId, status, select) {
    select.disabled = true;
    Api.patch('/admin/leads/' + encodeURIComponent(leadId), { status: status }).then(function (updated) {
      leads = leads.map(function (lead) { return lead.id === leadId ? updated : lead; });
      showToast('Lid holati yangilandi.');
      loadLeads();
      loadOverview();
    }).catch(function (error) {
      select.value = (leads.find(function (lead) { return lead.id === leadId; }) || {}).status || 'new';
      select.disabled = false;
      showToast(apiError(error), true);
    });
  }
  function renderUserTable() {
    var items = getPage(users, userPage);
    var table = '<table class="data-table"><thead><tr><th>Foydalanuvchi</th><th>Telefon</th><th>Daraja</th><th>Roli</th><th>Holati</th><th>Qo‘shilgan</th></tr></thead><tbody>';
    table += items.map(function (user) {
      var self = user.id === (Auth.user() || {}).id;
      return '<tr><td><span class="person">' + escape(user.full_name) + '</span><span class="subtext">' + escape(user.email || 'Email ulanmagan') + '</span></td><td>' + escape(user.phone || '—') + '</td><td>' + escape(user.level_title || user.level || '—') + '</td><td><select class="role-select" data-user-role="' + escape(user.id) + '"' + (self ? ' disabled title="O‘z rolingizni o‘zgartirib bo‘lmaydi"' : '') + '><option value="student"' + (user.role === 'student' ? ' selected' : '') + '>O‘quvchi</option><option value="teacher"' + (user.role === 'teacher' ? ' selected' : '') + '>O‘qituvchi</option><option value="admin"' + (user.role === 'admin' ? ' selected' : '') + '>Admin</option></select></td><td><label class="switch"><input type="checkbox" data-user-active="' + escape(user.id) + '"' + (user.is_active ? ' checked' : '') + (self ? ' disabled title="O‘z hisobingizni bloklab bo‘lmaydi"' : '') + '>Faol</label></td><td>' + escape(UI.date(user.created_at)) + '</td></tr>';
    }).join('');
    table += '</tbody></table>';
    el('userTable').innerHTML = items.length ? table : '<div class="empty">Foydalanuvchilar topilmadi.</div>';
    el('userCount').textContent = UI.number(userTotal) + ' ta foydalanuvchi';
    el('userPageInfo').textContent = userTotal ? (userPage + 1) + ' / ' + Math.ceil(userTotal / PAGE_SIZE) + '-sahifa' : '';
    el('userPrev').disabled = userPage <= 0;
    el('userNext').disabled = (userPage + 1) * PAGE_SIZE >= userTotal;
  }
  function loadUsers() {
    setLoading('Foydalanuvchilar yuklanmoqda…');
    var query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(userPage * PAGE_SIZE) });
    if (userQuery) query.set('q', userQuery);
    return Api.get('/admin/users?' + query.toString()).then(function (result) {
      users = result.items || [];
      userTotal = result.total || 0;
      renderUserTable();
      setLoading('');
    }).catch(function (error) { setLoading(apiError(error)); });
  }
  function updateUser(userId, change, source) {
    source.disabled = true;
    Api.patch('/admin/users/' + encodeURIComponent(userId), change).then(function (updated) {
      users = users.map(function (user) { return user.id === userId ? updated : user; });
      showToast('Foydalanuvchi ma’lumoti yangilandi.');
      renderUserTable();
    }).catch(function (error) {
      showToast(apiError(error), true);
      loadUsers();
    });
  }
  function renderFilters() {
    var filters = [{ key: 'all', label: 'Barchasi' }].concat(Object.keys(STATUS).map(function (key) { return { key: key, label: STATUS[key].label }; }));
    el('leadFilters').innerHTML = filters.map(function (item) {
      return '<button type="button" class="filter" data-lead-filter="' + item.key + '" aria-pressed="' + String(leadStatus === item.key) + '">' + item.label + '</button>';
    }).join('');
  }
  function loadAll() {
    setLoading('Boshqaruv ma’lumotlari yuklanmoqda…');
    var currentViewLoad = view === 'users' ? loadUsers() : view === 'leads' ? loadLeads() : Promise.resolve();
    Promise.all([loadOverview(), currentViewLoad]).then(function () {
      setLoading('');
    }).catch(function (error) { setLoading(apiError(error)); });
  }

  document.querySelectorAll('[data-view-link]').forEach(function (button) {
    button.addEventListener('click', function () { setView(button.getAttribute('data-view-link')); });
  });
  document.querySelectorAll('[data-open-view]').forEach(function (button) {
    button.addEventListener('click', function () { setView(button.getAttribute('data-open-view')); });
  });
  el('leadFilters').addEventListener('click', function (event) {
    var button = event.target.closest('[data-lead-filter]');
    if (!button) return;
    leadStatus = button.getAttribute('data-lead-filter');
    leadPage = 0;
    renderFilters();
    loadLeads();
  });
  var leadSearchTimer;
  el('leadSearch').addEventListener('input', function () {
    clearTimeout(leadSearchTimer);
    leadSearchTimer = setTimeout(function () {
      leadQuery = el('leadSearch').value.trim();
      leadPage = 0;
      loadLeads();
    }, 220);
  });
  el('leadTable').addEventListener('change', function (event) {
    var select = event.target.closest('[data-lead-status]');
    if (select) updateLead(select.getAttribute('data-lead-status'), select.value, select);
  });
  el('leadPrev').addEventListener('click', function () { leadPage = Math.max(0, leadPage - 1); loadLeads(); });
  el('leadNext').addEventListener('click', function () { leadPage += 1; loadLeads(); });
  el('userTable').addEventListener('change', function (event) {
    var role = event.target.closest('[data-user-role]');
    var active = event.target.closest('[data-user-active]');
    if (role) updateUser(role.getAttribute('data-user-role'), { role: role.value }, role);
    if (active) updateUser(active.getAttribute('data-user-active'), { is_active: active.checked }, active);
  });
  var searchTimer;
  el('userSearch').addEventListener('input', function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { userQuery = el('userSearch').value.trim(); userPage = 0; loadUsers(); }, 250);
  });
  el('userPrev').addEventListener('click', function () { userPage = Math.max(0, userPage - 1); loadUsers(); });
  el('userNext').addEventListener('click', function () { userPage += 1; loadUsers(); });
  el('refreshButton').addEventListener('click', loadAll);
  renderFilters();

  Auth.require().then(function (user) {
    if (!user || user.role !== 'admin') {
      el('adminShell').hidden = true;
      el('accessDenied').hidden = false;
      return;
    }
    el('adminShell').hidden = false;
    el('adminName').textContent = user.full_name || 'Administrator';
    el('adminAvatar').textContent = initials(user.full_name);
    loadAll();
  }).catch(function () {});
})();
