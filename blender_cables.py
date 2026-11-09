"""Blender 4.2 shots for the undersea cables film (run headless on the render server, CPU Cycles).

  blender -b --factory-startup -P scripts/blender_cables.py -- <shot> <out_dir> [seconds] [samples]
  shots: seabed      slim black deep-sea cable on fine sediment, low lateral tracking, marine snow, depth haze
         crosssection stepped cutaway of a lightweight deep-sea cable: fibres in a steel tube, steel strength wires,
                      copper conductor, polyethylene sheath; the layers slide out in turn while the camera orbits

Accuracy (TeleGeography / ICPC descriptions): deep-water cable about the width of a garden hose (modelled 21 mm), resting on
the seabed; fibres hair-thin inside a small steel tube; a copper layer carries power to the repeaters; black polyethylene
outside. Units are metres. Frames are written as PNG so an interrupted render resumes where it stopped.
"""
import math
import os
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = argv[0], Path(argv[1])
SECONDS = float(argv[2]) if len(argv) > 2 else 6.0
SAMPLES = int(argv[3]) if len(argv) > 3 else 24
STILL = int(argv[4]) if len(argv) > 4 else 0           # >0: render only this frame (look test)
RES = tuple(int(v) for v in argv[5].split("x")) if len(argv) > 5 else (1920, 1080)   # upscaled to 1080p in assembly
FPS = 24
random.seed(7)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 4
    sc.render.threads_mode = "FIXED"
    sc.render.threads = int(os.environ.get("YTG_THREADS", "3"))
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.use_persistent_data = True
    sc.cycles.denoising_prefilter = "FAST"
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, int(SECONDS * FPS)
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.render.use_overwrite = False                     # resume: frames already on disk are skipped
    sc.render.use_placeholder = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    return sc


def mat(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def world(color, strength):
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    return w


def ease(t):
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------------------------------------------- seabed
def seabed(variant="close"):
    sc = reset()
    world((0.014, 0.06, 0.075), 1.0)
    # sediment: a wide plane with gentle noise relief and fine bump
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    ground = bpy.context.object
    mod = ground.modifiers.new("sub", "SUBSURF"); mod.levels = mod.render_levels = 8; mod.subdivision_type = "SIMPLE"
    tex = bpy.data.textures.new("relief", "CLOUDS"); tex.noise_scale = 1.6
    d = ground.modifiers.new("disp", "DISPLACE"); d.texture = tex; d.strength = 0.02
    m = mat("sediment", (0.14, 0.13, 0.11), rough=0.97)      # pale silt (2026-11-09: v1 read as dark tarmac)
    nt = m.node_tree
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 90; noise.inputs["Detail"].default_value = 8
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    ripple = nt.nodes.new("ShaderNodeTexWave"); ripple.inputs["Scale"].default_value = 6; ripple.inputs["Distortion"].default_value = 4
    addh = nt.nodes.new("ShaderNodeMath"); addh.operation = "ADD"
    nt.links.new(noise.outputs["Fac"], addh.inputs[0]); nt.links.new(ripple.outputs["Fac"], addh.inputs[1])
    nt.links.new(addh.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    ground.data.materials.append(m)
    # the cable: 21 mm diameter, resting in a loose curve, slightly sunk into the sediment
    cu = bpy.data.curves.new("cable", "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    pts = [(-7, -0.6, .012), (-4, -0.2, .012), (-1, 0.15, .012), (2, -0.05, .012), (5, 0.35, .012), (8, 0.1, .012)]
    if variant == "repeater":         # the cable runs into the repeater housing's bend restrictors at both ends
        pts = [(-7, -0.3, .012), (-3, -0.05, .012), (-1.5, 0, .02), (-0.7, 0, 0.13), (0.7, 0, 0.13), (1.5, 0, .02), (3, .08, .012), (8, .3, .012)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = co; bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.bevel_depth = 0.0105; cu.bevel_resolution = 6
    cable = bpy.data.objects.new("cable", cu); sc.collection.objects.link(cable)
    cable.data.materials.append(mat("polyethylene", (0.012, 0.012, 0.014), rough=0.38, coat=0.25))
    if variant == "repeater":
        repeater(sc)
    # a few small rocks and a sea star for scale
    rock_m = mat("rock", (0.16, 0.16, 0.15), rough=0.9)
    for i in range(26):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=random.uniform(0.01, 0.05),
                                              location=(random.uniform(-6, 6), random.uniform(-2.5, 2.5), 0.0))
        r = bpy.context.object; r.scale = (1, random.uniform(0.6, 1.3), random.uniform(0.4, 0.8)); r.data.materials.append(rock_m)
    # marine snow: small faintly lit flakes drifting down
    snow_m = mat("snow", (0.8, 0.85, 0.9), rough=0.6, emit=(0.6, 0.75, 0.85), strength=0.6)
    end = sc.frame_end
    for i in range(240):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.0015, 0.004),
                                              location=(random.uniform(-3, 4), random.uniform(-1.2, 1.6), random.uniform(0.05, 1.6)))
        f = bpy.context.object; f.data.materials.append(snow_m)
        z0 = f.location.z
        f.keyframe_insert("location", frame=1)
        f.location.z = z0 - random.uniform(0.05, 0.18); f.location.x += random.uniform(-0.05, 0.05)
        f.keyframe_insert("location", frame=end)
    # light: a cool work-light from above and ahead (as from an ROV), plus a faint warm fill
    bpy.ops.object.light_add(type="SPOT", location=(0.6, -1.6, 2.4))
    key = bpy.context.object; key.data.energy = 900; key.data.spot_size = math.radians(72); key.data.spot_blend = 1.0
    key.data.color = (0.75, 0.9, 1.0); key.rotation_euler = (math.radians(38), 0, math.radians(8))
    bpy.ops.object.light_add(type="AREA", location=(-2.5, 1.5, 1.2))
    fill = bpy.context.object; fill.data.energy = 70; fill.data.color = (1.0, 0.75, 0.5); fill.data.size = 2
    fill.rotation_euler = (math.radians(60), 0, math.radians(-120))
    # camera: low lateral track along the cable, slight push and tilt
    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 32; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.8
    cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    target = bpy.data.objects.new("aim", None); sc.collection.objects.link(target)
    cam_d.dof.focus_object = target
    track = cam.constraints.new("TRACK_TO"); track.target = target; track.track_axis = "TRACK_NEGATIVE_Z"; track.up_axis = "UP_Y"
    moves = {   # variant: [(frame, camera, aim)]
        "close": [(1, (-2.6, -0.34, 0.10), (-1.2, 0.05, 0.01)), (end, (0.9, -0.34, 0.10), (2.1, 0.05, 0.01))],
        "wide": [(1, (-4.2, -1.15, 0.62), (2.5, 0.2, 0.0)), (end, (-3.0, -0.95, 0.48), (3.2, 0.2, 0.0))],
        "pullback": [(1, (-0.6, -0.30, 0.12), (0.6, 0.0, 0.01)), (end, (-2.2, -1.6, 1.7), (0.6, 0.0, 0.0))],
        "repeater": [(1, (-1.9, -1.5, 0.55), (0.0, 0.0, 0.12)), (end, (-0.6, -2.0, 0.38), (0.15, 0.0, 0.12))],
    }[variant]
    for f, c, t in moves:
        cam.location = c; cam.keyframe_insert("location", frame=f)
        target.location = t; target.keyframe_insert("location", frame=f)
    if variant == "pullback":         # the work-light fades as the camera rises: the cable goes back into the dark
        key.data.energy = 900; key.data.keyframe_insert("energy", frame=int(end * 0.35))
        key.data.energy = 60; key.data.keyframe_insert("energy", frame=end)
    # depth haze: the mist pass blends distant ground into dark teal water in the compositor
    sc.view_layers[0].use_pass_mist = True
    sc.world.mist_settings.start = 0.6; sc.world.mist_settings.depth = 8.0 if variant == "wide" else 5.5
    sc.world.mist_settings.falloff = "QUADRATIC"
    sc.use_nodes = True
    nt = sc.node_tree; nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    mix = nt.nodes.new("CompositorNodeMixRGB"); mix.inputs[2].default_value = (0.014, 0.06, 0.075, 1)
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Mist"], mix.inputs[0]); nt.links.new(rl.outputs["Image"], mix.inputs[1]); nt.links.new(mix.outputs[0], comp.inputs[0])
    return sc


# --------------------------------------------------------------------------------------------------------- cross-section
def crosssection():
    sc = reset()
    world((0.004, 0.009, 0.02), 1.0)
    end = sc.frame_end
    layers = [  # name, outer radius (m), colour, roughness, metallic, how far its cut end steps back (m)
        ("sheath", 0.0105, (0.002, 0.002, 0.0025), 0.55, 0.0, 0.00),
        ("copper", 0.0068, (0.80, 0.42, 0.22), 0.25, 1.0, 0.022),
        ("strength_wires", 0.0062, (0.55, 0.56, 0.58), 0.3, 1.0, 0.044),
        ("steel_tube", 0.0024, (0.62, 0.63, 0.65), 0.22, 1.0, 0.066),
    ]
    root = bpy.data.objects.new("cable", None); sc.collection.objects.link(root)
    L = 0.32
    for i, (name, r, col, rough, metal, step) in enumerate(layers):
        m = mat(name, col, rough=rough, metal=metal, coat=0.0)
        if name == "sheath":             # keep it black: weak, tight specular instead of a broad grey sheen (v1 read white)
            bsdf = m.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Specular IOR Level"].default_value = 0.06
        if name == "strength_wires":     # a ring of steel wires around the tube, not a solid layer
            n = 18
            for k in range(n):
                a = 2 * math.pi * k / n
                rr = 0.0040
                bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.00105, depth=L, location=(0, rr * math.cos(a), rr * math.sin(a)),
                                                    rotation=(0, math.radians(90), 0))
                w = bpy.context.object; w.data.materials.append(m); w.parent = root; w["layer"] = i
        else:
            inner = {"sheath": 0.0068, "copper": 0.0050, "steel_tube": 0.0018}[name]
            bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=L, rotation=(0, math.radians(90), 0))
            c = bpy.context.object; c.name = name; c.data.materials.append(m); c.parent = root; c["layer"] = i
            if inner > 0:                # hollow tube: the inner layers show through its cut end
                sol = c.modifiers.new("solid", "SOLIDIFY"); sol.thickness = r - inner; sol.offset = -1
    # eight hair-thin coloured fibres (250 micrometre coated fibre, drawn slightly larger to read on screen)
    fib_cols = [(0.1, 0.3, 0.9), (0.9, 0.5, 0.1), (0.1, 0.7, 0.3), (0.6, 0.35, 0.2), (0.5, 0.5, 0.55), (0.9, 0.9, 0.9), (0.85, 0.1, 0.1), (0.05, 0.05, 0.05)]
    for k, col in enumerate(fib_cols):
        a = 2 * math.pi * k / len(fib_cols)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.00032, depth=L, location=(0, 0.0012 * math.cos(a), 0.0012 * math.sin(a)),
                                            rotation=(0, math.radians(90), 0))
        f = bpy.context.object; f.data.materials.append(mat(f"fibre{k}", col, rough=0.3, emit=(0.6, 0.95, 1.0), strength=0.0)); f.parent = root; f["layer"] = 4
    # stepped reveal: starting flush, each layer's cut end slides back in turn (sheath first, most), so the inner layers
    # end up protruding furthest, like a cable prepared for jointing
    for ob in root.children:
        lay = ob["layer"]
        step = [0.088, 0.066, 0.044, 0.022, 0.0][lay]
        t0 = 1 + int(lay * 0.12 * end)
        t1 = t0 + int(0.35 * end)
        ob.location.x = 0.0
        ob.keyframe_insert("location", index=0, frame=t0)
        ob.location.x = -step
        ob.keyframe_insert("location", index=0, frame=min(t1, end))
    # the fibres' cut ends glow faintly once exposed (light in the glass), in the palette's cool cyan
    for ob in root.children:
        if ob["layer"] == 4:
            b = ob.data.materials[0].node_tree.nodes["Principled BSDF"]
            b.inputs["Emission Strength"].default_value = 0.0; b.inputs["Emission Strength"].keyframe_insert("default_value", frame=int(0.6 * end))
            b.inputs["Emission Strength"].default_value = 1.2; b.inputs["Emission Strength"].keyframe_insert("default_value", frame=end)
    # studio lighting: a cool key, a warm rim, a soft top
    for loc, energy, col, size in [((0.25, -0.25, 0.2), 7, (0.8, 0.9, 1.0), 0.3), ((-0.3, 0.3, 0.12), 6, (1.0, 0.7, 0.45), 0.2), ((0, 0, 0.5), 2.5, (0.7, 0.85, 1.0), 0.6)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object; l.data.energy = energy; l.data.color = col; l.data.size = size
        l.constraints.new("TRACK_TO").target = root
    # camera: slow orbit around the cut end
    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 85; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 11
    cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    aim = bpy.data.objects.new("aim", None); sc.collection.objects.link(aim); aim.location = (0.135, 0, 0)
    cam_d.dof.focus_object = aim
    tr = cam.constraints.new("TRACK_TO"); tr.target = aim; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
    for f, ang in [(1, -35), (end, 25)]:
        a = math.radians(ang)
        cam.location = (0.11 + 0.20 * math.cos(a), 0.20 * math.sin(a) - 0.02, 0.06); cam.keyframe_insert("location", frame=f)
    return sc


def repeater(sc):
    """An optical repeater: a sealed metal pressure housing spliced into the cable, with a tapered bend restrictor at each end
    (proportions after published photos of submarine repeaters; no brand, no dimensions claimed on screen)."""
    body_m = mat("housing", (0.50, 0.44, 0.34), rough=0.42, metal=1.0)
    boot_m = mat("restrictor", (0.03, 0.03, 0.035), rough=0.6)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.14, depth=1.3, location=(0, 0, 0.135), rotation=(0, math.radians(90), 0))
    b = bpy.context.object; b.data.materials.append(body_m)
    bev = b.modifiers.new("bev", "BEVEL"); bev.width = 0.03; bev.segments = 4
    for sgn in (-1, 1):
        for x in (0.45, 0.55):                          # two grooved collars near each end
            bpy.ops.mesh.primitive_torus_add(major_radius=0.141, minor_radius=0.008, location=(sgn * x, 0, 0.135), rotation=(0, math.radians(90), 0))
            bpy.context.object.data.materials.append(body_m)
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.07, radius2=0.017, depth=0.6,
                                        location=(sgn * 0.95, 0, 0.085), rotation=(0, sgn * math.radians(90 - 9), 0))
        bpy.context.object.data.materials.append(boot_m)


def pulses():
    """Light in glass: a bundle of coated fibres seen in macro, the glass core of each carrying bright pulses that race along
    it (an illustration of on-off light signals, not a measured waveform)."""
    sc = reset()
    world((0.002, 0.004, 0.01), 1.0)
    end = sc.frame_end
    coat_cols = [(0.08, 0.25, 0.8), (0.85, 0.45, 0.08), (0.08, 0.6, 0.25), (0.75, 0.75, 0.78), (0.8, 0.08, 0.08)]
    spots = [(0, 0), (0.011, 0.004), (-0.012, 0.006), (0.006, -0.011), (-0.007, -0.012)]
    for k, col in enumerate(coat_cols):
        y, z = spots[k]
        # coloured coating, cut open along the top so the glass and its glowing core read (a cut-away)
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.0042, depth=3.0, location=(0, y, z), rotation=(0, math.radians(90), 0))
        c = bpy.context.object; c.data.materials.append(mat(f"coat{k}", col, rough=0.35, coat=0.3))
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, y, z + 0.0052)); box = bpy.context.object
        box.scale = (2.6, 0.0075, 0.0058); box.hide_render = True
        cut = c.modifiers.new("cut", "BOOLEAN"); cut.object = box; cut.operation = "DIFFERENCE"
        glass = mat(f"glass{k}", (0.9, 0.95, 1.0), rough=0.04)
        glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.0031, depth=3.02, location=(0, y, z), rotation=(0, math.radians(90), 0))
        bpy.context.object.data.materials.append(glass)
        core = mat(f"core{k}", (0.0, 0.0, 0.0), rough=0.5, emit=(0.45, 0.88, 1.0), strength=1.0)
        nt = core.node_tree; b = nt.nodes["Principled BSDF"]
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        wave = nt.nodes.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 3.0 + 0.6 * k; wave.inputs["Distortion"].default_value = 0.0
        ramp = nt.nodes.new("ShaderNodeValToRGB"); el = ramp.color_ramp.elements
        el[0].position, el[0].color = 0.80, (0, 0, 0, 1)
        el[1].position, el[1].color = 0.97, (1, 1, 1, 1)
        gain = nt.nodes.new("ShaderNodeMath"); gain.operation = "MULTIPLY"; gain.inputs[1].default_value = 22.0
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
        nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs[0], gain.inputs[0]); nt.links.new(gain.outputs[0], b.inputs["Emission Strength"])
        loc = mp.inputs["Location"]
        loc.default_value[0] = 0.1 * k; loc.keyframe_insert("default_value", index=0, frame=1)
        loc.default_value[0] = 0.1 * k - 1.6; loc.keyframe_insert("default_value", index=0, frame=end)
        for fc in nt.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.0009, depth=3.03, location=(0, y, z), rotation=(0, math.radians(90), 0))
        bpy.context.object.data.materials.append(core)
    for loc, energy, col, size in [((0.05, -0.08, 0.06), 1.5, (0.75, 0.88, 1.0), 0.08), ((-0.08, 0.06, 0.05), 0.8, (1.0, 0.7, 0.5), 0.06)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object; l.data.energy = energy; l.data.color = col; l.data.size = size
        l.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 85; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 11
    cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    aim = bpy.data.objects.new("aim", None); sc.collection.objects.link(aim); cam_d.dof.focus_object = aim
    tr = cam.constraints.new("TRACK_TO"); tr.target = aim; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
    for f, cx, ax in [(1, -0.16, -0.02), (end, -0.06, 0.07)]:
        cam.location = (cx - 0.08, -0.13, 0.07); cam.keyframe_insert("location", frame=f)
        aim.location = (ax, 0, 0.002); aim.keyframe_insert("location", frame=f)
    sc.use_nodes = True                                 # a soft glow around the light, as a lens sees it
    nt = sc.node_tree; nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers"); gl = nt.nodes.new("CompositorNodeGlare")
    gl.glare_type = "FOG_GLOW"; gl.quality = "HIGH"; gl.threshold = 2.0; gl.size = 6
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"]); nt.links.new(gl.outputs["Image"], comp.inputs["Image"])
    return sc


if __name__ == "__main__":
    scene = {"seabed": seabed, "seabed_wide": lambda: seabed("wide"), "seabed_pullback": lambda: seabed("pullback"),
             "repeater": lambda: seabed("repeater"), "crosssection": crosssection, "pulses": pulses}[SHOT]()
    OUT.mkdir(parents=True, exist_ok=True)
    if STILL > 0:                                       # test still: render one frame only
        scene.frame_set(STILL)
        scene.render.filepath = str(OUT / f"test_{SHOT}_{STILL:04d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        if os.environ.get("YTG_FRAME_START"):          # render one chunk of the shot (parallel GitHub runners)
            scene.frame_start = int(os.environ["YTG_FRAME_START"])
            scene.frame_end = min(scene.frame_end, int(os.environ["YTG_FRAME_END"]))
        scene.render.filepath = str(OUT / "f_")
        bpy.ops.render.render(animation=True)
