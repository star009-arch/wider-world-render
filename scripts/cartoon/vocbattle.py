"""VOC pilot, visual-quality sample v2 (owner review 15 Nov): Colachel 1741, a 25-second battle sequence in four shots.

Richer than the first demo: late-afternoon golden light with cool shadows, painted texture and grain, layered hills,
a Kerala fishing village (steep thatched roofs, boats, nets), three depths of palms and undergrowth, a log stockade with
lashings, gabions and a cannon emplacement, a drifting smoke bank, a cannon with recoil, volleys with reloading,
skirmishers firing from cover, advancing swordsmen, reactions and expressions.

  python scripts/cartoon/vocbattle.py still <shot A|B|C|D> <t>
  python scripts/cartoon/vocbattle.py render <i>/<n> <outdir>
  python scripts/cartoon/vocbattle.py mix <parts dir> <out.mp4> [music]
"""
from __future__ import annotations

import math
import os
import random
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402
import people as PP  # noqa: E402
import voccast  # noqa: E402,F401
import vocart as A  # noqa: E402
import vocdemo as D  # noqa: E402
import vocfx as FX  # noqa: E402
import vocsets as VS  # noqa: E402
import vocship as V  # noqa: E402
from vocart import INK, Layer, W, H, S, hexc, mix, shade, light  # noqa: E402

P = D.P
SUN = (1640, 230)
SKY_TOP, SKY_MID, SKY_LOW = (46, 92, 146), (214, 182, 140), (240, 210, 162)
PALM = (62, 104, 46)
PALM_LIT = (122, 150, 58)
SAND = (204, 176, 130)
SAND_WET = (168, 138, 96)
LATERITE = hexc("#A65A3A")
LOG = (128, 88, 54)

# ---- richer cast for this sample (same body system, more period detail)
from dataclasses import replace  # noqa: E402
TW = PP.WORLDS["travancore_1741"]
ADULT = dict(head_k=0.70, height=1.25, eye_k=0.8, arm_w=0.62)   # documentary proportions, about 5 heads tall (hosts unchanged)
TW["nair_v2"] = replace(TW["nair"], bracelets=True, tiraz=True, earrings=True, sash=True, garment_col2=(176, 40, 36), build=1.1, **ADULT)
TW["nair2_v2"] = replace(TW["nair2"], bracelets=True, tiraz=True, sash=True, garment_col2=(176, 40, 36), build=1.12, **ADULT)
TW["nair3_v2"] = replace(TW["nair3"], bracelets=True, tiraz=True, earrings=True, sash=True, garment_col2=(30, 90, 70), build=1.08, **ADULT)
TW["ramayyan_v2"] = replace(TW["ramayyan"], bracelets=True, tiraz=True, build=1.15, **ADULT)
TW["voc_v2"] = replace(TW["voc_soldier"], build=1.1, flags=("kit",), **ADULT)
TW["voc2_v2"] = replace(TW["voc_soldier2"], build=1.15, flags=("kit",), **ADULT)
TW["nair4_v2"] = replace(TW["nair"], bracelets=True, tiraz=True, earrings=True, cloak="shawl", cloak_col=(244, 241, 232), cloak_trim=(212, 170, 64),
                         shield_col=(150, 44, 36), garment_col2=(212, 170, 64), skin=(140, 92, 60), build=1.05, **ADULT)
TW["nair5_v2"] = replace(TW["nair2"], bracelets=True, sash=True, garment_col2=(40, 70, 120), skin=(160, 108, 72), beard="full2",
                         beard_col=(30, 26, 24), build=1.15, **ADULT)
TW["delannoy_v2"] = replace(TW["delannoy"], build=1.08, **ADULT)

M.CLIPS.update({
    "reload": (2.4, [(0.0, {}, {}), (0.3, {"sh_l": 40, "el_l": 70, "lean": 4}, {"brows": -0.4}),
                     (0.6, {"sh_l": 150, "el_l": 10, "head": -4}, {}), (0.9, {"sh_l": 60, "el_l": 60}, {}),
                     (1.2, {"sh_l": 150, "el_l": 10}, {}), (1.5, {"sh_l": 60, "el_l": 60}, {}),
                     (2.0, {"sh_l": 84, "el_l": -8, "lean": 5}, {"brows": -0.6}), (2.4, {"sh_l": 84, "el_l": -8, "lean": 5}, {})]),
    "shout": (1.4, [(0.0, {}, {}), (0.2, {"sh_l": 130, "el_l": -10, "lean": 6, "head": 6}, {"brows": -0.9, "mouth": "D"}),
                    (0.7, {"sh_l": 100, "el_l": 0, "lean": 8, "head": 4}, {"mouth": "C"}), (1.4, {"sh_l": 96, "el_l": 0, "lean": 6}, {"mouth": "D"})]),
    "duck": (1.0, [(0.0, {}, {}), (0.12, {"y": -0.35, "sq": 0.9, "lean": 14, "head": -10, "sh_l": 60, "el_l": 70}, {"brows": 0.7, "blink": 1.0}),
                   (0.6, {"y": -0.2, "lean": 8, "head": -4}, {"brows": 0.4}), (1.0, {"y": 0.0, "lean": 4, "head": 0}, {"brows": -0.5})]),
    "charge": (0.8, [(0.0, {}, {}), (0.3, {"sh_l": 150, "el_l": 20, "lean": 12, "head": 6}, {"brows": -0.9, "mouth": "D"}),
                     (0.8, {"sh_l": 140, "el_l": 25, "lean": 12}, {"mouth": "D"})]),
})


# ================================================================================================ drawing the world
@lru_cache(maxsize=4)
def tex(seed, scale=70):
    return A.noise_tex((W, H), scale, seed)


def sky_v2():
    s = A.sky(SKY_TOP, SKY_MID, SKY_LOW, 600, sun=SUN, sun_col=(255, 236, 190))
    s = A.texturize(s, tex(1, 160), 0.05)
    for i, (cx, cy, sc) in enumerate(((330, 150, 1.6), (980, 96, 1.1), (1320, 230, 0.9), (620, 300, 0.7))):
        s.alpha_composite(A.soft_cloud(cx, cy, sc, i + 11))
    return s


def ghats(L: Layer, y0, col, amp, seed, n=9):
    rng = random.Random(seed)
    pts = [(-40, y0 + 200)] + [(-40 + i * 2040 / n, y0 - rng.uniform(0, amp)) for i in range(n + 1)] + [(2000, y0 + 200)]
    L.blob(pts, col, 2.2, n=6)
    for i in range(14):                                               # ridge lines
        x = rng.uniform(0, W)
        L.line([(x, y0 - amp * 0.4), (x + rng.uniform(-60, 60), y0 + 40)], shade(col, 0.88), 1.4, a=140)


def bush(L: Layer, x, y, s, col=(46, 86, 40), seed=0):
    rng = random.Random(seed)
    bumps = [(rng.uniform(-1.2, 1.2), rng.uniform(-0.8, 0.1), rng.uniform(0.35, 0.65)) for _ in range(7)]

    def fn(d, k):
        for bx, by, r in bumps:
            R = r * 60 * s
            d.ellipse([(x + bx * 50 * s - R) * k, (y + by * 50 * s - R) * k, (x + bx * 50 * s + R) * k, (y + by * 50 * s + R) * k], fill=255)
    form = A.union_shape(fn, col, shade(col, 0.72), 2.4, shade_dy=0.3)
    L.im.alpha_composite(form.resize((W * S, H * S), Image.BILINEAR))
    for bx, by, r in bumps:                                          # leaf strokes, lit on the sun side (right)
        cx, cy = x + bx * 50 * s, y + by * 50 * s
        for j in range(5):
            a_ = -2.4 + j * 0.45
            x0, y0 = cx + math.cos(a_) * r * 40 * s, cy + math.sin(a_) * r * 40 * s
            L.line([(x0, y0), (x0 + math.cos(a_ + 0.6) * 12 * s, y0 + math.sin(a_ + 0.6) * 12 * s)],
                   PALM_LIT if a_ > -1.2 else shade(col, 0.6), 2.0 * s, a=210)


def kerala_house(L: Layer, x, y, w, h, roof=(132, 104, 64), wall=(196, 150, 104)):
    L.rect((x, y - h, x + w, y), wall, 2.6)
    L.shade_poly([(x + w * 0.55, y - h), (x + w, y - h), (x + w, y), (x + w * 0.55, y)], shade(wall, 0.8), 255)
    L.rect((x + w * 0.2, y - h * 0.62, x + w * 0.38, y), (70, 50, 36), 2)
    rx = w * 0.22
    L.poly([(x - rx, y - h), (x + w * 0.25, y - h - h * 1.1), (x + w * 0.75, y - h - h * 1.1), (x + w + rx, y - h)], roof, 2.6)  # hipped roof
    L.shade_poly([(x + w * 0.75, y - h - h * 1.1), (x + w + rx, y - h), (x + w * 0.5, y - h)], shade(roof, 0.78), 255)
    for i in range(1, 6):
        k = i / 6
        L.line([(x - rx + (w * 0.25 + rx) * k, y - h - h * 1.1 * k), (x + w + rx - (w * 0.25 + rx) * k, y - h - h * 1.1 * k)], shade(roof, 0.7), 1.2)


def boat(L: Layer, x, y, ln, col=(110, 76, 46)):
    L.blob([(x - ln / 2, y - 8), (x - ln / 2 + 14, y + 6), (x + ln / 2 - 14, y + 6), (x + ln / 2, y - 10), (x, y - 4)], col, 2.4, n=4)
    L.line([(x - ln / 2 + 10, y - 6), (x + ln / 2 - 10, y - 7)], shade(col, 0.7), 1.6)


def nets(L: Layer, x, y):
    L.line([(x, y), (x, y - 70)], LOG, 4)
    L.line([(x + 90, y), (x + 90, y - 66)], LOG, 4)
    L.line([(x, y - 66), (x + 90, y - 62)], (90, 70, 50), 2)
    for i in range(9):
        L.line([(x + i * 11, y - 66 + i * 0.4), (x + 6 + i * 10, y - 18)], (150, 140, 120), 1.2, a=200)


def gabion(L: Layer, x, y, r=34, h=58):
    L.rect((x - r, y - h, x + r, y), (150, 116, 70), 2.6)
    L.shade_poly([(x + r * 0.3, y - h), (x + r, y - h), (x + r, y), (x + r * 0.3, y)], (110, 84, 52), 255)
    for i in range(-3, 4):
        L.line([(x + i * r / 3.5, y - h + 2), (x + i * r / 3.5, y - 2)], (96, 72, 44), 1.4)
    for j in range(1, 5):
        L.line([(x - r, y - h + j * h / 5), (x + r, y - h + j * h / 5)], (120, 92, 58), 1.0, a=180)
    L.ellipse((x - r, y - h - 10, x + r, y - h + 10), (110, 80, 56), 2.4)
    L.ellipse((x - r + 6, y - h - 6, x + r - 6, y - h + 6), (92, 66, 46), 0)


def log_wall(L: Layer, x0, x1, base, h, seed=3, lit=True):
    """Upright sharpened logs with bark lines, lashing and a sunlit edge (sun from the right)."""
    rng = random.Random(seed)
    x = x0
    while x < x1:
        w = rng.uniform(17, 23)
        hh = h * rng.uniform(0.9, 1.06)
        tip = hh + w * 0.85
        c = mix(LOG, (92, 64, 40), rng.random() * 0.5)
        pts = [(x, base), (x, base - hh), (x + w / 2, base - tip), (x + w, base - hh), (x + w, base)]
        L.poly(pts, c, 2.4)
        L.shade_poly([(x, base), (x, base - hh), (x + w / 2, base - tip), (x + w * 0.45, base - hh), (x + w * 0.45, base)], shade(c, 0.74), 255)
        if lit:
            L.line([(x + w - 3, base - hh), (x + w - 3, base - 4)], light(c, 0.35), 2.0, a=200)
        for k in range(3):
            yy = base - hh * rng.uniform(0.15, 0.9)
            L.line([(x + 3, yy), (x + w * 0.6, yy + rng.uniform(-3, 3))], shade(c, 0.58), 1.1)
        x += w - 2
    for yy in (base - h * 0.3, base - h * 0.72):                     # rope lashing
        L.line([(x0, yy), (x1, yy - 2)], (176, 150, 100), 3.2)
        L.line([(x0, yy + 2), (x1, yy)], INK, 1.0, a=160)


def cannon(L: Layer, x, y, s, recoil=0.0, facing=1):
    """1740s iron field gun on a wooden carriage with spoked wheels (sun from the right)."""
    x = x - facing * recoil * 30 * s
    f = facing
    L.poly([(x - f * 70 * s, y - 6 * s), (x + f * 40 * s, y - 34 * s), (x + f * 52 * s, y - 24 * s), (x - f * 62 * s, y + 6 * s)], (110, 76, 44), 2.4)
    L.poly([(x - f * 20 * s, y - 40 * s), (x + f * 110 * s, y - 52 * s), (x + f * 112 * s, y - 38 * s), (x - f * 20 * s, y - 24 * s)], (58, 58, 64), 2.6)
    L.line([(x - f * 10 * s, y - 37 * s), (x + f * 108 * s, y - 49 * s)], (120, 122, 130), 2.0, a=200)
    for wx in (x - f * 2 * s,):
        r = 30 * s
        L.ellipse((wx - r, y - r, wx + r, y + r), (124, 86, 50), 2.6)
        for k in range(8):
            a = k / 8 * math.pi + recoil * 2
            L.line([(wx + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9), (wx - math.cos(a) * r * 0.9, y - math.sin(a) * r * 0.9)], (80, 56, 34), 2.0)
        L.ellipse((wx - 6 * s, y - 6 * s, wx + 6 * s, y + 6 * s), (60, 50, 44), 1.6)


def smoke_bank(L: Layer, t, y, x0, x1, density=1.0, seed=2, col=(214, 206, 196), a=150):
    """A low drifting bank of powder smoke that thickens as the fight goes on."""
    rng = random.Random(seed)
    puffs = []
    n = int(14 * density)
    for i in range(n):
        bx = x0 + (x1 - x0) * rng.random()
        puffs.append((bx + 14 * t * rng.uniform(0.6, 1.4), y + rng.uniform(-30, 20) - 4 * t, rng.uniform(40, 90)))
    FX._puffs(L, puffs, col=col, ink=1.4, alpha=a)


# ================================================================================================ shots
def banana(L: Layer, x, y, s, t, seed=0):
    rng = random.Random(seed)
    L.line([(x, y), (x + 4 * s, y - 70 * s)], (110, 120, 60), 9 * s)
    for i in range(6):
        a = -math.pi / 2 + (i - 2.5) * 0.5 + 0.06 * math.sin(t * 1.4 + i + seed)
        ln = rng.uniform(60, 95) * s
        bx, by = x + 4 * s, y - 70 * s
        tip = (bx + math.cos(a) * ln, by + math.sin(a) * ln * 0.8 + ln * 0.25)
        mid = ((bx + tip[0]) / 2, (by + tip[1]) / 2)
        nx, ny = -(tip[1] - by) / ln * 16 * s, (tip[0] - bx) / ln * 16 * s
        L.poly([(bx, by), (mid[0] + nx, mid[1] + ny), tip, (mid[0] - nx * 0.6, mid[1] - ny * 0.6)], (86, 132, 56) if i % 2 else (70, 112, 46), 1.8)
        L.line([(bx, by), tip], (150, 170, 90), 1.2)


def palm_belt(seed, x0, x1, y0, rows=((0.55, 0.42, 34), (0.8, 0.22, 26), (1.0, 0.08, 20))):
    """Palms in three depth rows: (size, haze, spacing) far to near, irregular spacing, heights and leans."""
    rng = random.Random(seed)
    out = []
    for r, (sz, hz, sp) in enumerate(rows):
        x = x0 + rng.uniform(0, sp * 3)
        while x < x1:
            out.append((x, y0 + r * 22 + rng.uniform(-6, 8), rng.uniform(150, 290) * sz, rng.uniform(-0.2, 0.2), rng.randint(0, 999), hz, r))
            x += sp * rng.uniform(2.2, 5.0) * (1 + r * 0.5)
    return out


def draw_belt(f, t, belt, extra=None):
    for r in (0, 1, 2):
        L = Layer()
        for px, py, h, lean, sd, hz, rr in belt:
            if rr != r:
                continue
            A.palm(L, px, py, h, t, lean=lean, seed=sd, leaf=mix(PALM, (120, 140, 70), 0.15 * (2 - r)), ink=1.6 + 0.4 * r)
        if extra and r == 2:
            extra(L)
        f.alpha_composite(A.haze(L.out(), SKY_MID, [0.42, 0.22, 0.08][r]))


def ground_shadows(L: Layer, belt, ground_y=None, k=0.95):
    """Long afternoon shadows of the palms on the ground, falling away from the sun (to the left)."""
    for px, py, h, lean, sd, hz, rr in belt:
        if rr == 0:
            continue
        gy = py if ground_y is None else ground_y
        tip = (px - h * k, gy + h * 0.10)
        L.shade_poly([(px - 5, gy), (px + 5, gy), (tip[0] + 4, tip[1]), (tip[0] - 4, tip[1])], (60, 50, 70), 70)
        L.ellipse((tip[0] - h * 0.32, tip[1] - h * 0.05, tip[0] + h * 0.18, tip[1] + h * 0.06), (60, 50, 70), 0, a=60)


def ripples(L: Layer, box, seed=0, col=SAND):
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    for i in range(70):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        w = rng.uniform(30, 90) * (0.5 + (y - y0) / max(1, y1 - y0))
        L.d.arc([(x - w) * S, (y - 6) * S, (x + w) * S, (y + 6) * S], 200, 340, fill=shade(col, 0.86) + (90,), width=2 * S)
        L.d.arc([(x - w) * S, (y - 4) * S, (x + w) * S, (y + 8) * S], 200, 340, fill=light(col, 0.12) + (60,), width=1 * S)


@lru_cache(maxsize=2)
def sun_shafts(sun=SUN, n=6, seed=3):
    rng = random.Random(seed)
    m = Image.new("L", (W // 2, H // 2), 0)
    d = ImageDraw.Draw(m)
    sx, sy = sun[0] / 2, sun[1] / 2
    for i in range(n):
        a = math.radians(rng.uniform(112, 150))
        w = rng.uniform(0.03, 0.07)
        L_ = 1400
        p1 = (sx + math.cos(a - w) * L_, sy + math.sin(a - w) * L_)
        p2 = (sx + math.cos(a + w) * L_, sy + math.sin(a + w) * L_)
        d.polygon([(sx, sy), p1, p2], fill=int(rng.uniform(26, 46)))
    m = m.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
    out = Image.new("RGBA", (W, H), (255, 232, 180, 0))
    out.putalpha(m)
    return out


class Base:
    dur = 6.0

    def __init__(self):
        M.CUR_PLATE = "colachel_v2"                                    # characters cast shadows away from the sun (to the left)
        M.SUN_FROM_RIGHT.add("colachel_v2")
        self.perf = []
        self.static = None
        self.setup()

    def setup(self):
        pass

    def grade(self, f, t):
        f = f.convert("RGBA")
        f.alpha_composite(sun_shafts())
        return A.grade2(f, sun=SUN, t=t)


def far_layers(horizon=560, sea=True):
    s = sky_v2()
    L = Layer()
    ghats(L, horizon - 70, (116, 120, 150), 120, 4)
    s.alpha_composite(A.haze(L.out(), SKY_MID, 0.55))
    L = Layer()
    ghats(L, horizon - 20, (86, 108, 92), 70, 7, n=12)
    s.alpha_composite(A.haze(L.out(), SKY_MID, 0.32))
    return s


class ShotA(Base):
    """Wide: the stockade on the beach (left) fires its gun; Nair skirmishers advance through the palms (right);
    Ramayyan signals on his name. Slow push-in."""
    dur = 6.5

    def setup(self):
        rng = random.Random(1)
        s = far_layers()
        L = Layer()
        A.gradient_rect(L, (0, 560, 760, 610), (66, 120, 150), (44, 96, 128))           # sea on the left
        s.alpha_composite(L.out())
        L = Layer()
        L.poly([(-40, 600), (760, 590), (1960, 600), (1960, H + 20), (-40, H + 20)], SAND, 0)
        L.poly([(-40, 600), (760, 590), (700, 640), (-40, 660)], SAND_WET, 0)
        A.gradient_rect(L, (0, 780, W, H), SAND, shade(SAND, 0.82))
        A.ground_texture(L, (0, 640, W, H), SAND, n=300, seed=4, a=110)
        ripples(L, (0, 680, W, H), seed=2)
        self.belt = palm_belt(1, 760, 1960, 600)
        ground_shadows(L, self.belt)
        g = A.texturize(L.out(), tex(2, 50), 0.2)
        s.alpha_composite(g)
        V_ = Layer()                                                   # the village among the palms
        for x, w_ in ((900, 70), (1010, 60), (1500, 74), (1610, 60), (1760, 66)):
            kerala_house(V_, x, 620, w_, 30)
        for x in (220, 330, 470):
            boat(V_, x, 650, 120)
        nets(V_, 560, 650)
        s.alpha_composite(A.haze(V_.out(), SKY_MID, 0.12))
        self.static = s
        self.palms = sorted([(x + rng.uniform(-20, 20), 610 + rng.uniform(-6, 30), rng.uniform(170, 230), rng.uniform(-0.1, 0.14), i)
                             for i, x in enumerate(range(780, 1960, 80))], key=lambda q: q[1])
        g = 860
        main = []                                                     # the main body behind, marching in step (same start, same pace)
        for i, (dx, dy, key) in enumerate(((0, 0, "nair_v2"), (90, 8, "nair4_v2"), (180, -4, "nair3_v2"), (270, 6, "nair5_v2"),
                                           (360, -2, "nair_v2"), (450, 4, "nair4_v2"))):
            main.append(P(f"travancore_1741:{key}", 1500 + dx, g - 130 + dy, 0.82, flip=True, walks=[(0.0, 1200 + dx)]))
        self.main = main
        self.perf = [P("travancore_1741:nair_v2", 1420, g + 40, 1.25, flip=True, walks=[(0.3, 1120)], acts=[(2.3, "duck", None)],
                       faces=[(0.0, {"brows": -0.8})]),
                     P("travancore_1741:nair3_v2", 1560, g + 10, 1.2, flip=True, walks=[(0.0, 1240)], acts=[(2.35, "duck", None)],
                       faces=[(0.0, {"brows": -0.7})]),
                     P("travancore_1741:nair2_v2", 1700, g + 30, 1.22, flip=True, walks=[(0.5, 1400)], acts=[(2.4, "duck", None)]),
                     P("travancore_1741:nair_v2", 1300, g - 30, 1.05, flip=True, walks=[(0.0, 1000)]),
                     P("travancore_1741:nair3_v2", 1820, g - 40, 1.0, flip=True, walks=[(0.2, 1500)]),
                     P("travancore_1741:ramayyan_v2", 1760, g + 90, 1.4, flip=True, acts=[(4.6, "signal", None)], faces=[(0.0, {"brows": -0.6})]),
                     P("travancore_1741:voc_v2", 250, 770, 1.0, acts=[(1.0, "aim_fire", None)], props={"prop_l": "musket_aim"}),
                     P("travancore_1741:voc2_v2", 420, 760, 0.98)] + main

    def frame(self, t):
        f = self.static.copy()
        L = Layer()
        A.water_band(L, 566, 605, t, (60, 116, 146), rows=4, speed=10, density=1.4)
        off = 6 * math.sin(t * 0.9)
        L.line([(-40, 652 + off), (300, 640 + off), (600, 628 + off), (760, 598)], (244, 248, 246), 4, a=220, curve=True)
        f.alpha_composite(L.out())
        def extra(L):
            for x in (840, 1100, 1350, 1640, 1900):
                bush(L, x, 660, 0.9, seed=x)
            for x in (980, 1460, 1720):
                banana(L, x, 650, 1.0, t, seed=x)
        draw_belt(f, t, self.belt, extra)
        # the stockade (left), gabions, the gun and its flag
        L = Layer()
        log_wall(L, 60, 640, 800, 120, seed=3)
        for x in (520, 590):
            gabion(L, x, 812, 30, 50)
        rec = max(0.0, 1 - abs(t - 2.0) * 3) if t > 2.0 else 0.0
        cannon(L, 470, 790, 1.0, recoil=rec, facing=1)
        L.line([(140, 690), (140, 520)], INK, 4)
        V._flag(L, 144, 520, 90, 56, t * 1.2, [(176, 40, 40), (246, 242, 230), (40, 70, 140)], ink=2.4)
        f.alpha_composite(A.texturize(L.out(), tex(6, 18), 0.22))
        D.paint_all(f, t, self.perf)
        fx = Layer()
        FX.muzzle(fx, 590, 742, t, 2.0, f=1, wind=(-16, -10), size=2.2, seed=3)                        # the gun fires
        FX.dust(fx, 1260, 860, t, 2.6, 4.0, (206, 170, 120))                                         # the shot throws up sand
        FX.explosion(fx, 1262, 860, t, 2.6, 0.35, seed=9) if 2.6 <= t < 2.9 else None
        p = self.perf[6]
        mx, my = D.muzzle_point(p, 1.95)
        FX.muzzle(fx, mx, my, t, 1.95, f=1, wind=(-14, -8), size=1.0, seed=5)
        smoke_bank(fx, t, 700, 80, 700, density=0.6 + 0.1 * t, a=110)
        f.alpha_composite(fx.out())
        f.alpha_composite(self._foreground(t))
        k = 1 + 0.06 * t / self.dur                                    # slow, purposeful push-in towards the attackers
        cx, cy = 1100, 700
        f = f.crop((int(cx - cx / k), int(cy - cy / k), int(cx + (W - cx) / k), int(cy + (H - cy) / k))).resize((W, H), Image.LANCZOS)
        return self.grade(f, t)

    @staticmethod
    def _foreground(t):
        L = Layer()
        A.palm(L, 1900, 1120, 560, t, lean=-0.12, seed=31, leaf=(44, 80, 36), ink=3.2)
        bush(L, 60, 1060, 1.8, col=(36, 66, 32), seed=3)
        return L.out()


class ShotB(Base):
    """Inside the stockade: the company line presents, fires a volley and reloads; De Lannoy shouts orders."""
    dur = 6.0
    VOLLEY = 2.2

    def setup(self):
        s = far_layers()
        L = Layer()
        L.poly([(-40, 600), (1960, 600), (1960, H + 20), (-40, H + 20)], SAND, 0)
        A.gradient_rect(L, (0, 760, W, H), SAND, shade(SAND, 0.8))
        A.ground_texture(L, (0, 640, W, H), SAND, n=260, seed=7, a=110)
        s.alpha_composite(A.texturize(L.out(), tex(3, 50), 0.16))
        self.belt = palm_belt(4, -40, 1960, 600)
        L = Layer()
        log_wall(L, -40, 1960, 760, 150, seed=5)                        # far wall (the land side, facing the grove)
        s_wall = A.texturize(L.out(), tex(8, 16), 0.2)
        self.static = s
        self.wall = s_wall
        g = 930
        v = self.VOLLEY
        self.line = [P("travancore_1741:voc_v2", 700 + i * 250, g - i * 10, 1.75, flip=False,
                       acts=[(0.3 + i * 0.08, "brace", None), (v - 0.95 + i * 0.03, "aim_fire", None), (v + 1.3, "reload", None)],
                       props={"prop_l": "musket_aim"}, faces=[(0.0, {"brows": -0.5})]) for i in range(4)]
        for i, p in enumerate(self.line):
            if i % 2:
                p.key = "travancore_1741:voc2_v2"
                p.__post_init__()
        v2 = v + 1.5                                                  # the rear rank fires while the front rank reloads
        self.rear = [P("travancore_1741:voc2_v2" if i % 2 == 0 else "travancore_1741:voc_v2", 820 + i * 250, g - 90 - i * 8, 1.55,
                       acts=[(0.5 + i * 0.07, "brace", None), (v2 - 0.95 + i * 0.03, "aim_fire", None)], props={"prop_l": "musket_aim"},
                       faces=[(0.0, {"brows": -0.5})]) for i in range(3)]
        self.V2 = v2
        self.line[2].acts = self.line[2].acts + [(4.6, "flinch", None)]
        self.perf = self.rear + self.line + [P("travancore_1741:delannoy_v2", 400, g + 40, 1.85,
                                               acts=[(0.6, "shout", None), (v - 0.4, "shout", None), (v2 - 0.4, "shout", None)],
                                               faces=[(0.0, {"brows": -0.6})], props={"prop_l": "sword"})]

    def frame(self, t):
        f = self.static.copy()
        draw_belt(f, t, self.belt)
        f.alpha_composite(self.wall)
        fx0 = Layer()
        FX.fire(fx0, 160, 760, 80, 60, t, seed=4)                       # a store fire smouldering in the corner
        VS.smoke_plume(fx0, 160, 700, t, n=6, col=(96, 90, 88), rise=24, drift=-10, size=26, seed=5, a=210)
        f.alpha_composite(fx0.out())
        D.paint_all(f, t, self.perf)
        fx = Layer()
        for i, p in enumerate(self.line):
            tf = self.VOLLEY + i * 0.03
            mx, my = D.muzzle_point(p, tf)
            FX.muzzle(fx, mx, my, t, tf, f=1, wind=(-22, -6), size=1.5, seed=i + 1)
        for i, p in enumerate(self.rear):
            tf = self.V2 + i * 0.03
            mx, my = D.muzzle_point(p, tf)
            FX.muzzle(fx, mx, my, t, tf, f=1, wind=(-22, -6), size=1.3, seed=i + 7)
        FX.dust(fx, 1700, 690, t, 4.5, 2.0, (150, 110, 70))              # a Travancore ball splinters the wall top
        if t > self.VOLLEY:
            smoke_bank(fx, t - self.VOLLEY, 640, 600, 1960, density=1.2, a=160)
        f.alpha_composite(fx.out())
        L = Layer()                                                      # the land-side wall they fire over (right), gabions at its foot
        log_wall(L, 1660, 1960, 1000, 330, seed=11)
        for x in (1700, 1780, 1860):
            gabion(L, x, 1040, 40, 70)
        log_wall(L, -40, 1660, 1130, 270, seed=12)                        # the low inner rampart in the foreground (hides legs)
        f.alpha_composite(A.texturize(L.out(), tex(7, 16), 0.22))
        return self.grade(f, t)


class ShotC(Base):
    """The palm grove: matchlock men fire from behind trunks; swordsmen with shields advance; a ball strikes near them."""
    dur = 6.0

    def setup(self):
        s = far_layers()
        L = Layer()
        L.poly([(-40, 610), (1960, 610), (1960, H + 20), (-40, H + 20)], (150, 140, 84), 0)
        A.gradient_rect(L, (0, 760, W, H), (150, 140, 84), (110, 100, 60))
        rng = random.Random(5)
        for i in range(60):
            x, y = rng.uniform(0, W), rng.uniform(640, H)
            r = rng.uniform(20, 50) * (y / 800)
            L.ellipse((x - r, y - r * 0.25, x + r, y + r * 0.25), mix(LATERITE, (150, 140, 84), rng.uniform(0.3, 0.7)), 0)
        A.ground_texture(L, (0, 640, W, H), (150, 140, 84), n=300, seed=9, a=120)
        self.belt = palm_belt(5, -40, 1960, 610)
        ground_shadows(L, self.belt, k=1.1)
        s.alpha_composite(A.texturize(L.out(), tex(4, 50), 0.22))
        self.static = s
        g = 900
        self.shooters = [P("travancore_1741:nair2_v2", 1180, g - 30, 1.5, flip=True, acts=[(0.5, "aim_fire", None), (2.8, "reload", None)],
                           props={"prop_l": "matchlock_aim"}, faces=[(0.0, {"brows": -0.8})]),
                         P("travancore_1741:nair2_v2", 1560, g + 10, 1.6, flip=True, acts=[(1.4, "aim_fire", None), (3.7, "reload", None)],
                           props={"prop_l": "matchlock_aim"}, faces=[(0.0, {"brows": -0.8})])]
        self.perf = self.shooters + [
            P("travancore_1741:nair_v2", 1900, g + 60, 1.75, flip=True, walks=[(0.8, 900)], speed=1.3, acts=[(3.4, "charge", None)],
              faces=[(0.0, {"brows": -0.9})]),
            P("travancore_1741:nair3_v2", 2100, g + 20, 1.65, flip=True, walks=[(1.2, 1150)], speed=1.25, faces=[(0.0, {"brows": -0.8})]),
            P("travancore_1741:nair_v2", 2250, g + 80, 1.8, flip=True, walks=[(1.6, 1300)], speed=1.3, acts=[(4.2, "charge", None)],
              faces=[(0.0, {"brows": -0.9})]),
            P("travancore_1741:nair3_v2", 980, g - 70, 1.3, flip=True, acts=[(3.0, "duck", None)])]
        for i, (dx, key) in enumerate(((0, "nair4_v2"), (110, "nair_v2"), (220, "nair5_v2"), (330, "nair4_v2"), (440, "nair3_v2"))):
            self.perf.append(P(f"travancore_1741:{key}", 1700 + dx, g - 170 + (i % 2) * 10, 0.95, flip=True, walks=[(0.0, 1250 + dx)]))
        self.trunks = [(1100, g - 20, 360), (1480, g + 20, 400)]       # cover trunks the shooters stand behind

    def frame(self, t):
        f = self.static.copy()
        def extra(L):
            for x in range(0, 1960, 240):
                bush(L, x + 60, 690, 1.0, seed=x + 3)
            for x in (300, 760, 1640):
                banana(L, x, 680, 1.1, t, seed=x)
        draw_belt(f, t, self.belt, extra)
        fxb = Layer()                                                   # the stockade far away on the left, smoking
        log_wall(fxb, -40, 380, 700, 60, seed=2)
        smoke_bank(fxb, t + 4, 640, -40, 420, density=0.8, a=140)
        f.alpha_composite(A.haze(fxb.out(), SKY_MID, 0.25))
        D.paint_all(f, t, self.perf)
        L = Layer()
        for x, gy, h in self.trunks:                                     # the shooters' cover: trunks in front of them
            A.palm(L, x, gy + 40, h + 300, t, lean=0.04, seed=int(x), leaf=PALM, ink=2.8)
        f.alpha_composite(L.out())
        fx = Layer()
        for p, tf in ((self.shooters[0], 1.45), (self.shooters[1], 2.35)):
            mx, my = D.muzzle_point(p, tf)
            FX.muzzle(fx, mx, my, t, tf, f=-1, wind=(10, -10), size=1.4, seed=int(tf * 10))
        FX.dust(fx, 1020, 930, t, 3.0, 2.6, (150, 120, 80))              # a company musket ball strikes near them
        FX.dust(fx, 1100, 640, t, 4.1, 1.6, (170, 120, 80))              # and another splinters the bark of their cover
        f.alpha_composite(fx.out())
        L = Layer()
        bush(L, 1880, 1080, 2.2, col=(30, 60, 28), seed=7)
        bush(L, 40, 1100, 2.0, col=(30, 60, 28), seed=8)
        f.alpha_composite(L.out())
        return self.grade(f, t)


class ShotD(Base):
    """The powder store: fire reaches the barrels; the blast; the rice burns; the defenders react."""
    dur = 6.5
    BLAST = 1.7

    def setup(self):
        s = far_layers()
        L = Layer()
        L.poly([(-40, 600), (1960, 600), (1960, H + 20), (-40, H + 20)], SAND, 0)
        A.gradient_rect(L, (0, 760, W, H), SAND, shade(SAND, 0.8))
        A.ground_texture(L, (0, 640, W, H), SAND, n=240, seed=12, a=110)
        s.alpha_composite(A.texturize(L.out(), tex(5, 50), 0.16))
        L = Layer()
        log_wall(L, -40, 1960, 720, 150, seed=8)
        s.alpha_composite(A.texturize(L.out(), tex(9, 16), 0.2))
        self.static = s
        b = self.BLAST
        self.perf = [P("travancore_1741:voc_v2", 420, 960, 1.8, acts=[(b + 0.05, "flinch", None), (b + 1.8, "point", None)],
                       faces=[(b, {"brows": 0.8, "mouth": "o"})]),
                     P("travancore_1741:voc2_v2", 1420, 990, 1.85, flip=True, acts=[(b + 0.1, "cower", None)], faces=[(b, {"brows": 0.9})]),
                     P("travancore_1741:delannoy_v2", 1700, 950, 1.75, flip=True, acts=[(b + 0.12, "flinch", None), (b + 1.5, "shout", None)],
                       faces=[(b, {"brows": 0.7})], props={"prop_l": "sword"}),
                     P("travancore_1741:voc_v2", 2050, 900, 1.5, flip=True, walks=[(b + 0.8, 1250)], speed=1.6, faces=[(b, {"brows": 0.8})]),
                     P("travancore_1741:voc2_v2", 160, 905, 1.5, walks=[(b + 1.2, 560)], speed=1.5, faces=[(b, {"brows": 0.8})])]

    def frame(self, t):
        f = self.static.copy()
        L = Layer()
        L.poly([(620, 820), (624, 690), (1240, 676), (1250, 820)], (176, 150, 104), 3)                     # the store shed
        L.shade_poly([(1000, 820), (1000, 680), (1240, 676), (1250, 820)], (140, 118, 80), 255)
        L.poly([(600, 700), (930, 590), (1270, 690)], (120, 108, 64), 3)
        for i in range(5):
            L.line([(600 + i * 66, 700 - i * 22), (1270 - i * 68, 690 - i * 20)], (96, 86, 52), 1.4)
        for i in range(7):
            x = 680 + i * 70
            burnt = t > self.BLAST + 0.5 + i * 0.22
            L.blob([(x - 30, 820), (x - 28, 770), (x + 28, 770), (x + 30, 820)], (80, 62, 50) if burnt else (226, 206, 160), 2.6, n=3)
            if not burnt:
                L.line([(x - 12, 778), (x + 12, 776)], (150, 120, 80), 2)
        if t < self.BLAST:
            for x in (1120, 1180):                                       # powder barrels
                L.rect((x - 28, 752, x + 28, 820), (110, 72, 44), 3)
                for yy in (766, 806):
                    L.line([(x - 28, yy), (x + 28, yy)], (60, 52, 48), 3)
        f.alpha_composite(L.out())
        fx = Layer()
        if t < self.BLAST:                                               # fire creeping along the shed towards the barrels
            k = t / self.BLAST
            FX.fire(fx, 700 + 380 * k, 690, 120, 70, t, seed=2)
        FX.explosion(fx, 1150, 790, t, self.BLAST, 1.4, seed=4)
        if t > self.BLAST + 0.3:
            sp = min(1.0, (t - self.BLAST - 0.3) / 2.2)
            FX.fire(fx, 900, 820, 260 + 300 * sp, 140, t, seed=6)
            VS.smoke_plume(fx, 940, 700, t, n=9, col=(84, 78, 76), rise=30, drift=-14, size=44, seed=7, a=235)
        f.alpha_composite(fx.out())
        D.paint_all(f, t, self.perf)
        if self.BLAST <= t < self.BLAST + 0.12:                          # the flash lights everything
            fl = Image.new("RGBA", (W, H), (255, 236, 190, int(150 * (1 - (t - self.BLAST) / 0.12))))
            f.alpha_composite(fl)
        L = Layer()
        log_wall(L, -40, 360, 1120, 210, seed=14)
        f.alpha_composite(L.out())
        sh = 0.0 if not (self.BLAST <= t < self.BLAST + 0.6) else 14 * (1 - (t - self.BLAST) / 0.6)            # camera shake
        if sh:
            dx, dy = int(sh * math.sin(t * 90)), int(sh * math.cos(t * 70))
            f = f.crop((20 + dx, 12 + dy, W - 20 + dx, H - 12 + dy)).resize((W, H), Image.BILINEAR)
        return self.grade(f, t)


TIMELINE = [(ShotA, [("D09", 0.4)]), (ShotB, []), (ShotC, []), (ShotD, [("D10", 0.2)])]


def starts():
    out, t = [], 0.0
    for cls, _ in TIMELINE:
        out.append(t)
        t += cls.dur
    return out, t


_CACHE = {}


def frame_at(gt):
    st, total = starts()
    i = max(k for k, s in enumerate(st) if s <= gt + 1e-9)
    cls = TIMELINE[i][0]
    if cls not in _CACHE:
        _CACHE[cls] = cls()
    return _CACHE[cls].frame(gt - st[i])


# ================================================================================================ render and sound
import json  # noqa: E402
import subprocess  # noqa: E402
import vocfilm as VF  # noqa: E402

FPS = 24


def subtitle_cues():
    lines = {ln["id"]: ln for ln in json.loads((VF.VOICE / "lines.json").read_text(encoding="utf-8"))["lines"]}
    words = json.loads((VF.VOICE / "words.json").read_text(encoding="utf-8"))
    st, _ = starts()
    cues = []
    for (cls, vl), s0 in zip(TIMELINE, st):
        for lid, off in vl:
            tw = lines[lid]["subtitle"].replace("...", "").split()
            rec = words[lid]
            chunks, cur = [], []
            for w in tw:
                if cur and len(" ".join(cur + [w])) > 44:
                    chunks.append(cur)
                    cur = []
                cur.append(w)
                if w[-1] in ".?!" and len(" ".join(cur)) > 14:
                    chunks.append(cur)
                    cur = []
            if cur:
                chunks.append(cur)
            if len(chunks) > 1 and len(" ".join(chunks[-1])) < 14:
                last = chunks.pop()
                chunks[-1] = chunks[-1] + last
            n, k = len(tw), 0
            for ch in chunks:
                i0, i1 = k, k + len(ch) - 1
                a = rec[min(len(rec) - 1, int(i0 / n * len(rec)))][1]
                b = rec[min(len(rec) - 1, int(i1 / n * len(rec)))][2] if i1 < n - 1 else rec[-1][2]
                cues.append((s0 + off + a, s0 + off + b + 0.25, " ".join(ch)))
                k += len(ch)
    for i in range(len(cues) - 1):
        if cues[i][1] > cues[i + 1][0]:
            cues[i] = (cues[i][0], cues[i + 1][0] - 0.02, cues[i][2])
    return cues


_CUES = None


def full_frame(gt):
    global _CUES
    if _CUES is None:
        _CUES = subtitle_cues()
    fr = frame_at(gt)
    for a, b, text in _CUES:
        if a <= gt < b:
            d = ImageDraw.Draw(fr)
            d.text((960, 1010), text, font=VF._font(50), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(24, 20, 16))
    return fr


def render_part(i, n, outdir):
    import imageio_ffmpeg
    _, total = starts()
    nf = int(round(total * FPS))
    a, b = (i - 1) * nf // n, i * nf // n
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"part_{i:02d}.mp4"
    proc = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "medium", "-g", str(FPS),
                             str(out)], stdin=subprocess.PIPE)
    for k in range(a, b):
        proc.stdin.write(full_frame(k / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    print(out)


def sound_plan():
    st, total = starts()
    S_ = {cls.__name__: s for (cls, _), s in zip(TIMELINE, st)}
    ev = [("@surf", 0.0, -22, ShotA.dur + ShotB.dur), ("fire_crackle_1.wav", S_["ShotB"], -22, ShotB.dur),
          ("wind_steppe_1.wav", S_["ShotC"], -26, ShotC.dur), ("fire_crackle_1.wav", S_["ShotD"], -12, ShotD.dur)]
    ev += [("@explosion", S_["ShotA"] + 2.0, -6, None), ("@musket", S_["ShotA"] + 1.95, -12, None), ("@splash", S_["ShotA"] + 2.6, -10, None)]
    ev += [("@musket", S_["ShotB"] + ShotB.VOLLEY + i * 0.03, -7, None) for i in range(4)]
    ev += [("@musket", S_["ShotC"] + 1.45, -9, None), ("@musket", S_["ShotC"] + 2.35, -9, None), ("@musket", S_["ShotC"] + 3.0, -16, None)]
    ev += [("@explosion", S_["ShotD"] + ShotD.BLAST, -2, None)]
    return ev


def mix_film(parts_dir, out, music=None):
    """Same mixer as the demo (voices, beds, effects, ducked music, loudness to -14 LUFS)."""
    VF.TIMELINE = [(cls, cls.dur, vl) for cls, vl in TIMELINE]
    VF.sound_plan = sound_plan
    VF.mix(parts_dir, out, music)
    import imageio_ffmpeg
    tmp = Path(out).with_name("film_loud.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(out), "-c:v", "copy", "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(tmp)], check=True)
    print(tmp)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "render":
        i, n = map(int, sys.argv[2].split("/"))
        render_part(i, n, sys.argv[3])
    elif cmd == "mix":
        mix_film(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    if cmd == "still":
        cls = {"A": ShotA, "B": ShotB, "C": ShotC, "D": ShotD}[sys.argv[2]]
        out = Path("D:/Temp/cartoon/voc_demo/v2")
        out.mkdir(parents=True, exist_ok=True)
        cls().frame(float(sys.argv[3])).save(out / f"{sys.argv[2]}_{float(sys.argv[3]):.2f}.jpg", quality=90)
        print(out / f"{sys.argv[2]}_{float(sys.argv[3]):.2f}.jpg")
