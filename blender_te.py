"""Tiny Empires 3D plates (Blender 4.2, Cycles CPU, headless on GitHub runners). 2D characters are composited on top later.

  blender -b --factory-startup -P blender_te.py -- <shot> <out_dir> <seconds> <samples> <still_frame|0> <WxH> <terrain_dir>

Shots
  globe          the Earth from space, turning from Europe to India while the camera closes in
  india          3D relief of the subcontinent (real elevation, x22 exaggeration), oblique flight towards the Himalaya
  bengal         the Ganges delta and Bengal (real elevation), low flight over the rivers
  spice          the Spice Islands (Maluku) in 3D relief
  ocean          open ocean with three East Indiamen under sail
  fort           a Company fort by a river: brick walls, bastions, gate, warehouses, flag
  durbar         a Mughal durbar hall: cusped arches, columns, a throne under a canopy
  court          a Tudor hall: oak panelling, leaded windows, a throne under a red canopy
  plassey        open ground, a mango grove and a river, early afternoon
  plassey_rain   the same field under monsoon cloud
  camp           a night camp: tents, a lantern-lit tent, campfire, moonlight
Accuracy notes: terrain from Terrain Tiles (SRTM etc.); buildings are generic period reconstructions (labelled as such in the
film), not exact replicas.
"""
import json
import math
import os
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = argv[0], Path(argv[1])
SECONDS = float(argv[2]) if len(argv) > 2 else 8.0
SAMPLES = int(argv[3]) if len(argv) > 3 else 16
STILL = int(argv[4]) if len(argv) > 4 else 0
RES = tuple(int(v) for v in argv[5].split("x")) if len(argv) > 5 else (1920, 1080)
TERRAIN = Path(argv[6]) if len(argv) > 6 else Path("terrain")
FPS = 24
N = int(SECONDS * FPS)
random.seed(11)


# ------------------------------------------------------------------------------------------------ basics
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.threads_mode = "FIXED"
    sc.render.threads = int(os.environ.get("YTG_THREADS", "4"))
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.use_persistent_data = True
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, N
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    return sc


def mat(name, color, rough=0.6, metal=0.0, emit=None, strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def noisy(name, c1, c2, scale=8.0, rough=0.8, bump=0.3):
    """Two-tone material broken up with noise (plaster, brick, ground, wood)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*c1, 1)
    cr.color_ramp.elements[1].color = (*c2, 1)
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    return m


def bricks(name, brick, mortar, scale=6.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeNewGeometry")                                  # world position: bricks stay brick-sized
    bt = nt.nodes.new("ShaderNodeTexBrick")
    bt.inputs["Color1"].default_value = (*brick, 1)
    bt.inputs["Color2"].default_value = (*[c * 0.85 for c in brick], 1)
    bt.inputs["Mortar"].default_value = (*mortar, 1)
    bt.inputs["Scale"].default_value = scale
    bt.inputs["Mortar Size"].default_value = 0.015
    nt.links.new(tc.outputs["Position"], bt.inputs["Vector"])
    nt.links.new(bt.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.4
    nt.links.new(bt.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.85
    return m


def add(kind, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), m=None, name=None, **kw):
    fn = {"cube": bpy.ops.mesh.primitive_cube_add, "cyl": bpy.ops.mesh.primitive_cylinder_add, "sphere": bpy.ops.mesh.primitive_uv_sphere_add,
          "ico": bpy.ops.mesh.primitive_ico_sphere_add, "cone": bpy.ops.mesh.primitive_cone_add, "plane": bpy.ops.mesh.primitive_plane_add,
          "torus": bpy.ops.mesh.primitive_torus_add}[kind]
    fn(location=loc, rotation=rot, **kw)
    o = bpy.context.active_object
    o.scale = scale
    if name:
        o.name = name
    if m:
        o.data.materials.append(m)
    return o


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def sky(sun_el=25.0, sun_rot=40.0, strength=0.8, turbidity=None):
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    st = nt.nodes.new("ShaderNodeTexSky")
    st.sky_type = "NISHITA"
    st.sun_elevation = math.radians(sun_el)
    st.sun_rotation = math.radians(sun_rot)
    st.air_density = 1.0
    st.dust_density = 1.5
    st.sun_disc = False                                                         # the sun lamp lights the scene; the sky only fills
    nt.links.new(st.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength * 0.18
    return w


def flat_world(color, strength):
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*color, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = strength
    return w


def sun(el=35, az=40, strength=3.0, color=(1, 0.95, 0.88), angle=2.0):
    bpy.ops.object.light_add(type="SUN")
    s = bpy.context.active_object
    s.data.energy = strength * 0.7
    s.data.color = color
    s.data.angle = math.radians(angle)
    s.rotation_euler = (math.radians(90 - el), 0, math.radians(az))
    return s


def light(kind, loc, energy, color=(1, 0.85, 0.6), size=1.0):
    bpy.ops.object.light_add(type=kind, location=loc)
    l = bpy.context.active_object
    l.data.energy = energy
    l.data.color = color
    if kind == "AREA":
        l.data.size = size
    elif kind == "POINT":
        l.data.shadow_soft_size = size
    return l


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def camera_path(keys, lens=35, target_keys=None):
    """keys: [(frac, (x, y, z))]; target_keys: [(frac, (x, y, z))] the camera looks at (eased)."""
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.lens = lens
    cam.data.clip_end = 5000
    bpy.context.scene.camera = cam
    bpy.ops.object.empty_add(location=target_keys[0][1] if target_keys else (0, 0, 0))
    tgt = bpy.context.active_object
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    for f in range(1, N + 1, 2):
        fr = (f - 1) / max(1, N - 1)
        cam.location = _interp(keys, fr)
        cam.keyframe_insert("location", frame=f)
        if target_keys:
            tgt.location = _interp(target_keys, fr)
            tgt.keyframe_insert("location", frame=f)
    return cam


def _interp(keys, fr):
    if fr <= keys[0][0]:
        return Vector(keys[0][1])
    for (a, pa), (b, pb) in zip(keys, keys[1:]):
        if a <= fr <= b:
            e = ease((fr - a) / max(1e-6, b - a))
            return Vector(pa).lerp(Vector(pb), e)
    return Vector(keys[-1][1])


# ------------------------------------------------------------------------------------------------ terrain maps
def terrain(name, exaggeration=22.0, sea=(0.08, 0.2, 0.32)):
    """Real-elevation relief: a subdivided grid displaced by the 16-bit height map, coloured by Natural Earth imagery."""
    meta = json.loads((TERRAIN / f"{name}.json").read_text())
    lon0, lat0, lon1, lat1 = meta["bbox"]
    W, H = meta["size"]
    width_km = (lon1 - lon0) * meta["km_per_deg"]
    height_km = (lat1 - lat0) * 111.32
    sx, sy = 100.0, 100.0 * height_km / width_km                                # scene units: 100 across
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=900, y_subdivisions=int(900 * sy / sx), size=1)
    g = bpy.context.active_object
    g.scale = (sx, sy, 1)
    bpy.ops.object.transform_apply(scale=True)
    img_h = bpy.data.images.load(str(TERRAIN / f"{name}_height.png"))
    img_h.colorspace_settings.name = "Non-Color"
    tex = bpy.data.textures.new("h", "IMAGE")
    tex.image = img_h
    tex.extension = "EXTEND"
    md = g.modifiers.new("disp", "DISPLACE")
    md.texture = tex
    md.texture_coords = "UV"
    md.mid_level = 0.0
    km_per_unit = width_km / sx
    md.strength = 65.535 / km_per_unit * exaggeration                           # 16-bit 0..1 = 0..65.5 km
    smooth(g)
    m = bpy.data.materials.new("terrain")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ic = nt.nodes.new("ShaderNodeTexImage")
    ic.image = bpy.data.images.load(str(TERRAIN / f"{name}_color.png"))
    ic.extension = "EXTEND"
    iw = nt.nodes.new("ShaderNodeTexImage")
    iw.image = bpy.data.images.load(str(TERRAIN / f"{name}_water.png"))
    iw.image.colorspace_settings.name = "Non-Color"
    nt.links.new(tc.outputs["UV"], ic.inputs["Vector"])
    nt.links.new(tc.outputs["UV"], iw.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*sea, 1)
    nt.links.new(iw.outputs["Color"], mix.inputs["Factor"])
    nt.links.new(ic.outputs["Color"], mix.inputs["A"])
    hue = nt.nodes.new("ShaderNodeHueSaturation")
    hue.inputs["Saturation"].default_value = 1.15
    nt.links.new(mix.outputs["Result"], hue.inputs["Color"])
    nt.links.new(hue.outputs["Color"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.85
    rr.inputs["To Max"].default_value = 0.15
    nt.links.new(iw.outputs["Color"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    g.data.materials.append(m)
    return g, (sx, sy), (lon0, lat0, lon1, lat1)


def lonlat_to_xy(lon, lat, size, bbox):
    sx, sy = size
    lon0, lat0, lon1, lat1 = bbox
    return ((lon - lon0) / (lon1 - lon0) - 0.5) * sx, ((lat - lat0) / (lat1 - lat0) - 0.5) * sy


def haze_world(top=(0.35, 0.55, 0.85), strength=0.9):
    sky(30, 200, strength)


def shot_india():
    sc = reset()
    g, size, bbox = terrain("india", 18.0)
    sky(28, 160, 0.7)
    sun(28, 200, 4.0)
    tx, ty = lonlat_to_xy(80, 24, size, bbox)
    camera_path([(0.0, (tx - 6, ty - 70, 38)), (1.0, (tx - 2, ty - 42, 22))], lens=30,
                target_keys=[(0.0, (tx - 2, ty + 2, 0)), (1.0, (tx + 2, ty + 10, 0))])
    return sc


def shot_bengal():
    sc = reset()
    g, size, bbox = terrain("bengal", 9.0)
    sky(32, 170, 0.7)
    sun(30, 210, 4.0)
    cx, cy = lonlat_to_xy(88.3, 23.2, size, bbox)
    camera_path([(0.0, (cx - 18, cy - 46, 22)), (1.0, (cx - 6, cy - 26, 12))], lens=32,
                target_keys=[(0.0, (cx, cy + 4, 0)), (1.0, (cx + 3, cy + 8, 0))])
    return sc


def shot_spice():
    sc = reset()
    g, size, bbox = terrain("spice", 25.0)
    sky(35, 150, 0.7)
    sun(35, 200, 4.0)
    cx, cy = lonlat_to_xy(126, -2, size, bbox)
    camera_path([(0.0, (cx - 20, cy - 48, 30)), (1.0, (cx - 6, cy - 32, 18))], lens=30, target_keys=[(0.0, (cx, cy, 0)), (1.0, (cx + 4, cy + 4, 0))])
    return sc


def shot_globe():
    sc = reset()
    flat_world((0.0, 0.0, 0.004), 1.0)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=10)
    e = bpy.context.active_object
    smooth(e)
    img = bpy.data.images.load(str(TERRAIN / "globe_color.png"))
    m = bpy.data.materials.new("earth")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    it = nt.nodes.new("ShaderNodeTexImage")
    it.image = img
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["UV"], it.inputs["Vector"])
    nt.links.new(it.outputs["Color"], b.inputs["Base Color"])
    ih = nt.nodes.new("ShaderNodeTexImage")
    ih.image = bpy.data.images.load(str(TERRAIN / "globe_height.png"))
    ih.image.colorspace_settings.name = "Non-Color"
    nt.links.new(tc.outputs["UV"], ih.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    bp.inputs["Distance"].default_value = 0.02
    nt.links.new(ih.outputs["Color"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.7
    e.data.materials.append(m)
    # atmosphere shell: soft blue rim
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=10.35)
    a = bpy.context.active_object
    smooth(a)
    am = bpy.data.materials.new("atmo")
    am.use_nodes = True
    ant = am.node_tree
    for nd in list(ant.nodes):
        if nd.type != "OUTPUT_MATERIAL":
            ant.nodes.remove(nd)
    lw = ant.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    em = ant.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.35, 0.6, 1.0, 1)
    tr = ant.nodes.new("ShaderNodeBsdfTransparent")
    mx = ant.nodes.new("ShaderNodeMixShader")
    pw = ant.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 2.5
    ant.links.new(lw.outputs["Facing"], pw.inputs[0])
    ant.links.new(pw.outputs[0], mx.inputs["Fac"])
    ant.links.new(tr.outputs[0], mx.inputs[1])
    em.inputs["Strength"].default_value = 3.0
    ant.links.new(em.outputs[0], mx.inputs[2])
    ant.links.new(mx.outputs[0], ant.nodes["Material Output"].inputs["Surface"])
    a.data.materials.append(am)
    sun(10, 120, 5.0, (1, 0.97, 0.92), 0.5)
    rng = random.Random(3)                                                      # stars
    for _ in range(260):
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized() * 400
        s = add("ico", tuple(d), (0.5, 0.5, 0.5), m=mat("star", (1, 1, 1), emit=(1, 1, 1), strength=rng.uniform(2, 8)), subdivisions=1)
    # rotation: from Europe/Africa (lon 15) to India (lon 80), tilt to 22 N
    e.rotation_mode = a.rotation_mode = "XYZ"
    for f in range(1, N + 1, 2):
        fr = ease((f - 1) / max(1, N - 1))
        lon = 15 + (80 - 15) * fr
        lat = 15 + (22 - 15) * fr
        rz = math.radians(-90 - lon)                                            # UV seam at -180; face the camera on -Y
        rx = math.radians(lat)
        for o in (e, a):
            o.rotation_euler = (rx, 0, rz)
            o.keyframe_insert("rotation_euler", frame=f)
    camera_path([(0.0, (0, -46, 0)), (1.0, (0, -22, 2))], lens=40, target_keys=[(0.0, (0, 0, 0)), (1.0, (0, 0, 3.2))])
    return sc


# ------------------------------------------------------------------------------------------------ environments
def ground(size, mat_, subdiv=0, disp=0.0, scale_noise=0.05):
    o = add("plane", (0, 0, 0), (size, size, 1), m=mat_)
    if subdiv:
        md = o.modifiers.new("sub", "SUBSURF")
        md.subdivision_type = "SIMPLE"
        md.levels = md.render_levels = subdiv
        tex = bpy.data.textures.new("n", "CLOUDS")
        tex.noise_scale = 1.0 / max(1e-3, scale_noise)
        d = o.modifiers.new("d", "DISPLACE")
        d.texture = tex
        d.strength = disp
    return o


def tree(x, y, s=1.0, leaf=None, trunk=None, mango=True):
    trunk = trunk or mat("trunk", (0.25, 0.15, 0.08), 0.9)
    leaf = leaf or noisy("leaf", (0.09, 0.22, 0.07), (0.18, 0.36, 0.1), 3.0, 0.7, 0.6)
    add("cyl", (x, y, 1.0 * s), (0.18 * s, 0.18 * s, 1.0 * s), m=trunk, vertices=8)
    for dx, dy, dz, r in ((0, 0, 2.5, 1.5), (0.8, 0.3, 2.1, 1.1), (-0.7, -0.4, 2.2, 1.1), (0.2, -0.8, 2.9, 1.0)):
        o = add("ico", (x + dx * s, y + dy * s, dz * s), (r * s, r * s, r * 0.85 * s), m=leaf, subdivisions=2)
        smooth(o)


def water_plane(loc, scale, color=(0.08, 0.2, 0.25)):
    m = mat("water", color, 0.05)
    o = add("plane", loc, scale, m=m)
    tex = bpy.data.textures.new("w", "CLOUDS")
    tex.noise_scale = 0.4
    return o


def shot_plassey(rain=False):
    sc = reset()
    if rain:
        flat_world((0.32, 0.36, 0.42), 0.9)
        sun(40, 200, 0.6, (0.8, 0.85, 0.95), 25)
    else:
        sky(38, 230, 0.8)
        sun(38, 230, 3.5)
    g = ground(160, noisy("grass", (0.13, 0.26, 0.06), (0.26, 0.38, 0.1) if not rain else (0.18, 0.28, 0.08), 0.6, 0.9, 0.2), 6, 1.2, 0.03)
    water_plane((0, 70, 0.15), (160, 12, 1), (0.1, 0.22, 0.24) if not rain else (0.12, 0.17, 0.2))
    leaf = noisy("leaf", (0.07, 0.2, 0.06), (0.15, 0.32, 0.08), 3.0, 0.7, 0.6)
    trunk = mat("trunk", (0.25, 0.15, 0.08), 0.9)
    rng = random.Random(4)
    for _ in range(110):                                                        # the mango grove (Lakshabagh)
        tree(rng.uniform(-60, 60), rng.uniform(32, 55), rng.uniform(0.9, 1.3), leaf, trunk)
    for _ in range(25):
        tree(rng.uniform(-80, 80), rng.uniform(-10, 25), rng.uniform(0.8, 1.1), leaf, trunk)
    camera_path([(0.0, (-14, -40, 9)), (1.0, (6, -34, 6))], lens=30, target_keys=[(0.0, (0, 30, 2)), (1.0, (4, 30, 2))])
    return sc


def walls_rect(cx, cy, w, d, h, thick, m, crenel_m, bastion=True):
    parts = []
    for (x, y, sxx, syy) in ((cx, cy - d / 2, w / 2, thick / 2), (cx, cy + d / 2, w / 2, thick / 2), (cx - w / 2, cy, thick / 2, d / 2),
                             (cx + w / 2, cy, thick / 2, d / 2)):
        parts.append(add("cube", (x, y, h / 2), (sxx, syy, h / 2), m=m))
    for side in range(4):                                                       # crenellations
        for k in range(int((w if side < 2 else d) / 1.6)):
            if side < 2:
                x = cx - w / 2 + 0.8 + k * 1.6
                y = cy + (-d / 2 if side == 0 else d / 2)
            else:
                y = cy - d / 2 + 0.8 + k * 1.6
                x = cx + (-w / 2 if side == 2 else w / 2)
            add("cube", (x, y, h + 0.35), (0.4, thick / 2 + 0.02, 0.35), m=crenel_m)
    if bastion:
        for sx_ in (-1, 1):
            for sy_ in (-1, 1):
                add("cyl", (cx + sx_ * w / 2, cy + sy_ * d / 2, h * 0.6), (2.4, 2.4, h * 0.6), m=m, vertices=12)
    return parts


def shot_fort():
    sc = reset()
    sky(30, 250, 0.9)
    sun(30, 250, 3.5, (1, 0.9, 0.75))
    ground(200, noisy("sand", (0.55, 0.45, 0.3), (0.68, 0.58, 0.4), 0.4, 0.95, 0.2), 4, 0.4, 0.05)
    water_plane((0, 60, 0.1), (200, 30, 1), (0.12, 0.25, 0.3))
    brick = bricks("brick", (0.5, 0.2, 0.12), (0.72, 0.64, 0.55), 1.4)
    walls_rect(0, 25, 46, 30, 7, 1.6, brick, brick)
    add("cube", (0, 25 - 15.9, 2.6), (2.0, 0.3, 2.6), m=mat("gate", (0.22, 0.13, 0.08), 0.8))                # gate
    for i in range(4):                                                          # warehouses inside
        add("cube", (-15 + i * 10, 30, 3.2), (3.8, 4.5, 3.2), m=noisy("plaster", (0.82, 0.76, 0.66), (0.9, 0.86, 0.78), 2, 0.9, 0.1))
        add("cube", (-15 + i * 10, 30, 6.6), (4.1, 4.8, 0.35), m=mat("roof", (0.45, 0.2, 0.15), 0.8))
    pole = add("cyl", (18, 30, 12), (0.12, 0.12, 6), m=mat("pole", (0.2, 0.2, 0.2)))
    add("cube", (19.3, 30, 16.6), (1.3, 0.04, 0.8), m=mat("flag", (0.75, 0.1, 0.1), 0.7))
    rng = random.Random(9)
    for _ in range(14):
        tree(rng.choice([-1, 1]) * rng.uniform(32, 70), rng.uniform(-10, 40), rng.uniform(0.8, 1.1), mango=False)
    camera_path([(0.0, (-30, -40, 10)), (1.0, (-8, -36, 7))], lens=32, target_keys=[(0.0, (0, 22, 4)), (1.0, (4, 22, 4))])
    return sc


def half_arch(o):
    """Delete the lower half of a torus so it reads as an arch."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    mw = o.matrix_world
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if (mw @ v.co).z < o.location.z - 0.05], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()


def arch_row(y, x0, x1, n, h, m_col, m_arch, depth=0.6):
    step = (x1 - x0) / n
    for i in range(n + 1):
        x = x0 + i * step
        add("cyl", (x, y, h / 2), (0.35, 0.35, h / 2), m=m_col, vertices=16)
        add("cube", (x, y, h + 0.15), (0.5, 0.5, 0.15), m=m_col)
    for i in range(n):
        x = x0 + (i + 0.5) * step
        t = add("torus", (x, y, h), (1, 1, 1), (math.radians(90), 0, 0), m=m_arch, major_radius=step / 2 - 0.1, minor_radius=0.22,
                major_segments=48, minor_segments=10)
        half_arch(t)
    add("cube", ((x0 + x1) / 2, y, h + step / 2 + 0.6), ((x1 - x0) / 2 + 0.5, depth, 0.6), m=m_arch)


def shot_durbar():
    sc = reset()
    flat_world((0.9, 0.82, 0.7), 0.25)
    floor_m = bpy.data.materials.new("marble")
    floor_m.use_nodes = True
    nt = floor_m.node_tree
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Color1"].default_value = (0.86, 0.82, 0.74, 1)
    ck.inputs["Color2"].default_value = (0.62, 0.5, 0.38, 1)
    ck.inputs["Scale"].default_value = 30
    nt.links.new(ck.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.15
    add("plane", (0, 0, 0), (40, 40, 1), m=floor_m)
    sand = noisy("sandstone", (0.62, 0.36, 0.24), (0.72, 0.45, 0.3), 3, 0.7, 0.15)
    white = noisy("whitemarble", (0.88, 0.86, 0.8), (0.96, 0.95, 0.92), 4, 0.25, 0.05)
    for y in (-2, 6, 14):
        arch_row(y, -16, 16, 7, 5.0, white, sand)
    add("cube", (0, 22, 7), (20, 0.5, 7), m=sand)                               # back wall
    for x in (-10, 0, 10):
        add("plane", (x, 21.4, 6), (2.2, 1, 3.5), (math.radians(90), 0, 0), m=mat("jali", (1, 0.85, 0.6), emit=(1, 0.8, 0.55), strength=4.0))
    add("cube", (0, 17, 0.6), (5, 3, 0.6), m=white)                              # throne platform
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            add("cyl", (sx_ * 3, 17 + sy_ * 2, 3.5), (0.15, 0.15, 2.9), m=mat("gold", (0.85, 0.65, 0.2), 0.3, 0.8))
    d = add("sphere", (0, 17, 6.4), (3.4, 2.6, 2.0), m=mat("canopy", (0.75, 0.1, 0.12), 0.5))
    add("cube", (0, 17, 6.4), (3.6, 2.8, 0.2), m=mat("gold", (0.85, 0.65, 0.2), 0.3, 0.8))
    add("cube", (0, 16.5, 1.7), (1.4, 1.0, 0.5), m=mat("throne", (0.85, 0.65, 0.2), 0.3, 0.8))
    add("cube", (0, 6, 0.02), (3, 12, 0.02), m=mat("carpet", (0.55, 0.08, 0.1), 0.9))
    light("AREA", (0, 10, 13), 3000, (1, 0.86, 0.65), 18)
    light("AREA", (0, 20, 6), 1200, (1, 0.75, 0.45), 10)
    light("POINT", (0, 15, 5), 500, (1, 0.8, 0.5), 2)
    camera_path([(0.0, (0, -16, 4.5)), (1.0, (0, -8, 3.8))], lens=24, target_keys=[(0.0, (0, 14, 3.5)), (1.0, (0, 16, 3.2))])
    return sc


def shot_court():
    sc = reset()
    flat_world((0.5, 0.5, 0.6), 0.2)
    oak = noisy("oak", (0.22, 0.12, 0.06), (0.36, 0.2, 0.1), 12, 0.6, 0.3)
    add("plane", (0, 0, 0), (30, 30, 1), m=noisy("boards", (0.3, 0.18, 0.1), (0.42, 0.26, 0.14), 20, 0.5, 0.2))
    add("cube", (0, 16, 6), (16, 0.4, 6), m=oak)
    for x in (-16, 16):
        add("cube", (x, 4, 6), (0.4, 14, 6), m=oak)
    for x in (-12, -4, 4, 12):                                                  # panels and leaded windows
        add("plane", (x, 15.5, 7.5), (2.4, 1, 3.4), (math.radians(90), 0, 0), m=mat("window", (0.8, 0.85, 0.9), emit=(0.85, 0.9, 1.0), strength=3))
        for k in range(5):
            add("cube", (x - 2.4 + k * 1.2, 15.4, 7.5), (0.04, 0.05, 3.4), m=mat("lead", (0.1, 0.1, 0.1)))
    add("cube", (0, 13, 0.5), (4, 2.5, 0.5), m=oak)
    add("cube", (0, 13.5, 2.2), (1.2, 0.8, 1.2), m=mat("throne", (0.6, 0.08, 0.1), 0.6))
    add("cube", (0, 14.2, 5.5), (3.5, 0.15, 3.5), m=mat("canopy", (0.65, 0.08, 0.1), 0.7))
    add("cube", (0, 12.5, 9), (3.8, 2.0, 0.25), m=mat("canopy", (0.65, 0.08, 0.1), 0.7))
    add("cube", (0, 5, 0.02), (2.5, 9, 0.02), m=mat("rug", (0.35, 0.1, 0.12), 0.9))
    light("AREA", (0, 10, 11), 2500, (1, 0.9, 0.75), 14)
    light("AREA", (0, 13, 9), 800, (0.85, 0.9, 1.0), 8)
    camera_path([(0.0, (0, -12, 4.5)), (1.0, (2, -7, 4.0))], lens=24, target_keys=[(0.0, (0, 12, 3.5)), (1.0, (0, 13, 3.2))])
    return sc


def ship(x, y, s, heading=0.0, flag=(0.75, 0.1, 0.1)):
    hull = noisy("hull", (0.18, 0.1, 0.05), (0.3, 0.18, 0.08), 5, 0.6, 0.3)
    sail = noisy("sail", (0.86, 0.82, 0.72), (0.95, 0.93, 0.86), 2, 0.9, 0.05)
    h = add("cube", (x, y, 0.8 * s), (4.5 * s, 1.3 * s, 0.9 * s), (0, 0, heading), m=hull)
    md = h.modifiers.new("bev", "BEVEL")
    md.width = 0.5 * s
    md.segments = 3
    add("cube", (x - 3.6 * s * math.cos(heading), y - 3.6 * s * math.sin(heading), 2.0 * s), (1.0 * s, 1.2 * s, 0.6 * s), (0, 0, heading), m=hull)
    for k, mh in ((-2.0, 9), (0.4, 11), (2.6, 8)):
        mx, my = x + k * s * math.cos(heading), y + k * s * math.sin(heading)
        add("cyl", (mx, my, mh / 2 * s), (0.12 * s, 0.12 * s, mh / 2 * s), m=mat("mast", (0.3, 0.2, 0.1)), vertices=8)
        for j in range(2):
            sz = (mh * 0.18 - j * 0.3) * s
            o = add("plane", (mx, my, (mh * 0.45 + j * mh * 0.28) * s), (sz * 1.25, sz, 1), (math.radians(90), 0, heading + math.radians(90)), m=sail)
        add("plane", (mx, my, (mh + 0.4) * s), (0.6 * s, 0.4 * s, 1), (math.radians(90), 0, heading), m=mat("flag", flag, 0.7))
    return h


def shot_ocean():
    sc = reset()
    sky(14, 230, 0.9)
    sun(14, 230, 3.5, (1, 0.85, 0.7))
    bpy.ops.mesh.primitive_plane_add(size=2)
    o = bpy.context.active_object
    oc = o.modifiers.new("ocean", "OCEAN")
    oc.size = 2.0
    oc.spatial_size = 200
    oc.resolution = 12
    oc.wave_scale = 1.2
    oc.choppiness = 1.0
    oc.repeat_x = oc.repeat_y = 2
    oc.time = 1.0
    oc.keyframe_insert("time", frame=1)
    oc.time = 1.0 + SECONDS * 0.6
    oc.keyframe_insert("time", frame=N)
    m = mat("sea", (0.02, 0.12, 0.18), 0.05)
    o.data.materials.append(m)
    smooth(o)
    ships = [ship(-20, 40, 1.6, math.radians(10)), ship(30, 80, 1.3, math.radians(8)), ship(-60, 110, 1.2, math.radians(12))]
    for sh in ships:
        sh.keyframe_insert("location", frame=1)
    camera_path([(0.0, (-60, -40, 10)), (1.0, (-30, -30, 8))], lens=35, target_keys=[(0.0, (-10, 50, 6)), (1.0, (5, 60, 6))])
    return sc


def shot_camp():
    sc = reset()
    flat_world((0.01, 0.015, 0.04), 1.0)
    sun(25, 140, 0.25, (0.6, 0.7, 1.0), 1)
    ground(120, noisy("dirt", (0.08, 0.07, 0.05), (0.14, 0.12, 0.08), 0.5, 0.95, 0.2), 4, 0.3, 0.05)
    canvas = noisy("canvas", (0.62, 0.52, 0.36), (0.74, 0.64, 0.46), 3, 0.9, 0.1)
    rng = random.Random(2)
    for i in range(9):
        x, y = rng.uniform(-40, 40), rng.uniform(20, 60)
        add("cone", (x, y, 2.2), (3, 3, 2.2), (0, 0, rng.uniform(0, 3)), m=canvas, vertices=4)
    t = add("cone", (0, 10, 4.5), (7, 7, 4.5), (0, 0, math.radians(45)), m=canvas, vertices=4)               # the meeting tent
    light("POINT", (0, 8.5, 2.2), 900, (1, 0.6, 0.25), 0.6)
    add("cyl", (6, 2, 0.3), (1.0, 1.0, 0.3), m=mat("fire", (1, 0.4, 0.1), emit=(1, 0.45, 0.12), strength=12), vertices=10)
    light("POINT", (6, 2, 1.5), 1500, (1, 0.5, 0.2), 1.0)
    for _ in range(120):
        d = Vector((rng.uniform(-1, 1), rng.uniform(0.5, 1), rng.uniform(0.15, 1))).normalized() * 600
        add("ico", tuple(d), (0.9, 0.9, 0.9), m=mat("star", (1, 1, 1), emit=(1, 1, 1), strength=rng.uniform(2, 6)), subdivisions=1)
    camera_path([(0.0, (-8, -20, 4)), (1.0, (-2, -14, 3.2))], lens=30, target_keys=[(0.0, (0, 12, 3)), (1.0, (0, 12, 2.8))])
    return sc


def shot_terrain_generic(name, exag, lonlat, back=(-6, -60, 32), fwd=(-2, -38, 20), sun_az=200):
    sc = reset()
    g, size, bbox = terrain(name, exag)
    sky(28, 160, 0.7)
    sun(30, sun_az, 4.0)
    tx, ty = lonlat_to_xy(*lonlat, size, bbox)
    camera_path([(0.0, (tx + back[0], ty + back[1], back[2])), (1.0, (tx + fwd[0], ty + fwd[1], fwd[2]))], lens=30,
                target_keys=[(0.0, (tx, ty + 4, 0)), (1.0, (tx + 2, ty + 10, 0))])
    return sc


def shot_globe_to(lon_from, lat_from, lon_to, lat_to):
    sc = shot_globe()
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.startswith("Sphere"):
            ob.animation_data_clear()
            for f in range(1, N + 1, 2):
                fr = ease((f - 1) / max(1, N - 1))
                lon = lon_from + (lon_to - lon_from) * fr
                lat = lat_from + (lat_to - lat_from) * fr
                ob.rotation_euler = (math.radians(lat), 0, math.radians(-90 - lon))
                ob.keyframe_insert("rotation_euler", frame=f)
    return sc


def ger(x, y, s=1.0):
    felt = noisy("felt", (0.86, 0.83, 0.76), (0.94, 0.92, 0.86), 3, 0.95, 0.1)
    add("cyl", (x, y, 1.0 * s), (2.2 * s, 2.2 * s, 1.0 * s), m=felt, vertices=24)
    add("cone", (x, y, 2.6 * s), (2.35 * s, 2.35 * s, 0.6 * s), m=felt, vertices=24)
    add("cube", (x, y - 2.15 * s, 0.75 * s), (0.45 * s, 0.1 * s, 0.75 * s), m=mat("door", (0.6, 0.15, 0.1), 0.6))
    add("cyl", (x, y, 1.45 * s), (2.23 * s, 2.23 * s, 0.06 * s), m=mat("rope", (0.25, 0.15, 0.08)), vertices=24)


def horse(x, y, s=1.0, heading=0.0, coat=(0.35, 0.2, 0.1)):
    m = noisy("coat", coat, tuple(min(1.0, c * 1.25) for c in coat), 4, 0.7, 0.1)
    ch, sh = math.cos(heading), math.sin(heading)
    body = add("sphere", (x, y, 1.45 * s), (1.15 * s, 0.42 * s, 0.48 * s), (0, 0, heading), m=m, segments=16, ring_count=8)
    smooth(body)
    for dx, dy in ((0.75, 0.22), (0.75, -0.22), (-0.75, 0.22), (-0.75, -0.22)):
        lx, ly = x + (dx * ch - dy * sh) * s, y + (dx * sh + dy * ch) * s
        add("cyl", (lx, ly, 0.55 * s), (0.09 * s, 0.09 * s, 0.55 * s), m=m, vertices=8)
    add("cyl", (x + 1.2 * ch * s, y + 1.2 * sh * s, 1.95 * s), (0.17 * s, 0.17 * s, 0.45 * s), (0, math.radians(35), heading), m=m, vertices=10)
    hd = add("sphere", (x + 1.5 * ch * s, y + 1.5 * sh * s, 2.25 * s), (0.42 * s, 0.17 * s, 0.17 * s), (0, math.radians(25), heading), m=m,
             segments=12, ring_count=6)
    smooth(hd)


def shot_steppe():
    sc = reset()
    sky(30, 210, 0.9)
    sun(30, 210, 3.6)
    ground(260, noisy("steppe", (0.36, 0.42, 0.16), (0.5, 0.52, 0.24), 0.3, 0.95, 0.2), 6, 3.5, 0.015)
    rng = random.Random(6)
    for i in range(9):
        ger(rng.uniform(-30, 30), rng.uniform(20, 55), rng.uniform(0.9, 1.15))
    coats = [(0.35, 0.2, 0.1), (0.12, 0.09, 0.07), (0.55, 0.42, 0.28), (0.7, 0.66, 0.6)]
    for i in range(26):
        horse(rng.uniform(-45, 45), rng.uniform(0, 30), rng.uniform(0.9, 1.1), rng.uniform(0, 6.28), rng.choice(coats))
    for k in range(4):
        add("sphere", (-160 + k * 110, 230, -30), (90, 40, 60), m=noisy("hill", (0.3, 0.36, 0.2), (0.4, 0.44, 0.26), 0.2, 0.95, 0.1),
            segments=24, ring_count=12)
    camera_path([(0.0, (-26, -36, 7)), (1.0, (-6, -32, 6))], lens=30, target_keys=[(0.0, (0, 30, 2)), (1.0, (6, 32, 2))])
    return sc


def dome(x, y, z, r, m):
    o = add("sphere", (x, y, z), (r, r, r * 1.15), m=m, segments=24, ring_count=12)
    smooth(o)
    return o


def shot_city():
    sc = reset()
    sky(26, 240, 0.9)
    sun(26, 240, 3.5, (1, 0.9, 0.75))
    ground(220, noisy("dust", (0.6, 0.5, 0.34), (0.72, 0.62, 0.44), 0.4, 0.95, 0.2), 4, 0.4, 0.05)
    mud = noisy("mudbrick", (0.62, 0.48, 0.3), (0.74, 0.6, 0.4), 2.5, 0.9, 0.3)
    tile = noisy("tile", (0.05, 0.45, 0.55), (0.15, 0.62, 0.7), 6, 0.25, 0.1)
    walls_rect(0, 40, 90, 60, 8, 2.2, mud, mud, bastion=True)
    rng = random.Random(12)
    for _ in range(40):
        x, y = rng.uniform(-38, 38), rng.uniform(16, 64)
        h = rng.uniform(2.5, 5)
        add("cube", (x, y, h / 2), (rng.uniform(2, 4), rng.uniform(2, 4), h / 2), m=mud)
    add("cube", (0, 44, 6), (9, 9, 6), m=mud)
    dome(0, 44, 13.5, 6.5, tile)
    for x in (-22, 18):
        add("cube", (x, 52, 4), (5, 5, 4), m=mud)
        dome(x, 52, 9.5, 4, tile)
    add("cyl", (14, 34, 18), (1.6, 1.6, 18), m=noisy("minaret", (0.66, 0.52, 0.34), (0.78, 0.64, 0.44), 4, 0.8, 0.3), vertices=20)
    add("cyl", (14, 34, 36.6), (2.1, 2.1, 0.6), m=tile, vertices=20)
    add("cone", (14, 34, 38.5), (1.6, 1.6, 1.4), m=tile, vertices=20)
    camera_path([(0.0, (-40, -50, 14)), (1.0, (-14, -44, 11))], lens=30, target_keys=[(0.0, (0, 40, 8)), (1.0, (6, 42, 9))])
    return sc


def shot_hall():
    """Chinese-style imperial hall (generic Yuan-period reconstruction): stone terraces, red columns, hipped golden roof."""
    sc = reset()
    sky(32, 200, 0.9)
    sun(32, 200, 3.5)
    ground(200, noisy("paving", (0.6, 0.58, 0.54), (0.7, 0.68, 0.64), 1.5, 0.8, 0.2))
    stone = noisy("stone", (0.78, 0.76, 0.72), (0.88, 0.86, 0.82), 3, 0.7, 0.2)
    for k, (w, d, h) in enumerate(((44, 26, 1.2), (38, 22, 1.2), (32, 18, 1.2))):
        add("cube", (0, 30, h / 2 + k * 1.2), (w / 2, d / 2, h / 2), m=stone)
    red = mat("red", (0.55, 0.06, 0.05), 0.5)
    for i in range(8):
        for j in range(2):
            add("cyl", (-12.6 + i * 3.6, 23 + j * 12, 3.6 + 4.5), (0.45, 0.45, 4.5), m=red, vertices=16)
    add("cube", (0, 29, 8.0), (13, 6, 4.5), m=mat("wall", (0.6, 0.12, 0.08), 0.6))
    roof = mat("roof", (0.75, 0.55, 0.12), 0.35, 0.3)
    r = add("cube", (0, 29, 15.5), (19, 11, 3.0), m=roof)
    for v in r.data.vertices:
        if v.co.z > 0:
            v.co.x *= 0.45
            v.co.y *= 0.15
    add("cube", (0, 29, 12.6), (20, 12, 0.35), m=roof)
    camera_path([(0.0, (-28, -34, 8)), (1.0, (-8, -28, 7))], lens=30, target_keys=[(0.0, (0, 29, 8)), (1.0, (2, 29, 9))])
    return sc


def shot_storm():
    sc = reset()
    flat_world((0.16, 0.18, 0.22), 1.0)
    sun(20, 230, 0.8, (0.8, 0.85, 0.95), 20)
    bpy.ops.mesh.primitive_plane_add(size=2)
    o = bpy.context.active_object
    oc = o.modifiers.new("ocean", "OCEAN")
    oc.size = 2.0
    oc.spatial_size = 200
    oc.resolution = 12
    oc.wave_scale = 4.0
    oc.choppiness = 1.6
    oc.repeat_x = oc.repeat_y = 2
    oc.time = 1.0
    oc.keyframe_insert("time", frame=1)
    oc.time = 1.0 + SECONDS * 1.2
    oc.keyframe_insert("time", frame=N)
    o.data.materials.append(mat("sea", (0.03, 0.07, 0.09), 0.08))
    smooth(o)
    sh = [ship(-15, 40, 1.4, math.radians(25), (0.2, 0.2, 0.25)), ship(30, 70, 1.2, math.radians(-15), (0.2, 0.2, 0.25))]
    for i, s_ in enumerate(sh):
        z = s_.rotation_euler.z
        for f in range(1, N + 1, 6):
            s_.rotation_euler = (math.radians(8 * math.sin(f / 9 + i)), math.radians(6 * math.sin(f / 7 + i)), z)
            s_.keyframe_insert("rotation_euler", frame=f)
    camera_path([(0.0, (-50, -30, 8)), (1.0, (-30, -24, 7))], lens=35, target_keys=[(0.0, (0, 50, 4)), (1.0, (6, 55, 4))])
    return sc


def pyramid(x, y, base, h, m, rot=0.0):
    o = add("cone", (x, y, h / 2), (base / 1.4142, base / 1.4142, h / 2), (0, 0, math.radians(45) + rot), m=m, vertices=4)
    return o


def frustum(x, y, b0, b1, z0, z1, m):
    o = add("cube", (x, y, (z0 + z1) / 2), (b0 / 2, b0 / 2, (z1 - z0) / 2), m=m)
    k = b1 / b0
    for v in o.data.vertices:
        if v.co.z > 0:
            v.co.x *= k
            v.co.y *= k
    return o


def limestone(name="limestone", c1=(0.78, 0.7, 0.55), c2=(0.88, 0.8, 0.64)):
    return noisy(name, c1, c2, 1.2, 0.9, 0.35)


def palm(x, y, s=1.0):
    trunk = noisy("palmtrunk", (0.32, 0.22, 0.12), (0.42, 0.3, 0.16), 8, 0.9, 0.4)
    leaf = noisy("palmleaf", (0.12, 0.3, 0.08), (0.22, 0.42, 0.12), 3, 0.7, 0.2)
    add("cyl", (x, y, 3.5 * s), (0.22 * s, 0.22 * s, 3.5 * s), (math.radians(4), 0, 0), m=trunk, vertices=8)
    for k in range(7):
        a = k / 7 * 6.283
        add("cone", (x + math.cos(a) * 1.4 * s, y + math.sin(a) * 1.4 * s, 6.8 * s), (0.5 * s, 2.0 * s, 0.12 * s),
            (math.radians(-20), 0, a + math.radians(90)), m=leaf, vertices=4)


def nile_boat(x, y, s=1.0, heading=0.0):
    wood = noisy("reedwood", (0.45, 0.32, 0.16), (0.58, 0.42, 0.22), 4, 0.8, 0.2)
    h = add("cube", (x, y, 0.5 * s), (4 * s, 1.0 * s, 0.45 * s), (0, 0, heading), m=wood)
    for v in h.data.vertices:
        if abs(v.co.x) > 0.6:
            v.co.z += 0.5 * abs(v.co.x)
    add("cyl", (x, y, 4 * s), (0.1 * s, 0.1 * s, 3.6 * s), m=mat("mast", (0.3, 0.2, 0.1)), vertices=6)
    add("plane", (x, y, 4.6 * s), (2.2 * s, 2.6 * s, 1), (math.radians(90), 0, heading), m=noisy("linen", (0.86, 0.82, 0.7), (0.94, 0.9, 0.8), 2, 0.9, 0.05))


def desert_ground(size=400, disp=2.5):
    return ground(size, noisy("sand", (0.72, 0.58, 0.38), (0.84, 0.7, 0.48), 0.25, 0.95, 0.25), 6, disp, 0.012)


def shot_giza():
    sc = reset()
    sky(22, 250, 0.9)
    sun(22, 250, 3.8, (1, 0.88, 0.7))
    desert_ground(500, 3.0)
    ls = limestone()
    pyramid(0, 60, 46, 29, ls)                                                   # Khufu (scaled 1:5)
    pyramid(-40, 95, 43, 28, limestone("ls2", (0.76, 0.66, 0.5), (0.86, 0.76, 0.58)))   # Khafre
    pyramid(-70, 125, 21, 13, limestone("ls3"))                                  # Menkaure
    sx, sy = 25, 30                                                             # the Sphinx (simplified)
    stone = limestone("sphinx", (0.7, 0.58, 0.4), (0.8, 0.68, 0.48))
    add("cube", (sx, sy, 1.6), (2.0, 7.0, 1.6), m=stone)
    add("cube", (sx, sy - 6.2, 3.8), (1.4, 1.2, 1.8), m=stone)
    add("cube", (sx - 0.9, sy - 9.5, 0.6), (0.4, 3.0, 0.6), m=stone)
    add("cube", (sx + 0.9, sy - 9.5, 0.6), (0.4, 3.0, 0.6), m=stone)
    camera_path([(0.0, (70, -70, 14)), (1.0, (45, -55, 11))], lens=30, target_keys=[(0.0, (-10, 70, 14)), (1.0, (-14, 74, 16))])
    return sc


def shot_build():
    """Khufu's pyramid under construction: a truncated pyramid, a straight supply ramp, blocks and sledges."""
    sc = reset()
    sky(28, 230, 0.9)
    sun(28, 230, 3.8, (1, 0.9, 0.72))
    desert_ground(400, 1.5)
    ls = limestone()
    frustum(0, 50, 46, 24, 0, 13, ls)
    ramp = add("cube", (0, 50 - 23 - 30, 6.5), (4.5, 30, 6.5), m=noisy("mudbrick", (0.52, 0.4, 0.26), (0.62, 0.5, 0.34), 1.5, 0.95, 0.3))
    for v in ramp.data.vertices:                                                # slope up towards the pyramid
        if v.co.y < 0:
            v.co.z = -1.0
    rng = random.Random(3)
    blk = limestone("block", (0.8, 0.72, 0.56), (0.9, 0.82, 0.66))
    sled = mat("sledge", (0.4, 0.26, 0.12), 0.8)
    for i in range(10):
        y = -40 + i * 3.4
        z = max(0.4, 13 * (i / 10)) if False else 0.6
        add("cube", (rng.uniform(-14, 14), y - 20, 0.6), (0.9, 0.7, 0.6), m=blk)
    for k in range(6):                                                          # blocks on sledges going up the ramp
        t = k / 6
        y = 50 - 23 - 58 + t * 56
        z = 0.5 + t * 13
        add("cube", (0, y, z + 0.75), (0.9, 0.7, 0.6), m=blk)
        add("cube", (0, y, z + 0.1), (0.8, 1.0, 0.1), m=sled)
    for x in (-30, 30):
        for j in range(5):
            add("cube", (x + rng.uniform(-6, 6), rng.uniform(10, 70), 0.6), (0.9, 0.7, 0.6), m=blk)
    camera_path([(0.0, (-55, -60, 18)), (1.0, (-35, -50, 14))], lens=30, target_keys=[(0.0, (0, 30, 6)), (1.0, (2, 34, 8))])
    return sc


def shot_nile():
    sc = reset()
    sky(18, 250, 0.9)
    sun(18, 250, 3.6, (1, 0.85, 0.65))
    desert_ground(500, 4.0)
    water_plane((0, 40, 0.3), (300, 18, 1), (0.08, 0.22, 0.26))
    green = noisy("fields", (0.18, 0.32, 0.08), (0.3, 0.44, 0.12), 0.5, 0.9, 0.2)
    for yy in (16, 64):
        add("plane", (0, yy, 0.35), (300, 8, 1), m=green)
    rng = random.Random(8)
    for _ in range(40):
        palm(rng.uniform(-120, 120), rng.choice([rng.uniform(12, 20), rng.uniform(60, 68)]), rng.uniform(0.8, 1.2))
    for k in range(4):
        nile_boat(-40 + k * 30, 40 + rng.uniform(-6, 6), rng.uniform(1.0, 1.4), math.radians(rng.uniform(-8, 8)))
    camera_path([(0.0, (-60, -20, 9)), (1.0, (-30, -14, 8))], lens=30, target_keys=[(0.0, (0, 45, 3)), (1.0, (12, 48, 3))])
    return sc


def shot_quarry():
    sc = reset()
    sky(30, 220, 0.9)
    sun(30, 220, 3.8, (1, 0.9, 0.75))
    ls = limestone("quarry", (0.8, 0.72, 0.56), (0.9, 0.82, 0.66))
    desert_ground(300, 1.0)
    for i in range(6):                                                          # stepped quarry faces
        add("cube", (0, 40 + i * 5, 1.5 + i * 1.6), (40, 2.5, 1.5 + i * 1.6), m=ls)
    rng = random.Random(5)
    for _ in range(30):
        add("cube", (rng.uniform(-30, 30), rng.uniform(10, 34), 0.6), (0.9, 0.7, 0.6), (0, 0, rng.uniform(0, 0.4)), m=ls)
    camera_path([(0.0, (-30, -20, 9)), (1.0, (-14, -14, 7))], lens=30, target_keys=[(0.0, (0, 40, 4)), (1.0, (6, 42, 5))])
    return sc


def shot_saqqara():
    """Djoser's step pyramid (left) and Sneferu's Bent Pyramid (right), side by side as the learning curve."""
    sc = reset()
    sky(26, 230, 0.9)
    sun(26, 230, 3.8, (1, 0.88, 0.7))
    desert_ground(500, 2.0)
    ls = limestone()
    steps = [(40, 0, 4), (34, 4, 8), (28, 8, 11.5), (22, 11.5, 14.5), (16, 14.5, 17), (10, 17, 19)]
    for b, z0, z1 in steps:
        o = add("cube", (-40, 70, (z0 + z1) / 2), (b / 2, b * 0.8 / 2, (z1 - z0) / 2), m=ls)
    frustum(40, 75, 40, 20, 0, 14, ls)                                          # bent pyramid: steep lower part
    pyramid(40, 75, 20, 10, ls)
    for o in bpy.data.objects:
        if o.type == "MESH" and abs(o.location.x - 40) < 0.1 and o.location.z > 4 and o.data.vertices and len(o.data.vertices) == 5:
            o.location.z = 14 + 5
    camera_path([(0.0, (0, -60, 14)), (1.0, (0, -46, 12))], lens=28, target_keys=[(0.0, (0, 70, 10)), (1.0, (0, 72, 11))])
    return sc


SHOTS = {"globe": shot_globe, "india": shot_india, "bengal": shot_bengal, "spice": shot_spice, "ocean": shot_ocean, "fort": shot_fort,
         "durbar": shot_durbar, "court": shot_court, "plassey": lambda: shot_plassey(False), "plassey_rain": lambda: shot_plassey(True),
         "camp": shot_camp, "steppe": shot_steppe, "city": shot_city, "hall": shot_hall, "storm": shot_storm,
         "mongolia": lambda: shot_terrain_generic("mongolia", 14.0, (104, 46)),
         "centralasia": lambda: shot_terrain_generic("centralasia", 14.0, (64, 39)),
         "eurasia": lambda: shot_terrain_generic("eurasia", 10.0, (70, 40), back=(-4, -70, 42), fwd=(0, -48, 30)),
         "globe_mongol": lambda: shot_globe_to(20, 20, 104, 46),
         "giza": shot_giza, "build": shot_build, "nile": shot_nile, "quarry": shot_quarry, "saqqara": shot_saqqara,
         "egypt": lambda: shot_terrain_generic("egypt", 12.0, (31.2, 27.5), back=(-4, -66, 34), fwd=(0, -44, 22))}

if __name__ == "__main__":
    sc = SHOTS[SHOT]()
    OUT.mkdir(parents=True, exist_ok=True)
    fs, fe = int(os.environ.get("YTG_FRAME_START", "1")), int(os.environ.get("YTG_FRAME_END", str(N)))
    if STILL:
        fs = fe = STILL
    sc.frame_start, sc.frame_end = fs, fe
    sc.render.filepath = str(OUT / f"{SHOT}_") + "####"
    bpy.ops.render.render(animation=True)
