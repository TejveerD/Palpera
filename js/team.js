/*
 * "Who we are" (docs/L2-REDESIGN.md, section 6), from data/team.json.
 * While the file lists nobody, the section and its bar link stay hidden;
 * adding people to the file shows both, with no code change.
 */
(function () {
  'use strict';
  var section = document.querySelector('[data-team]');
  var list = document.querySelector('[data-team-list]');
  var link = document.querySelector('[data-team-link]');
  if (!section || !list) return;
  var BASE = document.documentElement.getAttribute('data-base') || '';

  fetch(BASE + 'data/team.json', { cache: 'no-cache' }).then(function (r) {
    if (!r.ok) throw new Error('team.json ' + r.status);
    return r.json();
  }).then(function (data) {
    var people = (data.people || []).filter(function (p) { return p && (p.name || '').trim(); });
    if (!people.length) return;
    people.forEach(function (p) {
      var li = document.createElement('li');
      li.className = 'person';
      var n = document.createElement('h3'); n.textContent = p.name.trim(); li.appendChild(n);
      if ((p.role || '').trim()) { var r = document.createElement('p'); r.className = 'person-role'; r.textContent = p.role.trim(); li.appendChild(r); }
      if ((p.line || '').trim()) { var l = document.createElement('p'); l.textContent = p.line.trim(); li.appendChild(l); }
      list.appendChild(li);
    });
    section.hidden = false;
    if (link) link.hidden = false;
    document.dispatchEvent(new CustomEvent('team:ready'));
  }).catch(function () { /* stay hidden */ });
})();
