/*
 * Palpera consent: cookie settings, the consent banner, analytics and
 * third-party embeds.
 *
 * Today the site uses no cookies, no analytics and no third-party embeds,
 * so CONFIG below switches nothing on and no banner is shown. Everything a
 * visitor needs (settings, policies) works anyway. To add an optional
 * service later:
 *
 *   analytics  set CONFIG.analytics to { name, src, attrs }. The script is
 *              only added to the page after the visitor allows analytics.
 *              Update cookies.html and privacy.html at the same time.
 *   embeds     set CONFIG.embeds to { name } (e.g. 'YouTube'), then mark up
 *              each embed as a placeholder:
 *                <div class="embed" data-embed data-src="https://..."
 *                     data-title="Video: ..." data-provider="YouTube"></div>
 *              It shows a "Load" button until the visitor allows embedded
 *              content, so nothing is fetched from the provider before that.
 *
 * When CONFIG changes in a way visitors must see again, bump CONFIG.version:
 * stored choices from an older version are ignored and the banner returns.
 *
 * The visitor's choice is kept in localStorage ('palpera.consent'). That is
 * strictly necessary (it is the record of their choice), sets no cookie and
 * is never sent anywhere.
 */
(function () {
  'use strict';

  var CONFIG = {
    version: 1,
    analytics: null,     // e.g. { name: 'Example Analytics', src: 'https://…/script.js', attrs: { 'data-domain': '…' } }
    embeds: null         // e.g. { name: 'YouTube' }
  };

  var KEY = 'palpera.consent';
  var BASE = document.documentElement.getAttribute('data-base-legal') || '';

  /* ---------- Stored choice ---------- */

  function read() {
    try {
      var v = JSON.parse(window.localStorage.getItem(KEY) || 'null');
      return v && v.version === CONFIG.version ? v : null;
    } catch (e) { return null; }
  }

  function write(choice) {
    var v = { version: CONFIG.version, analytics: !!choice.analytics, embeds: !!choice.embeds,
              date: new Date().toISOString() };
    try { window.localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) { /* private mode: applies to this page only */ }
    return v;
  }

  var choice = read();
  function allowed(kind) { return !!(CONFIG[kind] && choice && choice[kind]); }
  function optionalInUse() { return !!(CONFIG.analytics || CONFIG.embeds); }

  /* ---------- Applying it ---------- */

  var analyticsLoaded = false;
  function apply() {
    if (allowed('analytics') && !analyticsLoaded) {
      analyticsLoaded = true;
      var sc = document.createElement('script');
      sc.src = CONFIG.analytics.src;
      sc.defer = true;
      var attrs = CONFIG.analytics.attrs || {};
      Object.keys(attrs).forEach(function (k) { sc.setAttribute(k, attrs[k]); });
      document.head.appendChild(sc);
    }
    Array.prototype.forEach.call(document.querySelectorAll('[data-embed]'), function (box) {
      if (allowed('embeds')) loadEmbed(box);
      else placeholder(box);
    });
  }

  function loadEmbed(box) {
    if (box.querySelector('iframe')) return;
    box.textContent = '';
    var f = document.createElement('iframe');
    f.src = box.getAttribute('data-src');
    f.title = box.getAttribute('data-title') || 'Embedded content';
    f.loading = 'lazy';
    f.referrerPolicy = 'strict-origin-when-cross-origin';
    f.allowFullscreen = true;
    box.appendChild(f);
  }

  function placeholder(box) {
    if (box.querySelector('.embed-ask')) return;
    var provider = box.getAttribute('data-provider') || (CONFIG.embeds && CONFIG.embeds.name) || 'another company';
    var ask = el('div', 'embed-ask');
    ask.appendChild(el('p', '', (box.getAttribute('data-title') || 'This content') + ' is hosted by ' + provider +
      '. Loading it sends your IP address to ' + provider + ' and may set their cookies.'));
    var once = el('button', 'btn', 'Load it once');
    once.type = 'button';
    once.addEventListener('click', function () { loadEmbed(box); });
    var always = el('button', 'link-button', 'Always allow embedded content');
    always.type = 'button';
    always.addEventListener('click', function () { choice = write({ analytics: choice && choice.analytics, embeds: true }); apply(); });
    ask.appendChild(once);
    ask.appendChild(always);
    box.appendChild(ask);
  }

  /* ---------- UI ---------- */

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // Banner: only when an optional service is in use and the visitor has not
  // chosen yet. Accepting and rejecting are equally easy.
  var banner = null;
  function showBanner() {
    if (banner || !optionalInUse() || choice) return;
    banner = el('section', 'consent-banner');
    banner.setAttribute('aria-label', 'Cookie choices');
    var used = [];
    if (CONFIG.analytics) used.push('analytics (' + CONFIG.analytics.name + ')');
    if (CONFIG.embeds) used.push('embedded content (' + CONFIG.embeds.name + ')');
    var p = el('p', '');
    p.appendChild(document.createTextNode('With your permission we would also use ' + used.join(' and ') +
      '. Nothing optional runs until you choose. '));
    var a = el('a', '', 'Cookie policy');
    a.href = BASE + 'cookies.html';
    p.appendChild(a);
    banner.appendChild(p);
    var row = el('div', 'consent-actions');
    [['Allow all', function () { decide({ analytics: true, embeds: true }); }],
     ['Reject all', function () { decide({ analytics: false, embeds: false }); }],
     ['Choose', function () { openSettings(); }]].forEach(function (b, i) {
      var btn = el('button', i < 2 ? 'btn' : 'btn btn-quiet', b[0]);
      btn.type = 'button';
      btn.addEventListener('click', b[1]);
      row.appendChild(btn);
    });
    banner.appendChild(row);
    document.body.appendChild(banner);
  }

  function hideBanner() {
    if (banner) { banner.remove(); banner = null; }
  }

  function decide(c) {
    var had = { analytics: allowed('analytics') };
    choice = write(c);
    hideBanner();
    // A script cannot be taken back out of a running page: reload to stop
    // analytics after consent is withdrawn.
    if (had.analytics && !allowed('analytics')) { window.location.reload(); return; }
    apply();
  }

  // Settings: always available from "Cookie settings" in the footer.
  var dialog = null;
  function openSettings() {
    if (!dialog) {
      dialog = el('dialog', 'consent-dialog');
      dialog.setAttribute('aria-labelledby', 'consent-title');
      var h = el('h2', '', 'Cookie settings');
      h.id = 'consent-title';
      dialog.appendChild(h);
      dialog.appendChild(el('p', '', optionalInUse()
        ? 'Choose what this site may use. You can change this at any time.'
        : 'This site uses no cookies, no analytics and no third-party embeds, so there is nothing to switch on. If that changes, the options will appear here and we will ask you first.'));
      var form = el('form', '');
      form.method = 'dialog';
      form.appendChild(row('necessary', 'Strictly necessary',
        'Remembers the choice you make here, in your browser only. No cookie, and it is never sent to us.', true, true));
      form.appendChild(row('analytics', 'Analytics',
        CONFIG.analytics ? 'Counts visits so we can see how the page is used (' + CONFIG.analytics.name + ').' : 'Not used on this site.',
        allowed('analytics'), !CONFIG.analytics));
      form.appendChild(row('embeds', 'Embedded content',
        CONFIG.embeds ? 'Videos or maps hosted by ' + CONFIG.embeds.name + ', which receives your IP address and may set cookies.' : 'Not used on this site.',
        allowed('embeds'), !CONFIG.embeds));
      var actions = el('div', 'consent-actions');
      var save = el('button', 'btn', optionalInUse() ? 'Save choices' : 'Close');
      save.value = 'save';
      actions.appendChild(save);
      var link = el('a', '', 'Cookie policy');
      link.href = BASE + 'cookies.html';
      actions.appendChild(link);
      form.appendChild(actions);
      dialog.appendChild(form);
      dialog.addEventListener('close', function () {
        if (dialog.returnValue !== 'save' || !optionalInUse()) return;
        decide({ analytics: form.elements.analytics.checked, embeds: form.elements.embeds.checked });
      });
      document.body.appendChild(dialog);
    } else {
      dialog.querySelector('[name="analytics"]').checked = allowed('analytics');
      dialog.querySelector('[name="embeds"]').checked = allowed('embeds');
    }
    dialog.returnValue = '';
    if (dialog.showModal) dialog.showModal(); else dialog.setAttribute('open', '');
  }

  function row(name, title, text, checked, disabled) {
    var lab = el('label', 'consent-row');
    var box = el('input', '');
    box.type = 'checkbox';
    box.name = name;
    box.checked = !!checked;
    box.disabled = !!disabled;
    lab.appendChild(box);
    var t = el('span', '');
    t.appendChild(el('strong', '', title));
    t.appendChild(el('span', 'consent-row-text', text));
    lab.appendChild(t);
    return lab;
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-consent-open]');
    if (b) { e.preventDefault(); openSettings(); }
  });

  window.palperaConsent = {
    open: openSettings,
    allowed: allowed,
    get choice() { return choice; },
    config: CONFIG
  };

  apply();
  showBanner();
})();
