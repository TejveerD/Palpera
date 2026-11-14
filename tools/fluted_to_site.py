"""
Turn palpera_fluted.py renders into the files the fluted preview loads.

    python tools/fluted_to_site.py SEQ_DIR [--stills STILLS_DIR] [--site preview]
                                   [--quality 90] [--width 0]

SEQ_DIR holds seq/frame_0001.png (or .jpg) ... from an EXP_SEQ run (EXP=fl_site).
STILLS_DIR holds one folder per colour from EXP_T=1 runs, e.g.
    sand/key_100.png  graphite/key_100.png  silver/key_100.png
and an anchors.json from any of them (they share the close-up pose).

Writes into the site folder (default preview/):
    assets/sequence/frame_NNNN.webp   every frame, and data-frames in index.html
    assets/stills/s1.webp             frame 1 (the phone and reduced-motion still)
    assets/colours/white.webp         a byte copy of the last frame, so the
                                      handover to the carousel is pixel identical
    assets/colours/<colour>.webp      the other colour stills
    data/anchors.json                 converted from the script's {"key": [x, y]}
                                      to {"anchors": {"key": {"x", "y"}}}

--width 0 keeps the render width. Prints sizes, the frame-edge colours (the
page ground should match them) and the sequence's total weight.
"""
import argparse, glob, json, os, re, shutil, sys
from PIL import Image


def edge_colour(im):
    small = im.convert("RGB").resize((64, 36), Image.BILINEAR)
    px = [small.getpixel((x, y)) for y in (0, 35) for x in range(64)]
    return "#%02X%02X%02X" % tuple(round(sum(p[i] for p in px) / len(px)) for i in range(3))


def save(src, dst, quality, width):
    im = Image.open(src).convert("RGB")
    if width and im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality, method=6)
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("seq")
    ap.add_argument("--stills")
    ap.add_argument("--site", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "preview"))
    ap.add_argument("--quality", type=int, default=90)
    ap.add_argument("--width", type=int, default=0)
    a = ap.parse_args()

    frames = sorted(glob.glob(os.path.join(a.seq, "seq", "frame_*.png")) +
                    glob.glob(os.path.join(a.seq, "seq", "frame_*.jpg")))
    nums = [int(re.search(r"(\d+)\.(png|jpg)$", f).group(1)) for f in frames]
    if not frames or nums != list(range(1, len(frames) + 1)):
        sys.exit("need seq/frame_0001.png onward with no gaps (found %d files)" % len(frames))

    out = os.path.join(a.site, "assets", "sequence")
    os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "frame_*.webp")):
        os.remove(old)
    total = 0
    for n, f in zip(nums, frames):
        dst = os.path.join(out, "frame_%04d.webp" % n)
        im = save(f, dst, a.quality, a.width)
        total += os.path.getsize(dst)
    count = len(frames)
    print("sequence: %d frames, %dx%d, q%d, %.2f MB (%.0f KB a frame)"
          % (count, im.width, im.height, a.quality, total / 1e6, total / count / 1e3))
    print("frame edges: first %s, last %s" % (edge_colour(Image.open(frames[0])), edge_colour(Image.open(frames[-1]))))

    for sub in ("stills", "colours"):
        os.makedirs(os.path.join(a.site, "assets", sub), exist_ok=True)
    save(frames[0], os.path.join(a.site, "assets", "stills", "s1.webp"), a.quality, a.width)
    shutil.copyfile(os.path.join(out, "frame_%04d.webp" % count),
                    os.path.join(a.site, "assets", "colours", "white.webp"))

    anchors = None
    if a.stills:
        for d in sorted(glob.glob(os.path.join(a.stills, "*"))):
            key = os.path.join(d, "key_100.png")
            if not os.path.isfile(key):
                key = os.path.join(d, "key_100.jpg")
            if os.path.isfile(key):
                name = os.path.basename(d)
                save(key, os.path.join(a.site, "assets", "colours", name + ".webp"), a.quality, a.width)
                print("colour still:", name)
            if anchors is None and os.path.isfile(os.path.join(d, "anchors.json")):
                anchors = os.path.join(d, "anchors.json")
    if anchors is None and os.path.isfile(os.path.join(a.seq, "anchors.json")):
        anchors = os.path.join(a.seq, "anchors.json")
    if anchors:
        raw = json.load(open(anchors))
        conv = {"frame": count, "frame_size": [im.width, im.height],
                "anchors": {k: {"x": v[0], "y": v[1]} for k, v in raw.items()}}
        json.dump(conv, open(os.path.join(a.site, "data", "anchors.json"), "w"), indent=2)
        print("anchors: converted", anchors)
    else:
        print("note: no anchors.json found; data/anchors.json left as it was")

    index = os.path.join(a.site, "index.html")
    html = open(index).read()
    html2 = re.sub(r'data-frames="\d+"', 'data-frames="%d"' % count, html)
    if html2 != html:
        open(index, "w").write(html2)
    print("index.html: data-frames=%d" % count)


if __name__ == "__main__":
    main()
