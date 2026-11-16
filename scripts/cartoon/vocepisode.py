"""VOC pilot, full episode (approved script + Stage 5 storyboard + V5 visual standard). All artwork drawn in code.

The episode is a list of SEGMENTS. A line segment plays one recorded line; its shots cut on the line's recorded words.
A pause segment is action without narration. Shots never exceed 14 s.

  python scripts/cartoon/vocepisode.py plan                      shot list with times (checks the 14 s rule)
  python scripts/cartoon/vocepisode.py still <shot index> <t>    one frame
  python scripts/cartoon/vocepisode.py sheet                     one frame per shot -> contact sheet
  python scripts/cartoon/vocepisode.py render <i>/<n> <outdir>
  python scripts/cartoon/vocepisode.py mix <parts> <out> [music]

Owner rules applied: Colachel is shown as a SIEGE (siege battery, defenders behind the stockade, supplies running out,
the gunpowder fire, the surrender as the climax), never an open-field battle; Scene 7 is serious (no hosts, no jokes,
held camera, no gore); text = subtitles + short top labels only; hosts unchanged; the tease line is not recorded yet.
"""
from __future__ import annotations

import json
import math
import re
import os
import random
import sys
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("TE_VOICE", "D:/Temp/cartoon/voc_ep/voice")
import motions as M  # noqa: E402
import people as PP  # noqa: E402
import vocfilm as VF  # noqa: E402
VF.VOICE = Path(os.environ["TE_VOICE"])
import vocbattle as B  # noqa: E402
import vocbattle3 as B3  # noqa: E402
import vocart as A  # noqa: E402
import vocdemo as D  # noqa: E402
import vocfx as FX  # noqa: E402
import vocsets as VS  # noqa: E402
import vocsets2 as VS2  # noqa: E402
import vocship as V  # noqa: E402
import flatmap as F  # noqa: E402
from vocart import INK, Layer, W, H, S, mix, shade, light  # noqa: E402

VOICE = VF.VOICE
FPS = 24
_P_ORIG = D.P


def _P_sized(key, x, ground, scale=1.0, flip=False, **kw):
    """Owner review 16 Nov: characters were too large; documentary framing shows the place around them."""
    if scale > 4.0:
        scale *= 0.72
    elif scale > 2.0:
        scale *= 0.75
    return _P_ORIG(key, x, ground, scale, flip=flip, **kw)


D.P = _P_sized
VF.P = _P_sized
B.P = _P_sized
B3.P = _P_sized
LEAD, GAP = 0.25, 0.45
P = D.P
WORDS = json.loads((VOICE / "words.json").read_text(encoding="utf-8"))
DUR = json.loads((VOICE / "durations.json").read_text(encoding="utf-8"))

# ------------------------------------------------------------------------------------------------ extra cast (same body system)
TW = PP.WORLDS["travancore_1741"]
VW = PP.WORLDS["voc_1620"]
AD = B.ADULT
VW["coen"] = replace(VW["merchant"], neck="falling_band", beard="pointed", beard_col=(70, 50, 36), headwear="capotain", prop="", **AD)
VW["merchant_v2"] = replace(VW["merchant"], **AD)
VW["merchant2_v2"] = replace(VW["merchant"], skin=(232, 196, 166), beard="full2", beard_col=(150, 146, 140), old=True, neck="falling_band", **AD)
VW["sailor_v2"] = replace(VW["sailor"], **AD)
VW["sailor2_v2"] = replace(VW["sailor2"], **AD)
VW["soldier_v2"] = replace(VW["soldier"], **AD)
VW["banda_man_v2"] = replace(VW["banda_man"], **AD)
VW["banda_man2_v2"] = replace(VW["banda_man2"], **AD)
VW["banda_woman_v2"] = replace(VW["banda_woman"], **AD)
TW["marthanda"] = replace(TW["ramayyan"], name="Marthanda Varma, Maharaja of Travancore", skin=(150, 100, 66), beard="moustache", chain=True,
                          earrings=True, bracelets=True, tiraz=True, cloak="shawl", cloak_col=(244, 241, 232), cloak_trim=(212, 170, 64),
                          prop="", build=1.12, **AD)
TW["envoy"] = replace(TW["delannoy"], name="Company envoy", prop="scroll", hair_col=(220, 216, 210), **AD)
TW["valckenier"] = replace(TW["delannoy"], name="Governor-General (1740)", hair="queue", hair_col=(226, 222, 216), headwear="none",
                           garment_col=(40, 36, 40), flags=(), prop="", build=1.12, **AD)
TW["judge"] = replace(TW["delannoy"], name="Judge", hair="queue", hair_col=(226, 222, 216), headwear="none", garment_col=(24, 22, 26),
                      flags=(), prop="", **AD)
TW["chinese"] = replace(TW["voc_soldier"], name="Batavia Chinese resident (1740)", skin=(226, 190, 150), hair="queue", hair_col=(26, 24, 24),
                        headwear="none", garment="robe_round", garment_col=(52, 70, 104), garment_col2=(52, 70, 104), garment_col3=(40, 40, 50),
                        hem=2.0, flags=(), prop="", legs=((40, 40, 50), (40, 40, 50)), footwear="shoes", neck="", cuff_col=(), **AD)
TW["chinese2"] = replace(TW["chinese"], garment_col=(110, 70, 52), garment_col2=(110, 70, 52), skin=(214, 178, 140), beard="sparse")
TW["chinese_w"] = replace(TW["chinese"], hair="bun", garment_col=(140, 52, 48), garment_col2=(140, 52, 48))
TW["prisoner"] = replace(TW["voc_v2"], prop="")
VK, TK = "voc_1620:", "travancore_1741:"


# ------------------------------------------------------------------------------------------------ shot building blocks
def font(size, serif=True):
    for f in (("C:/Windows/Fonts/georgiab.ttf" if serif else "C:/Windows/Fonts/arialbd.ttf"), "DejaVuSerif-Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


_SETS = {}


def get_set(name):
    if name not in _SETS:
        if name in ("banda_harbour", "banda_quay", "fort_wall", "colachel_camp", "road_inland"):
            _SETS[name] = VS.Set(name)
        else:
            _SETS[name] = VS2.Set2(name)
    return _SETS[name]


class Shot:
    """A set, performers, under/over drawing, an optional top label and a camera move (zoom, centre)."""

    def __init__(self, set_name, perf=None, under=None, over=None, label=None, cam=None, blur=0, flat=False, tint=None, ctx=None):
        self.set_name, self.under, self.over, self.label, self.cam, self.blur, self.flat, self.tint = set_name, under, over, label, cam, blur, flat, tint
        self.ctx = ctx or {}
        self.perf = perf(self.ctx) if callable(perf) else (perf or [])

    def frame(self, t):
        s = get_set(self.set_name)
        M.CUR_PLATE = "colachel_v2"
        M.SUN_FROM_RIGHT.add("colachel_v2")

        def actors(f, tt):
            if self.blur:
                f.paste(f.filter(ImageFilter.GaussianBlur(self.blur)))
            if self.under:
                self.under(f, tt, self)
            old = M.SHADE
            M.SHADE = not self.flat
            D.paint_all(f, tt, self.perf)
            M.SHADE = old
            if self.over:
                self.over(f, tt, self)
        f = s.frame(t, actors).convert("RGBA")
        if hasattr(s, "front") and callable(getattr(s, "front")):
            pass
        if self.label:
            VF.label(f, self.label, a=VF.fade(t, 0.3, 999), size=40)
        if self.tint:
            f = Image.blend(f, Image.new("RGBA", f.size, self.tint[0] + (255,)), self.tint[1])
        f = camera(f, t, self.cam, self.dur)
        return A.grade2(f, sun=getattr(s, "sun", (1600, 220)) or (1600, 220), t=t)


def camera(f, t, cam, dur):
    if not cam:
        return f
    z0, z1, cx, cy = cam
    k = z0 + (z1 - z0) * min(1.0, t / max(0.1, dur))
    if abs(k - 1.0) < 1e-3:
        return f
    return f.crop((int(cx - cx / k), int(cy - cy / k), int(cx + (W - cx) / k), int(cy + (H - cy) / k))).resize((W, H), Image.LANCZOS)


class MapShot:
    """A flat 2D map with drawing on it; optional host standing on the map."""

    def __init__(self, bb, draw, perf=None, label=None, cam=None, ctx=None):
        self.bb, self.draw, self.label, self.cam = bb, draw, label, cam
        self.ctx = ctx or {}
        self.perf = perf(self.ctx) if callable(perf) else (perf or [])

    def frame(self, t):
        img, pj = F.base(self.bb)
        f = img.copy()
        f.alpha_composite(F.sea_waves(self.bb, t))
        d = ImageDraw.Draw(f)
        self.draw(f, d, pj, t)
        M.CUR_PLATE = ""
        D.paint_all(f, t, self.perf)
        if self.label:
            VF.label(f, self.label, a=VF.fade(t, 0.3, 999), size=40)
        f = camera(f, t, self.cam, self.dur)
        return A.grade2(f, sun=(1600, 200), t=t, sat=1.12, contrast=1.14, glow=0.08, vignette=0.15)


class Custom:
    """A close-up drawn by a function on top of a (blurred) set."""

    def __init__(self, set_name, draw, blur=8, label=None, ctx=None, darken=0.0):
        self.set_name, self.draw, self.blur, self.label, self.darken = set_name, draw, blur, label, darken
        self.ctx = ctx or {}

    def frame(self, t):
        s = get_set(self.set_name)
        f = s.frame(t).convert("RGBA")
        if self.blur:
            f = f.filter(ImageFilter.GaussianBlur(self.blur))
        if self.darken:
            f = Image.blend(f, Image.new("RGBA", f.size, (20, 16, 14, 255)), self.darken)
        L = Layer()
        self.draw(L, t, self)
        f.alpha_composite(L.out())
        if self.label:
            VF.label(f, self.label, a=VF.fade(t, 0.3, 999), size=40)
        return A.grade2(f, sun=getattr(s, "sun", (1600, 220)), t=t)


class Wrap:
    """Use an existing shot class (demo / battle) as is, with a time offset."""

    def __init__(self, cls, toff=0.0, ctx=None):
        self.obj = cls()
        self.toff = toff

    def frame(self, t):
        return self.obj.frame(t + self.toff)


def lip(ctx, line_id):
    return VF.lips(line_id, ctx.get(line_id, 0.0))


def host(key, x, ground, scale, line_id, acts=None, flip=False, props=None, faces=None):
    return lambda ctx: [P(key, x, ground, scale, flip=flip, lips=lip(ctx, line_id), acts=acts or [], props=props or {}, faces=faces or [])]


class TitleCard:
    """Opening/closing title: the channel name and what the episode is about (owner review 16 Nov)."""

    def __init__(self, ctx=None, sub="How the Dutch Built a Global Trading Empire"):
        self.sub = sub

    def frame(self, t):
        s = get_set("banda_harbour")
        f = s.frame(t + 20, lambda fr, tt: V.place(fr, tt, 980, 736, L=680, facing=-1)).convert("RGBA")
        a = VF.fade(t, 0.2, 999, 0.5)
        f.alpha_composite(Image.new("RGBA", f.size, (20, 16, 12, int(110 * a))))
        d = ImageDraw.Draw(f)
        d.text((960, 440), "TINY EMPIRES", font=font(110), fill=(250, 236, 200, int(255 * a)), anchor="mm", stroke_width=7,
               stroke_fill=INK + (int(255 * a),))
        b = VF.fade(t, 0.6, 999, 0.5)
        d.text((960, 570), self.sub, font=font(58), fill=(255, 220, 150, int(255 * b)), anchor="mm", stroke_width=5, stroke_fill=INK + (int(255 * b),))
        return A.grade2(f, sun=(380, 560), t=t)


# ------------------------------------------------------------------------------------------------ custom drawings
def nutmeg_close(L, t, sh):
    k = min(1.0, max(0.0, (t - 0.8) / 1.6))
    L.line([(300, 200), (980, 520)], (100, 76, 52), 16)
    for i, (x, y) in enumerate(((520, 300), (760, 420), (1180, 360))):
        L.blob([(x - 160, y), (x - 40, y - 70), (x + 160, y - 20), (x + 40, y + 60)], (56, 110, 60), 2.4, n=4)
    cx, cy = 980, 640
    L.line([(980, 520), (cx, cy - 150)], (100, 76, 52), 8)
    if k < 0.05:
        L.ellipse((cx - 150, cy - 160, cx + 150, cy + 160), A.hexc("#E2C25A"), 4)
    else:
        for side in (-1, 1):                                             # the fruit splits
            ox = side * 60 * k
            L.d.pieslice([(cx - 150 + ox) * S, (cy - 160) * S, (cx + 150 + ox) * S, (cy + 160) * S], 90 if side < 0 else 270,
                         270 if side < 0 else 90, fill=A.hexc("#E2C25A") + (255,), outline=INK + (255,), width=4 * S)
        L.ellipse((cx - 70, cy - 90, cx + 70, cy + 90), (90, 56, 40), 3)
        for i in range(10):                                              # the red lacy mace
            a = i / 10 * math.tau
            L.line([(cx + math.cos(a) * 30, cy + math.sin(a) * 40), (cx + math.cos(a + 0.4) * 72, cy + math.sin(a + 0.4) * 95)],
                   A.hexc("#C8282B"), 7 * k)


def charter_draw(L, t, sh):
    k = min(1.0, t / 1.2)
    w = 1200 * k
    L.rect((360, 220, 360 + max(40, w), 860), (240, 228, 196), 4)
    L.ellipse((330, 200, 400, 880), (220, 206, 170), 4)
    if k > 0.9:
        f = font(54)
        L.d.text((960 * S, 330 * S), "Octrooi", font=font(80 * S), fill=INK + (255,), anchor="mm")
        for i in range(8):
            L.line([(460, 420 + i * 46), (1460, 420 + i * 46)], (150, 130, 100), 3)
        a = min(1.0, (t - 1.6) / 0.6) if t > 1.6 else 0
        L.d.text((960 * S, 800 * S), "20 March 1602", font=font(56 * S), fill=(120, 30, 30, int(255 * a)), anchor="mm")
        if t > 2.6:                                                      # the monogram inked in
            kk = min(1.0, (t - 2.6) / 0.8)
            L.d.text((1380 * S, 760 * S), "VOC", font=font(90 * S), fill=(30, 40, 90, int(255 * kk)), anchor="mm")


def hourglass(L, t, sh):
    x, y = 1500, 560
    L.poly([(x - 90, y - 200), (x + 90, y - 200), (x + 10, y), (x + 90, y + 200), (x - 90, y + 200), (x - 10, y)], (230, 236, 240), 4)
    k = min(1.0, t / max(1.0, sh.dur))
    L.poly([(x - 80 * (1 - k), y - 190 + 180 * k), (x + 80 * (1 - k), y - 190 + 180 * k), (x, y - 6)], (214, 180, 110), 0)
    L.poly([(x - 80, y + 190), (x + 80, y + 190), (x + 80 * (1 - k * 0.3), y + 190 - 150 * k), (x - 80 * (1 - k * 0.3), y + 190 - 150 * k)], (214, 180, 110), 0)
    L.line([(x, y), (x, y + 190)], (214, 180, 110), 3, a=200)
    L.d.text((x * S, (y + 270) * S), "21 years", font=font(60 * S), fill=(250, 240, 214, 255), anchor="mm", stroke_width=6 * S,
             stroke_fill=INK + (255,))


def quill_labels(L, t, sh):
    L.rect((260, 160, 1660, 900), (240, 228, 196), 4)
    for i in range(10):
        L.line([(340, 260 + i * 56), (1580, 260 + i * 56)], (150, 130, 100), 3)
    for j, (txt, tt) in enumerate((("mint money", 3.4), ("declare war", 5.2))):
        x, y = 700 + j * 520, 520 + j * 120
        if t < tt + 1.2:
            L.rect((x - 200, y - 50, x + 200, y + 50), (250, 236, 120), 3)
            L.d.text((x * S, y * S), txt, font=font(48 * S), fill=INK + (255,), anchor="mm")
            if t > tt:
                L.line([(x - 190, y + 40), (x + 190, y - 40)], (200, 40, 40), 9)


def tally(L, t, sh):
    k = min(1.0, t / max(1.0, sh.dur * 0.8))
    v = 6.4 * k
    L.d.text((1500 * S, 260 * S), f"about {v:.1f} million guilders", font=font(54 * S), fill=(250, 240, 214, 255), anchor="mm",
             stroke_width=6 * S, stroke_fill=INK + (255,))


def population(fade_from):
    def draw(L, t, sh):
        L.rect((-10, -10, W + 10, H + 10), (40, 36, 34), 0, a=170)
        n_vis = 15 if t < fade_from else max(1, 15 - int((t - fade_from) / 0.35))
        for i in range(15):
            x, y = 360 + (i % 5) * 300, 300 + (i // 5) * 220
            a = 255 if i < n_vis else max(0, 255 - int((t - fade_from - (15 - i) * 0.35) * 300))
            if a <= 0:
                continue
            L.ellipse((x - 24, y - 70, x + 24, y - 22), (196, 160, 120), 3, a=a)
            L.poly([(x - 40, y + 60), (x - 30, y - 20), (x + 30, y - 20), (x + 40, y + 60)], (150, 110, 80), 3, a=a)
        txt = "Estimated population before 1621: about 13,000 to 15,000" if t < fade_from else "Estimated afterwards: about 1,000"
        L.d.text((960 * S, 120 * S), txt, font=font(44 * S), fill=(250, 240, 214, 255), anchor="mm")
        if t > fade_from + 2.5:
            L.d.text((960 * S, 1000 * S - 130 * S), "killed, starved, fled or enslaved: the split is not known", font=font(36 * S),
                     fill=(230, 220, 200, 255), anchor="mm")
    return draw


def ledger_people(L, t, sh):
    L.rect((300, 140, 1620, 940), (238, 226, 196), 4)
    L.line([(960, 140), (960, 940)], (160, 140, 110), 3)
    n = int(t * 3)
    for i in range(min(n, 22)):                                          # lines of entries (illegible, no names)
        side = i // 11
        y = 220 + (i % 11) * 60
        x0 = 360 + side * 640
        L.line([(x0, y), (x0 + 360 + (i * 37) % 160, y)], (60, 50, 60), 4)
        L.line([(x0 + 470, y), (x0 + 560, y)], (60, 50, 60), 4)
    px = 360 + (n % 11) * 30 + (n // 11) * 640
    py = 220 + (n % 11) * 60
    L.line([(px + 40, py - 120), (px, py)], (240, 236, 226), 6)
    L.ellipse((1720, 700, 1790, 820), (240, 230, 200), 3)                # the candle
    fl = 8 * math.sin(t * 9)
    L.blob([(1740, 700), (1755, 650 + fl), (1770, 700)], (255, 200, 80), 0, n=3)


def red_ledger(L, t, sh):
    L.rect((300, 140, 1620, 940), (238, 226, 196), 4)
    for i in range(12):
        y = 200 + i * 60
        L.line([(360, y), (1200, y)], (150, 130, 100), 3)
        k = min(1.0, max(0.0, t * 1.5 - i * 0.25))
        col = mix((60, 50, 60), (190, 30, 30), k)
        L.line([(1300, y - 10), (1300 + 200 * (0.5 + 0.5 * math.sin(i)), y - 10)], col, 6)


def banner_crack(L, t, sh):
    k = min(1.0, max(0.0, (t - 1.5) / 1.0))
    for i, ch in enumerate("TRILLIONS!"):
        x = 380 + i * 128
        y = 520 + (k * k * 900 * (0.5 + (i % 3) * 0.3) if k > 0 else 0)
        rot = k * (i - 5) * 12
        L.d.text((x * S, y * S), ch, font=font(150 * S), fill=(212, 170, 64, 255), anchor="mm", stroke_width=8 * S, stroke_fill=INK + (255,))
    if 1.2 < t < 1.7:
        L.line([(300, 400), (900, 640), (1200, 470), (1640, 700)], INK, 8)


def deficit(L, t, sh):
    k = min(1.0, t / 3.0)
    L.d.text((960 * S, 480 * S), f"{int(74 * k)} million guilders", font=font(110 * S), fill=(200, 40, 40, 255), anchor="mm",
             stroke_width=8 * S, stroke_fill=INK + (255,))
    L.d.text((960 * S, 620 * S), "in deficit (1789)", font=font(60 * S), fill=(250, 240, 214, 255), anchor="mm", stroke_width=6 * S,
             stroke_fill=INK + (255,))


def europe_shields(L, t, sh):
    def shield(x, y, col, txt, a=255):
        L.poly([(x - 80, y - 90), (x + 80, y - 90), (x + 80, y + 20), (x, y + 110), (x - 80, y + 20)], col, 4, a=a)
        L.d.text((x * S, (y + 160) * S), txt, font=font(40 * S), fill=(250, 240, 214, a), anchor="mm", stroke_width=5 * S, stroke_fill=INK + (a,))
    shield(560, 620, (40, 90, 160), "Portugal")
    shield(980, 560, (190, 50, 40), "Spain")
    shake = 6 * math.sin(t * 30) if t > 7.5 else 0
    shield(1420 + shake, 360, (230, 120, 40), "Dutch Republic")
    if t > 5.0:                                                          # 1580: one crown for both
        k = min(1.0, (t - 5.0) / 1.2)
        cx = 980 + (770 - 980) * k
        cy = 430 - 40 * math.sin(k * math.pi)
        L.poly([(cx - 70, cy), (cx - 60, cy - 60), (cx - 25, cy - 25), (cx, cy - 70), (cx + 25, cy - 25), (cx + 60, cy - 60), (cx + 70, cy)],
               (226, 184, 60), 4)
        if k >= 1:
            L.d.text((770 * S, 330 * S), "1580", font=font(44 * S), fill=(250, 240, 214, 255), anchor="mm", stroke_width=5 * S, stroke_fill=INK + (255,))


def split_screen(L, t, sh):
    pass


# ------------------------------------------------------------------------------------------------ maps
BB_SPICE = (116, -12, 140, 4)
BB_TRADE = (-12, -14, 140, 50)
BB_EUROPE = (-14, 34, 16, 56)
BB_ASIA = (12, -40, 146, 42)
BB_SEASIA = (94, -12, 136, 12)
BB_KERALA = (70, 6, 82, 14)
BB_AUS = (100, -36, 126, -4)
BB_INDIA = (64, 4, 100, 30)


def mdot(f, d, pj, lon, lat, name, t, t0, dy=-36, col=(200, 46, 40), size=34):
    if t < t0:
        return
    x, y = pj(lon, lat)
    F.dot(d, x, y, t, t0, col)
    if name:
        F.label(d, name, x, y + dy, size, a=min(1, (t - t0) / 0.4))


def glow(f, d, pj, lon, lat, t, col=(255, 220, 100)):
    x, y = pj(lon, lat)
    r = 26 + 10 * math.sin(t * 4)
    d.ellipse([x - r, y - r, x + r, y + r], outline=col + (255,), width=6)


def map_spice(f, d, pj, t):
    glow(f, d, pj, 129.9, -4.5, t)
    mdot(f, d, pj, 129.9, -4.5, "Banda Islands", t, 0.4)


def map_maluku(f, d, pj, t):
    mdot(f, d, pj, 129.9, -4.5, "Banda", t, 0)
    for lon, lat in ((127.4, 0.8), (128.2, -3.6), (127.9, 0.0)):
        glow(f, d, pj, lon, lat, t, (240, 160, 120))
    mdot(f, d, pj, 127.6, 0.3, "Maluku (cloves)", t, 0.5)


def map_chain(f, d, pj, t):
    stops = [((129.9, -4.5), "Banda"), ((100.3, 2.2), "Malay traders"), ((72.8, 21.2), "Gujarat"), ((44, 13), "Arab traders"),
             ((12.3, 45.4), "Venice")]
    for i, ((lon, lat), name) in enumerate(stops):
        t0 = i * 1.3
        mdot(f, d, pj, lon, lat, name, t, t0, dy=-40, size=30)
        if t > t0 + 0.4:                                                 # the price tag grows at every hand
            x, y = pj(lon, lat)
            s = 16 + i * 9
            d.rectangle([x + 18, y + 10, x + 18 + s * 1.6, y + 10 + s], fill=(250, 236, 120, 255), outline=INK + (255,), width=3)
    pts = [p for p, _ in stops]
    h, a = F.route(d, pj, pts, min(1.0, t / 6.0), color=(200, 150, 60), width=6)


def map_cape_gate(f, d, pj, t):
    x, y = pj(18.5, -36)
    d.rectangle([x - 6, y - 140, x + 6, y + 140], fill=(120, 80, 50, 255), outline=INK + (255,), width=3)
    for i in range(3):
        k = ((t * 0.4) + i / 3) % 1.0
        sx = x - 360 + 300 * min(1, k * 1.6) - (300 * max(0, k * 1.6 - 1) * 2 if k > 0.62 else 0)
        F.ship_icon(d, sx, y - 80 + i * 70, 0, t + i, 1.0)
    F.label(d, "The Cape of Good Hope: closed to other Dutch ships", x, y - 190, 32)


def map_reef(f, d, pj, t):
    xs = [pj(113.5, -22 - i * 1.2) for i in range(12)]
    if int(t * 3) % 2 == 0:
        d.line(xs, fill=(220, 40, 40, 255), width=10)
    h, a = F.route(d, pj, [(80, -40), (108, -36), (114, -28)], min(1.0, t / 3.0), color=(230, 150, 40))
    F.ship_icon(d, h[0], h[1], a, t, 1.3)
    if t > 3.0:
        F.label(d, "wreck coast", *pj(118, -26), 38)


def map_network(off):
    posts = [((128.2, -3.7), "Ambon 1605", 2.0), ((102.25, 2.2), "Malacca 1641", 5.5), ((79.9, 7.0), "Sri Lanka coast", 12.0),
             ((18.4, -33.9), "Cape 1652", 14.5), ((129.9, 32.7), "Dejima", 18.7), ((106.8, -6.2), "Batavia (Jakarta)", 0.0)]

    def draw(f, d, pj, t):
        T = t + off
        for (lon, lat), name, t0 in posts:
            mdot(f, d, pj, lon, lat, name, T, t0, size=30)
        if T > 2.8:
            x, y = pj(103.8, 1.6)
            F.label(d, "with Johor", x + 60, y + 40, 26, a=min(1, (T - 2.8) / 0.4))
    return draw


def map_blob(f, d, pj, t):
    k = min(1.0, t / 2.0) if t < 3.5 else max(0.0, 1 - (t - 3.5) / 1.0)
    if k > 0:
        pts = [pj(95, 6), pj(140, 6), pj(140, -10), pj(95, -10)]
        d.polygon(pts, fill=(200, 60, 40, int(110 * k)))
    for (lon, lat), name in (((106.8, -6.2), "Batavia"), ((128.2, -3.7), "Ambon"), ((102.25, 2.2), "Malacca"), ((129.9, -4.5), "Banda")):
        mdot(f, d, pj, lon, lat, name, t, 0, size=30)


def map_loop(f, d, pj, t):
    arrows = [((80, 13), (128, -3), (226, 214, 186), "cloth"), ((128, -3), (106, -6), (200, 120, 60), "spice"),
              ((130, 33), (88, 22), (200, 200, 210), "silver")]
    for i, (a, b, col, name) in enumerate(arrows):
        ph = (t * 0.35 + i / 3) % 1.0
        x0, y0 = pj(*a)
        x1, y1 = pj(*b)
        d.line([(x0, y0), (x1, y1)], fill=INK + (255,), width=12)
        d.line([(x0, y0), (x1, y1)], fill=col + (255,), width=7)
        cx, cy = x0 + (x1 - x0) * ph, y0 + (y1 - y0) * ph
        d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=col + (255,), outline=INK + (255,), width=3)
        F.label(d, name, (x0 + x1) / 2, (y0 + y1) / 2 - 30, 30)


def map_battles(f, d, pj, t):
    for i, ((lon, lat), name) in enumerate((((128.2, -3.7), "Ambon"), ((119.4, -5.1), "Makassar"), ((120.2, 23.0), "Taiwan"),
                                           ((77.3, 8.2), "Travancore"), ((102.25, 2.2), "Malacca"))):
        t0 = 0.6 + i * 1.2
        if t < t0:
            continue
        x, y = pj(lon, lat)
        s = 22 * (1 + 0.15 * math.sin((t - t0) * 5))
        d.line([(x - s, y - s), (x + s, y + s)], fill=INK + (255,), width=9)
        d.line([(x - s, y + s), (x + s, y - s)], fill=INK + (255,), width=9)
        d.line([(x - s, y - s), (x + s, y + s)], fill=(220, 200, 160, 255), width=5)
        d.line([(x - s, y + s), (x + s, y - s)], fill=(220, 200, 160, 255), width=5)
        F.label(d, name, x, y - 46, 30)


def map_makassar(f, d, pj, t):
    mdot(f, d, pj, 119.4, -5.1, "Makassar (Gowa)", t, 0.3)
    mdot(f, d, pj, 120.0, -4.2, "Bugis allies", t, 2.0, dy=40, col=(60, 120, 60))
    h, a = F.route(d, pj, [(106.8, -6.2), (113, -7), (119, -5.6)], min(1.0, t / 4.0), color=(230, 150, 40))
    F.ship_icon(d, h[0], h[1], a, t, 1.3)
    if t > 6:
        F.label(d, "1666-69", *pj(122.5, -7.5), 40)


def map_taiwan(f, d, pj, t):
    x, y = pj(120.9, 23.6)
    k = min(1.0, max(0.0, (t - 3.0) / 1.0))
    col = mix((200, 46, 40), (60, 90, 160), k)
    d.ellipse([x - 40, y - 70, x + 40, y + 70], fill=col + (150,), outline=INK + (255,), width=4)
    F.label(d, "Taiwan: lost in 1662" if k > 0.5 else "Taiwan (Fort Zeelandia)", x - 160, y - 100, 34)


def map_travancore(f, d, pj, t):
    k = min(1.0, t / 1.5)
    pts = [pj(76.4, 9.2), pj(77.5, 9.4), pj(77.6, 8.1), pj(77.0, 8.0)]
    d.polygon(pts, fill=(60, 140, 80, int(140 * k)), outline=INK + (255,))
    mdot(f, d, pj, 77.27, 8.18, "Colachel", t, 0.8, dy=40)
    F.label(d, "Travancore", *pj(77.2, 9.0), 40)


def map_1753(f, d, pj, t):
    pts = [pj(76.2, 10.2), pj(77.5, 10.0), pj(77.6, 8.1), pj(77.0, 8.0)]
    d.polygon(pts, fill=(60, 140, 80, 120), outline=INK + (255,))
    F.label(d, "Travancore", *pj(76.9, 9.2), 40)
    mdot(f, d, pj, 76.27, 9.96, "Cochin (still Dutch)", t, 0.5 if not getattr(f, "_late", False) else 0, dy=-40)
    if t > 1.0:
        F.label(d, "Treaty, 1753", *pj(78.6, 11.4), 40)


def map_rulers(f, d, pj, t):
    for i, ((lon, lat), col) in enumerate((((77, 9), (200, 160, 60)), ((110, -7), (140, 60, 60)), ((100, 14), (190, 120, 40)),
                                          ((120, -4), (60, 120, 80)), ((106.8, -6.2), (40, 70, 140)))):
        x, y = pj(lon, lat)
        d.line([(x, y + 30), (x, y - 60)], fill=INK + (255,), width=5)
        wv = 6 * math.sin(t * 3 + i)
        d.polygon([(x, y - 60), (x + 60, y - 50 + wv), (x, y - 30)], fill=col + (255,), outline=INK + (255,))


# ------------------------------------------------------------------------------------------------ action pieces for shots
def ship_in(x0, x1, y, L_=700, ports=0.0, era=1620, facing=-1):
    def under(f, t, sh):
        k = min(1.0, t / max(1.0, sh.dur))
        V.place(f, t, x0 + (x1 - x0) * k, y, L=L_, ports=ports, facing=facing, era=era)
    return under


def coins_fx(f, t, sh):
    L = Layer()
    for i in range(14):
        ph = ((t * 1.2) + i / 14) % 1.0
        x, y = 980 + math.sin(i * 1.7) * 60, 380 + ph * 420
        L.ellipse((x - 14, y - 8, x + 14, y + 8), (226, 184, 60), 2)
    L.rect((860, 800, 1120, 900), (110, 72, 44), 3)
    f.alpha_composite(L.out())


def table_fx(sword_t=1.5):
    def under(f, t, sh):
        L = Layer()
        L.poly([(300, 760), (1620, 760), (1700, 900), (220, 900)], (40, 80, 50), 3)
        for x in (520, 820, 1120):
            L.rect((x, 740, x + 120, 760), (240, 228, 196), 2)
        if t > sword_t:
            k = min(1.0, (t - sword_t) / 0.4)
            y = 700 - 300 * (1 - k)
            L.line([(760, y + 40), (1220, y + 10)], (200, 204, 210), 9)
            L.rect((720, y + 20, 770, y + 60), (180, 140, 60), 2)
        f.alpha_composite(L.out())
    return under


def stakes_rise(f, t, sh):
    L = Layer()
    n = int(8 + 40 * min(1.0, t / 2.0))
    D.stakes(L, 300, 300 + n * 19, 760, 180, t, seed=2)
    f.alpha_composite(L.out())


def hammocks(f, t, sh):
    L = Layer()
    for i in range(4):
        x = 300 + i * 380
        sw = 20 * math.sin(t * 1.4 + i)
        L.line([(x - 120, 300), (x + sw, 420), (x + 120, 300)], (200, 190, 160), 10, curve=True)
    L.line([(1500, 120), (1500 + 30 * math.sin(t * 1.4), 260)], (90, 70, 50), 3)
    L.ellipse((1480 + 30 * math.sin(t * 1.4), 250, 1530 + 30 * math.sin(t * 1.4), 300), (250, 210, 120), 3)
    f.alpha_composite(L.out())


def smoke_over(x, y, n=6, col=(110, 104, 100), size=30):
    def over(f, t, sh):
        L = Layer()
        VS.smoke_plume(L, x, y, t, n=n, col=col, rise=24, drift=-10, size=size, seed=3, a=220)
        f.alpha_composite(L.out())
    return over


def fire_town(f, t, sh):
    L = Layer()
    for x in (300, 700, 1200, 1600):
        VS.smoke_plume(L, x, 560, t + x, n=7, col=(96, 90, 88), rise=26, drift=-12, size=34, seed=x, a=230)
    f.alpha_composite(L.out())


def build_batavia(f, t, sh):
    L = Layer()
    n = int(2 + 10 * min(1.0, t / max(1.0, sh.dur * 0.7)))
    for i in range(n):
        L.rect((200 + i * 130, 560 - (i % 3) * 10, 300 + i * 130, 640), (232, 226, 210), 2.4)
    f.alpha_composite(L.out())


def battery_fx(times):
    def over(f, t, sh):
        L = Layer()
        for k, tt in enumerate(times):
            FX.muzzle(L, 640 - k * 380, 760, t, tt, f=-1, wind=(14, -10), size=2.2, seed=k)
        f.alpha_composite(L.out())
    return over


def siege_battery(f, t, sh):
    """Travancore's siege battery: guns behind an earthwork and gabions, firing at the stockade (off-frame left)."""
    L = Layer()
    L.blob([(-40, 900), (200, 820), (900, 800), (1500, 830), (1960, 860), (1960, 1100), (-40, 1100)], (150, 108, 70), 2.6, n=6)
    for x in (300, 420, 680, 800):
        B.gabion(L, x, 840, 36, 60)
    for k, gx in enumerate((560, 940)):
        tt = 1.2 + k * 1.4
        rec = max(0.0, 1 - abs(t - tt) * 3) if t > tt else 0.0
        B.cannon(L, gx, 830, 1.3, recoil=rec, facing=-1)
    f.alpha_composite(A.texturize(L.out(), B.tex(12, 30), 0.18))


def store_dwindle(f, t, sh):
    L = Layer()
    L.poly([(500, 900), (500, 640), (1400, 630), (1410, 900)], (196, 170, 120), 3)
    n = max(1, 8 - int(t * 2.2))
    for i in range(n):
        x = 620 + i * 95
        L.blob([(x - 44, 900), (x - 40, 830), (x + 40, 830), (x + 44, 900)], (226, 206, 160), 2.6, n=3)
    f.alpha_composite(L.out())


def flag_lower(f, t, sh):
    L = Layer()
    L.line([(980, 690), (980, 330)], INK, 6)
    y = 330 + 300 * min(1.0, t / max(1.0, sh.dur * 0.8))
    V._flag(L, 984, y, 150, 92, t, [(176, 40, 40), (246, 242, 230), (40, 70, 140)], ink=3)
    f.alpha_composite(L.out())


def crates_night(f, t, sh):
    L = Layer()
    for i in range(3):
        L.rect((1300 + i * 90, 820, 1380 + i * 90, 880), (120, 80, 48), 3)
    f.alpha_composite(L.out())


def lay_down_arms(f, t, sh):
    L = Layer()
    n = int(min(6, t * 1.5))
    for i in range(n):                                                   # muskets laid on the sand
        L.line([(820 + i * 30, 960 - i * 4), (1080 + i * 30, 948 - i * 4)], (90, 70, 50), 7)
    f.alpha_composite(L.out())


# ------------------------------------------------------------------------------------------------ the episode
def C(cls, **kw):
    return lambda ctx: cls(ctx=ctx, **kw)


def Wd(cls, toff=0.0):
    return lambda ctx: Wrap(cls, toff)


S1 = [
    ("L", "S1L01", [(0, Wd(VF.S01Harbour)), (7, Wd(VF.S02Ports)), (9, Wd(VF.S03Fort)), (12, Wd(VF.S04Ledger))]),
    ("L", "S1L02", [(0, Wd(VF.S05Quay)), ("it", C(Shot, set_name="interior", under=coins_fx, perf=lambda c: [P(VK + "merchant_v2", 760, 960, 1.9,
                    acts=[(0.4, "rub", None)], faces=[(0.0, {"mouth": "grin"})])])),
                    ("other", C(Custom, set_name="banda_grove", draw=lambda L, t, s: None, blur=0))]),
    ("L", "S1L03", [(0, C(Shot, set_name="interior", under=table_fx(1.2), perf=lambda c: [
        P(VK + "merchant_v2", 420, 980, 1.8), P(VK + "merchant2_v2", 1500, 980, 1.8, flip=True, acts=[(1.6, "double_take", None)]),
        P(VK + "coen", 1000, 1000, 1.9, acts=[(1.0, "present", None)])]))]),
    ("L", "S1L04", [(0, Wd(VF.S06Penny))]),
    ("P", 3.2, [(0, C(TitleCard))]),
]

S2 = [
    ("L", "S2L01", [(0, C(MapShot, bb=BB_SPICE, draw=map_spice, perf=lambda c: [P("atlas", 240, 1000, 2.1, lips=[], acts=[(1.0, "point", None)])])),
                    ("nutmeg", C(Custom, set_name="banda_grove", draw=nutmeg_close, blur=10)), ("came", C(MapShot, bb=BB_SPICE, draw=map_spice))]),
    ("L", "S2L02", [(0, C(MapShot, bb=BB_SPICE, draw=map_maluku))]),
    ("L", "S2L03", [(0, C(MapShot, bb=BB_TRADE, draw=map_chain))]),
    ("L", "S2L04", [(0, C(Shot, set_name="banda_quay", perf=lambda c: [P("zed", 760, 930, 2.2, lips=lip(c, "S2L04"), acts=[(1.0, "shrug", None)]),
                                                                       P("penny", 1240, 930, 2.2, flip=True, faces=[(0.0, {"mouth": "grin"})])]))]),
    ("L", "S2L05", [(0, C(Shot, set_name="banda_quay", perf=lambda c: [P("zed", 760, 930, 2.2, faces=[(0.0, {"brows": 0.5})]),
                                                                       P("penny", 1240, 930, 2.2, flip=True, lips=lip(c, "S2L05"), acts=[(0.4, "rub", None)])]))]),
    ("L", "S2L06", [(0, C(Custom, set_name="amsterdam", draw=lambda L, t, s: europe_shields(L, t, s), blur=12, label="Europe, late 1500s"))]),
    ("L", "S2L07", [(0, C(Shot, set_name="amsterdam", label="Amsterdam, 1595", under=ship_in(1400, 1700, 900, 520, facing=1), perf=lambda c: [
        P(VK + "merchant_v2", 420, 690, 1.5, acts=[(0.5, "present", None)]), P(VK + "sailor_v2", 600, 700, 1.5, flip=True, acts=[(1.0, "nod", None)]),
        P(VK + "soldier_v2", 760, 690, 1.45, flip=True), P(VK + "sailor2_v2", 220, 700, 1.5, walks=[(1.0, 900)])]))]),
]

S3 = [
    ("L", "S3L01", [(0, C(Shot, set_name="amsterdam", label="Amsterdam, 1597", under=ship_in(1800, 1300, 900, 560), perf=lambda c: [
        P(VK + "merchant_v2", 300, 690, 1.5, acts=[(0.6, "cheer", None), (2.5, "cheer", None)]), P(VK + "sailor_v2", 520, 700, 1.5, acts=[(0.9, "cheer", None)]),
        P(VK + "merchant2_v2", 700, 690, 1.5, acts=[(1.4, "celebrate", None)])])),
                    ("within", C(Shot, set_name="ocean", under=lambda f, t, s: [V.place(f, t + i, 300 + i * 500 + 60 * t * (1 + i * 0.3), 760 - i * 40, L=420 - i * 60, facing=1)
                                                                          for i in range(3)], label="Rival Dutch companies"))]),
    ("L", "S3L02", [(0, C(Shot, set_name="interior", under=table_fx(99), label="The States General", perf=lambda c: [
        P(VK + "merchant2_v2", 520, 980, 1.8, acts=[(0.8, "present", None)]), P(VK + "coen", 1380, 980, 1.8, flip=True, acts=[(2.0, "stamp", None)])])),
                    ("granted", C(Custom, set_name="interior", draw=charter_draw, blur=10))]),
    ("L", "S3L03", [(0, C(MapShot, bb=(-30, -45, 60, 10), draw=map_cape_gate)), ("for", C(Custom, set_name="interior", draw=hourglass, blur=10))]),
    ("L", "S3L04", [(0, C(Shot, set_name="interior", under=table_fx(99), perf=lambda c: [P(VK + "coen", 900, 1000, 2.0, acts=[(0.3, "stamp", None)])])),
                    ("build", C(Shot, set_name="fort_wall", under=stakes_rise, perf=lambda c: [])),
                    ("keep", C(Shot, set_name="fort_wall", perf=lambda c: [P(VK + "soldier_v2", 300 + i * 260, 880, 2.0, acts=[(0.2 + i * 0.1, "brace", None)])
                                                                         for i in range(5)]))]),
    ("L", "S3L05", [(0, C(Custom, set_name="interior", draw=quill_labels, blur=10)), ]),
    ("L", "S3L06", [(0, C(Shot, set_name="amsterdam", label="East India House: buying shares", over=lambda f, t, s: f.alpha_composite(
        (lambda L: (tally(L, t, s), L.out())[1])(Layer())), perf=lambda c: [
        P(VK + key, 300 + i * 170, 700, 1.4, walks=[(0.3 * i, 1300 - i * 120)], speed=0.6) for i, key in
        enumerate(("merchant_v2", "sailor_v2", "merchant2_v2", "sailor2_v2", "banda_man_v2" if False else "soldier_v2"))]))]),
    ("L", "S3L07", [(0, C(Shot, set_name="amsterdam", label="Amsterdam exchange (from 1611)", perf=lambda c: [
        P(VK + key, 300 + i * 260, 700 + (i % 2) * 20, 1.5, flip=i % 2 == 1, acts=[(0.3 + i * 0.4, "hold_up", None), (2.0 + i * 0.3, "shout" if i % 2 else "point", None)])
        for i, key in enumerate(("merchant_v2", "merchant2_v2", "coen", "merchant_v2", "merchant2_v2", "coen"))]))]),
]

S4 = [
    ("L", "S4L01", [(0, Wd(VF.S07Atlas))]),
    ("L", "S4L02", [(0, Wd(VF.S08Brouwer)), ("then#2", Wd(VF.S08bBrouwer))]),
    ("P", 3.2, [(0, C(Shot, set_name="ocean_storm", under=lambda f, t, s: V.place(f, t, 960, 760, L=820, facing=1, sea=3.5)))]),
    ("L", "S4L03", [(0, C(MapShot, bb=BB_AUS, draw=map_reef))]),
    ("L", "S4L04", [(0, C(Shot, set_name="amsterdam", label="Leaving for Asia", under=lambda f, t, s: V.place(f, t, 1500, 900, L=700, facing=1),
                          perf=lambda c: [P(VK + key, 100 + i * 120, 700, 1.4, walks=[(0.2 * i, 1150 + i * 30)], speed=1.2)
                                          for i, key in enumerate(("sailor_v2", "soldier_v2", "sailor2_v2", "sailor_v2", "soldier_v2", "sailor2_v2"))])),
                    ("counting", C(MapShot, bb=BB_TRADE, draw=lambda f, d, pj, t: (F.route(d, pj, B3.SHORE and [(4.5, 52.6), (-20, 10), (18.4, -34.8), (105.6, -6.6)],
                                                                                     min(1.0, t / 4)), F.label(d, "about 4,700 ships; nearly a million departures", 960, 980, 40))))]),
    ("L", "S4L05", [(0, C(Shot, set_name="interior", under=hammocks, tint=((30, 26, 30), 0.35), perf=host("pike", 900, 980, 2.3, "S4L05",
                                                                                                          acts=[(1.6, "facepalm", None)])))]),
]

S5 = [
    ("L", "S5L01", [(0, C(Shot, set_name="banda_harbour", label="Jayakarta, 1619", under=fire_town, perf=lambda c: [P(VK + "coen", 1500, 1000, 2.2, flip=True,
                                                                                                                     faces=[(0.0, {"brows": -0.4})])])),
                    ("built", C(Shot, set_name="batavia", under=build_batavia, perf=lambda c: [P(VK + "banda_man_v2", 300 + i * 300, 940, 1.6, walks=[(0.3 * i, 500 + i * 300)],
                                                                                            props={"prop_l": "bale"}) for i in range(4)])),
                    ("soon", C(Shot, set_name="batavia", label="Batavia (today Jakarta)", perf=lambda c: []))]),
    ("L", "S5L02", [(0, C(MapShot, bb=BB_SEASIA, draw=map_network(0))), ("coast", C(MapShot, bb=BB_ASIA, draw=map_network(12.0))), ("even", C(Shot, set_name="dejima", label="Dejima, Nagasaki", perf=lambda c: [
        P(VK + "merchant_v2", 860, 960, 1.4, acts=[(0.6, "nod", None)])])), ("where", C(MapShot, bb=BB_ASIA, draw=map_network(21.7)))]),
    ("L", "S5L03", [(0, C(MapShot, bb=BB_SEASIA, draw=map_blob, perf=host("atlas", 240, 1000, 2.1, "S5L03", acts=[(3.6, "point", None)])))]),
    ("L", "S5L04", [(0, C(Shot, set_name="weavers", label="Coromandel coast", perf=lambda c: [
        P("bengal_1757:weaver", 400 + i * 300, 940, 1.5, acts=[(0.4 * i, "nod", None)]) for i in range(3)])),
                    ("much", C(MapShot, bb=BB_ASIA, draw=map_loop))]),
    ("L", "S5L05", [(0, Wd(VF.S09Zed))]),
]

S6 = [
    ("L", "S6L01", [(0, C(MapShot, bb=BB_ASIA, draw=map_battles))]),
    ("L", "S6L02", [(0, C(Shot, set_name="fort_wall", label="Ambon, 1623", perf=lambda c: [
        P(TK + "prisoner", 200 + i * 220, 900, 2.0, walks=[(0.3, 700 + i * 220)], speed=0.6, faces=[(0.0, {"brows": 0.7})]) for i in range(3)]
        + [P(VK + "soldier_v2", 1500, 890, 2.1, flip=True)]))]),
    ("L", "S6L03", [(0, C(MapShot, bb=(110, -10, 126, 2), draw=map_makassar))]),
    ("L", "S6L04", [(0, C(MapShot, bb=(110, 16, 128, 28), draw=map_taiwan))]),
    ("L", "S6L05", [(0, C(MapShot, bb=BB_KERALA, draw=map_travancore))]),
    ("L", "S6L06", [(0, C(Shot, set_name="kerala_court", label="Marthanda Varma, Maharaja of Travancore", perf=lambda c: [
        P(TK + "marthanda", 960, 920, 2.0, faces=[(0.0, {"brows": -0.3})]), P(TK + "ramayyan_v2", 520, 960, 1.8, acts=[(2.0, "nod", None)]),
        P(TK + "nair4_v2", 1400, 960, 1.8, flip=True)])),
                    ("refused", C(Shot, set_name="kerala_court", perf=lambda c: [P(TK + "marthanda", 900, 940, 2.3, acts=[(0.6, "headshake", None)]),
                                                                          P(TK + "envoy", 1500, 960, 2.2, flip=True, acts=[(0.2, "present", None)])]))]),
    ("L", "S6L07", [(0, C(Shot, set_name="kerala_court", perf=lambda c: [P(TK + "marthanda", 900, 940, 2.3, acts=[(2.6, "headshake", None)]),
                                                                         P(TK + "envoy", 1500, 960, 2.2, flip=True, acts=[(0.2, "point", None)],
                                                                           faces=[(3.0, {"brows": 0.6})])]))]),
    ("L", "S6L08", [(0, Wd(VF.S10Landing))]),
    ("L", "S6L09", [(0, Wd(VF.S11Camp))]),
    ("L", "S6L10", [(0, Wd(B3.Wide))]),
    ("P", 4.0, [(0, C(Shot, set_name="colachel_camp", under=siege_battery, label="Travancore's siege guns", perf=lambda c: [
        P(TK + "nair5_v2", 700, 960, 1.6, flip=True, acts=[(1.0, "flinch", None)]), P(TK + "nair_v2", 1100, 980, 1.6, flip=True, acts=[(1.2, "haul", None)]),
        P(TK + "ramayyan_v2", 1550, 940, 1.7, flip=True, acts=[(0.5, "signal", None)])], over=battery_fx((1.2, 2.6))))]),
    ("P", 2.6, [(0, Wd(B3.Take))]),
    ("P", 3.0, [(0, Wd(B3.Volley))]),
    ("P", 3.0, [(0, C(Shot, set_name="colachel_camp", under=store_dwindle, label="Supplies running low", perf=lambda c: [
        P(TK + "voc_v2", 1560, 960, 1.8, flip=True, faces=[(0.0, {"brows": 0.8})], acts=[(1.2, "shrug", None)])]))]),
    ("L", "S6L11", [(0, Wd(B.ShotD))]),
    ("L", "S6L12", [(0, Wd(VF.S14PikeAsh))]),
    ("L", "S6L13", [(0, Wd(VF.S15Surrender, 2.2))]),
    ("P", 4.0, [(0, C(Shot, set_name="colachel_camp", under=lay_down_arms, label="The garrison surrenders", perf=lambda c: [
        P(TK + "prisoner", 500 + i * 140, 960, 1.6, walks=[(0.2 * i, 800 + i * 60)], speed=0.6, faces=[(0.0, {"brows": 0.7})]) for i in range(3)]
        + [P(TK + "ramayyan_v2", 1560, 940, 1.8, flip=True), P(TK + "nair4_v2", 1760, 960, 1.7, flip=True), P(TK + "nair3_v2", 1360, 900, 1.5, flip=True)]))]),
    ("L", "S6L14", [(0, Wd(VF.S16March)), ("he", Wd(VF.S17Drill))]),
    ("L", "S6L15", [(0, Wd(VF.S18Quill)), ("but", Wd(VF.S18bQuill))]),
    ("L", "S6L16", [(0, C(MapShot, bb=BB_KERALA, draw=map_1753)), ("but", C(MapShot, bb=BB_INDIA, draw=lambda f, d, pj, t: mdot(f, d, pj, 76.27, 9.96, "Cochin: Dutch until 1795", t, 0.2)))]),
]

S7 = [  # serious: no hosts, no jokes, held camera, no gore
    ("L", "S7L01", [(0, C(Shot, set_name="banda_harbour", perf=lambda c: []))]),
    ("L", "S7L02", [(0, C(Custom, set_name="banda_grove", draw=population(99), blur=10)), ("afterwards", C(Custom, set_name="banda_grove", draw=population(1.0), blur=10))]),
    ("L", "S7L03", [(0, C(Shot, set_name="banda_grove", perf=lambda c: [
        P(VK + "banda_man_v2", 400, 960, 1.7, walks=[(0.5, 760)], speed=0.5, props={"prop_l": "bale"}),
        P(VK + "banda_woman_v2", 1000, 950, 1.6, acts=[(1.0, "haul", None)]), P(VK + "banda_man2_v2", 1350, 970, 1.7, faces=[(0.0, {"brows": 0.5})]),
        P(VK + "merchant_v2", 1750, 930, 1.5, flip=True)]))]),
    ("L", "S7L04", [(0, C(Shot, set_name="ocean", under=lambda f, t, s: [f.alpha_composite(V.longboat(t * 1.3 + i, L=320, rowers=4)[0],
                                                                                         (int(200 + i * 520 + 30 * t), 720 + (i % 2) * 60)) for i in range(3)]))]),
    ("L", "S7L05", [(0, C(Shot, set_name="batavia", label="Batavia, 1740", perf=lambda c: [
        P(TK + "chinese", 600, 900, 1.8, walks=[(0.5, 1200)], speed=0.6, faces=[(0.0, {"brows": 0.7})]),
        P(TK + "voc_v2", 400, 900, 1.8, walks=[(0.5, 1000)], speed=0.6), P(TK + "chinese_w", 1600, 880, 1.7, flip=True, faces=[(0.0, {"brows": 0.8})]),
        P(TK + "chinese2", 1780, 890, 1.7, flip=True, faces=[(0.0, {"brows": 0.8})])])),
                    ("rumours", C(Shot, set_name="batavia_dusk", under=lambda f, t, s: V.place(f, t, 900 + 30 * t, 760, L=380, facing=1, water=(70, 60, 60), era=1741),
                           perf=lambda c: [P(TK + "chinese_w", 1500, 890, 1.6, flip=True, faces=[(0.0, {"brows": 0.9})]),
                                           P(TK + "chinese2", 1700, 900, 1.6, flip=True, faces=[(0.0, {"brows": 0.9})])]))]),
    ("L", "S7L06", [(0, C(Shot, set_name="road_inland", over=smoke_over(1400, 600, size=40), tint=((60, 40, 40), 0.15))),
                    ("then", C(Shot, set_name="batavia_dusk", over=smoke_over(1000, 520, n=8, col=(80, 74, 72), size=46), label="9 October 1740"))]),
    ("L", "S7L07", [(0, C(Shot, set_name="interior", tint=((30, 26, 30), 0.15), perf=lambda c: [
        P(TK + "valckenier", 960, 980, 2.0, faces=[(0.0, {"brows": 0.4})]), P(TK + "judge", 420, 960, 1.8), P(TK + "judge", 1500, 960, 1.8, flip=True)]))]),
    ("L", "S7L08", [(0, C(Custom, set_name="interior", draw=ledger_people, blur=12, darken=0.3))]),
    ("L", "S7L09", [(0, C(MapShot, bb=BB_ASIA, draw=map_rulers))]),
]

S8 = [
    ("L", "S8L01", [(0, C(Custom, set_name="interior", draw=red_ledger, blur=12)),
                    ("rivals", C(Shot, set_name="ocean", under=lambda f, t, s: [V.place(f, t + i, 500 + i * 600 + 20 * t, 640, L=260, facing=-1, era=1741) for i in range(2)],
                           label="Rivals: the English East India Company")),
                    ("plenty", C(Shot, set_name="batavia_dusk", under=crates_night, tint=((20, 24, 50), 0.35), perf=lambda c: [
                        P(TK + "valckenier", 1200, 900, 1.8, walks=[(0.3, 1400)], speed=0.5, faces=[(0.0, {"look": 0.8})])]))]),
    ("L", "S8L02", [(0, C(Shot, set_name="interior", perf=lambda c: [P("penny", 760, 980, 2.3, lips=lip(c, "S8L02"), acts=[(1.0, "rub", None)]),
                                                                     P("quill", 1240, 990, 2.3, flip=True)]))]),
    ("L", "S8L03", [(0, C(Shot, set_name="interior", perf=lambda c: [P("penny", 760, 980, 2.3, faces=[(0.0, {"brows": 0.4})]),
                                                                     P("quill", 1240, 990, 2.3, flip=True, lips=lip(c, "S8L03"), acts=[(0.5, "think", None)])]))]),
    ("L", "S8L04", [(0, C(Shot, set_name="amsterdam", label="War with Britain, 1780-84", perf=lambda c: [],
                          under=lambda f, t, s: [V.place(f, t + i, 500 + i * 700, 900, L=500, sails=0.0, facing=1) if False else
                                                 V.place(f, t + i, 500 + i * 700, 900, L=500, facing=1, sea=0.3) for i in range(2)]))]),
    ("L", "S8L05", [(0, C(Custom, set_name="interior", draw=deficit, blur=12))]),
    ("L", "S8L06", [(0, C(Shot, set_name="interior", label="1796: the state takes over", under=table_fx(99), perf=lambda c: [
        P(TK + "judge", 520, 980, 1.8, acts=[(0.6, "present", None)]), P(TK + "valckenier", 1400, 980, 1.8, flip=True, acts=[(1.2, "shrug", None)])])),
                    ("at", C(Shot, set_name="fort_wall", under=flag_lower, label="31 December 1799"))]),
]

S9 = [
    ("L", "S9L01", [(0, C(Custom, set_name="interior", draw=banner_crack, blur=12))]),
    ("L", "S9L02", [(0, C(Shot, set_name="banda_harbour", under=lambda f, t, s: V.place(f, t, 1100, 736, L=600, facing=-1, sea=0.4),
                          tint=((90, 50, 40), 0.18)))]),
    ("L", "S9L03", [(0, C(Shot, set_name="interior", under=coins_fx)), ("not", C(Shot, set_name="banda_grove", perf=lambda c: [
        P(VK + "banda_man_v2", 600, 960, 1.7, walks=[(0.2, 900)], speed=0.5, props={"prop_l": "bale"})]))]),
    ("L", "S9L04", [(0, C(Shot, set_name="banda_quay", tint=((120, 60, 40), 0.15), perf=lambda c: [
        P("atlas", 400, 940, 2.0, faces=[(0.0, {"look": 0.6})]), P("zed", 620, 940, 2.0), P("penny", 960, 940, 2.1, lips=lip(c, "S9L04"), acts=[(0.6, "present", None)]),
        P("quill", 1300, 950, 2.0, flip=True), P("pike", 1560, 940, 2.0, flip=True, acts=[(3.0, "nod", None)])]))]),
    ("P", 3.5, [(0, C(TitleCard, sub="The Company That Had Its Own Army"))]),
]

SEGMENTS = S1 + S2 + S3 + S4 + S5 + S6 + S7 + S8 + S9


# ------------------------------------------------------------------------------------------------ timeline from segments
def word_time(line_id, idx):
    """idx = word index, or a word ("rumours", "but#2" = its second occurrence) to cut on."""
    ws = WORDS.get(line_id, [])
    if isinstance(idx, str):
        word, _, nth = idx.partition("#")
        nth = int(nth or 1)
        hits = [i for i, w in enumerate(ws) if re.sub(r"[^a-z0-9]", "", w[0].lower()).startswith(word.lower())]
        if len(hits) < nth:
            raise SystemExit(f"cut word {idx!r} not found in {line_id}")
        idx = hits[nth - 1]
    if not ws or idx <= 0:
        return 0.0
    idx = min(idx, len(ws) - 1)
    return max(0.0, ws[idx][1] - 0.08)


@lru_cache(maxsize=1)
def plan():
    """[(start, dur, factory, ctx, voices)] where voices = [(line_id, offset within the shot)]."""
    out = []
    t = 0.0
    for kind, ref, shots in SEGMENTS:
        if kind == "L":
            seg_len = LEAD + DUR[ref] + GAP
            cuts = [LEAD + word_time(ref, w) if w else 0.0 for w, _ in shots]
        else:
            seg_len = ref
            cuts = [0.0 for _ in shots]
        cuts = sorted(cuts)
        for i, (w, fac) in enumerate(shots):
            s0 = cuts[i]
            s1 = cuts[i + 1] if i + 1 < len(shots) else seg_len
            ctx = {ref: LEAD - s0} if kind == "L" else {}
            voices = [(ref, LEAD)] if (kind == "L" and i == 0) else []
            out.append((t + s0, s1 - s0, fac, ctx, voices))
        t += seg_len
    return out


_CACHE = {}


def shot_obj(i):
    if i not in _CACHE:
        start, dur, fac, ctx, voices = plan()[i]
        o = fac(ctx)
        o.dur = dur
        if hasattr(o, "obj"):
            o.obj.dur = getattr(o.obj, "dur", dur)
        _CACHE[i] = o
    return _CACHE[i]


def total():
    p = plan()
    return p[-1][0] + p[-1][1]


def frame_at(gt):
    p = plan()
    i = max(k for k, s in enumerate(p) if s[0] <= gt + 1e-9)
    fr = shot_obj(i).frame(gt - p[i][0])
    if fr.mode != "RGB":
        fr = fr.convert("RGB")
    draw_sub(fr, gt)
    return fr


# ------------------------------------------------------------------------------------------------ subtitles, render, mix
_CUES = None


def cues():
    lines = {ln["id"]: ln for ln in json.loads((VOICE / "lines.json").read_text(encoding="utf-8"))["lines"]}
    out = []
    for start, dur, fac, ctx, voices in plan():
        for lid, off in voices:
            tw = lines[lid]["subtitle"].replace("...", "").split()
            rec = WORDS[lid]
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
                out.append((start + off + a, start + off + b + 0.25, " ".join(ch)))
                k += len(ch)
    out.sort()
    for i in range(len(out) - 1):
        if out[i][1] > out[i + 1][0]:
            out[i] = (out[i][0], out[i + 1][0] - 0.02, out[i][2])
    return out


def draw_sub(fr, gt):
    global _CUES
    if _CUES is None:
        _CUES = cues()
    for a, b, text in _CUES:
        if a <= gt < b:
            d = ImageDraw.Draw(fr)
            d.text((960, 1010), text, font=VF._font(50), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(24, 20, 16))
            return


def render_part(i, n, outdir):
    import subprocess
    import imageio_ffmpeg
    nf = int(round(total() * FPS))
    a, b = (i - 1) * nf // n, i * nf // n
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"part_{i:02d}.mp4"
    proc = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", "-g", str(FPS),
                             str(out)], stdin=subprocess.PIPE)
    for k in range(a, b):
        proc.stdin.write(frame_at(k / FPS).tobytes())
        if (k - a) % 48 == 0:
            print(f"part {i}/{n}: {k - a}/{b - a}", flush=True)
    proc.stdin.close()
    proc.wait()
    print(out)


class _T:
    pass


def mix_film(parts, out, music=None):
    import subprocess
    import imageio_ffmpeg
    entries = []
    for start, dur, fac, ctx, voices in plan():
        entries.append((_T, dur, voices))
    VF.TIMELINE = entries
    VF.sound_plan = lambda: [("@surf", 0.0, -24, 40.0), ("wind_steppe_1.wav", 0.0, -30, total())]
    VF.mix(parts, out, music)
    loud = Path(out).with_name("film_loud.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(out), "-c:v", "libx264", "-crf", "21", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(loud)], check=True)
    print(loud)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        for i, (s, d, fac, ctx, v) in enumerate(plan()):
            flag = "  <-- over 14 s" if d > 14.0 else ""
            print(f"{i:3d}  {s:7.2f}  {d:5.2f}  {v}{flag}")
        print("total", round(total(), 1), "s")
    elif cmd == "still":
        i, t = int(sys.argv[2]), float(sys.argv[3])
        out = Path("D:/Temp/cartoon/voc_ep/stills")
        out.mkdir(parents=True, exist_ok=True)
        shot_obj(i).frame(t).convert("RGB").save(out / f"{i:03d}_{t:.1f}.jpg", quality=85)
        print(out / f"{i:03d}_{t:.1f}.jpg")
    elif cmd == "sheet":
        import traceback
        p = plan()
        cells = []
        for i in range(len(p)):
            try:
                im = shot_obj(i).frame(min(p[i][1] * 0.6, p[i][1] - 0.1)).convert("RGB")
            except Exception:
                print("SHOT", i, "FAILED")
                traceback.print_exc()
                im = Image.new("RGB", (W, H), (200, 0, 0))
            cells.append(im.resize((384, 216)))
        cols = 6
        sheet = Image.new("RGB", (384 * cols, 236 * ((len(cells) + cols - 1) // cols)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, im in enumerate(cells):
            x, y = (i % cols) * 384, (i // cols) * 236
            sheet.paste(im, (x, y))
            d.text((x + 4, y + 218), str(i), fill=(255, 255, 255))
        out = Path("D:/Temp/cartoon/voc_ep/sheet.jpg")
        sheet.save(out, quality=82)
        print(out, len(cells))
    elif cmd == "render":
        i, n = map(int, sys.argv[2].split("/"))
        render_part(i, n, sys.argv[3])
    elif cmd == "mix":
        mix_film(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
