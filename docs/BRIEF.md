# Palpera website: build brief

Handoff from the design sessions to Claude Code. Read this before writing any code. Decisions marked **Decided** are settled with TJ. Section 0 says what is already built. One thing still has to come from him: a real contact email (section 8).

## 0. Current state (13 November 2026, evening)

Built, deployed and checked, per Claude Code's status handoff:

- Repo `TejveerD/Palpera` (public, `main`), live at `https://tejveerd.github.io/Palpera/`. Plain HTML, CSS and JavaScript, relative paths.
- The real 150-frame sequence and five colour stills from `tools/palpera_pod.py` are in place (4.2 MB of frames). The stand-in scene is gone.
- Desktop scroll sequence, colour carousel, static phone and reduced-motion version, and the Formspree signup all work.
- The frame is always shown at full width. Taller windows are filled above and below with the backdrop colour, with soft fades. `js/sequence.js` publishes the frame's position as CSS variables on the section: `--img-top` and `--img-h` (pixels).
- Violet stays on the canvas as the last frame; the other colours fade in over it.

**Still to build: the callouts (6.6) and the spec data (6.7).** Everything else in this brief describes what exists or the rules that still apply.

## 1. What this is

Palpera is a small sensor pod that clips onto the temple of glasses the wearer already owns. It follows blinking with an infrared sensor (no camera, no screen) and tells the wearer, through an iPhone app, when their eyes need rest. A full Palpera frame is planned for later.

**Status: early development.** The hardware is not built. Everything visual is a concept.

The site is a one-page coming-soon page whose only action is an email signup.

### Rules that hold for all copy and visuals

- Wellness product, not a medical device. No "detects", "diagnoses", "prevents", "treats".
- No invented statistics, testimonials, prices, dates or battery figures.
- Renders are concept renders. Show a small "Concept render" label near them.
- Do not mention (PRODUCT)RED or any partnership. The red pod is plain red.
- Do not claim to be first. A funded competitor (Stasis) launched in November 2026.

## 2. Tech and hosting

- **Decided:** hosted on GitHub Pages. Desktop gets the scroll animation; phones do not (see 6.5).
- Recommended: plain HTML, CSS and JavaScript with no framework and no build step, so Pages serves the repo directly. One `index.html`, one stylesheet, one script, an `assets/` folder.
- Fonts from Google Fonts: Cormorant Garamond (500, 500 italic) and Figtree (400, 500, 600).

Suggested layout:

```
index.html
css/site.css
js/sequence.js        scroll sequence
js/carousel.js        colour carousel
assets/hero/          hero stack still
assets/sequence/      numbered WebP frames
assets/colours/       five three-quarter stills
tools/palpera_pod.py  Blender scene script
```

## 3. Brand

**Decided: Direction D with the Lilac dusk palette.**

| Role | Hex |
|---|---|
| Page ground | `#F9F8FC` |
| Alternate band | `#F0EDF8` |
| Tint (illustration fills) | `#E3DDF6` |
| Placeholder fill | `#ECE8F5` |
| Ink (text) | `#1E1A2E` |
| Muted text | `#575170` |
| Accent (buttons, links, violet pod) | `#5A3FC0` |
| Decorative line | `#9C8AE0` |
| Sensor dot | `#E0A458` |
| Dark band | `#2A1F5C` |
| Button on dark band | `#CFC3FA` with ink text |
| Input border | `#B5AFCB` |

Type: headings and wordmark in Cormorant Garamond 500, with italic used for one phrase of emphasis in a headline. Body and UI in Figtree. Buttons and inputs are pill shaped (fully rounded). Tone: calm, restrained, eyewear first. Not gamified.

Wordmark: "Palpera" in Cormorant Garamond with a single thin upward-opening arc beneath it (a closed eyelid), stroke in the accent colour.

Pod colours (**Decided**): violet `#5A3FC0`, red `#C8322B`, graphite `#3A3D45`, silver `#C9CCD3`, sand `#D8C7A8`. Violet is the signature. Do not print colour names as a promise; the visuals show the range.

## 4. Page structure and copy

Order of sections, top to bottom. Copy is final unless TJ changes it.

1. **Header.** Wordmark left. Links: "How it works", "Where we are", and a pill button "Notify me" that jumps to the closing signup.
2. **Hero.** Eyebrow: "In development". Headline: "Your glasses, *made aware.*" Paragraph: "Palpera is a small pod that clips onto the glasses you already wear. No camera, no screen. It follows your blinking and tells you when your eyes need rest." Signup: label "One email when we launch", email field, button "Notify me". Main graphic: the pod renders (section 6).
3. **Scroll sequence and colour carousel** (section 6). New; replaces the old static hero illustration.
4. **Three reasons.**
   - "Keep your own frames": "No new prescription and no new look. The pod clips to the temple of the glasses you already own."
   - "No camera, ever": "Palpera senses blinking with a tiny infrared sensor. It cannot take pictures of you or anyone around you."
   - "A nudge, not a dashboard": "You do not need another score to check. Palpera stays quiet until your eyes are due a break."
5. **How it works.** Three steps.
   - Step one, "Clip it on": "The pod sits on one temple of your glasses, with a short arm that reaches toward the lens."
   - Step two, "It follows your blinking": "Long stretches at a screen change how often and how fully you blink. The sensor picks that up as you work."
   - Step three, "It tells you when to rest": "When your eyes have gone too long without a break, the Palpera app on your iPhone lets you know."
6. **Where we are.** "Palpera is in early development. The first prototypes are being built and tested now, and nothing is for sale yet." Then: "The pod comes first. A Palpera frame with everything built in is planned for later. We will share real results here as soon as we have them."
7. **Closing signup** on the dark band. Headline: "Be the first to know when it is ready." Label: "One email when we launch. Nothing else."
8. **Footer.** "Palpera is a wellness product, not a medical device." plus a contact email.

The three statements in section 4 describe intended behaviour that has not been tested. TJ knows this.

## 5. Blender scene

`palpera_pod.py` builds the whole scene from code (round acetate glasses, the concept pod in five colours, a true-to-size prototype pod, studio lighting, cameras) and renders stills, a turntable and the two website shots in 6.3. **It must be in `tools/` before any rendering.** If it is missing, stop and ask TJ for it; do not build a substitute scene. The first deployed version used a stand-in scene because the script was not in the repo, and the result was unusable.

- Confirmed working on Blender 5.0.1 (Windows, RTX card) and 5.3. 1 Blender unit = 1 cm.
- Run headless, which avoids the frozen window:

```
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b -P tools\palpera_pod.py
```

- Environment variables: `PALPERA_OUT` (output folder), `PALPERA_QUALITY` (`preview`, `draft`, `final`), `PALPERA_SHOTS` (comma list: `hero`, `hero_transparent`, `lineup`, `side`, `closeup`, `prototype`, `turntable`), `PALPERA_VIDEO` (`auto`, `1`, `0`).
- On TJ's laptop the script lives in `C:\Users\tejve\Palpera`, with no clone of the repo there. A full re-render of the sequence and colours takes about 11 minutes. TJ uploads the PNGs through GitHub's web upload (100 files per batch); Claude Code then sorts them into `concept-renders/website/`, runs `tools/frames_to_webp.py`, checks the result and pushes.
- The newest script (13 November, evening) keeps the repo's opening camera (lens 35, shift_x -0.22) and adds: `anchors.json` export, `PALPERA_SEQ_SCALE` for extra in-between frames, and `PALPERA_WORLD` / `PALPERA_FLOOR` / `PALPERA_FRAME` / `PALPERA_COLOURS` overrides. It renders the same frames as the version in the repo, so replacing the file does not require a re-render.
- **Known trap:** never change an object's visibility while looping over `collection.all_objects`. It crashes Blender. The script hides whole collections instead; keep it that way.
- The pod shape is invented (4.2 cm long, 1.15 cm tall, 0.62 cm thick). The prototype box (3.0 × 2.2 × 1.2 cm) is an estimate around a Seeed XIAO nRF52840 board, not a measured design.

## 6. Scroll sequence and colour carousel

This is the main new work.

### 6.1 What the visitor sees

1. **Hero stack.** The five pods in a staggered row, violet in front. This is the main graphic at the top of the page.
2. **Merge.** As the visitor scrolls, the section pins. The four other pods slide in behind the violet pod and disappear, leaving one violet pod.
3. **Attach.** A pair of round acetate glasses comes into view. The violet pod travels to the temple and clips on.
4. **Settle.** The camera moves to the three-quarter view (the existing `Cam_Hero` framing).
5. **Callouts.** The last frame holds while the visitor keeps scrolling. Pointer lines and labels appear on the pod one at a time (section 6.6).
6. **Colour carousel.** The callouts fade, the three-quarter shot stays, and the visitor changes pod colour by swipe, arrow buttons or five colour dots. Normal scrolling continues down the page from here.

### 6.2 Technique

**Decided by TJ: whichever gives the smoothest experience.** The choice made for him: a pre-rendered frame sequence drawn to a `<canvas>` and scrubbed by scroll position.

- Why: with frames preloaded, each scroll position maps to a finished image, so motion cannot stutter on the visitor's graphics hardware, and the render quality matches the stills.
- Render about 150 frames so slow scrolling does not show steps.
- Smooth the scroll value before picking a frame: each animation frame, move a displayed position a fraction of the way toward the real scroll position, then draw the nearest frame.
- Preload in the background after first paint. The first frame is the hero stack, so there is never a blank canvas.
- **Fallback if testing shows visible stepping or the load is too heavy:** real-time 3D with three.js and a glTF export of the same scene. It is continuous by nature and far lighter, at the cost of flatter materials. Do not start there.

### 6.3 Blender shots for the page (already in `palpera_pod.py`)

`palpera_pod.py` now contains both website shots. Do not write a separate sequence script or a stand-in scene.

- `sequence`: 150 frames. The five-pod stack sits right of centre (room for the headline on the left), the four other colours tuck in behind the violet pod, the glasses are lowered into view, the pod slides onto the temple, and the camera settles on the three-quarter view.
- `colours`: five stills rendered from the last sequence frame with the pod colour swapped, so the handover to the carousel cannot jump.
- Output layout matches `tools/frames_to_webp.py`: `sequence/frame_0001.png` to `frame_0150.png`, `sequence/hero_stack.png`, `colours/<colour>.png`.
- It also writes `anchors.json`, the callout positions for section 6.6.

```
set PALPERA_OUT=C:\palpera\renders
set PALPERA_QUALITY=final
set PALPERA_SHOTS=sequence,colours
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b -P tools\palpera_pod.py
python tools\frames_to_webp.py C:\palpera\renders
```

Use `PALPERA_QUALITY=preview` first for a fast low-resolution check of the motion. Never pass `--watermark` for these renders.

The frames carry their own soft lavender studio backdrop (about `#CFC9E0` shading lighter toward the floor), not the page ground. The page has already been adjusted for that: the stage is filled with colours sampled from frame 1, the edges fade, and in the hero the muted text is `#4A4462` and the accent `#4A31A6`, giving at least 5.9 to 1 over the real frames. Keep those hero colours for anything else drawn over the frames.

### 6.4 Page implementation

- A tall wrapper (about 350 to 450 viewport heights of scroll for the sequence; tune by feel) containing a `position: sticky` full-viewport stage with the canvas.
- Draw with `requestAnimationFrame`; only redraw when the frame index changes.
- Size the canvas for the device pixel ratio, capped at 2.
- The carousel sits in the same stage after the last frame: an `<img>` per colour, cross-faded. Arrow buttons and colour dots are real `<button>` elements with labels such as "Show red pod"; arrow keys work when the carousel has focus; announce the change politely for screen readers. Swipe on touch and trackpad.
- Budget: aim for under 10 MB for the whole sequence at about 1600 px wide, and check the real number. Hero text and signup must be usable before the frames finish loading.

### 6.5 Phones and reduced motion

**Decided: desktop only for now.** Below about 900 px wide, or when the visitor has `prefers-reduced-motion` set, do not load the frame sequence at all. Show the hero stack still, then the three-quarter still with the colour carousel. The four callouts appear there as a plain list under the still, with the same headings and values, and no pointer lines.

### 6.6 Callouts on the pod

**Decided:** design T1 ("Annotated") from the design canvas. The lilac brand and serif type stay; thin pointer lines and labels are added over the held last frame. Callouts appear one at a time as the visitor scrolls. **Smoothness is the requirement TJ cares most about: nothing clunky.**

Look:

- Pointer: a small ring at the anchor (6 px radius, ground-colour fill, 1.5 px ink stroke), then a 1.25 px ink line in two segments, a diagonal and then a horizontal run.
- Label sits on the horizontal run: a small heading in Figtree 600, 13 px, uppercase, letter-spacing 0.1em, colour `#3D2A96`; under it the value in Cormorant Garamond 500, about 27 px, ink.
- A short heading for the phase, bottom left: "What is in *the pod.*" with the line "One sensor, one battery and a clip. Nothing else to wear."

The four pointer callouts, in order of appearance:

| Order | Anchor | Heading | Value |
|---|---|---|---|
| 1 | `sensor` | Blink sensor | Infrared, no camera |
| 2 | `clip` | Clip | Fits your own frame |
| 3 | `pod_top` | Weight | from the spec data |
| 4 | `pod_rear` | Battery life | from the spec data |

Positions:

- `anchors.json` gives each anchor's x and y as fractions of the last frame, from the top left. A ready copy is supplied with this brief; it matches the frames already deployed, because the last frame's camera has not changed. Put it in the site (for example `data/anchors.json`) and place pointers from it. Do not measure renders by hand and do not hard-code pixel positions. The script rewrites the file on every sequence or colours render; replace the site's copy whenever the frames are re-rendered.
- The page shows the frame at full stage width, offset vertically. Screen position of an anchor: x = anchor x × stage width; y = `--img-top` + anchor y × `--img-h`. Use the same values `js/sequence.js` already computes, and recompute when they change.
- Put each label in clear space (above the glasses, or below and to the right of the pod), keep labels inside the viewport with a margin, and make sure no two labels overlap at 1280 × 720, 1440 × 900, 1920 × 1080 and one ultrawide size.

Motion:

- Extend the pinned section so the callout phase has its own scroll length after the last frame (roughly 50 to 70 viewport heights per callout; tune by feel).
- Drive everything from the same smoothed scroll value as the frames, so it scrubs forwards and backwards. No timers, no snapping, no scroll hijacking.
- Per callout: the ring scales in, the line draws from the anchor outwards (`stroke-dashoffset`), then the label fades in with a few pixels of movement. Earlier callouts stay visible.
- Animate only `opacity`, `transform` and `stroke-dashoffset`. Nothing in this phase may trigger layout.
- After the fourth callout there is a short hold, then all callouts fade out as the carousel controls fade in.
- If the frame scrub itself shows stepping at slow scroll speeds, render more in-between frames with `PALPERA_SEQ_SCALE=2` (299 frames, same motion) and update the frame count the page expects. TJ has agreed to render more frames if needed.

### 6.7 Spec data

**Decided:** every value lives in one small data file that TJ edits (for example `data/specs.json`, or a small script file if that is simpler to load without a server). Nothing is typed into the markup.

- An entry is a heading, a value, and an optional unit. An empty value is shown as the text "Coming soon" (**Decided**). Never invent a value to fill a slot.
- Pointer callouts read from it: weight (unit g) and battery life (unit hours) are empty today.
- The other specs are a short list in their own section directly after the pinned stage, not pointers, so the pod is not crowded with lines: Charging (empty; magnetic or USB-C is undecided), Water resistance (empty; depends on the charging choice), Length (empty, unit mm), Connectivity "Bluetooth LE to iPhone", Camera "None".
- Adding, removing or reordering entries in the file must not need code changes.

## 7. Checks before calling it done

- Callout phase: scrub slowly up and down through it with the browser's performance recorder running. No dropped frames, no layout work, pointers land on the right part of the pod at every tested window size.

- Scroll through the sequence slowly and quickly on the Windows laptop: no visible stepping, no blank frames, no jump at the handover to the carousel.
- Measure total page weight and time to a usable hero.
- Keyboard only: reach the signup, operate the carousel, reach the footer.
- Text contrast at least 4.5 to 1, including muted text on the tinted bands.
- Narrow window and reduced-motion both get the static version and never request the frame files.
- Read every line of copy against the rules in section 1.

## 8. Decisions on hosting, signup and placeholders

1. **Signup form: Formspree.** **Done.** The form is connected and a real test submission was received. Per Claude Code's handoff the free plan allows 50 signups a month and keeps submissions for 30 days, so TJ must export regularly and move to a mailing-list tool before launch.
2. **Repo and address.** **Done:** public repo `TejveerD/Palpera`, served at `https://tejveerd.github.io/Palpera/`. A custom domain can be pointed at the same repo later, so every asset and link path stays relative (no leading `/`).
3. **Contact email.** **Decided:** keep a visible placeholder, `[YOUR CONTACT EMAIL]`, in the footer until TJ supplies one. Do not invent an address.
4. **Photo slots.** **Decided:** dropped. No photo section until real hardware photos exist.

Open, waiting on TJ:

5. **Resized-window check.** TJ has confirmed the scroll works full screen. The fixes for non-maximised windows are pushed but he has not yet confirmed them on his laptop.
6. **Input border contrast.** `#B5AFCB` is 1.99 to 1 against the page; the guideline for input edges is 3 to 1. It is a palette colour, so darkening it is TJ's call.
7. **Repo size.** History is about 550 MB because of `concept-renders`. It does not affect the site but makes cloning slow. Removing it from history needs TJ's go-ahead, because it means a force push.

## 9. Not in scope

- The iPhone app, firmware and the printable enclosure.
- The F3 browline frame. It is a later product and appears only as one sentence in "Where we are".
