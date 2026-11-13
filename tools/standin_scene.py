"""
STAND-IN scene for developing the web page before the real renders exist.

Builds a crude version of the Palpera set (rough round glasses, five box-ish
pods, soft lights, Cam_Hero) with the object names palpera_sequence.py
expects, then runs the `colours` and `sequence` shots.

These renders are NOT concept renders. tools/frames_to_webp.py --watermark
stamps them "STAND-IN" so they cannot be shipped by accident. Replace them
with renders from palpera_pod.py + palpera_sequence.py before launch.

    blender -b -P tools/standin_scene.py
    (or: python tools/standin_scene.py with the `bpy` package installed)

Env: PALPERA_OUT (default ./renders-standin), PALPERA_STANDIN_SAMPLES (16),
     PALPERA_SEQ_SCALE (resolution percentage, default 100).
"""

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palpera_sequence  # noqa: E402

POD_COLOURS = {
    "violet": "#5A3FC0", "red": "#C8322B", "graphite": "#3A3D45",
    "silver": "#C9CCD3", "sand": "#D8C7A8",
}


def srgb(hexcode):
    h = hexcode.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


def material(name, hexcode, rough=0.45, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = srgb(hexcode)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def link(obj, coll):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def glasses(coll):
    acetate = material("Acetate", "#2B2230", rough=0.25)
    root = bpy.data.objects.new("Glasses", None)
    coll.objects.link(root)
    parts = []
    for side in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=2.45, minor_radius=0.22,
                                         major_segments=64, minor_segments=12,
                                         location=(side * 3.0, 0, 0), rotation=(math.radians(90), 0, 0))
        parts.append(bpy.context.object)
        # temple: from the hinge back along -Y
        bpy.ops.mesh.primitive_cube_add(size=1, location=(side * 5.55, -7.0, 0.35))
        t = bpy.context.object
        t.scale = (0.22, 14.0, 0.42)
        parts.append(t)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.75, minor_radius=0.18, location=(0, 0, 0.9),
                                     rotation=(math.radians(90), 0, 0))
    bridge = bpy.context.object
    bridge.scale = (1, 1, 0.6)
    parts.append(bridge)
    for p in parts:
        p.data.materials.append(acetate)
        p.parent = root
        bevel = p.modifiers.new("bevel", "BEVEL")
        bevel.width = 0.06
        link(p, coll)
    bpy.ops.object.select_all(action="DESELECT")
    return root


def pod(colour, coll):
    body = material("Pod_" + colour, POD_COLOURS[colour], rough=0.35 if colour != "silver" else 0.3,
                    metal=0.4 if colour == "silver" else 0.0)
    sensor = material("Sensor_" + colour, "#E0A458", rough=0.2)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.object
    o.name = "Pod_" + colour.capitalize()
    o.scale = (4.2, 0.62, 1.15)             # length X, thickness Y, height Z
    bpy.ops.object.transform_apply(scale=True)
    bev = o.modifiers.new("bevel", "BEVEL")
    bev.width, bev.segments = 0.26, 5
    o.modifiers.new("sub", "SUBSURF").levels = 1
    bpy.ops.object.shade_smooth()
    o.data.materials.append(body)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(1.55, -0.31, 0.1))
    dot = bpy.context.object
    dot.scale = (1, 0.4, 1)
    dot.data.materials.append(sensor)
    dot.parent = o
    link(o, coll)
    link(dot, coll)
    return o


def main():
    reset()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.01
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(os.environ.get("PALPERA_STANDIN_SAMPLES", "16"))
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = srgb("#F9F8FC")
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    scene.world = world

    g = collection("Glasses")
    p = collection("Pods")
    glasses(g)
    for c in POD_COLOURS:
        pod(c, p)

    # Clipped-on pose: outside of the right temple, near the hinge.
    attach = bpy.data.objects.new("Pod_Attach", None)
    attach.location = (5.55 + 0.45, -2.6, 0.35)
    attach.rotation_euler = (0, 0, math.radians(90))  # pod length along the temple (-Y)
    p.objects.link(attach)
    v = bpy.data.objects["Pod_Violet"]
    v.location, v.rotation_euler = attach.location, attach.rotation_euler

    # Lights
    for name, loc, energy, size in (("Key", (30, 25, 40), 120000, 30), ("Fill", (-35, 20, 15), 40000, 40),
                                    ("Rim", (10, -40, 30), 60000, 20)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size = energy, size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(lo)

    # Cam_Hero: three-quarter view of the right temple and lens.
    cd = bpy.data.cameras.new("Cam_Hero")
    cd.lens = 50
    cam = bpy.data.objects.new("Cam_Hero", cd)
    cam.location = (28.0, 17.0, 10.0)
    target = Vector((3.2, -1.6, 0.2))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam

    out = os.environ.get("PALPERA_OUT", os.path.abspath("renders-standin"))
    shots = os.environ.get("PALPERA_SEQ_SHOTS", "colours,sequence").split(",")
    palpera_sequence.run(shots, out)


main()
