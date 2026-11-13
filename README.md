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
concept-renders/            master stills and the turntable video (not used by the page)
tools/frames_to_webp.py     PNG renders -> WebP assets
```

## Before launch: do not ship until all of these are done

1. **Real renders.** Done: `assets/` holds the WebP versions of the `sequence` and `colours` renders from `palpera_pod.py` (the source PNGs and turntable frames were removed from the repo history on 14 November 2026 to cut its size; they can be re-rendered with `tools/palpera_pod.py`).
2. **Formspree endpoint.** Done: `https://formspree.io/f/xnpdjprv`, set in `FORMSPREE_ENDPOINT` at the top of `js/signup.js`.
3. **Contact email.** Replace `[YOUR CONTACT EMAIL]` in the footer of `index.html`, ideally as a `mailto:` link.

Formspree's free plan (checked November 2026): 50 submissions a month, and submission history is kept for **30 days only**. Export the list from the Formspree dashboard regularly so no address is lost. Before the launch email, move the list into a mailing-list tool.

## Rendering the sequence and colour stills

`tools/palpera_pod.py` builds the scene and renders both website shots: `sequence` (299 frames by default, `PALPERA_SEQ_SCALE=2`) and `colours` (five stills taken from the last sequence frame with the pod colour swapped). It writes WebP directly (about 25 KB a frame) and `anchors.json` (callout positions). Each object follows one smooth, baked curve; the four other pods close up along their row behind violet.

On TJ's laptop (script in `C:\Users\tejve\Palpera`, about 20 to 25 minutes on the RTX card):

```
set PALPERA_OUT=%CD%\renders&& set PALPERA_QUALITY=final&& set PALPERA_SHOTS=sequence,colours&& "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b -P palpera_pod.py
```

Upload everything in `renders\sequence`, `renders\colours` and `renders\anchors.json` to the repo (GitHub web upload, up to 100 files per batch). Then, in the repo:

```
python tools/frames_to_webp.py <folder with sequence/, colours/, anchors.json>
```

This copies the frames into `assets/sequence/` (WebP at 1600 px is copied as is, not recompressed), crops the phone hero still, copies `anchors.json` to `data/`, sets `data-frames` in `index.html`, checks that the violet still matches the last frame, and prints the total size (budget: under 10 MB). Use `PALPERA_QUALITY=preview` for a quick low-resolution look at the motion, and `PALPERA_SEQ_FRAMES=first,middle,last` (or frame numbers) to render only a few frames. Never pass `--watermark` for real renders.

## L2 "Eyelid" redesign (preview)

`preview/` holds the redesign from `docs/L2-REDESIGN.md`, reachable at `/Palpera/preview/` (noindex). The live root is untouched until TJ approves it. The preview has its own `index.html`, `css/` and `js/` (adds `js/lids.js` for the opening and `js/team.js`) and reads the shared `data/` and `assets/` from the root through `../` paths (`data-base="../"` on `<html>`).

- Opening: two violet lids leave a slit over frame 1; scrolling (the `opening` phase in `VH`) opens them and moves the name into the 64 px bar. Same smoothed scroll value, transform and opacity only, measured on resize only.
- Chrome layout traps to keep out (measured): scaling SVG elements; toggling a class or `pointer-events` mid-scroll; changing opacity from exactly 0; switching an element between no transform and a transform (faded elements are parked off screen with a transform and always carry one).
- "Who we are" reads `data/team.json`; while it lists nobody, the section and its bar link stay hidden.
- New frames for the redesign (opening lens 40, no shift; last frame unchanged) go in `preview/assets/sequence/` until promotion, so the live site keeps frames that suit its own layout.

To promote: move `preview/index.html`, `preview/css`, `preview/js` to the root, drop the `../` paths and `data-base`, move the new frames to `assets/sequence/`, remove the noindex tag, delete `preview/`.

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
