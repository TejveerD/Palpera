# Palpera design experiments: alternative frames and pods for three looks.
#   EXP=fluted | thermal | ascii     which concept to build
#   EXP_OUT=<folder>  EXP_RES=1440x810  EXP_SAMPLES=32
#   EXP_DEVICE=GPU (default; OptiX, then CUDA, else CPU) | CPU
#   EXP_SEQ=299 renders the camera move as seq/frame_0001.png ...
#   EXP_FRAMES=1-30,136-165 renders only those frames of the EXP_SEQ move
#   (same spacing as the full run). Frames already on disk are skipped
#   unless EXP_OVERWRITE=1, so an interrupted run can be restarted.
# Writes beauty.png, and for thermal/ascii also clay.png and podmask.png.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

EXP = os.environ.get("EXP", "fluted")
OUT = os.environ.get("EXP_OUT", "/tmp/exp")
RES = tuple(int(v) for v in os.environ.get("EXP_RES", "1440x810").split("x"))
SAMPLES = int(os.environ.get("EXP_SAMPLES", "32"))
FLOOR_Z = -2.75


def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(h):
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)


def setin(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return


def mat(name, colour, rough=0.4, metallic=0.0, coat=0.0, trans=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    setin(b, ["Base Color"], colour)
    setin(b, ["Roughness"], rough)
    setin(b, ["Metallic"], metallic)
    setin(b, ["Coat Weight", "Clearcoat"], coat)
    setin(b, ["Transmission Weight", "Transmission"], trans)
    setin(b, ["IOR"], ior)
    return m


def emit(name, strength, colour=(1, 1, 1, 1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = colour
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs["Emission"], o.inputs["Surface"])
    return m


def coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def add(name, data, col, m=None, loc=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, data)
    col.objects.link(ob)
    ob.location = loc
    if m is not None and hasattr(data, "materials"):
        data.materials.append(m)
    if parent is not None:
        ob.parent = parent
    return ob


def smooth(me, quads_only=False):
    for p in me.polygons:
        p.use_smooth = (len(p.vertices) == 4) if quads_only else True


def box(name, size, radius, col, m, loc=(0, 0, 0), parent=None, seg=8):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    radius = min(radius, min(size) / 2 * 0.98)
    if radius > 0.001:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=radius, segments=seg,
                        profile=0.5, affect="EDGES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if radius > 0.03:
        smooth(me)
    ob = add(name, me, col, m, loc, parent)
    if radius > 0.03:
        ob.modifiers.new("WN", "WEIGHTED_NORMAL").keep_sharp = False
    return ob


def cyl(name, radius, depth, col, m, loc, axis="Z", seg=48, parent=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius,
                          radius2=radius, depth=depth)
    if axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me, quads_only=True)
    return add(name, me, col, m, loc, parent)


def ball(name, radius, scale, col, m, loc, parent=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=radius)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me)
    return add(name, me, col, m, loc, parent)


def tube(name, pts, radius, col, m, extrude=0.0, parent=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 24
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.extrude = extrude
    cu.use_fill_caps = True
    cu.twist_mode = "Z_UP"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    return add(name, cu, col, m, parent=parent)


def outline(shape, a, b, n=160):
    """Closed 2D outline (x, z) for a lens: superellipse or rounded hexagon."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        if shape == "hex":
            k = math.pi / 3
            r_poly = math.cos(k / 2) / math.cos(((t + k / 2) % k) - k / 2)
            r = 0.82 * r_poly + 0.18          # soften the corners a little
            pts.append((a * r * c, b * r * s))
        else:
            p = shape                           # superellipse exponent
            pts.append((a * math.copysign(abs(c) ** (2 / p), c),
                        b * math.copysign(abs(s) ** (2 / p), s)))
    return pts


def rim(name, pts, radial_w, depth, col, m, loc, nv=20, power=3.0):
    n = len(pts)
    verts, faces = [], []
    for i in range(n):
        x0, z0 = pts[i - 1]
        x1, z1 = pts[(i + 1) % n]
        tx, tz = x1 - x0, z1 - z0
        ln = math.hypot(tx, tz) or 1.0
        nx, nz = tz / ln, -tx / ln              # outward normal
        px, pz = pts[i]
        if nx * px + nz * pz < 0:
            nx, nz = -nx, -nz
        for j in range(nv):
            bb = 2 * math.pi * j / nv
            cb, sb = math.cos(bb), math.sin(bb)
            sx = math.copysign(abs(cb) ** (2 / power), cb) * radial_w / 2
            sy = math.copysign(abs(sb) ** (2 / power), sb) * depth / 2
            verts.append((px + nx * sx, sy, pz + nz * sx))
    for i in range(n):
        for j in range(nv):
            a0 = i * nv + j
            a1 = i * nv + (j + 1) % nv
            b0 = ((i + 1) % n) * nv + j
            b1 = ((i + 1) % n) * nv + (j + 1) % nv
            faces.append((a0, b0, b1, a1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    smooth(me)
    return add(name, me, col, m, loc)


def lens(name, pts, col, m, loc, thick=0.12):
    n = len(pts)
    verts = [(x, -thick / 2, z) for x, z in pts] + [(x, thick / 2, z) for x, z in pts]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return add(name, me, col, m, loc)


def look(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
scene = bpy.context.scene

CFG = {
    "fluted": dict(shape=4.2, a=2.55, b=1.95, w=0.44, d=0.42, lens_x=3.05,
                   frame=mat("Frame", rgba("2F5D50"), rough=0.08, coat=0.5, trans=0.75, ior=1.49),
                   pod_col="F2EFE6", world="B9CBC3", floor="F4F4F0"),
    "thermal": dict(shape=5.0, a=2.65, b=2.0, w=0.62, d=0.5, lens_x=3.2,
                    frame=mat("Frame", rgba("1A1A1E"), rough=0.3),
                    pod_col="E8E8E8", world="CCCCCC", floor="F5F5F5"),
    "ascii": dict(shape="hex", a=2.55, b=2.45, w=0.30, d=0.30, lens_x=3.15,
                  frame=mat("Frame", rgba("101216"), rough=0.25, metallic=0.6),
                  pod_col="1B1E26", world="F2F3F5", floor="FFFFFF"),
    # ---- fluted-glass family
    "fl_window": dict(base="fluted", shape=2.6, a=2.6, b=2.2, w=0.42, d=0.42, lens_x=3.1,
                      frame=mat("Frame", rgba("E3EAF0"), rough=0.05, coat=0.6, trans=0.92, ior=1.49),
                      pod_col="1F3A8A", world="B4C2D3", floor="F3F5F8",
                      rods=dict(spans=[(-12.5, 4.3), (8.1, 14.5)], radius=0.28, step=0.56, tint="E4EDF6")),
    "fl_dusk": dict(base="fluted", shape=4.2, a=2.55, b=1.95, w=0.44, d=0.42, lens_x=3.05,
                    frame=mat("Frame", rgba("EDE6F2"), rough=0.2),
                    pod_col="FF7A59", world="24103A", floor="3A1C4E",
                    rods=dict(spans=[(-12.5, 14.5)], radius=0.34, step=0.68, tint="FFFFFF"),
                    backlights=[(-9, "FF6B4A", 3.0), (1, "D01F6E", 2.6), (10, "FFB347", 3.0)]),
    "fl_wide": dict(base="fluted", shape=2.0, a=2.45, b=2.45, w=0.46, d=0.42, lens_x=3.3,
                    frame=mat("Frame", rgba("E9E4DA"), rough=0.25),
                    pod_col="E8622A", world="2A2D33", floor="3B3E45",
                    rods=dict(spans=[(-13.2, 4.6)], radius=1.05, step=2.1, tint="DCE3E8")),
    "fl_macro": dict(base="fluted", shape=4.2, a=2.55, b=1.95, w=0.44, d=0.42, lens_x=3.05,
                     frame=mat("Frame", rgba("5A3A28"), rough=0.08, coat=0.5, trans=0.6, ior=1.49),
                     pod_col="F2A23C", world="D9D3D8", floor="F5F2F4", rods=None, pod_glass=True,
                     cam=((16.5, -9.5, 4.0), (6.9, 2.2, 0.55), 92)),
    # ---- chosen direction: the first fluted design, a little more frame in
    # view, with a glass pod, and a camera move into a close-up of the pod
    "fl_site": dict(base="fluted", shape=4.2, a=2.55, b=1.95, w=0.44, d=0.42, lens_x=3.05,
                    frame=mat("Frame", rgba("2F5D50"), rough=0.08, coat=0.5, trans=0.75, ior=1.49),
                    pod_col=os.environ.get("EXP_POD", "E6F1EB"), world="B9CBC3", floor="F4F4F0",
                    pod_glass=os.environ.get("EXP_POD_GLASS", "1") == "1", core_col="2F5D50",
                    rods=dict(spans=[(-10.5, 2.3)], radius=0.28, step=0.56, tint="E9F2EE"),
                    cam_end=((14.5, -11.0, 4.1), (6.1, 2.1, 0.3), 80), puck=True, sx=-2.3),
}[EXP]
BASE = CFG.get("base", EXP)

M_LENS = mat("Lens", (1, 1, 1, 1), rough=0.0, trans=1.0, ior=1.5)
M_SENSOR = mat("Sensor", rgba("1A0B0B"), rough=0.05, coat=1.0)
if CFG.get("pod_glass"):
    M_POD = mat("Pod", rgba(CFG["pod_col"]), rough=0.12, trans=0.92, ior=1.5)
else:
    _met = os.environ.get("EXP_POD_METAL", "0") == "1"
    M_POD = mat("Pod", rgba(CFG["pod_col"]), rough=0.32 if _met else 0.42,
                metallic=0.85 if _met else 0.0, coat=0.0 if _met else 0.2)
M_DARK = mat("Dark", rgba("17151C"), rough=0.1, coat=1.0)
M_FLOOR = mat("Floor", rgba(CFG["floor"]), rough=1.0)
M_FRAME = CFG["frame"]

C_GL = coll("Glasses")
C_POD = coll("Pod")
C_ST = coll("Studio")
C_FL = coll("Fluted")

pts = outline(CFG["shape"], CFG["a"], CFG["b"])
inner = outline(CFG["shape"], CFG["a"] - CFG["w"] * 0.25, CFG["b"] - CFG["w"] * 0.25)
LX = CFG["lens_x"]
TZ = min(0.95, CFG["b"] * 0.5)
outer_x = LX + CFG["a"] + CFG["w"] / 2
TX = outer_x + 0.12
for side in (-1, 1):
    t = "L" if side < 0 else "R"
    rim("Rim" + t, pts, CFG["w"], CFG["d"], C_GL, M_FRAME, (side * LX, 0, 0))
    lens("Lens" + t, inner, C_GL, M_LENS, (side * LX, 0, 0))
    box("Lug" + t, (0.6, 0.6, 0.64), 0.14, C_GL, M_FRAME, (side * (outer_x - 0.1), 0.12, TZ))
    if BASE == "ascii":
        tube("Temple" + t, [(side * TX, 0.3, TZ), (side * TX, 5, TZ), (side * TX, 9.4, TZ - 0.05),
                            (side * (TX - 0.14), 11.9, -0.75), (side * (TX - 0.3), 13.1, -2.35)],
             0.13, C_GL, M_FRAME)
    else:
        tube("Temple" + t, [(side * TX, 0.3, TZ), (side * TX, 5, TZ), (side * TX, 9.4, TZ - 0.05),
                            (side * (TX - 0.14), 11.9, -0.75), (side * (TX - 0.3), 13.1, -2.35)],
             0.085, C_GL, M_FRAME, extrude=0.23 if BASE == "fluted" else 0.3)
    ball("Pad" + t, 0.24, (0.5, 0.9, 1.5), C_GL, M_FRAME, (side * (LX - CFG["a"] + 0.35), 0.34, -0.9))
bx = LX - CFG["a"] - CFG["w"] / 2 + 0.1
tube("Bridge", [(-bx, 0, 0.7), (0, -0.04, 1.15), (bx, 0, 0.7)], 0.2 if BASE != "ascii" else 0.13,
     C_GL, M_FRAME)
if BASE == "thermal":                      # flat top bar for a bold D-frame look
    box("Brow", (2 * outer_x - 0.2, 0.46, 0.5), 0.2, C_GL, M_FRAME, (0, 0, CFG["b"] + 0.05))

# ------------------------------------------------------------------ pod
root = bpy.data.objects.new("PodRoot", None)
C_POD.objects.link(root)
if BASE == "fluted":
    size = (0.66, 4.0, 1.2)
    root.location = (TX + 0.46, 3.0, TZ)
    box("Body", size, 0.2, C_POD, M_POD, parent=root)
    for i in range(17):                    # ribs along the outer face
        cyl("Rib%d" % i, 0.085, size[2] - 0.34, C_POD, M_POD,
            (size[0] / 2 - 0.02, -1.6 + i * 0.2, 0), axis="Z", seg=20, parent=root)
    if CFG.get("pod_glass"):               # a dark core shows through the glass body
        M_CORE = mat("Core", rgba(CFG.get("core_col", "17151C")), rough=0.3)
        box("Core", (0.26, 3.0, 0.62), 0.08, C_POD, M_CORE, (-0.05, 0.1, 0), parent=root)
elif BASE == "thermal":
    size = (0.92, 3.6, 0.92)
    root.location = (TX + 0.58, 3.0, TZ)
    box("Body", size, 0.45, C_POD, M_POD, parent=root, seg=12)   # a capsule
    box("Band", (0.94, 0.5, 0.94), 0.46, C_POD, M_DARK, (0, -1.2, 0), parent=root, seg=12)
else:
    size = (0.7, 3.4, 1.3)
    root.location = (TX + 0.47, 3.0, TZ)
    box("Body", size, 0.03, C_POD, M_POD, parent=root)            # a hard-edged brick
    box("Step1", (0.7, 0.5, 0.9), 0.03, C_POD, M_POD, (0, -1.95, 0), parent=root)
    box("Step2", (0.7, 0.5, 0.9), 0.03, C_POD, M_POD, (0, 1.95, 0), parent=root)
for i, y in enumerate((-1.1, 1.1)):
    box("Clip%d" % i, (0.4, 0.44, 0.8), 0.08, C_POD, M_POD, (-size[0] / 2 - 0.15, y, 0), parent=root)
fy = -size[1] / 2
SX = CFG.get("sx", -1.92)                  # sensor position across the lens
tube("Arm", [(-0.02, fy + 0.3, -0.36), (-0.24, fy - 0.2, -0.74),
             (-0.95, fy - 0.24, -1.04), (SX + 0.14, fy - 0.08, -1.24)], 0.1, C_POD, M_POD, parent=root)
if CFG.get("puck"):
    # a flat puck: the outward face (-Y, seen through the lens) is where the
    # logo goes; the dark infrared window is on the side facing the eye
    cyl("SensorFace", 0.3, 0.2, C_POD, M_POD, (SX, fy - 0.04, -1.26), axis="Y", seg=48, parent=root)
    ball("Sensor", 0.2, (1, 0.5, 1), C_POD, M_SENSOR, (SX, fy + 0.07, -1.26), parent=root)
else:
    ball("Sensor", 0.25, (1, 0.7, 1), C_POD, M_SENSOR, (SX, fy - 0.04, -1.26), parent=root)

# --------------------------------------------------------------- studio
def plane(name, size, col, m, loc):
    s = size / 2
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.update()
    return add(name, me, col, m, loc)


floor = plane("Floor", 20000, C_ST, M_FLOOR, (0, 0, FLOOR_Z))
for nm, sz, loc, st in (("Key", 34, (-20, -26, 30), 2.2), ("Fill", 30, (34, -14, 14), 0.9),
                        ("Top", 60, (0, 4, 48), 0.7), ("Rim", 26, (6, 44, 20), 2.0)):
    sb = plane(nm, sz, C_ST, emit(nm + "M", st), loc)
    look(sb, (0, 3, 0))
    sb.visible_camera = False
world = bpy.data.worlds.new("W")
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = rgba(CFG["world"])
bg.inputs["Strength"].default_value = 1.0
scene.world = world

_cam = CFG.get("cam", ((25, -20, 7.5), (1.6, 3.4, -0.4), 62))
CAM_POS, CAM_TGT = Vector(_cam[0]), Vector(_cam[1])
cd = bpy.data.cameras.new("Cam")
cd.lens, cd.clip_start, cd.clip_end = _cam[2], 0.5, 5000
cam = add("Cam", cd, C_ST, loc=CAM_POS)
look(cam, CAM_TGT)
scene.camera = cam

RODS = CFG.get("rods", dict(spans=[(-10.5, 3.6)], radius=0.28, step=0.56, tint="E9F2EE")
               if BASE == "fluted" else None)
d = Vector((1.6 - 25, 3.4 + 20, 0)).normalized()      # away from the standard camera
u = Vector((-d.y, d.x, 0))
if u.x < 0:
    u = -u
if RODS:
    # Walls of glass rods between the camera and the glasses. Spans are
    # positions across the view; a gap between spans leaves a clear window.
    M_GLASS = mat("Fluted", rgba(RODS["tint"]), rough=0.02, trans=1.0, ior=1.5)
    height = 14.0
    k = 0
    for s0, s1 in RODS["spans"]:
        s_ = s0
        while s_ <= s1:
            p = u * s_ - d * 7.0
            cyl("Rod%d" % k, RODS["radius"], height, C_FL, M_GLASS,
                (p.x, p.y, FLOOR_Z + height / 2), seg=40)
            s_ += RODS["step"]
            k += 1
for i, (s_, colour, strength) in enumerate(CFG.get("backlights", [])):
    # coloured light panels behind the glasses, seen through the fluted glass
    p = u * s_ + d * 26.0
    bl = plane("Back%d" % i, 24, C_ST, emit("BackM%d" % i, strength, rgba(colour)), (p.x, p.y, 0.5))
    look(bl, CAM_POS)

# --------------------------------------------------------------- render
r = scene.render
r.engine = "CYCLES"
scene.cycles.use_denoising = True
scene.cycles.samples = SAMPLES


def use_gpu():
    want = os.environ.get("EXP_DEVICE", "GPU").upper()
    if want != "GPU":
        scene.cycles.device = "CPU"
        print("EXP device CPU (asked for)")
        return
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == kind
            scene.cycles.device = "GPU"
            print("EXP device", kind, [d.name for d in gpus])
            return
    scene.cycles.device = "CPU"
    print("EXP WARNING: no OptiX/CUDA GPU found, rendering on CPU")


use_gpu()
r.resolution_x, r.resolution_y = RES
r.resolution_percentage = 100
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGBA"
try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
except Exception:
    pass
os.makedirs(OUT, exist_ok=True)


def render(name):
    r.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("EXP wrote", r.filepath)


def pose(t):
    """Camera pose along the move from the hero view (t=0) to the close-up (t=1)."""
    end = CFG.get("cam_end")
    if not end:
        return
    e = t * t * (3 - 2 * t)
    cam.location = CAM_POS.lerp(Vector(end[0]), e)
    tgt = CAM_TGT.lerp(Vector(end[1]), e)
    cd.lens = _cam[2] + (end[2] - _cam[2]) * e
    look(cam, tgt)
    bpy.context.view_layer.update()


KEYS = [float(x) for x in os.environ.get("EXP_T", "").split(",") if x.strip()]
SEQ_N = int(os.environ.get("EXP_SEQ", "0"))
if KEYS:
    for t in KEYS:
        pose(t)
        render("key_%03d" % round(t * 100))
    if 1.0 in KEYS:
        import json
        from bpy_extras.object_utils import world_to_camera_view
        pose(1.0)
        fy_ = -size[1] / 2
        local = {"sensor": (SX, fy_ - 0.14, -1.26), "clip": (-size[0] / 2 - 0.15, -1.1, 0.42),
                 "pod_top": (0.1, 0.4, size[2] / 2), "pod_rear": (size[0] / 2, 1.7, -0.1),
                 "ribs": (size[0] / 2 + 0.05, -0.4, 0.2), "core": (0.0, 1.0, -0.45)}
        out = {}
        for k_, v_ in local.items():
            c_ = world_to_camera_view(scene, cam, root.matrix_world @ Vector(v_))
            out[k_] = [round(c_.x, 4), round(1 - c_.y, 4)]
        json.dump(out, open(os.path.join(OUT, "anchors.json"), "w"), indent=1)
        print("EXP anchors", out)
elif SEQ_N:
    import time
    want = set()
    for part in os.environ.get("EXP_FRAMES", "").split(","):
        if part.strip():
            a_, _, b_ = part.strip().partition("-")
            want.update(range(int(a_), int(b_ or a_) + 1))
    todo = [n for n in range(1, SEQ_N + 1) if not want or n in want]
    r.image_settings.color_mode = "RGB"   # opaque scene: no alpha needed
    overwrite = os.environ.get("EXP_OVERWRITE", "0") == "1"
    t0 = time.time()
    for k, n in enumerate(todo):
        if not overwrite and os.path.exists(os.path.join(OUT, "seq", "frame_%04d.png" % n)):
            continue
        t1 = time.time()
        pose((n - 1) / (SEQ_N - 1))
        render("seq/frame_%04d" % n)
        print("EXP frame %d (%d/%d) %.1fs, total %.0fs" % (n, k + 1, len(todo), time.time() - t1, time.time() - t0))
else:
    render("beauty")

if BASE in ("thermal", "ascii"):
    # clay pass: objects only, plain white, for shading and an alpha mask
    clay = mat("Clay", (0.8, 0.8, 0.8, 1), rough=1.0)
    for ob in list(C_GL.objects) + list(C_POD.objects):
        if hasattr(ob.data, "materials") and ob.data.materials:
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = clay
    floor.hide_render = True
    r.film_transparent = True
    scene.cycles.samples = max(8, SAMPLES // 3)
    render("clay")
    C_GL.hide_render = True
    render("podmask")
