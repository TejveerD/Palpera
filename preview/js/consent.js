/*
 * Palpera cookie consent, dormant (palpera-legal-pages.md, section 5).
 *
 * The site sets no cookies and loads nothing from other companies, so there
 * is nothing to ask about. data/site.json holds one flag:
 *
 *   "nonEssential": false   no banner, and nothing non-essential may load
 *   "nonEssential": true    a banner with "Accept" and "Reject" (equal
 *                           weight) and a link to the cookie policy appears
 *                           before anything non-essential loads; the choice
 *                           is remembered and can be changed from the
 *                           "Cookie settings" link in the footer
 *
 * Anything non-essential (analytics, embeds) must load through this gate.
 * Mark it up as an inert script, which runs only after "Accept":
 *
 *   <script type="text/plain" data-consent-src="https://example.com/x.js"></script>
 *
 * Turning the flag on is a decision that changes the privacy and cookie
 * policies in the same commit.
 */
(function () {
  'use strict';

  var KEY = 'palpera.consent';     // 'accept' or 'reject', in this browser only
  var settings = document.querySelector('[data-consent-open]');

  function read() { try { return window.localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(v) { try { window.localStorage.setItem(KEY, v); } catch (e) { /* this page only */ } }

  function load() {
    Array.prototype.forEach.call(document.querySelectorAll('script[data-consent-src]'), function (inert) {
      if (inert.dataset.loaded) return;
      inert.dataset.loaded = 'yes';
      var sc = document.createElement('script');
      sc.src = inert.dataset.consentSrc;
      sc.async = true;
      inert.parentNode.insertBefore(sc, inert.nextSibling);
    });
  }

  var banner = null;
  function showBanner() {
    if (banner) { banner.querySelector('button').focus(); return; }
    banner = document.createElement('div');
    banner.className = 'consent-banner';
    banner.setAttribute('role', 'region');
    banner.setAttribute('aria-label', 'Cookie choice');
    var p = document.createElement('p');
    p.innerHTML = 'May we use optional cookies? Nothing optional loads unless you accept. See the <a href="cookies.html">cookie policy</a>.';
    banner.appendChild(p);
    var row = document.createElement('div');
    row.className = 'consent-actions';
    [['Accept', 'accept'], ['Reject', 'reject']].forEach(function (b) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn';            // same style for both: equal weight
      btn.textContent = b[0];
      btn.addEventListener('click', function () { decide(b[1]); });
      row.appendChild(btn);
    });
    banner.appendChild(row);
    document.body.appendChild(banner);
  }

  function decide(v) {
    write(v);
    if (banner) { banner.remove(); banner = null; }
    if (v === 'accept') load();
    else if (document.querySelector('script[data-consent-src][data-loaded]')) {
      // Already-running scripts cannot be unloaded: start again without them.
      window.location.reload();
    }
  }

  fetch('data/site.json', { cache: 'no-cache' }).then(function (r) {
    return r.ok ? r.json() : { nonEssential: false };
  }).catch(function () {
    return { nonEssential: false };
  }).then(function (site) {
    if (site.nonEssential !== true) return;      // dormant: no banner, nothing loads
    if (settings) {
      settings.hidden = false;
      settings.addEventListener('click', showBanner);
    }
    var v = read();
    if (v === 'accept') load();
    else if (v !== 'reject') showBanner();
  });
})();
