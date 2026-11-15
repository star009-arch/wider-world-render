"""VOC pilot battle sequence v4 (owner review: scale and composition): Colachel 1741 as two forces fighting over a position.

Shots (about 24 s):
  1 WIDE      high establishing view: the company camp on the beach (palisade, gate, gun platform with gabions, tents,
              stores, flag), ships offshore, dunes, creek, palm groves; Travancore's army approaching in organised
              blocks along the inland track and round through the trees. Labels name the two sides. Narration D09.
  2 MEDIUM    defenders running to their places behind the palisade
  3 CLOSE     the officer gives the order
  4 MEDIUM    the volley: flashes, recoil, smoke drifting along the line (front rank, then rear rank)
  5 MEDIUM    Travancore's line reacts: shots strike ahead, the men go to cover behind an earth bank and return fire,
              a second body moves along the treeline to outflank
  6 WIDE      the ring closes on the land side

  python scripts/cartoon/vocbattle3.py still <1-6> <t> | render <i>/<n> <outdir> | mix <parts> <out> [music]
"""
from __future__ import annotations

import math
import random
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402
import vocbattle as B  # noqa: E402  (cast v2, helpers, ShotB/ShotC sets, grade, render+mix)
import vocart as A  # noqa: E402
import vocdemo as D  # noqa: E402
import vocfilm as VF  # noqa: E402
import vocfx as FX  # noqa: E402
import vocsets as VS  # noqa: E402
import vocship as V  # noqa: E402
from vocart import INK, Layer, W, H, S, mix, shade, light  # noqa: E402

P = D.P
M.CLIPS["crouch"] = (0.6, [(0.0, {}, {}), (0.25, {"y": -0.45, "sq": 0.88, "lean": 12, "head": -4}, {"brows": -0.6}),
                           (0.6, {"y": -0.5, "sq": 0.88, "lean": 10, "head": 0}, {"brows": -0.7})])
M.CLIPS["crouch_fire"] = (2.0, [(0.0, {"y": -0.5, "sq": 0.88, "lean": 10}, {}), (0.3, {"y": -0.2, "sh_l": 84, "el_l": -8, "lean": 6}, {"brows": -0.8}),
                                (0.9, {"y": -0.2, "sh_l": 86, "el_l": -6, "lean": 6}, {}), (0.95, {"y": -0.2, "lean": -8, "head": -6, "sh_l": 96}, {"mouth": "o"}),
                                (1.3, {"y": -0.2, "lean": 3, "sh_l": 86}, {}), (2.0, {"y": -0.5, "sq": 0.88, "lean": 10, "sh_l": 20}, {})])

SEA = (54, 112, 142)
SAND_L = (222, 196, 146)
LAND = (150, 146, 88)
LAT = (166, 92, 62)

# ------------------------------------------------------------------------------------------------ the high wide view
CAMP = [(470, 540), (640, 470), (900, 465), (1070, 540), (1020, 670), (760, 720), (520, 680)]       # palisade corners (oblique)
GATE = (3, 0.45, 0.62)                                                                              # edge index 3, gap along it
SHORE = [(0, 600), (240, 540), (520, 450), (760, 350), (1000, 270), (1260, 190), (1500, 150)]


def _edge_pts(a, b, step=9):
    n = max(1, int(math.dist(a, b) / step))
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n)]


def stakes_ring(L: Layer, front: bool, t):
    """Palisade stakes along the camp outline; back edges (behind the camp) or front edges (in front of it)."""
    cy = sum(p[1] for p in CAMP) / len(CAMP)
    rng = random.Random(4)
    for i in range(len(CAMP)):
        a, b = CAMP[i], CAMP[(i + 1) % len(CAMP)]
        is_front = (a[1] + b[1]) / 2 > cy
        if is_front != front:
            continue
        pts = _edge_pts(a, b)
        for j, (x, y) in enumerate(pts):
            k = j / max(1, len(pts) - 1)
            if i == GATE[0] and GATE[1] < k < GATE[2]:
                continue
            h = 24 * rng.uniform(0.9, 1.1)
            c = mix(B.LOG, (96, 66, 40), rng.random() * 0.5)
            L.poly([(x - 3.5, y), (x - 3.5, y - h), (x, y - h - 5), (x + 3.5, y - h), (x + 3.5, y)], c, 1.4)
            L.line([(x + 2, y - h), (x + 2, y - 2)], light(c, 0.3), 1.0, a=180)
        L.line([a, b], (90, 64, 40), 2.0, a=160)


def tent(L: Layer, x, y, s=1.0):
    c = (236, 228, 206)
    L.poly([(x - 22 * s, y), (x, y - 26 * s), (x + 22 * s, y)], c, 1.6)                                  # front gable
    L.poly([(x, y - 26 * s), (x + 34 * s, y - 34 * s), (x + 54 * s, y - 8 * s), (x + 22 * s, y)], shade(c, 0.86), 1.6)   # roof side
    L.poly([(x - 6 * s, y), (x, y - 14 * s), (x + 6 * s, y)], (90, 76, 60), 1.0)


def shed(L: Layer, x, y, w=90, h=24):
    L.rect((x, y - h, x + w, y), (176, 140, 96), 1.6)
    L.poly([(x - 8, y - h), (x + w * 0.3, y - h - 20), (x + w * 0.7 + 14, y - h - 24), (x + w + 10, y - h - 2)], (130, 110, 62), 1.6)


def barrels(L: Layer, x, y, n=4):
    for i in range(n):
        bx, by = x + (i % 3) * 13, y - (i // 3) * 10
        L.ellipse((bx - 6, by - 14, bx + 6, by), (120, 80, 48), 1.2)
        L.line([(bx - 6, by - 9), (bx + 6, by - 9)], (60, 52, 48), 1.2)


def sacks(L: Layer, x, y, n=6):
    for i in range(n):
        sx, sy = x + (i % 4) * 14, y - (i // 4) * 9
        L.blob([(sx - 7, sy), (sx - 6, sy - 10), (sx + 6, sy - 10), (sx + 7, sy)], (222, 204, 160), 1.2, n=3)


def mini_palm(L: Layer, x, y, h, t, seed):
    A.palm(L, x, y, h, t, lean=random.Random(seed).uniform(-0.15, 0.15), seed=seed, leaf=B.PALM, ink=1.2, nuts=False)


@lru_cache(maxsize=1)
def wide_static():
    s = A.sky(B.SKY_TOP, B.SKY_MID, B.SKY_LOW, 190, sun=(1700, 60), sun_col=(255, 236, 190))
    L = Layer()
    B.ghats(L, 150, (110, 118, 140), 60, 3, n=12)
    s.alpha_composite(A.haze(L.out(), B.SKY_MID, 0.5))
    G = Layer()
    G.poly([(-40, 160), (1960, 160), (1960, H + 20), (-40, H + 20)], LAND, 0)                    # inland ground
    rng = random.Random(8)
    Pt = Layer()                                                                                 # laterite and grass patches, soft-edged
    for i in range(160):
        x, y = rng.uniform(0, W), rng.uniform(200, H)
        r = rng.uniform(20, 70) * (0.5 + y / H)
        Pt.blob([(x - r, y), (x - r * 0.3, y - r * 0.4), (x + r * 0.6, y - r * 0.3), (x + r, y + r * 0.1), (x, y + r * 0.35)],
                mix(LAT, LAND, rng.uniform(0.35, 0.85)), 0, n=5)
    G.im.alpha_composite(Pt.out().filter(ImageFilter.GaussianBlur(6)).resize((W * S, H * S)))
    for i in range(500):                                                                         # scrub and grass tufts
        x, y = rng.uniform(0, W), rng.uniform(260, H)
        k = 0.5 + y / H
        G.line([(x, y), (x - 3 * k, y - 7 * k)], (98, 104, 56), 1.4 * k, a=170)
        G.line([(x, y), (x + 3 * k, y - 6 * k)], (98, 104, 56), 1.4 * k, a=170)
    sea = [(-40, 160)] + [(x, y - 4) for x, y in SHORE] + [(1960, 150), (1960, 160)]
    beach = [(x, y) for x, y in SHORE] + [(x + 60, y + 110) for x, y in SHORE[::-1]]
    G.poly(beach, SAND_L, 0)
    G.poly([(-40, 160), (1500, 150), (1500, 160)] + [(x, y) for x, y in SHORE[::-1]] + [(-40, 600)], SEA, 0)
    for i in range(5):                                                                           # dunes along the beach
        x, y = 160 + i * 300, 650 - i * 90
        G.blob([(x - 90, y), (x - 30, y - 22), (x + 40, y - 18), (x + 100, y + 4), (x, y + 16)], light(SAND_L, 0.08), 1.2, n=4)
        G.shade_poly([(x + 10, y - 18), (x + 40, y - 18), (x + 100, y + 4), (x + 30, y + 10)], shade(SAND_L, 0.86), 255)
    # the inland track to the camp gate, a creek running to the sea, a laterite rise
    G.line([(1960, 760), (1700, 720), (1440, 650), (1240, 615), (1050, 605)], (176, 110, 72), 22, curve=True)
    G.line([(1960, 760), (1700, 720), (1440, 650), (1240, 615), (1050, 605)], (192, 128, 86), 14, curve=True)
    G.line([(360, 1090), (330, 960), (250, 820), (150, 700), (60, 610)], (70, 120, 140), 16, curve=True)
    G.line([(360, 1090), (330, 960), (250, 820), (150, 700), (60, 610)], (110, 160, 176), 6, curve=True, a=160)
    G.blob([(1500, 1000), (1600, 900), (1760, 880), (1900, 930), (1960, 1060)], (150, 92, 62), 1.6, n=5)
    G.shade_poly([(1700, 890), (1760, 880), (1900, 930), (1960, 1060), (1760, 1060)], (120, 72, 50), 255)
    g = A.texturize(G.out(), B.tex(10, 40), 0.18)
    s.alpha_composite(g)
    # camp ground (trodden sand) and its contents behind the front wall
    C = Layer()
    C.poly(CAMP, (206, 182, 136), 0)
    stakes_ring(C, front=False, t=0)
    for x, y in ((590, 540), (650, 575), (720, 520), (830, 512), (890, 552)):
        tent(C, x, y, 1.0)
    shed(C, 540, 640)
    barrels(C, 660, 650, 6)
    sacks(C, 700, 668, 8)
    for x in (1030, 1060):                                                                       # gun platform: gabions and guns
        B.gabion(C, x, 600, 9, 14)
    for gy in (575, 625):
        B.cannon(C, 1000, gy, 0.32, facing=1)
    C.line([(760, 500), (760, 430)], INK, 2.4)
    s.alpha_composite(C.out())
    return s


class Formation:
    """A block of soldiers in ranks and files that marches in step (shared poses) and can halt."""

    def __init__(self, key, x0, y0, files, ranks, dx, dy, scale, walk_to, t0=0.0, flip=True, speed=1.0, halt_acts=None, keys=None):
        self.members = []
        for r in range(ranks):
            for c in range(files):
                k = keys[(r * files + c) % len(keys)] if keys else key
                x = x0 + c * dx + r * dy * 0.6
                y = y0 + r * dy
                self.members.append(P(k, x, y, scale * (1 + r * 0.03), flip=flip, walks=[(t0, x - (x0 - walk_to))], speed=speed,
                                      acts=halt_acts or []))


def paint_band(f, t, people, y0, y1):
    D.paint_all(f, t, [p for p in people if y0 <= p.ground < y1])


class Wide:
    dur = 8.0
    TOFF = 0.0
    LABELS = True

    def __init__(self):
        M.CUR_PLATE = "colachel_v2"
        M.SUN_FROM_RIGHT.add("colachel_v2")
        nk = ["travancore_1741:nair_v2", "travancore_1741:nair4_v2", "travancore_1741:nair3_v2", "travancore_1741:nair5_v2"]
        self.blockA = Formation(None, 1640, 650, 7, 4, 17, 13, 0.19, 1330, keys=nk)                 # along the track to the gate
        self.blockB = Formation(None, 1560, 870, 7, 3, 19, 14, 0.22, 1200, t0=0.6, keys=nk)         # through the southern grove
        self.blockC = Formation(None, 1520, 330, 9, 2, 15, 10, 0.15, 1120, t0=0.3, keys=nk)         # along the treeline to the beach
        self.cmd = P("travancore_1741:ramayyan_v2", 1790, 730, 0.24, flip=True, walks=[(0.0, 1480)])
        defenders = []
        for i, (x, y, tx) in enumerate(((700, 600, 1000), (740, 560, 1010), (660, 590, 985), (800, 600, 1005), (620, 560, 990),
                                        (860, 560, 970), (900, 600, 995))):
            defenders.append(P("travancore_1741:voc_v2" if i % 2 else "travancore_1741:voc2_v2", x, y, 0.17, walks=[(0.2 + i * 0.15, tx)],
                               speed=1.6))
        self.def_ = defenders
        rng = random.Random(3)
        self.palms = []
        for cx, cy, n, sp in ((1450, 330, 12, 260), (1700, 420, 10, 260), (1500, 880, 9, 300), (1250, 980, 6, 200), (300, 760, 5, 220),
                              (1150, 420, 5, 150)):
            for i in range(n):
                self.palms.append((cx + rng.uniform(-sp, sp), cy + rng.uniform(-60, 60), rng.uniform(56, 84) * (0.7 + cy / 1400), rng.randint(0, 999)))
        self.palms.sort(key=lambda q: q[1])

    def people(self):
        return self.blockA.members + self.blockB.members + self.blockC.members + [self.cmd] + self.def_

    def frame(self, t):
        T = t + self.TOFF
        f = wide_static().copy()
        L = Layer()
        A.water_band(L, 170, 560, T, SEA, rows=8, speed=8, density=1.6)
        off = 5 * math.sin(T)
        L.line([(x + off, y - 2) for x, y in SHORE], (246, 250, 248), 3, a=220, curve=True)
        f.alpha_composite(L.out())
        V.place(f, T, 330, 300, L=140, facing=1, sea=0.4, water=SEA, era=1741, wake=False)
        V.place(f, T + 2, 700, 238, L=105, facing=1, sea=0.4, water=SEA, era=1741, wake=False)
        fx = Layer()
        V._flag(fx, 762, 430, 34, 22, T * 1.3, [(176, 40, 40), (246, 242, 230), (40, 70, 140)], ink=1.4)
        VS.smoke_plume(fx, 610, 600, T, n=5, col=(170, 164, 160), rise=10, drift=-6, size=8, seed=2, a=200)   # cooking fire
        f.alpha_composite(fx.out())
        ppl = self.people()
        bands = [0, 400, 600, 700, 800, 900, 2000]
        for y0, y1 in zip(bands, bands[1:]):
            L = Layer()
            for x, y, h, sd in self.palms:
                if y0 <= y < y1:
                    mini_palm(L, x, y, h, T, sd)
            f.alpha_composite(L.out())
            paint_band(f, T, ppl, y0, y1)
            if y0 == 600:                                                # the front palisade passes in front of the camp
                L = Layer()
                stakes_ring(L, front=True, t=T)
                f.alpha_composite(L.out())
        if self.LABELS:
            fr = f
            if t > 0.6:
                VF.label(fr, "Company camp", 760, 380, a=VF.fade(t, 0.6, 99), size=34)
            if t > 2.0:
                VF.label(fr, "Travancore's army", 1600, 560, a=VF.fade(t, 2.0, 99), size=34)
            if t > 4.6:
                x, y = self.cmd.pos_at(T)
                VF.label(fr, "Ramayyan", x + 10, y - 70, a=VF.fade(t, 4.6, 99), size=24)
            VF.label(fr, "Colachel, 1741", 960, 60, a=VF.fade(t, 0.2, 99), size=40)
        else:
            VF.label(f, "The land side is cut off", 960, 60, a=VF.fade(t, 0.4, 99), size=40)
        k = 1 + 0.07 * (t / self.dur) if self.LABELS else 1.07 - 0.05 * (t / self.dur)
        cx, cy = 1000, 600
        f = f.crop((int(cx - cx / k), int(cy - cy / k), int(cx + (W - cx) / k), int(cy + (H - cy) / k))).resize((W, H), Image.LANCZOS)
        return B.Base.grade(None, f, t)


class WideEnd(Wide):
    dur = 3.0
    TOFF = 9.0
    LABELS = False

    def frame(self, t):
        f = super().frame(t)
        return f


# ------------------------------------------------------------------------------------------------ medium and close shots
class Take(B.ShotB):
    """Defenders run to their places behind the palisade; the officer points them on."""
    dur = 3.4
    VOLLEY = 99.0

    def setup(self):
        super().setup()
        g = 930
        self.line = []
        for i in range(4):
            x = 700 + i * 250
            self.line.append(P("travancore_1741:voc_v2" if i % 2 == 0 else "travancore_1741:voc2_v2", x - 520 - i * 60, g - i * 10, 1.75,
                               walks=[(0.0 + i * 0.1, x)], speed=1.9, acts=[(2.2 + i * 0.12, "brace", None)], props={"prop_l": "musket_aim"},
                               faces=[(0.0, {"brows": -0.5})]))
        self.rear = []
        self.V2 = 99.0
        self.perf = self.line + [P("travancore_1741:delannoy_v2", 400, g + 40, 1.85, acts=[(0.2, "point", None), (1.8, "shout", None)],
                                   faces=[(0.0, {"brows": -0.6})], props={"prop_l": "sword"})]


class Order(B.Base):
    """Close-up: the officer gives the order to fire."""
    dur = 1.4

    def setup(self):
        sb = B.ShotB()
        self.bg = sb.frame(0.5).filter(ImageFilter.GaussianBlur(8)).convert("RGBA")
        self.perf = [P("travancore_1741:delannoy_v2", 900, 1700, 5.2, acts=[(0.15, "shout", None)], faces=[(0.0, {"brows": -0.9})],
                       props={"prop_l": "sword"})]

    def frame(self, t):
        f = self.bg.copy()
        old = M.SHADE
        M.SHADE = False                                                   # big close-up: flat cel colour (no form-shading stripes)
        D.paint_all(f, t, self.perf)
        M.SHADE = old
        return B.Base.grade(None, f, t)


class Volley(B.ShotB):
    dur = 3.4
    VOLLEY = 0.7

    def setup(self):
        super().setup()
        v, v2 = self.VOLLEY, 2.1
        for i, p in enumerate(self.line):
            p.acts = [(0.0, "brace", None), (v - 0.95 + i * 0.03, "aim_fire", None), (v + 1.3, "reload", None)]
            p.__post_init__()
        for i, p in enumerate(self.rear):
            p.acts = [(0.0, "brace", None), (v2 - 0.95 + i * 0.03, "aim_fire", None)]
            p.__post_init__()
        self.V2 = v2


class React(B.ShotC):
    """Travancore's line comes under fire, goes to cover behind an earth bank and returns fire; a second body
    moves along the treeline to outflank the camp."""
    dur = 5.0
    HIT = 0.9

    def setup(self):
        super().setup()
        g = 900
        nk = ["nair_v2", "nair4_v2", "nair3_v2", "nair5_v2", "nair_v2", "nair4_v2"]
        self.line = []
        for i, k in enumerate(nk):
            x = 1150 + i * 120
            self.line.append(P(f"travancore_1741:{k}", x + 260, g + (i % 2) * 16, 1.45, flip=True, walks=[(0.0, x)],
                               acts=[(self.HIT + 0.1 + i * 0.05, "crouch", None)], faces=[(0.0, {"brows": -0.8})]))
        self.shoot = [P("travancore_1741:nair2_v2", 1240, g - 10, 1.45, flip=True, acts=[(self.HIT + 0.2, "crouch", None), (2.1, "crouch_fire", None)],
                        props={"prop_l": "matchlock_aim"}, faces=[(0.0, {"brows": -0.9})]),
                      P("travancore_1741:nair5_v2", 1500, g + 6, 1.45, flip=True, acts=[(self.HIT + 0.25, "crouch", None), (2.6, "crouch_fire", None)],
                        props={"prop_l": "matchlock_aim"}, faces=[(0.0, {"brows": -0.9})])]
        flank = []
        for i in range(8):
            flank.append(P(f"travancore_1741:{nk[i % len(nk)]}", 1900 + i * 70, 700 - (i % 2) * 6, 0.8, flip=True, walks=[(0.0, 900 + i * 70)],
                           speed=1.2))
        self.flank = flank
        self.perf = self.flank + self.line + self.shoot
        self.shooters = self.shoot
        self.trunks = [(1060, g - 30, 380)]

    def frame(self, t):
        f = self.static.copy()

        def extra(L):
            for x in range(0, 1960, 240):
                B.bush(L, x + 60, 690, 1.0, seed=x + 3)
        B.draw_belt(f, t, self.belt, extra)
        fxb = Layer()
        B.log_wall(fxb, -40, 380, 700, 60, seed=2)
        B.smoke_bank(fxb, t + 4, 640, -40, 420, density=0.8, a=140)
        f.alpha_composite(A.haze(fxb.out(), B.SKY_MID, 0.25))
        D.paint_all(f, t, self.flank)
        D.paint_all(f, t, self.line + self.shoot)
        L = Layer()                                                       # the earth bank they shelter behind
        L.blob([(980, 1060), (1080, 1000), (1300, 984), (1700, 990), (1960, 1010), (1960, 1100), (980, 1100)], (150, 108, 70), 2.6, n=6)
        L.shade_poly([(980, 1060), (1080, 1030), (1960, 1040), (1960, 1100), (980, 1100)], (120, 84, 54), 255)
        for x, gy, h in self.trunks:
            A.palm(L, x, gy + 40, h + 300, t, lean=0.04, seed=int(x), leaf=B.PALM, ink=2.8)
        f.alpha_composite(A.texturize(L.out(), B.tex(11, 30), 0.2))
        fx = Layer()
        for k, x in enumerate((1180, 1350, 1520, 1690)):                 # the company volley strikes the sand ahead of them
            FX.dust(fx, x, 925, t, self.HIT + k * 0.04, 1.4, (170, 130, 90))
        for p, tf in ((self.shoot[0], 2.1 + 0.95), (self.shoot[1], 2.6 + 0.95)):
            mx, my = D.muzzle_point(p, tf)
            FX.muzzle(fx, mx, my + 18, t, tf, f=-1, wind=(10, -10), size=1.4, seed=int(tf * 10))
        f.alpha_composite(fx.out())
        return self.grade(f, t)


TIMELINE = [(Wide, [("D09", 0.4)]), (Take, []), (Order, []), (Volley, []), (React, []), (WideEnd, [])]


def starts():
    out, t = [], 0.0
    for cls, _ in TIMELINE:
        out.append(t)
        t += cls.dur
    return out, t


# reuse the v2 renderer/mixer with this timeline
B.TIMELINE = TIMELINE
B.starts = starts
B._CACHE.clear()


def sound_plan():
    st, total = starts()
    S_ = {cls.__name__: s for (cls, _), s in zip(TIMELINE, st)}
    ev = [("@surf", 0.0, -20, Wide.dur), ("wind_steppe_1.wav", 0.0, -28, total), ("@surf", S_["WideEnd"], -22, WideEnd.dur)]
    ev += [("@musket", S_["Volley"] + Volley.VOLLEY + i * 0.03, -7, None) for i in range(4)]
    ev += [("@musket", S_["Volley"] + 2.1 + i * 0.03, -8, None) for i in range(3)]
    ev += [("@splash", S_["React"] + React.HIT + k * 0.04, -14, None) for k in range(4)]
    ev += [("@musket", S_["React"] + 3.05, -9, None), ("@musket", S_["React"] + 3.55, -9, None)]
    return ev


B.sound_plan = sound_plan

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        cls = TIMELINE[int(sys.argv[2]) - 1][0]
        out = Path("D:/Temp/cartoon/voc_demo/v4")
        out.mkdir(parents=True, exist_ok=True)
        fp = out / f"{sys.argv[2]}_{float(sys.argv[3]):.2f}.jpg"
        cls().frame(float(sys.argv[3])).save(fp, quality=90)
        print(fp)
    elif cmd == "render":
        i, n = map(int, sys.argv[2].split("/"))
        B.render_part(i, n, sys.argv[3])
    elif cmd == "mix":
        B.mix_film(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
