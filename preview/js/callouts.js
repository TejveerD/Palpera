/*
 * Palpera callouts (brief 6.6) and spec list (brief 6.7).
 *
 * Data: data/specs.json (headings and values, edited by TJ) and
 * data/anchors.json (where each anchor lands in the last sequence frame,
 * written by tools/palpera_pod.py; replace it whenever the frames are
 * re-rendered). An empty value shows as "Coming soon".
 *
 * Desktop: pointer callouts over the held last frame. sequence.js owns the
 * scroll and calls:
 *   layout(stageW, imgTop, imgH, stageH)  when the frame's place changes
 *   update(t, opacity)                    every animation frame it draws;
 *                                         t is 0..1 through the callout
 *                                         phase, from the smoothed scroll
 * update() only writes opacity, transform and stroke-dashoffset, so the
 * callout phase never triggers layout. All measuring happens in layout(),
 * which runs on resize only.
 *
 * Phones and reduced motion: the same callouts as a plain list under the
 * still. Both: the other specs as a list after the stage.
 */
(function () {
  'use strict';

  var section = document.querySelector('.sequence');
  var layer = document.querySelector('[data-callouts]');
  var svg = layer && layer.querySelector('svg');
  var labelsBox = layer && layer.querySelector('[data-callout-labels]');
  var ringsBox = layer && layer.querySelector('[data-callout-rings]');
  var heading = layer && layer.querySelector('[data-callout-heading]');
  var staticList = document.querySelector('[data-callout-list]');
  var specList = document.querySelector('[data-spec-list]');
  var specSection = document.querySelector('[data-specs]');
  if (!section || !layer) return;

  var SVGNS = 'http://www.w3.org/2000/svg';

  // Where each label goes, as fractions of the frame (like anchors.json):
  // the elbow where the diagonal meets the horizontal run, the run's length,
  // and its direction (1 = right, -1 = left). Chosen for clear space on the
  // three-quarter frame: above the glasses, or below and right of the pod.
  var PLACE = {
    sensor:    { elbow: [0.585, 0.70], run: 0.15, dir: 1 },
    clip:      { elbow: [0.585, 0.19], run: 0.14, dir: -1 },
    pod_top:   { elbow: [0.765, 0.22], run: 0.14, dir: 1 },
    pod_rear:  { elbow: [0.810, 0.70], run: 0.13, dir: 1 },
    pod_front: { elbow: [0.680, 0.60], run: 0.12, dir: 1 }
  };
  var MARGIN = 24;      // px kept clear at the window edges
  var GAP = 8;          // px between the run and the label above it
  var RING_R = 6;

  var items = [];       // { el, inner, ring, line, len, last: {} }
  var ready = false;
  var geom = null;
  var lastT = -1, lastO = -1;

  function text(entry) {
    var v = (entry.value || '').trim();
    if (!v) return { text: 'Coming soon', pending: true };
    return { text: entry.unit ? v + ' ' + entry.unit : v, pending: false };
  }

  function el(tag, cls, content) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (content != null) e.textContent = content;
    return e;
  }

  /* ---------- Building from the data ---------- */

  function build(specs, anchors) {
    var callouts = (specs.callouts || []).filter(function (c) {
      return anchors[c.anchor] && PLACE[c.anchor];
    });

    callouts.forEach(function (c) {
      c.dir = PLACE[c.anchor].dir;
      var t = text(c);
      var wrap = el('div', 'co-label' + (c.dir < 0 ? ' is-left' : ''));
      var inner = el('div', 'co-label-inner');
      var detail = (c.detail || '').trim();
      // With a detail paragraph the label is a button that opens it (hover,
      // focus or click), once all callouts are showing (see setLive).
      var face = el(detail ? 'button' : 'div', 'co-face');
      face.appendChild(el('span', 'co-heading', c.heading));
      face.appendChild(el('span', 'co-value' + (t.pending ? ' is-pending' : ''), t.text));
      inner.appendChild(face);
      var para = null;
      if (detail) {
        var id = 'co-detail-' + c.anchor;
        face.type = 'button';
        face.setAttribute('aria-expanded', 'false');
        face.setAttribute('aria-controls', id);
        face.tabIndex = -1;
        var more = el('span', 'co-more');
        face.appendChild(more);
        para = el('p', 'co-detail', detail);
        para.id = id;
        inner.appendChild(para);
        wire(wrap, face);
      }
      wrap.appendChild(inner);
      labelsBox.appendChild(wrap);

      var line = document.createElementNS(SVGNS, 'path');
      line.setAttribute('class', 'co-line');
      svg.appendChild(line);
      // The ring is HTML, not SVG: scaling an SVG element makes the browser
      // redo SVG layout, while scaling a positioned box is compositor-only.
      var ringPos = el('div', 'co-ring');
      var ring = el('div', 'co-ring-dot');
      ringPos.appendChild(ring);
      ringsBox.appendChild(ringPos);

      items.push({ data: c, a: anchors[c.anchor], p: PLACE[c.anchor], face: detail ? face : null,
                   more: detail ? more : null,
                   el: wrap, inner: inner, ring: ring, ringPos: ringPos, line: line, len: 0, last: {} });
    });

    // Static list (phones, reduced motion): same headings and values.
    if (staticList) {
      callouts.forEach(function (c) { staticList.appendChild(row(c)); });
    }
    // The other specs, after the stage.
    if (specList) {
      (specs.specs || []).forEach(function (s) { specList.appendChild(row(s)); });
      if (specSection) specSection.hidden = !(specs.specs || []).length;
    }
  }

  function row(entry) {
    var t = text(entry);
    var d = el('div', 'spec');
    d.appendChild(el('dt', 'spec-heading', entry.heading));
    d.appendChild(el('dd', 'spec-value' + (t.pending ? ' is-pending' : ''), t.text));
    if ((entry.detail || '').trim()) d.appendChild(el('dd', 'spec-detail', entry.detail.trim()));
    return d;
  }

  /* ---------- Expandable labels ---------- */

  // Open while hovered or focused; a click pins it open (and closes others).
  function wire(wrap, face) {
    var hover = false, focus = false, pinned = false;
    function sync() {
      var open = live && (hover || focus || pinned);
      if (wrap.classList.contains('is-open') === open) return;
      wrap.classList.toggle('is-open', open);
      face.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    wrap.addEventListener('mouseenter', function () { hover = true; sync(); });
    wrap.addEventListener('mouseleave', function () { hover = false; sync(); });
    face.addEventListener('focus', function () { focus = true; sync(); });
    face.addEventListener('blur', function () { focus = false; sync(); });
    face.addEventListener('click', function () {
      var was = pinned;
      closers.forEach(function (close) { close(); });
      pinned = !was;
      sync();
    });
    face.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { pinned = false; hover = false; face.blur(); sync(); }
    });
    closers.push(function () { pinned = false; sync(); });
    syncers.push(function (off) { if (off) { pinned = false; hover = false; } sync(); });
  }
  var closers = [], syncers = [];

  // The labels can only be opened once every callout is showing and before
  // the fade to the carousel; scrolling away closes them.
  var live = false;
  function setLive(on) {
    if (on === live) return;
    live = on;
    // Set on the buttons themselves: toggling a class on the layer makes
    // the browser run layout, and this happens mid-scroll.
    items.forEach(function (it) {
      if (!it.face) return;
      it.face.tabIndex = on ? 0 : -1;
      it.face.style.pointerEvents = on ? 'auto' : '';
      it.more.style.transform = on ? 'scale(1)' : '';
    });
    syncers.forEach(function (s) { s(!on); });
  }

  /* ---------- Layout (resize only) ---------- */

  function doLayout() {
    if (!ready || !geom) return;
    var W = geom.w, top = geom.top, H = geom.h, VH = geom.vh;
    svg.setAttribute('width', W);
    svg.setAttribute('height', VH);
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + VH);

    items.forEach(function (it) {
      var ax = it.a.x * W, ay = top + it.a.y * H;
      var ex = it.p.elbow[0] * W, ey = top + it.p.elbow[1] * H;
      var lw = it.el.offsetWidth + (it.face ? 24 : 0), lh = it.el.offsetHeight;   // + the open icon
      var run = Math.max(it.p.run * W, lw + 4);

      // Keep the label inside the window with a margin.
      ey = Math.max(ey, MARGIN + lh + GAP);
      ey = Math.min(ey, VH - MARGIN);
      if (it.p.dir > 0) ex = Math.min(ex, W - MARGIN - run);
      else ex = Math.max(ex, MARGIN + run);
      var rx = ex + it.p.dir * run;

      it.line.setAttribute('d', 'M' + ax.toFixed(1) + ' ' + ay.toFixed(1) +
                                ' L' + ex.toFixed(1) + ' ' + ey.toFixed(1) +
                                ' L' + rx.toFixed(1) + ' ' + ey.toFixed(1));
      it.len = Math.hypot(ex - ax, ey - ay) + run;
      it.line.style.strokeDasharray = it.len.toFixed(1);
      it.ringPos.style.transform = 'translate(' + (ax - RING_R).toFixed(1) + 'px,' + (ay - RING_R).toFixed(1) + 'px)';
      it.anchorAt = { x: ax, y: ay };   // for the placement check

      var lx = it.p.dir > 0 ? ex : rx;
      it.el.style.transform = 'translate(' + Math.round(lx) + 'px,' + Math.round(ey - GAP - lh) + 'px)';
      it.box = { x: lx, y: ey - GAP - lh, w: lw, h: lh };   // for the overlap check
      it.last = {};
    });
    lastT = lastO = -1;
  }

  /* ---------- Per animation frame: opacity, transform, dashoffset ---------- */

  function ease(v) {
    v = v < 0 ? 0 : v > 1 ? 1 : v;
    return v * v * (3 - 2 * v);
  }

  function set(it, key, value, apply) {
    if (it.last[key] === value) return;
    it.last[key] = value;
    apply(value);
  }

  function update(t, opacity) {
    if (!ready) return;
    t = Math.round(t * 10000) / 10000;
    opacity = Math.round(opacity * 1000) / 1000;
    if (t === lastT && opacity === lastO) return;
    lastT = t; lastO = opacity;

    layer.style.opacity = opacity;
    layer.style.visibility = opacity > 0 && t > 0 ? 'visible' : 'hidden';

    setLive(t >= 1 && opacity >= 0.98);

    var n = items.length;
    var h = ease(t * n / 0.3);
    if (heading) {
      heading.style.opacity = h;
      heading.style.transform = 'translateY(' + ((1 - h) * 6).toFixed(2) + 'px)';
    }
    items.forEach(function (it, i) {
      var u = t * n - i;                          // 0..1 for this callout
      // ring, line, label overlap closely; each callout is in by 70% of its
      // share, the rest is a short beat before the next one starts
      var ring = ease(u / 0.14);
      var draw = ease((u - 0.06) / 0.38);
      var lab = ease((u - 0.36) / 0.32);
      set(it, 'ring', ring.toFixed(3), function (v) {
        it.ring.style.transform = 'scale(' + v + ')';
      });
      set(it, 'draw', draw.toFixed(4), function (v) {
        it.line.style.strokeDashoffset = (it.len * (1 - v)).toFixed(2);
      });
      set(it, 'lab', lab.toFixed(3), function (v) {
        it.inner.style.opacity = v;
        it.inner.style.transform = 'translateY(' + ((1 - v) * 6).toFixed(2) + 'px)';
      });
    });
  }

  function layout(w, top, h, vh) {
    geom = { w: w, top: top, h: h, vh: vh };
    doLayout();
  }

  window.palperaCallouts = {
    count: function () { return ready ? items.length : 4; },
    layout: layout,
    update: update,
    boxes: function () { return items.map(function (it) { return it.box; }); },
    anchorsAt: function () { return items.map(function (it) { return { name: it.data.anchor, x: it.anchorAt.x, y: it.anchorAt.y }; }); }
  };

  /* ---------- Load ---------- */

  function json(path) {
    return fetch(path, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(path + ' ' + r.status);
      return r.json();
    });
  }

  // Shared data files: the preview reads them from the site root (data-base="../").
  var BASE = document.documentElement.getAttribute('data-base') || '';
  Promise.all([json(BASE + 'data/specs.json'), json(BASE + 'data/anchors.json')]).then(function (res) {
    build(res[0], res[1].anchors || {});
    ready = true;
    doLayout();
    document.dispatchEvent(new CustomEvent('callouts:ready'));
  }).catch(function (err) {
    if (window.console) console.warn('Palpera: spec data not loaded.', err);
    if (specSection) specSection.hidden = true;
  });
})();
