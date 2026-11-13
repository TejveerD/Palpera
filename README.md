# Palpera coming-soon page

One page, plain HTML, CSS and JavaScript, with no framework and no build step. GitHub Pages serves the repo as it is.

```
index.html
css/site.css
js/sequence.js        scroll sequence (canvas, desktop only)
js/carousel.js        colour carousel
js/signup.js          Formspree signup (FORMSPREE_ENDPOINT lives here)
assets/hero/          stack.webp: hero stack still (phones, reduced motion)
assets/sequence/      frame_0001.webp ... frame_0150.webp
assets/colours/       violet / red / graphite / silver / sand .webp
tools/palpera_sequence.py   Blender: `sequence` and `colours` shots
tools/frames_to_webp.py     PNG renders -> WebP assets
tools/standin_scene.py      crude stand-in scene, for testing only
```

## Before launch: do not ship until all of these are done

1. **Real renders.** The images in `assets/` are stand-in renders from `tools/standin_scene.py`. Each one is stamped "STAND-IN, NOT A CONCEPT RENDER". Re-render with `palpera_pod.py` (see below) and convert them without `--watermark`.
2. **Formspree endpoint.** Put the form URL in `FORMSPREE_ENDPOINT` at the top of `js/signup.js`. Until then the form says "Signup is not connected yet."
3. **Contact email.** Replace `[YOUR CONTACT EMAIL]` in the footer of `index.html`, ideally as a `mailto:` link.

Formspree's free plan (checked November 2026): 50 submissions a month, and submission history is kept for **30 days only**. Export the list from the Formspree dashboard regularly so no address is lost. Before the launch email, move the list into a mailing-list tool.

## Rendering the sequence and colour stills

`palpera_sequence.py` adds two shots on top of the scene that `palpera_pod.py` builds. Put both files in `tools/`. Then add one call to `palpera_pod.py` after the scene is built, with the violet pod on the temple in its Cam_Hero pose:

```python
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import palpera_sequence
palpera_sequence.run(["colours", "sequence"], out_dir)
```

The object names `palpera_sequence.py` expects are listed in `CONFIG` at the top of that file: `Cam_Hero`, `Pod_Violet`, `Pod_Red`, `Pod_Graphite`, `Pod_Silver`, `Pod_Sand`, `Glasses`, and optionally `Pod_Attach`. They are guesses. If one is wrong, the script stops and prints every object name in the scene, so you can fix `CONFIG`. Also check the pod axis settings (`pod_length_axis` and the others) against the first frame.

Run it headless (Windows):

```
set PALPERA_OUT=C:\palpera\renders
set PALPERA_QUALITY=final
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b -P tools\palpera_pod.py
```

For a quick check of the motion, add `set PALPERA_SEQ_SCALE=25` to render at a quarter size.

Then convert:

```
python tools\frames_to_webp.py C:\palpera\renders
```

This writes `assets/sequence/`, `assets/hero/stack.webp` and `assets/colours/`. The violet carousel still is copied from the last sequence frame, so the handover from the sequence to the carousel is identical by construction. The script also compares that frame with the separately rendered violet still and warns if they differ, which would mean the other four colour stills do not match either. It prints the total size; the budget is under 10 MB for the sequence.

If the frame count changes, update `data-frames` on the `.sequence` section in `index.html`.

## How the page behaves

- **Desktop (900 px or wider, no reduced-motion setting):** the hero text sits over a full-screen canvas. Scrolling plays the 150 frames: the stack merges, the glasses come in, the pod clips on and the camera settles. The page then holds on the last frame while the colour carousel takes over the same stage. The scroll length is `--seq-length` in `css/site.css` (420vh); tune it by feel. Frame 1 loads immediately. The rest load after the page has finished loading, coarse to fine, so early scrolling already shows motion.
- **Phones and reduced motion:** a static hero still, then the carousel. No frame file is ever requested.
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
