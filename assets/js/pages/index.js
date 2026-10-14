/*!
 * Englify — public landing page logic (index.html).
 * ---------------------------------------------------------------------------
 * Loaded last, AFTER config.js, ui.js, api.js and auth.js.
 *
 * Wires every lead form on the page (hero + contact, when present) to
 * `POST /leads`. The auth-aware header/footer links are handled by auth.js
 * through the `data-auth="login"` / `data-auth="user"` attributes.
 */
(function () {
  'use strict';

  var api = window.EnglifyApi;
  var UI = window.EnglifyUI;

  if (!api || !UI) {
    console.error('[Englify] index.js requires config.js, api.js and ui.js');
    return;
  }

  /** +998 (99) 123-45-67 — only these characters may appear in a phone. */
  var PHONE_CHARS = /^[+()\-\s\d]+$/;
  var PHONE_DIGITS = 7;
  var SUCCESS_TEXT = 'Yuborildi! Tez orada bog\u2018lanamiz';
  var SENDING_TEXT = 'Yuborilmoqda\u2026';

  function digits(value) {
    return String(value || '').replace(/\D/g, '');
  }

  /** Returns an Uzbek error string, or null when the values look valid. */
  function validate(name, phone) {
    if (String(name || '').trim().length < 2) {
      return 'Ismingiz va familiyangizni kiriting (kamida 2 ta belgi).';
    }
    var value = String(phone || '').trim();
    if (!value) return 'Telefon raqamingizni kiriting.';
    if (!PHONE_CHARS.test(value)) {
      return 'Telefon raqamida faqat raqam, +, bo\u2019shliq, qavs va chiziqcha bo\u2019lishi mumkin.';
    }
    if (digits(value).length < PHONE_DIGITS) {
      return 'Telefon raqami juda qisqa — kamida ' + PHONE_DIGITS + ' ta raqam kiriting.';
    }
    return null;
  }

  function wireForm(form) {
    var source = form.getAttribute('data-lead-form') || 'index-hero';
    var nameInput = form.querySelector('input[type="text"], input[name="name"]');
    var phoneInput = form.querySelector('input[type="tel"], input[name="phone"]');
    var button = form.querySelector('button[type="submit"], [data-lead-submit], #send, button');

    if (!nameInput || !phoneInput || !button) return;

    var idleText = button.textContent;
    var timer = null;

    function restore() {
      button.disabled = false;
      button.textContent = idleText;
      button.setAttribute('data-sent', 'no');
    }

    button.addEventListener('click', function (event) {
      event.preventDefault();
      if (button.disabled) return;

      var name = String(nameInput.value || '').trim();
      var phone = String(phoneInput.value || '').trim();

      var error = validate(name, phone);
      if (error) {
        UI.toast(error, 'error');
        return;
      }

      button.disabled = true;
      button.textContent = SENDING_TEXT;

      api
        .post('/leads', { name: name, phone: phone, source: source }, { auth: false })
        .then(function () {
          button.textContent = SUCCESS_TEXT;
          button.setAttribute('data-sent', 'yes');
          nameInput.value = '';
          phoneInput.value = '+998';
          if (timer) clearTimeout(timer);
          timer = setTimeout(restore, 3200);
        })
        .catch(function (requestError) {
          restore();
          UI.toast((requestError && requestError.message) || 'Xatolik yuz berdi.', 'error');
        });
    });
  }

  function wireForms() {
    var forms = Array.prototype.slice.call(document.querySelectorAll('form[data-lead-form]'));
    // Safety net: any other form living in the "Aloqa" (contact) section.
    Array.prototype.slice.call(document.querySelectorAll('#aloqa form')).forEach(function (form) {
      if (forms.indexOf(form) === -1) {
        if (!form.getAttribute('data-lead-form')) form.setAttribute('data-lead-form', 'index-contact');
        forms.push(form);
      }
    });
    forms.forEach(wireForm);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireForms);
  } else {
    wireForms();
  }
})();
