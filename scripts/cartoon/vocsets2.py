"""More VOC pilot sets in the approved V5 style (golden light, texture, outlined 2D). Same contract as vocsets.Set:
build once, then frame(t, actors_fn) -> RGBA; front(t, frame) for foreground layers.

  amsterdam      Amsterdam quay, 1600s: brick gabled houses, a church tower, ships, grey-blue sky
  interior       a Dutch room: panelled walls, tall leaded window, map on the wall, table with green cloth (boardroom, office)
  kerala_court   a Kerala wooden palace hall: carved pillars, sloping tiled eaves, laterite floor, brass lamps
  batavia        Batavia's canal: whitewashed Dutch houses with red roofs, the castle, palms; batavia_dusk for 1740
  ocean          open sea with long swells; ocean_storm: dark sky, rain, big waves
  banda_grove    nutmeg trees under tall kenari shade trees
  weavers        Coromandel coast: palm-thatched sheds, looms, dyed cloth drying, the sea beyond
  dejima         Nagasaki bay: the fan-shaped island, its bridge, Japanese warehouses, hills
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

import vocart as A
from vocart import INK, Layer, W, H, S, hexc, mix, shade, light


def _tex(seed, scale=50):
    return A.noise_tex((W, H), scale, seed)


def gabled_house(L: Layer, x, y, w, h, col, seed=0, roof=(70, 60, 60)):
    rng = random.Random(seed)
    L.rect((x, y - h, x + w, y), col, 2.6)
    L.shade_poly([(x + w * 0.7, y - h), (x + w, y - h), (x + w, y), (x + w * 0.7, y)], shade(col, 0.82), 255)
    kind = seed % 3                                                   # step gable, spout gable or neck gable
    if kind == 0:
        pts = [(x, y - h)]
        for i in range(4):
            pts += [(x + i * w / 8, y - h - (i + 1) * h * 0.12), (x + (i + 1) * w / 8, y - h - (i + 1) * h * 0.12)]
        pts += [(x + w - (i + 1) * w / 8, y - h - (4 - i) * h * 0.12) for i in range(4)]
        pts = [(x, y - h), (x + w * 0.12, y - h), (x + w * 0.12, y - h * 1.15), (x + w * 0.25, y - h * 1.15), (x + w * 0.25, y - h * 1.3),
               (x + w * 0.38, y - h * 1.3), (x + w * 0.38, y - h * 1.45), (x + w * 0.62, y - h * 1.45), (x + w * 0.62, y - h * 1.3),
               (x + w * 0.75, y - h * 1.3), (x + w * 0.75, y - h * 1.15), (x + w * 0.88, y - h * 1.15), (x + w * 0.88, y - h), (x + w, y - h)]
    elif kind == 1:
        pts = [(x, y - h), (x + w * 0.3, y - h * 1.2), (x + w * 0.38, y - h * 1.5), (x + w * 0.62, y - h * 1.5), (x + w * 0.7, y - h * 1.2), (x + w, y - h)]
    else:
        pts = [(x, y - h), (x + w * 0.5, y - h * 1.55), (x + w, y - h)]
    L.poly(pts, col, 2.6)
    for r in range(3):                                                # windows with white frames
        for c in range(2):
            wx, wy = x + w * (0.22 + c * 0.38), y - h * (0.85 - r * 0.28)
            L.rect((wx, wy, wx + w * 0.2, wy + h * 0.17), (60, 74, 90), 1.6)
            L.line([(wx + w * 0.1, wy), (wx + w * 0.1, wy + h * 0.17)], (236, 232, 220), 1.2)
    L.rect((x + w * 0.4, y - h * 0.26, x + w * 0.6, y), (70, 46, 32), 1.6)


class Set2:
    def __init__(self, name):
        self.name = name
        self.sun = (1600, 220)
        self.floor_y = 900
        getattr(self, "_b_" + name.replace("_dusk", "").replace("_storm", ""))()

    # ------------------------------------------------------------------ Amsterdam quay
    def _b_amsterdam(self):
        self.sun = (300, 200)
        s = A.sky((86, 110, 140), (190, 196, 196), (224, 214, 196), 560, sun=self.sun, sun_col=(255, 236, 200))
        for i, (cx, cy, k) in enumerate(((400, 140, 1.5), (1100, 110, 1.3), (1600, 190, 1.0))):
            s.alpha_composite(A.soft_cloud(cx, cy, k, i + 21, top=(240, 238, 232), bottom=(150, 154, 162)))
        L = Layer()
        L.rect((1460, 200, 1520, 560), (140, 96, 70), 2.4)                 # church tower (Oude Kerk type)
        L.poly([(1450, 200), (1490, 90), (1530, 200)], (60, 70, 70), 2.4)
        rng = random.Random(2)
        x = -20
        i = 0
        while x < 1960:
            w = rng.uniform(80, 120)
            h = rng.uniform(150, 220)
            gabled_house(L, x, 600, w, h, mix(hexc("#8C4A32"), (120, 70, 50), rng.random() * 0.6), seed=i)
            x += w + 4
            i += 1
        s.alpha_composite(A.texturize(A.haze(L.out(), (200, 200, 196), 0.18), _tex(31, 30), 0.14))
        G = Layer()
        A.gradient_rect(G, (0, 600, W, 640), hexc("#5E7366"), shade(hexc("#5E7366"), 0.85))        # a strip of harbour behind
        G.poly([(-40, 640), (1960, 640), (1960, 780), (-40, 780)], hexc("#CDB891"), 2.4)          # the cobbled quay people stand on
        for i in range(60):
            x = (i * 97) % 1960
            y = 660 + (i * 37) % 110
            G.ellipse((x - 18, y - 6, x + 18, y + 6), shade(hexc("#CDB891"), 0.93), 0)
        G.poly([(-40, 780), (1960, 780), (1960, 800), (-40, 800)], (110, 96, 80), 2.0)            # quay edge
        A.gradient_rect(G, (0, 800, W, H), hexc("#5E7366"), shade(hexc("#5E7366"), 0.7))          # harbour water in front
        s.alpha_composite(G.out())
        self.static = s
        self.water = (800, H)
        self.floor_y = 740

    def _a_amsterdam(self, t, f):
        L = Layer()
        A.water_band(L, 806, H, t, hexc("#5E7366"), rows=6, speed=8, density=1.2)
        f.alpha_composite(L.out())

    # ------------------------------------------------------------------ Dutch interior
    def _b_interior(self):
        self.sun = (300, 300)
        L = Layer(fill=(110, 80, 52, 255))
        wall = (120, 88, 58)
        L.rect((-10, -10, W + 10, 760), wall, 0)
        for x in range(0, W, 160):                                        # panelling
            L.rect((x + 12, 420, x + 148, 740), shade(wall, 0.9), 2)
            L.rect((x + 12, 60, x + 148, 400), shade(wall, 0.94), 1.6)
        L.rect((180, 120, 520, 600), (190, 214, 220), 3)                  # tall leaded window with sunlight
        for i in range(1, 6):
            L.line([(180 + i * 57, 120), (180 + i * 57, 600)], (90, 90, 96), 2)
        for j in range(1, 8):
            L.line([(180, 120 + j * 60), (520, 120 + j * 60)], (90, 90, 96), 2)
        L.rect((900, 160, 1500, 520), (226, 210, 170), 3)                 # wall map (old-style, no modern borders)
        L.blob([(960, 260), (1100, 220), (1220, 300), (1180, 420), (1020, 440)], (196, 170, 120), 2)
        L.blob([(1260, 330), (1420, 300), (1460, 420), (1300, 470)], (196, 170, 120), 2)
        L.poly([(-10, 760), (W + 10, 760), (W + 10, H + 10), (-10, H + 10)], (92, 64, 42), 0)   # floor
        for x in range(-200, W + 200, 160):
            L.line([(x, 760), (x - 300, H)], (70, 48, 32), 2)
        s = A.texturize(L.out(), _tex(32, 30), 0.14)
        beam = Layer()
        beam.shade_poly([(180, 120), (520, 120), (1400, H), (700, H)], (255, 236, 190), 40)
        s.alpha_composite(beam.out().filter(ImageFilter.GaussianBlur(20)))
        self.static = s
        self.floor_y = 900

    def _a_interior(self, t, f):
        L = Layer()                                                       # dust motes in the sunbeam
        rng = random.Random(4)
        for i in range(30):
            x = 300 + rng.uniform(0, 900) + 20 * math.sin(t * 0.5 + i)
            y = (rng.uniform(150, 1000) - t * 8 * rng.uniform(0.3, 1)) % 950 + 120
            L.ellipse((x - 2, y - 2, x + 2, y + 2), (255, 240, 200), 0, a=120)
        f.alpha_composite(L.out())

    # ------------------------------------------------------------------ Kerala court
    def _b_kerala_court(self):
        self.sun = (1500, 200)
        L = Layer(fill=(70, 46, 32, 255))
        L.rect((-10, -10, W + 10, 780), (96, 62, 40), 0)                  # dark carved wooden walls
        for x in range(60, W, 240):
            L.rect((x, 200, x + 160, 700), (110, 72, 46), 2)
            for k in range(4):
                L.ellipse((x + 40, 240 + k * 110, x + 120, 300 + k * 110), (126, 84, 54), 1.4)
        L.poly([(-10, -10), (W + 10, -10), (W + 10, 150), (-10, 150)], (60, 40, 30), 0)        # sloping eaves inside
        for x in range(-40, W, 60):
            L.line([(x, 150), (x + 40, -10)], (44, 30, 22), 3)
        for x in (180, 620, 1300, 1740):                                  # carved pillars with brass lamps
            L.rect((x - 26, 140, x + 26, 800), (130, 86, 52), 2.6)
            L.shade_poly([(x + 6, 140), (x + 26, 140), (x + 26, 800), (x + 6, 800)], (100, 64, 40), 255)
            for k in range(3):
                L.rect((x - 34, 200 + k * 220, x + 34, 222 + k * 220), (154, 104, 62), 2)
            L.line([(x + 40, 420), (x + 40, 470)], (190, 150, 70), 3)
            L.ellipse((x + 26, 470, x + 54, 490), (212, 170, 64), 2)
        L.poly([(-10, 780), (W + 10, 780), (W + 10, H + 10), (-10, H + 10)], hexc("#A65A3A"), 0)  # laterite floor, polished
        L.rect((760, 600, 1160, 800), (130, 40, 36), 2.6)                 # dais with a red cloth
        L.rect((860, 470, 1060, 640), (150, 100, 56), 2.6)                # throne seat
        s = A.texturize(L.out(), _tex(33, 26), 0.16)
        self.static = s
        self.floor_y = 900

    def _a_kerala_court(self, t, f):
        L = Layer()
        for x in (180, 620, 1300, 1740):
            fl = 6 + 2 * math.sin(t * 9 + x)
            L.ellipse((x + 34, 456 - fl, x + 46, 470), (255, 200, 90), 0, a=230)
        f.alpha_composite(L.out())

    # ------------------------------------------------------------------ Batavia canal
    def _b_batavia(self):
        dusk = self.name.endswith("_dusk")
        self.sun = (1700, 300) if not dusk else (1800, 520)
        top, mid, low = ((70, 120, 170), hexc("#CFE0E3"), (240, 226, 196)) if not dusk else ((40, 46, 80), (150, 96, 90), (200, 120, 80))
        s = A.sky(top, mid, low, 560, sun=self.sun, sun_col=(255, 230, 190) if not dusk else (255, 150, 90))
        L = Layer()
        L.rect((1200, 330, 1700, 560), (232, 226, 210), 2.6)               # the castle walls behind
        for x in range(1200, 1700, 40):
            L.rect((x, 312, x + 22, 332), (232, 226, 210), 1.6)
        rng = random.Random(5)
        x = -20
        i = 0
        while x < 1960:
            w = rng.uniform(90, 120)
            gabled_house(L, x, 640, w, rng.uniform(120, 170), hexc("#F3EFE4") if not dusk else (210, 196, 180), seed=i + 3)
            x += w + 10
            i += 1
        s.alpha_composite(A.texturize(L.out(), _tex(34, 30), 0.12))
        G = Layer()
        G.poly([(-40, 640), (1960, 640), (1960, 680), (-40, 680)], (196, 180, 150), 2.4)          # far quay under the houses
        A.gradient_rect(G, (0, 680, W, 760), hexc("#5C6B4A"), shade(hexc("#5C6B4A"), 0.8))        # the canal
        G.poly([(-40, 760), (1960, 760), (1960, H + 20), (-40, H + 20)], (188, 170, 138), 2.4)    # the near street people stand on
        for i in range(80):
            x = (i * 131) % 1960
            y = 790 + (i * 53) % 270
            G.ellipse((x - 22, y - 7, x + 22, y + 7), shade((188, 170, 138), 0.93), 0)
        s.alpha_composite(G.out())
        if dusk:
            s = Image.blend(s.convert("RGB"), Image.new("RGB", s.size, (60, 40, 50)), 0.25).convert("RGBA")
        self.static = s
        self.floor_y = 900

    def _a_batavia(self, t, f):
        L = Layer()
        A.water_band(L, 686, 756, t, hexc("#5C6B4A"), rows=3, speed=6, density=1.2)
        for x in (60, 1880):
            A.palm(L, x, 800, 380, t, lean=0.1 if x < 900 else -0.1, seed=x, leaf=(62, 110, 52))
        f.alpha_composite(L.out())

    # ------------------------------------------------------------------ open ocean
    def _b_ocean(self):
        storm = self.name.endswith("_storm")
        self.sun = (1500, 200)
        if storm:
            s = A.sky((40, 46, 58), (90, 96, 106), (120, 124, 130), 560)
            for i, (cx, cy, k) in enumerate(((300, 160, 2.2), (900, 120, 2.6), (1500, 180, 2.4))):
                s.alpha_composite(A.soft_cloud(cx, cy, k, i + 41, top=(110, 112, 120), bottom=(50, 54, 62), rim=(150, 150, 160)))
        else:
            s = A.sky(hexc("#1C2E4A"), (150, 170, 190), (226, 220, 200), 560, sun=self.sun)
            for i, (cx, cy, k) in enumerate(((400, 150, 1.4), (1300, 110, 1.1))):
                s.alpha_composite(A.soft_cloud(cx, cy, k, i + 51))
        self.static = s
        self.storm = storm

    def _a_ocean(self, t, f):
        L = Layer()
        base = (40, 60, 80) if self.storm else (40, 74, 110)
        A.gradient_rect(L, (0, 560, W, H), base, shade(base, 0.6))
        A.water_band(L, 566, H, t * (1.6 if self.storm else 1.0), base, rows=11, speed=22 if self.storm else 12, density=1.0)
        f.alpha_composite(L.out())
        if self.storm:
            R = Layer()
            rng = random.Random(int(t * 24) % 5)
            for i in range(160):
                x, y = rng.uniform(0, W), rng.uniform(0, H)
                R.line([(x, y), (x - 18, y + 46)], (200, 210, 220), 1.6, a=120)
            f.alpha_composite(R.out())
            if int(t * 24) % 70 in (0, 1):                                 # lightning
                f.alpha_composite(Image.new("RGBA", (W, H), (230, 236, 255, 90)))

    # ------------------------------------------------------------------ Banda nutmeg grove
    def _b_banda_grove(self):
        self.sun = (1500, 160)
        s = A.sky((70, 120, 160), (200, 214, 196), (226, 226, 200), 520, sun=self.sun)
        L = Layer()
        rng = random.Random(6)
        for i in range(9):                                                # tall kenari shade trees
            x = 60 + i * 230 + rng.uniform(-40, 40)
            L.rect((x - 16, 120, x + 16, 760), (110, 90, 70), 2.4)
            L.blob([(x - 220, 220), (x - 120, 60), (x + 60, 30), (x + 220, 120), (x + 200, 260), (x - 60, 300)], hexc("#234D2C"), 2.4, n=6)
        s.alpha_composite(A.texturize(L.out(), _tex(35, 30), 0.14))
        G = Layer()
        G.poly([(-40, 700), (1960, 700), (1960, H + 20), (-40, H + 20)], (96, 110, 60), 0)
        A.ground_texture(G, (0, 710, W, H), (96, 110, 60), n=260, seed=7, a=120)
        s.alpha_composite(A.texturize(G.out(), _tex(36, 40), 0.18))
        self.static = s
        self.trees = [(120 + i * 300 + rng.uniform(-40, 40), 760 + rng.uniform(-10, 20)) for i in range(7)]
        self.floor_y = 900

    def _a_banda_grove(self, t, f):
        L = Layer()
        for x, y in self.trees:                                           # nutmeg trees with yellow fruit
            L.rect((x - 8, y - 160, x + 8, y), (100, 80, 60), 2)
            sway = 4 * math.sin(t * 1.1 + x)
            L.blob([(x - 110 + sway, y - 120), (x - 60, y - 260), (x + 60, y - 270), (x + 120 + sway, y - 130), (x, y - 90)],
                   hexc("#2F6B3A"), 2.2, n=5)
            for k in range(6):
                fx, fy = x - 70 + k * 28 + sway, y - 140 - (k % 2) * 50
                L.ellipse((fx - 7, fy - 7, fx + 7, fy + 7), hexc("#E2C25A"), 1.4)
        f.alpha_composite(L.out())

    # ------------------------------------------------------------------ Coromandel weavers
    def _b_weavers(self):
        self.sun = (1600, 200)
        s = A.sky((80, 130, 176), (226, 214, 186), (240, 226, 196), 560, sun=self.sun)
        G = Layer()
        A.gradient_rect(G, (0, 560, W, 620), (80, 130, 150), (70, 116, 140))
        G.poly([(-40, 620), (1960, 610), (1960, H + 20), (-40, H + 20)], hexc("#A68F6A"), 0)
        A.ground_texture(G, (0, 630, W, H), hexc("#A68F6A"), n=220, seed=8, a=110)
        for x in (200, 900):                                              # palm-thatched sheds
            G.rect((x, 520, x + 420, 700), (190, 150, 100), 2.6)
            G.poly([(x - 30, 530), (x + 210, 420), (x + 450, 530)], (150, 120, 70), 2.6)
            G.rect((x + 20, 560, x + 400, 700), (80, 56, 40), 0)
        s.alpha_composite(A.texturize(G.out(), _tex(37, 40), 0.16))
        self.static = s
        self.floor_y = 900

    def _a_weavers(self, t, f):
        L = Layer()
        for k, col in enumerate((hexc("#2E3F7A"), hexc("#9E2F2A"), hexc("#F2EFE6"), (212, 170, 64))):   # dyed cloth on lines
            x = 1300 + k * 140
            L.line([(1280, 520), (1900, 520)], (120, 100, 80), 2)
            wav = [(x + i * 10, 522 + 120 * (i / 10) + 6 * math.sin(t * 2 + i * 0.6 + k)) for i in range(11)]
            L.poly([(x, 522), (x + 100, 522)] + [(px + 100, py) for px, py in wav[::-1]][:1] + [(x, 642 + 6 * math.sin(t * 2 + k))], col, 1.8)
        for x in (300, 520, 1000, 1220):                                  # looms with flying shuttles
            L.rect((x - 60, 600, x + 60, 690), (120, 86, 52), 2.2)
            for i in range(9):
                L.line([(x - 50 + i * 12, 604), (x - 50 + i * 12, 686)], (230, 226, 210), 1)
            sx = x - 50 + 100 * (0.5 + 0.5 * math.sin(t * 4 + x))
            L.ellipse((sx - 8, 640, sx + 8, 652), (90, 60, 40), 1.6)
        f.alpha_composite(L.out())

    # ------------------------------------------------------------------ Dejima
    def _b_dejima(self):
        self.sun = (1500, 200)
        s = A.sky((80, 120, 170), (200, 210, 214), (226, 222, 210), 520, sun=self.sun)
        L = Layer()
        L.blob([(-40, 520), (200, 380), (520, 420), (800, 340), (1100, 400), (1400, 330), (1700, 380), (1960, 340), (1960, 560), (-40, 560)],
               (90, 120, 92), 2.6, n=6)
        s.alpha_composite(A.haze(L.out(), (200, 210, 214), 0.35))
        G = Layer()
        A.gradient_rect(G, (0, 540, W, H), hexc("#3E6E8E"), shade(hexc("#3E6E8E"), 0.7))
        G.blob([(560, 700), (760, 600), (1160, 600), (1360, 700), (1300, 780), (620, 780)], (196, 180, 150), 2.6, n=5)   # the fan island
        for i, x in enumerate(range(640, 1300, 90)):
            G.rect((x, 620, x + 70, 680), hexc("#EDE8DC"), 2)
            G.poly([(x - 8, 622), (x + 35, 596), (x + 78, 622)], hexc("#5D6063"), 2)
        G.poly([(940, 600), (960, 440), (980, 600)], hexc("#3A2C22"), 0)
        G.line([(900, 780), (860, 1080)], (110, 80, 54), 18)                # the bridge to the city
        G.line([(900, 780), (860, 1080)], (150, 110, 70), 10)
        s.alpha_composite(A.texturize(G.out(), _tex(38, 40), 0.14))
        self.static = s
        self.floor_y = 980

    def _a_dejima(self, t, f):
        L = Layer()
        A.water_band(L, 560, H, t, hexc("#3E6E8E"), rows=7, speed=8, density=1.3)
        f.alpha_composite(L.out())

    def frame(self, t, actors_fn=None):
        f = self.static.copy()
        getattr(self, "_a_" + self.name.replace("_dusk", "").replace("_storm", ""))(t, f)
        if actors_fn:
            actors_fn(f, t)
        return f
