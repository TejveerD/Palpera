/*
 * Palpera colour carousel.
 *
 * Five stills of the pod at the three-quarter view, cross-faded. Works on its
 * own (phones, reduced motion) and as the end of the scroll sequence on
 * desktop, where it only becomes operable once the last frame is reached.
 *
 * Inputs: arrow buttons, colour dots, Left/Right/Home/End keys while the
 * carousel has focus, swipe (touch, pen, mouse drag) and horizontal trackpad
 * swipes. Changes are announced through a polite live region.
 */
(function () {
  'use strict';

  var root = document.querySelector('[data-carousel]');
  if (!root) return;

  var view = root.querySelector('[data-carousel-view]');
  var imgs = Array.prototype.slice.call(root.querySelectorAll('.carousel-img'));
  var dots = Array.prototype.slice.call(root.querySelectorAll('.dot'));
  var prev = root.querySelector('[data-carousel-prev]');
  var next = root.querySelector('[data-carousel-next]');
  var live = root.querySelector('[data-carousel-live]');
  var section = root.closest('.sequence');
  var count = imgs.length;
  var index = 0;

  function name(i) { return imgs[i].dataset.colour; }

  function show(i, announce) {
    index = (i + count) % count;
    imgs.forEach(function (img, n) { img.classList.toggle('is-active', n === index); });
    dots.forEach(function (dot, n) { dot.setAttribute('aria-pressed', n === index ? 'true' : 'false'); });
    if (announce && live) {
      live.textContent = 'Showing ' + name(index) + ' pod, ' + (index + 1) + ' of ' + count + '.';
    }
  }

  function step(d) { show(index + d, true); }

  prev.addEventListener('click', function () { step(-1); });
  next.addEventListener('click', function () { step(1); });
  dots.forEach(function (dot) {
    dot.addEventListener('click', function () { show(parseInt(dot.dataset.index, 10), true); });
  });

  root.addEventListener('keydown', function (e) {
    var key = e.key;
    if (key === 'ArrowLeft') step(-1);
    else if (key === 'ArrowRight') step(1);
    else if (key === 'Home') show(0, true);
    else if (key === 'End') show(count - 1, true);
    else return;
    e.preventDefault();
  });

  /* Swipe: pointer events. touch-action: pan-y on the view keeps vertical
     page scrolling with the finger while horizontal moves reach us. */
  var startX = 0, startY = 0, tracking = false;
  view.addEventListener('pointerdown', function (e) {
    if (e.button !== 0) return;
    tracking = true;
    startX = e.clientX;
    startY = e.clientY;
  });
  view.addEventListener('pointerup', function (e) {
    if (!tracking) return;
    tracking = false;
    var dx = e.clientX - startX, dy = e.clientY - startY;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.2) step(dx < 0 ? 1 : -1);
  });
  view.addEventListener('pointercancel', function () { tracking = false; });

  /* Trackpad: two-finger horizontal swipes arrive as wheel events with deltaX.
     Vertical wheel movement is left alone so the page keeps scrolling. */
  var acc = 0, lockUntil = 0, resetTimer = 0;
  view.addEventListener('wheel', function (e) {
    if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
    e.preventDefault();   // also stops the browser's swipe-to-go-back
    var now = Date.now();
    if (now < lockUntil) return;
    acc += e.deltaX;
    clearTimeout(resetTimer);
    resetTimer = setTimeout(function () { acc = 0; }, 180);
    if (Math.abs(acc) > 60) {
      step(acc > 0 ? 1 : -1);
      acc = 0;
      lockUntil = now + 550;   // one colour per gesture
    }
  }, { passive: false });

  /* Scroll sequence handover. Scrolling back into the animation always
     returns to white, because the frames show the white pod. */
  if (section) {
    section.addEventListener('sequence:leave-end', function () {
      if (root.contains(document.activeElement)) document.activeElement.blur();
      if (index !== 0) show(0, false);
    });
  }

  show(0, false);
})();
