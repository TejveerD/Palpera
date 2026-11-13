/*
 * Palpera signup forms -> Formspree.
 *
 * FORMSPREE_ENDPOINT is TJ's form (Formspree dashboard -> the form ->
 * Integration). To move to another form, change this one line.
 *
 * Free plan (checked November 2026): 50 submissions a month, and submissions
 * are kept for 30 days only. Export the list regularly, and move it into a
 * mailing-list tool before sending the launch email.
 */
var FORMSPREE_ENDPOINT = 'https://formspree.io/f/xnpdjprv';

(function () {
  'use strict';

  var notConnected = /REPLACE_WITH_FORM_ID/.test(FORMSPREE_ENDPOINT);
  if (notConnected && window.console) {
    console.warn('Palpera: FORMSPREE_ENDPOINT is still the placeholder. Signups will not be sent.');
  }

  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  // Bump when the consent wording next to the forms changes, so each stored
  // signup records which wording the person agreed to.
  var CONSENT_VERSION = '2026-11-13';

  Array.prototype.forEach.call(document.querySelectorAll('form[data-signup]'), function (form) {
    var input = form.querySelector('input[type="email"]');
    var button = form.querySelector('button[type="submit"]');
    var status = form.querySelector('.signup-status');
    var consent = form.querySelector('input[name="consent"]');
    var consentText = form.querySelector('[data-consent-text]');
    var gotcha = form.querySelector('input[name="_gotcha"]');

    form.setAttribute('action', FORMSPREE_ENDPOINT);
    form.setAttribute('method', 'POST');

    function say(text, kind) {
      status.textContent = text;
      status.classList.toggle('is-ok', kind === 'ok');
      status.classList.toggle('is-error', kind === 'error');
    }

    if (consent) {
      consent.addEventListener('change', function () {
        if (consent.checked && consent.getAttribute('aria-invalid') === 'true') {
          consent.removeAttribute('aria-invalid');
          say('', null);
        }
      });
    }

    input.addEventListener('input', function () {
      if (input.getAttribute('aria-invalid') === 'true') {
        input.removeAttribute('aria-invalid');
        say('', null);
      }
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var value = input.value.trim();

      if (!EMAIL.test(value)) {
        input.setAttribute('aria-invalid', 'true');
        say('Please enter a full email address, like name@example.com.', 'error');
        input.focus();
        return;
      }

      if (consent && !consent.checked) {
        consent.setAttribute('aria-invalid', 'true');
        say('Please tick the box so we can send you the email.', 'error');
        consent.focus();
        return;
      }

      if (notConnected) {
        say('Signup is not connected yet. Please try again soon.', 'error');
        return;
      }

      button.disabled = true;
      say('Sending…', null);

      // Only what is needed: the address, and a record of the consent given
      // (the exact wording and its version). Nothing else from the page or
      // the browser is sent.
      var body = new FormData();
      body.append('email', value);
      if (consent) {
        body.append('consent', 'yes');
        body.append('consent_wording', consentText ? consentText.textContent.replace(/\s+/g, ' ').trim() : '');
        body.append('consent_version', CONSENT_VERSION);
      }
      body.append('_gotcha', gotcha ? gotcha.value : '');

      fetch(FORMSPREE_ENDPOINT, {
        method: 'POST',
        body: body,
        headers: { Accept: 'application/json' }
      }).then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        form.reset();
        say('Thanks, we’ll email you once.', 'ok');
      }).catch(function () {
        say('Sorry, that did not go through. Please try again in a moment.', 'error');
      }).then(function () {
        button.disabled = false;
      });
    });
  });
})();
