"""Three Gorges 3D shots (Blender 4.2, Cycles CPU, headless on GitHub runners).

  blender -b --factory-startup -P blender_gorges.py -- <shot> <out_dir> <seconds> <samples> <still|0> <WxH> <terrain_dir>

Terrain: scripts/gorges_terrain.py (Terrain Tiles = SRTM, Feb 2000: the river BEFORE the reservoir), procedural colour.
Heights are exaggerated x1.5 (stated on screen: "Relief exaggerated"). The dam is a simplified block at the real site
(Sandouping, 30.823 N 111.003 E), crest 185 m, about 2.3 km long. Water levels are real: old river about 62 m (from the
DEM), flood-season limit 145 m, normal pool 175 m.

Shots
  gorge_rise    low flight down the gorge while the water rises from the old river to 175 m (the "stopping the river" shot)
  gorge_full    high oblique flight along the full reservoir towards the dam, golden hour
  dam_approach  from the reservoir towards the dam wall at full pool, the river far below on the other side
  ba_before     static view up the gorge, old river (2000)       (still; pair with ba_after for a wipe / thumbnail)
  ba_after      the same camera at 175 m
  flood_cycle   the same camera: 175 m -> 145 m (flood season) -> 175 m, with level labels added in 2D
"""
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = argv[0], Path(argv[1])
SECONDS = float(argv[2]) if len(argv) > 2 else 8.0
SAMPLES = int(argv[3]) if len(argv) > 3 else 24
STILL = int(argv[4]) if len(argv) > 4 else 0
RES = tuple(int(v) for v in argv[5].split("x")) if len(argv) > 5 else (1920, 1080)
TERRAIN = Path(argv[6]) if len(argv) > 6 else Path("terrain")
FPS = 24
N = max(1, int(SECONDS * FPS))
EXAG = 1.5
OLD_RIVER, FLOOD_LIMIT, FULL_POOL, CREST = 62.0, 145.0, 175.0, 185.0
DAM = (111.003, 30.823)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 4
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.render.threads_mode = "FIXED"
    sc.render.threads = int(os.environ.get("YTG_THREADS", "4"))
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.use_persistent_data = True
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, N
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    return sc


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Geo:
    """lon/lat/metres <-> scene units (100 units across the region)."""
    def __init__(self, name):
        self.meta = json.loads((TERRAIN / f"{name}.json").read_text())
        self.lon0, self.lat0, self.lon1, self.lat1 = self.meta["bbox"]
        self.width_km = (self.lon1 - self.lon0) * self.meta["km_per_deg"]
        self.height_km = (self.lat1 - self.lat0) * 111.32
        self.sx, self.sy = 100.0, 100.0 * self.height_km / self.width_km
        self.upm = self.sx / (self.width_km * 1000)                    # scene units per metre (horizontal)
        self.min_m = self.meta["min_m"]

    def z(self, metres):
        return (metres - self.min_m) * self.upm * EXAG

    def xy(self, lon, lat):
        return ((lon - self.lon0) / (self.lon1 - self.lon0) - 0.5) * self.sx, ((lat - self.lat0) / (self.lat1 - self.lat0) - 0.5) * self.sy

    def p(self, lon, lat, metres):
        return Vector((*self.xy(lon, lat), self.z(metres)))

    def river(self, frac):
        """Point on the river centreline at a fraction 0..1 from west to east: (lon, lat, metres)."""
        r = self.meta["river"]
        i = frac * (len(r) - 1)
        a, b = r[int(i)], r[min(len(r) - 1, int(i) + 1)]
        f = i - int(i)
        return [a[k] + (b[k] - a[k]) * f for k in range(3)]


def terrain(g, name, sub=1400):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=sub, y_subdivisions=int(sub * g.sy / g.sx), size=1)
    o = bpy.context.active_object
    o.scale = (g.sx, g.sy, 1)
    bpy.ops.object.transform_apply(scale=True)
    img = bpy.data.images.load(str(TERRAIN / f"{name}_height.png"))
    img.colorspace_settings.name = "Non-Color"
    tex = bpy.data.textures.new("h", "IMAGE")
    tex.image = img
    tex.extension = "EXTEND"
    md = o.modifiers.new("disp", "DISPLACE")
    md.texture = tex
    md.texture_coords = "UV"
    md.mid_level = 0.0
    md.strength = 6553.5 * g.upm * EXAG                                    # png 0..65535 = 0..6553.5 m above min
    for pl in o.data.polygons:
        pl.use_smooth = True
    m = bpy.data.materials.new("terrain")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    ic = nt.nodes.new("ShaderNodeTexImage")
    ic.image = bpy.data.images.load(str(TERRAIN / f"{name}_color.png"))
    ic.extension = "EXTEND"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["UV"], ic.inputs["Vector"])
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = 1.1
    nt.links.new(ic.outputs["Color"], hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    nz = nt.nodes.new("ShaderNodeTexNoise")                                # fine canopy grain
    nz.inputs["Scale"].default_value = 900.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    o.data.materials.append(m)
    return o


def water_material(name="water"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.11, 0.17, 0.13, 1)          # silty green Yangtze water
    b.inputs["Roughness"].default_value = 0.07
    b.inputs["IOR"].default_value = 1.33
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 140.0
    wv.inputs["Distortion"].default_value = 6.0
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 300.0
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "ADD"
    nt.links.new(wv.outputs["Fac"], mx.inputs[0])
    nt.links.new(nz.outputs["Fac"], mx.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.06
    nt.links.new(mx.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def plane(name, x0, x1, y0, y1, z, mat):
    bpy.ops.mesh.primitive_plane_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, z))
    o = bpy.context.active_object
    o.name = name
    o.scale = (x1 - x0, y1 - y0, 1)
    o.data.materials.append(mat)
    return o


def dam(g):
    """Simplified gravity dam across the river at Sandouping: about 2.3 km long, crest 185 m, pale concrete."""
    r = g.meta["river"]
    i = min(range(len(r)), key=lambda k: abs(r[k][0] - DAM[0]))
    a, b = r[max(0, i - 3)], r[min(len(r) - 1, i + 3)]
    ang = math.atan2((b[1] - a[1]) * 111.32, (b[0] - a[0]) * g.meta["km_per_deg"])  # river direction
    base = g.z(OLD_RIVER - 10)
    top = g.z(CREST)
    length = 2.3 * 1000 * g.upm
    thick = 0.12 * 1000 * g.upm
    x, y = g.xy(*DAM)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, (base + top) / 2))
    o = bpy.context.active_object
    o.name = "dam"
    o.scale = (thick, length, top - base)
    o.rotation_euler = (0, 0, ang)
    m = bpy.data.materials.new("concrete")
    m.use_nodes = True
    bb = m.node_tree.nodes["Principled BSDF"]
    bb.inputs["Base Color"].default_value = (0.62, 0.61, 0.57, 1)
    bb.inputs["Roughness"].default_value = 0.8
    o.data.materials.append(m)
    return o, x


def sky(sun_el, sun_rot, strength=1.0):
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    st = nt.nodes.new("ShaderNodeTexSky")
    st.sky_type = "NISHITA"
    st.sun_elevation = math.radians(sun_el)
    st.sun_rotation = math.radians(sun_rot)
    st.dust_density = 2.5
    st.air_density = 1.2
    st.sun_disc = False
    nt.links.new(st.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.2 * strength
    bpy.ops.object.light_add(type="SUN")
    s = bpy.context.active_object
    s.data.energy = 3.2
    s.data.color = (1.0, 0.86, 0.68) if sun_el < 20 else (1.0, 0.95, 0.88)
    s.data.angle = math.radians(1.5)
    s.rotation_euler = (math.radians(90 - sun_el), 0, math.radians(sun_rot + 180))


def haze(start, depth, color=(0.62, 0.68, 0.74)):
    """Aerial perspective from the mist pass (cheap, no volumes)."""
    sc = bpy.context.scene
    sc.view_layers[0].use_pass_mist = True
    sc.world.mist_settings.start = start
    sc.world.mist_settings.depth = depth
    sc.world.mist_settings.falloff = "QUADRATIC"
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    mix = nt.nodes.new("CompositorNodeMixRGB")
    mix.inputs[2].default_value = (*color, 1)
    mul = nt.nodes.new("CompositorNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.75
    nt.links.new(rl.outputs["Mist"], mul.inputs[0])
    nt.links.new(mul.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(rl.outputs["Image"], mix.inputs[1])
    out = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(mix.outputs["Image"], out.inputs["Image"])


def camera(keys, target_keys, lens=24):
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.lens = lens
    cam.data.clip_start = 0.01
    cam.data.clip_end = 400
    bpy.context.scene.camera = cam
    bpy.ops.object.empty_add(location=target_keys[0][1])
    tgt = bpy.context.active_object
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    for f in range(1, N + 1):
        fr = (f - 1) / max(1, N - 1)
        cam.location = interp(keys, fr)
        tgt.location = interp(target_keys, fr)
        cam.keyframe_insert("location", frame=f)
        tgt.keyframe_insert("location", frame=f)
    return cam


def interp(keys, fr):
    if fr <= keys[0][0]:
        return Vector(keys[0][1])
    for (a, pa), (b, pb) in zip(keys, keys[1:]):
        if a <= fr <= b:
            return Vector(pa).lerp(Vector(pb), ease((fr - a) / max(1e-6, b - a)))
    return Vector(keys[-1][1])


def animate_level(obj, g, levels):
    """levels: [(frac, metres)] eased between keys."""
    for f in range(1, N + 1):
        fr = (f - 1) / max(1, N - 1)
        lv = levels[0][1]
        for (a, la), (b, lb) in zip(levels, levels[1:]):
            if a <= fr <= b:
                lv = la + (lb - la) * ease((fr - a) / max(1e-6, b - a))
            elif fr > b:
                lv = lb
        obj.location.z = g.z(lv)
        obj.keyframe_insert("location", index=2, frame=f)


def scene(name="gorge"):
    g = Geo(name)
    terrain(g, name)
    wm = water_material()
    d, dam_x = dam(g)
    up = plane("reservoir", -g.sx / 2, dam_x, -g.sy / 2, g.sy / 2, g.z(FULL_POOL), wm)
    plane("river_below", dam_x - 0.5, g.sx / 2, -g.sy / 2, g.sy / 2, g.z(OLD_RIVER + 4), wm)
    return g, up


def above_river(g, frac, metres_above, side=0.0):
    lon, lat, h = g.river(frac)
    v = g.p(lon, lat, max(h, OLD_RIVER) + metres_above)
    v.y += side
    return v


def shot():
    reset()
    g, up = scene()
    if SHOT == "gorge_rise":
        sky(14, 250)
        haze(2, 60)
        cam = [(0.0, above_river(g, 0.50, 420, 0.25)), (1.0, above_river(g, 0.56, 330, 0.15))]
        tgt = [(0.0, above_river(g, 0.60, 60)), (1.0, above_river(g, 0.66, 60))]
        camera(cam, tgt, lens=22)
        animate_level(up, g, [(0.0, OLD_RIVER + 3), (0.15, OLD_RIVER + 3), (0.85, FULL_POOL), (1.0, FULL_POOL)])
    elif SHOT == "gorge_full":
        sky(9, 255)
        haze(3, 80)
        camera([(0.0, above_river(g, 0.30, 1500, -1.5)), (1.0, above_river(g, 0.50, 1300, -1.2))],
               [(0.0, above_river(g, 0.62, 100)), (1.0, above_river(g, 0.82, 100))], lens=28)
    elif SHOT == "dam_approach":
        sky(12, 260)
        haze(1, 40)
        dx, dy = g.xy(*DAM)
        dz = g.z(CREST)
        camera([(0.0, Vector((dx - 9, dy + 1.5, dz + 0.9))), (1.0, Vector((dx - 3.2, dy + 0.6, dz + 0.45)))],
               [(0.0, Vector((dx, dy, dz - 0.1))), (1.0, Vector((dx + 1.5, dy - 0.2, g.z(OLD_RIVER))))], lens=26)
    elif SHOT in ("ba_before", "ba_after", "flood_cycle"):
        sky(16, 245)
        haze(2, 70)
        c = above_river(g, 0.42, 650, 0.45)
        t = above_river(g, 0.52, 80)
        camera([(0.0, c), (1.0, c + Vector((0.6, -0.05, -0.02)))], [(0.0, t), (1.0, t + Vector((0.6, 0, 0)))], lens=24)
        if SHOT == "ba_before":
            animate_level(up, g, [(0.0, OLD_RIVER + 3), (1.0, OLD_RIVER + 3)])
        elif SHOT == "ba_after":
            animate_level(up, g, [(0.0, FULL_POOL), (1.0, FULL_POOL)])
        else:
            animate_level(up, g, [(0.0, FULL_POOL), (0.1, FULL_POOL), (0.45, FLOOD_LIMIT), (0.6, FLOOD_LIMIT), (0.95, FULL_POOL), (1.0, FULL_POOL)])
    else:
        raise SystemExit(f"unknown shot {SHOT}")
    render()


def render():
    sc = bpy.context.scene
    OUT.mkdir(parents=True, exist_ok=True)
    s = int(os.environ.get("YTG_FRAME_START", "1"))
    e = int(os.environ.get("YTG_FRAME_END", str(N)))
    frames = [STILL] if STILL else range(s, e + 1)
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = str(OUT / f"{SHOT}_{f:04d}.png")
        bpy.ops.render.render(write_still=True)


shot()
