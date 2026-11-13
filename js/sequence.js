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

  // Share of the scroll range used to play the frames. The rest is a hold on
  // the last frame so the carousel can be used before the stage unpins.
  var PLAY_SHARE = 0.86;
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

  var target = 0;                  // frame position wanted by scroll (float)
  var shown = 0;                   // smoothed frame position (float)
  var drawnImg = null;             // image currently on the canvas
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
      var x = c.getContext('2d');
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
      var here = Math.round(target);
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

  function progress() {
    var rect = section.getBoundingClientRect();
    var range = rect.height - stage.offsetHeight;
    return range > 0 ? -rect.top / range : 0;
  }

  function readScroll() {
    var p = Math.min(1, Math.max(0, progress() / PLAY_SHARE));
    target = p * (COUNT - 1);
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
    var w = Math.round(canvas.clientWidth * dpr);
    var h = Math.round(canvas.clientHeight * dpr);
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
  function draw(img) {
    var cw = canvas.width, ch = canvas.height;
    var dpr = cw / Math.max(1, canvas.clientWidth);
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
    }
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
    if (Math.abs(target - shown) < 0.01) shown = target;

    if (sizeDirty) { resizeCanvas(); drawnImg = null; }

    var index = Math.round(shown);
    var img = nearestLoaded(index);
    if (img && img !== drawnImg) draw(img);

    // Hand over only when the real last frame is actually on the canvas
    // (or when a keyboard visitor jumped here: the violet carousel still is
    // the same picture, so it can stand in until the frame arrives).
    setAtEnd(index === COUNT - 1 && (img === frames[COUNT - 1] || keyboardJump));
    if (index !== COUNT - 1) keyboardJump = false;

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
  function onFocusIn() {
    if (atEnd) return;
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
    return window.scrollY + rect.top + range * (PLAY_SHARE + (1 - PLAY_SHARE) / 2);
  }

  /* ---------- Switching between the scroll and static versions ---------- */

  function enable() {
    active = true;
    root.classList.add('seq');
    window.addEventListener('scroll', onScroll, { passive: true });
    section.addEventListener('focusin', onFocusIn);
    sizeDirty = true;
    drawnImg = null;
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
  }

  // The scroll version's height depends on the window height (420vh) and the
  // two versions differ hugely in height, so a resize would otherwise drop
  // the visitor somewhere else on the page. What is at the top of the window
  // is noted on every scroll (by the time a resize event arrives the layout
  // has already changed) and brought back after each resize.
  var anchors = [section.ownerDocument.querySelector('.hero'), section]
    .concat(Array.prototype.slice.call(document.querySelectorAll('main > section, .site-footer')));

  function captureAnchor() {
    if (active) {
      var p = progress();
      if (p < 1) return { seq: p };        // still inside the pinned stage
    }
    for (var i = 0; i < anchors.length; i++) {
      var el = anchors[i];
      if (!el) continue;
      var r = el.getBoundingClientRect();
      if (r.bottom > 1) return { el: el, top: r.top };
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
    restoreAnchor(anchor);
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
