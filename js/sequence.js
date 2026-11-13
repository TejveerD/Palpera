/*
 * Palpera scroll sequence.
 *
 * A pre-rendered frame sequence drawn to a <canvas> and scrubbed by scroll
 * position. Only runs when <html> has the .seq class (desktop width and no
 * reduced-motion preference); otherwise no frame file is ever requested.
 *
 * Frames come from the section's data attributes:
 *   data-frames="150"
 *   data-frame-pattern="assets/sequence/frame_{n}.webp"
 *   data-frame-pad="4"            ({n} is 1-based and zero padded)
 *
 * When the last frame is on screen the section gets .at-end, and the colour
 * carousel (carousel.js) takes over the same stage. The last frame and the
 * violet carousel still must be the same image, so the handover is invisible.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  var section = document.querySelector('.sequence');
  if (!section || !root.classList.contains('seq')) return;

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
  var BG = '#CFC9E0';             // replaced by the sampled frame edge colour

  var frames = new Array(COUNT);   // HTMLImageElement once decoded
  var loadedCount = 0;

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

  function loadFrame(i) {
    return new Promise(function (resolve) {
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
    });
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

  /* ---------- Scroll and drawing ---------- */

  function readScroll() {
    var rect = section.getBoundingClientRect();
    var range = rect.height - stage.offsetHeight;
    var p = range > 0 ? -rect.top / range : 0;
    p = Math.min(1, Math.max(0, p / PLAY_SHARE));
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

  // Same geometry as CSS object-fit: cover; object-position: 50% 50%, so the
  // canvas and the carousel <img> elements line up exactly.
  function draw(img) {
    var cw = canvas.width, ch = canvas.height;
    var iw = img.naturalWidth, ih = img.naturalHeight;
    var scale = Math.max(cw / iw, ch / ih);
    var dw = iw * scale, dh = ih * scale;
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, cw, ch);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, (cw - dw) / 2, (ch - dh) / 2, dw, dh);
    drawnImg = img;
  }

  function setAtEnd(value) {
    if (value === atEnd) return;
    atEnd = value;
    section.classList.toggle('at-end', value);
    section.dispatchEvent(new CustomEvent(value ? 'sequence:end' : 'sequence:leave-end'));
  }

  function tick(now) {
    rafId = 0;
    var dt = lastTime ? Math.min(now - lastTime, 100) : 16.7;
    lastTime = now;

    var k = 1 - Math.pow(1 - EASE, dt / 16.7);
    shown += (target - shown) * k;
    if (Math.abs(target - shown) < 0.01) shown = target;

    if (sizeDirty) { resizeCanvas(); drawnImg = null; }

    var index = Math.round(shown);
    var img = nearestLoaded(index);
    if (img && img !== drawnImg) draw(img);

    // Hand over only when the real last frame is actually on the canvas.
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
    if (!rafId) rafId = requestAnimationFrame(tick);
  }

  function onScroll() {
    readScroll();
    requestTick();
  }

  /* ---------- Start ---------- */

  function fallBackToStatic() {
    // Frame 1 could not be loaded: show the static stills instead.
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('resize', onResize);
    root.classList.remove('seq');
    section.classList.remove('at-end');
  }

  var wideQuery = window.matchMedia('(min-width: 900px)');

  function onResize() {
    // A window narrowed below the desktop width gets the static version.
    if (!wideQuery.matches) return fallBackToStatic();
    sizeDirty = true;
    readScroll();
    requestTick();
  }

  readScroll();
  shown = target;   // no easing on a reload halfway down the page

  // Frame 1 is the hero stack, so the canvas is never blank for long. Load it
  // (and the frame for the current scroll position) straight away; the rest
  // waits until the page has painted and finished its own loading.
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
      var top = avg(0), bottom = avg(h - 1);
      section.style.setProperty('--stage-top', top);
      section.style.setProperty('--stage-bottom', bottom);
      BG = top;
      drawnImg = null;
    } catch (e) { /* keep the fallback colours */ }
  }

  loadFrame(0).then(function (ok) {
    if (!ok) return fallBackToStatic();
    sampleBackdrop(frames[0]);
    var here = Math.round(target);
    if (here > 0) loadFrame(here);
    requestTick();
  });

  function startPreload() {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(preloadAll, { timeout: 1500 });
    } else {
      setTimeout(preloadAll, 200);
    }
  }
  if (document.readyState === 'complete') startPreload();
  else window.addEventListener('load', startPreload, { once: true });

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onResize);
  if ('ResizeObserver' in window) {
    new ResizeObserver(function () { sizeDirty = true; requestTick(); }).observe(canvas);
  }

  // Keyboard visitors who tab into the carousel before scrolling there are
  // taken straight to the end of the sequence, where the carousel is live.
  section.addEventListener('focusin', function () {
    if (atEnd) return;
    var rect = section.getBoundingClientRect();
    var range = rect.height - stage.offsetHeight;
    var y = window.scrollY + rect.top + range * (PLAY_SHARE + (1 - PLAY_SHARE) / 2);
    window.scrollTo({ top: y, behavior: 'instant' });
    readScroll();
    shown = target;
    // Hand over now, not on the next animation frame, so the carousel
    // buttons are focusable before the visitor presses Tab again.
    if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
    keyboardJump = true;
    tick(performance.now());
    if (!frames[COUNT - 1]) loadFrame(COUNT - 1);
  });

  // Debug handle for checking load progress in the console.
  window.palperaSequence = {
    get loaded() { return loadedCount; },
    count: COUNT
  };
})();
