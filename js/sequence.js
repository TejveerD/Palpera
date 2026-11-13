/*
 * Palpera scroll sequence.
 *
 * A pre-rendered frame sequence drawn to a <canvas> and scrubbed by scroll
 * position. Runs while <html> has the .seq class: a window at least 900 px
 * wide and no reduced-motion preference. Below that, or with reduced motion,
 * the page shows the static stills and no frame file is requested. Resizing
 * the window across 900 px switches between the two without a reload.
 *
 * Frames come from the section's data attributes:
 *   data-frames="150"
 *   data-frame-pattern="assets/sequence/frame_{n}.webp"
 *   data-frame-pad="4"            ({n} is 1-based and zero padded)
 *
 * Framing: the whole width of every frame is always shown (the pods sit far
 * right at the start and the glasses fill the width at the end). In a window
 * wider than 16:9 the top and bottom are cropped; in a taller one the
 * backdrop colours sampled from frame 1 fill the space above and below.
 * The carousel <img> elements use the same geometry in css/site.css.
 *
 * When the last frame is on screen the section gets .at-end, and the colour
 * carousel (carousel.js) takes over the same stage. The last frame and the
 * violet carousel still must be the same image, so the handover is invisible.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  var section = document.querySelector('.sequence');
  if (!section) return;

  var canvas = section.querySelector('.stage-canvas');
  var stage = section.querySelector('.stage');
  var ctx = canvas.getContext('2d', { alpha: false });

  var COUNT = parseInt(section.dataset.frames, 10) || 150;
  var PATTERN = section.dataset.framePattern;
  var PAD = parseInt(section.dataset.framePad, 10) || 4;

  // Scroll budget for each phase, in viewport heights (tune by feel). The
  // pinned section is these added up plus one viewport for the stage itself.
  //   frames    the 150-frame animation
  //   callout   per callout on the held last frame (callouts.js)
  //   hold      after the last callout
  //   fade      callouts fade out while the carousel controls fade in
  //   carousel  the carousel, live, before the stage unpins
  var VH = { frames: 275, callout: 38, hold: 45, fade: 30, carousel: 45 };
  var phase;                       // the budget above as shares of 0..1
  function computePhases() {
    var n = window.palperaCallouts ? window.palperaCallouts.count() : 0;
    var total = VH.frames + n * VH.callout + VH.hold + VH.fade + VH.carousel;
    var f = VH.frames / total, c = n * VH.callout / total;
    phase = {
      frames: f,
      callouts: [f, f + c],
      fade: [f + c + VH.hold / total, f + c + (VH.hold + VH.fade) / total],
      total: total
    };
    phase.carouselMid = (phase.fade[1] + 1) / 2;
    section.style.setProperty('--seq-length', (total + 100) + 'vh');
  }
  computePhases();

  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function frameAt(p) { return clamp01(p / phase.frames) * (COUNT - 1); }
  // How far the displayed position moves toward the scroll position per
  // 60 Hz frame. Lower is smoother but lags more.
  var EASE = 0.16;
  var MAX_PARALLEL = 6;

  // Backdrop colours, replaced by the ones sampled from frame 1.
  var TOP = '#CFC9E0';
  var BOTTOM = '#DCD7EA';

  var wideQuery = window.matchMedia('(min-width: 900px)');
  var calmQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

  var frames = new Array(COUNT);   // HTMLImageElement once decoded
  var loadedCount = 0;
  var loadingStarted = false;
  var broken = false;              // frame 1 failed: static version for good
  var active = false;

  var target = 0;                  // scroll position wanted, 0..1 of the section
  var shown = 0;                   // smoothed scroll position: drives everything
  var drawnImg = null;             // image currently on the canvas (null: redraw)
  var drawnKey = '';
  var cssW = 1, cssH = 1;          // canvas size in CSS px, measured on resize
  var sizeDirty = true;
  var rafId = 0;
  var lastTime = 0;
  var atEnd = false;
  var keyboardJump = false;

  function url(i) {
    var n = String(i + 1);
    while (n.length < PAD) n = '0' + n;
    return PATTERN.replace('{n}', n);
  }

  /* ---------- Loading ---------- */

  var pending = {};
  function loadFrame(i) {
    if (pending[i]) return pending[i];
    return (pending[i] = new Promise(function (resolve) {
      if (frames[i]) return resolve(true);
      var img = new Image();
      img.decoding = 'async';
      img.src = url(i);
      var done = function () {
        frames[i] = img;
        loadedCount++;
        requestTick();
        resolve(true);
      };
      if (img.decode) {
        img.decode().then(done, function () { resolve(false); });
      } else {
        img.onload = done;
        img.onerror = function () { resolve(false); };
      }
    }));
  }

  // Coarse to fine: every 16th frame, then every 8th, 4th, 2nd, then the rest.
  // A fast scroll early on still shows motion, just with bigger steps, and
  // the steps close up as loading continues.
  function loadOrder() {
    var order = [];
    var seen = new Uint8Array(COUNT);
    [16, 8, 4, 2, 1].forEach(function (step) {
      for (var i = 0; i < COUNT; i += step) {
        if (!seen[i]) { seen[i] = 1; order.push(i); }
      }
    });
    if (!seen[COUNT - 1]) order.push(COUNT - 1);
    // Make sure the last frame (the carousel handover) arrives early.
    order.splice(order.indexOf(COUNT - 1), 1);
    order.splice(1, 0, COUNT - 1);
    return order;
  }

  function preloadAll() {
    var queue = loadOrder().filter(function (i) { return !frames[i]; });
    var running = 0;
    function next() {
      while (running < MAX_PARALLEL && queue.length) {
        running++;
        loadFrame(queue.shift()).then(function () { running--; next(); });
      }
    }
    next();
  }

  // Sample the studio backdrop from frame 1's top and bottom edges, so the
  // canvas fill and the stage behind it match the renders exactly.
  function sampleBackdrop(img) {
    try {
      var w = 64, h = 36;
      var c = document.createElement('canvas');
      c.width = w; c.height = h;
      var x = c.getContext('2d', { willReadFrequently: true });
      x.drawImage(img, 0, 0, w, h);
      var avg = function (y) {
        var d = x.getImageData(0, y, w, 1).data, r = 0, g = 0, b = 0;
        for (var i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; }
        var n = d.length / 4;
        return 'rgb(' + Math.round(r / n) + ',' + Math.round(g / n) + ',' + Math.round(b / n) + ')';
      };
      TOP = avg(0);
      BOTTOM = avg(h - 1);
      section.style.setProperty('--stage-top', TOP);
      section.style.setProperty('--stage-bottom', BOTTOM);
      drawnImg = null;
    } catch (e) { /* keep the fallback colours */ }
  }

  // Frame 1 is the hero stack, so the canvas is never blank for long. Load it
  // (and the frame for the current scroll position) straight away; the rest
  // waits until the page has painted and finished its own loading.
  function startLoading() {
    if (loadingStarted) return;
    loadingStarted = true;
    loadFrame(0).then(function (ok) {
      if (!ok) { broken = true; return sync(); }
      sampleBackdrop(frames[0]);
      var here = Math.round(frameAt(target));
      if (here > 0) loadFrame(here);
      requestTick();
    });
    var later = function () {
      if ('requestIdleCallback' in window) requestIdleCallback(preloadAll, { timeout: 1500 });
      else setTimeout(preloadAll, 200);
    };
    if (document.readyState === 'complete') later();
    else window.addEventListener('load', later, { once: true });
  }

  /* ---------- Scroll and drawing ---------- */

  // Positions are measured only when sizes change (measure()), never while
  // scrolling: the per-frame path is arithmetic on window.scrollY, so the
  // scroll, the frames and the callouts never force a layout.
  var M = { top: 0, range: 1, anchors: [] };
  function measure() {
    var y = window.scrollY;
    var rect = section.getBoundingClientRect();
    M.top = rect.top + y;
    M.range = Math.max(1, rect.height - stage.offsetHeight);
    M.anchors = anchors.map(function (el) {
      if (!el) return null;
      var r = el.getBoundingClientRect();
      return { el: el, top: r.top + y, bottom: r.bottom + y };
    });
  }

  function progress() {
    return (window.scrollY - M.top) / M.range;
  }

  function readScroll() {
    target = clamp01(progress());
  }

  // Nearest loaded frame to i, searching outward.
  function nearestLoaded(i) {
    if (frames[i]) return frames[i];
    for (var d = 1; d < COUNT; d++) {
      if (i - d >= 0 && frames[i - d]) return frames[i - d];
      if (i + d < COUNT && frames[i + d]) return frames[i + d];
    }
    return null;
  }

  function resizeCanvas() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    cssW = canvas.clientWidth;
    cssH = canvas.clientHeight;
    var w = Math.round(cssW * dpr);
    var h = Math.round(cssH * dpr);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    sizeDirty = false;
  }

  // Full width, centred vertically (see the note at the top). In a window
  // taller than 16:9 the frame's top and bottom edges fade into the backdrop
  // colours. The frame's position is handed to CSS (--img-top, --img-h,
  // --fade-h, --fade-on) so the carousel <img> elements and their fades sit
  // on exactly the same device pixels.
  var FADE = 0.16;                 // fade band, as a share of the frame height

  function transparent(rgb) {
    var m = /rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(rgb);
    return m ? 'rgba(' + m[1] + ',' + m[2] + ',' + m[3] + ',0)' : 'rgba(0,0,0,0)';
  }

  var geometry = '';
  // Draws frame a, with frame b laid over it at the given opacity: the
  // in-between of two neighbouring frames, so a slow scroll moves smoothly
  // instead of stepping from frame to frame.
  function draw(img, next, alpha) {
    var cw = canvas.width, ch = canvas.height;
    var dpr = cw / Math.max(1, cssW);
    var dw = cw;
    var dh = Math.round(img.naturalHeight * cw / img.naturalWidth);
    var dy = Math.round((ch - dh) / 2);
    var fade = Math.round(dh * FADE);

    if (dy > 0) {
      ctx.fillStyle = TOP;
      ctx.fillRect(0, 0, cw, dy + 1);
      ctx.fillStyle = BOTTOM;
      ctx.fillRect(0, dy + dh - 1, cw, ch - dy - dh + 1);
    }
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, 0, dy, dw, dh);
    if (next && alpha > 0) {
      ctx.globalAlpha = alpha;
      ctx.drawImage(next, 0, dy, dw, dh);
      ctx.globalAlpha = 1;
    }
    if (dy > 0) {
      var g = ctx.createLinearGradient(0, dy, 0, dy + fade);
      g.addColorStop(0, TOP);
      g.addColorStop(1, transparent(TOP));
      ctx.fillStyle = g;
      ctx.fillRect(0, dy, cw, fade);
      g = ctx.createLinearGradient(0, dy + dh, 0, dy + dh - fade);
      g.addColorStop(0, BOTTOM);
      g.addColorStop(1, transparent(BOTTOM));
      ctx.fillStyle = g;
      ctx.fillRect(0, dy + dh - fade, cw, fade);
    }
    drawnImg = img;

    var key = [dy, dh, fade, dpr].join();
    if (key !== geometry) {
      geometry = key;
      section.style.setProperty('--img-top', dy / dpr + 'px');
      section.style.setProperty('--img-h', dh / dpr + 'px');
      section.style.setProperty('--fade-h', fade / dpr + 'px');
      section.style.setProperty('--fade-on', dy > 0 ? '1' : '0');
      if (window.palperaCallouts) {
        window.palperaCallouts.layout(cssW, dy / dpr, dh / dpr, cssH);
      }
    }
  }

  var controls = section.querySelector('.carousel-controls');
  var controlsT = -1;
  function setControls(t) {
    if (!controls || t === controlsT) return;
    controlsT = t;
    controls.style.opacity = t;
    controls.style.transform = 'translate(-50%,' + ((1 - t) * 12).toFixed(2) + 'px)';
    controls.style.visibility = t > 0 ? 'visible' : 'hidden';
  }
  function clearControls() {
    if (!controls) return;
    controlsT = -1;
    controls.style.opacity = controls.style.transform = controls.style.visibility = '';
  }

  function setAtEnd(value) {
    if (value === atEnd) return;
    atEnd = value;
    section.classList.toggle('at-end', value);
    section.dispatchEvent(new CustomEvent(value ? 'sequence:end' : 'sequence:leave-end'));
  }

  function tick(now) {
    rafId = 0;
    if (!active) return;
    var dt = lastTime ? Math.min(now - lastTime, 100) : 16.7;
    lastTime = now;

    var k = 1 - Math.pow(1 - EASE, dt / 16.7);
    shown += (target - shown) * k;
    // Snap once within a tenth of a pixel of scroll.
    if (Math.abs(target - shown) * M.range < 0.1) shown = target;

    if (sizeDirty) { resizeCanvas(); drawnImg = null; }

    var pos = frameAt(shown);
    var index = Math.min(COUNT - 1, Math.floor(pos + 1e-6));
    var frac = index >= COUNT - 1 ? 0 : pos - index;
    var img = nearestLoaded(index);
    // Blend only while scrolling slowly, where steps would show; a fast
    // scroll draws single frames and costs half as much.
    var slow = Math.abs(frameAt(target) - pos) < 1.5;
    var next = slow && img === frames[index] && frac > 0 ? frames[index + 1] : null;
    var mix = next ? Math.round(frac * 32) / 32 : 0;   // 32 steps per frame gap
    // At rest, show the nearest whole frame: a blend left on screen would
    // show a faint double image of anything moving fast (the glasses).
    if (shown === target && next) {
      if (frac >= 0.5) { img = next; }
      next = null;
      mix = 0;
    }
    var key = (img ? img.src : '') + '|' + (next ? next.src : '') + '|' + mix;
    if (img && (key !== drawnKey || drawnImg === null)) {
      draw(img, next, mix);
      drawnKey = key;
    }

    // Hand over only when the real last frame is actually on the canvas
    // (or when a keyboard visitor jumped here: the violet carousel still is
    // the same picture, so it can stand in until the frame arrives).
    var fadeT = clamp01((shown - phase.fade[0]) / (phase.fade[1] - phase.fade[0]));
    setAtEnd(index === COUNT - 1 && fadeT >= 0.5 &&
             (img === frames[COUNT - 1] || keyboardJump));
    if (index !== COUNT - 1) keyboardJump = false;

    // Callouts and carousel controls follow the same smoothed value, so they
    // scrub backwards exactly as they play forwards. Opacity and transform
    // only (see callouts.js).
    if (window.palperaCallouts) {
      window.palperaCallouts.update(
        clamp01((shown - phase.callouts[0]) / Math.max(1e-6, phase.callouts[1] - phase.callouts[0])),
        1 - fadeT);
    }
    setControls(fadeT);

    if (shown !== target) {
      requestTick();
    } else {
      lastTime = 0;
    }
  }

  function requestTick() {
    if (active && !rafId) rafId = requestAnimationFrame(tick);
  }

  function onScroll() {
    readScroll();
    requestTick();
  }

  // Keyboard visitors who tab into the carousel before scrolling there are
  // taken straight to the end of the sequence, where the carousel is live.
  function onFocusIn(e) {
    // Only the carousel: the callout labels have their own buttons.
    if (atEnd || !(e.target.closest && e.target.closest('[data-carousel]'))) return;
    window.scrollTo({ top: endScrollY(), behavior: 'instant' });
    readScroll();
    shown = target;
    // Hand over now, not on the next animation frame, so the carousel
    // buttons are focusable before the visitor presses Tab again.
    if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
    keyboardJump = true;
    tick(performance.now());
    if (!frames[COUNT - 1]) loadFrame(COUNT - 1);
  }

  // Scroll position where the last frame holds and the carousel is live.
  function endScrollY() {
    var rect = section.getBoundingClientRect();
    var range = rect.height - stage.offsetHeight;
    return window.scrollY + rect.top + range * phase.carouselMid;
  }

  /* ---------- Switching between the scroll and static versions ---------- */

  function enable() {
    active = true;
    root.classList.add('seq');
    window.addEventListener('scroll', onScroll, { passive: true });
    section.addEventListener('focusin', onFocusIn);
    sizeDirty = true;
    drawnImg = null;
    measure();
    readScroll();
    shown = target;   // no easing after a reload or a switch
    startLoading();
    requestTick();
  }

  function disable() {
    active = false;
    root.classList.remove('seq');
    window.removeEventListener('scroll', onScroll);
    section.removeEventListener('focusin', onFocusIn);
    if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
    setAtEnd(false);
    clearControls();
  }

  // callouts.js loads the spec data after this script starts; the scroll
  // length depends on how many callouts there are, so re-measure then.
  document.addEventListener('callouts:ready', function () {
    var anchor = captureAnchor();
    computePhases();
    geometry = '';
    drawnImg = null;
    measure();
    if (active) { restoreAnchor(anchor); measure(); readScroll(); shown = target; requestTick(); }
  });

  // The scroll version's height depends on the window height (see VH) and the
  // two versions differ hugely in height, so a resize would otherwise drop
  // the visitor somewhere else on the page. What is at the top of the window
  // is noted on every scroll (by the time a resize event arrives the layout
  // has already changed) and brought back after each resize.
  var anchors = [section.ownerDocument.querySelector('.hero'), section]
    .concat(Array.prototype.slice.call(document.querySelectorAll('main > section, .site-footer')));

  // From the cached positions, so it is cheap enough to run on every scroll.
  function captureAnchor() {
    if (active) {
      var p = progress();
      if (p < 1) return { seq: p };        // still inside the pinned stage
    }
    var y = window.scrollY;
    for (var i = 0; i < M.anchors.length; i++) {
      var a = M.anchors[i];
      if (a && a.bottom - y > 1) return { el: a.el, top: a.top - y };
    }
    return null;
  }

  function restoreAnchor(a) {
    if (!a) return;
    var y;
    if (a.seq !== undefined && active) {
      // Still the scroll version: same point in the animation.
      var rect = section.getBoundingClientRect();
      y = window.scrollY + rect.top + a.seq * (rect.height - stage.offsetHeight);
    } else if (a.seq !== undefined) {
      // Leaving the scroll version from inside the animation: the top of the
      // page early on, the colour carousel later.
      y = a.seq < 0.35 ? 0 : window.scrollY + section.getBoundingClientRect().top;
    } else if (active && a.el === section) {
      y = endScrollY();                    // static carousel -> live carousel
    } else if (active && a.el.classList.contains('hero')) {
      y = 0;
    } else {
      y = window.scrollY + a.el.getBoundingClientRect().top - a.top;
    }
    window.scrollTo({ top: Math.max(0, y), behavior: 'instant' });
    if (active) { readScroll(); shown = target; requestTick(); }
  }

  function wanted() {
    return wideQuery.matches && !calmQuery.matches && !broken;
  }

  var lastAnchor = null;
  var anchorQueued = false;
  function noteAnchor() {
    if (anchorQueued) return;
    anchorQueued = true;
    requestAnimationFrame(function () {
      anchorQueued = false;
      if (!restoring) lastAnchor = captureAnchor();
    });
  }

  // Switch versions if needed, then put back what was at the top.
  var restoring = false;
  function sync() {
    var anchor = lastAnchor || captureAnchor();
    var want = wanted();
    if (want !== active) { if (want) enable(); else disable(); }
    restoring = true;
    measure();
    restoreAnchor(anchor);
    measure();
    lastAnchor = captureAnchor();
    restoring = false;
    sizeDirty = true;
    requestTick();
  }

  window.addEventListener('scroll', noteAnchor, { passive: true });
  window.addEventListener('resize', sync);
  if (calmQuery.addEventListener) calmQuery.addEventListener('change', sync);
  else if (calmQuery.addListener) calmQuery.addListener(sync);

  if ('ResizeObserver' in window) {
    new ResizeObserver(function () { sizeDirty = true; requestTick(); }).observe(canvas);
    // Page height changes without a window resize (web fonts arriving, the
    // spec list filling in): re-measure. Fires on size changes only.
    new ResizeObserver(function () { measure(); readScroll(); requestTick(); }).observe(document.body);
  }

  // The inline script in <head> already chose the version before first
  // paint; start the scroll version if it did.
  if (root.classList.contains('seq')) enable();
  lastAnchor = captureAnchor();

  // Debug handle for checking load progress in the console.
  window.palperaSequence = {
    get loaded() { return loadedCount; },
    get active() { return active; },
    count: COUNT
  };
})();
