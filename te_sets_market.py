# Look-test set (Nov 2026): a Bukhara bazaar square, c. 1200, built for richness rather than size.
# Runs inside blender_te.py's namespace together with te_sets_mongol.py (MgB, mg_* helpers, mat, add, reset, ...).
#
# What is here: a monumental brick portal with a deep pointed arch, two-storey caravanserai arcades with niches, carved doors and
# latticed balconies, a timber porch on carved columns, brick domes, the Kalyan minaret; a market lane of stalls (pottery, fruit,
# spices, bread, cloth, carpets) under striped awnings; merchants and buyers in robes, sashes and turbans, standing, bargaining
# and sitting; loaded camels, horses, a cart; low warm sun.
# Period note: plain and carved baked brick (no blue-tiled domes: those are Timurid, 14th-15th century). Colour comes from
# cloth, carpets, goods and clothing.


def bz_niche(dk, x, y, z0, w, h, face, depth=0.12):
    """Dark pointed-arch recess on a wall face. face: 'S' (wall faces -y), 'E' (faces +x), 'W' (faces -x)."""
    if face == "S":
        dk.box((x, y - depth, z0 + h * 0.36), (w, 0.06, h * 0.36))
        dk.ico((x, y - depth, z0 + h * 0.66), w, (1.0, 0.05, h * 0.34 / w), 2)
    else:
        sx = depth if face == "E" else -depth
        dk.box((x + sx, y, z0 + h * 0.36), (0.06, w, h * 0.36))
        dk.ico((x + sx, y, z0 + h * 0.66), w, (0.05, 1.0, h * 0.34 / w), 2)


def bz_arcade(wall, trim, dk, wood, lat, p0, p1, face, h=9.0, bay=5.0, thick=3.0):
    """Two-storey arcade wall from p0 to p1 (axis-aligned). Piers, niches, carved doors, latticed balconies, cornice, merlons."""
    (x0, y0), (x1, y1) = p0, p1
    along_x = abs(x1 - x0) > abs(y1 - y0)
    L = abs(x1 - x0) if along_x else abs(y1 - y0)
    n = max(1, int(L / bay))
    step = L / n
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if along_x:
        wall.box((cx, cy + thick / 2, h / 2), (L / 2, thick / 2, h / 2))
        trim.box((cx, cy - 0.12, h + 0.25), (L / 2 + 0.2, 0.3, 0.3))
        trim.box((cx, cy - 0.08, 4.15), (L / 2, 0.18, 0.14))
    else:
        s = 1 if face == "W" else -1                                            # the mass lies behind the visible face
        wall.box((cx + s * thick / 2, cy, h / 2), (thick / 2, L / 2, h / 2))
        trim.box((cx - s * 0.12, cy, h + 0.25), (0.3, L / 2 + 0.2, 0.3))
        trim.box((cx - s * 0.08, cy, 4.15), (0.18, L / 2, 0.14))
    for i in range(n):
        t = (i + 0.5) * step
        bx, by = (min(x0, x1) + t, cy) if along_x else (cx, min(y0, y1) + t)
        bz_niche(dk, bx, by, 0.0, step * 0.3, 3.9, face)                        # shop niche below
        bz_niche(dk, bx, by, 4.5, step * 0.24, 3.4, face)                       # loggia above
        off = {"S": (0, -0.22), "E": (0.22, 0), "W": (-0.22, 0)}[face]
        if i % 2 == 0:                                                          # carved wooden door in every second niche
            hb = (step * 0.2, 0.05, 1.25) if along_x else (0.05, step * 0.2, 1.25)
            wood.box((bx + off[0], by + off[1], 1.25), hb)
        hb = (step * 0.26, 0.05, 0.45) if along_x else (0.05, step * 0.26, 0.45)  # latticed balcony rail
        lat.box((bx + off[0] * 1.6, by + off[1] * 1.6, 5.0), hb)
    for i in range(n + 1):                                                      # piers and merlons
        t = i * step
        px, py = (min(x0, x1) + t, cy) if along_x else (cx, min(y0, y1) + t)
        off = {"S": (0, -0.2), "E": (0.2, 0), "W": (-0.2, 0)}[face]
        trim.box((px + off[0], py + off[1], h / 2), (0.42, 0.42, h / 2))
        trim.box((px + off[0], py + off[1], h + 0.95), (0.5, 0.5, 0.42))


def bz_person(B, x, y, ang, rng, pose="stand", z=0.0):
    """One merchant or townsman, about 1.7 m: long robe with sash, turban or cap, head, beard, arms and hands."""
    c, s = math.cos(ang), math.sin(ang)

    def P(lx, ly, lz):
        return (x + lx * c - ly * s, y + lx * s + ly * c, z + lz)
    k = rng.uniform(0.94, 1.06)
    robe = rng.choice(B["robes"])
    if pose == "sit":
        robe.lathe([(0.44 * k, 0.0), (0.4 * k, 0.28), (0.24 * k, 0.62), (0.2 * k, 0.86), (0.1 * k, 0.94)], 10, P(0, 0, 0))
        hz = 1.08
        sh = 0.8
    else:
        robe.lathe([(0.3 * k, 0.0), (0.27 * k, 0.5), (0.21 * k, 1.02), (0.23 * k, 1.34), (0.1 * k, 1.45)], 10, P(0, 0, 0))
        rng.choice(B["sashes"]).cyl(P(0, 0, 0.98), 0.235 * k, 0.07, 10)
        hz = 1.6 * k
        sh = 1.3 * k
    B["skin"].ico(P(0, 0, hz), 0.125, (1, 1, 1.08), 2)
    if rng.random() < 0.72:
        rng.choice(B["turbans"]).ico(P(0, 0, hz + 0.1), 0.175, (1, 1, 0.62), 2)
    else:
        rng.choice(B["sashes"]).cyl(P(0, 0, hz + 0.13), 0.12, 0.05, 10, r2=0.1)
    if rng.random() < 0.6:
        B["beard"].ico(P(0.09, 0, hz - 0.09), 0.085, (0.8, 1, 1.1), 1)
    for side in (-1, 1):
        if pose == "gesture" and side == 1:
            hand = P(0.42, 0.24, sh - 0.1)
        elif pose == "carry":
            hand = P(0.3, side * 0.2, sh - 0.25)
        else:
            hand = P(0.08, side * 0.3, sh - 0.52)
        robe.seg(P(0, side * 0.2, sh), hand, 0.065, 0.05)
        B["skin"].ico(hand, 0.055, (1, 1, 1), 1)
    if pose == "carry":
        B["sack"].ico(P(0.36, 0, sh - 0.18), 0.24, (1, 1.2, 0.8), 1)


def bz_stall(B, x, y, face, kind, rng):
    """A stall facing 'face' (+1 looks towards +x, -1 towards -x): poles, striped awning with a sag, draped table, wares."""
    f = face
    for dy in (-2.0, 2.0):
        B["wood"].cyl((x - f * 1.3, y + dy, 1.6), 0.07, 1.6, 6)
        B["wood"].cyl((x + f * 1.5, y + dy, 1.25), 0.07, 1.25, 6)
    aw = rng.choice(B["awnings"])
    aw.box((x + f * 0.1, y, 2.95), (1.75, 2.35, 0.04), (0, -f * 0.26, 0))
    aw.box((x + f * 1.75, y, 2.42), (0.3, 2.35, 0.035), (0, -f * 0.95, 0))        # hanging front flap
    B["wood"].box((x, y, 0.42), (0.85, 1.9, 0.42))
    rng.choice(B["cloths"]).box((x, y, 0.86), (0.95, 2.0, 0.03))
    rng.choice(B["cloths"]).box((x + f * 0.93, y, 0.52), (0.03, 2.0, 0.36))
    for k in range(-3, 4):
        px, py = x + rng.uniform(-0.45, 0.45), y + k * 0.52
        if kind == "pottery":
            sc_ = rng.uniform(0.7, 1.25)
            B["clay"][k % 2].lathe([(0.0, 0.0), (0.15 * sc_, 0.02), (0.25 * sc_, 0.26 * sc_), (0.19 * sc_, 0.5 * sc_), (0.09 * sc_, 0.6 * sc_),
                                    (0.13 * sc_, 0.67 * sc_)], 12, (px, py, 0.9))
        elif kind == "fruit":
            B["basket"].cyl((px, py, 0.98), 0.24, 0.09, 12)
            g = rng.choice(B["fruit"])
            for _ in range(6):
                g.ico((px + rng.uniform(-0.14, 0.14), py + rng.uniform(-0.14, 0.14), 1.1 + rng.uniform(0, 0.1)), rng.uniform(0.07, 0.12), (1, 1, 1), 1)
        elif kind == "spice":
            B["clay"][0].lathe([(0.0, 0.0), (0.18, 0.02), (0.25, 0.12)], 12, (px, py, 0.9))
            rng.choice(B["spice"]).cyl((px, py, 1.1), 0.2, 0.14, 12, r2=0.01)
        elif kind == "bread":
            for j in range(rng.randint(3, 6)):
                B["bread"].cyl((px, py, 0.93 + j * 0.05), 0.2, 0.025, 12)
        else:                                                                   # cloth: bolts of fabric
            rng.choice(B["robes"]).cyl((px, y + k * 0.52, 1.0 + 0.1 * (k % 2)), 0.1, 0.42, 10, rot=(0, math.pi / 2, 0))
    for _ in range(3):                                                          # big jars and sacks on the ground in front
        gx, gy = x + f * rng.uniform(1.3, 2.0), y + rng.uniform(-2.2, 2.2)
        if rng.random() < 0.5:
            B["clay"][1].lathe([(0.0, 0.0), (0.22, 0.03), (0.38, 0.4), (0.3, 0.8), (0.14, 0.95), (0.2, 1.02)], 12, (gx, gy, 0.0))
        else:
            B["sack"].ico((gx, gy, 0.3), 0.36, (1, 0.85, 0.85), 1)
    bz_person(B, x - f * 1.25, y + rng.uniform(-1, 1), 0.0 if f > 0 else math.pi, rng, rng.choice(["stand", "gesture", "sit"]))


def bz_build(view):
    sc = reset()
    mg_render_tweaks(sc, vol=False)
    info = mg_sky("hilly_terrain_01_puresky", 0.85, sun_az=-52, sun_el=21, sun_power=5.6, sun_col=(1.0, 0.8, 0.56), view_az=95)
    exposure(0.1)
    rng = random.Random(41)

    def h(x, y):
        return mg_fbm(x / 60, y / 60, 3, 2) * 0.12
    gm = mg_ground_mat("bzsquare", [("dirt", 0.3, (1.08, 0.94, 0.76)), ("dry_ground_rocks", 0.3, (1.05, 0.93, 0.78)),
                                    ("brown_mud_dry", 0.3, (1.12, 0.98, 0.8))], 0.02, fb=(0.66, 0.54, 0.38))
    mg_terrain("bzground", 3000, 240, h, gm, 0, 80, 2.2)
    brick = mg_ph("bzbrick", "yellow_brick", 1.0, tint=(1.16, 0.93, 0.7), fb=(0.78, 0.6, 0.4))
    carved = mg_ph("bzcarved", "patterned_brick_wall", 0.55, tint=(1.32, 1.04, 0.76), fb=(0.74, 0.56, 0.38))
    dark = mat("bzdark", (0.05, 0.035, 0.025), 0.9)
    woodm = mg_ph("bzwood", "rough_wood", 0.9, tint=(0.62, 0.42, 0.26), fb=(0.36, 0.24, 0.14))
    carvedwood = mg_ph("bzdoor", "rough_wood", 0.5, tint=(0.46, 0.27, 0.15), fb=(0.3, 0.18, 0.1))
    lattice = mg_lattice_mat("bzlattice", wood=(0.34, 0.2, 0.1), paper=(0.12, 0.08, 0.05), k=5.0)
    glaze = mat("bzglaze", (0.1, 0.52, 0.56), 0.25)
    wall, trim, dk, door, lat, gl, dome = MgB(), MgB(), MgB(), MgB(), MgB(), MgB(), MgB()
    # --- the great portal (pishtaq) on the north side, with a deep pointed arch and a narrow band of turquoise glaze
    wall.box((0, 129, 9.0), (9.0, 3.0, 9.0))
    trim.box((-7.4, 125.7, 9.0), (1.4, 0.4, 9.0))
    trim.box((7.4, 125.7, 9.0), (1.4, 0.4, 9.0))
    trim.box((0, 125.7, 16.6), (9.0, 0.4, 1.4))
    gl.box((0, 125.25, 14.9), (6.0, 0.06, 0.22))
    dk.box((0, 125.9, 5.2), (5.6, 0.1, 5.2))
    dk.ico((0, 125.9, 10.2), 5.6, (1.0, 0.03, 0.82), 3)
    door.box((0, 126.4, 2.3), (1.7, 0.1, 2.3))
    for sx in (-9.6, 9.6):                                                      # corner towers with little domes
        trim.cyl((sx, 126.5, 9.6), 1.15, 9.6, 16, r2=1.0)
        mg_dome(dome, sx, 126.5, 19.2, 1.15, 1.25, 16)
    bz_arcade(wall, trim, dk, door, lat, (-40, 124), (-11, 124), "S")
    bz_arcade(wall, trim, dk, door, lat, (11, 124), (40, 124), "S")
    bz_arcade(wall, trim, dk, door, lat, (-40, 6), (-40, 124), "E")              # west side, facing east
    bz_arcade(wall, trim, dk, door, lat, (40, 6), (40, 124), "W")                # east side, facing west
    for (dx, dy, r) in ((-20, 142, 7.0), (20, 142, 7.0), (0, 150, 9.0)):        # brick domes on drums behind the portal
        wall.cyl((dx, dy, 6.0), r + 0.5, 6.0, 28)
        mg_dome(dome, dx, dy, 12.0, r, 1.2, 32)
    wall.finish("bz_walls", brick)
    trim.finish("bz_trim", carved)
    dome.finish("bz_domes", brick, smooth=True)
    dk.finish("bz_niches", dark)
    door.finish("bz_doors", carvedwood)
    lat.finish("bz_lattice", lattice)
    gl.finish("bz_glaze", glaze)
    mg_kalyan(-58, 150, 0.0)
    # --- timber porch (ayvan) on carved columns along the west arcade
    pw, pr = MgB(), MgB()
    for i in range(12):
        y = 14 + i * 9
        pw.cyl((-34.5, y, 2.4), 0.16, 2.4, 10, r2=0.11)
        pw.box((-34.5, y, 4.9), (0.34, 0.34, 0.14))
        pw.cyl((-34.5, y, 0.25), 0.26, 0.25, 10, r2=0.18)
    pw.box((-34.5, 63.5, 5.15), (0.2, 50.5, 0.14))
    pr.box((-37.0, 63.5, 5.35), (3.0, 50.5, 0.07), (0, -0.05, 0))
    pw.finish("bz_porch", woodm)
    pr.finish("bz_porchroof", mg_ph("bzreed", "rough_wood", 2.0, tint=(0.8, 0.66, 0.42), fb=(0.6, 0.5, 0.32)))
    # --- wares, cloth and people share builders so the whole market is a handful of objects
    def M(name, col, rough=0.8):
        return mat(name, col, rough)
    robe_cols = [(0.55, 0.1, 0.1), (0.1, 0.22, 0.45), (0.14, 0.36, 0.24), (0.72, 0.5, 0.12), (0.4, 0.14, 0.36), (0.82, 0.78, 0.68), (0.3, 0.2, 0.14)]
    B = {
        "robes": [MgB() for _ in range(len(robe_cols) + 3)], "sashes": [MgB() for _ in range(4)], "turbans": [MgB() for _ in range(4)],
        "skin": MgB(), "beard": MgB(), "sack": MgB(), "wood": MgB(), "basket": MgB(), "bread": MgB(),
        "awnings": [MgB() for _ in range(5)], "cloths": [MgB() for _ in range(4)], "clay": [MgB(), MgB()],
        "fruit": [MgB() for _ in range(4)], "spice": [MgB() for _ in range(4)],
    }
    lane = [(-9.0, 1), (9.0, -1)]
    kinds = ["pottery", "fruit", "spice", "cloth", "bread", "fruit", "cloth", "pottery", "spice"]
    for row, (sx, face) in enumerate(lane):
        for i in range(9):
            bz_stall(B, sx, 14 + i * 9.6 + (2.5 if row else 0), face, kinds[(i + row * 3) % len(kinds)], rng)
    for (sx, face) in ((-27.0, 1), (27.0, -1)):                                 # shorter rows near the arcades
        for i in range(5):
            bz_stall(B, sx, 24 + i * 15, face, kinds[(i * 2 + 1) % len(kinds)], rng)
    people = 0
    for _ in range(46):                                                         # buyers in the lane, in twos and threes
        gx, gy = rng.uniform(-5.5, 5.5), rng.uniform(8, 104)
        n = rng.choice([1, 2, 2, 3])
        for k in range(n):
            a = 2 * math.pi * k / max(1, n) + rng.uniform(-0.4, 0.4)
            bz_person(B, gx + 0.55 * n * math.cos(a) * 0.6, gy + 0.55 * n * math.sin(a) * 0.6, a + math.pi + rng.uniform(-0.3, 0.3), rng,
                      rng.choice(["stand", "stand", "gesture", "carry"]))
            people += 1
    for _ in range(26):                                                         # people under the porch and by the arcades
        side = rng.choice((-1, 1))
        bz_person(B, side * rng.uniform(30, 37), rng.uniform(12, 116), rng.uniform(0, 6.28), rng, rng.choice(["stand", "sit", "sit", "gesture"]))
        people += 1
    print("BAZAAR people:", people)
    for b_, c_ in zip(B["robes"][:len(robe_cols)], robe_cols):
        b_.finish("bz_robe", M("bzrobe%d" % robe_cols.index(c_), c_, 0.85), smooth=True)
    B["robes"][-3].finish("bz_robe_s1", mg_stripe_mat("bzikat1", (0.6, 0.1, 0.1), (0.88, 0.74, 0.3), 5.0, 0), smooth=True)
    B["robes"][-2].finish("bz_robe_s2", mg_stripe_mat("bzikat2", (0.1, 0.25, 0.42), (0.85, 0.82, 0.72), 6.0, 1), smooth=True)
    B["robes"][-1].finish("bz_robe_s3", mg_stripe_mat("bzikat3", (0.16, 0.38, 0.22), (0.78, 0.56, 0.16), 4.0, 0), smooth=True)
    for b_, c_ in zip(B["sashes"], [(0.82, 0.62, 0.14), (0.7, 0.12, 0.1), (0.9, 0.88, 0.8), (0.12, 0.3, 0.5)]):
        b_.finish("bz_sash", M("bzsash%.2f" % c_[0], c_, 0.8))
    for b_, c_ in zip(B["turbans"], [(0.93, 0.91, 0.85), (0.86, 0.8, 0.62), (0.58, 0.12, 0.1), (0.2, 0.36, 0.5)]):
        b_.finish("bz_turban", M("bzturban%.2f" % c_[0], c_, 0.9), smooth=True)
    B["skin"].finish("bz_skin", M("bzskin", (0.62, 0.42, 0.29), 0.7), smooth=True)
    B["beard"].finish("bz_beard", M("bzbeard", (0.09, 0.07, 0.06), 0.9), smooth=True)
    B["sack"].finish("bz_sacks", M("bzsack", (0.74, 0.62, 0.42), 0.95), smooth=True)
    B["wood"].finish("bz_stallwood", woodm)
    B["basket"].finish("bz_baskets", M("bzbasket", (0.56, 0.4, 0.2), 0.9))
    B["bread"].finish("bz_bread", M("bzbread", (0.82, 0.62, 0.32), 0.9), smooth=True)
    aw_mats = [mg_stripe_mat("bzaw1", (0.72, 0.14, 0.1), (0.92, 0.86, 0.72), 1.6, 1), mg_stripe_mat("bzaw2", (0.12, 0.3, 0.52), (0.9, 0.84, 0.68), 1.6, 1),
               mg_stripe_mat("bzaw3", (0.84, 0.6, 0.14), (0.6, 0.16, 0.1), 1.2, 1), mg_stripe_mat("bzaw4", (0.16, 0.42, 0.3), (0.92, 0.88, 0.76), 1.6, 1),
               M("bzaw5", (0.9, 0.84, 0.7), 0.9)]
    for b_, m_ in zip(B["awnings"], aw_mats):
        b_.finish("bz_awning", m_)
    cl_mats = [mg_stripe_mat("bzcl1", (0.56, 0.08, 0.08), (0.1, 0.12, 0.3), 3.0, 1), M("bzcl2", (0.14, 0.2, 0.44), 0.9),
               mg_stripe_mat("bzcl3", (0.8, 0.58, 0.16), (0.5, 0.1, 0.1), 2.4, 1), M("bzcl4", (0.5, 0.1, 0.12), 0.9)]
    for b_, m_ in zip(B["cloths"], cl_mats):
        b_.finish("bz_cloth", m_)
    B["clay"][0].finish("bz_clay1", M("bzclay1", (0.66, 0.36, 0.2), 0.6), smooth=True)
    B["clay"][1].finish("bz_clay2", M("bzclay2", (0.2, 0.48, 0.5), 0.3), smooth=True)   # glazed turquoise ware
    for b_, c_ in zip(B["fruit"], [(0.3, 0.5, 0.14), (0.86, 0.66, 0.16), (0.62, 0.1, 0.1), (0.86, 0.42, 0.1)]):
        b_.finish("bz_fruit", M("bzfruit%.2f" % c_[0], c_, 0.5), smooth=True)
    for b_, c_ in zip(B["spice"], [(0.85, 0.55, 0.08), (0.62, 0.14, 0.08), (0.36, 0.42, 0.14), (0.45, 0.28, 0.14)]):
        b_.finish("bz_spice", M("bzspice%.2f" % c_[0], c_, 0.95))
    # --- carpets laid out and hung (real carpet patterns need UVs, so these are planes)
    rugs = [mg_rug_mat("bzrug1"), mg_rug_mat("bzrug2", (0.08, 0.14, 0.32), (0.5, 0.08, 0.06), (0.82, 0.66, 0.3)),
            mg_rug_mat("bzrug3", (0.56, 0.3, 0.08), (0.3, 0.06, 0.06), (0.9, 0.84, 0.66))]
    for i, (x, y) in enumerate(((-2, 6.5), (2.6, 9.5), (-20, 60), (-17, 64), (19, 86), (16, 90), (0, 108), (4, 111))):
        add("plane", (x, y, 0.05 + 0.01 * i), (1.5, 2.3, 1), (0, 0, rng.uniform(-0.4, 0.4)), m=rugs[i % 3])
    for i, y in enumerate((30, 34, 38)):                                         # carpets hanging on a rail by the west porch
        add("plane", (-33.2, y, 2.4), (1.6, 1.9, 1), (0, math.pi / 2, 0), m=rugs[i % 3])
    # --- animals and a cart
    try:
        cm = MG_M.setdefault("camelhide", noisy("camelhide", (0.42, 0.32, 0.2), (0.55, 0.43, 0.28), 4, 0.9, 0.15))
        lb = MgB()
        for k in range(4):
            x, y = 17 + k * 4.4, 104 + rng.uniform(-0.6, 0.6)
            mg_inst(mg_camel_me(), (x, y, 0.0), math.pi, 1.0, cm)
            for sy in (-0.55, 0.55):
                lb.ico((x - 0.2, y + sy, 1.75), 0.5, (1.2, 0.6, 0.9), 1)
        lb.finish("bz_loads", mat("bzload", (0.6, 0.2, 0.16), 0.9), smooth=True)
        coats = mg_coats()
        for (x, y, a) in ((-22, 100, 0.4), (-18, 103, 2.6), (24, 14, 1.2)):
            mg_inst(mg_horse_me(), (x, y, 0.0), a, 1.0, rng.choice(coats))
        wb, cb = MgB(), MgB()
        mg_wagon(wb, cb, 22, 44, 0.0, 1.3, True)
        wb.finish("bz_cart", woodm)
        cb.finish("bz_cartcover", mat("bzcover", (0.86, 0.8, 0.64), 0.9))
    except Exception as e_:
        print("animals skipped:", e_)
    # --- the town beyond, and two trees
    hb, dd = MgB(), MgB()
    for _ in range(140):
        x, y = rng.uniform(-220, 220), rng.uniform(165, 620)
        w, d, hh = rng.uniform(4, 9), rng.uniform(4, 8), rng.uniform(3.5, 8.5)
        hb.box((x, y, hh / 2 - 0.4), (w, d, hh / 2 + 0.4))
        hb.box((x, y - d + 0.25, hh + 0.35), (w, 0.25, 0.35))
        dd.box((x + rng.uniform(-w * 0.5, w * 0.5), y - d - 0.03, hh * 0.6), (0.4, 0.05, 0.5))
    hb.finish("bz_town", mg_ph("bzplaster", "clay_plaster", 0.35, tint=(0.98, 0.82, 0.62), fb=(0.72, 0.58, 0.4)))
    dd.finish("bz_townwin", dark)
    try:
        tb, lf = MgB(), MgB()
        for (x, y) in ((-24, 78), (26, 62)):
            mg_tree(tb, lf, x, y, 0, 10, rng, "willow")
        tb.finish("bz_trunks", MG_M.setdefault("bark", mg_ph("bark", "bark_willow", 1.0, tint=(0.7, 0.62, 0.55), fb=(0.3, 0.25, 0.2))))
        lf.finish("bz_leaves", mg_leaf_mat("bzleaf", (0.2, 0.36, 0.1), (0.42, 0.52, 0.16)), smooth=True)
    except Exception as e_:
        print("trees skipped:", e_)
    if view == "wide":
        mg_camera([(0.0, (30, -40, 19)), (1.0, (26, -34, 17))], 30, [(0.0, (-3, 70, 4.0)), (1.0, (-3, 72, 4.0))])
    else:
        mg_camera([(0.0, (3.2, 1.0, 2.2)), (1.0, (2.2, 6.0, 2.2))], 26, [(0.0, (-1.5, 80, 5.5)), (1.0, (-1.0, 82, 5.5))])
    mg_aerial(info["haze"], 2600, 0.55)
    return sc


SHOTS.update({"x_bazaar_wide": lambda: bz_build("wide"), "x_bazaar_street": lambda: bz_build("street")})
