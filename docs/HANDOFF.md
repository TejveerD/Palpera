# Palpera: handoff (14 November 2026)

Repo TejveerD/Palpera (public). Live site: https://tejveerd.github.io/Palpera/
Staging copy: https://tejveerd.github.io/Palpera/preview/ (noindex).

## State

The fluted-glass redesign is LIVE at the root (TJ approved 14 November 2026).
`preview/` is an identical staging copy, except that it has noindex. Build and check
every change there first. Push to `main` only when TJ says so, every time.

- Branches: `main` (what Pages serves) and `fluted-wip` (working branch; same
  files as main right now). Develop on fluted-wip, then bring the same tree to main.
- History was rewritten twice on 14 November (TJ approved): the frame folders of
  `concept-renders/` and every upload ever dropped at the repo root were stripped.
  The repo is about 65 MB. Only `index.html`, `README.md`, `.gitignore` and
  `.nojekyll` may sit at the root, apart from folders.
- Specs: TJ's "palpera-fluted-redesign.md" and "palpera-legal-pages.md" (he
  re-pastes them). `docs/BRIEF.md` section 1 rules still apply: wellness product
  (never say detects, diagnoses, prevents or treats), no invented numbers,
  "Concept render" label, never claim to be first, empty values read "Coming soon".

## What is on the page

- Stage: 450 frames (`assets/sequence/frame_0001-0450.webp`, 1600x900, WebP q90,
  22.6 MB). The camera moves from glasses behind fluted glass to a pod close-up.
  Frames load coarse to fine in the background. Phones (<900 px) and reduced
  motion never request frames: they get `assets/stills/s1.webp`, the text, the
  carousel and a callout list.
- Hero (js/hero.js): on the first screen "Palpera" is as wide as the text column
  (TJ's annotated photo), then shrinks to 24 px at the top centre during the move.
  Below it: headline "Your Glasses, Made Aware." and the paragraph "A pod for the
  glasses you already wear. It uses an infrared sensor, with no camera anywhere in
  it.", then the signup. These fade out over the first quarter of the move. The top
  links ("How it works", "Specs", "Who we are" (only when data/team.json has
  people), and "Notify me", which TJ asked for) fade in over the last third. The
  links stay keyboard-focusable throughout.
- Statement on the held last frame: "It follows your blinking.<br> It never sees
  you." (TJ chose "blinking" over "eyes").
- Five callouts (js/callouts.js, data/specs.json, data/anchors.json): Sensor
  (diagonal down-left into the lens), Fit (diagonal up-left; TJ asked to move it
  left), Weight (up), Water resistance (down), Battery life (down, ends higher).
  The approved detail sentences stay on Sensor and Fit. Up labels keep clear of the
  header boxes only where they sit under them. Frames wider than 16:9 crop 25%
  from the top and 75% from the bottom.
- Colours carousel: white (a byte copy of the last frame, so the handover is
  pixel-identical), sand on warm brown, graphite on smoke grey, silver (metallic)
  on clear. These pairs are TJ-approved. The stills are TJ's GPU renders.
- Legal: privacy, terms, cookies and refund pages, effective 14 November 2026.
  Operator: Tejveer Dhakne. Contact: palperapod@gmail.com (a business address comes
  later; replace it in every footer and in privacy and terms). The terms' "which
  courts" line was removed until a lawyer confirms. The consent checkbox at both
  signups sends `email`, `consent=yes`, `policy_version=2026-11-14` and
  `_gotcha`, nothing else. Formspree endpoint: `js/signup.js`. Cookie gate
  (`js/consent.js`) is dormant while `data/site.json` has `"nonEssential": false`.
- Fonts: Bricolage Grotesque 400/500, self-hosted in `fonts/`. Nothing loads from
  any other host. Tokens are in `css/site.css` (ink #12302A, muted #24443C,
  border #4E6F66, light #F4F7F5, card #FBFCFB, hairline #D5DED9).
- Cache-busting: every frame, still, CSS and JS URL ends in `?v=20261114`.
  Returning browsers once mixed old violet frames into the scroll because file
  names were reused. Bump the version whenever frames or stills change.

## Engine rules that must hold

- One smoothed scroll value drives everything. Phases are budgeted in VH in
  js/sequence.js: frames 275, statement 90, 38 per callout, hold 45, fade 30,
  carousel 45.
- Scroll-driven changes animate only transform, opacity and stroke-dashoffset.
  Measure on resize only (layout() functions); per-frame code is arithmetic.
- Chrome layout traps to keep out: scaling SVG elements, toggling a class or
  pointer-events mid-scroll, changing opacity from exactly 0 (floor at 0.001),
  switching an element between no transform and a transform.
- Neighbour-frame blending only while scrolling slowly, and a whole frame at rest.
  Ghosting in the glass mid-move is faint at 450 frames; TJ said it looks amazing.
- Layout order on geometry change: hero first, then callouts.

## Measured (14 November, headless Chromium)

0 layout passes in slow and fast scrubs at 1280x720, 1440x900, 1920x1080 and
2560x1080 (one stray pass seen once at 1920, probably lazy carousel images).
Ring-to-anchor distance under 0.07 px. Brand-to-link gap at least 185 px. Only the
site's own host is contacted; Formspree is contacted only on submit. No cookies and
no storage. Contrast: every text pairing passes AA, the lowest 5.49 (muted on frame
1's darkest edge). Headless Chromium draws on the CPU, so its frame drops are not
conclusive; TJ checks smoothness on his laptop (Windows, RTX 5080).

## Rendering (TJ's laptop)

- TJ has no git. Give him `curl -L -o tools\<file> https://raw.githubusercontent.com/TejveerD/Palpera/fluted-wip/tools/<file>`
  commands, one command per code block.
- `tools/palpera_fluted.py` (EXP=fl_site), with these switches: EXP_DEVICE=GPU
  (OptiX), EXP_FRAME=green|brown|smoke|clear, EXP_ROD_SINK=3 (removes the dark
  rings at the rod bases), EXP_FRAMES ranges, EXP_FORMAT=JPEG, and resume (skips
  files already on disk). Never set EXP_SEQ to an empty string: it crashes.
- `tools/render_fluted_full.ps1` renders 450 frames plus three stills, about 6 to
  8 s a frame on the GPU, about 1 hour in all. The masters stay on his laptop in
  `renders\fl_full` and are not kept in the repo.
- Uploads: GitHub web upload, up to 100 files a batch. Ask him to upload to a
  throwaway branch (`renders`). Same-named files in different folders overwrite
  each other (key_100.jpg happened once), so rename them first. Copy the files
  out, run `tools/fluted_to_site.py <dir> --stills <dir> --site preview --quality 90`,
  check, then delete the branch.
- Blender for checks in a cloud session: `pip install bpy==5.0.1` in a Python 3.11
  venv (blender.org downloads are blocked). Run the script through runpy.

## Open with TJ

1. Business email, which will replace palperapod@gmail.com.
2. Lawyer review before any pre-order or payment: the courts line in the terms,
   and the privacy sentence "By signing up you understand that it leaves your own
   country", which is not a valid EU/UK transfer basis.
3. Names for "Who we are" (data/team.json; the section is hidden while empty).
4. The logo (he is designing it). The sensor disc is blank on purpose; the word
   "Palpera" is used where a logo would go.
5. Possible tweaks he may raise: how fast the name shrinks (now over the whole
   move); the headline coming close to the sensor arm at 2560x1080.
6. TJ wants no Formspree export reminder (the free plan keeps signups for 30 days).
