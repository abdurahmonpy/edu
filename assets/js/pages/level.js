/*!
 * Englify — level.html (CEFR levels + placement test).
 * ---------------------------------------------------------------------------
 * Everything on this page is server driven:
 *   GET   /levels                     -> level cards (unlock state, %, bar)
 *   GET   /courses/placement-test     -> find the `placement-quiz` lesson
 *   GET   /lessons/{id}/quiz          -> questions (NO answer key)
 *   POST  /lessons/{id}/quiz          -> {answers:[int]} graded SERVER-SIDE
 *   PATCH /auth/me {level}            -> store the recommended CEFR level
 *
 * The client never sees or computes the correct answers.
 */
(function () {
  'use strict';

  var UI = window.EnglifyUI;
  var Api = window.EnglifyApi;
  var Auth = window.EnglifyAuth;
  if (!UI || !Api || !Auth) return;

  // Display-only CEFR codes. The backend exposes `points_required`, and the
  // prototype used exactly these thresholds (0 -> A1, 500 -> A2, ...).
  var CODE_BY_POINTS = {
    '0': 'A1',
    '500': 'A2',
    '1500': 'B1',
    '3000': 'B2',
    '5000': 'C1',
    '8000': 'C1+',
    '12000': 'C2'
  };

  // Uzbek gloss shown next to the level title (same copy as the prototype).
  var SUBTITLES = {
    'starter': "Boshlang'ich",
    'beginner': "Boshlang'ich",
    'elementary': 'Oddiy muloqot',
    'pre-intermediate': "O'rta bosqich",
    'intermediate': 'Ishonchli nutq',
    'upper-intermediate': 'Yuqori bosqich',
    'advanced': "Ilg'or daraja"
  };

  var PASS_LEVEL = 'elementary';   // score >= total (same rule as the prototype)
  var FAIL_LEVEL = 'starter';

  var levels = [];
  var user = null;

  // --------------------------------------------------------------- helpers
  function codeFor(level, index) {
    var code = CODE_BY_POINTS[String(level.points_required)];
    return code || ('L' + (index + 1));
  }

  function percent(level) {
    var value = Number(level.progress_percent);
    if (!isFinite(value) || value < 0) value = 0;
    if (value > 100) value = 100;
    return value;
  }

  function percentLabel(value) {
    return (value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)) + '%';
  }

  function titleOf(level) {
    var gloss = SUBTITLES[level.slug];
    return gloss ? level.title + ' \u2022 ' + gloss : level.title;
  }

  function pill(text) {
    var node = document.getElementById('currentLevelPill');
    if (node) node.textContent = text;
  }

  // ----------------------------------------------------------- level cards
  function cardHtml(level, index, firstLockedIndex) {
    var unlocked = !!level.unlocked;
    var isCurrent = user && user.level === level.slug;
    var value = percent(level);

    var badgeColors = unlocked
      ? 'background: #6B3FD8; color: #fff;'
      : (index === firstLockedIndex
          ? 'background: #C9C3FA; color: #5B2BC4;'
          : 'background: #E6E8F2; color: #8F95B2;');

    var statusHtml;
    if (unlocked) {
      statusHtml = isCurrent
        ? '<span style="background: #2ED573; color: #fff; border-radius: 999px; padding: 4px 12px; font-weight: 700; font-size: 13px">Hozir o\'qilmoqda</span>'
        : '<span style="background: #2ED573; color: #fff; border-radius: 999px; padding: 4px 12px; font-weight: 700; font-size: 13px">Ochilgan \u2713</span>';
    } else {
      statusHtml =
        '<span style="background: #E4E8F7; color: #7F87A7; border-radius: 999px; padding: 4px 12px; font-weight: 700; font-size: 13px">' +
        '\uD83D\uDD12 ' + UI.number(level.points_required) + ' ball kerak</span>';
    }

    var progressHtml = unlocked
      ? '<div style="display: flex; align-items: center; gap: 12px">' +
          '<div style="flex: 1; height: 10px; background: #E6E8F2; border-radius: 99px; overflow: hidden">' +
            '<div style="width: ' + value + '%; height: 100%; background: #6B3FD8; border-radius: 99px"></div>' +
          '</div>' +
          '<span style="font-weight: 800; font-size: 14px; color: #6B3FD8">' + percentLabel(value) + '</span>' +
        '</div>'
      : '';

    var body =
      '<div style="width: 64px; height: 64px; border-radius: 20px; ' + badgeColors +
        ' display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 26px; flex-shrink: 0">' +
        UI.escape(codeFor(level, index)) +
      '</div>' +
      '<div style="flex: 1; min-width: 0">' +
        '<div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 6px">' +
          '<h4 style="margin: 0; font-weight: 800; font-size: 22px; color: var(--ink)">' + UI.escape(titleOf(level)) + '</h4>' +
          statusHtml +
        '</div>' +
        '<p style="margin: 6px 0 ' + (unlocked ? '12px' : '0') + '; font-size: 15px; color: #6A5A92">' +
          UI.escape(level.description || '') + '</p>' +
        progressHtml +
      '</div>';

    if (unlocked) {
      return '<a class="level-card ' + (isCurrent ? 'active' : 'active') + '" href="dars.html">' + body + '</a>';
    }
    return '<div class="level-card locked">' + body + '</div>';
  }

  function renderLevels() {
    var host = document.getElementById('levelRoadmap');
    if (!host) return;

    if (!levels.length) {
      host.innerHTML = UI.empty('Darajalar topilmadi', "Keyinroq qayta urinib ko'ring");
      return;
    }

    var firstLockedIndex = -1;
    for (var i = 0; i < levels.length; i += 1) {
      if (!levels[i].unlocked) { firstLockedIndex = i; break; }
    }

    host.innerHTML = levels.map(function (level, index) {
      return cardHtml(level, index, firstLockedIndex);
    }).join('');

    var current = null;
    levels.forEach(function (level) {
      if (user && level.slug === user.level) current = level;
    });
    if (current) {
      pill('Joriy: ' + codeFor(current, levels.indexOf(current)) + ' ' + current.title);
    } else if (user && user.level_title) {
      pill('Joriy: ' + user.level_title);
    }
  }

  function loadLevels() {
    return Api.get('/levels')
      .then(function (list) {
        levels = Array.isArray(list) ? list.slice().sort(function (a, b) {
          return (a.order || 0) - (b.order || 0);
        }) : [];
        renderLevels();
      })
      .catch(function (error) {
        var host = document.getElementById('levelRoadmap');
        if (host) host.innerHTML = UI.errorBox(error);
        UI.toast(error.message, 'error');
      });
  }

  // --------------------------------------------------------- placement quiz
  var quiz = {
    lessonId: null,
    questions: [],
    answers: [],
    index: 0,
    ready: false,
    locked: false,
    submitting: false
  };

  function findQuizLesson(course) {
    var units = (course && course.units) || [];
    for (var u = 0; u < units.length; u += 1) {
      var lessons = units[u].lessons || [];
      for (var l = 0; l < lessons.length; l += 1) {
        var lesson = lessons[l];
        if (lesson.kind === 'quiz' || lesson.slug === 'placement-quiz') return lesson;
      }
    }
    // Fall back to any lesson the course carries.
    for (var u2 = 0; u2 < units.length; u2 += 1) {
      if ((units[u2].lessons || []).length) return units[u2].lessons[0];
    }
    return null;
  }

  function showQuizMessage(message) {
    var host = document.getElementById('optionsContainer');
    if (host) host.innerHTML = UI.errorBox({ message: message });
    var number = document.getElementById('qNumber');
    if (number) number.textContent = 'TEST YUKLANMADI';
  }

  function renderQuestion() {
    var question = quiz.questions[quiz.index];
    if (!question) return;

    var number = document.getElementById('qNumber');
    var text = document.getElementById('qText');
    var host = document.getElementById('optionsContainer');
    if (!number || !text || !host) return;

    number.textContent = (quiz.index + 1) + '-SAVOL (' + quiz.questions.length + ' tadan)';
    text.textContent = question.prompt || '';

    var options = Array.isArray(question.options) ? question.options : [];
    host.innerHTML = options.map(function (option, index) {
      return '<button type="button" class="quiz-opt" data-opt="' + index + '">' +
        UI.escape(option) + '</button>';
    }).join('');
  }

  function loadQuiz() {
    return Api.get('/courses/placement-test')
      .then(function (course) {
        var lesson = findQuizLesson(course);
        if (!lesson) throw new Error('Placement test darsi topilmadi.');
        quiz.lessonId = lesson.id;
        return Api.get('/lessons/' + lesson.id + '/quiz');
      })
      .then(function (questions) {
        quiz.questions = (Array.isArray(questions) ? questions : []).slice().sort(function (a, b) {
          return (a.order_index || 0) - (b.order_index || 0);
        });
        if (!quiz.questions.length) throw new Error('Test savollari topilmadi.');
        quiz.answers = [];
        quiz.index = 0;
        quiz.ready = true;
        renderQuestion();
      })
      .catch(function (error) {
        showQuizMessage(error.message || 'Test yuklanmadi.');
        UI.toast(error.message, 'error');
      });
  }

  // Called by the pre-rendered option buttons and by the delegated handler.
  window.selectQuizAnswer = function (optionIndex) {
    if (!quiz.ready || quiz.locked || quiz.submitting) return;
    if (typeof optionIndex !== 'number' || !isFinite(optionIndex)) return;

    var host = document.getElementById('optionsContainer');
    var button = host && host.querySelector('[data-opt="' + optionIndex + '"]');
    if (button) button.classList.add('selected');

    quiz.locked = true;
    quiz.answers[quiz.index] = optionIndex;

    window.setTimeout(function () {
      quiz.index += 1;
      quiz.locked = false;
      if (quiz.index < quiz.questions.length) {
        renderQuestion();
      } else {
        submitQuiz();
      }
    }, 180);
  };

  function submitQuiz() {
    quiz.submitting = true;
    var host = document.getElementById('optionsContainer');
    if (host) {
      host.innerHTML = '<div style="font-weight:700;color:#7F87A7;padding:12px 0">Natija tekshirilmoqda\u2026</div>';
    }

    Api.post('/lessons/' + quiz.lessonId + '/quiz', { answers: quiz.answers })
      .then(function (result) {
        showResult(result);
      })
      .catch(function (error) {
        quiz.submitting = false;
        // Let the learner answer the last question again.
        quiz.answers.pop();
        quiz.index = quiz.questions.length - 1;
        renderQuestion();
        UI.toast(error.message, 'error');
      });
  }

  function resultRow(result, index) {
    var correct = !!result.is_correct;
    return '<div style="display:flex; gap:10px; align-items:flex-start; text-align:left; ' +
      'background:' + (correct ? '#EAFBF1' : '#FFF1F2') + '; ' +
      'border:2px solid ' + (correct ? '#B6EFD2' : '#FFD0D6') + '; border-radius:16px; padding:10px 14px">' +
      '<span aria-hidden="true">' + (correct ? '\u2705' : '\u274C') + '</span>' +
      '<span style="font-weight:700; font-size:14px; color:' + (correct ? '#108A45' : '#B3121F') + '">' +
        (index + 1) + '-savol \u2014 ' + (correct ? "to'g'ri" : "noto'g'ri") +
        (result.explanation && !correct
          ? '<div style="font-weight:600; color:#6A5A92; margin-top:4px">' + UI.escape(result.explanation) + '</div>'
          : '') +
      '</span>' +
    '</div>';
  }

  function showResult(result) {
    var total = Number(result.total) || quiz.questions.length;
    var correct = Number(result.correct_count) || 0;
    var passed = correct >= total;
    var slug = passed ? PASS_LEVEL : FAIL_LEVEL;

    var container = document.getElementById('quizContainer');
    var box = document.getElementById('quizResult');
    if (container) container.style.display = 'none';
    if (box) box.style.display = 'block';

    var levelNode = document.getElementById('resLevel');
    var descNode = document.getElementById('resDesc');
    if (levelNode) levelNode.textContent = passed ? 'A2 Elementary' : 'A1 Starter';
    if (descNode) {
      descNode.textContent = passed
        ? "Ajoyib natija! Boshlang'ich bilimlaringiz mustahkam. Elementary darslariga tayyorsiz!"
        : "Siz uchun hozirgi A1 Starter darslari (Unit 1.1) ayni muddao. Darsni hoziroq davom ettiring!";
    }

    var breakdown = document.getElementById('quizBreakdown');
    if (breakdown) {
      var scoreText = (Number(result.score) || 0);
      var rows = (result.results || []).map(resultRow).join('');
      breakdown.innerHTML =
        '<div style="font-weight:800; font-size:16px; color:#6B3FD8; margin-bottom:14px">' +
          'Natija: ' + correct + '/' + total + " to'g'ri \u00b7 " +
          (scoreText % 1 === 0 ? scoreText.toFixed(0) : scoreText.toFixed(1)) + '% \u00b7 +' +
          UI.number(result.points_earned) + ' ball' +
        '</div>' +
        '<div style="display:flex; flex-direction:column; gap:8px; max-width:520px; margin:0 auto">' +
          rows +
        '</div>';
    }

    UI.toast(
      "Test yakunlandi: " + correct + '/' + total + " to'g'ri. +" +
        UI.number(result.points_earned) + ' ball',
      'success'
    );

    return Api.patch('/auth/me', { level: slug })
      .then(function (updated) {
        user = updated || user;
        if (Auth.state) Auth.state.user = user;
        UI.toast("Darajangiz saqlandi: " + (user.level_title || slug), 'success');
        return loadLevels();
      })
      .catch(function (error) {
        UI.toast(error.message, 'error');
      });
  }

  // ------------------------------------------------------------------ boot
  window.scrollToQuiz = function () {
    var section = document.getElementById('quizSection');
    if (section) section.scrollIntoView({ behavior: 'smooth' });
  };

  function start(currentUser) {
    user = currentUser || Api.user();
    if (user && user.level && user.level_title) pill('Joriy: ' + user.level_title);

    var host = document.getElementById('optionsContainer');
    if (host) host.innerHTML = '<div style="font-weight:700;color:#7F87A7;padding:12px 0">Savollar yuklanmoqda\u2026</div>';

    loadLevels();
    loadQuiz();
  }

  function boot() {
    Auth.require()
      .then(function (currentUser) {
        if (!currentUser) return; // auth.js is redirecting to kirish.html
        start(currentUser);
      })
      .catch(function () {
        /* require() rejects while redirecting a logged-out visitor */
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
