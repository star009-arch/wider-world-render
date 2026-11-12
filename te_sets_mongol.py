"""Tiny Empires ep. 'How the Mongols Conquered Almost Everything': 3D background plates (empty, lit sets; 2D characters go on top).

Loaded by blender_te.py (exec in its namespace, so N, FPS, add, mat, noisy, light, camera_path, exposure, _ph_files, _fetch,
TEXDIR, reset ... are available). Source of truth: projects/tiny-empires/visual_bibles/05_mongol_empire_1160-1368.md.
Everything is CC0: Poly Haven photo-scanned textures and HDRI skies (downloaded and cached at render time) + procedural shaders.

Shots (camera looks roughly north, +Y; lower third kept as open ground for the characters)
  m_steppe_dawn  Mongolian steppe at dawn: rolling grass, braided river, a kuriyen ring of white felt gers (Rubruck's taller
                 domed roofs, felt door flaps facing south), a great ger on a 22-ox cart, box carts, ponies, sheep, smoke, mountains
  m_ger_inside   inside an elite ger: khana lattice, roof poles to the crown ring, sun shaft, open hearth with tripod, felt,
                 carpets, painted chests, the master's seat at the north with felt ongghot idols
  m_karakorum    Karakorum c. 1254: low rammed-earth wall, green-glazed timber hall on a brick platform, Chinese and Muslim
                 quarters, mosque, kilns, turtle stele, many gers outside the walls
  m_zhongdu      Jin Zhongdu 1215: battered rammed-earth wall with horse-face bastions, brick-faced gate with barbican and a
                 Jin-style gate tower (big brackets, grey tile, green ridges), Liao/Jin brick pagoda, moat, traction trebuchets
  m_bukhara      Bukhara 1220: the Kalyan minaret (banded buff brick, one thin turquoise band), the burning Friday mosque,
                 the Ark citadel on its mound, mud-brick houses, bare winter trees. No tiled domes.
  m_mohi         the Sajo at Mohi, April 1241: spring meadow, timber bridge, willows in first leaf, Romanesque church and timber
                 village, King Bela's wagon-fort camp
  m_baghdad      Baghdad 1258 from the west bank: the Tigris, Mustansiriya-style river facade, plain brick domes and a muqarnas
                 cone dome, minarets, the al-Mustazhir wall, a bridge of boats, boats, palm groves, smoke of the siege
  m_hakata       Hakata Bay 1281: the Genko Borui stone wall along the beach, black pines, stormy sea breaking on the shore,
                 islands and the invasion fleet on the horizon
  m_dadu_hall    Kublai's audience hall at Dadu: red columns with gilt dragons, big painted brackets, coffered ceiling, throne
                 dais, fur and brocade hangings, felt carpets; yellow/green glazed roofs seen through the rear doors
  m_caravan      Silk Road: Bactrian camel caravan crossing gravel desert below snow mountains, a yam relay station
"""
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils import noise as mg_noise

MG_M = {}          # material cache (one shot per Blender process)
MG_T = {}          # creature mesh templates
MG_IMG = {}


# ============================================================================================ small utilities
def mg_link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mg_ss(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))) if e1 != e0 else (1.0 if x >= e1 else 0.0)
    return t * t * (3 - 2 * t)


def mg_fbm(x, y, octaves=4, seed=0.0):
    s = a = 0.0
    amp, f = 1.0, 1.0
    for i in range(octaves):
        s += amp * mg_noise.noise(Vector((x * f, y * f, seed + i * 7.31)))
        a += amp
        amp *= 0.5
        f *= 2.03
    return s / a


def mg_ridge(x, y, octaves=5, seed=0.0):
    s = a = 0.0
    amp, f = 1.0, 1.0
    for i in range(octaves):
        n = 1.0 - abs(mg_noise.noise(Vector((x * f, y * f, seed + i * 3.7))))
        s += amp * n * n
        a += amp
        amp *= 0.5
        f *= 2.1
    return s / a


def _try(obj, **kw):
    for k, v in kw.items():
        try:
            setattr(obj, k, v)
        except Exception as e:                                                  # API differences between versions
            print("mg: cannot set", k, e)


class MgB:
    """Accumulates primitives into one bmesh -> one object (fast, few objects)."""

    def __init__(self):
        self.bm = bmesh.new()

    @staticmethod
    def _mtx(loc, rot=(0, 0, 0), scale=(1, 1, 1)):
        return Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))

    def box(self, loc, half, rot=(0, 0, 0)):
        bmesh.ops.create_cube(self.bm, size=2.0, matrix=self._mtx(loc, rot, half))

    def cyl(self, loc, r, hh, seg=12, r2=None, rot=(0, 0, 0), scale=(1, 1, 1)):
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2,
                              depth=2 * hh, matrix=self._mtx(loc, rot, scale))

    def ico(self, loc, r, scale=(1, 1, 1), sub=2, rot=(0, 0, 0)):
        bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=r, matrix=self._mtx(loc, rot, scale))

    def seg(self, a, b, r, r2=None, n=6):
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-4:
            return
        q = d.normalized().to_track_quat("Z", "Y")
        M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=n, radius1=r, radius2=r if r2 is None else r2,
                              depth=d.length, matrix=M)

    def poly(self, pts, r, r2=None, n=6):
        r2 = r if r2 is None else r2
        k = max(1, len(pts) - 1)
        for i in range(len(pts) - 1):
            self.seg(pts[i], pts[i + 1], r + (r2 - r) * i / k, r + (r2 - r) * (i + 1) / k, n)

    def quads(self, verts, faces):
        vs = [self.bm.verts.new(v) for v in verts]
        for f in faces:
            try:
                self.bm.faces.new([vs[i] for i in f])
            except ValueError:
                pass

    def lathe(self, prof, seg=24, loc=(0, 0, 0), a0=0.0, a1=None):
        closed = a1 is None
        n = seg if closed else seg + 1
        span = 2 * math.pi if closed else (a1 - a0)
        verts = [(loc[0] + r * math.cos(a0 + span * j / seg), loc[1] + r * math.sin(a0 + span * j / seg), loc[2] + z)
                 for (r, z) in prof for j in range(n)]
        faces = []
        for i in range(len(prof) - 1):
            for j in range(seg):
                j2 = (j + 1) % n if closed else j + 1
                faces.append((i * n + j, i * n + j2, (i + 1) * n + j2, (i + 1) * n + j))
        self.quads(verts, faces)

    def frustum(self, loc, bx, by, tx, ty, h, rot=0.0):
        c, s = math.cos(rot), math.sin(rot)

        def P(x, y, z):
            return (loc[0] + x * c - y * s, loc[1] + x * s + y * c, loc[2] + z)
        v = [P(-bx, -by, 0), P(bx, -by, 0), P(bx, by, 0), P(-bx, by, 0), P(-tx, -ty, h), P(tx, -ty, h), P(tx, ty, h), P(-tx, ty, h)]
        self.quads(v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def gable(self, loc, hx, hy, h, ov=0.3, rot=0.0):
        """Gable roof, ridge along local x."""
        c, s = math.cos(rot), math.sin(rot)

        def P(x, y, z):
            return (loc[0] + x * c - y * s, loc[1] + x * s + y * c, loc[2] + z)
        x, y = hx + ov, hy + ov
        v = [P(-x, -y, 0), P(x, -y, 0), P(x, y, 0), P(-x, y, 0), P(-x, 0, h), P(x, 0, h)]
        self.quads(v, [(0, 1, 5, 4), (2, 3, 4, 5), (3, 0, 4), (1, 2, 5), (0, 3, 2, 1)])

    def finish(self, name, m=None, smooth=False, loc=None, rot=0.0):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        if m is not None:
            me.materials.append(m)
        if smooth:
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        ob = mg_link(bpy.data.objects.new(name, me))
        if loc is not None:
            ob.location = loc
        if rot:
            ob.rotation_euler = (0, 0, rot)
        return ob


def mg_mesh(name, verts, faces, m=None, smooth=True, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        lv = [0] * len(me.loops)
        me.loops.foreach_get("vertex_index", lv)
        flat = []
        for vi in lv:
            flat.extend(uvs[vi])
        uvl.data.foreach_set("uv", flat)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if m is not None:
        me.materials.append(m)
    return mg_link(bpy.data.objects.new(name, me))


def mg_terrain(name, half, n, hfn, m, cx=0.0, cy=0.0, p=2.2, wfn=None, halfy=None):
    """Height-field grid, dense near (cx, cy) and coarse far away (so mountains 5 km out stay cheap)."""
    halfy = halfy or half
    ts = [2 * i / (n - 1) - 1 for i in range(n)]
    xs = [cx + half * math.copysign(abs(t) ** p, t) for t in ts]
    ys = [cy + halfy * math.copysign(abs(t) ** p, t) for t in ts]
    verts = [(x, y, hfn(x, y)) for y in ys for x in xs]
    faces = [(j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i) for j in range(n - 1) for i in range(n - 1)]
    ob = mg_mesh(name, verts, faces, m, True)
    if wfn:
        vg = ob.vertex_groups.new(name="dens")
        buckets = {}
        for i, (x, y, z) in enumerate(verts):
            w = round(max(0.0, min(1.0, wfn(x, y))) * 20) / 20
            if w > 0:
                buckets.setdefault(w, []).append(i)
        for w, idx in buckets.items():
            vg.add(idx, w, "REPLACE")
    return ob


# ============================================================================================ node helpers
def _c4(c):
    return tuple(c) + (1.0,) if len(c) == 3 else tuple(c)


def _in(nt, sock, v):
    if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, sock)
    elif isinstance(v, (tuple, list)):
        try:
            n = len(sock.default_value)
        except TypeError:
            n = 1
        sock.default_value = _c4(v) if (len(v) == 3 and n == 4) else tuple(v)
    else:
        sock.default_value = v


def _node(nt, kind, inputs=None, **props):
    nd = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(nd, k, v)
    for k, v in (inputs or {}).items():
        _in(nt, nd.inputs[k], v)
    return nd


def _math(nt, op, a, b=0.0, c=None, clamp=False):
    nd = _node(nt, "ShaderNodeMath", operation=op, use_clamp=clamp)
    _in(nt, nd.inputs[0], a)
    _in(nt, nd.inputs[1], b)
    if c is not None:
        _in(nt, nd.inputs[2], c)
    return nd.outputs[0]


def _mix(nt, fac, a, b, blend="MIX"):
    nd = _node(nt, "ShaderNodeMixRGB", blend_type=blend)
    _in(nt, nd.inputs["Fac"], fac)
    _in(nt, nd.inputs["Color1"], a)
    _in(nt, nd.inputs["Color2"], b)
    return nd.outputs["Color"]


def _noise(nt, vec, scale, detail=4.0, rough=0.55):
    nd = _node(nt, "ShaderNodeTexNoise", {"Scale": scale, "Detail": detail, "Roughness": rough})
    if vec is not None:
        nt.links.new(vec, nd.inputs["Vector"])
    return nd.outputs["Fac"]


def _ramp(nt, fac, stops):
    nd = nt.nodes.new("ShaderNodeValToRGB")
    els = nd.color_ramp.elements
    els[0].position = stops[0][0]
    els[0].color = _c4(stops[0][1])
    els[1].position = stops[-1][0]
    els[1].color = _c4(stops[-1][1])
    for p, c in stops[1:-1]:
        e = els.new(p)
        e.color = _c4(c)
    _in(nt, nd.inputs["Fac"], fac)
    return nd.outputs["Color"]


def _maprange(nt, v, a, b, c=0.0, d=1.0, smooth=True):
    nd = _node(nt, "ShaderNodeMapRange", {"From Min": a, "From Max": b, "To Min": c, "To Max": d},
               interpolation_type="SMOOTHSTEP" if smooth else "LINEAR")
    _in(nt, nd.inputs["Value"], v)
    return nd.outputs["Result"]


def _band(nt, v, lo, hi):
    return _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", v, lo), _math(nt, "LESS_THAN", v, hi))


def _pos(nt):
    return nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]


def _tc(nt, out="Object"):
    return nt.nodes.new("ShaderNodeTexCoord").outputs[out]


def _sep(nt, vec):
    nd = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(vec, nd.inputs[0])
    return nd.outputs


def _mnew(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes["Principled BSDF"]


def _bump(nt, b, h, strength=0.2, dist=0.03):
    bp = _node(nt, "ShaderNodeBump", {"Strength": strength, "Distance": dist})
    _in(nt, bp.inputs["Height"], h)
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])


# ============================================================================================ Poly Haven layers (anti-tiling)
def _img(path, color=True):
    key = str(path)
    if key not in MG_IMG:
        im = bpy.data.images.load(key, check_existing=True)
        if not color:
            im.colorspace_settings.name = "Non-Color"
        MG_IMG[key] = im
    return MG_IMG[key]


def _ph_maps(asset, res="1k"):
    f = _ph_files(asset)
    out = {}
    for key, k in (("Diffuse", "diff"), ("Rough", "rough")):
        try:
            out[k] = _fetch(f[key][res]["jpg"]["url"], TEXDIR / asset / f"{k}_{res}.jpg")
        except Exception:
            out[k] = None
    if not out["diff"]:
        raise RuntimeError("no diffuse for " + asset)
    return out


def _ph_layer(nt, asset, scale, tint=None, res="1k", anti=True, macro=0.22, pos=None):
    """Box-projected world-space texture; two rotated lookups blended by noise hide the repeat; slow macro variation on top."""
    maps = _ph_maps(asset, res)
    pos = pos or _pos(nt)
    vecs = []
    for s, rz, off in ((scale, 0.0, (0, 0, 0)), (scale * 0.43, 0.9, (0.37, 0.71, 0.19)))[: 2 if anti else 1]:
        mp = _node(nt, "ShaderNodeMapping", {"Scale": (s, s, s), "Rotation": (0, 0, rz), "Location": off})
        nt.links.new(pos, mp.inputs["Vector"])
        vecs.append(mp.outputs["Vector"])

    def tex(path, color, v):
        nd = nt.nodes.new("ShaderNodeTexImage")
        nd.image = _img(path, color)
        nd.projection = "BOX"
        nd.projection_blend = 0.3
        nt.links.new(v, nd.inputs["Vector"])
        return nd.outputs["Color"]
    mask = _ramp(nt, _noise(nt, pos, scale * 0.22, 3), [(0.42, (0, 0, 0)), (0.58, (1, 1, 1))]) if anti else None
    res_ = {}
    for k, colr in (("diff", True), ("rough", False)):
        if not maps[k]:
            res_[k] = None
            continue
        a = tex(maps[k], colr, vecs[0])
        res_[k] = _mix(nt, mask, a, tex(maps[k], colr, vecs[1])) if anti else a
    col = res_["diff"]
    if macro:
        mv = _ramp(nt, _noise(nt, pos, scale * 0.035, 3), [(0.3, (1 - macro,) * 3), (0.7, (1.0, 1.0, 1.0))])
        col = _mix(nt, 1.0, col, mv, "MULTIPLY")
    if tint:
        col = _mix(nt, 1.0, col, tint, "MULTIPLY")
    return {"col": col, "rough": res_["rough"]}


def _pbr(nt, b, L, rough=1.0, bump=0.25):
    nt.links.new(L["col"], b.inputs["Base Color"])
    if L["rough"] is not None:
        nt.links.new(_math(nt, "MULTIPLY", L["rough"], rough, clamp=True), b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = min(1.0, 0.8 * rough)
    if bump:
        _bump(nt, b, L["col"], bump, 0.03)


def _fallback(name, c):
    return noisy(name, c, tuple(min(1.0, v * 1.18) for v in c), 2, 0.85, 0.2)


def mg_ph(name, asset, scale, tint=None, rough=1.0, bump=0.25, res="1k", anti=True, macro=0.2, fb=(0.6, 0.5, 0.4)):
    m, nt, b = _mnew(name)
    try:
        L = _ph_layer(nt, asset, scale, tint, res, anti, macro)
    except Exception as e:
        print("mg_ph fallback", asset, e)
        bpy.data.materials.remove(m)
        return _fallback(name, fb)
    _pbr(nt, b, L, rough, bump)
    return m


def mg_mask_height(z0, z1, wobble=0.0):
    def fn(nt, pos):
        z = _sep(nt, pos)[2]
        if wobble:
            z = _math(nt, "ADD", z, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, pos, 0.004, 4), 0.5), wobble))
        return _maprange(nt, z, z0, z1)
    return fn


def mg_mask_slope(flat=0.93, steep=0.78):
    def fn(nt, pos):
        nz = _sep(nt, nt.nodes.new("ShaderNodeNewGeometry").outputs["Normal"])[2]
        return _maprange(nt, nz, flat, steep)
    return fn


def mg_ground_mat(name, layers, blend_scale=0.012, rough=1.0, bump=0.3, extra=(), fb=(0.4, 0.42, 0.2), res="2k"):
    """layers: [(asset, scale, tint)], blended by large noise; extra: [(asset, scale, tint, maskfn)] laid on top."""
    m, nt, b = _mnew(name)
    pos = _pos(nt)
    try:
        Ls = [_ph_layer(nt, a, s, t, res if i == 0 else "1k", pos=pos) for i, (a, s, t) in enumerate(layers)]
        L = Ls[0]
        for i, L2 in enumerate(Ls[1:]):
            mk = _ramp(nt, _noise(nt, pos, blend_scale * (1 + i * 0.7), 4), [(0.45, (0, 0, 0)), (0.62, (1, 1, 1))])
            L = {k: (_mix(nt, mk, L[k], L2[k]) if (L[k] is not None and L2[k] is not None) else L[k]) for k in L}
        for (a, s, t, fn) in extra:
            L2 = _ph_layer(nt, a, s, t, "1k", pos=pos)
            mk = fn(nt, pos)
            L = {k: (_mix(nt, mk, L[k], L2[k]) if (L[k] is not None and L2[k] is not None) else L[k]) for k in L}
    except Exception as e:
        print("ground fallback", name, e)
        bpy.data.materials.remove(m)
        return _fallback(name, fb)
    _pbr(nt, b, L, rough, bump)
    return m


# ============================================================================================ procedural materials
def mg_felt_mat(name, c1, c2, dirt=(0.42, 0.36, 0.28), dirt_h=0.9, smoke_top=None):
    m, nt, b = _mnew(name)
    pos = _pos(nt)
    oc = _tc(nt, "Object")
    n1 = _noise(nt, pos, 2.5, 6, 0.6)
    col = _ramp(nt, n1, [(0.3, c1), (0.75, c2)])
    col = _mix(nt, _maprange(nt, _noise(nt, pos, 0.35, 3), 0.35, 0.7, 0.0, 0.35), col, tuple(c * 0.8 for c in c1))
    z = _sep(nt, oc)[2]
    col = _mix(nt, _maprange(nt, z, dirt_h, 0.0, 0.0, 0.6), col, dirt)
    if smoke_top:
        col = _mix(nt, _maprange(nt, z, smoke_top[0], smoke_top[1], 0.0, 0.65), col, (0.16, 0.12, 0.09))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    _try(b.inputs["Sheen Weight"], default_value=0.4)
    _bump(nt, b, n1, 0.15, 0.02)
    return m


def mg_applique_mat(name="applique", base=(0.4, 0.07, 0.05), line=(0.85, 0.78, 0.6), line2=(0.1, 0.13, 0.3)):
    """Rubruck's coloured felt applique: bold curling vine lines on red felt."""
    m, nt, b = _mnew(name)
    pos = _pos(nt)
    n = _noise(nt, pos, 4.0, 2, 0.4)
    col = _mix(nt, _band(nt, n, 0.47, 0.53), base, line)
    col = _mix(nt, _band(nt, _noise(nt, pos, 2.5, 2, 0.4), 0.6, 0.64), col, line2)
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    _try(b.inputs["Sheen Weight"], default_value=0.4)
    return m


def mg_rug_mat(name, field=(0.42, 0.06, 0.05), border=(0.07, 0.09, 0.24), motif=(0.78, 0.58, 0.28), line=(0.85, 0.8, 0.66), k=5.0):
    """Knotted carpet from the plane's UVs: border band with guard lines and a lozenge field."""
    m, nt, b = _mnew(name)
    s = _sep(nt, _tc(nt, "UV"))
    e = _math(nt, "MINIMUM", _math(nt, "MINIMUM", s[0], _math(nt, "SUBTRACT", 1.0, s[0])),
              _math(nt, "MINIMUM", s[1], _math(nt, "SUBTRACT", 1.0, s[1])))
    a = _math(nt, "FRACT", _math(nt, "MULTIPLY", _math(nt, "ADD", s[0], s[1]), k))
    c = _math(nt, "FRACT", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", s[0], s[1]), k))
    dm = _math(nt, "ADD", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", a, 0.5)), _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", c, 0.5)))
    col = _mix(nt, _math(nt, "LESS_THAN", dm, 0.3), field, motif)
    col = _mix(nt, _band(nt, dm, 0.3, 0.36), col, line)
    col = _mix(nt, _math(nt, "LESS_THAN", e, 0.13), col, border)
    bm = _math(nt, "FRACT", _math(nt, "MULTIPLY", _math(nt, "ADD", s[0], s[1]), k * 4))
    col = _mix(nt, _math(nt, "MULTIPLY", _band(nt, e, 0.045, 0.1), _math(nt, "LESS_THAN", bm, 0.5)), col, motif)
    col = _mix(nt, _math(nt, "ADD", _band(nt, e, 0.015, 0.03), _band(nt, e, 0.13, 0.145)), col, line)
    wear = _maprange(nt, _noise(nt, _pos(nt), 3.0, 4), 0.3, 0.75, 0.75, 1.0)
    col = _mix(nt, 1.0, col, _ramp(nt, wear, [(0.0, (0, 0, 0)), (1.0, (1, 1, 1))]), "MULTIPLY")
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    _try(b.inputs["Sheen Weight"], default_value=0.6)
    return m


def mg_nasij(name, base=(0.05, 0.07, 0.2), gold=(0.85, 0.6, 0.2), k=9.0):
    """Gold brocade (nasij): roundels and scrolling gold on a dark silk ground, metallic threads."""
    m, nt, b = _mnew(name)
    pos = _pos(nt)
    s = _sep(nt, pos)
    fu = _math(nt, "FRACT", _math(nt, "MULTIPLY", _math(nt, "ADD", s[0], s[1]), k * 0.5))
    fv = _math(nt, "FRACT", _math(nt, "MULTIPLY", s[2], k * 0.5))
    rr = _math(nt, "ADD", _math(nt, "POWER", _math(nt, "SUBTRACT", fu, 0.5), 2), _math(nt, "POWER", _math(nt, "SUBTRACT", fv, 0.5), 2))
    ring = _math(nt, "MAXIMUM", _band(nt, rr, 0.09, 0.13), _math(nt, "LESS_THAN", rr, 0.03))
    vine = _band(nt, _noise(nt, pos, k, 2, 0.4), 0.46, 0.54)
    g = _math(nt, "MAXIMUM", ring, vine)
    nt.links.new(_mix(nt, g, base, gold), b.inputs["Base Color"])
    nt.links.new(_math(nt, "MULTIPLY", g, 0.85), b.inputs["Metallic"])
    nt.links.new(_math(nt, "MULTIPLY_ADD", g, -0.35, 0.65), b.inputs["Roughness"])
    return m


def mg_painted_mat(name, base=(0.5, 0.1, 0.05), c1=(0.8, 0.6, 0.22), c2=(0.1, 0.2, 0.42)):
    m, nt, b = _mnew(name)
    pos = _pos(nt)
    col = _mix(nt, _band(nt, _noise(nt, pos, 7.0, 2, 0.4), 0.47, 0.53), base, c1)
    col = _mix(nt, _band(nt, _noise(nt, pos, 4.0, 2, 0.4), 0.62, 0.66), col, c2)
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45
    return m


def mg_tile_mat(name, col, rough=0.4, edge_col=None, edge_v=1.5, k_u=3.2, k_v=2.6):
    """Chinese barrel-tile roof from roof UVs (u along the eave, v up the slope, both in metres)."""
    m, nt, b = _mnew(name)
    s = _sep(nt, _tc(nt, "UV"))
    ru = _math(nt, "FRACT", _math(nt, "MULTIPLY", s[0], k_u))
    prof = _math(nt, "SUBTRACT", 1.0, _math(nt, "POWER", _math(nt, "MULTIPLY", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", ru, 0.5)), 2.0), 2.0))
    course = _math(nt, "FRACT", _math(nt, "MULTIPLY", s[1], k_v))
    base = col
    if edge_col:
        base = _mix(nt, _math(nt, "LESS_THAN", s[1], edge_v), col, edge_col)
    dark = _mix(nt, 1.0, base, (0.42, 0.42, 0.42), "MULTIPLY")
    c = _mix(nt, _maprange(nt, prof, 0.0, 0.6), dark, base)
    var = _maprange(nt, _noise(nt, _tc(nt, "UV"), 1.3, 2), 0.3, 0.7, 0.85, 1.05)
    c = _mix(nt, 1.0, c, _ramp(nt, var, [(0.0, (0, 0, 0)), (1.0, (1, 1, 1))]), "MULTIPLY")
    nt.links.new(c, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    _bump(nt, b, _math(nt, "ADD", _math(nt, "MULTIPLY", prof, 0.8), _math(nt, "MULTIPLY", course, 0.3)), 0.6, 0.06)
    return m


def mg_lattice_mat(name="lattice", wood=(0.36, 0.07, 0.04), paper=(0.82, 0.74, 0.58), k=3.2, axis=0):
    m, nt, b = _mnew(name)
    s = _sep(nt, _pos(nt))
    a = _math(nt, "FRACT", _math(nt, "MULTIPLY", s[axis], k))
    c = _math(nt, "FRACT", _math(nt, "MULTIPLY", s[2], k))
    bar = _math(nt, "MAXIMUM", _math(nt, "LESS_THAN", a, 0.2), _math(nt, "LESS_THAN", c, 0.2))
    nt.links.new(_mix(nt, bar, paper, wood), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    return m


def mg_rammed_mat(name, tint=(0.8, 0.66, 0.48), asset="brown_mud_dry", scale=0.3, lift=0.9):
    """Rammed earth (hangtu): photo texture + thin tamping layers + darker formwork lifts."""
    m, nt, b = _mnew(name)
    pos = _pos(nt)
    try:
        L = _ph_layer(nt, asset, scale, tint, "1k", pos=pos)
    except Exception as e:
        print("rammed fallback", e)
        L = {"col": _ramp(nt, _noise(nt, pos, 1.5, 5), [(0.3, tint), (0.7, tuple(c * 0.85 for c in tint))]), "rough": None}
    z = _sep(nt, pos)[2]
    zz = _math(nt, "ADD", z, _math(nt, "MULTIPLY", _noise(nt, pos, 0.4, 2), 0.25))
    thin = _math(nt, "LESS_THAN", _math(nt, "FRACT", _math(nt, "MULTIPLY", zz, 9.0)), 0.13)
    lifts = _math(nt, "LESS_THAN", _math(nt, "FRACT", _math(nt, "MULTIPLY", zz, 1.0 / lift)), 0.045)
    col = _mix(nt, _math(nt, "MULTIPLY", thin, 0.18), L["col"], (0.25, 0.2, 0.14))
    col = _mix(nt, _math(nt, "MULTIPLY", lifts, 0.45), col, (0.2, 0.16, 0.11))
    L["col"] = col
    _pbr(nt, b, L, 1.0, 0.3)
    return m


def mg_water_mat(name, col=(0.05, 0.09, 0.09), rough=0.05, wave=0.2, scale=0.3):
    m, nt, b = _mnew(name)
    b.inputs["Base Color"].default_value = _c4(col)
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = 1.33
    _bump(nt, b, _noise(nt, _pos(nt), scale, 6, 0.55), wave, 0.12)
    return m


def mg_grass_mat(name, root=(0.07, 0.08, 0.03), ca=(0.3, 0.34, 0.1), cb=(0.56, 0.5, 0.22), trans=0.35):
    m, nt, b = _mnew(name)
    hi = nt.nodes.new("ShaderNodeHairInfo")
    col = _ramp(nt, hi.outputs["Random"], [(0.0, ca), (0.55, tuple((x + y) / 2 for x, y in zip(ca, cb))), (1.0, cb)])
    col = _mix(nt, _maprange(nt, hi.outputs["Intercept"], 0.0, 0.5, 1.0, 0.0), col, root)
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(col, tr.inputs["Color"])
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = trans
    out = nt.nodes["Material Output"]
    nt.links.new(b.outputs[0], mx.inputs[1])
    nt.links.new(tr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def mg_leaf_mat(name, c1, c2, trans=0.3, scale=6.0):
    m, nt, b = _mnew(name)
    pos = _pos(nt)
    n = _noise(nt, pos, scale, 6, 0.65)
    col = _ramp(nt, n, [(0.3, c1), (0.7, c2)])
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    _try(b.inputs["Subsurface Weight"], default_value=0.0)
    _bump(nt, b, _noise(nt, pos, scale * 6, 4), 0.5, 0.05)
    if trans:
        tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
        nt.links.new(col, tr.inputs["Color"])
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = trans
        nt.links.new(b.outputs[0], mx.inputs[1])
        nt.links.new(tr.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def mg_emit_mat(name, col, strength):
    m = mat(name, col, emit=col, strength=strength)
    m["mg_emit"] = 1
    return m


# ============================================================================================ sky, sun, aerial perspective, smoke
def mg_sun(el, az, power=4.0, col=(1, 0.92, 0.8), angle=1.2):
    """az = compass of the sun's position in scene degrees (90 = straight ahead of a camera looking +Y, 0 = right)."""
    bpy.ops.object.light_add(type="SUN")
    s = bpy.context.active_object
    s.data.energy = power
    s.data.color = col
    s.data.angle = math.radians(angle)
    s.rotation_euler = (math.radians(90 - el), 0, math.radians(az + 90))
    return s


def mg_sky(hdri, strength=1.0, sun_az=None, sun_el=None, sun_power=4.0, sun_col=(1, 0.92, 0.8), sun_angle=1.2, view_az=90.0,
           clamp_pct=99.6, gamma=1.0, tint=(1, 1, 1), res="2k"):
    """Poly Haven HDRI sky, rotated so its sun glow sits at sun_az; the sun hot spot is clamped and replaced by a sun lamp.
    Returns the horizon colour in the view direction (for the aerial-perspective haze)."""
    info = {"haze": (0.55, 0.6, 0.68)}
    try:
        f = _ph_files(hdri)
        path = _fetch(f["hdri"][res]["hdr"]["url"], TEXDIR / hdri / f"{res}.hdr")
        img = bpy.data.images.load(str(path))
        W, H = img.size
        px = np.empty(W * H * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(H, W, 4)[:, :, :3]
        lum = px @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        up = lum[H // 2:]
        r, c = np.unravel_index(int(np.argmax(up)), up.shape)
        r += H // 2
        az_s = math.pi - 2 * math.pi * (c + 0.5) / W
        el_s = math.pi * ((r + 0.5) / H - 0.5)
        rho = (az_s - math.radians(sun_az)) if sun_az is not None else 0.0
        thr = float(np.percentile(up, clamp_pct))
        rows = slice(int(H * (0.5 + 1 / 180)), int(H * (0.5 + 7 / 180)) + 1)
        col_az = math.pi - 2 * math.pi * (np.arange(W) + 0.5) / W - rho
        diff = np.abs((col_az - math.radians(view_az) + math.pi) % (2 * math.pi) - math.pi)
        sel = diff < math.radians(40)
        band = np.minimum(px[rows][:, sel], thr).reshape(-1, 3).mean(axis=0)
        if gamma != 1.0:
            band = np.power(np.maximum(band, 1e-6), gamma)
        band = band * strength * np.array(tint)
        info["haze"] = tuple(float(v) for v in band)
        info["el_hdri"] = math.degrees(el_s)
        w = bpy.data.worlds.new("mgw")
        bpy.context.scene.world = w
        w.use_nodes = True
        nt = w.node_tree
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = img
        mp = _node(nt, "ShaderNodeMapping", {"Rotation": (0, 0, rho)})
        nt.links.new(_tc(nt, "Generated"), mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        col = env.outputs["Color"]
        if gamma != 1.0:
            g = _node(nt, "ShaderNodeGamma", {"Gamma": gamma})
            nt.links.new(col, g.inputs["Color"])
            col = g.outputs["Color"]
        vm = _node(nt, "ShaderNodeVectorMath", operation="MINIMUM")
        nt.links.new(col, vm.inputs[0])
        t = thr ** gamma if gamma != 1.0 else thr
        vm.inputs[1].default_value = (t, t, t)
        col = _mix(nt, 1.0, vm.outputs["Vector"], tint, "MULTIPLY")
        nt.links.new(col, nt.nodes["Background"].inputs["Color"])
        nt.nodes["Background"].inputs["Strength"].default_value = strength
        print("mg_sky", hdri, "sun px el %.1f" % math.degrees(el_s), "clamp %.2f" % thr, "haze", info["haze"])
    except Exception as e:
        print("mg_sky fallback", hdri, e)
        sky(sun_el or 25, (sun_az or 40) + 90, strength)
    if sun_az is not None:
        el = sun_el if sun_el is not None else max(3.0, info.get("el_hdri", 20.0))
        info["sun"] = mg_sun(el, sun_az, sun_power, sun_col, sun_angle)
    return info


def mg_aerial(col, dist, fmax=1.0, k=0.85):
    """Aerial perspective: blend every surface towards the horizon colour with camera distance (cheap, no volumes)."""
    col = tuple(c * k for c in col)
    for m in list(bpy.data.materials):
        if not m.use_nodes or m.get("mg_nohaze"):
            continue
        nt = m.node_tree
        outs = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"]
        if not outs or not outs[0].inputs["Surface"].is_linked:
            continue
        out = outs[0]
        src = out.inputs["Surface"].links[0].from_socket
        cd = nt.nodes.new("ShaderNodeCameraData")
        f = _math(nt, "EXPONENT", _math(nt, "DIVIDE", cd.outputs["View Distance"], -dist))
        f = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, f), fmax, clamp=True)
        em = _node(nt, "ShaderNodeEmission", {"Color": col, "Strength": 1.0})
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(f, mx.inputs[0])
        nt.links.new(src, mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
        if not m.get("mg_emit"):
            try:
                m.cycles.emission_sampling = "NONE"
            except Exception:
                pass


def mg_smoke(x, y, z0, h, r, dens=0.5, col=(0.3, 0.28, 0.26), lean=(0.0, 0.0), seed=0.0, speed=1.2):
    """Rising smoke column: volume in a cylinder, noise drifts upward over the shot. lean = (tilt towards +x, towards +y) rad."""
    rot = Euler((-lean[1], lean[0], 0.0))
    cen = Vector((x, y, z0)) + rot.to_matrix() @ Vector((0, 0, h / 2))
    o = add("cyl", tuple(cen), (r, r, h / 2), vertices=16)
    o.rotation_euler = rot
    m = bpy.data.materials.new("smoke")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    out = nt.nodes["Material Output"]
    oc = _tc(nt, "Object")
    mp = _node(nt, "ShaderNodeMapping", {"Scale": (1.0, 1.0, (h / 2) / r * 0.6)})
    nt.links.new(oc, mp.inputs["Vector"])
    loc = mp.inputs["Location"]
    loc.default_value = (seed, seed * 0.7, 0.0)
    loc.keyframe_insert("default_value", frame=1)
    loc.default_value = (seed, seed * 0.7, -speed)
    loc.keyframe_insert("default_value", frame=N)
    nd = _maprange(nt, _noise(nt, mp.outputs["Vector"], 1.4, 6, 0.6), 0.38, 0.7)
    s = _sep(nt, oc)
    z01 = _math(nt, "MULTIPLY_ADD", s[2], 0.5, 0.5)
    cx = _node(nt, "ShaderNodeCombineXYZ")
    nt.links.new(s[0], cx.inputs[0])
    nt.links.new(s[1], cx.inputs[1])
    ln = _node(nt, "ShaderNodeVectorMath", operation="LENGTH")
    nt.links.new(cx.outputs[0], ln.inputs[0])
    rr = _math(nt, "DIVIDE", ln.outputs["Value"], _math(nt, "MULTIPLY_ADD", z01, 0.65, 0.35))
    radial = _maprange(nt, rr, 1.0, 0.3)
    vert = _math(nt, "MULTIPLY", _maprange(nt, z01, 1.0, 0.3), _maprange(nt, z01, 0.0, 0.06))
    d = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", nd, radial), _math(nt, "MULTIPLY", vert, dens))
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = _c4(col)
    pv.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(d, pv.inputs["Density"])
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    o.data.materials.append(m)
    o.visible_shadow = True
    return o


def mg_shaft(p0, p1, r, col=(1, 0.85, 0.62), strength=0.3):
    """Fake volumetric light shaft (additive, camera-only)."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    o = add("cyl", tuple((a + b) / 2), (r, r, d.length / 2), vertices=32)
    o.rotation_euler = d.normalized().to_track_quat("Z", "Y").to_euler()
    m = bpy.data.materials.new("shaft")
    m["mg_nohaze"] = 1
    m["mg_emit"] = 1
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    lw = _node(nt, "ShaderNodeLayerWeight", {"Blend": 0.5})
    soft = _math(nt, "POWER", _math(nt, "SUBTRACT", 1.0, lw.outputs["Facing"]), 2.5)
    z = _sep(nt, _tc(nt, "Object"))[2]
    ends = _math(nt, "MULTIPLY", _maprange(nt, z, -1.0, -0.6), _maprange(nt, z, 1.0, 0.85))
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = _c4(col)
    nt.links.new(_math(nt, "MULTIPLY", _math(nt, "MULTIPLY", soft, ends), strength), em.inputs["Strength"])
    ad = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(nt.nodes.new("ShaderNodeBsdfTransparent").outputs[0], ad.inputs[0])
    nt.links.new(em.outputs[0], ad.inputs[1])
    nt.links.new(ad.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    o.data.materials.append(m)
    for k in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
        _try(o, **{k: False})
    return o


def mg_grass(ob, count, length, m, children=8, radius=0.004, seed=1, rand=0.45, clump=0.3):
    """Hair-particle grass on the 'dens' vertex group of a terrain."""
    ob.data.materials.append(m)
    mod = ob.modifiers.new("grass", "PARTICLE_SYSTEM")
    ps = mod.particle_system
    ps.seed = seed
    ps.vertex_group_density = "dens"
    s = ps.settings
    s.type = "HAIR"
    s.count = count
    s.emit_from = "FACE"
    _try(s, distribution="RAND", use_emit_random=True, use_advanced_hair=True)
    _try(s, factor_random=rand * 0.25, render_type="PATH", hair_step=4, render_step=3, display_step=2)
    _try(s, child_type="INTERPOLATED", rendered_child_count=children, child_nbr=1)
    _try(s, clump_factor=clump, roughness_2=0.12, roughness_endpoint=0.04, roughness_1=0.02, child_length=1.0,
         child_length_threshold=0.45)
    _try(s, radius_scale=radius, root_radius=1.0, tip_radius=0.0, use_close_tip=True)
    s.hair_length = length                                                      # last: it rescales the normal velocity
    print("mg_grass length", s.hair_length)
    try:
        s.material = len(ob.data.materials)
    except Exception:
        _try(s, material_slot=m.name)
    try:
        bpy.context.scene.cycles_curves.shape = "RIBBONS"
    except Exception:
        pass
    return ps


def mg_render_tweaks(sc, vol=False):
    _try(sc.cycles, blur_glossy=1.0, sample_clamp_indirect=4.0)
    if vol:
        _try(sc.cycles, volume_step_rate=3.0, volume_max_steps=256)


def mg_camera(keys, lens, target_keys):
    cam = camera_path(keys, lens=lens, target_keys=target_keys)
    cam.data.clip_end = 30000
    cam.data.clip_start = 0.1
    return cam


# ============================================================================================ kit: gers, carts, creatures
def mg_gmats():
    if "white" not in MG_M:
        MG_M["white"] = mg_felt_mat("feltW", (0.84, 0.81, 0.74), (0.92, 0.9, 0.85))
        MG_M["grey"] = mg_felt_mat("feltG", (0.62, 0.58, 0.51), (0.73, 0.69, 0.61))
        MG_M["black"] = mg_felt_mat("feltB", (0.1, 0.09, 0.08), (0.17, 0.15, 0.13), dirt=(0.25, 0.22, 0.18))
        MG_M["deco"] = mg_applique_mat()
        MG_M["rope"] = mat("rope", (0.12, 0.09, 0.07), 0.9)
        MG_M["hole"] = mat("hole", (0.025, 0.02, 0.018), 1.0)
        MG_M["wood"] = mg_ph("cartwood", "rough_wood", 0.6, tint=(0.8, 0.62, 0.45), fb=(0.35, 0.25, 0.15))
    return MG_M


def mg_ger_profile(R):
    HW = 1.45
    top = 1.6 + 0.95 * R
    roof = [(R * 1.045, HW + 0.12)]
    for k in range(1, 9):
        f = k / 8
        roof.append((R * 1.045 * (1 - f) + 0.2 * R * f, HW + 0.12 + (top - HW - 0.12) * math.sin(f * math.pi / 2) ** 0.8))
    return HW, top, roof


def mg_ger(x, y, z, R=2.8, felt="white", rot=0.0, door=True):
    """13th-c. ger after Rubruck: white chalked felt, taller domed roof rising to a chimney-like neck, felt door flap (south),
    applique band round the neck, horse-hair ropes."""
    M = mg_gmats()
    HW, top, roof = mg_ger_profile(R)
    loc = (x, y, z)
    w = MgB()
    w.lathe([(R, -0.3), (R, HW), (R * 1.045, HW + 0.12)], 32)
    w.finish("gerwall", M[felt], True, loc, rot)
    rf = MgB()
    rf.lathe(roof + [(0.19 * R, top + 0.28), (0.17 * R, top + 0.42)], 32)
    rf.finish("gerroof", M[felt], True, loc, rot)
    d = MgB()
    d.lathe([(0.215 * R, top - 0.1), (0.2 * R, top + 0.3)], 24)
    if door:
        d.box((0, -R - 0.035, 0.72), (0.46, 0.04, 0.74))
    d.finish("gerdeco", M["deco"], False, loc, rot)
    rp = MgB()
    for zz in (0.45, 1.05):
        rp.lathe([(R + 0.015, zz - 0.035), (R + 0.04, zz), (R + 0.015, zz + 0.035)], 32)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        rp.poly([((r + 0.035) * math.cos(a), (r + 0.035) * math.sin(a), zz + 0.03) for (r, zz) in roof], 0.025, n=4)
    rp.finish("gerrope", M["rope"], False, loc, rot)
    h = MgB()
    h.cyl((0, 0, top + 0.36), 0.165 * R, 0.03, 16)
    h.finish("gerhole", M["hole"], False, loc, rot)
    return top


def mg_wheel(b, c, r, spokes=8, t=0.07, axis_y=True):
    """Spoked wheel in the local xz plane at centre c (axle along y)."""
    cx, cy, cz = c
    pts = [(cx + r * math.cos(2 * math.pi * k / 18), cy, cz + r * math.sin(2 * math.pi * k / 18)) for k in range(19)]
    b.poly(pts, t, n=5)
    b.cyl((cx, cy, cz), r * 0.18, 0.12, 10, rot=(math.pi / 2, 0, 0))
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        b.seg((cx, cy, cz), (cx + r * math.cos(a), cy, cz + r * math.sin(a)), t * 0.5, n=4)


def mg_cart_ger(x, y, z, heading=math.pi, oxen=22, coat=None):
    """Rubruck: a great ger carried whole on a cart, 22 oxen in two rows of 11, door facing the team."""
    M = mg_gmats()
    b = MgB()
    b.box((0, 0, 1.35), (3.4, 2.7, 0.12))
    for wx in (-1.7, 1.7):
        for wy in (-2.75, 2.75):
            mg_wheel(b, (wx, wy, 1.0), 1.0)
    b.seg((3.4, 0.5, 1.2), (6.5, 0.5, 0.95), 0.09)
    b.seg((3.4, -0.5, 1.2), (6.5, -0.5, 0.95), 0.09)
    b.finish("cartger", M["wood"], False, (x, y, z), heading)
    ch, sh = math.cos(heading), math.sin(heading)
    mg_ger(x, y, z + 1.45, 3.3, "white", heading + math.pi / 2)
    me = mg_ox_me()
    hide = MG_M.setdefault("oxhide", [noisy("oxa", (0.3, 0.2, 0.12), (0.4, 0.28, 0.16), 4, 0.75, 0.08),
                                      noisy("oxb", (0.12, 0.1, 0.08), (0.2, 0.16, 0.12), 4, 0.75, 0.08),
                                      noisy("oxc", (0.6, 0.55, 0.48), (0.7, 0.65, 0.56), 4, 0.75, 0.08)])
    rng = random.Random(int(x * 13 + y))
    for i in range(oxen // 2):
        for side in (-0.85, 0.85):
            lx, ly = 7.6 + i * 2.1, side
            mg_inst(me, (x + lx * ch - ly * sh, y + lx * sh + ly * ch, z), heading, rng.uniform(0.92, 1.04), rng.choice(hide))


def mg_box_cart(x, y, z, heading=0.0):
    M = mg_gmats()
    w = MgB()
    mg_wheel(w, (0, -0.72, 0.55), 0.55)
    mg_wheel(w, (0, 0.72, 0.55), 0.55)
    w.seg((0.8, 0, 0.75), (2.6, 0, 0.6), 0.05)
    w.finish("boxcartw", M["wood"], False, (x, y, z), heading)
    c = MgB()
    c.box((0, 0, 1.15), (0.85, 0.6, 0.42))
    c.finish("boxcart", M["black"], False, (x, y, z), heading)


def mg_skin_mesh(name, nodes, edges, sub=2):
    me = bpy.data.meshes.new(name + "_sk")
    me.from_pydata([n[0] for n in nodes], edges, [])
    me.update()
    ob = mg_link(bpy.data.objects.new(name + "_sk", me))
    ob.modifiers.new("skin", "SKIN")
    if len(me.skin_vertices) == 0:
        me.skin_vertices.new()
    sv = me.skin_vertices[0].data
    for i, n in enumerate(nodes):
        r = n[1]
        sv[i].radius = (r, r) if isinstance(r, (int, float)) else r
    sv[0].use_root = True
    s = ob.modifiers.new("sub", "SUBSURF")
    s.levels = s.render_levels = sub
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    me2.polygons.foreach_set("use_smooth", [True] * len(me2.polygons))
    me2.materials.append(mat("tmp_" + name, (0.5, 0.5, 0.5)))
    me2.name = name
    return me2


def mg_inst(me, loc, rz=0.0, s=1.0, m=None):
    ob = mg_link(bpy.data.objects.new(me.name + "_i", me))
    ob.location = loc
    ob.rotation_euler = (0, 0, rz)
    ob.scale = (s, s, s)
    if m is not None:
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = m
    return ob


def _legs(nodes, edges, specs):
    for top, mid, low, attach, rt, rm, rl in specs:
        i = len(nodes)
        nodes.extend([(top, rt), (mid, rm), (low, rl), ((low[0] + 0.03, low[1], 0.0), rl * 1.15)])
        edges.extend([(attach, i), (i, i + 1), (i + 1, i + 2), (i + 2, i + 3)])


def mg_horse_me(graze=False):
    """Mongolian pony, c. 1.3 m at the withers: big head, short thick neck, short strong legs."""
    key = "horse_g" if graze else "horse"
    if key in MG_T:
        return MG_T[key]
    if graze:
        head = [((0.72, 0, 1.06), (0.17, 0.2)), ((0.95, 0, 0.66), 0.13), ((1.06, 0, 0.38), 0.115), ((1.1, 0, 0.12), 0.085)]
    else:
        head = [((0.72, 0, 1.26), (0.17, 0.2)), ((0.88, 0, 1.5), 0.13), ((0.98, 0, 1.6), 0.115), ((1.3, 0, 1.32), 0.085)]
    nodes = [((-0.5, 0, 1.02), (0.28, 0.3)), ((0, 0, 1.0), (0.33, 0.35)), ((0.48, 0, 1.0), (0.28, 0.32))] + head
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]
    specs = []
    for sy in (0.14, -0.14):
        specs.append(((0.5, sy, 0.72), (0.52, sy, 0.4), (0.52, sy, 0.12), 2, 0.09, 0.055, 0.05))
    for sy in (0.15, -0.15):
        specs.append(((-0.52, sy, 0.75), (-0.6, sy, 0.42), (-0.56, sy, 0.12), 0, 0.11, 0.06, 0.05))
    _legs(nodes, edges, specs)
    i = len(nodes)
    nodes.extend([((-0.78, 0, 0.98), 0.08), ((-0.88, 0, 0.62), 0.075), ((-0.9, 0, 0.3), 0.06)])
    edges.extend([(0, i), (i, i + 1), (i + 1, i + 2)])
    MG_T[key] = mg_skin_mesh(key, nodes, edges)
    return MG_T[key]


def mg_camel_me():
    """Bactrian camel: two humps, long curved neck, shaggy."""
    if "camel" in MG_T:
        return MG_T["camel"]
    nodes = [((-0.7, 0, 1.45), (0.4, 0.42)), ((0, 0, 1.45), (0.45, 0.48)), ((0.65, 0, 1.4), (0.38, 0.4)),
             ((-0.38, 0, 2.02), 0.24), ((0.36, 0, 1.98), 0.24),
             ((1.0, 0, 1.25), (0.2, 0.22)), ((1.3, 0, 1.42), 0.15), ((1.42, 0, 1.88), 0.13), ((1.78, 0, 1.84), (0.1, 0.12))]
    edges = [(0, 1), (1, 2), (1, 3), (1, 4), (2, 5), (5, 6), (6, 7), (7, 8)]
    specs = []
    for sy in (0.2, -0.2):
        specs.append(((0.6, sy, 1.05), (0.62, sy, 0.6), (0.62, sy, 0.1), 2, 0.13, 0.08, 0.08))
    for sy in (0.22, -0.22):
        specs.append(((-0.68, sy, 1.1), (-0.75, sy, 0.6), (-0.7, sy, 0.1), 0, 0.16, 0.08, 0.08))
    _legs(nodes, edges, specs)
    i = len(nodes)
    nodes.extend([((-1.05, 0, 1.4), 0.05), ((-1.1, 0, 0.95), 0.045)])
    edges.extend([(0, i), (i, i + 1)])
    MG_T["camel"] = mg_skin_mesh("camel", nodes, edges)
    return MG_T["camel"]


def mg_ox_me():
    if "ox" in MG_T:
        return MG_T["ox"]
    nodes = [((-0.65, 0, 1.0), (0.35, 0.38)), ((0, 0, 0.95), (0.42, 0.45)), ((0.6, 0, 0.98), (0.38, 0.42)),
             ((0.9, 0, 1.02), 0.25), ((1.2, 0, 0.85), (0.15, 0.17)), ((1.36, 0, 0.62), 0.11)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    specs = []
    for sy in (0.2, -0.2):
        specs.append(((0.6, sy, 0.7), (0.62, sy, 0.35), (0.62, sy, 0.1), 2, 0.11, 0.07, 0.065))
    for sy in (0.22, -0.22):
        specs.append(((-0.62, sy, 0.75), (-0.68, sy, 0.38), (-0.65, sy, 0.1), 0, 0.13, 0.07, 0.065))
    _legs(nodes, edges, specs)
    i = len(nodes)
    nodes.extend([((1.2, 0.22, 1.05), 0.035), ((1.2, -0.22, 1.05), 0.035)])                         # horns
    edges.extend([(4, i), (4, i + 1)])
    MG_T["ox"] = mg_skin_mesh("ox", nodes, edges)
    return MG_T["ox"]


def mg_sheep_me():
    if "sheep" in MG_T:
        return MG_T["sheep"]
    nodes = [((-0.3, 0, 0.62), (0.3, 0.32)), ((0.25, 0, 0.62), (0.3, 0.32)), ((0.5, 0, 0.66), 0.12), ((0.62, 0, 0.5), 0.08)]
    edges = [(0, 1), (1, 2), (2, 3)]
    specs = []
    for sy in (0.12, -0.12):
        specs.append(((0.25, sy, 0.4), (0.26, sy, 0.22), (0.26, sy, 0.08), 1, 0.06, 0.035, 0.03))
        specs.append(((-0.28, sy, 0.4), (-0.3, sy, 0.22), (-0.3, sy, 0.08), 0, 0.06, 0.035, 0.03))
    _legs(nodes, edges, specs)
    i = len(nodes)
    nodes.append(((-0.55, 0, 0.5), 0.16))                                                         # fat tail
    edges.append((0, i))
    MG_T["sheep"] = mg_skin_mesh("sheep", nodes, edges)
    return MG_T["sheep"]


def mg_coats():
    if "coats" not in MG_M:
        MG_M["coats"] = [noisy("dun", (0.55, 0.42, 0.27), (0.66, 0.52, 0.34), 5, 0.75, 0.08),
                         noisy("bay", (0.28, 0.14, 0.07), (0.38, 0.2, 0.1), 5, 0.7, 0.08),
                         noisy("chestnut", (0.42, 0.2, 0.09), (0.5, 0.27, 0.12), 5, 0.7, 0.08),
                         noisy("blackcoat", (0.05, 0.045, 0.04), (0.1, 0.085, 0.07), 5, 0.6, 0.08),
                         noisy("greycoat", (0.48, 0.47, 0.45), (0.64, 0.63, 0.6), 5, 0.75, 0.08),
                         noisy("whitecoat", (0.76, 0.74, 0.69), (0.84, 0.82, 0.77), 5, 0.75, 0.08)]
    return MG_M["coats"]


def mg_herd(cx, cy, n, sx, sy, hfn, rng, graze=0.6, s=1.0, heading=None):
    coats = mg_coats()
    for _ in range(n):
        x, y = cx + rng.gauss(0, sx), cy + rng.gauss(0, sy)
        hd = (heading + rng.gauss(0, 0.6)) if heading is not None else rng.uniform(0, 6.283)
        mg_inst(mg_horse_me(rng.random() < graze), (x, y, hfn(x, y)), hd, s * rng.uniform(0.92, 1.05), rng.choice(coats))


def mg_flock(cx, cy, n, sx, sy, hfn, rng):
    wool = MG_M.setdefault("wool", [noisy("wool", (0.72, 0.68, 0.6), (0.82, 0.78, 0.7), 8, 0.95, 0.2),
                                    noisy("wool2", (0.35, 0.28, 0.22), (0.45, 0.36, 0.28), 8, 0.95, 0.2)])
    for _ in range(n):
        x, y = cx + rng.gauss(0, sx), cy + rng.gauss(0, sy)
        mg_inst(mg_sheep_me(), (x, y, hfn(x, y)), rng.uniform(0, 6.283), rng.uniform(0.9, 1.1), wool[0] if rng.random() < 0.8 else wool[1])


# ============================================================================================ kit: trees
def mg_branch(b, leaves, p, d, length, radius, depth, rng, spread=38, up=0.25, droop=0.0, nchild=3, leaf_r=0.0, segs=3, leaf_scale=(1, 1, 0.7)):
    cur = Vector(p)
    d = Vector(d).normalized()
    pts = [cur.copy()]
    for k in range(segs):
        d = (d + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.18 + Vector((0, 0, up * 0.12 - droop * 0.25))).normalized()
        nxt = cur + d * (length / segs)
        b.seg(cur, nxt, radius * (1 - 0.45 * k / segs), radius * (1 - 0.45 * (k + 1) / segs), 6 if radius > 0.06 else 4)
        cur = nxt
        pts.append(cur.copy())
    if depth == 0:
        if leaves is not None and leaf_r > 0:
            leaves.ico(tuple(cur), leaf_r * rng.uniform(0.7, 1.2), leaf_scale, 1)
        return
    for c in range(nchild):
        t = rng.uniform(0.4, 1.0)
        idx = min(len(pts) - 1, max(1, int(round(t * segs))))
        base = pts[idx]
        perp = d.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
        a = math.radians(spread * rng.uniform(0.7, 1.3))
        cd = (d * math.cos(a) + perp * math.sin(a) + Vector((0, 0, up))).normalized()
        mg_branch(b, leaves, base, cd, length * rng.uniform(0.55, 0.72), radius * 0.55, depth - 1, rng, spread, up, droop, nchild,
                  leaf_r, segs, leaf_scale)
        if leaves is not None and leaf_r > 0 and depth <= 1:
            leaves.ico(tuple(base), leaf_r * 0.8, leaf_scale, 1)


def mg_tree(b, leaves, x, y, z, h, rng, kind="oak"):
    """Recursive tree into builders b (wood) and leaves (foliage blobs or None)."""
    if kind == "oak":                                                           # bare spring oak/ash, faint buds
        mg_branch(b, leaves, (x, y, z - 0.3), (0, 0, 1), h * 0.42, h * 0.035, 4, rng, 40, 0.18, 0.0, 3, h * 0.025, 3)
    elif kind == "willow":
        mg_branch(b, leaves, (x, y, z - 0.3), (rng.uniform(-0.2, 0.2), 0, 1), h * 0.35, h * 0.045, 3, rng, 45, 0.3, 0.6, 4, h * 0.075, 3,
                  (1.0, 1.0, 1.3))
    elif kind == "poplar":                                                      # columnar, bare
        mg_branch(b, leaves, (x, y, z - 0.3), (0, 0, 1), h * 0.55, h * 0.03, 3, rng, 16, 0.6, 0.0, 4, h * 0.03, 3)
    elif kind == "poplar_leaf":
        mg_branch(b, None, (x, y, z - 0.3), (0, 0, 1), h * 0.5, h * 0.03, 2, rng, 18, 0.6, 0.0, 3, 0, 3)
        for k in range(9):
            zz = z + h * (0.3 + 0.07 * k)
            rr = h * 0.11 * math.sin(math.pi * (0.15 + 0.85 * (k + 1) / 10))
            leaves.ico((x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), zz), rr + 0.4, (1, 1, 1.6), 2)


def _pad(pads, c, r, rng):
    """A cloud-pad of pine needles: a cluster of flattened lumps, not one disc."""
    for k in range(7):
        a = rng.uniform(0, 6.283)
        d = r * rng.uniform(0.2, 0.9)
        pads.ico((c.x + math.cos(a) * d * 1.3, c.y + math.sin(a) * d * 1.3, c.z + rng.uniform(-0.15, 0.25) * r),
                 r * rng.uniform(0.45, 0.7), (1.4, 1.4, 0.75), 2)


def mg_pine(trunk, pads, x, y, z, h, rng, lean=0.0):
    """Japanese black pine: leaning, twisting trunk, near-horizontal limbs ending in flat cloud-pads of needles."""
    d = Vector((math.cos(lean), math.sin(lean), 0)) * 0.35 + Vector((0, 0, 1))
    pts = [Vector((x, y, z - 0.4))]
    cur = pts[0].copy()
    for k in range(6):
        d = (d + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0.05))).normalized()
        cur = cur + d * (h / 6)
        pts.append(cur.copy())
    trunk.poly([tuple(p) for p in pts], h * 0.028, h * 0.012, 7)
    _pad(pads, pts[-1] + Vector((0, 0, 0.3)), h * 0.13, rng)
    for k in range(7):
        base = pts[2 + k % 4] + (pts[3 + k % 3] - pts[2 + k % 4]) * rng.random()
        a = rng.uniform(0, 6.283)
        L = h * rng.uniform(0.18, 0.34)
        end = base + Vector((math.cos(a) * L, math.sin(a) * L, rng.uniform(-0.05, 0.25) * L))
        trunk.seg(tuple(base), tuple(end), h * 0.01, h * 0.005, 5)
        _pad(pads, end + Vector((0, 0, 0.2)), h * rng.uniform(0.08, 0.12), rng)


def mg_palm(trunk, fronds, x, y, z, h, rng, dead=None):
    """Date palm: slightly curved trunk, crown of stiff feathery fronds (built as leaflet triangles)."""
    lean = Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), 1)).normalized()
    pts = [Vector((x, y, z - 0.3)) + lean * (h * k / 6) + Vector((0, 0, 0)) * k for k in range(7)]
    trunk.poly([tuple(p) for p in pts], 0.3, 0.22, 8)
    top = pts[-1]
    verts, faces = [], []
    nf = 18
    for f in range(nf):
        az = 2 * math.pi * f / nf + rng.uniform(-0.15, 0.15)
        e0 = math.radians(rng.uniform(25, 60) if f % 2 else rng.uniform(-5, 30))
        L = rng.uniform(3.0, 4.2)
        dirh = Vector((math.cos(az), math.sin(az), 0))
        side = Vector((-math.sin(az), math.cos(az), 0))
        p = top.copy()
        n = 14
        for i in range(n):
            s = (i + 1) / n
            e = e0 - math.radians(85) * s ** 1.4
            step = (dirh * math.cos(e) + Vector((0, 0, math.sin(e)))) * (L / n)
            q = p + step
            wl = 0.75 * math.sin(math.pi * min(1.0, s * 1.15)) + 0.08
            for sg in (-1, 1):
                tip = q + side * sg * wl + Vector((0, 0, -0.18 * wl))
                bi = len(verts)
                verts.extend([tuple(p), tuple(q), tuple(tip)])
                faces.append((bi, bi + 1, bi + 2))
            p = q
    bm = fronds.bm
    vs = [bm.verts.new(v) for v in verts]
    for f_ in faces:
        try:
            bm.faces.new([vs[i] for i in f_])
        except ValueError:
            pass


# ============================================================================================ kit: Chinese timber architecture
def mg_roof(cx, cy, z0, hx, hy, rise, m, t_end=1.0, upturn=0.8, curve=1.7, nrings=10, nx=20, ny=10, thick=0.35, ridge_m=None, ridge_r=0.26):
    """Hipped (wudian) roof: concave slope, deep eaves, corners swept up; UVs in metres for the tile shader.
    t_end < 1 gives the lower ring of a double-eave roof."""
    hx = max(hx, hy + 0.05)
    rings = []
    for i in range(nrings + 1):
        t = t_end * i / nrings
        ax, ay = hx - t * hy, max(1e-3, hy * (1 - t))
        z = z0 + rise * t ** curve
        ring = []
        for (p0, p1, n, L0) in (((-ax, -ay), (ax, -ay), nx, 2 * hx), ((ax, -ay), (ax, ay), ny, 2 * hy),
                                ((ax, ay), (-ax, ay), nx, 2 * hx), ((-ax, ay), (-ax, -ay), ny, 2 * hy)):
            for k in range(n):
                f = k / n
                dc = min(f, 1 - f) * L0
                lift = upturn * max(0.0, 1 - dc / (0.9 * hy)) ** 2 * (1 - t) ** 2
                ring.append((cx + p0[0] + (p1[0] - p0[0]) * f, cy + p0[1] + (p1[1] - p0[1]) * f, z + lift))
        rings.append(ring)
    nr = len(rings[0])
    u0 = [0.0]
    for j in range(1, nr):
        u0.append(u0[-1] + math.dist(rings[0][j][:2], rings[0][j - 1][:2]))
    vacc = [0.0] * nr
    uvs = []
    for i, r in enumerate(rings):
        if i:
            for j in range(nr):
                vacc[j] += math.dist(rings[i][j], rings[i - 1][j])
        uvs.extend((u0[j], vacc[j]) for j in range(nr))
    verts = [p for r in rings for p in r]
    faces = [(i * nr + j, i * nr + (j + 1) % nr, (i + 1) * nr + (j + 1) % nr, (i + 1) * nr + j) for i in range(nrings) for j in range(nr)]
    ob = mg_mesh("roof", verts, faces, m, True, uvs)
    sd = ob.modifiers.new("thick", "SOLIDIFY")
    sd.thickness = thick
    sd.offset = -1
    rb = MgB()
    for jc in (0, nx, nx + ny, 2 * nx + ny):
        rb.poly([(p[0], p[1], p[2] + 0.12) for p in (rings[i][jc] for i in range(nrings + 1))], ridge_r * 0.75, n=6)
    if t_end >= 0.999:
        a, b = rings[-1][0], rings[-1][nx]
        rb.seg((a[0], a[1], a[2] + 0.2), (b[0], b[1], b[2] + 0.2), ridge_r * 1.3, n=8)
        for e in (a, b):
            rb.box((e[0], e[1], e[2] + 0.75), (ridge_r * 1.2, ridge_r * 2.2, 0.6))
    rb.finish("ridge", ridge_m or m)
    return ob


def mg_hall_mats():
    if "hall" not in MG_M:
        MG_M["hall"] = dict(
            col=noisy("lacquer", (0.42, 0.07, 0.04), (0.5, 0.1, 0.06), 6, 0.35, 0.05),
            bracket=noisy("dougong", (0.1, 0.26, 0.24), (0.14, 0.32, 0.29), 5, 0.6, 0.1),
            beam=noisy("beam", (0.09, 0.2, 0.28), (0.13, 0.26, 0.33), 5, 0.6, 0.1),
            wall=mg_ph("hallwall", "white_plaster_02", 0.3, tint=(0.62, 0.22, 0.13), fb=(0.55, 0.2, 0.12)),
            lattice=mg_lattice_mat("lattice"),
            plat=mg_ph("hallplat", "yellow_brick", 0.55, tint=(0.66, 0.64, 0.62), fb=(0.5, 0.5, 0.48)),
            stone=mg_ph("plinth", "marble_01", 0.3, tint=(0.88, 0.86, 0.82), fb=(0.8, 0.78, 0.74)))
    return MG_M["hall"]


def _dougong(b, x, y, z, s=1.0):
    b.box((x, y, z + 0.16 * s), (0.32 * s, 0.32 * s, 0.16 * s))
    b.box((x, y, z + 0.42 * s), (0.85 * s, 0.18 * s, 0.1 * s))
    b.box((x, y, z + 0.42 * s), (0.18 * s, 0.85 * s, 0.1 * s))
    b.box((x, y, z + 0.62 * s), (0.34 * s, 0.34 * s, 0.1 * s))
    b.box((x, y, z + 0.82 * s), (1.25 * s, 0.18 * s, 0.1 * s))
    b.box((x, y, z + 0.82 * s), (0.18 * s, 1.25 * s, 0.1 * s))
    b.box((x, y, z + 1.02 * s), (0.42 * s, 0.42 * s, 0.1 * s))
    return 1.12 * s


def mg_hall(cx, cy, nx, ny, bay=4.5, col_h=5.5, plat_h=1.4, z=0.0, roof_m=None, ridge_m=None, double=False, plat_m=None,
            wall_m=None, front_doors=True, rise_k=0.62):
    """Song/Jin/Yuan-style timber hall: platform, red columns, big bracket sets (about a quarter of column height), lattice
    front, hipped roof with deep eaves and gently swept corners. Faces -Y."""
    M = mg_hall_mats()
    roof_m = roof_m or MG_M.setdefault("greytile", mg_tile_mat("greytile", (0.3, 0.3, 0.31), 0.6))
    W, D = nx * bay, ny * bay
    hx, hy = W / 2, D / 2
    pb = MgB()
    pb.box((cx, cy, z + plat_h / 2 - 0.4), (hx + 2.6, hy + 2.6, plat_h / 2 + 0.4))
    for k in range(5):
        hk = plat_h * (1 - (k + 1) / 6)
        pb.box((cx, cy - hy - 2.6 - 0.45 * (k + 0.5), z + hk / 2), (max(3.0, W * 0.16), 0.23, hk / 2 + 0.01))
    pb.finish("platform", plat_m or M["plat"])
    z1 = z + plat_h
    ztop = z1 + col_h
    rc = 0.05 * col_h + 0.12
    cb, sb, bb, br, wb, lb = MgB(), MgB(), MgB(), MgB(), MgB(), MgB()
    pts = [(cx - hx + i * bay, cy - hy + j * bay) for i in range(nx + 1) for j in range(ny + 1) if i in (0, nx) or j in (0, ny)]
    s = col_h / 4.8
    for (x, y) in pts:
        cb.cyl((x, y, z1 + col_h / 2), rc, col_h / 2, 14)
        sb.cyl((x, y, z1 + 0.12), rc * 1.5, 0.12, 12)
        bh = _dougong(br, x, y, ztop, s)
    for i in range(nx):                                                         # intermediate bracket sets
        for yy in (cy - hy, cy + hy):
            _dougong(br, cx - hx + (i + 0.5) * bay, yy, ztop, s * 0.85)
    for j in range(ny):
        for xx in (cx - hx, cx + hx):
            _dougong(br, xx, cy - hy + (j + 0.5) * bay, ztop, s * 0.85)
    for yy in (cy - hy, cy + hy):                                               # architrave + top beam
        bb.box((cx, yy, ztop - 0.3), (hx + 0.3, 0.22, 0.3))
        bb.box((cx, yy, ztop + bh * 0.97), (hx + 1.0, 0.3, 0.18))
    for xx in (cx - hx, cx + hx):
        bb.box((xx, cy, ztop - 0.3), (0.22, hy + 0.3, 0.3))
        bb.box((xx, cy, ztop + bh * 0.97), (0.3, hy + 1.0, 0.18))
    wh = (col_h - 0.6) / 2
    for i in range(nx):                                                         # back wall and front lattice doors
        x = cx - hx + (i + 0.5) * bay
        wb.box((x, cy + hy, z1 + wh), (bay / 2 - rc * 0.8, 0.2, wh))
        if front_doors:
            lb.box((x, cy - hy, z1 + 0.6 + (wh - 0.3)), (bay / 2 - rc * 0.8, 0.09, wh - 0.3))
            wb.box((x, cy - hy, z1 + 0.3), (bay / 2 - rc * 0.8, 0.12, 0.3))
        else:
            wb.box((x, cy - hy, z1 + wh), (bay / 2 - rc * 0.8, 0.2, wh))
    for j in range(ny):
        y = cy - hy + (j + 0.5) * bay
        for xx in (cx - hx, cx + hx):
            wb.box((xx, y, z1 + wh), (0.2, bay / 2 - rc * 0.8, wh))
    cb.finish("columns", M["col"])
    sb.finish("plinths", M["stone"])
    br.finish("brackets", M["bracket"])
    bb.finish("beams", M["beam"])
    wb.finish("walls", wall_m or M["wall"])
    lb.finish("lattice", M["lattice"])
    zr = ztop + bh
    ov = 0.3 * col_h + 1.0
    rise = (hy + ov) * rise_k
    if double:
        mg_roof(cx, cy, zr, hx + ov, hy + ov, rise, roof_m, t_end=0.3, ridge_m=ridge_m, upturn=0.9)
        hxi, hyi = hx - bay * 0.55, hy - bay * 0.55
        zl = zr + rise * 0.3 ** 1.7
        cl = MgB()
        cl.frustum((cx, cy, zl - 0.6), hxi, hyi, hxi, hyi, 3.2)
        cl.finish("clerestory", wall_m or M["wall"])
        b2 = MgB()
        for i in range(nx):
            for yy in (cy - hyi, cy + hyi):
                _dougong(b2, cx - hxi + (i + 0.5) * (2 * hxi / nx), yy, zl + 2.6, s * 0.8)
        b2.finish("brackets2", M["bracket"])
        mg_roof(cx, cy, zl + 3.5, hxi + ov * 0.8, hyi + ov * 0.8, (hyi + ov * 0.8) * rise_k, roof_m, ridge_m=ridge_m)
        return zl + 3.5 + (hyi + ov * 0.8) * rise_k
    mg_roof(cx, cy, zr, hx + ov, hy + ov, rise, roof_m, ridge_m=ridge_m)
    return zr + rise


def mg_earth_wall(b, p0, p1, h, base_w, top_w, z0=-1.0, merlon_b=None, merlon_every=2.6, outward=(0, -1)):
    """Battered rammed-earth wall along p0 -> p1 (trapezoid section)."""
    p0, p1 = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0))
    d = p1 - p0
    L = d.length
    ang = math.atan2(d.y, d.x)
    c = (p0 + p1) / 2
    b.frustum((c.x, c.y, z0), L / 2 + base_w / 2, base_w / 2, L / 2 + top_w / 2, top_w / 2, h - z0, ang)
    if merlon_b is not None:
        n = Vector((-math.sin(ang), math.cos(ang), 0))
        if n.dot(Vector((outward[0], outward[1], 0))) < 0:
            n = -n
        k = int(L / merlon_every)
        for i in range(k):
            q = p0 + d * ((i + 0.5) / k) + n * (top_w / 2 - 0.3)
            merlon_b.box((q.x, q.y, h + 0.55), (0.6, 0.3, 0.55), (0, 0, ang))


# ============================================================================================ SHOTS
def shot_m_steppe_dawn():
    """Opening shot: Temujin's steppe, c. 1190. Dawn light from the east (right), camp in a sheltered valley by the river."""
    sc = reset()
    mg_render_tweaks(sc, vol=True)
    info = mg_sky("kloppenheim_06_puresky", 0.7, sun_az=12, sun_el=7, sun_power=5.0, sun_col=(1.0, 0.64, 0.38), sun_angle=1.0, view_az=95)
    exposure(0.35)
    rng = random.Random(21)

    def riv(x):
        return 74 + 22 * math.sin(x / 130 + 0.4) + 9 * math.sin(x / 47 + 1.3)
    camp = (-38.0, 160.0)

    def h(x, y):
        d = math.hypot(x * 0.8, y + 5)
        z = (mg_fbm(x / 240, y / 240, 3, 1) + 0.45) * 10 * mg_ss(30, 260, d)
        z += mg_fbm(x / 28, y / 28, 2, 3) * 0.3
        z += (mg_fbm(x / 650, y / 650, 4, 5) + 0.5) * 85 * mg_ss(420, 1500, y)
        z += mg_ridge(x / 1400, y / 1400, 5, 9) ** 1.5 * 950 * mg_ss(2200, 4800, y)
        k = 1 - mg_ss(55, 120, math.hypot(x - camp[0], (y - camp[1]) * 1.3))
        z = z * (1 - k) + 1.2 * k
        k = 1 - mg_ss(5, 20, abs(y - riv(x)))
        return z * (1 - k) - 2.4 * k

    def dens(x, y):
        return (1 - mg_ss(25, 75, math.hypot(x * 0.8, y - 8))) * mg_ss(-26, -18, y) * mg_ss(5, 9, abs(y - riv(x)))
    gm = mg_ground_mat("steppe", [("leafy_grass", 0.35, (0.92, 0.88, 0.62)), ("withered_grass", 0.3, (1.0, 0.92, 0.7))], 0.008,
                       extra=[("rocky_terrain_02", 0.01, (0.85, 0.85, 0.8), mg_mask_height(120, 400, 80))])
    ground = mg_terrain("steppe", 7000, 480, h, gm, 0, 20, 2.2, dens)
    mg_grass(ground, 70000, 0.3, mg_grass_mat("grass", (0.06, 0.07, 0.03), (0.3, 0.33, 0.1), (0.62, 0.52, 0.24)), 8, 0.0035, 3)
    add("plane", (0, 80, -1.55), (3000, 160, 1), m=mg_water_mat("river", (0.03, 0.05, 0.06), 0.03, 0.15))
    # the camp: a kuriyen ring round the leader's great white ger, doors to the south
    mg_ger(camp[0], camp[1], 1.0, 3.7, "white", 0.0)
    smoke_at = [(camp[0], camp[1], 1.0 + mg_ger_profile(3.7)[1])]
    for i in range(15):
        a = 2 * math.pi * i / 15 + 0.2
        x, y = camp[0] + 40 * math.cos(a) * 1.15, camp[1] + 40 * math.sin(a) * 0.8
        R = rng.uniform(2.5, 3.1)
        felt = "black" if i in (4, 11) else ("grey" if i % 3 == 0 else "white")
        top = mg_ger(x, y, h(x, y), R, felt, rng.uniform(-0.15, 0.15))
        if i in (2, 7, 9, 13):
            smoke_at.append((x, y, h(x, y) + top))
    for k in range(5):
        x, y = rng.uniform(40, 140), rng.uniform(200, 330)
        mg_ger(x, y, h(x, y), rng.uniform(2.5, 3.0), "white" if k % 2 else "grey", rng.uniform(-0.15, 0.15))
    for i, (x, y, z) in enumerate(smoke_at):
        mg_smoke(x, y, z + 0.3, 26, 1.4, 0.9, (0.55, 0.52, 0.5), (-0.28, 0.05), seed=i * 3.1)
    mg_cart_ger(75, 225, h(75, 225), math.pi)
    for k in range(4):                                                          # camel train with felt-covered box carts
        x, y = -130 + k * 9.5, 222
        mg_inst(mg_camel_me(), (x + 3.2, y, h(x + 3.2, y)), 0.0, 1.0, MG_M.setdefault("camelhide", noisy("camelhide", (0.42, 0.32, 0.2), (0.55, 0.43, 0.28), 4, 0.9, 0.15)))
        mg_box_cart(x, y, h(x, y), 0.0)
    mg_herd(42, 112, 24, 22, 12, h, rng, 0.65)
    mg_herd(-115, 105, 14, 14, 8, h, rng, 0.7)
    mg_herd(-10, 230, 10, 12, 8, h, rng, 0.5)
    mg_flock(10, 205, 45, 14, 7, h, rng)
    h0 = h(-4, -20)
    mg_camera([(0.0, (-6, -22, h0 + 2.4)), (1.0, (-2.5, -19.5, h0 + 2.3))], 30, [(0.0, (-20, 200, 6)), (1.0, (-16, 200, 6))])
    mg_aerial(info["haze"], 2600, 0.93)
    return sc


def shot_m_ger_inside():
    """Inside an elite ger, c. 1240 (Rubruck/Carpini): looking north from the door to the master's seat."""
    sc = reset()
    mg_render_tweaks(sc, vol=True)
    sc.cycles.max_bounces = 6
    mg_sky("kloppenheim_06_puresky", 0.8, sun_az=-55, sun_el=56, sun_power=7.0, sun_col=(1.0, 0.88, 0.72), view_az=90)
    exposure(-0.35)
    M = mg_gmats()
    R, HW, TOP, CR = 4.0, 1.75, 4.4, 0.75
    wood = mg_ph("willow", "rough_wood", 1.2, tint=(0.82, 0.6, 0.4), fb=(0.4, 0.28, 0.16))
    felt_in = mg_felt_mat("feltin", (0.7, 0.64, 0.54), (0.8, 0.75, 0.65), dirt=(0.4, 0.34, 0.27), dirt_h=0.5, smoke_top=(2.6, 4.4))
    fl = MgB()
    fl.cyl((0, 0, -0.05), R + 0.3, 0.05, 48)
    fl.finish("floor", mg_felt_mat("floorfelt", (0.42, 0.36, 0.28), (0.52, 0.45, 0.35), dirt=(0.3, 0.25, 0.2), dirt_h=0.0))
    add("plane", (0, 0, -0.12), (40, 40, 1), m=mat("outside", (0.3, 0.32, 0.18), 0.9))
    lat = MgB()                                                                 # khana: interlaced willow lattice
    for k in range(84):
        a = 2 * math.pi * k / 84
        for sg in (1, -1):
            a2 = a + sg * 0.42
            lat.seg((R * math.cos(a), R * math.sin(a), 0.03), (R * math.cos(a2), R * math.sin(a2), HW), 0.022, n=4)
    lat.lathe([(R - 0.03, HW - 0.05), (R - 0.03, HW + 0.06)], 64)
    lat.finish("khana", wood)
    fw = MgB()
    fw.lathe([(R + 0.07, -0.05), (R + 0.07, HW + 0.08)], 64)
    prof = []
    for k in range(13):
        f = k / 12
        prof.append(((R + 0.07) * (1 - f) + (CR + 0.06) * f, HW + 0.08 + (TOP - HW) * math.sin(f * math.pi / 2) ** 0.85))
    fw.lathe(prof, 64)
    fw.finish("feltwall", felt_in, True)
    po = MgB()                                                                  # roof poles (uni) to the crown ring (toono)
    for k in range(66):
        a = 2 * math.pi * k / 66
        ca, sa = math.cos(a), math.sin(a)
        po.poly([((r - 0.06) * ca, (r - 0.06) * sa, z - 0.05) for (r, z) in prof[::3]] + [(CR * ca, CR * sa, TOP - 0.02)], 0.032, 0.026, 5)
    po.lathe([(CR - 0.02, TOP - 0.08), (CR + 0.13, TOP - 0.08), (CR + 0.13, TOP + 0.12), (CR - 0.02, TOP + 0.12), (CR - 0.02, TOP - 0.08)], 48)
    for rot_ in (0.0, math.pi / 2):
        pts = []
        for i in range(11):
            t = -1 + 2 * i / 10
            pts.append((t * CR * math.cos(rot_), t * CR * math.sin(rot_), TOP + 0.1 + 0.35 * (1 - t * t)))
        po.poly(pts, 0.035, n=5)
    for sx in (-0.55, 0.55):                                                    # two central posts (bagana)
        po.seg((sx, 0.9, 0), (sx * 0.9, 0.75, TOP - 0.05), 0.075, 0.06, 8)
    po.finish("poles", wood)
    hb = MgB()                                                                  # open hearth: ring of stones, iron tripod, cauldron
    for k in range(11):
        a = 2 * math.pi * k / 11
        hb.ico((0.6 * math.cos(a), 0.2 + 0.6 * math.sin(a), 0.08), 0.17, (1.2, 1, 0.7), 1)
    hb.finish("hearthstones", mg_ph("hstone", "rock_face", 1.5, tint=(0.6, 0.55, 0.5), fb=(0.35, 0.33, 0.3)), True)
    iron = mat("iron", (0.06, 0.055, 0.05), 0.5, 0.6)
    ib = MgB()
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        ib.seg((0.75 * math.cos(a), 0.2 + 0.75 * math.sin(a), 0), (0, 0.2, 1.35), 0.025, n=5)
    ib.lathe([(0.05, 0.62), (0.3, 0.68), (0.4, 0.85), (0.38, 1.02), (0.34, 1.05)], 20, (0, 0.2, 0))
    ib.finish("tripod", iron, True)
    fire = mg_emit_mat("fire", (1.0, 0.42, 0.1), 14)
    fb_ = MgB()
    for k in range(5):
        a = 2 * math.pi * k / 5
        fb_.cyl((0.15 * math.cos(a), 0.2 + 0.15 * math.sin(a), 0.28), 0.14, 0.24, 8, r2=0.0)
    fb_.cyl((0, 0.2, 0.08), 0.42, 0.06, 12)
    fb_.finish("fire", fire)
    light("POINT", (0, 0.2, 0.55), 260, (1.0, 0.5, 0.2), 0.25)
    mg_smoke(0, 0.2, 0.7, TOP - 0.4, 0.5, 0.35, (0.6, 0.58, 0.55), (0.0, -0.05), seed=1.0, speed=0.5)
    sunv = Vector((math.cos(math.radians(56)) * math.cos(math.radians(-55)), math.cos(math.radians(56)) * math.sin(math.radians(-55)),
                   math.sin(math.radians(56))))
    end = Vector((0, 0, TOP)) - sunv * (TOP / sunv.z)
    mg_shaft((0, 0, TOP + 0.2), tuple(end), CR * 0.85, (1.0, 0.86, 0.62), 0.9)
    brocade = mg_nasij("brocade", (0.05, 0.07, 0.2))
    brocade2 = mg_nasij("brocade2", (0.35, 0.05, 0.04))
    fur = mg_ph("fur", "curly_teddy_natural", 1.2, tint=(1.0, 0.92, 0.8), fb=(0.8, 0.75, 0.65))
    leather = mg_ph("leather", "brown_leather", 1.0, tint=(0.9, 0.7, 0.5), fb=(0.35, 0.22, 0.12))

    def polar(th, r, z=0.0):
        return (r * math.cos(math.radians(th)), r * math.sin(math.radians(th)), z)
    bed = MgB()                                                                 # the master's seat-bed at the north
    bed.box((0, R - 1.05, 0.22), (1.5, 0.6, 0.22))
    bed.finish("bed", mg_painted_mat("bedpaint", (0.45, 0.1, 0.05)))
    fr = MgB()
    fr.box((0, R - 1.05, 0.5), (1.45, 0.56, 0.07))
    fr.finish("bedfur", fur)
    cu = MgB()
    for x in (-0.9, 0, 0.9):
        cu.box((x, R - 0.6, 0.75), (0.38, 0.14, 0.24))
    cu.finish("cushions", brocade2)
    hg = MgB()                                                                  # brocade hangings on the lattice
    for th, w_ in ((90, 1.7), (128, 0.7), (52, 0.7), (205, 0.8), (-25, 0.8)):
        x, y, _ = polar(th, R - 0.06)
        hg.box((x, y, 1.05), (w_, 0.025, 0.75), (0, 0, math.radians(th + 90)))
    hg.finish("hangings", brocade)
    ido = MgB()                                                                 # felt ongghot idols above the master and mistress
    for x in (-0.55, 0.55):
        ido.ico((x, R - 0.16, 1.52), 0.08, (1.0, 0.6, 2.0), 2)
        ido.ico((x, R - 0.16, 1.78), 0.07, (1, 1, 1), 2)
    ido.finish("ongghot", MG_M["white"], True)
    ch = MgB()                                                                  # painted chests along the walls
    for th, rr in ((160, R - 0.55), (175, R - 0.55), (25, R - 0.55), (38, R - 0.55)):
        x, y, _ = polar(th, rr)
        ch.box((x, y, 0.36), (0.55, 0.32, 0.36), (0, 0, math.radians(th + 90)))
    ch.finish("chests", mg_painted_mat("chestpaint", (0.52, 0.12, 0.05), (0.85, 0.62, 0.22), (0.1, 0.22, 0.45)))
    se = MgB()                                                                  # men's felt seat (west), women's seat (east)
    for th in (195, 212, -8):
        x, y, _ = polar(th, R - 0.8)
        se.box((x, y, 0.18), (0.75, 0.42, 0.18), (0, 0, math.radians(th + 90)))
    se.finish("seats", fur)
    kb = MgB()                                                                  # leather koumiss bag by the door
    x, y, _ = polar(-38, R - 0.55)
    kb.ico((x, y, 0.55), 0.32, (1, 0.8, 1.6), 2)
    kb.seg((x, y, 0.95), (x, y, 1.25), 0.05)
    kb.finish("koumiss", leather, True)
    bc = MgB()                                                                  # bowcase and quiver hanging on the lattice
    x, y, _ = polar(185, R - 0.1)
    bc.box((x, y + 0.5, 1.25), (0.05, 0.22, 0.45), (0, 0, 0.0))
    bc.box((x, y - 0.4, 1.15), (0.05, 0.12, 0.4))
    bc.finish("bowcase", leather)
    r1 = add("plane", (0.3, -1.5, 0.012), (1.7, 1.05, 1), m=mg_rug_mat("rug1"))
    r2 = add("plane", (-2.15, 0.9, 0.014), (1.4, 0.8, 1), (0, 0, math.radians(75)), m=mg_rug_mat("rug2", (0.1, 0.12, 0.3), (0.45, 0.07, 0.05), (0.8, 0.62, 0.3)))
    r3 = add("plane", (2.15, 0.9, 0.014), (1.4, 0.8, 1), (0, 0, math.radians(-75)), m=mg_applique_mat("shyrdak", (0.35, 0.06, 0.05)))
    r4 = add("plane", (0, 2.2, 0.016), (1.6, 0.7, 1), m=mg_rug_mat("rug3", (0.5, 0.25, 0.08), (0.2, 0.05, 0.04), (0.85, 0.72, 0.4), k=7))
    l1 = light("AREA", (0, 0, TOP - 0.25), 160, (0.85, 0.9, 1.0), 1.4)
    l2 = light("AREA", (0.3, -R + 0.5, 1.7), 220, (1.0, 0.88, 0.74), 2.2)
    l2.rotation_euler = (math.radians(90), 0, 0)
    l3 = light("AREA", (0, 1.0, 3.4), 70, (1.0, 0.7, 0.45), 3.0)
    for l in (l1, l2, l3):
        _try(l, visible_camera=False, visible_glossy=False)
    mg_camera([(0.0, (0.9, -3.25, 1.5)), (1.0, (0.55, -2.85, 1.47))], 17, [(0.0, (-0.35, 2.8, 1.62)), (1.0, (-0.5, 2.8, 1.58))])
    return sc


def shot_m_karakorum():
    """Karakorum c. 1254 (Rubruck): a modest town inside a low rammed-earth wall in the Orkhon valley; gers outnumber buildings."""
    sc = reset()
    mg_render_tweaks(sc, vol=True)
    info = mg_sky("evening_road_01_puresky", 0.9, sun_az=150, sun_el=17, sun_power=4.5, sun_col=(1.0, 0.8, 0.58), view_az=90)
    exposure(0.2)
    rng = random.Random(5)

    def h(x, y):
        z = 11.0 * (1 - mg_ss(10, 150, math.hypot(x * 0.8, y + 45)))
        z += mg_fbm(x / 40, y / 40, 2, 2) * 0.35
        z += (mg_fbm(x / 800, y / 800, 4, 3) + 0.5) * 110 * mg_ss(1000, 2200, y)
        z += (mg_fbm(x / 500, y / 500, 3, 4) + 0.5) * 70 * mg_ss(600, 1300, abs(x))
        z += mg_ridge(x / 1600, y / 1600, 5, 7) ** 1.4 * 700 * mg_ss(2600, 5200, y)
        return z

    def dens(x, y):
        return (1 - mg_ss(18, 55, math.hypot(x, y + 30))) * mg_ss(-60, -50, y)
    gm = mg_ground_mat("orkhon", [("leafy_grass", 0.35, (0.95, 0.9, 0.66)), ("withered_grass", 0.3, (1.0, 0.92, 0.72)),
                                  ("dry_ground_01", 0.25, (0.9, 0.82, 0.68))], 0.01,
                       extra=[("rocky_terrain_02", 0.01, (0.85, 0.85, 0.8), mg_mask_height(150, 450, 100))])
    ground = mg_terrain("orkhon", 7000, 440, h, gm, 0, 150, 2.2, dens)
    mg_grass(ground, 30000, 0.26, mg_grass_mat("grass", (0.06, 0.07, 0.03), (0.32, 0.34, 0.12), (0.6, 0.52, 0.26)), 8, 0.0035, 4)
    X0, X1, Y0, Y1 = -320.0, 280.0, 230.0, 640.0                                 # walled town (compressed for the frame)
    earth = mg_rammed_mat("kkwall", (0.86, 0.72, 0.52), "clay_plaster", 0.3)
    wb = MgB()
    for (p0, p1) in (((X0, Y0), (-9, Y0)), ((9, Y0), (X1, Y0)), ((X1, Y0), (X1, Y1)), ((X1, Y1), (X0, Y1)), ((X0, Y1), (X0, Y0))):
        mg_earth_wall(wb, p0, p1, 4.6, 7.0, 3.2)
    for x in (-13, 13):
        wb.frustum((x, Y0, -1), 4.5, 5.0, 3.6, 4.0, 6.5)
    wb.finish("kkwall", earth)
    mg_hall(0, Y0, 3, 1, 3.6, 3.6, 6.4, 0.0, front_doors=False, rise_k=0.55)       # gatehouse over the south gate
    green = mg_tile_mat("greenglaze", (0.12, 0.36, 0.18), 0.25)
    greyt = MG_M.setdefault("greytile", mg_tile_mat("greytile", (0.3, 0.3, 0.31), 0.6))
    mg_hall(-120, 470, 7, 4, 5.0, 6.2, 2.6, 0.0, roof_m=green, ridge_m=green, double=True)  # Ogedei's palace hall (interpretation)
    pw = MgB()
    for (p0, p1) in (((-185, 420), (-55, 420)), ((-55, 420), (-55, 530)), ((-55, 530), (-185, 530)), ((-185, 530), (-185, 420))):
        mg_earth_wall(pw, p0, p1, 3.2, 1.6, 1.0)
    pw.finish("palacewall", MG_M["hall"]["wall"])
    for (x, y, nx_, ny_) in ((90, 540, 3, 2), (190, 440, 3, 2), (-250, 590, 3, 2)):   # temples (green ridges)
        mg_hall(x, y, nx_, ny_, 4.2, 4.6, 1.4, 0.0, roof_m=greyt, ridge_m=green)
    plaster = mg_ph("whitewash", "white_plaster_02", 0.3, tint=(0.95, 0.9, 0.82), fb=(0.85, 0.8, 0.72))
    mud = mg_ph("mudplaster", "clay_plaster", 0.35, tint=(0.88, 0.74, 0.56), fb=(0.65, 0.52, 0.38))
    hb, rb, mb = MgB(), MgB(), MgB()
    for _ in range(46):                                                         # Cathayan quarter: grey-tiled courtyard houses
        x, y = rng.uniform(30, 260), rng.uniform(260, 620)
        if abs(x - 190) < 20 and abs(y - 440) < 16 or abs(x - 90) < 20 and abs(y - 540) < 16:
            continue
        w, d = rng.uniform(4, 7), rng.uniform(3, 5)
        hb.box((x, y, 1.6), (w, d, 1.8))
        rb.gable((x, y, 3.4), w, d, 2.2, 0.5)
    for _ in range(40):                                                         # Saracen quarter: flat-roofed mud-brick
        x, y = rng.uniform(-300, -40), rng.uniform(250, 410)
        w, d, hh = rng.uniform(4, 8), rng.uniform(4, 7), rng.uniform(2.8, 4.5)
        mb.box((x, y, hh / 2 - 0.5), (w, d, hh / 2 + 0.5))
    hb.finish("houses", plaster)
    rb.finish("houseroofs", greyt)
    mb.finish("mudhouses", mud)
    brick = mg_ph("kkbrick", "yellow_brick", 0.9, tint=(1.0, 0.9, 0.75), fb=(0.65, 0.5, 0.35))
    mq = MgB()                                                                  # one of the two mosques: brick hall + small minaret
    mq.box((-210, 330, 3), (11, 8, 4))
    mq.cyl((-196, 322, 8), 1.4, 8, 16, r2=1.1)
    mq.cyl((-196, 322, 16.6), 1.8, 0.4, 16)
    mq.finish("mosque", brick)
    aw = MgB()                                                                  # market square awnings (Saracen quarter)
    cloths = [mat("aw%d" % i, c, 0.9) for i, c in enumerate(((0.62, 0.48, 0.32), (0.5, 0.18, 0.12), (0.7, 0.62, 0.45)))]
    for i in range(14):
        x, y = -110 + (i % 5) * 9 + rng.uniform(-1, 1), 290 + (i // 5) * 9
        aw.box((x, y, 2.6), (3.2, 2.4, 0.05), (rng.uniform(-0.1, 0.1), 0, 0))
    aw.finish("awnings", cloths[1])
    for k, (x, y) in enumerate(((150, 360), (210, 520), (60, 300))):            # kilns (green-glazed tiles, iron)
        mg_smoke(x, y, 3, 60, 5, 0.35, (0.45, 0.43, 0.42), (-0.3, 0.05), seed=k * 2.3)
    tb = MgB()                                                                  # granite turtle with its stele, by the road
    tz = h(22, 150)
    tb.ico((22, 150, tz + 0.5), 1.0, (1.7, 1.15, 0.6), 2)
    tb.ico((22, 148, tz + 0.55), 0.35, (1, 1.2, 0.8), 2)
    tb.box((22, 150.4, tz + 2.2), (0.85, 0.22, 1.5))
    tb.finish("turtle", mg_ph("granite", "granite_tile", 0.4, tint=(0.7, 0.68, 0.66), fb=(0.5, 0.5, 0.48)), True)
    gx = []                                                                     # the ger city outside the walls
    for _ in range(80):
        x, y = rng.uniform(-330, 320), rng.uniform(20, 220)
        if abs(x) < 16 or math.hypot(x, y + 40) < 75 or any(math.hypot(x - a, y - b) < 9 for a, b in gx):
            continue
        gx.append((x, y))
        top = mg_ger(x, y, h(x, y), rng.uniform(2.4, 3.1), rng.choice(("white", "white", "grey", "grey", "black")), rng.uniform(-0.2, 0.2))
        if len(gx) % 11 == 0:
            mg_smoke(x, y, h(x, y) + top + 0.3, 20, 1.2, 0.8, (0.55, 0.52, 0.5), (-0.3, 0.05), seed=len(gx))
    mg_herd(-150, 140, 18, 25, 12, h, rng, 0.6)
    mg_herd(160, 120, 14, 20, 10, h, rng, 0.6)
    for k in range(3):
        mg_box_cart(30 + k * 6, 110 + k * 2, h(30 + k * 6, 110), 1.5)
    hz = h(-6, -46)
    mg_camera([(0.0, (-8, -48, hz + 2.6)), (1.0, (-4, -45, hz + 2.5))], 32, [(0.0, (-40, 420, 6)), (1.0, (-36, 420, 6))])
    mg_aerial(info["haze"], 3500, 0.9)
    return sc


def mg_pagoda(x, y, z, m_body, m_eave):
    """Liao/Jin dense-eave octagonal brick pagoda (Tianning type, c. 1120): base, tall first storey, 13 close eaves."""
    b, e = MgB(), MgB()
    r8 = (0, 0, math.pi / 8)
    b.cyl((x, y, z + 1.5), 10, 1.5, 8, rot=r8)
    b.cyl((x, y, z + 5), 8, 2, 8, r2=7.4, rot=r8)
    b.cyl((x, y, z + 12.5), 6.0, 5.5, 8, r2=5.8, rot=r8)
    e.cyl((x, y, z + 18.3), 7.6, 0.35, 8, r2=6.3, rot=r8)
    zz = z + 18.6
    for k in range(13):
        hk = 2.4 - 0.06 * k
        rk = 6.0 * (1 - 0.035 * k) * (1 + 0.04 * math.sin(math.pi * k / 12))
        b.cyl((x, y, zz + hk / 2), rk - 0.6, hk / 2, 8, rot=r8)
        e.cyl((x, y, zz + hk - 0.15), rk + 0.9, 0.22, 8, r2=rk, rot=r8)
        zz += hk
    b.cyl((x, y, zz + 1.2), 1.5, 1.2, 8, r2=0.8, rot=r8)
    b.cyl((x, y, zz + 4.0), 0.3, 1.8, 8, r2=0.1)
    b.finish("pagoda", m_body)
    e.finish("pagodaeaves", m_eave)
    return zz + 5.8


def mg_trebuchet(wood_b, rope_b, x, y, z, s=1.0):
    """Traction trebuchet (pao, A-frame): crews pull ropes on the short arm. No counterweight before 1273."""
    for sx in (-1.6, 1.6):
        for sy in (-2.3, 2.3):
            wood_b.seg((x + sx * s, y + sy * s, z), (x + sx * s, y, z + 6.2 * s), 0.13 * s, 0.1 * s, 6)
        wood_b.seg((x + sx * s, y - 1.6 * s, z + 2.0 * s), (x + sx * s, y + 1.6 * s, z + 2.0 * s), 0.08 * s, n=5)
    wood_b.seg((x - 2.0 * s, y, z + 6.2 * s), (x + 2.0 * s, y, z + 6.2 * s), 0.17 * s, n=8)
    a, b = Vector((x, y - 7.0 * s, z + 1.6 * s)), Vector((x, y + 2.9 * s, z + 8.4 * s))
    wood_b.seg(tuple(a), tuple(b), 0.2 * s, 0.13 * s, 8)
    rope_b.seg(tuple(a), (x, y - 7.4 * s, z + 0.5 * s), 0.03 * s, n=4)
    rope_b.box((x, y - 7.4 * s, z + 0.45 * s), (0.25 * s, 0.2 * s, 0.12 * s))
    for k in range(12):
        gx = x + (k - 5.5) * 0.45 * s
        rope_b.seg(tuple(b), (gx, y + (6.0 + (k % 3) * 1.4) * s, z + 0.1), 0.02 * s, n=3)


def shot_m_zhongdu():
    """Siege of the Jin Central Capital (Zhongdu), 1215, from the Mongol lines."""
    sc = reset()
    mg_render_tweaks(sc, vol=True)
    info = mg_sky("wasteland_clouds_puresky", 0.95, sun_az=35, sun_el=24, sun_power=4.2, sun_col=(1.0, 0.84, 0.64), view_az=90)
    exposure(0.1)
    rng = random.Random(8)
    WY = 110.0                                                                  # outer foot of the city wall

    def h(x, y):
        z = mg_fbm(x / 60, y / 60, 3, 1) * 0.5
        z += mg_ridge(x / 1800, y / 1800, 5, 3) ** 1.3 * 650 * mg_ss(2500, 5500, y) * mg_ss(800, -1500, x)
        k = 1 - mg_ss(7, 11, abs(y - 79))                                       # moat
        return z * (1 - k) - 2.6 * k

    gm = mg_ground_mat("loess", [("dry_ground_rocks", 0.3, (1.0, 0.92, 0.78)), ("brown_mud_dry", 0.3, (1.0, 0.9, 0.75)),
                                 ("dirt", 0.3, (1.05, 0.95, 0.8))], 0.015, fb=(0.6, 0.5, 0.36))
    mg_terrain("plain", 7000, 400, h, gm, 0, 60, 2.2)
    add("plane", (0, 79, -1.4), (2000, 10, 1), m=mg_water_mat("moat", (0.06, 0.07, 0.05), 0.06, 0.1))
    earth = mg_rammed_mat("hangtu", (0.85, 0.72, 0.54), "brown_mud_dry", 0.3)
    wb, mb = MgB(), MgB()
    T = 15.0                                                                    # wall: 13 m high, 20 m base, 12 m top
    mg_earth_wall(wb, (-1500, WY + 10), (-52, WY + 10), 13, 20, 12, -1, mb)
    mg_earth_wall(wb, (2, WY + 10), (1500, WY + 10), 13, 20, 12, -1, mb)
    for k in range(-14, 16):                                                    # horse-face bastions every 72 m
        x = -25 + k * 72
        if abs(x + 25) < 50:
            continue
        wb.frustum((x, WY - 3, -1), 7.5, 7.5, 6.0, 5.8, 14)
        for i in range(4):
            mb.box((x - 4.5 + i * 3, WY - 8.5, 13.55), (0.6, 0.3, 0.55))
    wb.finish("wall", earth)
    mb.finish("merlons", earth)
    gbrick = mg_ph("greybrick", "yellow_brick", 0.9, tint=(0.66, 0.66, 0.68), fb=(0.45, 0.45, 0.45))
    gb = MgB()                                                                  # brick-faced gate block + barbican (wengcheng)
    gb.frustum((-25, WY + 6, -1), 28, 14, 25.5, 12, 15)
    for (p0, p1) in (((-55, 88), (5, 88)), ((-55, 88), (-55, WY - 2)), ((5, 88), (5, WY - 2))):
        mg_earth_wall(gb, p0, p1, 10.5, 7, 5)
    gb.finish("gate", gbrick)
    dark = mat("dark", (0.02, 0.018, 0.015), 1.0)
    dk = MgB()
    dk.box((-25, WY - 8.05, 3.5), (3.0, 0.1, 3.5))
    dk.cyl((-25, WY - 8.05, 7.0), 3.0, 0.1, 16, rot=(math.pi / 2, 0, 0))
    dk.box((-25, 84.4, 3.0), (2.6, 0.1, 3.0))
    dk.cyl((-25, 84.4, 6.0), 2.6, 0.1, 16, rot=(math.pi / 2, 0, 0))
    dk.finish("passages", dark)
    br = MgB()                                                                  # timber bridge over the moat
    br.box((-25, 76, 0.6), (3.5, 8, 0.25))
    for yy in (70, 76, 82):
        for xx in (-28, -22):
            br.seg((xx, yy, -2.5), (xx, yy, 0.5), 0.18, n=6)
    br.finish("bridge", MG_M.setdefault("planks", mg_ph("planks", "weathered_planks", 0.6, tint=(0.75, 0.62, 0.48), fb=(0.4, 0.3, 0.2))))
    greyt = MG_M.setdefault("greytile", mg_tile_mat("greytile", (0.3, 0.3, 0.31), 0.6))
    green = mg_tile_mat("jingreen", (0.13, 0.33, 0.2), 0.25)
    mg_hall(-25, WY + 6, 5, 2, 4.4, 5.0, 1.2, 14.0, roof_m=greyt, ridge_m=green, double=True)   # gate tower
    for x in (-169, 119, 263):                                                  # watch pavilions on bastions
        mg_hall(x, WY - 2, 2, 1, 3.4, 3.4, 0.6, 13.0, roof_m=greyt, ridge_m=green, rise_k=0.6)
    mg_pagoda(150, 520, 0.0, mg_ph("pagodabrick", "yellow_brick", 0.9, tint=(0.72, 0.7, 0.68), fb=(0.5, 0.5, 0.48)), greyt)
    mg_hall(-260, 620, 9, 4, 5.2, 9.0, 4.0, 0.0, roof_m=green, ridge_m=green, double=True)    # Jin palace roofs beyond
    wood = MG_M.setdefault("timber", mg_ph("timber", "rough_wood", 0.6, tint=(0.8, 0.65, 0.5), fb=(0.4, 0.3, 0.2)))
    tw, tr = MgB(), MgB()
    for (x, y) in ((-62, 44), (-24, 36), (24, 40), (58, 50)):
        mg_trebuchet(tw, tr, x, y, h(x, y))
        tw.box((x, y + 9.5, 1.3), (3.2, 0.12, 1.3))                            # mantlet screen
    pal = MgB()
    for k in range(60):                                                         # palisade
        x = -330 + k * 11
        if abs(x + 10) < 30:
            continue
        pal.seg((x, 62, -0.5), (x + rng.uniform(-0.3, 0.3), 62, 2.4), 0.12, 0.08, 5)
        pal.seg((x, 62, 1.6), (x + 11, 62, 1.6), 0.06, n=4)
    tw.finish("trebuchets", wood)
    tr.finish("ropes", MG_M.setdefault("hemp", mat("hemp", (0.45, 0.38, 0.26), 0.9)))
    pal.finish("palisade", wood)
    st = MgB()
    for _ in range(40):
        x, y = rng.choice((-62, -24, 24, 58)) + rng.uniform(-4, 4), rng.uniform(26, 34)
        st.ico((x, y, 0.3), rng.uniform(0.25, 0.4), (1, 1, 0.9), 1)
    st.finish("stones", mg_ph("stoneballs", "rock_face", 1.2, tint=(0.75, 0.72, 0.68), fb=(0.5, 0.48, 0.45)), True)
    for k in range(22):                                                         # Mongol camp to the sides
        x = rng.choice((-1, 1)) * rng.uniform(70, 260)
        y = rng.uniform(15, 66)
        mg_ger(x, y, h(x, y), rng.uniform(2.3, 2.9), rng.choice(("grey", "white", "black")), rng.uniform(-0.3, 0.3))
    mg_herd(-90, 20, 14, 14, 6, h, rng, 0.5)
    for k, (x, y, r_) in enumerate(((-210, 420, 26), (90, 480, 32), (330, 360, 22), (-420, 520, 28))):
        mg_smoke(x, y, 2, 210, r_, 0.13, (0.16, 0.14, 0.13), (-0.25, 0.08), seed=k * 1.7, speed=0.2)
    mg_smoke(-180, 20, 0.5, 25, 2.0, 0.6, (0.45, 0.42, 0.4), (-0.3, 0.05), seed=9)
    mg_camera([(0.0, (-6, -32, 3.0)), (1.0, (-2.5, -30, 3.0))], 26, [(0.0, (-14, 110, 6.5)), (1.0, (-10, 110, 6.5))])
    mg_aerial(info["haze"], 3200, 0.85)
    return sc


def mg_kalyan(x, y, z):
    """Kalyan minaret, Bukhara (1127): tapering baked-brick shaft in bands of different bond, 16-arch lantern,
    muqarnas corbel cornice, a single thin turquoise band. c. 46 m."""
    mats = {"A": mg_ph("kbA", "yellow_brick", 1.1, tint=(1.12, 0.92, 0.72), fb=(0.75, 0.58, 0.4)),
            "B": mg_ph("kbB", "herringbone_brick", 0.8, tint=(1.5, 1.18, 0.86), fb=(0.72, 0.55, 0.38)),
            "C": mg_ph("kbC", "patterned_brick_wall", 0.6, tint=(1.3, 1.08, 0.82), fb=(0.72, 0.56, 0.4)),
            "band": mg_ph("kbband", "clay_plaster", 0.6, tint=(1.0, 0.82, 0.62), fb=(0.8, 0.62, 0.45)),
            "turq": mat("turquoise", (0.06, 0.42, 0.42), 0.3),
            "dark": mat("karch", (0.05, 0.04, 0.03), 0.9)}
    bs = {k: MgB() for k in mats}
    r0, r1, Ht = 4.6, 3.05, 33.0

    def rad(zz):
        return r0 + (r1 - r0) * zz / Ht
    secs = [(0, 3.5, "A"), (3.5, 4.0, "band"), (4.0, 9.0, "B"), (9.0, 9.5, "band"), (9.5, 14.5, "C"), (14.5, 15.0, "band"),
            (15.0, 20.0, "A"), (20.0, 20.5, "band"), (20.5, 25.5, "B"), (25.5, 26.0, "band"), (26.0, 30.5, "C"), (30.5, 31.1, "band"),
            (31.1, 33.0, "A")]
    bs["A"].cyl((x, y, z - 0.5), r0 + 0.4, 0.9, 32)
    for z0, z1, k in secs:
        e = 0.07 if k == "band" else 0.0
        bs[k].cyl((x, y, z + (z0 + z1) / 2), rad(z0) + e, (z1 - z0) / 2, 40, r2=rad(z1) + e)
    bs["B"].cyl((x, y, z + 35.8), 3.35, 2.8, 40)                                # lantern rotunda
    for k in range(16):
        a = 2 * math.pi * k / 16
        cx_, cy_ = x + 3.37 * math.cos(a), y + 3.37 * math.sin(a)
        bs["dark"].box((cx_, cy_, z + 35.3), (0.4, 0.06, 1.2), (0, 0, a + math.pi / 2))
        bs["dark"].ico((cx_, cy_, z + 36.5), 0.4, (1.0, 0.15, 1.15), 1, (0, 0, a + math.pi / 2))
    bs["turq"].cyl((x, y, z + 38.8), 3.42, 0.2, 40)
    for t in range(3):                                                          # muqarnas corbel tiers
        rr = 3.45 + 0.25 * t
        bs["band"].cyl((x, y, z + 39.25 + 0.55 * t), rr - 0.1, 0.27, 40)
        for k in range(24):
            a = 2 * math.pi * (k + 0.5 * t) / 24
            bs["A"].box((x + rr * math.cos(a), y + rr * math.sin(a), z + 39.25 + 0.55 * t), (0.22, 0.2, 0.26), (0, 0, a))
    bs["band"].cyl((x, y, z + 40.85), 4.15, 0.22, 40)
    bs["A"].cyl((x, y, z + 42.8), 2.25, 1.8, 32)
    for k in range(8):
        a = 2 * math.pi * k / 8
        bs["dark"].box((x + 2.27 * math.cos(a), y + 2.27 * math.sin(a), z + 42.8), (0.3, 0.05, 0.9), (0, 0, a + math.pi / 2))
    bs["band"].lathe([(2.35, 0.0), (2.2, 0.6), (1.6, 1.3), (0.6, 1.75), (0.0, 1.85)], 32, (x, y, z + 44.6))
    for k, b in bs.items():
        b.finish("kalyan_" + k, mats[k], k in ("A", "B", "C", "band", "turq"))


def mg_dome(b, x, y, z, r, pointed=1.15, seg=32):
    prof = []
    for k in range(10):
        a = math.pi / 2 * k / 9
        prof.append((r * math.cos(a), r * math.sin(a) * pointed + (r * 0.12 * (k / 9) ** 3 if pointed > 1 else 0)))
    prof.append((0.0, prof[-1][1]))
    b.lathe(prof, seg, (x, y, z))


def shot_m_bukhara():
    """Bukhara, February 1220: the Kalyan minaret (spared) above the burning Friday mosque; the Ark on its mound at left."""
    sc = reset()
    mg_render_tweaks(sc, vol=True)
    info = mg_sky("hilly_terrain_01_puresky", 0.9, sun_az=-35, sun_el=26, sun_power=4.4, sun_col=(1.0, 0.86, 0.68), view_az=95)
    exposure(0.0)
    rng = random.Random(3)

    def h(x, y):
        return mg_fbm(x / 50, y / 50, 3, 2) * 0.25 + mg_fbm(x / 600, y / 600, 3, 5) * 6 * mg_ss(800, 2000, y)
    gm = mg_ground_mat("square", [("dirt", 0.3, (1.05, 0.95, 0.8)), ("dry_ground_rocks", 0.3, (1.05, 0.95, 0.8)),
                                  ("brown_mud_dry", 0.3, (1.1, 0.98, 0.82))], 0.02, fb=(0.62, 0.52, 0.38))
    mg_terrain("bukhara", 6000, 360, h, gm, 0, 80, 2.2)
    mg_kalyan(-15, 170, 0.0)
    brick = mg_ph("buffbrick", "yellow_brick", 1.0, tint=(1.12, 0.92, 0.72), fb=(0.75, 0.58, 0.4))
    carved = mg_ph("carvedbrick", "patterned_brick_wall", 0.6, tint=(1.3, 1.06, 0.8), fb=(0.72, 0.56, 0.4))
    mq, pq, dk = MgB(), MgB(), MgB()
    mq.box((40, 205, 5), (32, 32, 6))                                           # Friday mosque: brick walls, plain brick domes
    for (dx, dy, r) in ((22, 200, 6.5), (50, 190, 5.0), (58, 220, 5.0), (30, 228, 4.5)):
        mq.cyl((dx, dy, 11.5), r + 0.4, 0.6, 32)
        mg_dome(mq, dx, dy, 12, r, 1.18)
    pq.box((30, 171, 10), (8.5, 3.0, 10))                                       # pishtaq portal, carved brick
    dk.box((30, 167.9, 6.0), (4.0, 0.1, 6.0))
    dk.ico((30, 167.9, 12.0), 4.0, (1.0, 0.03, 1.25), 2)
    mq.finish("mosque", brick)
    pq.finish("pishtaq", carved)
    dk.finish("arch", mat("darkarch", (0.05, 0.04, 0.03), 0.9))
    for k, (x, y, r_) in enumerate(((35, 205, 14), (60, 222, 11), (15, 214, 9))):
        mg_smoke(x, y, 6, 170, r_, 0.16, (0.17, 0.14, 0.12), (-0.18, 0.1), seed=k * 2.1, speed=0.25)
    mud = mg_rammed_mat("arkwall", (0.88, 0.74, 0.56), "clay_plaster", 0.35, 0.7)
    ak = MgB()                                                                  # the Ark: citadel walls on a high mound
    ak.frustum((-130, 150, -1), 55, 72, 44, 60, 15)
    for (p0, p1) in (((-172, 95), (-90, 95)), ((-90, 95), (-90, 205)), ((-90, 205), (-172, 205)), ((-172, 205), (-172, 95))):
        mg_earth_wall(ak, p0, p1, 25, 5, 3, 14)
    for (tx, ty) in ((-172, 95), (-90, 95), (-90, 205), (-131, 95), (-90, 150)):
        ak.cyl((tx, ty, 19), 4.8, 7, 20, r2=4.2)
    ak.frustum((-80, 128, -1), 7, 10, 3, 8, 14)                                 # ramp up to the gate
    ak.finish("ark", mud)
    plaster = mg_ph("mudhouse", "clay_plaster", 0.35, tint=(0.95, 0.8, 0.62), fb=(0.7, 0.56, 0.4))
    plaster2 = mg_ph("mudhouse2", "brown_mud_dry", 0.3, tint=(1.08, 0.92, 0.74), fb=(0.62, 0.5, 0.36))
    hb, hb2, dd, wd = MgB(), MgB(), MgB(), MgB()

    def house(b, x, y, w, d, hh, face=True):
        b.box((x, y, hh / 2 - 0.4), (w, d, hh / 2 + 0.4))
        b.box((x, y - d + 0.25, hh + 0.35), (w, 0.25, 0.35))
        if face:
            dd.box((x + rng.uniform(-w * 0.4, w * 0.4), y - d - 0.03, 1.1), (0.6, 0.05, 1.1))
            for _ in range(2):
                dd.box((x + rng.uniform(-w * 0.7, w * 0.7), y - d - 0.03, hh * 0.65), (0.35, 0.05, 0.45))
            for k in range(int(w)):
                wd.cyl((x - w + 0.6 + k * 2, y - d - 0.1, hh - 0.5), 0.1, 0.25, 6, rot=(math.pi / 2, 0, 0))
    for side in (-1, 1):                                                        # houses framing the square
        y = -5.0
        while y < 120:
            w, d = rng.uniform(4, 7), rng.uniform(4, 6)
            x = side * (44 + rng.uniform(0, 6) + w)
            if not (side < 0 and y > 70):
                house(hb if rng.random() < 0.6 else hb2, x, y, w, d, rng.uniform(4, 8), True)
            y += 2 * d + rng.uniform(0.5, 3)
    for _ in range(170):                                                        # the dense town behind
        x, y = rng.uniform(-60, 260), rng.uniform(120, 700)
        if -40 < x < 80 and 140 < y < 245 or math.hypot(x + 15, y - 170) < 12:
            continue
        w, d = rng.uniform(4, 9), rng.uniform(4, 8)
        house(hb if rng.random() < 0.6 else hb2, x, y, w, d, rng.uniform(3.5, 8.5), y < 260)
    for k in range(9):
        x, y = -30 + k * 7, 128 + rng.uniform(-2, 2)
        house(hb2, x, y, 3.2, 3.5, rng.uniform(4, 6), True)
    hb.finish("houses", plaster)
    hb2.finish("houses2", plaster2)
    dd.finish("openings", mat("doorway", (0.07, 0.05, 0.035), 0.9))
    wd.finish("beams", mg_ph("beamends", "rough_wood", 1.0, tint=(0.7, 0.55, 0.4), fb=(0.35, 0.25, 0.15)))
    cw = MgB()                                                                  # the outer city wall, far
    mg_earth_wall(cw, (-900, 760), (900, 760), 11, 9, 5)
    for k in range(-20, 21):
        cw.cyl((k * 45, 755, 6), 5, 7, 16, r2=4.2)
    cw.finish("citywall", mud)
    tb = MgB()                                                                  # bare winter trees (mulberry, elm)
    for (x, y) in ((-38, 58), (36, 30), (58, 96), (-20, 112), (90, 140), (-50, 125)):
        mg_tree(tb, None, x, y, 0, rng.uniform(8, 12), rng, "oak")
    tb.finish("trees", MG_M.setdefault("bark", mg_ph("bark", "bark_willow", 1.0, tint=(0.7, 0.62, 0.55), fb=(0.3, 0.25, 0.2))))
    mg_camera([(0.0, (8, -42, 1.9)), (1.0, (5, -39, 1.9))], 27, [(0.0, (-8, 160, 7.0)), (1.0, (-6, 160, 7.2))])
    mg_aerial(info["haze"], 3000, 0.8)
    return sc


def mg_wagon(b, cb, x, y, z, ang, covered=False):
    c, s = math.cos(ang), math.sin(ang)

    def P(lx, ly, lz):
        return (x + lx * c - ly * s, y + lx * s + ly * c, z + lz)
    b.box(P(0, 0, 1.0), (1.7, 0.75, 0.32), (0, 0, ang))
    for lx in (-1.1, 1.1):
        for ly in (-0.85, 0.85):
            cx, cy, cz = P(lx, ly, 0.55)
            b.cyl((cx, cy, cz), 0.55, 0.06, 14, rot=(math.pi / 2, 0, ang))
    if covered:
        cb.lathe([(0.8, -1.5), (0.8, 1.5)], 12, (0, 0, 0), 0, math.pi)


def shot_m_mohi():
    """The Sajo at Mohi, 10-11 April 1241: flat plain, timber bridge, early-spring trees, a Romanesque village church, and
    King Bela's wagon-fort camp on the far side."""
    sc = reset()
    mg_render_tweaks(sc)
    info = mg_sky("citrus_orchard_puresky", 1.0, sun_az=140, sun_el=26, sun_power=3.8, sun_col=(1.0, 0.92, 0.8), view_az=90)
    exposure(0.1)
    rng = random.Random(41)

    def riv(x):
        return 58 + 12 * math.sin(x / 90 + 0.5) + 5 * math.sin(x / 33)

    def h(x, y):
        z = mg_fbm(x / 80, y / 80, 3, 1) * 0.6 + mg_fbm(x / 20, y / 20, 2, 2) * 0.15
        z += (mg_fbm(x / 900, y / 900, 4, 3) + 0.5) * 140 * mg_ss(1500, 3000, y) * mg_ss(-200, 800, x)
        k = 1 - mg_ss(9, 22, abs(y - riv(x)))
        return z * (1 - k) - 2.2 * k

    def dens(x, y):
        return (1 - mg_ss(20, 60, math.hypot(x * 0.8, y + 5))) * mg_ss(-28, -22, y) * mg_ss(14, 20, abs(y - riv(x)))
    gm = mg_ground_mat("meadow", [("forrest_ground_01", 0.3, (0.95, 0.95, 0.8)), ("grass_ground", 0.3, (0.95, 0.95, 0.8))], 0.01,
                       extra=[("brown_mud", 0.35, (0.85, 0.8, 0.72), mg_mask_height(-0.2, -0.9, 0.3)),
                              ("farm_furrows", 0.25, (0.9, 0.82, 0.72),
                               lambda nt, pos: _math(nt, "MULTIPLY", _maprange(nt, _noise(nt, pos, 0.004, 2), 0.55, 0.58),
                                                     _maprange(nt, _sep(nt, pos)[1], 300, 380)))],
                       fb=(0.3, 0.35, 0.15))
    ground = mg_terrain("plain", 6000, 420, h, gm, 0, 60, 2.2, dens)
    mg_grass(ground, 60000, 0.2, mg_grass_mat("springgrass", (0.06, 0.08, 0.03), (0.28, 0.4, 0.12), (0.5, 0.48, 0.25)), 8, 0.003, 5)
    add("plane", (0, 60, -1.3), (3000, 60, 1), m=mg_water_mat("sajo", (0.07, 0.08, 0.06), 0.05, 0.12))
    planks = mg_ph("planks", "weathered_planks", 0.6, tint=(0.8, 0.68, 0.55), fb=(0.4, 0.3, 0.2))
    bb = MgB()                                                                  # timber trestle bridge
    BX = 28.0
    y0, y1 = riv(BX) - 24, riv(BX) + 24
    bb.box((BX, (y0 + y1) / 2, 1.3), (2.2, (y1 - y0) / 2, 0.18))
    for k in range(9):
        yy = y0 + 3 + k * (y1 - y0 - 6) / 8
        for xx in (BX - 1.9, BX, BX + 1.9):
            bb.seg((xx, yy, -2.6), (xx, yy, 1.2), 0.15, n=6)
        bb.box((BX, yy, 1.0), (2.3, 0.15, 0.15))
        for xx in (BX - 2.1, BX + 2.1):
            bb.seg((xx, yy, 1.4), (xx, yy, 2.4), 0.07, n=5)
    for xx in (BX - 2.1, BX + 2.1):
        bb.seg((xx, y0, 2.3), (xx, y1, 2.3), 0.06, n=5)
    bb.finish("bridge", planks)
    stone = mg_ph("churchstone", "old_stone_wall", 0.35, tint=(1.05, 1.0, 0.92), fb=(0.7, 0.66, 0.6))
    roofw = mg_ph("shingle", "weathered_planks", 0.9, tint=(0.55, 0.5, 0.46), fb=(0.3, 0.27, 0.25))
    cbx, cby = 112.0, 190.0                                                     # Romanesque church: nave, apse, west tower
    zc = h(cbx, cby)
    ch, cr = MgB(), MgB()
    ch.box((cbx, cby, zc + 3.0), (8.0, 4.0, 3.8))
    ch.cyl((cbx + 8.0, cby, zc + 2.8), 3.2, 3.6, 20)
    ch.box((cbx - 10.2, cby, zc + 8.0), (2.4, 2.4, 9.0))
    cr.gable((cbx, cby, zc + 6.8), 8.0, 4.0, 4.6, 0.5)
    cr.cyl((cbx + 8.0, cby, zc + 7.4), 3.6, 1.0, 20, r2=0.6)
    cr.cyl((cbx - 10.2, cby, zc + 19.2), 3.6, 2.2, 4, r2=0.05, rot=(0, 0, math.pi / 4))
    ch.finish("church", stone)
    cr.finish("churchroof", roofw)
    logs = mg_ph("logs", "wood_trunk_wall", 0.5, tint=(0.85, 0.75, 0.62), fb=(0.4, 0.3, 0.2))
    thatch = mg_ph("thatch", "thatch_roof_angled", 0.5, tint=(1.1, 1.0, 0.8), fb=(0.55, 0.45, 0.3))
    hw, hr, fe = MgB(), MgB(), MgB()
    for _ in range(16):                                                         # timber houses with steep thatch
        x, y = rng.uniform(80, 200), rng.uniform(130, 260)
        if math.hypot(x - cbx, y - cby) < 16:
            continue
        a = rng.choice((0.0, math.pi / 2)) + rng.uniform(-0.1, 0.1)
        z = h(x, y)
        hw.frustum((x, y, z - 0.5), 3.4, 2.4, 3.4, 2.4, 3.2, a)
        hr.gable((x, y, z + 2.7), 3.4, 2.4, 3.6, 0.6, a)
        fe.seg((x - 6, y - 5, z + 0.7), (x + 6, y - 5, z + 0.7), 0.05, n=4)
        for k in range(7):
            fe.seg((x - 6 + 2 * k, y - 5, z - 0.3), (x - 6 + 2 * k, y - 5, z + 1.0), 0.05, n=4)
    hw.finish("houses", logs)
    hr.finish("thatch", thatch)
    fe.finish("fences", planks)
    wf, cv = MgB(), MgB()                                                       # wagon fort: a ring of wagons round the tents
    FX, FY = -70.0, 205.0
    for k in range(28):
        a = 2 * math.pi * k / 28
        x, y = FX + 38 * math.cos(a), FY + 30 * math.sin(a)
        mg_wagon(wf, cv, x, y, h(x, y), a + math.pi / 2)
    wf.finish("wagons", planks)
    stripe_a = mg_stripe_mat("tentA", (0.75, 0.12, 0.1), (0.9, 0.86, 0.76))
    stripe_b = mg_stripe_mat("tentB", (0.16, 0.25, 0.5), (0.9, 0.86, 0.76))
    for k in range(9):
        x, y = FX + rng.uniform(-25, 25), FY + rng.uniform(-18, 18)
        z = h(x, y)
        t = MgB()
        t.cyl((0, 0, 0.9), 2.6, 1.0, 20)
        t.cyl((0, 0, 3.0), 2.9, 1.1, 20, r2=0.05)
        t.seg((0, 0, 3.5), (0, 0, 5.4), 0.04, n=4)
        t.finish("tent", stripe_a if k % 2 else stripe_b, False, (x, y, z), rng.uniform(0, 3))
    fl = MgB()
    for k in range(4):                                                          # Arpad red-and-silver barry flags
        x, y = FX + rng.uniform(-20, 20), FY + rng.uniform(-14, 14)
        z = h(x, y)
        fl.seg((x, y, z), (x, y, z + 8), 0.06, n=5)
        fl.box((x + 1.0, y, z + 7.2), (1.0, 0.02, 0.7))
    fl.finish("flags", mg_stripe_mat("arpad", (0.7, 0.08, 0.08), (0.88, 0.88, 0.86), axis=2, k=3.6))
    bark = mg_ph("bark", "bark_willow", 1.0, tint=(0.7, 0.62, 0.55), fb=(0.3, 0.25, 0.2))
    tb, lv, lv2 = MgB(), MgB(), MgB()
    for _ in range(22):                                                         # willows on the banks, in first leaf
        x = rng.uniform(-260, 260)
        y = riv(x) + rng.choice((-1, 1)) * rng.uniform(14, 22)
        if abs(x - BX) < 10 or (y < 40 and -70 < x < 60):
            continue
        mg_tree(tb, lv, x, y, h(x, y), rng.uniform(8, 12), rng, "willow")
    for _ in range(26):                                                         # bare oaks / ash, buds only
        x, y = rng.uniform(-300, 300), rng.uniform(110, 420)
        if math.hypot(x - FX, y - FY) < 48 or (80 < x < 200 and 130 < y < 260):
            continue
        mg_tree(tb, lv2, x, y, h(x, y), rng.uniform(10, 16), rng, "oak")
    for _ in range(60):                                                         # forest edge far
        x, y = rng.uniform(-900, 900), rng.uniform(520, 700)
        mg_tree(tb, lv2, x, y, h(x, y), rng.uniform(12, 18), rng, "oak")
    tb.finish("trees", bark)
    lv.finish("willowleaf", mg_leaf_mat("willowleaf", (0.42, 0.5, 0.16), (0.6, 0.65, 0.25), 0.35), True)
    lv2.finish("buds", mg_leaf_mat("buds", (0.32, 0.3, 0.16), (0.45, 0.45, 0.2), 0.2), True)
    mg_smoke(130, 230, h(130, 230) + 4, 30, 1.5, 0.7, (0.55, 0.53, 0.5), (-0.25, 0.1), seed=2)
    mg_smoke(FX + 5, FY, h(FX, FY) + 1, 22, 1.4, 0.7, (0.55, 0.53, 0.5), (-0.25, 0.1), seed=5)
    mg_camera([(0.0, (-6, -30, 2.3)), (1.0, (-2.5, -27.5, 2.25))], 30, [(0.0, (12, 160, 3.0)), (1.0, (15, 160, 3.0))])
    mg_aerial(info["haze"], 3000, 0.88)
    return sc


def mg_stripe_mat(name, c1, c2, k=6.0, axis=None):
    """Striped canvas. axis None = radial stripes (tents, object coords); 2 = horizontal bands (flags)."""
    m, nt, b = _mnew(name)
    oc = _tc(nt, "Object")
    s = _sep(nt, oc)
    if axis is None:
        at = _math(nt, "ARCTAN2", s[1], s[0])
        v = _math(nt, "FRACT", _math(nt, "MULTIPLY", at, k / math.pi))
    else:
        v = _math(nt, "FRACT", _math(nt, "MULTIPLY", s[axis], k))
    nt.links.new(_mix(nt, _math(nt, "LESS_THAN", v, 0.5), c2, c1), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    _try(b.inputs["Sheen Weight"], default_value=0.3)
    return m


def mg_boat(b, sail_b, x, y, z, ang, L=9.0, sail=True):
    c, s = math.cos(ang), math.sin(ang)
    verts = []
    for lx, w, hz in ((-L / 2, 0.1, 1.1), (-L / 4, 1.0, 0.7), (L / 4, 1.0, 0.7), (L / 2, 0.1, 1.2)):
        for sg in (-1, 1):
            verts.append((x + lx * c - sg * w * s, y + lx * s + sg * w * c, z + hz))
        verts.append((x + lx * c, y + lx * s, z - 0.2))
    faces = []
    for i in range(3):
        a, b_ = i * 3, (i + 1) * 3
        faces += [(a, b_, b_ + 2, a + 2), (a + 1, a + 2, b_ + 2, b_ + 1), (a, a + 1, b_ + 1, b_)]
    b.quads(verts, faces)
    if sail:
        b.seg((x, y, z + 0.5), (x, y, z + 7.5), 0.08, n=5)
        sail_b.box((x, y, z + 4.8), (0.04, 2.2, 2.4), (0, 0, ang + 0.4))


def shot_m_baghdad():
    """Baghdad, February 1258, from the west bank: the east-bank city across the Tigris (no Round City)."""
    sc = reset()
    mg_render_tweaks(sc, vol=True)
    info = mg_sky("drackenstein_quarry_puresky", 0.95, sun_az=-60, sun_el=20, sun_power=4.4, sun_col=(1.0, 0.82, 0.6), view_az=90)
    exposure(0.1)
    rng = random.Random(58)
    B0, B1 = 12.0, 180.0                                                        # river from y=B0 (near bank) to y=B1 (far quay)

    def h(x, y):
        z = mg_fbm(x / 40, y / 40, 3, 1) * 0.3
        k = mg_ss(B0 - 6, B0 + 2, y) * (1 - mg_ss(B1 - 4, B1 + 2, y))
        z = z * (1 - k) - 3.0 * k
        z += (y > B1) * 2.0
        return z
    gm = mg_ground_mat("bank", [("dirt", 0.3, (1.05, 0.95, 0.82)), ("dry_ground_rocks", 0.3, (1.05, 0.95, 0.82))], 0.015,
                       extra=[("brown_mud", 0.35, (0.8, 0.72, 0.6), mg_mask_height(-0.15, -1.0, 0.2))], fb=(0.6, 0.5, 0.38))
    mg_terrain("baghdad", 6000, 380, h, gm, 0, 60, 2.2)
    add("plane", (0, (B0 + B1) / 2, -1.2), (3000, (B1 - B0) / 2 + 6, 1), m=mg_water_mat("tigris", (0.07, 0.085, 0.07), 0.05, 0.18, 0.15))
    brick = mg_ph("bbrick", "yellow_brick", 1.0, tint=(1.12, 0.92, 0.72), fb=(0.75, 0.58, 0.4))
    carved = mg_ph("bcarved", "patterned_brick_wall", 0.6, tint=(1.3, 1.06, 0.8), fb=(0.72, 0.56, 0.4))
    dark = mat("barch", (0.05, 0.04, 0.03), 0.9)
    q, f, dk, ins = MgB(), MgB(), MgB(), MgB()
    q.box((0, B1 + 1.0, 0.5), (900, 2.5, 3.0))                                  # brick river quay
    MX0, MX1 = -170.0, -40.0                                                    # Mustansiriya-type river facade
    f.box(((MX0 + MX1) / 2, B1 + 14, 7.5), ((MX1 - MX0) / 2, 10, 7.5))
    for row, zc_ in ((0, 3.2), (1, 10.0)):
        for k in range(22):
            x = MX0 + 4 + k * (MX1 - MX0 - 8) / 21
            if abs(x - (MX0 + MX1) / 2) < 7:
                continue
            dk.box((x, B1 + 3.9, zc_), (1.1, 0.1, 1.8))
            dk.ico((x, B1 + 3.9, zc_ + 1.8), 1.1, (1.0, 0.1, 1.15), 1)
    ins.box(((MX0 + MX1) / 2, B1 + 3.85, 14.0), ((MX1 - MX0) / 2, 0.12, 0.45))
    mx_ = (MX0 + MX1) / 2
    f.box((mx_, B1 + 6, 11), (8, 3, 11))                                        # central iwan portal
    dk.box((mx_, B1 + 2.9, 7.5), (4.2, 0.1, 7.5))
    dk.ico((mx_, B1 + 2.9, 15), 4.2, (1, 0.05, 1.3), 2)
    for (dx, dy, r) in ((-120, 230, 7.0), (-30, 260, 9.0), (120, 250, 8.0), (30, 330, 6.0), (-200, 300, 6.5)):   # plain brick domes
        f.cyl((dx, dy, 5.5), r + 1.0, 5.5, 8, rot=(0, 0, math.pi / 8))
        f.cyl((dx, dy, 11.5), r + 0.3, 0.6, 32)
        mg_dome(f, dx, dy, 12, r, 1.2)
    zx, zy = 70.0, 320.0                                                        # muqarnas cone dome (Zumurrud Khatun type)
    f.cyl((zx, zy, 6), 7.5, 6, 8, rot=(0, 0, math.pi / 8))
    prof = []
    for k in range(15):
        t = k / 14
        prof.append((7.0 * (1 - t) ** 0.9 * (1.0 if k % 2 == 0 else 0.9), 12 + 22 * t))
    f.lathe(prof, 16, (zx, zy, 0))
    for (mxx, myy, hh) in ((-95, 215, 34), (10, 240, 30), (150, 290, 36)):     # brick minarets with a balcony
        f.cyl((mxx, myy, hh / 2), 2.0, hh / 2, 20, r2=1.5)
        f.cyl((mxx, myy, hh * 0.78), 2.4, 0.5, 20)
        f.cyl((mxx, myy, hh + 1.2), 1.3, 1.2, 16, r2=0.9)
    pal = MgB()                                                                 # Dar al-Khilafa palace walls by the river (right)
    pal.box((150, B1 + 30, 6.5), (60, 25, 6.5))
    for k in range(10):
        dk.box((95 + k * 12, B1 + 4.9, 4.0), (1.6, 0.1, 2.6))
        dk.ico((95 + k * 12, B1 + 4.9, 6.6), 1.6, (1.0, 0.1, 1.2), 1)
    pal.box((150, B1 + 8, 9), (10, 3, 9))
    dk.box((150, B1 + 4.9, 6.5), (5, 0.1, 6.5))
    dk.ico((150, B1 + 4.9, 13), 5, (1, 0.05, 1.25), 2)
    q.finish("quay", brick)
    f.finish("monuments", brick)
    pal.finish("palace", carved)
    dk.finish("arches", dark)
    ins.finish("inscription", mg_ph("stucco", "white_plaster_02", 0.5, tint=(0.95, 0.88, 0.75), fb=(0.85, 0.8, 0.7)))
    cw = MgB()                                                                  # al-Mustazhir wall with round towers, receding
    a0, a1 = Vector((235, B1 + 4, 0)), Vector((380, 1200, 0))
    mg_earth_wall(cw, a0[:2], a1[:2], 13, 10, 6)
    for k in range(26):
        p = a0.lerp(a1, k / 25)
        cw.cyl((p.x, p.y, 7.5), 6, 8.5, 20, r2=5.2)
    cw.finish("citywall", brick)
    plaster = mg_ph("bplaster", "clay_plaster", 0.35, tint=(1.0, 0.86, 0.68), fb=(0.72, 0.58, 0.42))
    hb, hb2 = MgB(), MgB()
    for _ in range(260):
        x, y = rng.uniform(-420, 330), rng.uniform(B1 + 8, 900)
        if MX0 - 3 < x < MX1 + 3 and y < B1 + 26 or 85 < x < 215 and y < B1 + 58:
            continue
        w, d, hh = rng.uniform(5, 11), rng.uniform(5, 10), rng.uniform(5, 12)
        (hb if rng.random() < 0.5 else hb2).box((x, y, hh / 2), (w, d, hh / 2))
    hb.finish("houses", plaster)
    hb2.finish("houses2", brick)
    trunk = mg_ph("palmtrunk", "palm_bark", 1.0, tint=(0.85, 0.75, 0.62), fb=(0.35, 0.27, 0.18))
    tb, fb_ = MgB(), MgB()
    for _ in range(9):                                                          # palms on the near bank (left edge of frame)
        mg_palm(tb, fb_, rng.uniform(-40, -16), rng.uniform(-2, 9), 0, rng.uniform(9, 14), rng)
    for _ in range(3):
        mg_palm(tb, fb_, rng.uniform(17, 26), rng.uniform(6, 11), 0, rng.uniform(10, 13), rng)
    for _ in range(90):                                                         # palm gardens on the far bank, among and beside the town
        x = rng.choice((rng.uniform(-500, -175), rng.uniform(220, 500), rng.uniform(-160, 200)))
        y = rng.uniform(B1 + 6, B1 + 30) if abs(x) > 175 else rng.uniform(B1 + 60, B1 + 220)
        mg_palm(tb, fb_, x, y, 2.0, rng.uniform(10, 16), rng)
    tb.finish("palmtrunks", trunk)
    fb_.finish("fronds", mg_leaf_mat("frond", (0.16, 0.24, 0.08), (0.3, 0.36, 0.14), 0.25, 2.0))
    bo, sl = MgB(), MgB()                                                       # bridge of boats + river craft
    BX = 120.0
    for k in range(17):
        mg_boat(bo, sl, BX, B0 + 6 + k * (B1 - B0 - 12) / 16, -1.25, 0.0, 8.0, False)
    bo.box((BX, (B0 + B1) / 2, -0.15), (1.8, (B1 - B0) / 2, 0.12))
    for (x, y, a) in ((-28, 42, 0.1), (30, 95, -0.2), (70, 48, 0.3), (-90, 120, 0.0), (55, 150, 0.15)):
        mg_boat(bo, sl, x, y, -1.25, a, 11.0, True)
    for (x, y) in ((-20, 40), (12, 62), (-35, 95), (60, 85)):
        bo.cyl((x, y, -1.0), 1.3, 0.4, 16)                                      # quffa coracles (bitumen)
    bo.finish("boats", mg_ph("boatwood", "weathered_planks", 0.6, tint=(0.7, 0.58, 0.45), fb=(0.35, 0.27, 0.18)))
    sl.finish("sails", mg_felt_mat("sailcloth", (0.78, 0.72, 0.6), (0.86, 0.8, 0.68), dirt_h=0.0))
    for k, (x, y, r_) in enumerate(((-260, 520, 30), (40, 640, 36), (260, 480, 26), (-80, 900, 34))):
        mg_smoke(x, y, 4, 260, r_, 0.12, (0.16, 0.14, 0.13), (-0.22, 0.1), seed=k * 2.7, speed=0.2)
    mg_camera([(0.0, (0, -24, 3.2)), (1.0, (3.0, -21.5, 3.1))], 26, [(0.0, (-20, 260, 8.0)), (1.0, (-16, 260, 8.0))])
    mg_aerial(info["haze"], 3000, 0.8)
    return sc


def shot_m_hakata():
    """Hakata Bay, summer 1281: the Genko Borui stone wall (built 1276) behind the beach, black pines, a storm rising, the
    Yuan/Goryeo fleet off the islands."""
    sc = reset()
    mg_render_tweaks(sc)
    info = mg_sky("kloofendal_overcast_puresky", 0.38, sun_az=150, sun_el=16, sun_power=1.1, sun_col=(0.85, 0.88, 0.95), sun_angle=8,
                  view_az=109, gamma=1.6, tint=(0.72, 0.78, 0.9))
    exposure(0.25)
    rng = random.Random(81)

    def sl(y):                                                                  # shoreline x at y (sea to the left)
        return -34 - 0.35 * y

    def h(x, y):
        u = x - sl(y)
        if u < 0:
            z = max(-7.0, 0.06 * u)
        elif u < 36:
            z = 0.045 * u
        else:
            z = 1.6 + min(1.2, (u - 36) * 0.15) + mg_fbm(x / 30, y / 30, 3, 1) * 0.8 * mg_ss(40, 70, u)
        z += mg_fbm(x / 12, y / 12, 2, 4) * 0.12
        for (ix, iy, ir, ih) in ((-1400, 2400, 700, 110), (-500, 3300, 900, 160), (900, 2600, 800, 220), (-2600, 2900, 1200, 40)):
            d = math.hypot((x - ix) / ir, (y - iy) / (ir * 0.5))
            if d < 1.0:
                z = max(z, ih * (1 - d * d) ** 1.4 * (0.75 + 0.5 * mg_fbm(x / 200, y / 200, 3, 7)))
        return z

    def dens(x, y):
        u = x - sl(y)
        return mg_ss(40, 46, u) * (1 - mg_ss(30, 70, math.hypot(x - 10, y + 5)))
    gm = mg_ground_mat("beach", [("coast_sand_01", 0.3, (1.0, 0.96, 0.88)), ("damp_beach_sand", 0.3, (0.95, 0.92, 0.85))], 0.02,
                       extra=[("forrest_ground_01", 0.3, (0.7, 0.75, 0.6),
                               lambda nt, pos: _maprange(nt, _sep(nt, pos)[2], 1.8, 2.6)),
                              ("rocky_terrain_02", 0.01, (0.55, 0.62, 0.5), mg_mask_height(6, 25, 6))], fb=(0.6, 0.55, 0.45))
    ground = mg_terrain("bay", 6000, 420, h, gm, -20, 80, 2.2, dens)
    mg_grass(ground, 18000, 0.38, mg_grass_mat("dunegrass", (0.08, 0.09, 0.05), (0.32, 0.36, 0.2), (0.5, 0.48, 0.32)), 6, 0.004, 7, 0.6)

    def hw(x, y):
        return 0.0 if (x - sl(y)) < 9 else -8.0
    sea = mg_terrain("sea", 5000, 300, hw, None, -300, 400, 2.0)
    oc = sea.modifiers.new("ocean", "OCEAN")
    _try(oc, geometry_mode="DISPLACE", resolution=14, spatial_size=120, wave_scale=2.6, choppiness=1.6, wind_velocity=28,
         wave_alignment=0.5, wave_direction=math.radians(-20), use_foam=True, foam_layer_name="foam", foam_coverage=0.55, random_seed=4)
    oc.time = 1.0
    oc.keyframe_insert("time", frame=1)
    oc.time = 1.0 + SECONDS * 0.8
    oc.keyframe_insert("time", frame=N)
    m, nt, b = _mnew("stormsea")
    b.inputs["Roughness"].default_value = 0.08
    b.inputs["IOR"].default_value = 1.33
    pos = _pos(nt)
    s = _sep(nt, pos)
    u = _math(nt, "ADD", _math(nt, "ADD", s[0], 34.0), _math(nt, "MULTIPLY", s[1], 0.35))      # x - sl(y)
    band = _math(nt, "MULTIPLY", _maprange(nt, u, -70, -6), _maprange(nt, u, 4, 0))
    stripes = _maprange(nt, _noise(nt, pos, 0.09, 6, 0.65), 0.45, 0.62)
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "foam"
    foam = _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", band, stripes), _maprange(nt, at.outputs["Fac"], 0.2, 0.7), clamp=True)
    col = _mix(nt, foam, (0.02, 0.045, 0.05), (0.75, 0.78, 0.78))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(_math(nt, "MULTIPLY_ADD", foam, 0.8, 0.08), b.inputs["Roughness"])
    sea.data.materials.append(m)
    wall = mg_ph("borui", "rock_wall_08", 0.4, tint=(0.95, 0.92, 0.86), fb=(0.45, 0.43, 0.4))
    wb = MgB()                                                                  # stone wall: vertical seaward face, sloped landward
    verts, faces = [], []
    ys = [-80 + k * 6 for k in range(130)]
    prof = [(36.0, -0.8), (36.0, 1.6 + 2.8), (38.5, 4.4), (42.0, 2.0), (42.0, -0.8)]
    for i, y in enumerate(ys):
        jit = mg_fbm(y / 25, 3.3, 2, 9) * 0.35
        for (uu, zz) in prof:
            zz2 = zz + (mg_fbm(y / 9, uu, 2, 1) * 0.12 if zz > 3 else 0)
            verts.append((sl(y) + uu + jit, y, zz2))
    np_ = len(prof)
    for i in range(len(ys) - 1):
        for j in range(np_ - 1):
            faces.append((i * np_ + j, i * np_ + j + 1, (i + 1) * np_ + j + 1, (i + 1) * np_ + j))
    wb.quads(verts, faces)
    wb.finish("genko_borui", wall, False)
    trunk = mg_ph("pinebark", "pine_bark", 0.8, tint=(0.75, 0.68, 0.62), fb=(0.3, 0.24, 0.2))
    tb, pb = MgB(), MgB()
    for _ in range(70):                                                         # black pines behind the wall (Ikinomatsubara)
        y = rng.uniform(-40, 520)
        x = sl(y) + rng.uniform(48, 120)
        if math.hypot(x + 4, y + 24) < 25:
            continue
        mg_pine(tb, pb, x, y, h(x, y), rng.uniform(9, 14), rng, rng.uniform(2.6, 3.6))
    for (x, y) in ((0, 70), (-8, 95), (5, 55)):
        mg_pine(tb, pb, x, y, h(x, y), rng.uniform(10, 13), rng, 2.9)
    tb.finish("pinetrunks", trunk)
    pb.finish("pineneedles", mg_leaf_mat("needles", (0.04, 0.08, 0.04), (0.09, 0.14, 0.07), 0.1, 14.0), True)
    hull = mg_ph("junkwood", "weathered_planks", 0.6, tint=(0.55, 0.45, 0.36), fb=(0.3, 0.24, 0.18))
    jb, js = MgB(), MgB()
    for (x, y, sc_) in ((-700, 1500, 1.6), (-420, 1900, 1.4), (-950, 2100, 1.4), (-250, 2300, 1.3), (-600, 2500, 1.2), (-1250, 1800, 1.5)):
        jb.frustum((x, y, -1.5 * sc_), 13 * sc_, 3.2 * sc_, 15 * sc_, 4.2 * sc_, 4.0 * sc_)
        jb.box((x - 11 * sc_, y, 3.5 * sc_), (3.2 * sc_, 3.6 * sc_, 1.6 * sc_))
        for k, (mx, mh) in enumerate(((-4, 16), (2, 20), (8, 12))):
            jb.seg((x + mx * sc_, y, 0), (x + mx * sc_, y, mh * sc_), 0.25 * sc_, n=5)
            js.box((x + mx * sc_, y + 0.6 * sc_, mh * 0.6 * sc_), (mh * 0.2 * sc_, 0.1, mh * 0.32 * sc_))
    jb.finish("junks", hull)
    js.finish("matsails", mg_stripe_mat("matsail", (0.42, 0.34, 0.22), (0.55, 0.45, 0.3), 1.2, 2))
    mg_camera([(0.0, (-11, -26, h(-11, -26) + 2.1)), (1.0, (-9.5, -23.5, h(-9.5, -23.5) + 2.05))], 28,
              [(0.0, (-108, 250, 1.2)), (1.0, (-105, 250, 1.2))])
    mg_aerial(info["haze"], 1600, 0.92)
    return sc


def shot_m_dadu_hall():
    """Kublai's audience hall at Dadu (Khanbaliq), c. 1285: Chinese timber hall dressed in Mongol taste."""
    sc = reset()
    sc.cycles.max_bounces = 6
    mg_render_tweaks(sc)
    mg_sky("kloofendal_48d_partly_cloudy_puresky", 1.0, sun_az=-75, sun_el=34, sun_power=5.0, sun_col=(1.0, 0.93, 0.82), view_az=95)
    exposure(-0.1)
    rng = random.Random(12)
    M = mg_hall_mats()
    HX, Y1, CH, CEIL = 22.5, 24.0, 8.4, 10.6
    floor = mg_ph("hallfloor", "granite_tile", 0.22, tint=(0.82, 0.76, 0.68), rough=0.6, fb=(0.5, 0.48, 0.45))
    add("plane", (0, 30, 0), (60, 60, 1), m=floor)
    wallm = mg_ph("dwall", "white_plaster_02", 0.3, tint=(0.62, 0.2, 0.12), fb=(0.55, 0.2, 0.12))
    wb, cb, br, bm, sb = MgB(), MgB(), MgB(), MgB(), MgB()
    for x0, x1 in ((-HX, -12.6), (-9.4, 9.4), (12.6, HX)):                     # rear wall with two open doors
        wb.box(((x0 + x1) / 2, Y1 + 0.3, CEIL / 2), ((x1 - x0) / 2, 0.3, CEIL / 2))
    for xc in (-11, 11):
        wb.box((xc, Y1 + 0.3, (5.6 + CEIL) / 2), (1.65, 0.3, (CEIL - 5.6) / 2))
    for x0, x1 in ((-HX, -13), (-9, 9), (13, HX)):                              # front wall (behind camera) with doors
        wb.box(((x0 + x1) / 2, -0.5, CEIL / 2), ((x1 - x0) / 2, 0.3, CEIL / 2))
    for xc in (-11, 11):
        wb.box((xc, -0.5, (6.0 + CEIL) / 2), (2.0, 0.3, (CEIL - 6.0) / 2))
    for xx in (-HX - 0.3, HX + 0.3):
        wb.box((xx, Y1 / 2, CEIL / 2), (0.3, Y1 / 2 + 0.8, CEIL / 2))
    wb.finish("walls", wallm)
    lw = MgB()
    for xx in (-HX, HX):                                                        # lattice windows in the side walls
        for yc in (5, 12, 19):
            lw.box((xx * 0.995, yc, 4.6), (0.05, 2.0, 1.8))
    lw.finish("sidelattice", mg_lattice_mat("lattice_y", axis=1))
    cols = [(x, y) for x in [-HX + 5 * i for i in range(10)] for y in (6.0, 18.0) if abs(x) > 3]
    s = CH / 4.8
    for (x, y) in cols:
        cb.cyl((x, y, CH / 2), 0.5, CH / 2, 16)
        sb.cyl((x, y, 0.15), 0.78, 0.15, 16)
        _dougong(br, x, y, CH, s * 0.9)
    for y in (6.0, 18.0):
        bm.box((0, y, CH + 1.2), (HX, 0.35, 0.35))
    for x in [-HX + 5 * i for i in range(10)]:
        bm.box((x, Y1 / 2, CH + 1.35), (0.3, Y1 / 2, 0.3))
    for k in range(17):                                                         # coffered ceiling grid
        bm.box((-HX + k * (2 * HX / 16), Y1 / 2, CEIL - 0.12), (0.12, Y1 / 2, 0.12))
    for k in range(10):
        bm.box((0, k * Y1 / 9, CEIL - 0.12), (HX, 0.12, 0.12))
    cb.finish("columns", M["col"])
    sb.finish("plinths", M["stone"])
    br.finish("brackets", M["bracket"])
    bm.finish("beams", M["beam"])
    m, nt, b = _mnew("caisson")                                                 # painted ceiling panels
    p = _sep(nt, _pos(nt))
    fu = _math(nt, "FRACT", _math(nt, "MULTIPLY", p[0], 16 / (2 * HX)))
    fv = _math(nt, "FRACT", _math(nt, "MULTIPLY", p[1], 9 / Y1))
    rr = _math(nt, "ADD", _math(nt, "POWER", _math(nt, "SUBTRACT", fu, 0.5), 2), _math(nt, "POWER", _math(nt, "SUBTRACT", fv, 0.5), 2))
    col = _mix(nt, _math(nt, "LESS_THAN", rr, 0.09), (0.08, 0.22, 0.22), (0.12, 0.2, 0.4))
    col = _mix(nt, _band(nt, rr, 0.09, 0.11), col, (0.75, 0.55, 0.18))
    col = _mix(nt, _math(nt, "LESS_THAN", rr, 0.025), col, (0.6, 0.12, 0.08))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    add("plane", (0, Y1 / 2, CEIL), (HX, Y1 / 2 + 0.6, 1), m=m)
    gold = mat("gilt", (0.8, 0.55, 0.18), 0.28, 1.0)
    gd = MgB()                                                                  # gilt dragons coiled on the throne columns
    for (x, y) in ((-7.5, 18.0), (7.5, 18.0), (-2.6, 18.0), (2.6, 18.0)):
        if abs(x) < 3:
            cb2 = MgB()
            cb2.cyl((x, y, CH / 2), 0.5, CH / 2, 16)
            cb2.finish("thronecol", M["col"])
        pts = [(x + 0.56 * math.cos(t * 0.55), y + 0.56 * math.sin(t * 0.55), 0.6 + t * 0.2) for t in range(37)]
        gd.poly(pts, 0.12, 0.07, 6)
    gd.finish("dragons", gold)
    mb = mg_ph("marble", "marble_01", 0.3, tint=(0.95, 0.93, 0.9), rough=0.5, fb=(0.85, 0.83, 0.8))
    tp = MgB()                                                                  # throne dais: three marble tiers with balustrade
    for k in range(3):
        tp.box((0, 20.6 + k * 0.5, 0.25 + k * 0.5), (5.6 - k * 0.8, 3.0 - k * 0.5, 0.25 + k * 0.5))
    for k in range(13):
        tp.box((-4.8 + k * 0.8, 18.2, 1.9), (0.08, 0.08, 0.35))
    tp.box((-2.8, 18.2, 2.25), (2.0, 0.07, 0.06))
    tp.box((2.8, 18.2, 2.25), (2.0, 0.07, 0.06))
    tp.finish("dais", mb)
    th = MgB()
    th.box((0, 21.6, 2.05), (1.5, 0.75, 0.3))
    th.box((0, 22.25, 2.9), (1.5, 0.12, 0.9))
    for sx in (-1.45, 1.45):
        th.box((sx, 21.6, 2.6), (0.1, 0.7, 0.3))
    th.finish("throne", gold)
    sc_ = MgB()
    sc_.box((0, 23.3, 3.4), (3.6, 0.15, 2.6))
    sc_.finish("screen", mg_painted_mat("screenpaint", (0.08, 0.05, 0.04), (0.8, 0.58, 0.2), (0.6, 0.12, 0.08)))
    brocade = mg_nasij("nasij", (0.05, 0.07, 0.2))
    ermine = mg_ph("ermine", "curly_teddy_natural", 1.6, tint=(1.15, 1.12, 1.08), fb=(0.85, 0.83, 0.8))
    sable = mg_ph("sable", "curly_teddy_natural", 1.6, tint=(0.35, 0.25, 0.18), fb=(0.2, 0.15, 0.1))
    hb, he, hs = MgB(), MgB(), MgB()
    for xc in (-6.5, 6.5, -17.0, 17.0):                                        # hangings on the rear wall
        hb.box((xc, Y1 - 0.05, 5.0), (1.6 if abs(xc) < 10 else 3.0, 0.04, 3.6))
    for yc in (3.0, 9.0, 15.0, 21.0):                                           # fur panels on the side walls
        for xx in (-HX + 0.08, HX - 0.08):
            (he if (yc // 6) % 2 == 0 else hs).box((xx, yc, 5.0), (0.05, 1.3, 2.8))
    hb.box((0, 21.0, 7.4), (3.4, 2.2, 0.12))                                    # canopy over the throne
    hb.finish("brocade", brocade)
    he.finish("ermine", ermine)
    hs.finish("sable", sable)
    add("plane", (0, 9.5, 0.012), (3.2, 8.0, 1), m=mg_rug_mat("runner", (0.45, 0.06, 0.05), (0.06, 0.08, 0.22), (0.8, 0.6, 0.28), k=9))
    add("plane", (-11, 12, 0.01), (5.5, 9, 1), m=mg_felt_mat("feltcarpet", (0.62, 0.56, 0.46), (0.7, 0.64, 0.53), dirt_h=0.0))
    add("plane", (11, 12, 0.01), (5.5, 9, 1), m=mg_rug_mat("rugside", (0.1, 0.12, 0.3), (0.45, 0.07, 0.05), (0.8, 0.62, 0.3), k=6))
    lan = MgB()
    for (x, y) in ((-7.5, 12), (7.5, 12), (-2.5, 4), (2.5, 4)):                 # hanging lanterns
        lan.seg((x, y, CEIL), (x, y, 7.4), 0.02, n=4)
        lan.ico((x, y, 7.0), 0.32, (1, 1, 1.3), 2)
    lan.finish("lanterns", mg_emit_mat("lantern", (0.9, 0.3, 0.12), 2.5))
    ct = MgB()                                                                  # the courtyard and rear hall seen through the doors
    ct.box((0, 46, -0.2), (60, 22, 0.2))
    for k in range(40):
        ct.box((-30 + k * 1.5, 34, 0.55), (0.1, 0.1, 0.55))
    ct.box((0, 34, 1.15), (30, 0.12, 0.1))
    ct.finish("terrace", mb)
    yellow = mg_tile_mat("yellowglaze", (0.78, 0.55, 0.12), 0.25, edge_col=(0.12, 0.38, 0.2), edge_v=1.8)
    mg_hall(0, 52, 9, 3, 4.6, 6.4, 2.0, 0.0, roof_m=yellow, ridge_m=mg_tile_mat("greenridge", (0.12, 0.38, 0.2), 0.25),
            plat_m=mb, double=True)
    mg_ger(-20, 42, 0.0, 3.0, "white", 0.0)
    for xc in (-11, 11):
        l = light("AREA", (xc, Y1 + 0.7, 2.8), 10, (1, 1, 1), 3.2)
        l.data.shape = "RECTANGLE"
        l.data.size, l.data.size_y = 3.3, 5.6
        l.rotation_euler = (math.radians(-90), 0, 0)
        _try(l.data.cycles, is_portal=True)
    for xc in (-11, 11):
        l = light("AREA", (xc, -0.9, 3.0), 10, (1, 1, 1), 4.0)
        l.data.shape = "RECTANGLE"
        l.data.size, l.data.size_y = 4.0, 6.0
        l.rotation_euler = (math.radians(90), 0, 0)
        _try(l.data.cycles, is_portal=True)
    fills = [light("AREA", (0, 10, CEIL - 0.6), 2600, (1.0, 0.82, 0.6), 14), light("AREA", (0, 20, 6.5), 700, (1.0, 0.78, 0.5), 5),
             light("AREA", (-12, 10, CEIL - 0.6), 900, (1.0, 0.85, 0.65), 8), light("AREA", (12, 10, CEIL - 0.6), 900, (1.0, 0.85, 0.65), 8)]
    for l in fills:
        _try(l, visible_camera=False, visible_glossy=False)
    mg_camera([(0.0, (4.4, 1.2, 1.75)), (1.0, (3.6, 2.4, 1.72))], 21, [(0.0, (-1.2, 22, 3.0)), (1.0, (-1.4, 22, 2.95))])
    return sc


def shot_m_caravan():
    """A Silk Road caravan under Mongol rule (Pax Mongolica): Bactrian camels crossing gravel desert below the Tian Shan,
    a yam relay station with its horses."""
    sc = reset()
    mg_render_tweaks(sc, vol=True)
    info = mg_sky("table_mountain_1_puresky", 0.9, sun_az=150, sun_el=15, sun_power=4.6, sun_col=(1.0, 0.8, 0.56), view_az=90)
    exposure(0.15)
    rng = random.Random(91)

    def h(x, y):
        z = mg_fbm(x / 70, y / 70, 3, 1) * 0.8 + mg_fbm(x / 15, y / 15, 2, 3) * 0.1
        dune = (1 - abs(math.sin((x * 0.8 + y * 0.6) / 38 + mg_fbm(x / 120, y / 120, 2, 5) * 3))) ** 2 * 14
        z += dune * mg_ss(70, 160, x) * mg_ss(120, 260, y) * (1 - mg_ss(900, 1400, y))
        z += (mg_fbm(x / 500, y / 500, 4, 6) + 0.5) * 120 * mg_ss(1200, 2600, y)
        z += mg_ridge(x / 2600, y / 2600, 6, 2) ** 1.8 * 1700 * mg_ss(4000, 8500, y)
        return z
    gm = mg_ground_mat("desert", [("gravelly_sand", 0.3, (1.05, 0.95, 0.8)), ("dry_ground_rocks", 0.3, (1.05, 0.95, 0.8))], 0.012,
                       extra=[("aerial_sand", 0.04, (1.1, 0.98, 0.82), mg_mask_height(2.0, 5.0, 1.5)),
                              ("rock_face", 0.02, (0.8, 0.76, 0.72), mg_mask_height(150, 500, 100)),
                              ("snow_02", 0.05, (1.0, 1.0, 1.0), mg_mask_height(700, 950, 200))], fb=(0.7, 0.6, 0.45))
    mg_terrain("desert", 9000, 440, h, gm, 0, 80, 2.3)
    camel = mg_camel_me()
    hides = [noisy("camelA", (0.42, 0.32, 0.2), (0.55, 0.43, 0.28), 4, 0.9, 0.15),
             noisy("camelB", (0.33, 0.24, 0.15), (0.45, 0.34, 0.22), 4, 0.9, 0.15),
             noisy("camelC", (0.55, 0.45, 0.32), (0.66, 0.56, 0.4), 4, 0.9, 0.15)]
    bales = [mg_stripe_mat("baleA", (0.55, 0.12, 0.08), (0.85, 0.78, 0.6), 2.5, 2), mg_stripe_mat("baleB", (0.16, 0.22, 0.42), (0.82, 0.75, 0.58), 2.5, 2),
             mg_ph("bags", "brown_leather", 1.0, tint=(0.95, 0.8, 0.6), fb=(0.4, 0.28, 0.16))]
    rope = MgB()
    p0, p1 = Vector((-52, 52, 0)), Vector((14, 30, 0))
    ang = math.atan2(p1.y - p0.y, p1.x - p0.x)
    prev = None
    for k in range(10):
        p = p0.lerp(p1, k / 9) + Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), 0))
        z = h(p.x, p.y)
        mg_inst(camel, (p.x, p.y, z), ang + rng.uniform(-0.08, 0.08), rng.uniform(0.95, 1.05), rng.choice(hides))
        c, s = math.cos(ang), math.sin(ang)
        bb = MgB()
        for sg in (-1, 1):
            bb.box((-0.0, sg * 0.62, 1.55), (0.45, 0.22, 0.35))
        bb.box((0, 0, 1.95), (0.5, 0.5, 0.08))
        bb.finish("bales", rng.choice(bales), False, (p.x, p.y, z), ang)
        nose = (p.x + 1.85 * c, p.y + 1.85 * s, z + 1.7)
        if prev is not None:
            rope.seg(prev, nose, 0.02, n=3)
        prev = (p.x - 1.0 * c, p.y - 1.0 * s, z + 1.2)
    rope.finish("leadrope", MG_M.setdefault("hemp", mat("hemp", (0.45, 0.38, 0.26), 0.9)))
    SX, SY = -78.0, 118.0                                                      # yam station: rammed-earth enclosure
    zs = h(SX, SY)
    earth = mg_rammed_mat("yamwall", (0.9, 0.78, 0.6), "brown_mud_dry", 0.3, 0.75)
    yw = MgB()
    for (a, b) in (((SX - 22, SY - 16), (SX - 4, SY - 16)), ((SX + 4, SY - 16), (SX + 22, SY - 16)), ((SX + 22, SY - 16), (SX + 22, SY + 16)),
                   ((SX + 22, SY + 16), (SX - 22, SY + 16)), ((SX - 22, SY + 16), (SX - 22, SY - 16))):
        mg_earth_wall(yw, a, b, zs + 4.0, 2.2, 1.2, zs - 1)
    for (tx, ty) in ((SX - 22, SY - 16), (SX + 22, SY - 16), (SX - 22, SY + 16), (SX + 22, SY + 16)):
        yw.frustum((tx, ty, zs - 1), 2.6, 2.6, 2.0, 2.0, 6.5)
    yw.box((SX, SY + 8, zs + 1.6), (10, 4, 2.4))
    yw.box((SX + 12, SY - 4, zs + 1.4), (5, 4, 2.2))
    yw.finish("yam", earth)
    mg_ger(SX - 12, SY - 4, zs, 2.6, "grey", 0.0)
    mg_ger(SX + 30, SY + 4, h(SX + 30, SY + 4), 2.6, "white", 0.1)
    pb = MgB()
    pb.seg((SX - 3, SY - 18, zs), (SX - 3, SY - 18, zs + 9), 0.08, n=6)          # pole with a horse-tail tassel
    pb.ico((SX - 3, SY - 18, zs + 8.2), 0.4, (1, 1, 1.8), 1)
    for k in range(7):                                                          # hitching line
        pb.seg((SX + 26 + k * 3, SY - 22, zs - 0.3), (SX + 26 + k * 3, SY - 22, zs + 1.3), 0.07, n=5)
    pb.seg((SX + 26, SY - 22, zs + 1.2), (SX + 44, SY - 22, zs + 1.2), 0.04, n=4)
    pb.finish("poles", MG_M.setdefault("timber", mg_ph("timber", "rough_wood", 0.6, tint=(0.8, 0.65, 0.5), fb=(0.4, 0.3, 0.2))))
    coats = mg_coats()
    for k in range(6):
        x, y = SX + 27.5 + k * 3, SY - 23.2
        mg_inst(mg_horse_me(k % 3 == 1), (x, y, h(x, y)), -math.pi / 2 + rng.uniform(-0.2, 0.2), rng.uniform(0.95, 1.03), coats[k % len(coats)])
    mg_herd(SX - 40, SY + 30, 8, 10, 6, h, rng, 0.7)
    tb, lv = MgB(), MgB()
    for k in range(8):                                                          # poplars by the station's well
        x, y = SX - 34 + rng.uniform(-6, 6), SY - 10 + k * 5
        mg_tree(tb, lv, x, y, h(x, y), rng.uniform(12, 16), rng, "poplar_leaf")
    tb.finish("poplars", MG_M.setdefault("bark", mg_ph("bark", "bark_willow", 1.0, tint=(0.7, 0.62, 0.55), fb=(0.3, 0.25, 0.2))))
    lv.finish("poplarleaf", mg_leaf_mat("poplarleaf", (0.22, 0.3, 0.08), (0.42, 0.45, 0.14), 0.3, 3.0), True)
    mg_smoke(SX + 5, SY + 8, zs + 3.5, 22, 1.2, 0.7, (0.55, 0.52, 0.5), (0.25, 0.1), seed=3)
    h0 = h(-5, -30)
    mg_camera([(0.0, (-9, -32, h0 + 2.5)), (1.0, (-5, -29.5, h0 + 2.45))], 28, [(0.0, (-24, 300, 8)), (1.0, (-20, 300, 8))])
    mg_aerial(info["haze"], 6000, 0.8)
    return sc


SHOTS.update({"m_steppe_dawn": shot_m_steppe_dawn, "m_ger_inside": shot_m_ger_inside, "m_karakorum": shot_m_karakorum,
              "m_zhongdu": shot_m_zhongdu, "m_bukhara": shot_m_bukhara, "m_mohi": shot_m_mohi, "m_baghdad": shot_m_baghdad,
              "m_hakata": shot_m_hakata, "m_dadu_hall": shot_m_dadu_hall, "m_caravan": shot_m_caravan})
