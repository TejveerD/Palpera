/*
 * Palpera hero: the text over the frames (fluted spec, sections 4.1 to 4.3).
 *
 * sequence.js owns the scroll and calls:
 *   layout(stageW, imgTop, imgH, stageH)  when the frame's place changes
 *                                          (resize, fonts arriving)
 *   update(move, statement)               every animation frame it draws;
 *                                          move is 0..1 through the camera
 *                                          move, statement 0..1 its opacity
 * update() writes only opacity and transform, so scrolling never triggers
 * layout. Elements are never left without a transform and their opacity
 * never sits at exactly 0 (both cost a layout in Chrome).
 *
 *   paragraph, signup, headline  fade out over the first quarter of the move
 *   brand name                   one move from the text column to the top
 *                                centre, 32 px to 24 px (translate + scale)
 *   top links                    fade in over the last third
 *   statement                    fades in and out on the held last frame
 */
(function () {
  'use strict';

  var hero = document.querySelector('[data-hero]');
  if (!hero) return;
  var brand = hero.querySelector('[data-brand]');
  var nav = hero.querySelector('[data-nav]');
  var block = hero.querySelector('[data-hero-block]');
  var statement = hero.querySelector('[data-statement]');

  // Mock-up geometry (1440 x 900 window, frame drawn 1440 x 810 from y 45).
  var MOCK = { w: 1440, frameTop: 45, frameH: 810 };
  var BLOCK_Y = 560, STATEMENT_Y = 720;   // top of the signup block and statement
  var NAME_END_TOP = 12, NAME_END_SCALE = 24 / 32;
  var MIN = 0.001;                        // never exactly 0 (see above)

  var g = null;                           // measured on layout
  var last = { brand: '', block: '', nav: '', st: '' };

  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function ease(v) { v = clamp01(v); return v * v * (3 - 2 * v); }

  function frameY(mockY, imgTop, imgH) {
    return imgTop + (mockY - MOCK.frameTop) / MOCK.frameH * imgH;
  }

  function layout(W, imgTop, imgH, H) {
    var u = W / MOCK.w;
    // offsetLeft/Top ignore transforms, so the start position is read
    // without undoing the current move.
    var x0 = brand.offsetLeft, y0 = brand.offsetTop, w = brand.offsetWidth;
    var k = NAME_END_SCALE;
    g = {
      dx: W / 2 - (w * k) / 2 - x0,
      dy: NAME_END_TOP * u - y0,
      k: k
    };
    // Signup block below the pod and temple, but never off the bottom.
    var bh = block.offsetHeight;
    var bt = Math.min(frameY(BLOCK_Y, imgTop, imgH), H - bh - Math.max(16, 24 * u));
    block.style.top = Math.round(Math.max(bt, 80 * u)) + 'px';
    var sh = statement.offsetHeight;
    var stTop = Math.min(frameY(STATEMENT_Y, imgTop, imgH), H - sh - Math.max(36, 48 * u));
    statement.style.top = Math.round(stTop) + 'px';
    g.brandEnd = { left: W / 2 - (w * k) / 2, top: NAME_END_TOP * u, w: w * k, h: brand.offsetHeight * k };
    // Where the top links rest once faded in (their transform ends at 0).
    g.navBox = { left: nav.offsetLeft, top: nav.offsetTop, w: nav.offsetWidth, h: nav.offsetHeight };
    last = { brand: '', block: '', nav: '', st: '' };
  }

  // keep: stays focusable while faded (the top links: keyboard visitors can
  // reach them anywhere; CSS shows them while they have focus).
  function show(el, key, t, transform, keep) {
    var v = Math.max(MIN, Math.round(t * 1000) / 1000).toFixed(3);
    var s = v + '|' + transform;
    if (last[key] === s) return;
    last[key] = s;
    el.style.opacity = v;
    el.style.transform = transform;
    el.style.visibility = keep || t > MIN ? 'visible' : 'hidden';
  }

  function update(move, st) {
    if (!g) return;
    var e = ease(move);
    var s = 1 + (g.k - 1) * e;
    var tb = 'translate(' + (g.dx * e).toFixed(2) + 'px,' + (g.dy * e).toFixed(2) + 'px) scale(' + s.toFixed(4) + ')';
    if (last.brand !== tb) { last.brand = tb; brand.style.transform = tb; }

    var b = 1 - ease(move / 0.25);
    show(block, 'block', b, 'translateY(' + (-(1 - b) * 16).toFixed(2) + 'px)');

    var n = ease((move - 2 / 3) * 3);
    show(nav, 'nav', n, 'translateY(' + (-(1 - n) * 4).toFixed(2) + 'px)', true);

    show(statement, 'st', st, 'translateY(' + ((1 - st) * 8).toFixed(2) + 'px)');
  }

  function clear() {
    g = null;
    [brand, nav, block, statement].forEach(function (el) {
      el.style.opacity = el.style.transform = el.style.visibility = el.style.top = '';
    });
  }

  window.palperaHero = {
    layout: layout,
    update: update,
    clear: clear,
    // For the overlap checks in testing.
    brandEnd: function () { return g && g.brandEnd; },
    // The header in its final place: the name at the top centre and the links.
    headerBoxes: function () { return g ? [g.brandEnd, g.navBox] : []; }
  };
})();
