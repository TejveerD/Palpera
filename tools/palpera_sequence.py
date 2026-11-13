"""
Palpera: `sequence` and `colours` shots.

Adds two shots to the scene that palpera_pod.py builds:

  sequence   One continuous animation (default 150 frames): the five-pod
             stack, the four other pods merge behind the violet pod, the
             glasses come into view, the violet pod travels to the temple and
             clips on, and the camera settles on exactly Cam_Hero.
             Also renders `hero_stack.png`, the stack framed centred, for the
             phone / reduced-motion hero.
  colours    Five stills at Cam_Hero, one per pod colour, same lighting.

Output (under PALPERA_OUT, default ./renders):
  sequence/frame_0001.png ... frame_0150.png
  sequence/hero_stack.png
  colours/violet.png red.png graphite.png silver.png sand.png

Then convert for the web with tools/frames_to_webp.py.

HOW TO WIRE IT INTO palpera_pod.py
----------------------------------
This file only adds the two shots. The scene (glasses, pods, lights, cameras,
render quality) still comes from palpera_pod.py. After palpera_pod.py has
built the scene, and with the violet pod in its hero position on the temple
(the pose Cam_Hero frames), call:

    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import palpera_sequence
    palpera_sequence.run(shots, out_dir)      # shots: list of shot names

e.g. inside the shot loop:   if shot in ("sequence", "colours"): ...

Or, without editing palpera_pod.py, chain it as a second script:

    blender -b -P tools\\palpera_pod.py -P tools\\palpera_sequence.py

In that case it reads PALPERA_SHOTS and renders only `sequence` / `colours`
from it (palpera_pod.py must tolerate those names, or set PALPERA_SEQ_SHOTS
for this file and leave PALPERA_SHOTS for palpera_pod.py).

The object names below are a guess at palpera_pod.py's naming. If a name is
wrong the script stops and lists the objects it can see. Edit CONFIG to match.

1 Blender unit = 1 cm.

Rules kept from palpera_pod.py:
  * Never change object visibility while looping over collection.all_objects
    (crashes Blender). Pods that must vanish are scaled to near zero while
    hidden behind the violet pod; nothing is hidden per object, and the only
    visibility change is un-excluding whole collections.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

CONFIG = {
    # Camera whose framing the sequence ends on, and the carousel uses.
    "end_camera": "Cam_Hero",

    # Root object of each pod (the parent that moves the whole pod). Order
    # matters: first is the signature colour, in front of the stack and the
    # one that clips on. Names are matched case-insensitively; if a name is
    # missing, the script looks for a parentless object whose name contains
    # both "pod" and the colour.
    "pods": [
        ("violet", "Pod_Violet"),
        ("red", "Pod_Red"),
        ("graphite", "Pod_Graphite"),
        ("silver", "Pod_Silver"),
        ("sand", "Pod_Sand"),
    ],

    # Optional empty marking where the pod sits on the temple. If absent, the
    # violet pod's current pose is taken as the clipped-on pose.
    "attach_target": "Pod_Attach",

    # Collections that must be visible for these shots (pods, glasses).
    # Whole collections only. Missing names are ignored.
    "show_collections": ["Glasses", "Pods", "Pods_Concept",
                         "Pod_Violet", "Pod_Red", "Pod_Graphite",
                         "Pod_Silver", "Pod_Sand"],
    # Collections that must be hidden (e.g. the prototype box).
    "hide_collections": ["Prototype"],

    # Pod local axes (palpera_pod.py: 4.2 long, 1.15 tall, 0.62 thick).
    # Which local axis runs along the pod's length, which is "up", and which
    # side faces the camera in the stack. Used only for the stack pose.
    "pod_length_axis": "X",
    "pod_up_axis": "Z",
    "pod_face_axis": "-Y",      # this side faces the camera in the stack
    "stack_yaw_deg": -30.0,     # turn each pod a little for a 3/4 look

    # Stack layout, in cm, in the camera's frame (right, up, depth).
    "stack_spacing_right": 2.9,
    "stack_spacing_up": 0.95,
    "stack_spacing_depth": 3.2,
    # Where the stack sits relative to the clipped-on pod, along the end
    # camera's right axis. Far enough that the glasses start out of frame.
    "stack_lateral_cm": 42.0,
    # Share of frame width the stack fills at the start, and where its centre
    # sits (0 = middle, 0.5 = right edge). Right of centre leaves room for
    # the hero text on the left of the page.
    "stack_fill": 0.5,
    "stack_frame_x": 0.2,
    # Stack size in the centred phone still (share of frame width).
    "hero_stack_fill": 0.72,

    # Clip-on approach: the pod arrives this far outside its final pose,
    # along the line from the glasses' centre to the attach point, then slides
    # on. In cm.
    "clip_approach_cm": 2.6,
    "travel_arc_cm": 3.0,
    # Mid-sequence camera: Cam_Hero pulled back by this factor so the whole
    # pair of glasses is in view while the pod travels.
    "mid_pullback": 0.75,
    # Object to aim the clip approach away from (centre of the glasses).
    "glasses_root": "Glasses",

    # Timeline (frame numbers, 1-based, inclusive end).
    "frames": 150,
    "hold_start": 10,        # stack holds still until here
    "merge_end": 50,         # other pods are behind violet by here
    "vanish": (44, 54),      # other pods shrink away (while hidden)
    "travel": (48, 104),     # violet travels to the approach point
    "clip": (104, 116),      # violet slides onto the temple
    "camera_mid": (46, 108), # camera: stack framing -> pulled-back view
    "camera_end": (108, 142),# camera: pulled-back view -> Cam_Hero exactly

    # Render size for both shots (the page expects 16:9, about 1600 px).
    "resolution": (1600, 900),
    "disable_motion_blur": True,
}

PARK = Vector((0.0, 0.0, -1000.0))   # where unused pods wait in `colours`
TINY = 0.001


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------

def _scene_names():
    return sorted(o.name for o in bpy.data.objects)


def _find(name, required=True):
    obj = bpy.data.objects.get(name)
    if obj is None:
        low = name.lower()
        for o in bpy.data.objects:
            if o.name.lower() == low:
                obj = o
                break
    if obj is None and required:
        raise RuntimeError(
            "palpera_sequence: object '%s' not found. Objects in the scene:\n  %s\n"
            "Edit CONFIG in tools/palpera_sequence.py to match."
            % (name, "\n  ".join(_scene_names())))
    return obj


def _find_pod(colour, name):
    obj = _find(name, required=False)
    if obj is not None:
        return obj
    hits = [o for o in bpy.data.objects
            if o.parent is None and "pod" in o.name.lower() and colour in o.name.lower()
            and "proto" not in o.name.lower()]
    if len(hits) == 1:
        return hits[0]
    raise RuntimeError(
        "palpera_sequence: no pod root for '%s' (tried '%s'; %d name matches). "
        "Objects in the scene:\n  %s" % (colour, name, len(hits), "\n  ".join(_scene_names())))


def _set_collections():
    """Show / hide whole collections in the active view layer."""
    def walk(lc):
        yield lc
        for child in lc.children:
            yield from walk(child)

    layers = list(walk(bpy.context.view_layer.layer_collection))
    show = {n.lower() for n in CONFIG["show_collections"]}
    hide = {n.lower() for n in CONFIG["hide_collections"]}
    for lc in layers:
        n = lc.collection.name.lower()
        if n in show:
            lc.exclude = False
            lc.hide_viewport = False
            lc.collection.hide_render = False
        elif n in hide:
            lc.collection.hide_render = True
    # Parents of shown collections must be included too.
    for lc in layers:
        if lc.collection.name.lower() in show:
            for parent in layers:
                if lc in list(parent.children):
                    parent.exclude = False


# --------------------------------------------------------------------------
# Maths helpers
# --------------------------------------------------------------------------

def _axis(spec):
    sign = -1.0 if spec.startswith("-") else 1.0
    return Vector({"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[spec.strip("+-").upper()]) * sign


def _smooth(t):
    """Ease in and out (smootherstep), clamped."""
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def _phase(frame, span):
    a, b = span
    return _smooth((frame - a) / float(b - a))


def _compose(loc, rot, scale=1.0):
    return Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ Matrix.Diagonal((scale, scale, scale, 1.0))


def _slerp(q0, q1, t):
    if q0.dot(q1) < 0:
        q1 = -q1
    return q0.slerp(q1, t)


# --------------------------------------------------------------------------
# Scene state
# --------------------------------------------------------------------------

class State:
    def __init__(self):
        scene = bpy.context.scene
        self.scene = scene
        self.cam_end = _find(CONFIG["end_camera"])
        self.pods = [(c, _find_pod(c, n)) for c, n in CONFIG["pods"]]
        self.violet = self.pods[0][1]

        bpy.context.view_layer.update()
        target = _find(CONFIG["attach_target"], required=False)
        self.attach = (target or self.violet).matrix_world.copy()
        # Keep pods at their own scale (attach empties are often scale 1).
        self.pod_scale = self.violet.matrix_world.to_scale()
        loc, rot, _ = self.attach.decompose()
        self.attach_loc, self.attach_rot = loc, rot

        self.original = {pod.name: pod.matrix_world.copy() for _, pod in self.pods}

        cam = self.cam_end.matrix_world
        self.cam_end_mw = cam.copy()
        self.cam_loc, self.cam_rot, _ = cam.decompose()
        r = self.cam_rot.to_matrix()
        self.right = r.col[0].normalized()
        self.up = r.col[1].normalized()
        self.back = r.col[2].normalized()          # camera looks along -back

    def pod_matrix(self, loc, rot, scale=1.0):
        s = self.pod_scale * scale
        return Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ Matrix.Diagonal((s.x, s.y, s.z, 1.0))


def _frame_width_at(cam_obj, distance):
    data = cam_obj.data
    scene = bpy.context.scene
    aspect = scene.render.resolution_x / float(scene.render.resolution_y)
    sensor = data.sensor_width
    if data.sensor_fit == "VERTICAL":
        sensor = data.sensor_height * aspect
    elif data.sensor_fit == "AUTO" and aspect < 1:
        sensor = data.sensor_width * aspect
    return distance * sensor / data.lens


# --------------------------------------------------------------------------
# Shots
# --------------------------------------------------------------------------

def _render_settings():
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = CONFIG["resolution"]
    # PALPERA_SEQ_SCALE: render at a percentage for quick tests (default 100).
    scene.render.resolution_percentage = int(os.environ.get("PALPERA_SEQ_SCALE", "100"))
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if scene.render.film_transparent else "RGB"
    scene.render.image_settings.color_depth = "8"
    if CONFIG["disable_motion_blur"]:
        scene.render.use_motion_blur = False
    if scene.render.engine == "CYCLES":
        # Same noise pattern every frame, so the held frames do not shimmer
        # and the last frame matches the violet still.
        scene.cycles.use_animated_seed = False


def _clear_anim(objs):
    for o in objs:
        if o.animation_data:
            o.animation_data_clear()


def _render_still(path):
    scene = bpy.context.scene
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("palpera_sequence: wrote", path)


def shot_colours(out_dir):
    st = State()
    _set_collections()
    _render_settings()
    pods = [p for _, p in st.pods]
    _clear_anim(pods)
    scene = st.scene
    scene.camera = st.cam_end
    folder = os.path.join(out_dir, "colours")
    os.makedirs(folder, exist_ok=True)
    for colour, pod in st.pods:
        for other in pods:
            other.matrix_world = Matrix.Translation(PARK) @ Matrix.Diagonal((TINY, TINY, TINY, 1.0))
        pod.matrix_world = st.pod_matrix(st.attach_loc, st.attach_rot)
        bpy.context.view_layer.update()
        _render_still(os.path.join(folder, colour + ".png"))
    # Put everything back as palpera_pod.py left it.
    for _, pod in st.pods:
        pod.matrix_world = st.original[pod.name]


def _build_sequence(st):
    cfg = CONFIG
    scene = st.scene
    n = cfg["frames"]

    # --- Camera for the sequence: a copy of Cam_Hero (same lens, sensor,
    # shift, depth of field), keyed per frame.
    cam = bpy.data.objects.get("Cam_Sequence")
    if cam is None:
        cam = bpy.data.objects.new("Cam_Sequence", st.cam_end.data.copy())
        for coll in st.cam_end.users_collection:
            coll.objects.link(cam)
    else:
        cam.data = st.cam_end.data.copy()
    cam.parent = None
    cam.rotation_mode = "QUATERNION"

    # --- Stack pose. Centre S sits to the end camera's right, so the glasses
    # start out of frame and come in as the camera travels back.
    S = st.attach_loc + st.right * cfg["stack_lateral_cm"]
    stack_width = 4.2 + 4 * cfg["stack_spacing_right"]
    dist = stack_width / (cfg["stack_fill"] * _frame_width_at(st.cam_end, 1.0))
    frame_w = _frame_width_at(st.cam_end, dist)
    cam_start = S + st.back * dist - st.right * (cfg["stack_frame_x"] * frame_w)

    # Pod orientation in the stack: length along camera right, up along
    # camera up, face toward the camera, then a small yaw.
    L, U, F = _axis(cfg["pod_length_axis"]), _axis(cfg["pod_up_axis"]), _axis(cfg["pod_face_axis"])
    local = Matrix((L, U, F)).transposed()           # columns: pod axes
    world = Matrix((st.right, st.up, st.back)).transposed()
    align = (world @ local.inverted()).to_quaternion()
    yaw = Quaternion(st.up, math.radians(cfg["stack_yaw_deg"]))
    stack_rot = yaw @ align

    # Slots: violet front centre; then right, left, far right, far left,
    # each further back and a touch higher.
    slots = [0, 1, -1, 2, -2]
    stack_pos = []
    for k in slots:
        a = abs(k)
        stack_pos.append(S + st.right * (k * cfg["stack_spacing_right"])
                         + st.up * (a * cfg["stack_spacing_up"])
                         - st.back * (a * cfg["stack_spacing_depth"]))

    # Merge: each other pod slides to a point straight behind the violet pod
    # on the camera's line of sight, so it is hidden as it arrives.
    view_dir = (S - cam_start).normalized()
    behind = [S + view_dir * (1.2 + 0.6 * i) for i in range(5)]

    # Clip-on approach point: outward from the glasses' centre.
    groot = _find(cfg["glasses_root"], required=False)
    centre = groot.matrix_world.translation if groot else st.attach_loc - st.right * 7.0
    outward = st.attach_loc - centre
    outward -= st.up * outward.dot(st.up)    # keep it horizontal-ish
    outward = outward.normalized() if outward.length > 1e-6 else st.right
    approach = st.attach_loc + outward * cfg["clip_approach_cm"]

    cam_mid = st.cam_loc + (st.cam_loc - st.attach_loc) * cfg["mid_pullback"]

    for _, pod in st.pods:
        pod.rotation_mode = "QUATERNION"

    def pose_at(f):
        """World matrices for frame f: (camera, [pods])."""
        # Camera
        t1 = _phase(f, cfg["camera_mid"])
        t2 = _phase(f, cfg["camera_end"])
        c = cam_start.lerp(cam_mid, t1).lerp(st.cam_loc, t2)
        cam_m = Matrix.Translation(c) @ st.cam_rot.to_matrix().to_4x4()
        if f >= cfg["camera_end"][1]:
            cam_m = st.cam_end_mw.copy()     # exact, no float drift

        # Violet
        tt = _phase(f, cfg["travel"])
        tc = _phase(f, cfg["clip"])
        p = stack_pos[0].lerp(approach, tt) + st.up * (math.sin(math.pi * tt) * cfg["travel_arc_cm"])
        p = p.lerp(st.attach_loc, tc)
        q = _slerp(stack_rot, st.attach_rot, tt)
        violet_m = st.pod_matrix(p, q)
        if f >= cfg["clip"][1]:
            violet_m = st.pod_matrix(st.attach_loc, st.attach_rot)

        mats = [violet_m]
        tm = _phase(f, (cfg["hold_start"], cfg["merge_end"]))
        tv = _phase(f, cfg["vanish"])
        for i in range(1, 5):
            # Staggered start so they fold in one after another.
            lag = (i - 1) * 0.06
            ti = _smooth((tm - lag) / (1.0 - 0.18)) if tm > lag else 0.0
            pos = stack_pos[i].lerp(behind[i], ti)
            mats.append(st.pod_matrix(pos, stack_rot, 1.0 - (1.0 - TINY) * tv))
        return cam_m, mats

    pods = [p for _, p in st.pods]
    _clear_anim(pods + [cam])
    for f in range(1, n + 1):
        cam_m, mats = pose_at(f)
        cam.matrix_world = cam_m
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        for pod, m in zip(pods, mats):
            pod.matrix_world = m
            pod.keyframe_insert("location", frame=f)
            pod.keyframe_insert("rotation_quaternion", frame=f)
            pod.keyframe_insert("scale", frame=f)

    # Keys every frame: interpolation between them does not matter, but make
    # it linear so nothing overshoots.
    for o in pods + [cam]:
        action = o.animation_data.action if o.animation_data else None
        for fc in _fcurves(action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

    scene.frame_start, scene.frame_end = 1, n
    scene.camera = cam
    return cam, stack_pos, dist


def _fcurves(action):
    """F-curves of an action, for both the classic and the layered (4.4+) action API."""
    if action is None:
        return []
    curves = list(getattr(action, "fcurves", []) or [])
    if curves:
        return curves
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                curves.extend(bag.fcurves)
    return curves


def shot_sequence(out_dir):
    st = State()
    _set_collections()
    _render_settings()
    cam, stack_pos, dist = _build_sequence(st)
    scene = st.scene
    folder = os.path.join(out_dir, "sequence")
    os.makedirs(folder, exist_ok=True)

    scene.render.filepath = os.path.join(folder, "frame_")   # -> frame_0001.png
    bpy.ops.render.render(animation=True)
    print("palpera_sequence: wrote %d frames to %s" % (CONFIG["frames"], folder))

    # Centred still of the stack for the phone / reduced-motion hero.
    scene.frame_set(1)
    S = stack_pos[0]
    centred = Matrix.Translation(S + st.back * dist * (CONFIG["stack_fill"] / CONFIG["hero_stack_fill"])) @ st.cam_rot.to_matrix().to_4x4()
    if cam.animation_data:
        cam.animation_data.action = None
    cam.matrix_world = centred
    bpy.context.view_layer.update()
    _render_still(os.path.join(folder, "hero_stack.png"))


SHOTS = {"colours": shot_colours, "sequence": shot_sequence}


def run(shots=None, out_dir=None):
    out_dir = os.path.abspath(out_dir or os.environ.get("PALPERA_OUT", "renders"))
    if shots is None:
        raw = os.environ.get("PALPERA_SEQ_SHOTS") or os.environ.get("PALPERA_SHOTS") or "colours,sequence"
        shots = [s.strip() for s in raw.split(",") if s.strip()]
    # colours first: sequence leaves keyframes on the pods.
    for name in ("colours", "sequence"):
        if name in shots:
            SHOTS[name](out_dir)


if __name__ == "__main__":
    # Run as a second -P after palpera_pod.py.
    run()
