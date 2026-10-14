/*!
 * Englify — jang.html («Jang» quiz battles: lobby + arena).
 * ---------------------------------------------------------------------------
 * Server-authoritative rewrite of the old client-side simulation:
 *   - `POST /battles` creates the match, the AI opponent answers server-side
 *   - `POST /battles/{id}/answer` grades the round (the client NEVER scores)
 *   - `POST /battles/{id}/finish` decides the winner
 *   - duel/group wait for an opponent over `WS /ws/battles/{id}` (+ REST poll)
 *   - the lobby shows real `GET /battles/stats` and `GET /battles/history`
 *
 * Loads after config.js, ui.js, api.js and auth.js.
 */
(function () {
  'use strict';

  var UI = window.EnglifyUI;
  var API = window.EnglifyApi;
  var Auth = window.EnglifyAuth;

  if (!UI || !API || !Auth) {
    console.error('[Englify] jang.js requires ui.js, api.js and auth.js');
    return;
  }

  var MODE_LABEL = { ai: 'AI', duel: 'Duel', group: 'Guruh' };
  var TOPIC_LABEL = { grammar: 'Grammar', vocabulary: 'Vocabulary', mixed: 'Aralash' };

  var state = {
    mode: 'ai',
    topic: 'grammar',
    battle: null,
    me: null,
    roundIndex: 0,
    answered: false,
    playing: false,
    busy: false,
    resultShown: false,
    timerId: null,
    pollId: null,
    socket: null,
    historyLoaded: false
  };

  function $(id) {
    return document.getElementById(id);
  }

  function label(map, key) {
    return map[key] || String(key || '');
  }

  // ------------------------------------------------------------- identity
  function myScore(battle) {
    var b = battle || state.battle;
    if (!b) return 0;
    return b.is_host ? (b.host_score || 0) : (b.guest_score || 0);
  }

  function oppScore(battle) {
    var b = battle || state.battle;
    if (!b) return 0;
    return b.is_host ? (b.guest_score || 0) : (b.host_score || 0);
  }

  /** The avatar markup for `user`, falling back to an emoji then an icon. */
  function avatarMarkup(user, size, fallbackIcon) {
    if (!user) return UI.escape(fallbackIcon || '👤');
    if (user.avatar_url) return UI.avatar(user, size);
    if (user.emoji) return UI.escape(user.emoji);
    if (user.is_bot) return '🤖';
    return UI.escape(UI.initials(user.name) ? UI.avatar(user, size).replace(/^\s+/, '') : '👤');
  }

  function renderPlayerIdentity() {
    var me = state.me || API.user();
    var node = $('playerAvatar');
    if (node && me) node.innerHTML = avatarMarkup(me, 28, '👤');
  }

  function renderOpponent() {
    var nameNode = $('opponentName');
    var avatarNode = $('opponentAvatar');
    var b = state.battle;
    if (!nameNode || !b) return;

    var opp = b.is_host ? b.guest : b.host;
    if (!opp) {
      nameNode.textContent = 'Raqib kutilmoqda…';
      if (avatarNode) avatarNode.textContent = '⏳';
      return;
    }
    nameNode.textContent = opp.name || (opp.is_bot ? 'AI Bot' : 'Raqib');
    if (avatarNode) avatarNode.innerHTML = avatarMarkup(opp, 28, '👤');
  }

  function renderScores() {
    var b = state.battle;
    if (!b) return;
    var mine = $('playerScore');
    var theirs = $('opponentScore');
    if (mine) mine.textContent = myScore(b) + ' ball';
    if (theirs) theirs.textContent = oppScore(b) + ' ball';
    if (!b.is_host && b.host && $('playerScore')) {
      // nothing extra: the left side always shows the viewer's score
    }
  }

  // ----------------------------------------------------------------- lobby
  window.selectMode = function (mode, el) {
    state.mode = mode;
    document.querySelectorAll('.mode-card').forEach(function (card) {
      card.classList.remove('selected');
    });
    if (el) el.classList.add('selected');
  };

  window.selectLobby = function (topic, el) {
    state.topic = topic;
    document.querySelectorAll('.lobby-card').forEach(function (card) {
      card.classList.remove('selected');
    });
    if (el) el.classList.add('selected');
  };

  function setStartBusy(busy) {
    var btn = $('startBtn');
    if (!btn) return;
    btn.disabled = !!busy;
    btn.textContent = busy ? 'Yuklanmoqda…' : 'Jangni boshlang';
  }

  window.startBattle = function () {
    if (state.busy) return;
    state.busy = true;
    setStartBusy(true);

    var payload = { mode: state.mode, topic: state.topic };
    var user = state.me || API.user();
    if (user && user.level) payload.level = user.level;

    API.post('/battles', payload)
      .then(function (battle) {
        state.busy = false;
        setStartBusy(false);
        enterBattle(battle);
      })
      .catch(function (error) {
        state.busy = false;
        setStartBusy(false);
        UI.toast(error.message, 'error');
      });
  };

  // ---------------------------------------------------------------- battles
  function showView(view) {
    var lobby = $('lobbyView');
    var arena = $('gameArena');
    if (lobby) lobby.style.display = view === 'arena' ? 'none' : 'flex';
    if (arena) arena.style.display = view === 'arena' ? 'flex' : 'none';
  }

  function setHidden(node, hidden) {
    if (!node) return;
    if (hidden) node.setAttribute('hidden', '');
    else node.removeAttribute('hidden');
  }

  function enterBattle(battle) {
    state.battle = battle;
    state.me = API.user() || state.me;
    state.resultShown = false;
    state.playing = false;
    state.roundIndex = 0;
    state.answered = false;

    showView('arena');
    renderPlayerIdentity();
    renderOpponent();
    renderScores();

    if (battle.status === 'active') {
      startPlay();
    } else {
      enterWaiting();
    }

    if (battle.mode !== 'ai') {
      openSocket(battle.id);
      startPoll();
    }
  }

  function enterWaiting() {
    setHidden($('waitingBox'), false);
    setHidden($('questionPanel'), true);
    setHidden($('optionsWrap'), true);
    setHidden($('resultBox'), true);
    var nameNode = $('opponentName');
    if (nameNode) nameNode.textContent = 'Raqib kutilmoqda…';
    stopTimer();
  }

  function leaveWaiting() {
    setHidden($('waitingBox'), true);
    setHidden($('questionPanel'), false);
    setHidden($('optionsWrap'), false);
  }

  function startPlay() {
    if (state.playing) return;
    state.playing = true;
    state.roundIndex = 0;
    leaveWaiting();
    setHidden($('resultBox'), true);
    renderOpponent();
    renderScores();
    playRound();
  }

  function stopTimer() {
    if (state.timerId) {
      clearInterval(state.timerId);
      state.timerId = null;
    }
  }

  function stopPoll() {
    if (state.pollId) {
      clearInterval(state.pollId);
      state.pollId = null;
    }
  }

  function closeSocket() {
    if (state.socket) {
      try {
        state.socket.close();
      } catch (error) {
        /* ignore */
      }
      state.socket = null;
    }
  }

  function stopAll() {
    stopTimer();
    stopPoll();
    closeSocket();
  }

  function playRound() {
    var battle = state.battle;
    if (!battle) return;
    var questions = battle.questions || [];
    var question = questions[state.roundIndex];
    if (!question) {
      finishBattle();
      return;
    }

    state.answered = false;
    leaveWaiting();

    var countNode = $('qCount');
    if (countNode) countNode.textContent = (state.roundIndex + 1) + '/' + (battle.rounds || questions.length);

    var textNode = $('questionText');
    if (textNode) textNode.textContent = question.prompt;

    var wrap = $('optionsWrap');
    if (wrap) {
      wrap.innerHTML = '';
      (question.options || []).forEach(function (option, index) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'option-btn';
        btn.textContent = option;
        btn.addEventListener('click', function () {
          submitAnswer(index, btn);
        });
        wrap.appendChild(btn);
      });
    }

    startTimer(battle.seconds_per_round || 15);
  }

  function startTimer(seconds) {
    stopTimer();
    var total = Number(seconds) || 15;
    var left = total;
    var node = $('roundTimer');
    if (node) node.textContent = left;
    state.timerId = setInterval(function () {
      left -= 1;
      if (node) node.textContent = left > 0 ? left : 0;
      if (left <= 0) {
        stopTimer();
        submitAnswer(null, null);
      }
    }, 1000);
  }

  function markButtons(disabled) {
    var wrap = $('optionsWrap');
    if (!wrap) return;
    wrap.querySelectorAll('.option-btn').forEach(function (btn) {
      btn.disabled = !!disabled;
    });
  }

  function submitAnswer(index, btn) {
    if (state.answered || !state.battle) return;
    state.answered = true;
    stopTimer();
    markButtons(true);
    if (btn) btn.style.borderColor = '#0B5AA4';

    var before = myScore();
    // The backend derives correctness from `answer_index` and IGNORES the
    // `correct` flag (backend/app/routers/battles.py -> submit_answer).
    // BattleQuestion never exposes the correct option, so the client cannot
    // know the truth and must not claim it: `false` means "not asserted".
    var payload = {
      round_index: state.roundIndex,
      correct: false,
      answer_index: index === null || index === undefined ? null : index
    };

    API.post('/battles/' + state.battle.id + '/answer', payload)
      .then(function (battle) {
        state.battle = battle;
        var gained = myScore() - before;

        if (btn) {
          btn.style.background = gained > 0 ? '#E9FBF2' : '#FFF1F2';
          btn.style.borderColor = gained > 0 ? '#17C877' : '#FF4757';
        } else if (index === null) {
          UI.toast('Vaqt tugadi!', 'warn');
        }
        if (gained <= 0 && index !== null) {
          UI.toast('Noto\u2019g\u2019ri javob', 'info');
        }

        renderScores();
        if (state.roundIndex + 1 >= (battle.rounds || 0) || state.roundIndex + 1 >= (battle.questions || []).length) {
          setTimeout(finishBattle, 500);
        } else {
          state.roundIndex += 1;
          setTimeout(function () {
            if (state.playing) playRound();
          }, 900);
        }
      })
      .catch(function (error) {
        state.answered = false;
        markButtons(false);
        UI.toast(error.message, 'error');
      });
  }

  function finishBattle() {
    if (!state.battle) return;
    var id = state.battle.id;
    stopTimer();
    API.post('/battles/' + id + '/finish')
      .then(function (battle) {
        state.battle = battle;
        state.playing = false;
        renderScores();
        showResult(battle);
        stopAll();
        loadStats();
        state.historyLoaded = false;
        if (!$('historyPanel') || !$('historyPanel').hasAttribute('hidden')) loadHistory();
      })
      .catch(function (error) {
        UI.toast(error.message, 'error');
      });
  }

  function showResult(battle) {
    var box = $('resultBox');
    if (!box) return;
    state.resultShown = true;
    state.playing = false;
    stopTimer();
    setHidden($('waitingBox'), true);
    setHidden($('questionPanel'), true);
    setHidden($('optionsWrap'), true);

    var mine = myScore(battle);
    var theirs = oppScore(battle);
    var title;
    var color;
    if (mine > theirs) {
      title = '🎉 G\u2019ALABA!';
      color = '#17C877';
    } else if (mine < theirs) {
      title = '😔 Mag\u2019lubiyat';
      color = '#FF4757';
    } else {
      title = '🤝 Durang';
      color = '#8C99B8';
    }

    var opp = battle.is_host ? battle.guest : battle.host;
    var oppName = (opp && opp.name) || 'Raqib';

    box.innerHTML =
      '<div style="font-weight:800;font-size:26px;color:' + color + '">' + title + '</div>' +
      '<div style="font-weight:700;font-size:17px;margin-top:12px">Siz: ' + UI.escape(mine) +
      ' ball · ' + UI.escape(oppName) + ': ' + UI.escape(theirs) + ' ball</div>' +
      '<div style="color:#69789A;font-weight:600;font-size:15px;margin-top:6px">' +
      UI.escape(label(TOPIC_LABEL, battle.topic) + ' · ' + label(MODE_LABEL, battle.mode)) + '</div>' +
      '<button id="backToLobby" type="button" style="margin-top:20px;background:#0B5AA4;color:#fff;border:0;' +
      'border-radius:16px;padding:14px 26px;font-weight:800;font-size:16px;cursor:pointer;' +
      'box-shadow:0 4px 0 #076FC2">Lobbyga qaytish</button>';

    var back = $('backToLobby');
    if (back) back.addEventListener('click', backToLobby);

    box.removeAttribute('hidden');
  }

  function backToLobby() {
    stopAll();
    state.battle = null;
    state.playing = false;
    state.resultShown = false;
    setHidden($('resultBox'), true);
    setHidden($('waitingBox'), true);
    setHidden($('questionPanel'), false);
    setHidden($('optionsWrap'), false);
    if ($('optionsWrap')) $('optionsWrap').innerHTML = '';
    showView('lobby');
    loadStats();
  }

  // -------------------------------------------------------- waiting / realtime
  function startPoll() {
    stopPoll();
    state.pollId = setInterval(refreshBattle, 3000);
  }

  function refreshBattle() {
    if (!state.battle) return;
    var id = state.battle.id;
    API.get('/battles/' + id)
      .then(function (battle) {
        var wasWaiting = state.battle && state.battle.status === 'waiting';
        state.battle = battle;
        renderOpponent();
        renderScores();

        if (battle.status === 'active' && wasWaiting && !state.playing) {
          UI.toast('Raqib topildi!', 'success');
          startPlay();
        } else if (battle.status === 'finished' && !state.resultShown) {
          state.playing = false;
          showResult(battle);
          stopAll();
          loadStats();
        } else if (battle.status === 'cancelled') {
          UI.toast('Jang bekor qilindi.', 'info');
          backToLobby();
        }
      })
      .catch(function () {
        /* keep the current view; the next tick retries */
      });
  }

  function openSocket(id) {
    if (typeof WebSocket === 'undefined') return;
    closeSocket();
    var socket;
    try {
      socket = new WebSocket(API.wsUrl('/ws/battles/' + id));
    } catch (error) {
      return; // REST play/poll keeps working
    }
    state.socket = socket;

    socket.onmessage = function (event) {
      var frame;
      try {
        frame = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      handleFrame(frame);
    };
    socket.onerror = function () {
      /* the 3s REST poll is the fallback */
    };
  }

  function handleFrame(frame) {
    if (!frame || !frame.type) return;
    var data = frame.data || {};

    if (frame.type === 'battle.started') {
      state.battle = data && data.id ? data : state.battle;
      renderOpponent();
      renderScores();
      if (state.battle && state.battle.status === 'active' && !state.playing) {
        UI.toast('Jang boshlandi!', 'success');
        startPlay();
      }
    } else if (frame.type === 'battle.score') {
      if (!state.battle) return;
      if (typeof data.host_score === 'number') state.battle.host_score = data.host_score;
      if (typeof data.guest_score === 'number') state.battle.guest_score = data.guest_score;
      renderScores();
    } else if (frame.type === 'battle.finished') {
      if (data && data.id) state.battle = data;
      if (!state.resultShown) {
        state.playing = false;
        showResult(state.battle);
        stopAll();
        loadStats();
      }
    } else if (frame.type === 'battle.cancelled') {
      UI.toast('Jang bekor qilindi.', 'info');
      backToLobby();
    }
  }

  function bindCancel() {
    var btn = $('cancelBtn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      if (!state.battle) return backToLobby();
      btn.disabled = true;
      API.post('/battles/' + state.battle.id + '/cancel')
        .then(function () {
          UI.toast('Jang bekor qilindi.', 'info');
          backToLobby();
        })
        .catch(function (error) {
          btn.disabled = false;
          UI.toast(error.message, 'error');
        });
    });
  }

  // ------------------------------------------------------------ stats/history
  function loadStats() {
    return API.get('/battles/stats')
      .then(function (stats) {
        var played = $('statPlayed');
        var won = $('statWon');
        var lost = $('statLost');
        if (played) played.textContent = UI.number(stats.played);
        if (won) won.textContent = UI.number(stats.won);
        if (lost) lost.textContent = UI.number(stats.lost);
      })
      .catch(function () {
        /* the lobby keeps its 0 defaults */
      });
  }

  function historyRow(item) {
    var mine = item.is_host ? item.host_score : item.guest_score;
    var theirs = item.is_host ? item.guest_score : item.host_score;
    var opp = item.is_host ? item.guest : item.host;
    var oppName = (opp && opp.name) || 'Raqib';
    var result = mine > theirs ? 'win' : (mine < theirs ? 'loss' : 'draw');
    var palette = {
      win: { color: '#17C877', bg: '#E9FBF2', label: 'G\u2019alaba' },
      loss: { color: '#FF4757', bg: '#FFF1F2', label: 'Mag\u2019lubiyat' },
      draw: { color: '#8C99B8', bg: '#F1F3F9', label: 'Durang' }
    }[result];

    return (
      '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;background:#fff;' +
      'border:1px solid #EEF1F9;border-left:5px solid ' + palette.color + ';border-radius:20px;padding:14px 18px;flex-wrap:wrap">' +
      '<div>' +
      '<div style="font-weight:800;font-size:16px">' + UI.escape(oppName) +
      ' <span style="color:#8C99B8;font-weight:700;font-size:13px">' +
      UI.escape(label(MODE_LABEL, item.mode) + ' · ' + label(TOPIC_LABEL, item.topic)) + '</span></div>' +
      '<div style="color:#8C99B8;font-weight:600;font-size:13px">' +
      UI.escape(UI.relative(item.finished_at || item.created_at)) + '</div>' +
      '</div>' +
      '<div style="display:flex;align-items:center;gap:10px">' +
      '<span style="font-weight:800;font-size:16px">' + UI.escape(mine) + ' : ' + UI.escape(theirs) + '</span>' +
      '<span style="background:' + palette.bg + ';color:' + palette.color + ';font-weight:800;font-size:13px;' +
      'border-radius:999px;padding:5px 12px">' + palette.label + '</span>' +
      '</div></div>'
    );
  }

  function loadHistory() {
    var list = $('historyList');
    if (!list) return;
    UI.loading(list, 3);
    API.get('/battles/history?limit=20')
      .then(function (items) {
        state.historyLoaded = true;
        if (!items || !items.length) {
          list.innerHTML = UI.empty('Hali janglar yo\u2019q', 'Birinchi jangni boshlang!');
          return;
        }
        list.innerHTML = items.map(historyRow).join('');
      })
      .catch(function (error) {
        list.innerHTML = UI.errorBox(error);
        UI.toast(error.message, 'error');
      });
  }

  window.openHistory = function () {
    var panel = $('historyPanel');
    if (!panel) return;
    if (panel.hasAttribute('hidden')) {
      panel.removeAttribute('hidden');
      if (panel.scrollIntoView) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      loadStats();
      loadHistory();
    } else {
      panel.setAttribute('hidden', '');
    }
  };

  // -------------------------------------------------------------------- boot
  function boot() {
    bindCancel();
    Auth.require()
      .then(function (user) {
        state.me = user || API.user();
        renderPlayerIdentity();
        loadStats();
      })
      .catch(function () {
        /* auth.js already redirects when the session is missing */
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
