# Palpera pod: concept render scene for Blender (written for 4.x / 5.x).
# Builds everything from code: round acetate glasses, the slim concept pod in
# five colours, and a true-to-size prototype pod. Renders stills and a
# front-to-side turntable.
#
# Run inside Blender (Scripting tab > Run Script) or headless:
#   Blender -b -P palpera_pod.py
#
# 1 Blender unit = 1 cm.
#
# Settings can be overridden with environment variables:
#   PALPERA_OUT      output folder        (default ~/Palpera/renders)
#   PALPERA_QUALITY  preview | draft | final  (default final)
#   PALPERA_SHOTS    comma list of shots  (default: all of SHOT_ORDER)
#                    extra shots for the website, only when named here:
#                    sequence (150-frame scroll animation), colours (five stills)
#   PALPERA_VIDEO    auto | 1 | 0         (1 = write an .mp4, 0 = numbered frames)
#   PALPERA_WORLD / PALPERA_FLOOR / PALPERA_FRAME   sRGB hex colours for the
#                    studio wall, the floor and the glasses frame
#   PALPERA_COLOURS  comma list limiting which pod colours the colours shot renders
#   PALPERA_SEQ_SCALE  1 | 2 | 3  sequence frame multiplier (2 = 299 frames)

import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

OUT = os.path.expanduser(os.environ.get("PALPERA_OUT", "~/Palpera/renders"))
QUALITY = os.environ.get("PALPERA_QUALITY", "final")
SHOT_ORDER = ["hero", "lineup", "hero_transparent", "closeup", "side",
              "prototype", "turntable"]
SHOTS = [s for s in os.environ.get("PALPERA_SHOTS", ",".join(SHOT_ORDER)).split(",") if s]

# quality: (still size, still samples, turntable size, turntable samples, frame step)
TIERS = {
    "preview": ((600, 400), 12, (480, 270), 8, 12),
    "draft":   ((1200, 800), 40, (640, 360), 16, 2),
    "final":   ((2400, 1600), 192, (1920, 1080), 64, 1),
}
STILL_RES, STILL_SAMPLES, ANIM_RES, ANIM_SAMPLES, ANIM_STEP = TIERS.get(QUALITY, TIERS["final"])
ANIM_FRAMES = 96          # 4 seconds at 24 fps
# website scroll sequence: (frame size, samples, frame step)
SEQ_TIERS = {
    "preview": ((480, 270), 8, 3),
    "draft":   ((1440, 810), 32, 1),
    "final":   ((1600, 900), 96, 1),
}
SEQ_RES, SEQ_SAMPLES, SEQ_STEP = SEQ_TIERS.get(QUALITY, SEQ_TIERS["final"])
SEQ_FRAMES = 150
# Render 2x or 3x as many in-between frames for a smoother scrub, same motion.
SEQ_SCALE = max(1, int(os.environ.get("PALPERA_SEQ_SCALE", "1")))


def seq_f(f):
    return 1 + (f - 1) * SEQ_SCALE


SEQ_LAST = seq_f(SEQ_FRAMES)
# Write a video directly when run inside the Blender app; as a Python module
# (no app binary) write numbered frames instead and encode them separately.
_video = os.environ.get("PALPERA_VIDEO", "auto")     # auto | 1 | 0
ANIM_VIDEO = (_video == "1") or (_video == "auto" and QUALITY != "preview"
                                 and bool(bpy.app.binary_path))

FLOOR_Z = -2.75

COLOURS = {            # brand pod colours (sRGB hex)
    "violet":   "5A3FC0",
    "red":      "C8322B",
    "graphite": "3A3D45",
    "silver":   "C9CCD3",
    "sand":     "D8C7A8",
}
WORLD = os.environ.get("PALPERA_WORLD", "CFC9E0")   # studio wall colour (sRGB hex)
FLOOR = os.environ.get("PALPERA_FLOOR", "F5F5F5")   # floor; near-white picks up the wall colour
FRAME = os.environ.get("PALPERA_FRAME", "141316")   # glasses frame colour


# ----------------------------------------------------------------- helpers

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h):
    h = h.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (1.0,)


def set_input(node, names, value):
    """Set the first socket that exists; names differ between Blender versions."""
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def principled(name, colour, rough=0.4, metallic=0.0, coat=0.0,
               transmission=0.0, ior=1.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    set_input(bsdf, ["Base Color"], colour)
    set_input(bsdf, ["Roughness"], rough)
    set_input(bsdf, ["Metallic"], metallic)
    set_input(bsdf, ["Coat Weight", "Clearcoat"], coat)
    set_input(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.08)
    set_input(bsdf, ["Transmission Weight", "Transmission"], transmission)
    set_input(bsdf, ["IOR"], ior)
    return mat


def emission(name, strength, colour=(1, 1, 1, 1)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = colour
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def add_object(name, data, col, mat=None, loc=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, data)
    col.objects.link(ob)
    ob.location = loc
    if mat is not None and hasattr(data, "materials"):
        data.materials.append(mat)
    if parent is not None:
        ob.parent = parent
    return ob


def smooth(mesh, only_quads=False):
    for p in mesh.polygons:
        p.use_smooth = (len(p.vertices) == 4) if only_quads else True


def rounded_box(name, size, radius, col, mat, loc=(0, 0, 0), parent=None, segments=8):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    radius = min(radius, min(size) / 2 * 0.98)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=radius, segments=segments,
                    profile=0.5, affect="EDGES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me)
    ob = add_object(name, me, col, mat, loc, parent)
    mod = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    mod.keep_sharp = False
    return ob


def ring(name, major, radial_w, depth, col, mat, loc, nu=128, nv=24, power=3.0):
    """Lens rim: a ring in the XZ plane with a soft rounded-rectangle section."""
    verts, faces = [], []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        for j in range(nv):
            b = 2 * math.pi * j / nv
            cb, sb = math.cos(b), math.sin(b)
            # superellipse cross-section
            sx = math.copysign(abs(cb) ** (2 / power), cb) * radial_w / 2
            sy = math.copysign(abs(sb) ** (2 / power), sb) * depth / 2
            r = major + sx
            verts.append((r * math.cos(a), sy, r * math.sin(a)))
    for i in range(nu):
        for j in range(nv):
            a0 = i * nv + j
            a1 = i * nv + (j + 1) % nv
            b0 = ((i + 1) % nu) * nv + j
            b1 = ((i + 1) % nu) * nv + (j + 1) % nv
            faces.append((a0, b0, b1, a1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    smooth(me)
    return add_object(name, me, col, mat, loc)


def disc(name, radius, depth, col, mat, loc):
    """Lens: a thin cylinder whose axis runs front to back (Y)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=128,
                          radius1=radius, radius2=radius, depth=depth)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                     matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me, only_quads=True)
    return add_object(name, me, col, mat, loc)


def tube(name, points, radius, col, mat, extrude=0.0, parent=None, loc=(0, 0, 0)):
    """A smooth rod (or flat strap when extrude > 0) through the given points."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 24
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.extrude = extrude
    cu.use_fill_caps = True
    cu.twist_mode = "Z_UP"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    return add_object(name, cu, col, mat, loc, parent)


def uv_sphere(name, radius, scale, col, mat, loc=(0, 0, 0), parent=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=radius)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me)
    return add_object(name, me, col, mat, loc, parent)


def plane(name, size, col, mat, loc=(0, 0, 0)):
    s = size / 2
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.update()
    return add_object(name, me, col, mat, loc)


def look_at(ob, target):
    direction = Vector(target) - ob.location
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def set_hidden(col, hidden):
    # Hide at collection level. Changing visibility object by object while
    # looping over col.all_objects crashes Blender (the loop is invalidated).
    col.hide_render = hidden
    col.hide_viewport = hidden


# ------------------------------------------------------------- clean slate

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
              bpy.data.cameras, bpy.data.lights):
    for item in list(block):
        if item.users == 0:
            block.remove(item)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)

scene = bpy.context.scene

# ---------------------------------------------------------------- materials

M_ACETATE = principled("Acetate", hex_rgba(FRAME), rough=0.12, coat=0.6)
M_LENS = principled("Lens", (1, 1, 1, 1), rough=0.0, transmission=1.0, ior=1.5)
M_SENSOR = principled("SensorWindow", hex_rgba("1A0B0B"), rough=0.05, coat=1.0)
M_PORT = principled("Port", hex_rgba("0C0C0E"), rough=0.35, metallic=0.6)
M_PLA = principled("PrintedPLA", hex_rgba("B9BBC0"), rough=0.62)
M_FLOOR = principled("Floor", hex_rgba(FLOOR), rough=1.0)
M_CAP = principled("PodCap", hex_rgba("17151C"), rough=0.08, coat=1.0)
M_POD = {}
for cname, chex in COLOURS.items():
    metallic = 0.85 if cname == "silver" else 0.0
    rough = 0.32 if cname == "silver" else 0.38
    M_POD[cname] = principled("Pod_" + cname, hex_rgba(chex), rough=rough,
                              metallic=metallic, coat=0.25)

# ------------------------------------------------------------------ glasses

C_GLASSES = new_collection("Glasses")
LENS_X, LENS_R = 3.3, 2.3
RIM_R, RIM_W, RIM_D = 2.47, 0.46, 0.42
TEMPLE_X, TEMPLE_Z = 6.08, 0.95

for side in (-1, 1):
    tag = "L" if side < 0 else "R"
    ring("Rim_" + tag, RIM_R, RIM_W, RIM_D, C_GLASSES, M_ACETATE, (side * LENS_X, 0, 0))
    disc("Lens_" + tag, LENS_R + 0.06, 0.14, C_GLASSES, M_LENS, (side * LENS_X, 0, 0))
    rounded_box("Lug_" + tag, (0.62, 0.62, 0.66), 0.16, C_GLASSES, M_ACETATE,
                (side * 5.86, 0.12, TEMPLE_Z))
    tube("Temple_" + tag,
         [(side * TEMPLE_X, 0.30, TEMPLE_Z),
          (side * (TEMPLE_X + 0.04), 4.80, TEMPLE_Z),
          (side * (TEMPLE_X + 0.02), 9.40, TEMPLE_Z - 0.05),
          (side * (TEMPLE_X - 0.14), 11.9, -0.75),
          (side * (TEMPLE_X - 0.30), 13.1, -2.35)],
         0.085, C_GLASSES, M_ACETATE, extrude=0.23)
    uv_sphere("NosePad_" + tag, 0.25, (0.5, 0.9, 1.5), C_GLASSES, M_ACETATE,
              (side * 0.98, 0.34, -0.95))

tube("Bridge", [(-1.02, 0, 0.72), (0, -0.04, 1.22), (1.02, 0, 0.72)],
     0.21, C_GLASSES, M_ACETATE)

# One handle for the whole frame, so the glasses can be moved as a unit.
GLASSES_ROOT = bpy.data.objects.new("Glasses", None)
C_GLASSES.objects.link(GLASSES_ROOT)
for _ob in list(C_GLASSES.objects):
    if _ob is not GLASSES_ROOT and _ob.parent is None:
        _ob.parent = GLASSES_ROOT

# ---------------------------------------------------------------------- pods

POD_SIZE = (0.62, 4.2, 1.15)          # thickness, length, height in cm
POD_ON_TEMPLE = (TEMPLE_X + 0.44, 3.05, TEMPLE_Z)


def make_pod(name, mat, col, loc):
    """Slim concept pod. Local origin is the centre of the body."""
    root = bpy.data.objects.new(name, None)
    root.empty_display_size = 0.5
    col.objects.link(root)
    root.location = loc
    rounded_box(name + "_Body", POD_SIZE, 0.30, col, mat, parent=root, segments=10)
    for i, y in enumerate((-1.25, 1.25)):          # clips that grip the temple
        rounded_box("%s_Clip%d" % (name, i), (0.40, 0.46, 0.84), 0.10, col, mat,
                    loc=(-0.46, y, 0), parent=root)
    # dark glossy cap at the front end, where the sensor arm leaves the body
    rounded_box(name + "_Cap", (POD_SIZE[0] + 0.006, 0.62, POD_SIZE[2] + 0.006), 0.30,
                col, M_CAP, loc=(0, -POD_SIZE[1] / 2 + 0.31, 0), parent=root, segments=10)
    # the arm drops under the temple and reaches in behind the lens
    tube(name + "_Arm",
         [(-0.02, -1.80, -0.36), (-0.24, -2.30, -0.74),
          (-0.95, -2.34, -1.04), (-1.78, -2.18, -1.24)],
         0.10, col, mat, parent=root)
    uv_sphere(name + "_Sensor", 0.25, (1.0, 0.7, 1.0), col, M_SENSOR,
              loc=(-1.92, -2.14, -1.26), parent=root)
    return root


def make_prototype_pod(name, col, loc):
    """True-to-size estimate of an enclosure around the XIAO board, IMU and wiring."""
    size = (1.2, 3.0, 2.2)
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    root.location = loc
    rounded_box(name + "_Body", size, 0.14, col, M_PLA, parent=root, segments=5)
    for i, y in enumerate((-0.9, 0.9)):
        rounded_box("%s_Clip%d" % (name, i), (0.44, 0.5, 0.9), 0.08, col, M_PLA,
                    loc=(-0.74, y, 0), parent=root)
    rounded_box(name + "_USBC", (0.34, 0.12, 0.92), 0.05, col, M_PORT,
                loc=(0.05, size[1] / 2, 0), parent=root)
    tube(name + "_Arm",
         [(-0.30, -1.45, -0.95), (-0.50, -1.80, -1.12),
          (-0.95, -1.92, -1.18), (-1.40, -1.86, -1.18)],
         0.12, col, M_PLA, parent=root)
    uv_sphere(name + "_Sensor", 0.24, (1.0, 0.75, 1.0), col, M_SENSOR,
              loc=(-1.52, -1.84, -1.18), parent=root)
    return root


C_POD = new_collection("PodOnGlasses")
POD_ROOT = make_pod("Pod", M_POD["violet"], C_POD, POD_ON_TEMPLE)

C_PROTO = new_collection("PrototypePod")
make_prototype_pod("Proto", C_PROTO, (TEMPLE_X + 0.73, 2.3, TEMPLE_Z))

C_LINEUP = new_collection("ColourLineup")
LINEUP_ORDER = ["violet", "red", "graphite", "silver", "sand"]
LINEUP_ROOTS = {}
LINEUP_POS = {}
for i, cname in enumerate(LINEUP_ORDER):
    LINEUP_POS[cname] = Vector((4.6 - i * 2.4, 1.6 - i * 2.3, FLOOR_Z + 1.75))
    LINEUP_ROOTS[cname] = make_pod("Lineup_" + cname, M_POD[cname], C_LINEUP,
                                   LINEUP_POS[cname])

# ------------------------------------------------------------------- studio

C_STUDIO = new_collection("Studio")
# Seamless backdrop: a white matte floor under an evenly coloured "sky" takes on
# the sky colour, so floor and background meet without a visible horizon.
floor = plane("Floor", 20000, C_STUDIO, M_FLOOR, (0, 0, FLOOR_Z))
catcher = plane("ShadowCatcher", 400, C_STUDIO, M_FLOOR, (0, 0, FLOOR_Z))
catcher.is_shadow_catcher = True


def softbox(name, size, loc, target, strength):
    ob = plane(name, size, C_STUDIO, emission(name + "_mat", strength), loc)
    look_at(ob, target)
    ob.visible_camera = False
    return ob


softbox("Key", 34, (-20, -26, 30), (0, 3, 0), 2.2)
softbox("Fill", 30, (34, -14, 14), (0, 3, 0), 0.9)
softbox("Top", 60, (0, 4, 48), (0, 4, 0), 0.7)
softbox("Rim", 26, (6, 44, 20), (0, 3, 0), 2.0)

world = bpy.data.worlds.new("World")
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg is not None:
    bg.inputs["Color"].default_value = hex_rgba(WORLD)
    bg.inputs["Strength"].default_value = 1.0
scene.world = world

# ------------------------------------------------------------------ cameras

C_CAMS = new_collection("Cameras")


def camera(name, loc, target, lens, parent=None):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.5
    cam.clip_end = 5000
    ob = add_object(name, cam, C_CAMS, loc=loc)
    look_at(ob, target)
    if parent is not None:
        ob.parent = parent
    return ob


POD_CENTRE = Vector(POD_ON_TEMPLE)
CAM_HERO = camera("Cam_Hero", (25, -20, 7.5), (1.6, 3.4, -0.4), 62)
CAM_SIDE = camera("Cam_Side", (46, 4.6, 1.2), (6, 4.6, -0.2), 95)
CAM_CLOSE = camera("Cam_Closeup", (17.5, -10.5, 4.2), (6.0, 2.3, 0.35), 88)
CAM_LINEUP = camera("Cam_Lineup", (29, -17, 11), (0.3, -2.7, FLOOR_Z + 1.2), 54)

TURN_TARGET = (0.4, 3.8, -0.1)
pivot = bpy.data.objects.new("TurntablePivot", None)
C_CAMS.objects.link(pivot)
pivot.location = TURN_TARGET
CAM_TURN = camera("Cam_Turntable", (0, -40, 4.5), (0, 0, 0), 62, parent=pivot)
pivot.rotation_euler = (0, 0, 0)
pivot.keyframe_insert(data_path="rotation_euler", frame=1)
pivot.rotation_euler = (0, 0, math.radians(90))
pivot.keyframe_insert(data_path="rotation_euler", frame=ANIM_FRAMES)

# ------------------------------------------------------------ render set-up

r = scene.render
r.engine = "CYCLES"
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("METAL", "OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            if any(d.type == dev_type for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = "GPU"
                print("Palpera: rendering on GPU via", dev_type)
                break
        except Exception:
            continue
    else:
        scene.cycles.device = "CPU"
        print("Palpera: rendering on CPU")
except Exception as exc:
    print("Palpera: GPU set-up skipped:", exc)

try:
    scene.view_settings.view_transform = "Standard"   # keeps brand colours true
    scene.view_settings.look = "None"
except Exception:
    pass

scene.frame_start = 1
scene.frame_end = ANIM_FRAMES
r.fps = 24
os.makedirs(OUT, exist_ok=True)


def still_settings():
    r.resolution_x, r.resolution_y = STILL_RES
    r.resolution_percentage = 100
    scene.cycles.samples = STILL_SAMPLES
    if hasattr(r.image_settings, "media_type"):
        r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    scene.frame_set(1)


def show(glasses=True, pod=True, proto=False, lineup=False, transparent=False):
    set_hidden(C_GLASSES, not glasses)
    set_hidden(C_POD, not pod)
    set_hidden(C_PROTO, not proto)
    set_hidden(C_LINEUP, not lineup)
    r.film_transparent = transparent
    floor.hide_render = transparent
    catcher.hide_render = not transparent


def render_still(name, cam):
    still_settings()
    scene.camera = cam
    r.filepath = os.path.join(OUT, "palpera_" + name + ".png")
    bpy.ops.render.render(write_still=True)
    print("Palpera: wrote", r.filepath)


def render_turntable():
    show()
    scene.camera = CAM_TURN
    r.resolution_x, r.resolution_y = ANIM_RES
    r.resolution_percentage = 100
    scene.cycles.samples = ANIM_SAMPLES
    scene.frame_step = ANIM_STEP
    r.fps = max(1, 24 // ANIM_STEP)      # keeps the move 4 seconds long
    if ANIM_VIDEO:
        if hasattr(r.image_settings, "media_type"):
            r.image_settings.media_type = "VIDEO"
        r.image_settings.file_format = "FFMPEG"
        r.ffmpeg.format = "MPEG4"
        r.ffmpeg.codec = "H264"
        r.ffmpeg.constant_rate_factor = "HIGH"
        r.filepath = os.path.join(OUT, "palpera_turntable_")
    else:
        r.image_settings.file_format = "PNG"
        os.makedirs(os.path.join(OUT, "turntable_frames"), exist_ok=True)
        r.filepath = os.path.join(OUT, "turntable_frames", "frame_")
    bpy.ops.render.render(animation=True)
    scene.frame_step = 1
    r.fps = 24
    print("Palpera: wrote turntable to", OUT)


# ------------------------------------------------- website scroll sequence
#
# One continuous move for the landing page:
#   1. the five-pod stack, violet in front
#   2. the other four slide in behind the violet pod and vanish
#   3. the glasses are lowered into view while the violet pod lifts clear
#   4. the pod slides onto the temple and the camera settles on the
#      three-quarter view (same framing as Cam_Hero)
# The colour stills are rendered from the last frame of the same camera, so
# the handover from the sequence to the colour carousel cannot jump.

LINEUP_CAM_POS = Vector((29, -17, 11))
LINEUP_CAM_TARGET = Vector((0.3, -2.7, FLOOR_Z + 1.2))
HERO_CAM_POS = Vector((25, -20, 7.5))
HERO_CAM_TARGET = Vector((1.6, 3.4, -0.4))


def key(ob, path, frame, value=None):
    if value is not None:
        setattr(ob, path, value)
    ob.keyframe_insert(data_path=path, frame=seq_f(frame))


def build_web_sequence():
    """Adds the keyframes and returns (camera, list of animated datablocks)."""
    animated = []
    stack_pos = LINEUP_POS["violet"]
    final_pos = Vector(POD_ON_TEMPLE)

    # camera that looks at a moving target
    target = bpy.data.objects.new("SeqTarget", None)
    C_CAMS.objects.link(target)
    cam = camera("Cam_Sequence", LINEUP_CAM_POS, LINEUP_CAM_TARGET, 54)
    cam.rotation_euler = (0, 0, 0)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    ready_pos = final_pos + Vector((2.3, 0, 1.6))
    for f in (1, 34):
        key(cam, "location", f, LINEUP_CAM_POS)
        key(target, "location", f, LINEUP_CAM_TARGET)
        key(cam.data, "lens", f, 35)
        # the stack starts right of centre, leaving room for the headline:
        # it spans about 47% to 94% of the frame width, clear of the hero
        # text on a 16:10 laptop screen (was lens 42, shift -0.18)
        key(cam.data, "shift_x", f, -0.22)
        key(cam.data, "shift_y", f, 0.04)
    key(target, "location", 70, ready_pos)       # follow the pod as it lifts
    key(cam.data, "shift_x", 72, 0.0)
    key(cam.data, "shift_y", 72, 0.0)
    for f in (138, SEQ_FRAMES):
        key(cam, "location", f, HERO_CAM_POS)
        key(target, "location", f, HERO_CAM_TARGET)
        key(cam.data, "lens", f, 62)
    animated += [cam, target, cam.data]

    # the four other colours tuck in behind the violet pod, then shrink away
    away = (stack_pos - LINEUP_CAM_POS).normalized()
    others = [c for c in LINEUP_ORDER if c != "violet"]
    for i, cname in enumerate(others, start=1):
        root = LINEUP_ROOTS[cname]
        start = 1 + (len(others) - i) * 4
        arrive = start + 26
        key(root, "location", start, LINEUP_POS[cname])
        key(root, "location", arrive, stack_pos + away * (0.5 * i))
        key(root, "scale", arrive, (1, 1, 1))
        key(root, "scale", arrive + 3, (0.001, 0.001, 0.001))
        animated.append(root)

    # the glasses are lowered into place
    for f in (1, 44):
        key(GLASSES_ROOT, "location", f, (0, 0, 34))
    key(GLASSES_ROOT, "location", 92, (0, 0, 0))
    animated.append(GLASSES_ROOT)

    # the violet pod lifts clear, lines up beside the temple, then slides on
    key(POD_ROOT, "location", 1, stack_pos)
    key(POD_ROOT, "location", 40, stack_pos)
    key(POD_ROOT, "location", 70, ready_pos)
    key(POD_ROOT, "location", 98, final_pos + Vector((1.9, 0, 0)))
    key(POD_ROOT, "location", 116, final_pos)
    key(POD_ROOT, "location", SEQ_FRAMES, final_pos)
    animated.append(POD_ROOT)
    return cam, animated


def clear_web_sequence(animated):
    for block in animated:
        block.animation_data_clear()
    for cname in LINEUP_ORDER:
        LINEUP_ROOTS[cname].location = LINEUP_POS[cname]
        LINEUP_ROOTS[cname].scale = (1, 1, 1)
    GLASSES_ROOT.location = (0, 0, 0)
    POD_ROOT.location = POD_ON_TEMPLE


def set_pod_colour(cname):
    for ob in list(POD_ROOT.children_recursive):
        mats = getattr(ob.data, "materials", None)
        if mats and mats[0] in M_POD.values():
            mats[0] = M_POD[cname]


# Points on the pod that the page's callouts point at, in the pod's own space.
ANCHOR_POINTS = {
    "sensor":    (-1.92, -2.14, -1.26),   # infrared sensor head
    "clip":      (-0.46, -1.25, 0.42),    # front clip, where it grips the temple
    "pod_top":   (0.20, 0.30, 0.575),     # top edge of the body
    "pod_rear":  (0.31, 1.75, -0.15),     # outer face, rear end
    "pod_front": (0.31, -1.80, 0.0),      # dark front cap
}


def write_anchors(cam):
    """Saves where each anchor lands in the last sequence frame (anchors.json).

    x and y are fractions of the frame, measured from the top left corner, so
    the page can place callouts without anyone measuring a render by hand."""
    import json
    from bpy_extras.object_utils import world_to_camera_view
    scene.frame_set(SEQ_LAST)
    bpy.context.view_layer.update()
    out = {"frame": SEQ_LAST, "frame_size": list(SEQ_RES), "anchors": {}}
    for name, local in ANCHOR_POINTS.items():
        v = world_to_camera_view(scene, cam, POD_ROOT.matrix_world @ Vector(local))
        out["anchors"][name] = {"x": round(v.x, 4), "y": round(1.0 - v.y, 4)}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "anchors.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print("Palpera: wrote", path)


def render_web(do_sequence, do_colours):
    import shutil
    cam, animated = build_web_sequence()
    show(lineup=True)
    # the violet pod in the stack is the one that flies, so hide its twin
    for ob in list(LINEUP_ROOTS["violet"].children_recursive):
        ob.hide_render = True
    scene.camera = cam
    scene.frame_start, scene.frame_end = 1, SEQ_LAST
    r.resolution_x, r.resolution_y = SEQ_RES
    r.resolution_percentage = 100
    scene.cycles.samples = SEQ_SAMPLES
    if hasattr(r.image_settings, "media_type"):
        r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.film_transparent = False
    write_anchors(cam)

    if do_colours:
        col_dir = os.path.join(OUT, "colours")
        os.makedirs(col_dir, exist_ok=True)
        scene.frame_set(SEQ_LAST)
        wanted = os.environ.get("PALPERA_COLOURS", ",".join(LINEUP_ORDER)).split(",")
        for cname in [c for c in LINEUP_ORDER if c in wanted]:
            set_pod_colour(cname)
            r.filepath = os.path.join(col_dir, cname + ".png")
            bpy.ops.render.render(write_still=True)
            print("Palpera: wrote", r.filepath)
        set_pod_colour("violet")

    if do_sequence:
        seq_dir = os.path.join(OUT, "sequence")
        os.makedirs(seq_dir, exist_ok=True)
        frames = list(range(1, SEQ_LAST + 1, SEQ_STEP))
        if frames[-1] != SEQ_LAST:
            frames.append(SEQ_LAST)
        for f in frames:
            scene.frame_set(f)
            r.filepath = os.path.join(seq_dir, "frame_%04d.png" % f)
            bpy.ops.render.render(write_still=True)
            print("Palpera: sequence frame %d of %d" % (f, SEQ_LAST))
        shutil.copyfile(os.path.join(seq_dir, "frame_0001.png"),
                        os.path.join(seq_dir, "hero_stack.png"))
        print("Palpera: wrote sequence to", seq_dir)

    for ob in list(LINEUP_ROOTS["violet"].children_recursive):
        ob.hide_render = False
    clear_web_sequence(animated)
    scene.frame_set(1)
    scene.frame_end = ANIM_FRAMES


# Default visibility for anyone opening the scene: violet pod on the glasses.
show()
scene.camera = CAM_HERO

if "hero" in SHOTS:
    show()
    render_still("hero", CAM_HERO)
if "hero_transparent" in SHOTS:
    show(transparent=True)
    render_still("hero_transparent", CAM_HERO)
if "lineup" in SHOTS:
    show(glasses=False, pod=False, lineup=True)
    render_still("lineup", CAM_LINEUP)
if "side" in SHOTS:
    show()
    render_still("side", CAM_SIDE)
if "closeup" in SHOTS:
    show()
    render_still("closeup", CAM_CLOSE)
if "prototype" in SHOTS:
    show(pod=False, proto=True)
    render_still("prototype_true_size", CAM_HERO)
if "turntable" in SHOTS:
    render_turntable()
if "sequence" in SHOTS or "colours" in SHOTS:
    render_web("sequence" in SHOTS, "colours" in SHOTS)

show()
scene.camera = CAM_HERO
still_settings()
try:
    blend_path = os.path.join(os.path.dirname(OUT), "palpera_pod.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("Palpera: saved scene to", blend_path)
except Exception as exc:
    print("Palpera: could not save .blend:", exc)
