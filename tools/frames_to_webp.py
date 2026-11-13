"""
Convert Blender PNG renders into the WebP files the page loads.

    python tools/frames_to_webp.py RENDERS_DIR [--site .] [--width 1600]
                                   [--quality 95] [--watermark]

RENDERS_DIR is PALPERA_OUT from a palpera_pod.py run with
PALPERA_SHOTS=sequence,colours, containing (WebP by default, PNG also read):
    sequence/frame_0001.webp ...     -> assets/sequence/frame_0001.webp ...
                                        (and data-frames in index.html)
    sequence/hero_stack.png          -> assets/hero/stack.webp (cropped to the pods)
    colours/<colour>.png             -> assets/colours/<colour>.webp
    anchors.json                     -> data/anchors.json (callout positions)

The violet carousel still is written from the LAST sequence frame, so the
handover from the scroll sequence to the carousel is pixel identical by
construction. The separately rendered colours/violet.png is compared with it
and the difference reported, which checks that the other four colour stills
were rendered with the same camera and lighting.

Transparent renders are flattened onto the page ground (#F9F8FC).

--watermark stamps "STAND-IN" across every image. Never use it for renders
from palpera_pod.py.

Needs Pillow (pip install pillow). Prints the total size at the end; the
brief's budget is under 10 MB for the sequence.
"""

import argparse
import glob
import os
import re
import shutil
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

GROUND = (0xF9, 0xF8, 0xFC)
COLOURS = ["violet", "red", "graphite", "silver", "sand"]


def load(path, width):
    im = Image.open(path)
    im.load()
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, GROUND + (255,))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    if width and im.width != width:
        h = round(im.height * width / im.width)
        im = im.resize((width, h), Image.LANCZOS)
    return im


def stamp(im):
    im = im.copy()
    d = ImageDraw.Draw(im)
    size = max(14, im.width // 48)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    text = "STAND-IN, NOT A CONCEPT RENDER"
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
    # Top right, clear of the hero text (left) and carousel controls (bottom).
    x = im.width - (x1 - x0) - size
    y = int(im.height * 0.11)
    d.text((x, y), text, font=font, fill=(200, 50, 43))
    return im


def crop_to_subject(im, margin=0.18):
    """Crop a still to its subject at 16:9, for the phone hero. Frame 1 leaves
    the left half empty for the desktop headline; a phone has no text beside
    the image, so the pods are framed tighter. Subject = pixels that are
    clearly darker or more saturated than the lavender backdrop."""
    small = im.resize((im.width // 4, im.height // 4))
    px = small.load()
    xs, ys = [], []
    for y in range(small.height):
        for x in range(small.width):
            r, g, b = px[x, y]
            if max(r, g, b) - min(r, g, b) > 60 or max(r, g, b) < 140:
                xs.append(x)
                ys.append(y)
    if not xs:
        return im
    x0, x1, y0, y1 = min(xs) * 4, max(xs) * 4 + 4, min(ys) * 4, max(ys) * 4 + 4
    w = (x1 - x0) * (1 + 2 * margin)
    h = (y1 - y0) * (1 + 2 * margin)
    w = max(w, h * 16 / 9, im.width * 0.4)
    h = w * 9 / 16
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left = min(max(cx - w / 2, 0), im.width - w)
    top = min(max(cy - h / 2, 0), im.height - h)
    box = tuple(round(v) for v in (left, top, left + w, top + h))
    return im.crop(box).resize((im.width, im.height), Image.LANCZOS)


def save(im, path, quality, watermark):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if watermark:
        im = stamp(im)
    im.save(path, "WEBP", quality=quality, method=6)
    return os.path.getsize(path)


def find(folder, stem):
    """stem.webp or stem.png (palpera_pod.py writes WebP by default)."""
    for ext in (".webp", ".png"):
        f = os.path.join(folder, stem + ext)
        if os.path.exists(f):
            return f
    return None


def passthrough(src, width, watermark):
    """A WebP already at the right width is copied as it is, so it is not
    compressed a second time."""
    if watermark or not src.lower().endswith(".webp"):
        return False
    with Image.open(src) as im:
        return im.width == width and im.mode == "RGB"


def put(src, im, path, a):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if passthrough(src, a.width, a.watermark):
        shutil.copyfile(src, path)
        return os.path.getsize(path)
    return save(im, path, a.quality, a.watermark)


def set_frame_count(site, n):
    """Keeps index.html's data-frames in step with the files written."""
    page = os.path.join(site, "index.html")
    if not os.path.exists(page):
        return
    with open(page, encoding="utf-8") as fh:
        html = fh.read()
    new = re.sub(r'data-frames="\d+"', 'data-frames="%d"' % n, html, count=1)
    if new != html:
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(new)
        print("index.html: data-frames set to %d" % n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("renders")
    ap.add_argument("--site", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=95)   # lower values band the soft backdrop
    ap.add_argument("--watermark", action="store_true")
    a = ap.parse_args()

    site = os.path.abspath(a.site)
    seq_dir = os.path.join(a.renders, "sequence")
    col_dir = os.path.join(a.renders, "colours")
    frames = sorted(glob.glob(os.path.join(seq_dir, "frame_[0-9]*.webp")))
    if not frames:
        frames = sorted(glob.glob(os.path.join(seq_dir, "frame_[0-9]*.png")))
    total = {"sequence": 0, "colours": 0, "hero": 0}

    last = last_src = None
    if frames:
        out = os.path.join(site, "assets", "sequence")
        for old in glob.glob(os.path.join(out, "frame_*.webp")):
            os.remove(old)
        for i, f in enumerate(frames, 1):
            im = load(f, a.width)
            total["sequence"] += put(f, im, os.path.join(out, "frame_%04d.webp" % i), a)
            last, last_src = im, f
        print("sequence: %d frames, %.2f MB" % (len(frames), total["sequence"] / 1e6))
        set_frame_count(site, len(frames))

    stack = find(seq_dir, "hero_stack")
    if stack:
        total["hero"] += save(crop_to_subject(load(stack, a.width)), os.path.join(site, "assets", "hero", "stack.webp"),
                              a.quality, a.watermark)

    for c in COLOURS:
        src = find(col_dir, c)
        if c == "violet" and last is not None:
            if src:
                diff = ImageChops.difference(load(src, a.width), last)
                mean = sum(ImageStat.Stat(diff).mean) / 3
                peak = max(b[1] for b in diff.getextrema())
                print("violet still vs last sequence frame: mean diff %.2f, max %d (of 255)" % (mean, peak))
                if mean > 2.0:
                    print("  WARNING: large difference. Check that both shots use Cam_Hero, the same "
                          "resolution, lighting and pod pose.")
            im, src = last, last_src
        elif src:
            im = load(src, a.width)
        else:
            print("missing", os.path.join(col_dir, c + ".webp"))
            continue
        total["colours"] += put(src, im, os.path.join(site, "assets", "colours", c + ".webp"), a)

    # Callout positions for this render (written by palpera_pod.py).
    anchors = os.path.join(a.renders, "anchors.json")
    if os.path.exists(anchors):
        os.makedirs(os.path.join(site, "data"), exist_ok=True)
        with open(anchors) as src, open(os.path.join(site, "data", "anchors.json"), "w") as dst:
            dst.write(src.read())
        print("anchors: copied to data/anchors.json")
    elif frames:
        print("note: no anchors.json in the renders; data/anchors.json left as it was")

    print("colours: %.2f MB, hero: %.2f MB" % (total["colours"] / 1e6, total["hero"] / 1e6))
    print("total: %.2f MB" % (sum(total.values()) / 1e6))


if __name__ == "__main__":
    sys.exit(main())
