# Palpera coming-soon page

One page, plain HTML, CSS and JavaScript, with no framework and no build step. GitHub Pages serves the repo as it is.

```
index.html
css/site.css
js/sequence.js        scroll sequence (canvas, desktop only)
js/carousel.js        colour carousel
js/callouts.js        pointer callouts on the held last frame + spec lists
js/signup.js          Formspree signup (FORMSPREE_ENDPOINT lives here)
data/specs.json       every spec value (edit this; empty = "Coming soon")
data/anchors.json     where each callout points (from palpera_pod.py)
docs/BRIEF.md         the build brief
assets/hero/          stack.webp: hero stack still (phones, reduced motion)
assets/sequence/      frame_0001.webp ... frame_0150.webp
assets/colours/       violet / red / graphite / silver / sand .webp
tools/palpera_pod.py        Blender scene script
concept-renders/            full-size renders from palpera_pod.py (not used by the page)
concept-renders/website/    PNG sources of the page's sequence and colour stills
tools/frames_to_webp.py     PNG renders -> WebP assets
```

## Before launch: do not ship until all of these are done

1. **Real renders.** Done: `assets/` holds the WebP versions of the `sequence` and `colours` renders from `palpera_pod.py` (sources in `concept-renders/website/`).
2. **Formspree endpoint.** Done: `https://formspree.io/f/xnpdjprv`, set in `FORMSPREE_ENDPOINT` at the top of `js/signup.js`.
3. **Contact email.** Replace `[YOUR CONTACT EMAIL]` in the footer of `index.html`, ideally as a `mailto:` link.

Formspree's free plan (checked November 2026): 50 submissions a month, and submission history is kept for **30 days only**. Export the list from the Formspree dashboard regularly so no address is lost. Before the launch email, move the list into a mailing-list tool.

## Rendering the sequence and colour stills

`tools/palpera_pod.py` builds the scene and contains both website shots (`sequence`, 150 frames, and `colours`, five stills taken from the last sequence frame with the pod colour swapped). It must be in `tools/` before any rendering.

Windows:

```
set PALPERA_OUT=C:\palpera\renders
set PALPERA_QUALITY=final
set PALPERA_SHOTS=sequence,colours
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b -P tools\palpera_pod.py
python tools\frames_to_webp.py C:\palpera\renders
```

Use `PALPERA_QUALITY=preview` first for a fast low-resolution check of the motion. Never pass `--watermark` for these renders.

`frames_to_webp.py` writes `assets/sequence/`, `assets/hero/stack.webp` and `assets/colours/`. It reports how far `colours/violet.png` differs from the last sequence frame (it should be about zero) and prints the total size; the budget is under 10 MB for the sequence. If the frame count changes, update `data-frames` on the `.sequence` section in `index.html`.

The frames carry their own lavender studio backdrop. On load, `sequence.js` samples the top and bottom edge colours of frame 1 and paints the stage with them, and the bottom of the stage fades into the band below. In the hero, muted text and the accent are darkened (`#4A4462`, `#4A31A6`) so they stay above 4.5:1 on the backdrop.

## Editing specs

All spec values live in `data/specs.json`. Edit a `value` (and optionally a `unit`), commit, and the page updates; an empty value shows as "Coming soon". Entries can be added, removed or reordered without touching code. `callouts` point at the pod (each needs an `anchor` from `data/anchors.json`: sensor, clip, pod_top, pod_rear, pod_front); `specs` are the list after the stage. Never fill a value with a guess.

## How the page behaves

- **Desktop (900 px or wider, no reduced-motion setting):** the hero text sits over a full-screen canvas. Scrolling plays the 150 frames: the stack merges, the glasses come in, the pod clips on and the camera settles. The page then holds on the last frame while the colour carousel takes over the same stage. The scroll length is `--seq-length` in `css/site.css` (420vh); tune it by feel. Frame 1 loads immediately. The rest load after the page has finished loading, coarse to fine, so early scrolling already shows motion.
- **Phones and reduced motion:** a static hero still, then the carousel. No frame file is ever requested.
- **Callouts:** after the animation the last frame holds while the visitor keeps scrolling; each callout's ring scales in, its line draws out and its label fades in, one at a time, then all fade as the carousel controls appear. Everything follows the same smoothed scroll value as the frames, so it scrubs backwards exactly as forwards, and only opacity, transform and stroke-dashoffset change (no layout). Scroll budget per phase: `VH` at the top of `js/sequence.js`. Label placement: `PLACE` at the top of `js/callouts.js`.
- **Window size and resizing:** the whole width of every frame is always shown. In a window taller than 16:9 the backdrop colours fill the space above and below, with a soft fade at the frame edges. Resizing across 900 px switches between the scroll and static versions without a reload and keeps your place on the page.
- **Handover to the carousel:** the violet pod stays on the canvas (the last frame); the other four colours fade in over it, so there is no image swap at the handover.
- **Carousel:** arrow buttons, colour dots, Left/Right/Home/End keys while it has focus, swipe, and two-finger trackpad swipe. Changes are announced through a polite live region. Scrolling back into the sequence resets it to violet. A keyboard user who tabs into it is taken to the end of the sequence.

## Local preview

```
python -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` straight from disk also works, but a local server is closer to GitHub Pages.

## Publishing on GitHub Pages

1. Create a public repo named `palpera` and push this folder to it.
2. In the repo, go to Settings → Pages → Build and deployment: Source "Deploy from a branch", branch `main`, folder `/ (root)`.
3. The site appears at `https://<username>.github.io/palpera/`.

All paths are relative, so the same files work later at the root of a custom domain.
