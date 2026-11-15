"""VOC pilot backgrounds, drawn in code (Premium 2D style guide). Each set = static layers rendered once (cached) plus
animated layers drawn every frame, so nothing on screen is a still picture.

  s = Set(name)                 build once
  s.frame(t, actors_fn=None)    -> RGB frame; actors_fn(frame, t) draws characters/ships between the mid and front layers

Sets (palettes from research_notes/voc/02_visual_research.md section 6):
  banda_harbour     Banda Neira at dawn, 1620s: Fort Nassau on its low hill, Gunung Api smoking across the lagoon
  colachel_camp     Colachel beach, 1741: the company stockade, palm grove inland, the Arabian Sea, hot hazy afternoon
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

import vocart as A
from vocart import INK, Layer, W, H, S, hexc, mix, shade, light

BANDA = dict(jungle=hexc("#2F6B3A"), canopy=hexc("#234D2C"), volcanic=hexc("#3A3A3C"), lagoon=hexc("#2FA3A3"), nutmeg=hexc("#E2C25A"),
             mace=hexc("#C8282B"))
MALABAR = dict(palm=hexc("#4F7F3A"), laterite=hexc("#A65A3A"), mundu=hexc("#F4F1E8"), gold=hexc("#D4A62A"), monsoon=hexc("#7B8790"))
WHITEWASH = hexc("#F1EDE2")
STONE = (204, 192, 166)
THATCH = (176, 140, 84)
ROOF = hexc("#A8442E")


def _fort(L: Layer, x, y, w, h, stone=STONE, flag_t=None):
    """A small square stone fort with corner bastions seen from the side (Fort Nassau type)."""
    L.poly([(x, y), (x + w, y), (x + w - 8, y - h), (x + 8, y - h)], stone, 3.5)
    L.shade_poly([(x + w * 0.62, y), (x + w, y), (x + w - 8, y - h), (x + w * 0.62 - 4, y - h)], shade(stone, 0.82), 255)
    for bx in (x - 14, x + w - 22):                                   # bastions
        L.poly([(bx, y + 2), (bx + 36, y + 2), (bx + 32, y - h - 10), (bx + 4, y - h - 10)], light(stone, 0.12), 3.5)
        for i in range(4):                                            # crenels
            L.rect((bx + 4 + i * 8, y - h - 18, bx + 9 + i * 8, y - h - 10), light(stone, 0.12), 2)
    for gx in range(int(x + 30), int(x + w - 30), 26):                # embrasures
        L.rect((gx, y - h + 8, gx + 10, y - h + 15), (60, 50, 44), 1.6)
    L.rect((x + w / 2 - 12, y - 30, x + w / 2 + 12, y), (92, 64, 44), 2.5)         # gate
    L.line([(x + w / 2 - 12, y - 30), (x + w / 2, y - 38), (x + w / 2 + 12, y - 30)], INK, 2.5)


def _house(L: Layer, x, y, w, h, wall=(226, 206, 170), roof=THATCH, seed=0):
    """Stilt-and-plank house with a steep palm-thatch roof (Banda), inked."""
    L.rect((x, y - h, x + w, y), wall, 3)
    L.shade_poly([(x + w * 0.6, y - h), (x + w, y - h), (x + w, y), (x + w * 0.6, y)], shade(wall, 0.84), 255)
    L.rect((x + w * 0.3, y - h * 0.55, x + w * 0.48, y), (96, 66, 44), 2)
    L.poly([(x - 10, y - h), (x + w / 2, y - h - h * 0.95), (x + w + 10, y - h)], roof, 3)
    L.shade_poly([(x + w / 2, y - h - h * 0.95), (x + w + 10, y - h), (x + w / 2 + 6, y - h)], shade(roof, 0.8), 255)
    for i in range(1, 5):
        k = i / 5
        L.line([(x - 10 + (w / 2 + 10) * k, y - h - h * 0.95 * k), (x + w + 10 - (w / 2 + 10) * k, y - h - h * 0.95 * k)], shade(roof, 0.7), 1.2)


def _volcano(L: Layer, cx, base_y, half_w, peak_y, rock, green):
    cone = [(cx - half_w, base_y), (cx - half_w * 0.55, base_y - (base_y - peak_y) * 0.42), (cx - 46, peak_y + 6), (cx - 26, peak_y),
            (cx + 22, peak_y + 2), (cx + 44, peak_y + 8), (cx + half_w * 0.5, base_y - (base_y - peak_y) * 0.45), (cx + half_w, base_y)]
    L.blob(cone, rock, 3.5, n=5)
    L.shade_poly([(cx + 4, peak_y + 4), (cx + 44, peak_y + 8), (cx + half_w * 0.5, base_y - (base_y - peak_y) * 0.45), (cx + half_w, base_y),
                  (cx + half_w * 0.15, base_y)], shade(rock, 0.78), 255)
    # gullies
    for gx in (-0.5, -0.25, 0.08, 0.32):
        L.line([(cx + gx * 90, peak_y + 20), (cx + gx * half_w * 1.4, base_y - 30)], shade(rock, 0.65), 2.2, curve=False)
    # green lower slopes
    slope = [(cx - half_w, base_y), (cx - half_w * 0.75, base_y - 70), (cx - half_w * 0.3, base_y - 110), (cx + half_w * 0.25, base_y - 96),
             (cx + half_w * 0.7, base_y - 60), (cx + half_w, base_y)]
    L.blob(slope, green, 3, n=6)
    L.shade_poly([(cx + half_w * 0.1, base_y - 98), (cx + half_w * 0.25, base_y - 96), (cx + half_w * 0.7, base_y - 60), (cx + half_w, base_y),
                  (cx + half_w * 0.1, base_y)], shade(green, 0.8), 255)


def smoke_plume(L: Layer, x, y, t, n=7, col=(206, 200, 196), rise=36, drift=22, size=24, seed=0, a=230):
    """Rising, drifting smoke drawn as ONE inked form (overlapping puffs merged), looping continuously."""
    rng = random.Random(seed)
    puffs = []
    for i in range(n):
        ph = ((t * 0.18) + i / n) % 1.0
        r = size * (0.6 + 1.5 * ph) * rng.uniform(0.85, 1.15)
        puffs.append((x + drift * ph * 6 + math.sin(t * 0.7 + i) * 6, y - rise * ph * 6, r, ph))
    puffs = [p for p in puffs if p[3] < 0.92]

    def fn(d, k):
        for px, py, r, ph in puffs:
            d.ellipse([(px - r) * k, (py - r * 0.85) * k, (px + r) * k, (py + r * 0.85) * k], fill=255)
    form = A.union_shape(fn, col, shade(col, 0.84), 2.6, shade_dy=0.3)
    if a < 255:
        al = form.getchannel("A").point(lambda v: v * a // 255)
        form.putalpha(al)
    L.im.alpha_composite(form.resize((W * S, H * S), Image.BILINEAR))


class Set:
    def __init__(self, name):
        self.name = name
        getattr(self, "_build_" + name)()

    # ------------------------------------------------------------------------------------------ Banda harbour
    def _build_banda_harbour(self):
        self.horizon = 612
        sky = A.sky((96, 128, 176), (238, 186, 160), (252, 216, 172), self.horizon, sun=(380, 560), sun_col=(255, 226, 170))
        far = Layer()
        rng = random.Random(3)
        _volcano(far, 1500, self.horizon + 6, 430, 236, (92, 84, 96), (78, 116, 92))
        far_im = A.haze(far.out(), (238, 196, 170), 0.32)
        for i, (cx, cy, s) in enumerate(((280, 150, 1.0), (760, 96, 0.8), (1180, 170, 0.9), (1700, 110, 0.7))):
            sky.alpha_composite(A.haze(A.puff_cloud(cx, cy, s, i, col=(255, 236, 222), shade_col=(238, 196, 186), ink=2.6), (238, 196, 170), 0.15))
        mid = Layer()
        # Banda Neira: green hills on the left behind the town
        hills = [(-40, self.horizon), (-40, 470), (120, 430), (300, 455), (470, 420), (640, 480), (760, self.horizon)]
        mid.blob(hills, BANDA["jungle"], 3.5, n=6)
        mid.shade_poly([(300, 455), (470, 420), (640, 480), (760, self.horizon), (360, self.horizon)], shade(BANDA["jungle"], 0.8), 255)
        for i in range(26):                                           # canopy texture: rounded tree crowns
            x, y = rng.uniform(-20, 720), rng.uniform(450, 600)
            r = rng.uniform(16, 30)
            mid.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), mix(BANDA["canopy"], BANDA["jungle"], rng.uniform(0.2, 0.7)), 0)
            mid.d.arc([(x - r) * S, (y - r * 0.8) * S, (x + r) * S, (y + r * 0.8) * S], 200, 330, fill=light(BANDA["jungle"], 0.2) + (200,), width=2 * S)
        # the fort on its low hill
        mid.blob([(120, self.horizon), (190, 548), (420, 540), (520, self.horizon)], (120, 132, 82), 3, n=5)
        _fort(mid, 210, 560, 230, 52)
        mid.line([(325, 508), (325, 446)], INK, 3)                    # flagpole (flag animated)
        self.flag_at = (325, 446)
        # shore with houses
        mid.poly([(-40, self.horizon + 2), (760, self.horizon + 2), (820, self.horizon + 26), (-40, self.horizon + 30)], (226, 204, 156), 3)
        for i, x in enumerate((20, 100, 520, 600, 690)):
            _house(mid, x, self.horizon + 6, 52, 30, seed=i)
        self.mid_im = A.haze(mid.out(), (238, 196, 170), 0.12)
        self.static = sky
        self.static.alpha_composite(far_im)
        self.water_top = self.horizon + 18
        self.palms = [(36, 630, 120, 0.16, 1), (176, 628, 104, 0.08, 2), (492, 626, 110, -0.08, 3), (668, 632, 128, 0.12, 4)]

    def _anim_banda_harbour(self, t, frame):
        L = Layer()
        # lagoon: gradient water with a soft reflection of the volcano and the dawn sun
        A.gradient_rect(L, (0, self.water_top, W, H), mix(BANDA["lagoon"], (240, 190, 160), 0.35), shade(BANDA["lagoon"], 0.72))
        rng = random.Random(11)
        for i in range(26):                                           # sun glitter: short dashes that twinkle
            y = self.water_top + 8 + (i ** 1.35) * 4.2
            x = 380 + rng.uniform(-1, 1) * (30 + i * 6) + math.sin(t * 1.5 + i) * 10
            ln = 14 + i * 1.6
            al = int(120 + 120 * (0.5 + 0.5 * math.sin(t * 3 + i * 1.7)))
            L.line([(x - ln / 2, y), (x + ln / 2, y)], (255, 236, 196), 2.4 + i * 0.05, a=al)
        A.water_band(L, self.water_top + 6, H + 20, t, BANDA["lagoon"], rows=10, speed=10)
        frame.alpha_composite(L.out())
        frame.alpha_composite(self.mid_im)
        fx = Layer()
        smoke_plume(fx, 1478, 236, t, n=6, col=(214, 206, 204), rise=22, drift=16, size=20, seed=1, a=200)
        # fort flag (orange-white-blue before about 1630)
        x, y = self.flag_at
        import vocship as V
        V._flag(fx, x, y, 52, 32, t, [(224, 116, 40), (246, 242, 230), (40, 70, 140)])
        for px, py, h, lean, sd in self.palms:
            A.palm(fx, px, py, h, t, lean=lean, seed=sd, leaf=BANDA["jungle"])
        frame.alpha_composite(fx.out())

    # ------------------------------------------------------------------------------------------ Colachel camp
    def _build_colachel_camp(self):
        self.horizon = 560
        self.sun = (1560, 190)
        sky = A.sky((126, 166, 200), (232, 218, 192), (246, 228, 194), self.horizon, sun=self.sun, sun_col=(255, 244, 214))
        for i, (cx, cy, s) in enumerate(((380, 150, 0.9), (930, 96, 1.1), (1380, 200, 0.7))):
            sky.alpha_composite(A.puff_cloud(cx, cy, s, i + 5, col=(250, 246, 236), shade_col=(224, 220, 212), ink=2.6))
        far = Layer()
        far.blob([(820, self.horizon + 4), (1000, 452), (1180, 482), (1380, 418), (1580, 468), (1780, 430), (1980, 450), (1980, self.horizon + 4)],
                 (120, 138, 128), 3, n=6)                             # the Western Ghats, far inland
        self.static = sky
        self.static.alpha_composite(A.haze(far.out(), (232, 218, 192), 0.5))
        mid = Layer()
        rng = random.Random(7)
        belt = [(760, self.horizon + 2), (1960, self.horizon + 2), (1960, 700), (1700, 712), (1400, 694), (1150, 706), (900, 676), (700, 640)]
        mid.blob(belt, (148, 150, 86), 3, n=6)                        # palm belt: grass and laterite
        for i in range(70):
            x, y = rng.uniform(780, 1920), rng.uniform(self.horizon + 14, 690)
            r = rng.uniform(14, 34)
            mid.ellipse((x - r, y - r * 0.22, x + r, y + r * 0.22), A.mix(MALABAR["laterite"], (148, 150, 86), rng.uniform(0.35, 0.75)), 0)
        self.mid_im = mid.out()
        ground = Layer()
        sand = (226, 200, 150)
        ground.poly([(-40, 640), (700, 640), (900, 676), (1150, 706), (1400, 694), (1700, 712), (1960, 700), (1960, H + 20), (-40, H + 20)], sand, 0)
        A.gradient_rect(ground, (0, 780, W, H), sand, A.shade(sand, 0.88))
        A.ground_texture(ground, (0, 700, W, H), sand, n=240, seed=5, a=90)
        self.ground_im = ground.out()
        rng2 = random.Random(9)
        self.palms_back = [(x + rng2.uniform(-20, 20), self.horizon + 60 + rng2.uniform(-10, 40), rng2.uniform(170, 240), rng2.uniform(-0.1, 0.14), i)
                           for i, x in enumerate(range(800, 1960, 95))]
        self.palms_front = [(1890, 1080, 560, -0.1, 31)]
        self.floor_y = 900

    def _anim_colachel_camp(self, t, frame):
        L = Layer()
        shore = [(-40, self.horizon), (860, self.horizon), (760, 600), (600, 628), (300, 646), (-40, 660)]
        L.poly(shore, (84, 142, 166), 0)
        A.water_band(L, self.horizon + 6, 640, t, (84, 142, 166), rows=5, speed=12, density=1.3)
        off = 10 * math.sin(t * 0.9)                                  # surf line advancing and withdrawing
        L.line([(-40, 662 + off), (300, 648 + off), (600, 630 + off), (760, 602 + off), (860, self.horizon + 2)], (246, 250, 248), 5, a=230, curve=True)
        frame.alpha_composite(L.out())
        frame.alpha_composite(self.mid_im)
        fx = Layer()
        for px, py, h, lean, sd in sorted(self.palms_back, key=lambda q: q[1]):
            A.palm(fx, px, py, h, t, lean=lean, seed=sd, leaf=mix(MALABAR["palm"], (200, 206, 186), 0.18), ink=2.4)
        frame.alpha_composite(A.haze(fx.out(), (232, 218, 192), 0.12))
        frame.alpha_composite(self.ground_im)

    # ------------------------------------------------------------------------------------------ Banda quay (closer, plank floor)
    def _build_banda_quay(self):
        self._build_banda_harbour()
        self.sun = (380, 560)
        q = Layer()
        q.poly([(-40, 820), (1960, 800), (1960, H + 20), (-40, H + 20)], (150, 108, 70), 3.5)        # the quay deck
        for i in range(14):                                                                    # planks
            y = 820 + i * 20 + (i ** 1.6)
            q.line([(-40, y), (1960, y - 20 + i * 1.4)], A.shade((150, 108, 70), 0.72), 2.2)
        for x in range(-20, 1960, 140):
            q.line([(x, 812), (x - 60, H)], A.shade((150, 108, 70), 0.6), 1.6)
        q.poly([(-40, 820), (1960, 800), (1960, 812), (-40, 832)], (120, 84, 52), 2.4)          # the edge beam
        # warehouse on the left: plank wall, tile roof, open door with sacks
        q.poly([(-40, 820), (-40, 470), (330, 470), (330, 820)], (176, 128, 84), 3.5)
        q.shade_poly([(220, 820), (220, 470), (330, 470), (330, 820)], A.shade((176, 128, 84), 0.8), 255)
        for x in range(0, 330, 30):
            q.line([(x, 474), (x, 816)], A.shade((176, 128, 84), 0.7), 1.4)
        q.poly([(-60, 480), (150, 380), (360, 480)], ROOF, 3.5)
        q.rect((120, 640, 240, 820), (60, 42, 32), 3)
        rng = random.Random(4)
        for i in range(9):                                                                     # spice sacks and barrels
            x, y = 380 + (i % 5) * 54 + rng.uniform(-6, 6), 800 - (i // 5) * 40
            q.blob([(x - 26, y), (x - 24, y - 40), (x, y - 50), (x + 24, y - 40), (x + 26, y)], (196, 170, 120), 2.8, n=4)
            q.line([(x - 10, y - 44), (x + 8, y - 42)], (120, 90, 60), 2)
        for x in (1700, 1780):
            q.rect((x - 30, 740, x + 30, 812), (130, 88, 52), 3)
            for yy in (754, 798):
                q.line([(x - 30, yy), (x + 30, yy)], (70, 60, 56), 3)
        # crane post and beam (the jib swings in the animated layer)
        q.rect((1560, 470, 1584, 812), (120, 84, 52), 3)
        self.quay_im = q.out()

    def _anim_banda_quay(self, t, frame):
        self._anim_banda_harbour(t, frame)
        frame.alpha_composite(self.quay_im)
        L = Layer()
        a = math.radians(-12 + 14 * math.sin(t * 0.6))                                       # the crane jib swings the bale ashore
        x0, y0 = 1572, 480
        x1, y1 = x0 + math.cos(math.pi + a) * 320, y0 + math.sin(math.pi + a) * 320 * 0.3
        L.line([(x0, y0), (x1, y1)], (120, 84, 52), 12)
        L.line([(x0, y0), (x1, y1)], INK, 2)
        rope_y = y1 + 170 + 18 * math.sin(t * 1.2)
        L.line([(x1, y1), (x1 + 4 * math.sin(t * 1.4), rope_y)], (200, 180, 140), 3)
        bx = x1 + 4 * math.sin(t * 1.4)
        L.blob([(bx - 34, rope_y), (bx - 30, rope_y + 50), (bx + 30, rope_y + 50), (bx + 34, rope_y)], (204, 176, 120), 3, n=4)
        frame.alpha_composite(L.out())

    # ------------------------------------------------------------------------------------------ fort wall, low angle
    def _build_fort_wall(self):
        self.sun = (380, 300)
        sky = A.sky((96, 136, 186), (226, 196, 176), (250, 220, 186), 900, sun=(380, 300), sun_col=(255, 230, 180))
        for i, (cx, cy, s) in enumerate(((300, 180, 1.1), (1300, 120, 0.9))):
            sky.alpha_composite(A.puff_cloud(cx, cy, s, i + 2, col=(255, 240, 226), shade_col=(236, 200, 186), ink=2.6))
        self.static = sky
        w = Layer()
        stone = STONE
        w.poly([(-40, 760), (1960, 700), (1960, H + 20), (-40, H + 20)], stone, 4)            # parapet face (seen from below)
        w.shade_poly([(-40, 900), (1960, 860), (1960, H + 20), (-40, H + 20)], A.shade(stone, 0.85), 255)
        rng = random.Random(2)
        for row in range(6):                                                                    # masonry courses
            y = 780 + row * 52
            w.line([(-40, y), (1960, y - 60 + row * 4)], A.shade(stone, 0.72), 1.6)
            for x in range(int(rng.uniform(0, 80)), 1960, 150):
                yy = y + (x / 1960) * (-60 + row * 4)
                w.line([(x, yy), (x, yy + 52)], A.shade(stone, 0.72), 1.6)
        for x in range(-20, 1960, 190):                                                         # merlons
            y = 760 - (x / 1960) * 60
            w.poly([(x, y + 4), (x, y - 70), (x + 110, y - 74), (x + 110, y)], light(stone, 0.08), 4)
            w.shade_poly([(x + 76, y), (x + 76, y - 72), (x + 110, y - 74), (x + 110, y)], A.shade(stone, 0.82), 255)
        self.wall_im = w.out()
        self.floor_y = 760

    def _anim_fort_wall(self, t, frame):
        L = Layer()
        for px, py, h, lean, sd in ((1700, 760, 260, -0.1, 7), (1880, 740, 220, 0.08, 8), (120, 800, 240, 0.1, 9)):
            A.palm(L, px, py, h, t, lean=lean, seed=sd, leaf=BANDA["jungle"], ink=2.8)
        L.line([(980, 690), (980, 330)], INK, 6)
        import vocship as V
        V._flag(L, 984, 330, 150, 92, t * 1.3, [(224, 116, 40), (246, 242, 230), (40, 70, 140)], ink=3)
        frame.alpha_composite(L.out())

    # ------------------------------------------------------------------------------------------ road inland (South Travancore)
    def _build_road_inland(self):
        self.horizon = 600
        self.sun = (1500, 220)
        sky = A.sky((126, 166, 200), (232, 218, 192), (246, 228, 194), self.horizon, sun=self.sun, sun_col=(255, 244, 214))
        for i, (cx, cy, s) in enumerate(((420, 140, 0.9), (1100, 100, 1.0))):
            sky.alpha_composite(A.puff_cloud(cx, cy, s, i + 7, col=(250, 246, 236), shade_col=(224, 220, 212), ink=2.6))
        far = Layer()
        far.blob([(-40, self.horizon), (200, 470), (520, 430), (760, 480), (1000, 380), (1300, 420), (1600, 360), (1960, 440), (1960, self.horizon)],
                 (110, 132, 112), 3, n=6)
        # Udayagiri fort on the hill: granite walls along the ridge
        for x in range(1180, 1680, 70):
            y = 400 - (x - 1180) * 0.04
            far.rect((x, y - 28, x + 56, y + 6), (168, 160, 150), 2.4)
            far.rect((x + 6, y - 40, x + 22, y - 28), (168, 160, 150), 2)
        self.static = sky
        self.static.alpha_composite(A.haze(far.out(), (232, 218, 192), 0.42))
        g = Layer()
        g.poly([(-40, self.horizon), (1960, self.horizon), (1960, H + 20), (-40, H + 20)], (150, 152, 88), 3)
        g.poly([(860, self.horizon), (980, self.horizon), (1500, H + 20), (300, H + 20)], MALABAR["laterite"], 3)   # red earth road
        g.shade_poly([(980, self.horizon), (1500, H + 20), (1200, H + 20), (930, self.horizon)], A.shade(MALABAR["laterite"], 0.85), 255)
        rng = random.Random(3)
        for i in range(16):                                                                     # rice paddies on the left
            x, y = rng.uniform(0, 700), rng.uniform(self.horizon + 20, 760)
            g.ellipse((x - 70, y - 10, x + 70, y + 10), (120, 168, 120), 2)
        A.ground_texture(g, (0, self.horizon + 10, W, H), (150, 152, 88), n=200, seed=8, a=90)
        self.ground_im = g.out()
        self.palms = [(x, self.horizon + 30 + (abs(x - 920) / 960) * 260, 160 + (abs(x - 920) / 960) * 260, (0.12 if x < 920 else -0.12), i)
                      for i, x in enumerate((60, 260, 480, 680, 1240, 1440, 1660, 1880))]
        self.floor_y = 900

    def _anim_road_inland(self, t, frame):
        frame.alpha_composite(self.ground_im)
        L = Layer()
        for px, py, h, lean, sd in sorted(self.palms, key=lambda q: q[1]):
            A.palm(L, px, py, h, t, lean=lean, seed=sd, leaf=MALABAR["palm"], ink=2.8)
        frame.alpha_composite(L.out())

    def front(self, t, frame):
        """Foreground layer drawn after the actors (palms in front, haze)."""
        if self.name == "fort_wall":
            frame.alpha_composite(self.wall_im)
        if self.name == "colachel_camp":
            fx = Layer()
            for px, py, h, lean, sd in self.palms_front:
                A.palm(fx, px, py, h, t, lean=lean, seed=sd, leaf=MALABAR["palm"], ink=3.4)
            frame.alpha_composite(fx.out())

    def frame(self, t, actors_fn=None):
        f = self.static.copy()
        getattr(self, "_anim_" + self.name)(t, f)
        if actors_fn:
            actors_fn(f, t)
        self.front(t, f)
        if getattr(self, "sun", None):
            f = A.grade(f, sun=self.sun)
        return f
