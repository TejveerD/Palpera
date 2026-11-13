/*
 * Palpera signup forms -> Formspree.
 *
 * DO NOT SHIP until FORMSPREE_ENDPOINT holds TJ's real form URL
 * (Formspree dashboard -> your form -> Integration, looks like
 * https://formspree.io/f/abcdwxyz).
 *
 * Free plan (checked November 2026): 50 submissions a month, and submissions
 * are kept for 30 days only. Export the list regularly, and move it into a
 * mailing-list tool before sending the launch email.
 */
var FORMSPREE_ENDPOINT = 'https://formspree.io/f/REPLACE_WITH_FORM_ID';

(function () {
  'use strict';

  var notConnected = /REPLACE_WITH_FORM_ID/.test(FORMSPREE_ENDPOINT);
  if (notConnected && window.console) {
    console.warn('Palpera: FORMSPREE_ENDPOINT is still the placeholder. Signups will not be sent.');
  }

  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  Array.prototype.forEach.call(document.querySelectorAll('form[data-signup]'), function (form) {
    var input = form.querySelector('input[type="email"]');
    var button = form.querySelector('button[type="submit"]');
    var status = form.querySelector('.signup-status');

    form.setAttribute('action', FORMSPREE_ENDPOINT);
    form.setAttribute('method', 'POST');

    function say(text, kind) {
      status.textContent = text;
      status.classList.toggle('is-ok', kind === 'ok');
      status.classList.toggle('is-error', kind === 'error');
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

      if (notConnected) {
        say('Signup is not connected yet. Please try again soon.', 'error');
        return;
      }

      button.disabled = true;
      say('Sending…', null);

      fetch(FORMSPREE_ENDPOINT, {
        method: 'POST',
        body: new FormData(form),
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
