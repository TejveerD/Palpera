# Palpera website: L2 "Eyelid" redesign

Addendum to `docs/BRIEF.md`, agreed with TJ on 13 November 2026 (late). It restyles the site and replaces the top of the page. Where this file and the brief disagree, this file wins. It supersedes the brief's section 3 (brand), the hero part of section 4, and the look of the callouts in 6.6. Everything else in the brief still applies, including every rule in its section 1.

The design reference is three mock-ups TJ approved: on load, lids open with the bar docked, and callouts.

## 1. What stays exactly as it is

- The 299-frame scroll sequence, the frame blending, the callout behaviour and timing, the expandable detail cards and their approved copy, the colour carousel, `data/specs.json`, `data/anchors.json`, the phone and reduced-motion fallbacks, and the Formspree signup.
- The three Chrome layout traps listed in the last handover must stay removed.
- `tools/palpera_pod.py` in the repo is the only scene script. Ignore any older copy of it supplied earlier in the design session.

## 2. The idea

"Palpera" comes from the Latin for eyelid. The page opens as an eye does: a deep violet page with the name set very large, and the render visible only through a wide slit. Scrolling opens the lids until the render fills the screen. Violet stays on screen the whole time, as the top bar.

## 3. Tokens

Colour:

| Role | Value |
|---|---|
| Violet: lids, bar, closing band | `#2A1F5C` |
| Bone: text and button fill on violet; ring fill | `#F0EDF8` |
| Soft lilac: small text on violet | `#CFC8EC` |
| Input border on violet | `#A79DD6` |
| Ink: text on light surfaces and over the frames | `#1B143D` |
| Muted text on light surfaces | `#575170` |
| Page ground (light sections) | `#F9F8FC` |
| Alternate band | `#F0EDF8` |
| Input border on light surfaces | `#6F6A8A` (replaces `#B5AFCB`, which failed the 3 to 1 guideline) |
| Callout lines, rings and headings | `#2A1F5C` |

- Violet `#2A1F5C` is now the one interactive colour on light surfaces: primary buttons are solid violet with bone text. The brighter `#5A3FC0` is no longer a UI colour; it remains only as the violet pod's colour in the carousel dots.
- No gradients, no blur, no drop shadows on the new elements.

Type:

- Display: **Bodoni Moda**, weight 500, with its optical-size axis left on automatic. Used for the name, all headings, and callout values.
- Everything else: **Hanken Grotesk**, weights 400 and 500 only.
- Cormorant Garamond and Figtree are removed.
- Sizes: body 16 px, secondary 14 px, small print 12 px, nothing smaller. Heading line-height 1.1 to 1.25; body 1.5.

Things to remove across the whole page, because they made it read as a template:

- Italics on part of a headline. "Your glasses, *made aware.*" and "What is in *the pod.*" lose the `<em>`; the wording of the second stays.
- The uppercase "In development" label above the headline. That fact now lives in the small print under the signup.
- Uppercase, letter-spaced labels anywhere. Use sentence case. The "Step one / two / three" labels stay, because the steps are a real sequence, but in sentence case at 14 px.
- Pill shapes. Buttons and inputs have a 2 px corner radius. Remove `--radius-pill`.

## 4. The top of the page (desktop, 900 px and wider, motion allowed)

### 4.1 On load

The existing pinned full-screen stage sits at the back, showing frame 1. In front of it are two violet panels, the lids, leaving a slit:

- Slit: full width, about 41% of the viewport height, starting about 31% down.
- Top lid: from the top of the viewport to the top of the slit. It carries the name, centred, in Bodoni Moda, sized so the word spans roughly 83% of the viewport width. The feet of the letters are just clipped by the top edge of the slit (about 14 px at a 900 px tall window).
- Bottom lid: from the bottom of the slit to the bottom of the viewport. Left: the headline "A pod that clips to the glasses you already wear, and notices when your eyes need rest." at 28 px, weight 400, bone, no wider than 592 px. Right: the signup, with the label "Email address", a field with a 1 px `#A79DD6` border, a bone button "Notify me" with violet text, and beneath it at 12 px in soft lilac: "One email when it is ready. Concept render; the product is in development."
- No navigation links are visible yet.

### 4.2 Opening (new scroll phase, before the frames start)

Add a phase to the `VH` budget ahead of `frames`, about 80 viewport heights; tune by feel. Frame 1 holds during it.

- The top lid slides up until only a 64 px strip is left: the bar.
- The bottom lid slides down until it is off screen. Its text and signup fade out over the first 40% of the phase.
- The name shrinks and travels in one continuous move from its large centred position to the bar's left edge (72 px in), ending at 28 px.
- The bar's links fade in over the last 30% of the phase, after the name has cleared them. The name must never overlap a link at any point of the move, at any tested width.
- Scrolling back up reverses all of it exactly.

Rules for this phase, same as the callouts:

- Drive it from the same smoothed scroll value as the frames. No timers, no snapping.
- Animate only `transform` and `opacity`. The lids move with `translateY`; the name with `translate` and `scale`. Never animate height, top, font-size or padding.
- Measure positions on resize only; scroll handling stays arithmetic.
- Keep the three layout traps out: no scaling of SVG elements, no class toggling mid-scroll, and no changing opacity from exactly 0.

### 4.3 The bar

- 64 px tall, violet, fixed to the top for the whole page (**Decided**: it stays pinned).
- Left: the name, linking to the top. It is the same element that shrank from the hero, in the serif, not capitals.
- Right, 14 px, bone: "How it works", "Where we are", "Who we are", then a bone button "Notify me" (44 px tall, 2 px radius, violet text) that goes to the closing signup. This button matters: once the bottom lid has gone, it is the only route to the signup until the end of the page.
- Give linked sections a top scroll margin of 64 px so the bar does not cover their headings.
- The frame geometry must now treat the area below the bar as the stage: publish `--img-top` and `--img-h` accordingly, so the callouts and carousel keep lining up.

### 4.4 Frames: one re-render

The stack no longer has to leave room for a headline, so it should sit in the middle of the slit.

- In `tools/palpera_pod.py` the opening camera uses `shift_x = -0.22` and `shift_y = 0.04`, fading to 0 along the move. Change the opening to no shift, and choose the opening lens so the row of five pods spans about 55% of the frame width and sits inside the middle 40% of the frame height. In the design session, lens 40 with no shift gave that result on the older, unbaked script; check it on the current one.
- The last frame must not change. Confirm by comparing the new last frame with the current one, and confirm `anchors.json` is unchanged.
- Before the full render, render three frames only (first, middle, last) at low quality and show TJ. Add a way to render selected frames if the script lacks one.
- Then TJ runs the full 299-frame render on his laptop (20 to 25 minutes) and uploads, as in the existing workflow. The phone hero still is re-cropped from the new frame 1.

## 5. Callouts, restyled

Behaviour, timing, positions and copy do not change. Only the look:

- Ring: bone fill, 1.5 px violet stroke. Line: 1.25 px violet.
- Heading: Hanken Grotesk 500, 14 px, violet, sentence case.
- Value: Bodoni Moda 500, 28 px, line-height 1.2, ink.
- Phase heading: "What is in the pod." in Bodoni Moda 500 at 44 px, no italics, with the existing line beneath it at 16 px.
- Detail cards: near-white surface, 1 px violet border at about 12% opacity, 2 px radius, 14 px text.
- Carousel arrows follow the new button style. The colour dots stay round.

## 6. The rest of the page

- Apply the tokens in section 3 to every section: specs, reasons, how it works, where we are, closing band, footer. Section order and copy are unchanged.
- The closing band is violet `#2A1F5C` with bone text, a bone button and a `#A79DD6` input border.
- Spec list heading: use "The details so far" as a visible heading unless TJ picks another.
- **New section, "Who we are"**, placed after "Where we are". TJ has no content for it yet. Build it to read from a small data file (for example `data/team.json`: a name, a role and one line each). While that file is empty, the section and its bar link are not rendered. They appear when TJ adds entries, with no code change. Do not invent names or text.

## 7. Phones and reduced motion

- No lids and no travelling name. The page starts with a violet block holding the name (large, fitted to the width), then the still of the pod stack, the headline and the signup.
- A slim pinned violet bar with the name and the "Notify me" button only. Section links are left out at this size.
- No frame files are requested, as now.

## 8. How to ship it

The first version of this site went live before TJ had seen it. Do not repeat that.

- Build the redesign in a `preview/` folder on `main`, sharing the existing assets through relative paths, with a `noindex` tag. It will be reachable at `https://tejveerd.github.io/Palpera/preview/` while the current site stays untouched at the root.
- TJ reviews the preview on his laptop. Promote it to the root only after he says so, then remove `preview/`.

## 9. Checks to report, with measured results

- Opening phase scrubbed slowly and quickly, forwards and backwards, with the performance recorder: layout passes and dropped frames (target: none), at 1280 × 720, 1440 × 900, 1920 × 1080 and 2560 × 1080.
- The name never overlaps a bar link during its move, at each of those sizes and at 900 px wide.
- Callouts and carousel still line up with the pod now that the bar takes 64 px (ring-to-anchor distance, as measured before).
- Contrast: every text and input-edge pairing in section 3, measured.
- Keyboard path from the top: signup in the bottom lid, bar links, callout buttons, carousel, closing signup.
- Phones and reduced motion: no frame requests; bar and signup usable.
- Page weight after the font change and re-render (budget still 10 MB).
- Anything headless Chromium cannot judge, such as real scrub smoothness, listed plainly for TJ to check himself.

## 10. Still open for TJ

1. Names and one line each for "Who we are".
2. The footer contact email.
3. Whether to strip `concept-renders` from the repo history.
4. Exporting Formspree signups regularly.
