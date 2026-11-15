"""VOC pilot: the 2-minute animated demo (Stage 6), assembled from code-drawn sets, cast, ships, maps and effects.

  python scripts/cartoon/vocfilm.py still <shot_id> <local t>           one frame for checking
  python scripts/cartoon/vocfilm.py render <i>/<n> <outdir>             render part i of n (equal frame ranges) -> outdir/part_XX.mp4
  python scripts/cartoon/vocfilm.py mix <parts dir> <out.mp4> [music]   join parts, add voices, music, effects, burned subtitles

Voice files (George + hosts), lip-sync and word timings live in TE_VOICE (default D:/Temp/cartoon/voc_demo/voice); the
subtitle text comes from TE_VOICE/lines.json (projects/tiny-empires/voc_demo/lines.json 'subtitle'), never from this file.
Timeline follows the signed-off storyboard (Stage 5 rev 3) shots marked DEMO, cut on the recorded words.
"""
from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402
import vocdemo as D  # noqa: E402  (clips, stakes, muzzle_point, combat setup)
import vocart as A  # noqa: E402
import vocfx as FX  # noqa: E402
import vocsets as VS  # noqa: E402
import vocship as V  # noqa: E402
import flatmap as F  # noqa: E402
from vocart import INK, Layer  # noqa: E402

VOICE = Path(os.environ.get("TE_VOICE", "D:/Temp/cartoon/voc_demo/voice"))
FPS = 24
W, H = 1920, 1080
P = D.P


def lips(line_id, offset):
    f = VOICE / f"{line_id}_lips.json"
    return M.load_rhubarb(str(f), offset) if f.exists() else []


_SETS = {}


def set_(name):
    if name not in _SETS:
        _SETS[name] = VS.Set(name)
    M.CUR_PLATE = name
    return _SETS[name]


def label(fr, text, x=960, y=70, a=1.0, size=44):
    """Short place/date label at the top of the frame (style bible: the only text besides subtitles)."""
    d = ImageDraw.Draw(fr, "RGBA")
    fo = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf" if os.name == "nt" else "DejaVuSerif-Bold.ttf", size)
    w = d.textlength(text, font=fo) + 56
    d.rounded_rectangle([x - w / 2, y - 34, x + w / 2, y + 34], radius=16, fill=(43, 33, 24, int(200 * a)))
    d.text((x, y), text, font=fo, fill=(250, 238, 210, int(255 * a)), anchor="mm")


def fade(t, t0, t1, k=0.3):
    return max(0.0, min(1.0, (t - t0) / k, (t1 - t) / k))


# ================================================================================================ shots
class Shot:
    set_name = ""
    perf: list = []

    def __init__(self):
        self.perf = []
        self.setup()

    def setup(self):
        pass

    def under(self, f, t):                # drawn before the characters
        pass

    def over(self, f, t):                 # drawn after the characters
        pass

    def frame(self, t):
        s = set_(self.set_name)

        def actors(f, tt):
            self.under(f, tt)
            D.paint_all(f, tt, self.perf)
            self.over(f, tt)
        return s.frame(t, actors).convert("RGB")


# ---- Scene 1: hook ------------------------------------------------------------------------------------------
class S01Harbour(Shot):                    # 1.1 the ship arrives
    set_name = "banda_harbour"

    def over(self, f, t):
        pass

    def frame(self, t):
        s = set_(self.set_name)
        x = 1460 - 60 * t
        return s.frame(t + 3, lambda f, tt: V.place(f, tt, x, 736, L=780, facing=-1)).convert("RGB")


class S02Ports(Shot):                      # 1.2 gun ports open, close on the hull
    set_name = "banda_harbour"

    def frame(self, t):
        s = set_(self.set_name)
        return s.frame(t + 9, lambda f, tt: V.place(f, tt, 1060, 1010, L=2100, ports=min(1, t / 0.8), facing=-1, wake=False)).convert("RGB")


class S03Fort(Shot):                       # 1.3 soldiers on the wall
    set_name = "fort_wall"

    def setup(self):
        g = 760
        self.perf = [P("voc_1620:soldier", 160, 880, 2.5, walks=[(0.0, 760)]),
                     P("voc_1620:soldier", -200, 890, 2.5, walks=[(0.0, 420)]),
                     P("voc_1620:soldier", 1480, 870, 2.4, flip=True)]

    def over(self, f, t):
        L = Layer()                                                   # glowing match cord on the standing sentry
        x, g_y = 1480 - 60, 640
        L.ellipse((x - 6, g_y - 6, x + 6, g_y + 6), (255, 140, 60), 0, a=int(160 + 90 * math.sin(t * 9)))
        f.alpha_composite(L.out())


class S04Ledger(Shot):                     # 1.4 "It was a business." ledger slam
    set_name = "banda_quay"

    def setup(self):
        self.perf = [P("voc_1620:merchant", 820, 1120, 5.2, acts=[(1.45, "stamp", None)], props={"prop_l": "ledger"},
                       faces=[(0.0, {"mouth": "smirk"})])]

    def frame(self, t):
        s = set_(self.set_name)
        base = s.frame(t)
        base = base.filter(ImageFilter.GaussianBlur(6)).convert("RGBA")                   # shallow focus: the quay behind
        D.paint_all(base, t, self.perf)
        L = Layer()
        L.poly([(-40, 820), (1960, 800), (1960, H + 20), (-40, H + 20)], (120, 80, 50), 4)  # the desk top
        L.shade_poly([(-40, 900), (1960, 880), (1960, H + 20), (-40, H + 20)], A.shade((120, 80, 50), 0.82), 255)
        slam = 1.7
        k = 0.0 if t < slam else 1.0
        cx, cy = 1180, 860
        if k == 0:                                                    # open ledger with columns
            for side in (-1, 1):
                L.poly([(cx, cy), (cx + side * 240, cy - 20), (cx + side * 250, cy + 70), (cx, cy + 86)], (246, 238, 214), 3)
                for i in range(7):
                    y = cy + 4 + i * 10
                    L.line([(cx + side * 30, y), (cx + side * 220, y - 14)], (150, 130, 110), 1.4)
        else:
            L.poly([(cx - 250, cy + 10), (cx + 250, cy - 6), (cx + 254, cy + 70), (cx - 246, cy + 86)], (60, 40, 30), 3.5)
            L.line([(cx - 240, cy + 40), (cx + 244, cy + 26)], (200, 160, 70), 3)
            if t < slam + 0.5:
                FX.dust(L, cx - 200, cy + 60, t, slam, 1.6, (230, 220, 200))
                FX.dust(L, cx + 220, cy + 50, t, slam, 1.6, (230, 220, 200))
        base.alpha_composite(L.out())
        return A.grade(base, sun=(380, 560)).convert("RGB")


class S05Quay(Shot):                       # 1.5 the busy quay
    set_name = "banda_quay"

    def setup(self):
        self.perf = [P("voc_1620:banda_man", 1900, 905, 1.55, flip=True, walks=[(0.0, 700)], props={"prop_l": "bale"}),
                     P("voc_1620:banda_man2", 2150, 925, 1.6, flip=True, walks=[(0.6, 900)], props={"prop_l": "bale"}),
                     P("voc_1620:banda_woman", 520, 880, 1.45, acts=[(1.0, "point", None), (4.0, "shrug", None)]),
                     P("voc_1620:sailor", 1260, 900, 1.55, acts=[(0.2, "haul", None), (1.2, "haul", None), (2.2, "haul", None), (3.2, "haul", None)]),
                     P("voc_1620:sailor2", 1400, 910, 1.6, acts=[(0.5, "haul", None), (1.5, "haul", None), (2.5, "haul", None), (3.5, "haul", None)]),
                     P("voc_1620:merchant", 360, 860, 1.4, acts=[(2.0, "nod", None)], props={"prop_l": "ledger"}),
                     P("voc_1620:soldier", 1000, 860, 1.35, flip=True)]


class S06Penny(Shot):                      # 1.9 Penny on the quay
    set_name = "banda_quay"

    def setup(self):
        self.perf = [P("penny", 980, 930, 2.3, lips=lips("D03", 0.2), acts=[(0.05, "jump", 0.0), (2.1, "rub", None)],
                       faces=[(0.0, {"mouth": "grin"})], props={"prop_r": "cane"})]

    def under(self, f, t):
        L = Layer()                                                   # the cannon she pats
        x, y = 1380, 930
        L.rect((x - 150, y - 70, x + 120, y - 20), (60, 60, 66), 3)
        L.ellipse((x - 120, y - 70, x - 20, y + 30), (110, 74, 44), 3)
        L.ellipse((x + 20, y - 70, x + 120, y + 30), (110, 74, 44), 3)
        f.alpha_composite(L.out())


# ---- Scene 4: route map ---------------------------------------------------------------------------------------
BB = (-25, -50, 125, 62)
R1 = [(4.5, 52.6), (2.5, 51.0), (-6, 48.5), (-13, 42), (-19, 30), (-26, 14), (-26, 0), (-16, -18), (2, -31), (18.4, -34.8)]
R2 = [(18.4, -34.8), (30, -39.5), (60, -40.5), (90, -39), (104, -28), (105.6, -6.6)]


class MapShot(Shot):
    zoom = (0, 0, W, H)

    def mapframe(self, t):
        img, pj = F.base(BB)
        f = img.copy()
        f.alpha_composite(F.sea_waves(BB, t))
        return f, pj

    def crop(self, f):
        x0, y0, x1, y1 = self.zoom
        return f.crop((int(x0), int(y0), int(x1), int(y1))).resize((W, H), Image.LANCZOS)


class S07Atlas(MapShot):                   # 4.2 Atlas walks onto the map; the route draws down Africa
    def setup(self):
        self.perf = [P("atlas", -200, 1000, 2.2, walks=[(0.0, 300)], lips=lips("D04", 0.3), acts=[(1.6, "point", None)])]

    def frame(self, t):
        f, pj = self.mapframe(t)
        d = ImageDraw.Draw(f)
        h, a = F.route(d, pj, R1, min(1.0, t / 5.6))
        F.ship_icon(d, h[0], h[1], a, t, 1.3)
        for n, ll, dy in (("Amsterdam", (4.9, 52.4), -34), ("Cape of Good Hope", (18.4, -34.3), 40)):
            x, y = pj(*ll)
            if n == "Amsterdam" or t > 5.0:
                F.dot(d, x, y, t, 0 if n == "Amsterdam" else 5.0)
                F.label(d, n, x, y + dy, 34)
        M.CUR_PLATE = ""
        D.paint_all(f, t, self.perf)
        return f.convert("RGB")


class S08Brouwer(MapShot):                 # 4.5 the shortcut through the Roaring Forties
    part = 0

    def frame(self, t):
        T = t + self.part
        f, pj = self.mapframe(T)
        d = ImageDraw.Draw(f)
        F.route(d, pj, R1, 1.0)
        prog = min(1.0, max(0.0, (T - 0.8) / 9.4))
        h, a = F.route(d, pj, R2, prog, color=(230, 150, 40))
        F.ship_icon(d, h[0], h[1], a, T, 1.4)
        if T > 1.6:
            F.wind_arrow(d, *pj(30, -45), *pj(98, -45), T)
        for n, ll, dy in (("Amsterdam", (4.9, 52.4), -34), ("Cape of Good Hope", (18.4, -34.3), 40), ("Java", (110.0, -7.4), 40)):
            x, y = pj(*ll)
            F.dot(d, x, y, T, 0 if n != "Java" else 9.0)
            if n != "Java" or T > 9.0:
                F.label(d, n, x, y + dy, 34)
        if T > 2.1:
            F.label(d, "1611: Brouwer", *pj(60, -33), 42, a=min(1, (T - 2.1) / 0.4))
        if T > 11.4:
            F.label(d, "standard route by about 1616-17", *pj(66, -27), 34, a=min(1, (T - 11.4) / 0.4))
        if self.part:                                                  # second half: push in on the Indian Ocean
            k = min(1.0, t / 1.2)
            self.zoom = (560 * k, 380 * k, W - 120 * k, H - 30 * k)
            f = self.crop(f)
        return f.convert("RGB")


class S08bBrouwer(S08Brouwer):
    part = 7.0


# ---- Scene 5 bridge: Zed ---------------------------------------------------------------------------------------
class S09Zed(Shot):
    set_name = "banda_quay"

    def setup(self):
        self.perf = [P("zed", 820, 930, 2.3, lips=lips("D06", 0.3), acts=[(1.3, "double_take", None)], props={"prop_l": "book"})]

    def under(self, f, t):
        L = Layer()                                                   # a cannon rolls up beside him
        x = 1700 - 520 * min(1.0, t / 1.4)
        y = 930
        rot = -(1700 - x) / 50
        L.rect((x - 170, y - 86, x + 120, y - 30), (60, 60, 66), 3)
        L.ellipse((x - 150, y - 80, x - 150 + 110, y + 30), (110, 74, 44), 3)
        L.ellipse((x + 10, y - 80, x + 120, y + 30), (110, 74, 44), 3)
        for cx in (x - 95, x + 65):
            L.line([(cx + 40 * math.cos(rot), y - 25 + 40 * math.sin(rot)), (cx - 40 * math.cos(rot), y - 25 - 40 * math.sin(rot))], INK, 4)
        f.alpha_composite(L.out())


# ---- Scene 6B: Colachel ----------------------------------------------------------------------------------------
def offshore(f, t, era=1741):
    V.place(f, t, 260, 600, L=240, facing=1, sea=0.6, water=(84, 142, 166), era=era, wake=False)
    V.place(f, t + 2, 640, 590, L=200, facing=1, sea=0.6, water=(84, 142, 166), era=era, wake=False)


class S10Landing(Shot):                    # 6.8 boats through the surf, soldiers wade ashore
    set_name = "colachel_camp"

    def setup(self):
        self.perf = [P("travancore_1741:voc_soldier", 520, 760, 1.25, walks=[(2.4, 980)], hide=(0, 2.3)),
                     P("travancore_1741:voc_soldier2", 600, 780, 1.3, walks=[(3.0, 1100)], hide=(0, 2.9)),
                     P("travancore_1741:delannoy", 440, 770, 1.3, walks=[(3.6, 860)], hide=(0, 3.5)),
                     P("travancore_1741:voc_soldier", 380, 800, 1.35, walks=[(4.4, 820)], hide=(0, 4.3))]

    def under(self, f, t):
        offshore(f, t)
        for i, (x0, y0, t0) in enumerate(((120, 640, 0.0), (40, 700, 0.6))):
            k = min(1.0, (t - t0) / 2.6)
            x = x0 + 380 * max(0, k)
            y = y0 + 40 * max(0, k)
            img, (ax, ay) = V.longboat(t * 1.3 + i, L=230, rowers=4)
            f.alpha_composite(img, (int(x - ax), int(y - ay + 3 * math.sin(t * 2 + i))))
        L = Layer()
        for t0, x in ((2.3, 520), (2.9, 600), (3.5, 440), (4.3, 380)):
            FX.splash(L, x, 770, t, t0, 1.2)
        f.alpha_composite(L.out())
        # fishermen pull a canoe up the beach, away from the landing
        Lb = Layer()
        cx = 1500 + 60 * min(1, t / 6)
        Lb.blob([(cx - 120, 880), (cx - 100, 900), (cx + 100, 900), (cx + 130, 878)], (120, 80, 50), 3, n=4)
        f.alpha_composite(Lb.out())

    def setup_more(self):
        pass


class S11Camp(Shot):                       # 6.9-6.10 building the stockade; Pike
    set_name = "colachel_camp"

    def setup(self):
        self.perf = [P("travancore_1741:voc_soldier", 300, 900, 1.45, acts=[(0.2, "stamp", None), (1.4, "stamp", None), (2.6, "stamp", None)]),
                     P("travancore_1741:voc_soldier2", 520, 880, 1.4, walks=[(0.0, 700)], props={"prop_l": "bale"}),
                     P("pike", 1240, 960, 2.2, flip=True, lips=lips("D08", 0.2), acts=[(3.4, "shrug", None)])]

    def under(self, f, t):
        L = Layer()
        n = int(6 + 18 * min(1.0, t / 5.0))                           # the wall grows stake by stake
        D.stakes(L, 40, 40 + n * 19, 820, 150, t, seed=2)
        for i in range(5):                                            # rice sacks and powder barrels stacked under the shed
            x = 820 + i * 50
            L.blob([(x - 24, 830), (x - 22, 790), (x + 22, 790), (x + 24, 830)], (214, 196, 150), 2.6, n=3)
        for x in (1120, 1180):
            L.rect((x - 26, 770, x + 26, 830), (120, 80, 48), 3)
        f.alpha_composite(L.out())
        L2 = Layer()
        for t0 in (0.55, 1.75, 2.95):
            FX.dust(L2, 380, 900, t, t0, 1.3)
        f.alpha_composite(L2.out())


class S12Skirmish(Shot):                   # 6.11 Travancore closes in from the land side
    def __init__(self):
        self.b = D.BibleBattle()
        # Ramayyan signals on his name in the narration (word 'Ramayyan' at 4.32 s + line offset 0.2)
        self.b.nair[3].acts = [(4.4, "signal", None)]

    def frame(self, t):
        return self.b.frame(t)


class S13Blast(Shot):                      # 6.12 fire reaches the powder; the rice burns
    set_name = "colachel_camp"
    T_BLAST = 1.6

    def setup(self):
        self.perf = [P("travancore_1741:voc_soldier", 400, 960, 1.6, acts=[(self.T_BLAST + 0.1, "flinch", None), (2.6, "haul", None), (3.6, "haul", None)]),
                     P("travancore_1741:voc_soldier2", 1300, 980, 1.6, flip=True, acts=[(self.T_BLAST + 0.15, "cower", None)]),
                     P("travancore_1741:delannoy", 1600, 940, 1.5, flip=True, acts=[(self.T_BLAST + 0.2, "flinch", None), (2.8, "point", None)])]

    def under(self, f, t):
        L = Layer()
        D.stakes(L, -20, 1960, 760, 150, t, seed=2)
        L.poly([(700, 800), (700, 700), (1100, 690), (1110, 800)], (196, 170, 120), 3)              # store shed
        L.poly([(680, 704), (900, 610), (1130, 696)], (150, 140, 80), 3)
        for i in range(6):
            x = 740 + i * 58
            burnt = t > self.T_BLAST + 0.6 + i * 0.25
            L.blob([(x - 26, 800), (x - 24, 756), (x + 24, 756), (x + 26, 800)], (90, 70, 56) if burnt else (214, 196, 150), 2.6, n=3)
        f.alpha_composite(L.out())
        fx = Layer()
        FX.explosion(fx, 1040, 780, t, self.T_BLAST, 1.0)
        if t > self.T_BLAST + 0.3:
            spread = min(1.0, (t - self.T_BLAST - 0.3) / 2.0)
            FX.fire(fx, 900, 800, 200 + 260 * spread, 120, t, seed=5)
            VS.smoke_plume(fx, 900, 700, t, n=8, col=(96, 90, 88), rise=30, drift=16, size=36, seed=6, a=230)
        f.alpha_composite(fx.out())


class S14PikeAsh(Shot):                    # 6.13 "You can't fight with no food."
    set_name = "colachel_camp"

    def setup(self):
        self.perf = [P("pike", 900, 960, 2.4, lips=lips("D11", 0.2), acts=[(1.9, "hold_up", None)], props={"prop_l": "bale"},
                       faces=[(0.0, {"brows": 0.6})])]

    def under(self, f, t):
        L = Layer()
        D.stakes(L, -20, 1960, 760, 150, t, seed=4)
        for i in range(7):
            x = 300 + i * 60 + (i % 2) * 14
            L.blob([(x - 26, 820), (x - 24, 786), (x + 24, 786), (x + 26, 820)], (84, 68, 56), 2.6, n=3)
        f.alpha_composite(L.out())
        fx = Layer()
        VS.smoke_plume(fx, 420, 780, t, n=6, col=(110, 104, 100), rise=24, drift=12, size=26, seed=3, a=200)
        FX.fire(fx, 660, 820, 70, 40, t, seed=8, embers=True)
        if t > 2.0:                                                   # ash pouring from the empty sack
            for i in range(10):
                ph = ((t - 2.0) * 1.6 + i / 10) % 1.0
                fx.ellipse((1010 + math.sin(i) * 10 - 3, 760 + ph * 180 - 3, 1010 + math.sin(i) * 10 + 3, 760 + ph * 180 + 3), (70, 66, 64), 0,
                           a=int(220 * (1 - ph)))
        f.alpha_composite(fx.out())


class S15Surrender(Shot):                  # 6.14 the food runs out; surrender (three beats)
    set_name = "colachel_camp"

    def setup(self):
        self.perf = [P("travancore_1741:voc_soldier", 600, 960, 1.6, acts=[(2.5, "sit", None)], faces=[(0.0, {"brows": 0.7})]),
                     P("travancore_1741:voc_soldier2", 900, 980, 1.6, acts=[(2.6, "sit", None)], faces=[(0.0, {"brows": 0.8})]),
                     P("travancore_1741:delannoy", 1300, 960, 1.55, flip=True, acts=[(3.4, "hold_up", None)], props={"prop_l": "white_flag"},
                       faces=[(0.0, {"brows": 0.6})])]

    def frame(self, t):
        if t < 1.2:                                                   # beat 1: a half-empty store
            return self._still_beat(t, 3)
        if t < 2.4:                                                   # beat 2: scraped-out barrels
            return self._barrels(t)
        f = super().frame(t)
        fr = f.convert("RGBA")
        if t > 3.6:
            L = Layer()                                               # a white cloth on a musket, rising and catching the breeze
            k = min(1.0, (t - 3.6) / 0.8)
            x, y = 1250, 640 - 120 * k
            L.line([(x, y + 260), (x, y)], (70, 50, 34), 6)
            pts_t = [(x + i * 14, y + 6 * math.sin(t * 6 + i)) for i in range(9)]
            pts_b = [(px, py + 70) for px, py in pts_t]
            L.poly(pts_t + pts_b[::-1], (250, 250, 246), 3)
            fr.alpha_composite(L.out())
            label(fr, "August 1741", a=min(1, (t - 3.6) / 0.4))
        return fr.convert("RGB")

    def _still_beat(self, t, n):
        s = set_(self.set_name)

        def actors(f, tt):
            L = Layer()
            D.stakes(L, -20, 1960, 760, 150, tt, seed=2)
            L.poly([(600, 900), (600, 700), (1300, 690), (1310, 900)], (196, 170, 120), 3)
            for i in range(n):
                x = 760 + i * 120
                L.blob([(x - 50, 900), (x - 46, 820), (x + 46, 820), (x + 50, 900)], (214, 196, 150), 3, n=3)
            f.alpha_composite(L.out())
            fx = Layer()
            VS.smoke_plume(fx, 1500, 700, tt, n=5, col=(130, 124, 120), rise=18, drift=10, size=22, seed=2, a=150)
            f.alpha_composite(fx.out())
        return s.frame(t, actors).convert("RGB")

    def _barrels(self, t):
        s = set_(self.set_name)

        def actors(f, tt):
            L = Layer()
            D.stakes(L, -20, 1960, 700, 150, tt, seed=3)
            for i, x in enumerate((700, 1000, 1300)):
                L.rect((x - 110, 700, x + 110, 1000), (120, 80, 48), 4)
                L.ellipse((x - 110, 660, x + 110, 740), (60, 42, 30), 4)
                for yy in (760, 900):
                    L.line([(x - 110, yy), (x + 110, yy)], (70, 60, 56), 6)
            sc = 1000 + 30 * math.sin(tt * 8)                         # a ladle scraping the bottom
            L.line([(sc, 700), (sc + 60, 560)], (150, 120, 80), 8)
            f.alpha_composite(L.out())
        return s.frame(t, actors).convert("RGB")


class S16March(Shot):                      # 6.15 prisoners marched inland; De Lannoy looks back
    set_name = "road_inland"

    def setup(self):
        g = 820
        self.perf = [P("travancore_1741:nair3", 700, g + 20, 1.5, walks=[(0.0, 1500)]),
                     P("travancore_1741:voc_soldier", 480, g, 1.45, walks=[(0.0, 1280)], props={"prop_l": "none"}),
                     P("travancore_1741:delannoy", 260, g + 10, 1.5, walks=[(0.0, 1060)], props={"prop_l": "none"},
                       turns=[(2.0, True), (3.1, False)], faces=[(2.0, {"brows": 0.5, "look": -0.8})]),
                     P("travancore_1741:voc_soldier2", 40, g, 1.45, walks=[(0.0, 840)], props={"prop_l": "none"}),
                     P("travancore_1741:nair2", -180, g + 30, 1.5, walks=[(0.0, 620)])]


class S17Drill(Shot):                      # 6.16 years later: Travancore's army drills
    set_name = "road_inland"

    def setup(self):
        rows = []
        keys = ["travancore_1741:nair2", "travancore_1741:nair3", "travancore_1741:nair2", "travancore_1741:nair",
                "travancore_1741:nair2", "travancore_1741:nair3"]
        for i, k in enumerate(keys):
            rows.append(P(k, 700 + i * 170, 860 + (i % 2) * 24, 1.35, flip=True,
                          acts=[(1.0 + 0.05 * i, "brace", None), (3.2 + 0.03 * i, "aim_fire", None)],
                          props={"prop_l": "matchlock_aim"} if "nair2" in k else {}))
        self.perf = rows + [P("travancore_1741:delannoy", 300, 900, 1.6, acts=[(0.6, "point", None), (3.0, "nod", None)],
                              faces=[(0.0, {"brows": -0.2})])]

    def over(self, f, t):
        L = Layer()
        for p in self.perf[:-1]:
            if "nair2" in p.key:
                mx, my = D.muzzle_point(p, 4.2)
                FX.muzzle(L, mx, my, t, 4.2, f=-1, wind=(-10, -8), size=0.9, seed=int(mx))
        f.alpha_composite(L.out())

    def frame(self, t):
        fr = super().frame(t).convert("RGBA")
        label(fr, "Years later: Travancore's army", a=fade(t, 0.2, 99))
        return fr.convert("RGB")


# ---- Quill ------------------------------------------------------------------------------------------------------
BB2 = (66, -2, 132, 34)


class S18Quill(Shot):
    part = 0

    def setup(self):
        self.perf = [P("quill", 330, 1010, 2.5, lips=lips("D14", 0.3 - self.part), acts=[(5.6 - self.part, "headshake", None)]
                       if not self.part else [(0.6, "point", None)])]

    def frame(self, t):
        T = t + self.part
        img, pj = F.base(BB2)
        f = img.copy()
        f.alpha_composite(F.sea_waves(BB2, T))
        d = ImageDraw.Draw(f)
        x, y = pj(77.27, 8.18)
        F.dot(d, x, y, T, 0.2)
        F.label(d, "Colachel 1741", x + 10, y - 44, 44)
        tx, ty = pj(120.2, 23.0)
        if T > 7.0:
            F.dot(d, tx, ty, T, 7.0, color=(60, 90, 160))
            F.label(d, "Taiwan: lost in 1662", tx - 120, ty + 50, 44)
        fr = f.convert("RGBA")
        M.CUR_PLATE = ""
        D.paint_all(fr, t, self.perf)
        if T < 10.0:
            txt, col = "FIRST?", (200, 46, 40)
        else:
            txt, col = "RARE", (46, 110, 60)
        dd = ImageDraw.Draw(fr)
        fo = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf" if os.name == "nt" else "DejaVuSerif-Bold.ttf", 64)
        bx, by = 1300, 200
        a = 1.0 if T < 5.9 or T > 10.0 else max(0.0, 1 - (T - 5.9) / 0.3)
        if T > 1.8:
            dd.rounded_rectangle([bx - 150, by - 54, bx + 150, by + 54], radius=18, fill=(250, 242, 222, int(255 * a)), outline=INK + (int(255 * a),), width=5)
            dd.text((bx, by), txt, font=fo, fill=col + (int(255 * a),), anchor="mm")
            if 6.0 < T < 10.0:                                            # crossed out
                dd.line([(bx - 140, by + 40), (bx + 140, by - 40)], fill=(200, 46, 40, 255), width=10)
        return fr.convert("RGB")


class S18bQuill(S18Quill):
    part = 9.9


class S19End(Shot):
    def frame(self, t):
        s = set_("banda_harbour")
        fr = s.frame(t + 20, lambda f, tt: V.place(f, tt, 980, 736, L=680, facing=-1)).convert("RGBA")
        a = fade(t, 0.2, 99, 0.5)
        dk = Image.new("RGBA", fr.size, (20, 16, 12, int(140 * a)))
        fr.alpha_composite(dk)
        d = ImageDraw.Draw(fr)
        fo = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf" if os.name == "nt" else "DejaVuSerif-Bold.ttf", 96)
        d.text((960, 500), "TINY EMPIRES", font=fo, fill=(250, 236, 200, int(255 * a)), anchor="mm", stroke_width=6, stroke_fill=INK + (int(255 * a),))
        return fr.convert("RGB")


# ================================================================================================ timeline
# (shot class, duration s, [(voice line, start within shot)])
TIMELINE = [
    (S01Harbour, 2.45, [("D01", 0.2)]),
    (S02Ports, 1.0, []),
    (S03Fort, 1.65, []),
    (S04Ledger, 2.7, []),
    (S05Quay, 7.4, [("D02", 0.2)]),
    (S06Penny, 4.5, [("D03", 0.2)]),
    (S07Atlas, 6.3, [("D04", 0.3)]),
    (S08Brouwer, 7.0, [("D05", 0.1)]),
    (S08bBrouwer, 8.4, []),
    (S09Zed, 3.9, [("D06", 0.3)]),
    (S10Landing, 8.3, [("D07", 0.2)]),
    (S11Camp, 7.2, [("D08", 0.2)]),
    (S12Skirmish, 8.2, [("D09", 0.2)]),
    (S13Blast, 5.4, [("D10", 0.2)]),
    (S14PikeAsh, 4.4, [("D11", 0.2)]),
    (S15Surrender, 5.2, [("D12", 2.4)]),
    (S16March, 4.0, [("D13", 0.3)]),
    (S17Drill, 6.7, []),
    (S18Quill, 10.2, [("D14", 0.3)]),
    (S18bQuill, 6.0, []),
    (S19End, 2.5, []),
]
SFX_EVENTS = []   # filled by build_sfx()


def starts():
    out, t = [], 0.0
    for cls, dur, _ in TIMELINE:
        out.append(t)
        t += dur
    return out, t


def frame_at(gt, cache={}):
    st, total = starts()
    i = max(k for k, s in enumerate(st) if s <= gt + 1e-9)
    cls, dur, _ = TIMELINE[i]
    if cls not in cache:
        cache[cls] = cls()
    fr = cache[cls].frame(gt - st[i])
    draw_subtitle(fr, gt)
    return fr


def render_part(i, n, outdir):
    import imageio_ffmpeg
    st, total = starts()
    nf = int(round(total * FPS))
    a, b = (i - 1) * nf // n, i * nf // n
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"part_{i:02d}.mp4"
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "medium", "-g", str(FPS), str(out)], stdin=subprocess.PIPE)
    for k in range(a, b):
        proc.stdin.write(frame_at(k / FPS).tobytes())
        if (k - a) % 24 == 0:
            print(f"part {i}/{n}: frame {k - a}/{b - a}", flush=True)
    proc.stdin.close()
    proc.wait()
    print(out)


# ================================================================================================ subtitles
def _font(size):
    for f in ("C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def subtitle_cues():
    """[(t0, t1, text)] in film time: each line's approved subtitle text, split into short chunks timed by the recorded words."""
    lines = {ln["id"]: ln for ln in json.loads((VOICE / "lines.json").read_text(encoding="utf-8"))["lines"]}
    words = json.loads((VOICE / "words.json").read_text(encoding="utf-8"))
    st, _ = starts()
    cues = []
    for (cls, dur, vl), s0 in zip(TIMELINE, st):
        for lid, off in vl:
            text = lines[lid]["subtitle"].replace("...", "").strip()
            tw = text.split()
            rec = words.get(lid, [])
            if not rec:
                continue
            end = rec[-1][2]
            chunks, cur = [], []
            for w in tw:
                if cur and len(" ".join(cur + [w])) > 44:
                    chunks.append(cur)
                    cur = []
                cur.append(w)
                if w[-1] in ".?!:" and len(" ".join(cur)) > 18:
                    chunks.append(cur)
                    cur = []
            if cur:
                chunks.append(cur)
            if len(chunks) > 1 and len(" ".join(chunks[-1])) < 14:          # never leave one short word on its own
                last = chunks.pop()
                chunks[-1] = chunks[-1] + last
            n = len(tw)
            k = 0
            for ch in chunks:
                i0, i1 = k, k + len(ch) - 1
                a = rec[min(len(rec) - 1, int(i0 / n * len(rec)))][1]
                b = rec[min(len(rec) - 1, int(i1 / n * len(rec)))][2] if i1 < n - 1 else end
                cues.append((s0 + off + a, s0 + off + b + 0.25, " ".join(ch)))
                k += len(ch)
    for i in range(len(cues) - 1):                                    # no overlaps
        if cues[i][1] > cues[i + 1][0]:
            cues[i] = (cues[i][0], cues[i + 1][0] - 0.02, cues[i][2])
    return cues


_CUES = None


def draw_subtitle(fr, gt):
    global _CUES
    if _CUES is None:
        _CUES = subtitle_cues()
    for a, b, text in _CUES:
        if a <= gt < b:
            d = ImageDraw.Draw(fr)
            fo = _font(50)
            d.text((960, 1010), text, font=fo, fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(24, 20, 16))
            return


# ================================================================================================ sound
SFX_DIR = Path(os.environ.get("TE_SFX", "D:/Temp/cartoon/sfx"))


def synth(kind, sr=44100, seed=0):
    import numpy as np
    rng = np.random.default_rng(seed)
    if kind == "musket":
        n = int(sr * 0.9)
        tt = np.arange(n) / sr
        noise = rng.standard_normal(n)
        crack = noise * np.exp(-tt * 38)
        boom = np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 9) * 0.8
        tail = np.convolve(noise, np.ones(40) / 40, "same") * np.exp(-tt * 4) * 0.5
        x = crack + boom + tail
    elif kind == "explosion":
        n = int(sr * 3.2)
        tt = np.arange(n) / sr
        noise = rng.standard_normal(n)
        low = np.convolve(noise, np.ones(120) / 120, "same") * 6
        x = (low * np.exp(-tt * 1.6) + noise * np.exp(-tt * 12) * 0.6 + np.sin(2 * np.pi * 45 * tt) * np.exp(-tt * 2.5))
    elif kind == "splash":
        n = int(sr * 0.8)
        tt = np.arange(n) / sr
        noise = rng.standard_normal(n)
        x = np.convolve(noise, np.ones(6) / 6, "same") * np.exp(-tt * 6) * (1 - np.exp(-tt * 60))
    elif kind == "surf":
        n = int(sr * 12)
        tt = np.arange(n) / sr
        noise = np.convolve(rng.standard_normal(n), np.ones(30) / 30, "same")
        x = noise * (0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 6.0)) ** 2) * 3
    else:
        raise ValueError(kind)
    x = x / (np.abs(x).max() + 1e-9) * 0.9
    return (x * 32767).astype("int16"), sr


def write_wav(path, data, sr):
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def sound_plan():
    """[(file, film time, gain dB, loop seconds or None)]: ambience beds per shot plus event sounds."""
    st, total = starts()
    S = {cls.__name__: s for (cls, _, _), s in zip(TIMELINE, st)}
    D_ = {cls.__name__: d for cls, d, _ in TIMELINE}
    ev = []

    def bed(name, shots, gain):
        a = S[shots[0]]
        b = S[shots[-1]] + D_[shots[-1]]
        ev.append((name, a, gain, b - a))

    bed("water_river_1.wav", ["S01Harbour", "S02Ports"], -16)
    bed("crowd_work_1.wav", ["S05Quay", "S06Penny"], -20)
    bed("water_river_1.wav", ["S05Quay", "S06Penny"], -22)
    bed("wind_steppe_1.wav", ["S08Brouwer", "S08bBrouwer"], -24)
    bed("crowd_work_1.wav", ["S09Zed"], -24)
    bed("@surf", ["S10Landing", "S11Camp"], -18)
    bed("@surf", ["S12Skirmish"], -24)
    bed("fire_crackle_1.wav", ["S13Blast", "S14PikeAsh"], -14)
    bed("wind_desert_1.wav", ["S15Surrender", "S16March", "S17Drill"], -26)
    for i in range(8):
        ev.append(("stamp_thud_1.wav", S["S02Ports"] + 0.05 + i * 0.09, -20, None))
    ev.append(("stamp_thud_1.wav", S["S04Ledger"] + 1.7, -6, None))
    ev.append(("coins_1.wav", S["S06Penny"] + 0.2, -14, None))
    ev.append(("whoosh_1.wav", S["S07Atlas"], -16, None))
    ev.append(("rope_creak_1.wav", S["S05Quay"] + 0.3, -18, None))
    for t0 in (2.3, 2.9, 3.5, 4.3):
        ev.append(("@splash", S["S10Landing"] + t0, -12, None))
    for t0 in (0.55, 1.75, 2.95):
        ev.append(("hammer_chisel_1.wav", S["S11Camp"] + t0, -16, None))
    for t0 in (1.25, 2.05, 2.85, 1.75, 2.95, 5.1, 6.0):
        ev.append(("@musket", S["S12Skirmish"] + t0, -8, None))
    ev.append(("@explosion", S["S13Blast"] + 1.6, -3, None))
    for k in range(3):
        ev.append(("@musket", S["S17Drill"] + 4.2 + k * 0.05, -9, None))
    ev.append(("paper_rustle_1.wav", S["S18Quill"] + 1.8, -16, None))
    ev.append(("stamp_thud_1.wav", S["S18Quill"] + 6.0, -12, None))
    ev.append(("whoosh_2.wav", S["S19End"], -14, None))
    return ev


def mix(parts_dir, out, music=None):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    parts = sorted(Path(parts_dir).glob("part_*.mp4"))
    work = Path(out).parent / "mixwork"
    work.mkdir(parents=True, exist_ok=True)
    lst = work / "parts.txt"
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
    video = work / "video.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)], check=True)
    st, total = starts()
    inputs, filt, labels = [], [], []
    k = 1                                                             # input 0 is the video
    for (cls, dur, vl), s0 in zip(TIMELINE, st):                       # voices
        for lid, off in vl:
            inputs += ["-i", str(VOICE / f"{lid}.mp3")]
            ms = int((s0 + off) * 1000)
            filt.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume=1.0[v{k}]")
            labels.append(f"[v{k}]")
            k += 1
    nv = k - 1
    synths = {}
    for name, t0, gain, loop in sound_plan():                         # effects and beds
        if name.startswith("@"):
            if name not in synths:
                data, sr = synth(name[1:], seed=len(synths))
                fp = work / f"{name[1:]}.wav"
                write_wav(fp, data, sr)
                synths[name] = fp
            src = synths[name]
        else:
            src = SFX_DIR / name
            if not src.exists():
                continue
        if loop:
            inputs += ["-stream_loop", "-1", "-i", str(src)]
        else:
            inputs += ["-i", str(src)]
        ms = int(t0 * 1000)
        trim = f"atrim=0:{loop:.2f},afade=t=in:d=0.4,afade=t=out:st={max(0, loop - 0.5):.2f}:d=0.5," if loop else ""
        filt.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,{trim}volume={gain}dB,adelay={ms}|{ms}[s{k}]")
        labels.append(f"[s{k}]")
        k += 1
    filt.append("".join(labels[:nv]) + f"amix=inputs={nv}:normalize=0[vox]")
    filt.append("[vox]asplit=2[voxa][voxb]")
    filt.append("".join(labels[nv:]) + f"amix=inputs={len(labels) - nv}:normalize=0[fx]")
    if music and Path(music).exists():
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        filt.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume=-17dB,afade=t=in:d=1.5,"
                    f"afade=t=out:st={total - 3:.2f}:d=3[mus]")
        filt.append("[fx][mus]amix=inputs=2:normalize=0[bed]")
        k += 1
    else:
        filt.append("[fx]anull[bed]")
    filt.append("[bed][voxb]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck]")
    filt.append(f"[voxa][duck]amix=inputs=2:normalize=0,atrim=0:{total:.2f},volume=-1.5dB,alimiter=limit=0.8[aout]")
    (work / "filter.txt").write_text(";\n".join(filt), encoding="utf-8")
    r = subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(video)] + inputs +
                   ["-/filter_complex", str(work / "filter.txt"), "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(out)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-3000:])
    print(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        sid, t = sys.argv[2], float(sys.argv[3])
        cls = [c for c, _, _ in TIMELINE if c.__name__.startswith(sid)][0]
        out = Path("D:/Temp/cartoon/voc_demo/stills")
        out.mkdir(parents=True, exist_ok=True)
        cls().frame(t).save(out / f"{sid}_{t:.2f}.jpg", quality=88)
        print(out / f"{sid}_{t:.2f}.jpg")
    elif cmd == "render":
        i, n = map(int, sys.argv[2].split("/"))
        render_part(i, n, sys.argv[3])
    elif cmd == "mix":
        mix(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "total":
        print(starts()[1])
