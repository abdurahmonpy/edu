/*!
 * Englify — "Suhbatlar" (chat.html) page logic.
 * ---------------------------------------------------------------------------
 * Talks to /chat/* over REST and /ws/chat/{id} for realtime, and degrades to a
 * 15 s polling loop when WebSockets are unavailable.
 *
 * Requires (loaded before this file): config.js, ui.js, api.js, auth.js.
 */
(function () {
  'use strict';

  var api = window.EnglifyApi;
  var UI = window.EnglifyUI;
  var Auth = window.EnglifyAuth;

  if (!api || !UI || !Auth) {
    console.error('[Englify] chat.js requires config.js, ui.js, api.js and auth.js');
    return;
  }

  var MESSAGE_LIMIT = 50;
  var PREVIEW_CHARS = 90;
  var POLL_MS = 15000;
  var PING_MS = 25000;
  var TYPING_THROTTLE_MS = 2500;
  var MAX_WS_ATTEMPTS = 3;
  var PENDING_CLASS = 'chat-pending';

  var state = {
    conversations: [],
    activeId: null,
    activeTitle: '',
    messages: [],
    socket: null,
    generation: 0,
    attempts: 0,
    closing: false,
    reconnectTimer: null,
    heartbeatTimer: null,
    pollTimer: null,
    typingLastSent: 0,
    typingNode: null,
    typingTimer: null
  };

  // --------------------------------------------------------------- utilities
  function el(id) {
    return document.getElementById(id);
  }

  function me() {
    return api.user() || null;
  }

  function truncate(text, max) {
    var value = String(text === null || text === undefined ? '' : text);
    if (value.length <= max) return value;
    return value.slice(0, max - 1).replace(/\s+$/, '') + '\u2026';
  }

  function avatarLetter(conversation) {
    var value = conversation && conversation.emoji ? String(conversation.emoji) : '';
    if (value) return value;
    var title = (conversation && conversation.title) || '?';
    return title.charAt(0).toUpperCase();
  }

  function findConversation(id) {
    for (var i = 0; i < state.conversations.length; i += 1) {
      if (state.conversations[i].id === id) return state.conversations[i];
    }
    return null;
  }

  function setUnread(id, count) {
    var conversation = findConversation(id);
    if (conversation) conversation.unread_count = Math.max(0, Number(count) || 0);
  }

  function bubbleText(value) {
    return String(value === null || value === undefined ? '' : value);
  }

  // ------------------------------------------------------------------- list
  function conversationRow(conversation) {
    var row = document.createElement('div');
    row.className = 'chat-row';
    row.setAttribute('data-conversation-id', conversation.id);
    row.setAttribute('role', 'button');
    row.setAttribute('tabindex', '0');

    var avatarWrap = document.createElement('div');
    avatarWrap.style.cssText = 'position:relative;flex-shrink:0';

    var badge = document.createElement('div');
    badge.className = 'avatar-badge';
    badge.textContent = avatarLetter(conversation);
    avatarWrap.appendChild(badge);

    var unread = Number(conversation.unread_count) || 0;
    if (unread > 0) {
      var dot = document.createElement('span');
      dot.className = 'chat-unread';
      dot.textContent = unread > 99 ? '99+' : String(unread);
      dot.style.cssText =
        'position:absolute;top:-4px;right:-4px;min-width:20px;height:20px;border-radius:999px;' +
        'background:#FF4757;color:#fff;font-size:11.5px;font-weight:800;display:flex;' +
        'align-items:center;justify-content:center;padding:0 5px;border:2px solid #fff';
      avatarWrap.appendChild(dot);
    }
    row.appendChild(avatarWrap);

    var body = document.createElement('div');
    body.style.cssText = 'flex:1;min-width:0';

    var head = document.createElement('div');
    head.style.cssText = 'display:flex;justify-content:space-between;align-items:baseline';

    var title = document.createElement('span');
    title.className = 'chat-title';
    title.textContent = conversation.title || 'Suhbat';

    var time = document.createElement('span');
    time.className = 'chat-time';
    time.textContent = conversation.last_message_at ? UI.short(conversation.last_message_at) : '';

    head.appendChild(title);
    head.appendChild(time);

    var preview = document.createElement('div');
    preview.className = 'chat-preview';
    preview.textContent = truncate(conversation.last_message && conversation.last_message.body, PREVIEW_CHARS);

    body.appendChild(head);
    body.appendChild(preview);
    row.appendChild(body);
    return row;
  }

  function renderConversations() {
    var list = el('chatList');
    if (!list) return;
    if (!state.conversations.length) {
      list.innerHTML = UI.empty("Suhbatlar yo'q", "Yangi suhbat shu yerda ko'rinadi");
      return;
    }
    list.innerHTML = '';
    state.conversations.forEach(function (conversation) {
      list.appendChild(conversationRow(conversation));
    });
  }

  function loadConversations(silent) {
    var list = el('chatList');
    if (!silent && list) UI.loading(list, 3);

    return api
      .get('/chat/conversations')
      .then(function (items) {
        state.conversations = Array.isArray(items) ? items : [];
        renderConversations();
        return state.conversations;
      })
      .catch(function (error) {
        if (!silent) {
          state.conversations = [];
          renderConversations();
          UI.toast(error.message, 'error');
        }
        return state.conversations;
      });
  }

  // ------------------------------------------------------------------- room
  function messageNode(message, pending) {
    var mine = !!(message && message.is_mine);

    var node = document.createElement('div');
    node.className = 'msg-bubble ' + (mine ? 'user' : 'bot');
    node.setAttribute('data-message-id', (message && message.id) || '');
    if (pending) {
      node.classList.add(PENDING_CLASS);
      node.style.opacity = '.65';
    }

    if (!mine && message && message.sender_name) {
      var author = document.createElement('div');
      author.style.cssText = 'font-size:12px;font-weight:700;color:#7987A8;margin-bottom:4px';
      author.textContent = message.sender_name;
      node.appendChild(author);
    }

    var text = document.createElement('div');
    text.textContent = bubbleText(message && message.body);
    node.appendChild(text);
    return node;
  }

  function scrollToBottom() {
    var area = el('messagesArea');
    if (area) area.scrollTop = area.scrollHeight;
  }

  function hasMessage(id) {
    for (var i = 0; i < state.messages.length; i += 1) {
      if (state.messages[i].id === id) return true;
    }
    return false;
  }

  /** Appends a message once; returns false when the id is already rendered. */
  function appendMessage(message) {
    if (!message || !message.id) return false;
    if (hasMessage(message.id)) return false;

    var area = el('messagesArea');
    if (!area) return false;

    state.messages.push(message);
    area.appendChild(messageNode(message, !!message._pending));
    scrollToBottom();
    return true;
  }

  function removeMessage(id) {
    state.messages = state.messages.filter(function (message) {
      return message.id !== id;
    });
    var area = el('messagesArea');
    if (!area) return;
    var node = area.querySelector('[data-message-id="' + String(id).replace(/"/g, '') + '"]');
    if (node && node.parentNode) node.parentNode.removeChild(node);
  }

  function renderMessages() {
    var area = el('messagesArea');
    if (!area) return;
    area.innerHTML = '';
    state.messages.forEach(function (message) {
      area.appendChild(messageNode(message, !!message._pending));
    });
    scrollToBottom();
  }

  function updateConversationPreview(id, message) {
    var conversation = findConversation(id);
    if (!conversation || !message) return;
    conversation.last_message = message;
    conversation.last_message_at = message.created_at || conversation.last_message_at;
    renderConversations();
  }

  function loadMessages() {
    var id = state.activeId;
    if (!id) return Promise.resolve([]);

    return api
      .get('/chat/conversations/' + encodeURIComponent(id) + '/messages?limit=' + MESSAGE_LIMIT)
      .then(function (items) {
        if (state.activeId !== id) return [];
        state.messages = Array.isArray(items) ? items : [];
        renderMessages();
        return state.messages;
      })
      .catch(function (error) {
        if (state.activeId === id) {
          var area = el('messagesArea');
          if (area) area.innerHTML = UI.errorBox(error);
          UI.toast(error.message, 'error');
        }
        return [];
      });
  }

  function markRead() {
    var id = state.activeId;
    if (!id) return Promise.resolve();
    return api
      .post('/chat/conversations/' + encodeURIComponent(id) + '/read', {})
      .then(function () {
        setUnread(id, 0);
        renderConversations();
        if (Auth.refreshBadges) Auth.refreshBadges();
      })
      .catch(function () {
        /* read receipts are best-effort: never break the room */
      });
  }

  function syncQuery(id) {
    if (!window.history || !window.history.replaceState) return;
    var next = location.pathname + (id ? '?c=' + encodeURIComponent(id) : '') + location.hash;
    try {
      window.history.replaceState(null, '', next);
    } catch (error) {
      /* ignore: file:// or restricted environment */
    }
  }

  function openRoom(id, title) {
    if (!id) return;
    var conversation = findConversation(id);
    state.activeId = id;
    state.activeTitle = title || (conversation && conversation.title) || 'Suhbat';

    var listView = el('chatListView');
    var room = el('chatRoomContainer');
    var header = el('chatHeaderTitle');
    var area = el('messagesArea');

    if (listView) listView.style.display = 'none';
    if (room) room.style.display = 'flex';
    if (header) header.textContent = state.activeTitle;
    if (area) UI.loading(area, 4);

    state.messages = [];
    syncQuery(id);

    loadMessages().then(function () {
      if (state.activeId !== id) return;
      markRead();
      connectSocket();
    });
  }

  function showList() {
    var room = el('chatRoomContainer');
    var listView = el('chatListView');
    var header = el('chatHeaderTitle');
    if (room) room.style.display = 'none';
    if (listView) listView.style.display = 'flex';
    if (header) header.textContent = 'Suhbatlar';
    syncQuery(null);
  }

  /** Closes the socket/timers and returns to the list state. */
  function stopRoom() {
    closeSocket();
    stopPolling();
    stopHeartbeat();
    hideTyping();
    state.activeId = null;
    state.activeTitle = '';
    state.messages = [];
  }

  // ------------------------------------------------------------------ resume
  function openFromQuery() {
    var id = UI.qs('c');
    if (!id) return;
    var known = findConversation(id);
    if (known) {
      openRoom(known.id, known.title);
      return;
    }
    api
      .get('/chat/conversations/' + encodeURIComponent(id))
      .then(function (conversation) {
        if (conversation && conversation.id) openRoom(conversation.id, conversation.title);
      })
      .catch(function (error) {
        UI.toast(error.message, 'error');
        syncQuery(null);
      });
  }

  // ------------------------------------------------------------- realtime
  function socketSend(payload) {
    var socket = state.socket;
    if (!socket || socket.readyState !== 1) return false;
    try {
      socket.send(JSON.stringify(payload));
      return true;
    } catch (error) {
      return false;
    }
  }

  function startHeartbeat() {
    stopHeartbeat();
    state.heartbeatTimer = setInterval(function () {
      socketSend({ type: 'ping' });
    }, PING_MS);
  }

  function stopHeartbeat() {
    if (state.heartbeatTimer) {
      clearInterval(state.heartbeatTimer);
      state.heartbeatTimer = null;
    }
  }

  function startPolling() {
    if (state.pollTimer) return;
    state.pollTimer = setInterval(pollRoom, POLL_MS);
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  /** Realtime fallback: refetches the open room every 15 s. */
  function pollRoom() {
    var id = state.activeId;
    if (!id) return;
    api
      .get('/chat/conversations/' + encodeURIComponent(id) + '/messages?limit=' + MESSAGE_LIMIT)
      .then(function (items) {
        if (state.activeId !== id || !Array.isArray(items)) return;
        var added = false;
        items.forEach(function (message) {
          if (appendMessage(message)) added = true;
        });
        if (added) {
          markRead();
          updateConversationPreview(id, items[items.length - 1]);
        }
      })
      .catch(function () {
        /* keep the room usable while offline */
      });
    loadConversations(true);
  }

  function hideTyping() {
    if (state.typingTimer) {
      clearTimeout(state.typingTimer);
      state.typingTimer = null;
    }
    if (state.typingNode && state.typingNode.parentNode) {
      state.typingNode.parentNode.removeChild(state.typingNode);
    }
    state.typingNode = null;
  }

  function showTyping(data) {
    var user = me();
    if (data && user && data.user_id === user.id) return;
    var area = el('messagesArea');
    if (!area) return;

    if (!state.typingNode) {
      var node = document.createElement('div');
      node.className = 'msg-bubble bot';
      node.style.opacity = '.75';
      node.style.fontStyle = 'italic';
      node.textContent = ((data && data.name) || 'Kimdir') + ' yozmoqda\u2026';
      area.appendChild(node);
      state.typingNode = node;
      scrollToBottom();
    }

    if (state.typingTimer) clearTimeout(state.typingTimer);
    state.typingTimer = setTimeout(hideTyping, 4000);
  }

  function handleFrame(event) {
    var frame;
    try {
      frame = JSON.parse(event.data);
    } catch (error) {
      return;
    }
    if (!frame || typeof frame !== 'object') return;

    var type = frame.type;

    if (type === 'connected') {
      state.attempts = 0;
      return;
    }
    if (type === 'ping') {
      socketSend({ type: 'pong' });
      return;
    }
    if (type === 'pong') return;

    if (type === 'message.created') {
      var message = frame.data;
      if (!message || !message.id) return;
      if (appendMessage(message)) {
        updateConversationPreview(message.conversation_id || state.activeId, message);
        if (message.conversation_id === state.activeId && !message.is_mine) markRead();
      }
      return;
    }
    if (type === 'typing') {
      showTyping(frame.data);
      return;
    }
    if (type === 'conversation.read') {
      var user = me();
      if (frame.data && user && frame.data.user_id === user.id) {
        setUnread(state.activeId, 0);
        renderConversations();
      }
      return;
    }
  }

  function closeSocket() {
    state.closing = true;
    state.generation += 1;
    if (state.reconnectTimer) {
      clearTimeout(state.reconnectTimer);
      state.reconnectTimer = null;
    }
    var socket = state.socket;
    state.socket = null;
    if (socket) {
      try {
        socket.close();
      } catch (error) {
        /* ignore */
      }
    }
  }

  function connectSocket() {
    closeSocket();
    state.closing = false;

    var id = state.activeId;
    if (!id) return;

    if (typeof window.WebSocket === 'undefined') {
      startPolling();
      return;
    }

    var generation = state.generation;
    var socket;
    try {
      socket = new WebSocket(api.wsUrl('/ws/chat/' + encodeURIComponent(id)));
    } catch (error) {
      startPolling();
      return;
    }
    state.socket = socket;

    socket.onopen = function () {
      if (state.generation !== generation || state.activeId !== id) return;
      state.attempts = 0;
      stopPolling();
      startHeartbeat();
    };

    socket.onmessage = function (event) {
      if (state.generation !== generation || state.activeId !== id) return;
      handleFrame(event);
    };

    socket.onclose = function () {
      if (state.generation !== generation) return;
      if (state.socket === socket) state.socket = null;
      stopHeartbeat();
      if (state.closing || state.activeId !== id) return;

      state.attempts += 1;
      if (state.attempts >= MAX_WS_ATTEMPTS) startPolling();

      var delay = Math.min(1000 * Math.pow(2, state.attempts - 1), 30000);
      state.reconnectTimer = setTimeout(function () {
        state.reconnectTimer = null;
        if (state.activeId === id) connectSocket();
      }, delay);
    };

    socket.onerror = function () {
      /* onclose schedules the retry / polling fallback */
    };
  }

  // ------------------------------------------------------------------ actions
  function sendChatMessage(event) {
    if (event && event.preventDefault) event.preventDefault();

    var input = el('chatInput');
    if (!input) return;

    var text = input.value.trim();
    if (!text) return;

    var id = state.activeId;
    if (!id) {
      UI.toast('Avval suhbatni tanlang.', 'warn');
      return;
    }

    input.value = '';

    var user = me();
    var optimistic = {
      id: 'pending-' + Date.now() + '-' + Math.random().toString(36).slice(2),
      conversation_id: id,
      body: text,
      kind: 'text',
      sender_name: (user && user.full_name) || 'Siz',
      created_at: new Date().toISOString(),
      is_mine: true,
      _pending: true
    };
    appendMessage(optimistic);

    api
      .post('/chat/conversations/' + encodeURIComponent(id) + '/messages', { body: text })
      .then(function (message) {
        removeMessage(optimistic.id);
        if (state.activeId === id && appendMessage(message)) {
          updateConversationPreview(id, message);
        }
      })
      .catch(function (error) {
        removeMessage(optimistic.id);
        UI.toast(error.message, 'error');
      });
  }

  function onTypingInput() {
    var socket = state.socket;
    if (!socket || socket.readyState !== 1) return;

    var now = Date.now();
    if (now - state.typingLastSent < TYPING_THROTTLE_MS) return;
    state.typingLastSent = now;

    var user = me();
    socketSend({
      type: 'typing',
      data: { user_id: (user && user.id) || null, name: (user && user.full_name) || '' }
    });
  }

  function handleChatBack() {
    var room = el('chatRoomContainer');
    if (room && room.style.display === 'flex') {
      stopRoom();
      showList();
    } else {
      window.location.href = 'app.html#asosiy';
    }
  }

  /** Legacy hook kept for the static fallback rows in the markup. */
  function openChatRoom(title) {
    var conversation = null;
    for (var i = 0; i < state.conversations.length; i += 1) {
      if (state.conversations[i].title === title) {
        conversation = state.conversations[i];
        break;
      }
    }
    if (conversation) {
      openRoom(conversation.id, conversation.title);
      return;
    }
    loadConversations(true).then(function () {
      var found = null;
      for (var j = 0; j < state.conversations.length; j += 1) {
        if (state.conversations[j].title === title) {
          found = state.conversations[j];
          break;
        }
      }
      if (found) openRoom(found.id, found.title);
      else UI.toast('Suhbat topilmadi.', 'error');
    });
  }

  function markAllChatRead() {
    if (!state.conversations.length) {
      UI.toast("Hozircha suhbatlar yo'q.", 'info');
      return;
    }
    Promise.all(
      state.conversations.map(function (conversation) {
        return api
          .post('/chat/conversations/' + encodeURIComponent(conversation.id) + '/read', {})
          .catch(function () {
            return null;
          });
      })
    ).then(function () {
      state.conversations.forEach(function (conversation) {
        conversation.unread_count = 0;
      });
      renderConversations();
      if (Auth.refreshBadges) Auth.refreshBadges();
      UI.toast("Barcha suhbatlar o'qilgan deb belgilandi! \u2713\u2713", 'success');
    });
  }

  // -------------------------------------------------------------------- boot
  function bind() {
    var list = el('chatList');
    if (list) {
      UI.on(list, '.chat-row', 'click', function (event, node) {
        var id = node.getAttribute('data-conversation-id');
        if (id) openRoom(id);
      });
      list.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        var node = event.target.closest ? event.target.closest('.chat-row') : null;
        if (!node) return;
        var id = node.getAttribute('data-conversation-id');
        if (!id) return;
        event.preventDefault();
        openRoom(id);
      });
    }

    var input = el('chatInput');
    if (input) input.addEventListener('input', onTypingInput);
    /* The composer submits through its existing inline onsubmit="sendChatMessage(event)". */
  }

  function init() {
    bind();
    loadConversations().then(openFromQuery);
  }

  window.handleChatBack = handleChatBack;
  window.openChatRoom = openChatRoom;
  window.sendChatMessage = sendChatMessage;
  window.markAllChatRead = markAllChatRead;

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
