/*
 * Palpera lids (docs/L2-REDESIGN.md, section 4).
 *
 * Desktop (the .seq version): two violet lids cover the stage, leaving a
 * slit. Scrolling opens them: the top lid rises until only the 64 px bar is
 * left, the bottom lid drops off screen, and the name shrinks from its large
 * centred size into the bar. sequence.js owns the scroll and calls
 *   update(t)   every animation frame it draws; t is 0..1 through the
 *               opening phase, from the same smoothed scroll value as the
 *               frames, so scrolling back up reverses it exactly
 * Positions and sizes are measured in layout(), on resize only. update()
 * writes transform and opacity only, and keeps out of the three Chrome
 * layout traps: no SVG scaling, no class toggling mid-scroll, and no
 * opacity change from exactly 0 (faded things rest at 0.001).
 *
 * Phones and reduced motion: no motion; CSS lays the lids out as blocks.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  var lids = document.querySelector('[data-lids]');
  var top = document.querySelector('[data-lid-top]');
  var bottom = document.querySelector('[data-lid-bottom]');
  var content = document.querySelector('[data-lid-content]');
  var name = document.querySelector('[data-name]');
  var links = document.querySelector('[data-bar-links]');
  if (!lids || !top || !bottom || !name) return;

  var BAR = 64;              // bar height, px
  var SLIT_TOP = 0.31;       // slit starts 31% down the window
  var SLIT_H = 0.41;         // and is 41% of its height
  var NAME_W = 0.83;         // name spans 83% of the window width on load
  var NAME_END = 28;         // px, the name's size in the bar
  var NAME_LEFT = 72;        // px from the left in the bar
  var FEET = 14 / 900;       // letters' feet clipped by this share of the window height
  var MIN = 0.001;           // faded things rest here, never at exactly 0

  var G = null;              // geometry from layout()
  var last = {};
  var lastT = -1;

  function ease(v) {
    v = v < 0 ? 0 : v > 1 ? 1 : v;
    return v * v * (3 - 2 * v);
  }

  function active() { return root.classList.contains('seq'); }

  /* ---------- Layout (resize, fonts, switching versions) ---------- */

  // A zero-size inline-block marks the text baseline inside the name.
  var mark = document.createElement('span');
  mark.className = 'name-baseline';
  mark.setAttribute('aria-hidden', 'true');
  name.firstElementChild.appendChild(mark);

  function layout() {
    if (!active()) { G = null; return; }
    var vw = document.documentElement.clientWidth;
    var vh = window.innerHeight;
    var topH = Math.round(vh * SLIT_TOP);
    var botTop = Math.round(vh * (SLIT_TOP + SLIT_H));

    top.style.height = topH + 'px';
    bottom.style.top = botTop + 'px';
    bottom.style.height = (vh - botTop) + 'px';

    // Size the name so it spans 83% of the window: measure at 100 px.
    name.style.transform = 'none';
    name.style.fontSize = '100px';
    var w100 = name.getBoundingClientRect().width;
    var F = Math.round(100 * NAME_W * vw / Math.max(1, w100));
    name.style.fontSize = F + 'px';
    var box = name.getBoundingClientRect();
    var base = mark.getBoundingClientRect().top - box.top;   // baseline, from the element's top
    var W = box.width;

    var s1 = NAME_END / F;
    // Start: centred, feet clipped by the slit's top edge (lid coordinates).
    var x0 = (vw - W) / 2;
    var y0 = topH + Math.round(vh * FEET) - base;
    // End: in the bar. The bar is the lid's last 64 px; centre the letters
    // (cap top about 0.7 em above the baseline, descender about 0.22 em
    // below) on the bar's middle line.
    var barMid = topH - BAR / 2;
    var baseline1 = barMid + (0.7 - 0.22) / 2 * NAME_END;
    var x1 = NAME_LEFT;
    var y1 = baseline1 - base * s1;

    G = { vw: vw, vh: vh, topH: topH, botTop: botTop, F: F, W: W,
          x0: x0, y0: y0, x1: x1, y1: y1, s1: s1, base: base };
    last = {};
    lastT = -1;
    if (window.palperaSequence && window.palperaSequence.redraw) window.palperaSequence.redraw();
  }

  function clear() {
    [top, bottom, name, content, links].forEach(function (el) {
      if (!el) return;
      el.style.transform = el.style.opacity = el.style.pointerEvents = '';
    });
    top.style.height = bottom.style.top = bottom.style.height = name.style.fontSize = '';
    last = {};
    lastT = -1;
  }

  /* ---------- Per animation frame: transform and opacity only ---------- */

  function set(key, value, apply) {
    if (last[key] === value) return;
    last[key] = value;
    apply(value);
  }

  function update(t) {
    if (!G) return;
    t = Math.round(t * 10000) / 10000;
    if (t === lastT) return;
    lastT = t;

    var lid = ease(t);
    set('top', (-(G.topH - BAR) * lid).toFixed(2), function (v) {
      top.style.transform = 'translateY(' + v + 'px)';
    });
    set('bottom', ((G.vh - G.botTop) * lid).toFixed(2), function (v) {
      bottom.style.transform = 'translateY(' + v + 'px)';
    });

    // The name: one continuous move, finished by 85% of the phase so it
    // has cleared the links before they fade in. Scale changes evenly on a
    // log scale, so the shrink reads as one steady motion.
    var n = ease(t / 0.85);
    var s = Math.pow(G.s1, n);
    var x = G.x0 + (G.x1 - G.x0) * n;
    var y = G.y0 + (G.y1 - G.y0) * n;
    set('name', x.toFixed(2) + ',' + y.toFixed(2) + ',' + s.toFixed(5), function () {
      name.style.transform = 'translate(' + x.toFixed(2) + 'px,' + y.toFixed(2) + 'px) scale(' + s.toFixed(5) + ')';
    });

    // Headline and signup fade over the first 40%.
    var c = Math.max(MIN, 1 - ease(t / 0.4));
    // Once faded, things are moved off screen with a transform so they
    // cannot be clicked: switching pointer-events mid-scroll costs a layout,
    // and so does going between no transform and a transform, so these
    // always carry one (CSS starts them at translateY(0)).
    set('content', c.toFixed(3), function (v) {
      content.style.opacity = v;
      content.style.transform = v < 0.05 ? 'translateY(200vh)' : 'translateY(0px)';
    });

    // Bar links fade in over the last 30%.
    var l = Math.max(MIN, ease((t - 0.7) / 0.3));
    set('links', l.toFixed(3), function (v) {
      links.style.opacity = v;
      links.style.transform = v < 0.05 ? 'translateY(-200px)' : 'translateY(0px)';
    });
  }

  /* ---------- Keyboard ---------- */

  // A bar link focused while the lids are still closed: open them first.
  // The signup in the bottom lid focused after it has gone: back to the top.
  if (links) {
    links.addEventListener('focusin', function () {
      if (active() && lastT < 1 && window.palperaSequence) window.palperaSequence.scrollToOpened();
    });
  }
  if (content) {
    content.addEventListener('focusin', function () {
      if (active() && lastT > 0.3) window.scrollTo({ top: 0, behavior: 'instant' });
    });
  }

  /* ---------- Hooks ---------- */

  window.palperaLids = {
    layout: layout,
    clear: clear,
    update: update,
    // For the checks: the name's box and the links' boxes right now.
    boxes: function () {
      var r = name.getBoundingClientRect();
      return { name: r, links: Array.prototype.map.call(links.children, function (a) { return a.getBoundingClientRect(); }),
               linksOpacity: +(links.style.opacity || 1) };
    }
  };

  window.addEventListener('resize', layout);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);
  layout();
})();
