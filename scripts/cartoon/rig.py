"""Character engine (Cartoon Engine V2, Phase 1): a shared bone rig for every character.

Bones: root (hips) -> spine (lean) -> neck/head (tilt, turn); shoulders -> upper arm -> forearm -> hand (+ held prop);
hips -> thigh -> shin -> foot. A Pose holds bone angles in degrees (0 = hanging/standing straight; + = towards the facing
direction), squash/stretch, and a Face (brows, eyes, blink, mouth shape A-H/X from Rhubarb, or an expression mouth).
draw_character() paints one frame of one character on a 2x RGBA tile and returns it at 1x with its ground anchor.

Characters: permanent hosts (Atlas, Penny, Private Pike, Quill, Stampy: culturally neutral, same in every episode) and
historical casts built from puppet.Spec (heads from puppet.draw(head_only=True)). Same rig, same motions for all.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import lru_cache

from PIL import Image, ImageDraw

import puppet as P

INK = (34, 28, 30)
OUT = 7
SKIN = (236, 196, 150)


# ------------------------------------------------------------------------------------------------ pose data
@dataclass(frozen=True)
class Face:
    brows: float = 0.0          # -1 angry .. 1 worried/raised
    look: float = 0.0           # -1 .. 1 (pupils)
    blink: float = 0.0          # 0 open .. 1 shut
    mouth: str = "X"            # Rhubarb A-H, X; or smile | grin | frown | worried | o | wide | smirk
    bulge: float = 1.0          # eye size (shock > 1)


@dataclass(frozen=True)
class Pose:
    lean: float = 0.0           # spine, + forward
    head: float = 0.0           # head tilt
    sh_l: float = 12.0          # shoulder (upper arm) angles; "l" = the arm on the facing side
    el_l: float = 0.0           # elbow bend (+ bends forward/up)
    sh_r: float = 12.0
    el_r: float = 0.0
    th_l: float = 0.0           # thighs; + forward
    kn_l: float = 0.0           # knees; + bends back (natural)
    th_r: float = 0.0
    kn_r: float = 0.0
    y: float = 0.0              # root lift in head units (jumps, bob)
    sq: float = 1.0             # squash (<1) / stretch (>1) of the whole body
    rot: float = 0.0            # whole-body rotation (falls), degrees
    face: Face = Face()
    prop_l: str = ""            # prop held in the facing-side hand
    prop_r: str = ""


# ------------------------------------------------------------------------------------------------ characters
@dataclass
class Char:
    key: str
    kind: str = "human"         # human | coin | owl
    coat: tuple = (36, 140, 140)
    sleeve: tuple | None = None
    legs: tuple = (70, 64, 60)
    boots: tuple = (96, 62, 40)
    hand: tuple = SKIN
    leg_len: float = 1.0        # thigh = shin = leg_len * 0.75 u
    arm_len: float = 1.0
    torso_h: float = 3.4
    spec: P.Spec | None = None  # historical characters: head drawn by puppet.py
    host: str = ""              # host key for the custom head/torso drawers


def _seg(d, a, b, w, fill, outline_pass):
    if outline_pass:
        d.line([a, b], fill=INK, width=int(w + 2 * OUT))
        for (x, y) in (a, b):
            r = w / 2 + OUT
            d.ellipse([x - r, y - r, x + r, y + r], fill=INK)
    else:
        d.line([a, b], fill=fill, width=int(w))
        for (x, y) in (a, b):
            r = w / 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _rot(dx, dy, ang):
    a = math.radians(ang)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def _down(x, y, ang, length, f):
    """Point `length` below (x, y) after rotating by ang degrees towards facing direction f."""
    a = math.radians(ang)
    return x + f * math.sin(a) * length, y + math.cos(a) * length


# ---------------------------------------------------------------------------------------- faces and heads
def face_eyes(d, cx, cy, u, f: Face, gap=0.82, size=1.0, facing=1):
    s = size * f.bulge
    for side in (-1, 1):
        ex, ey = cx + side * gap * u + facing * 0.12 * u, cy
        eh = 0.62 * u * s * (1 - 0.92 * f.blink)
        d.ellipse([ex - 0.5 * u * s, ey - eh, ex + 0.5 * u * s, ey + eh], fill=(255, 255, 255), outline=INK, width=4)
        if f.blink < 0.6:
            px = ex + (f.look * 0.17 + facing * 0.06) * u
            pr = 0.24 * u * min(1.0, size)
            d.ellipse([px - pr, ey - pr * 0.7, px + pr, ey + pr * 1.3], fill=INK)
            d.ellipse([px - 0.06 * u, ey - 0.07 * u, px + 0.05 * u, ey + 0.04 * u], fill=(255, 255, 255))
        by = ey - 0.88 * u * s
        inner, outer = ex - side * 0.35 * u, ex + side * 0.45 * u
        dy = 0.33 * u * f.brows
        d.line([(inner, by - dy), (outer, by + dy)], fill=INK, width=int(0.16 * u))


RHUBARB = {"A": ("line", 0.36, 0.0), "B": ("open", 0.34, 0.12), "C": ("open", 0.4, 0.24), "D": ("open", 0.5, 0.38),
           "E": ("open", 0.32, 0.3), "F": ("open", 0.2, 0.2), "G": ("teeth", 0.38, 0.12), "H": ("open", 0.38, 0.22),
           "X": ("line", 0.34, 0.0)}


def face_mouth(d, mx, my, u, m):
    if m in RHUBARB:
        kind, w, h = RHUBARB[m]
        if kind == "line":
            d.line([(mx - w * u, my), (mx + w * u, my)], fill=INK, width=int(0.13 * u))
        else:
            d.ellipse([mx - w * u, my - h * u, mx + w * u, my + h * u], fill=(110, 40, 46), outline=INK, width=5)
            if kind == "teeth" or h > 0.2:
                d.rectangle([mx - w * 0.7 * u, my - h * u + 2, mx + w * 0.7 * u, my - h * 0.45 * u], fill=(255, 255, 255))
        return
    if m == "smile":
        d.arc([mx - 0.5 * u, my - 0.45 * u, mx + 0.5 * u, my + 0.25 * u], 20, 160, fill=INK, width=int(0.13 * u))
    elif m == "grin":
        d.chord([mx - 0.62 * u, my - 0.42 * u, mx + 0.62 * u, my + 0.48 * u], 0, 180, fill=(255, 255, 255), outline=INK, width=5)
    elif m == "frown":
        d.arc([mx - 0.45 * u, my - 0.02 * u, mx + 0.45 * u, my + 0.55 * u], 200, 340, fill=INK, width=int(0.13 * u))
    elif m == "worried":
        d.line([(mx - 0.4 * u, my + 0.1 * u), (mx - 0.1 * u, my - 0.05 * u), (mx + 0.15 * u, my + 0.1 * u), (mx + 0.4 * u, my - 0.02 * u)],
               fill=INK, width=int(0.12 * u))
    elif m == "smirk":
        d.arc([mx - 0.15 * u, my - 0.45 * u, mx + 0.6 * u, my + 0.12 * u], 20, 120, fill=INK, width=int(0.13 * u))
    elif m in ("o", "wide"):
        w, h = (0.24, 0.32) if m == "o" else (0.58, 0.5)
        d.ellipse([mx - w * u, my - h * u, mx + w * u, my + h * u], fill=(110, 40, 46), outline=INK, width=5)


def _shade(c, k=0.8):
    return tuple(int(v * k) for v in c[:3])


def _tint(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


def _cheeks(d, cx, cy, u):
    for side in (-1, 1):
        x = cx + side * 1.15 * u
        d.ellipse([x - 0.36 * u, cy + 0.35 * u, x + 0.36 * u, cy + 0.7 * u], fill=(236, 160, 150))


def _ball(d, cx, cy, r, fill, shade=True):
    """Outlined disc with cel shading (light from the upper left) and a small highlight."""
    d.ellipse([cx - r - OUT, cy - r - OUT, cx + r + OUT, cy + r + OUT], fill=INK)
    if not shade:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
        return
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_shade(fill, 0.8))
    d.ellipse([cx - r, cy - r, cx + r * 0.84, cy + r * 0.84], fill=fill)
    hr = r * 0.22
    d.ellipse([cx - r * 0.55 - hr, cy - r * 0.6 - hr * 0.6, cx - r * 0.55 + hr, cy - r * 0.6 + hr * 0.6], fill=_tint(fill, 0.35))


def _ear(d, x, y, u, skin):
    d.ellipse([x - 0.5 * u - OUT, y - 0.6 * u - OUT, x + 0.5 * u + OUT, y + 0.6 * u + OUT], fill=INK)
    d.ellipse([x - 0.5 * u, y - 0.6 * u, x + 0.5 * u, y + 0.6 * u], fill=_shade(skin, 0.9))
    d.ellipse([x - 0.22 * u, y - 0.3 * u, x + 0.22 * u, y + 0.3 * u], fill=_shade(skin, 0.75))


def _nose(d, x, y, u, skin, r=0.38):
    d.ellipse([x - r * u - 4, y - r * 0.85 * u - 4, x + r * u + 4, y + r * 0.85 * u + 4], fill=INK)
    d.ellipse([x - r * u, y - r * 0.85 * u, x + r * u, y + r * 0.85 * u], fill=_shade(skin, 0.92))
    d.ellipse([x - r * 0.55 * u, y - r * 0.6 * u, x + r * 0.1 * u, y - r * 0.05 * u], fill=_tint(skin, 0.3))


def head_atlas(d, cx, cy, u, f: Face, facing):
    hair = (110, 70, 40)
    _ear(d, cx - facing * 2.1 * u, cy + 0.2 * u, u, SKIN)
    _ball(d, cx, cy, 2.25 * u, SKIN)
    for side in (-1, 1):                                                       # sideburns under the hat
        d.polygon([(cx + side * 2.15 * u, cy - 1.0 * u), (cx + side * 1.6 * u, cy - 1.3 * u), (cx + side * 1.75 * u, cy + 0.2 * u),
                   (cx + side * 2.1 * u, cy + 0.1 * u)], fill=hair)
    face_eyes(d, cx, cy - 0.15 * u, u, f, gap=0.8, facing=facing)
    _cheeks(d, cx, cy + 0.15 * u, u)
    nx = cx + facing * 0.3 * u
    face_mouth(d, nx - facing * 0.05 * u, cy + 1.45 * u, u, f.mouth)
    for side in (-1, 1):                                                       # explorer's moustache
        mx = nx + side * 0.5 * u
        d.ellipse([mx - 0.62 * u - 4, cy + 0.72 * u - 4, mx + 0.62 * u + 4, cy + 1.18 * u + 4], fill=INK)
        d.ellipse([mx - 0.62 * u, cy + 0.72 * u, mx + 0.62 * u, cy + 1.18 * u], fill=hair)
    _nose(d, nx, cy + 0.55 * u, u, SKIN)
    hat, band = (204, 168, 110), (110, 76, 44)                                 # safari hat with goggles on the band
    d.ellipse([cx - 3.3 * u - OUT, cy - 2.25 * u - OUT, cx + 3.3 * u + OUT, cy - 1.15 * u + OUT], fill=INK)
    d.ellipse([cx - 3.3 * u, cy - 2.25 * u, cx + 3.3 * u, cy - 1.15 * u], fill=_shade(hat, 0.86))
    d.chord([cx - 2.0 * u - OUT, cy - 4.4 * u - OUT, cx + 2.0 * u + OUT, cy - 0.6 * u + OUT], 180, 360, fill=INK)
    d.chord([cx - 2.0 * u, cy - 4.4 * u, cx + 2.0 * u, cy - 0.6 * u], 180, 360, fill=hat)
    d.chord([cx - 1.6 * u, cy - 4.2 * u, cx - 0.2 * u, cy - 1.6 * u], 180, 270, fill=_tint(hat, 0.25))
    d.rectangle([cx - 2.0 * u, cy - 3.0 * u, cx + 2.0 * u, cy - 2.55 * u], fill=band)
    for k in (-0.55, 0.65):
        gx, gy = cx + facing * k * u, cy - 2.78 * u
        d.ellipse([gx - 0.55 * u, gy - 0.48 * u, gx + 0.55 * u, gy + 0.48 * u], fill=(184, 146, 64), outline=INK, width=5)
        d.ellipse([gx - 0.38 * u, gy - 0.32 * u, gx + 0.38 * u, gy + 0.32 * u], fill=(150, 205, 222))
        d.ellipse([gx - 0.25 * u, gy - 0.24 * u, gx - 0.05 * u, gy - 0.06 * u], fill=(235, 248, 252))


def head_pike(d, cx, cy, u, f: Face, facing):
    skin = (240, 200, 168)
    _ear(d, cx - facing * 2.05 * u, cy + 0.3 * u, u, skin)
    _ball(d, cx, cy, 2.2 * u, skin)
    face_eyes(d, cx, cy - 0.1 * u, u, f, size=1.1, facing=facing)
    nx = cx + facing * 0.35 * u
    face_mouth(d, nx - facing * 0.1 * u, cy + 1.4 * u, u, f.mouth)
    _nose(d, nx, cy + 0.62 * u, u, (236, 170, 150), r=0.55)                    # the big unlucky nose
    blk, red = (36, 34, 40), (200, 40, 44)                                     # tall shako with a plume
    d.polygon([(cx - 1.95 * u - OUT, cy - 1.15 * u + OUT), (cx + 1.95 * u + OUT, cy - 1.15 * u + OUT), (cx + 2.2 * u + OUT, cy - 4.2 * u - OUT),
               (cx - 2.2 * u - OUT, cy - 4.2 * u - OUT)], fill=INK)
    d.polygon([(cx - 1.95 * u, cy - 1.15 * u), (cx + 1.95 * u, cy - 1.15 * u), (cx + 2.2 * u, cy - 4.2 * u), (cx - 2.2 * u, cy - 4.2 * u)], fill=blk)
    d.polygon([(cx - 1.6 * u, cy - 1.3 * u), (cx - 1.1 * u, cy - 1.3 * u), (cx - 1.3 * u, cy - 4.0 * u), (cx - 1.85 * u, cy - 4.0 * u)], fill=(62, 60, 68))
    d.rectangle([cx - 2.18 * u, cy - 4.25 * u, cx + 2.18 * u, cy - 3.85 * u], fill=(212, 176, 70))
    d.polygon([(cx + facing * 0.0 * u, cy - 1.15 * u), (cx + facing * 2.6 * u, cy - 0.85 * u), (cx + facing * 1.9 * u, cy - 1.5 * u)], fill=blk, outline=INK)
    px, py = cx + facing * 0.3 * u, cy - 2.55 * u                               # brass plate
    d.polygon([(px, py - 0.75 * u), (px + 0.6 * u, py), (px, py + 0.75 * u), (px - 0.6 * u, py)], fill=(222, 186, 80), outline=INK)
    plx = cx + facing * 0.9 * u
    d.ellipse([plx - 0.42 * u, cy - 5.5 * u, plx + 0.42 * u, cy - 4.1 * u], fill=red, outline=INK, width=5)
    d.ellipse([plx - 0.25 * u, cy - 5.25 * u, plx + 0.17 * u, cy - 4.7 * u], fill=(250, 246, 240))
    if f.brows > 0.5:                                                          # nervous sweat
        sx, sy = cx - facing * 1.9 * u, cy - 0.6 * u
        d.polygon([(sx, sy - 0.5 * u), (sx + 0.28 * u, sy + 0.05 * u), (sx - 0.28 * u, sy + 0.05 * u)], fill=(140, 200, 240))
        d.ellipse([sx - 0.28 * u, sy - 0.2 * u, sx + 0.28 * u, sy + 0.32 * u], fill=(140, 200, 240), outline=(60, 120, 170), width=3)


def head_stampy(d, cx, cy, u, f: Face, facing):
    g = (120, 186, 96)
    for side in (-1, 1):                                                       # big goblin ears
        e = [(cx + side * 1.6 * u, cy - 0.7 * u), (cx + side * 4.0 * u, cy - 2.0 * u), (cx + side * 1.85 * u, cy + 0.9 * u)]
        d.polygon(e, fill=g, outline=INK, width=OUT)
        d.polygon([(cx + side * 2.0 * u, cy - 0.45 * u), (cx + side * 3.4 * u, cy - 1.6 * u), (cx + side * 2.1 * u, cy + 0.45 * u)], fill=(214, 150, 140))
    _ball(d, cx, cy, 2.1 * u, g)
    for k, dx in enumerate((-0.6, 0.0, 0.6)):                                  # tufts of hair
        hx = cx + dx * u
        d.polygon([(hx - 0.35 * u, cy - 1.95 * u), (hx + 0.1 * u, cy - 3.0 * u + k * 0.1 * u), (hx + 0.35 * u, cy - 1.9 * u)], fill=(70, 60, 50), outline=INK)
    face_eyes(d, cx, cy - 0.2 * u, u, f, size=0.95, facing=facing)
    nx = cx + facing * 0.3 * u
    x0, x1 = sorted((nx - facing * 0.35 * u, nx + facing * 1.15 * u))
    d.ellipse([x0 - 4, cy + 0.12 * u - 4, x1 + 4, cy + 0.85 * u + 4], fill=INK)
    d.ellipse([x0, cy + 0.12 * u, x1, cy + 0.85 * u], fill=_shade(g, 0.92))
    d.ellipse([x0 + 0.2 * u, cy + 0.2 * u, x1 - 0.5 * u, cy + 0.42 * u], fill=_tint(g, 0.3))
    face_mouth(d, cx + facing * 0.15 * u, cy + 1.35 * u, u, f.mouth)


HEADS = {"atlas": head_atlas, "pike": head_pike, "stampy": head_stampy}


@lru_cache(maxsize=4096)
def spec_head(key: str, face: Face, flip: bool, s: float):
    """Historical character head from puppet.py (hats, hair, beards), as a 2x RGBA sprite with its centre at (W/2, H/2)."""
    spec = P.CAST[key]
    u = 40 * s
    W, H = int(9 * u), int(9 * u)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mouth = face.mouth
    mouth = {"A": "closed", "X": "closed", "B": "open", "C": "open", "D": "wide", "E": "o", "F": "o", "G": "open", "H": "open",
             "worried": "frown", "smirk": "smile"}.get(mouth, mouth)
    pose = P.Pose(brows=face.brows, look=face.look, blink=face.blink, mouth=mouth, flip=flip)
    P.draw(im, spec, pose, W / 2, H / 2 + 7.0 * u, s, head_only=True)
    return im


# ------------------------------------------------------------------------------------------------ props
def draw_prop(d, kind, x, y, u, ang, facing):
    if kind == "scroll":
        d.rounded_rectangle([x - 0.3 * u, y - 1.4 * u, x + 0.3 * u, y + 0.4 * u], radius=0.25 * u, fill=(244, 230, 196), outline=INK, width=5)
    elif kind == "contract":                                                           # the comically long one
        d.polygon([(x, y - 0.2 * u), (x + facing * 1.4 * u, y - 0.4 * u), (x + facing * 1.8 * u, y + 6.5 * u), (x + facing * 0.2 * u, y + 6.8 * u)],
                  fill=(248, 242, 222), outline=INK)
        for k in range(8):
            yy = y + 0.6 * u + k * 0.7 * u
            d.line([(x + facing * 0.4 * u, yy), (x + facing * 1.3 * u, yy - 0.05 * u)], fill=(160, 150, 130), width=3)
    elif kind == "stamp":
        d.rectangle([x - 0.45 * u, y - 1.3 * u, x + 0.45 * u, y - 0.5 * u], fill=(120, 70, 40), outline=INK, width=4)
        d.rectangle([x - 0.8 * u, y - 0.55 * u, x + 0.8 * u, y - 0.1 * u], fill=(190, 40, 40), outline=INK, width=4)
    elif kind == "sign":
        d.line([(x, y), (x, y - 2.4 * u)], fill=(110, 80, 50), width=int(0.25 * u))
        d.rounded_rectangle([x - 1.6 * u, y - 4.0 * u, x + 1.6 * u, y - 2.3 * u], radius=0.2 * u, fill=(250, 246, 232), outline=INK, width=5)
    elif kind == "pepper":
        d.ellipse([x - 0.35 * u, y - 0.35 * u, x + 0.35 * u, y + 0.35 * u], fill=(40, 30, 26), outline=INK, width=3)
    elif kind == "musket":
        d.line([(x - facing * 0.3 * u, y + 1.6 * u), (x + facing * 0.5 * u, y - 4.2 * u)], fill=(150, 154, 162), width=int(0.22 * u))
        d.line([(x - facing * 0.4 * u, y + 2.2 * u), (x - facing * 0.1 * u, y + 0.2 * u)], fill=(118, 76, 44), width=int(0.5 * u))
        d.line([(x + facing * 0.5 * u, y - 4.2 * u), (x + facing * 0.62 * u, y - 5.2 * u)], fill=(200, 204, 212), width=int(0.12 * u))
    elif kind == "book":
        d.rounded_rectangle([x - 0.9 * u, y - 1.2 * u, x + 0.9 * u, y + 0.3 * u], radius=6, fill=(120, 40, 40), outline=INK, width=5)
        d.rectangle([x - 0.75 * u, y - 1.05 * u, x + 0.6 * u, y + 0.15 * u], fill=(246, 238, 220))
        d.rectangle([x - 0.9 * u, y - 1.2 * u, x - 0.6 * u, y + 0.3 * u], fill=(90, 30, 30))
    elif kind == "map":
        d.polygon([(x - 1.4 * u, y - 1.6 * u), (x + 1.4 * u, y - 1.8 * u), (x + 1.5 * u, y + 0.2 * u), (x - 1.3 * u, y + 0.3 * u)],
                  fill=(238, 222, 180), outline=INK)
        d.line([(x - 0.8 * u, y - 0.9 * u), (x + 0.2 * u, y - 0.4 * u), (x + 0.9 * u, y - 1.1 * u)], fill=(200, 60, 50), width=4)
    elif kind == "seal":
        d.ellipse([x - 0.45 * u, y - 0.45 * u, x + 0.45 * u, y + 0.45 * u], fill=(186, 30, 40), outline=INK, width=4)
    elif kind == "sword":
        d.line([(x, y), (x + facing * 0.2 * u, y - 3.0 * u)], fill=(200, 205, 214), width=int(0.22 * u))
        d.line([(x - 0.5 * u, y - 0.4 * u), (x + 0.5 * u, y - 0.4 * u)], fill=(200, 160, 60), width=int(0.2 * u))


# ------------------------------------------------------------------------------------------------ torso
def draw_torso(d, ch: Char, hx, hy, u, lean, facing, f: Face):
    """Torso from the hips (hx, hy) up, leaning. Coin and owl torsos carry the face."""
    if ch.kind == "coin":
        cx, cy, r = hx, hy - 2.2 * u, 3.4 * u
        gold = (236, 186, 52)
        _ball(d, cx, cy, r, gold)
        d.ellipse([cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8], outline=_shade(gold, 0.78), width=int(0.22 * u))
        for k in range(24):                                                    # milled, embossed rim
            a = k / 24 * 2 * math.pi
            bx, by = cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9
            d.ellipse([bx - 0.09 * u, by - 0.09 * u, bx + 0.09 * u, by + 0.09 * u], fill=_tint(gold, 0.3))
        hat = (30, 28, 34)
        d.rounded_rectangle([cx - 1.55 * u - OUT, cy - r - 3.0 * u - OUT, cx + 1.55 * u + OUT, cy - r + 0.3 * u], radius=0.2 * u, fill=INK)
        d.rounded_rectangle([cx - 1.55 * u, cy - r - 3.0 * u, cx + 1.55 * u, cy - r + 0.2 * u], radius=0.2 * u, fill=hat)
        d.rectangle([cx - 1.2 * u, cy - r - 2.8 * u, cx - 0.8 * u, cy - r - 0.2 * u], fill=(62, 60, 70))
        d.rectangle([cx - 1.55 * u, cy - r - 0.75 * u, cx + 1.55 * u, cy - r - 0.15 * u], fill=(186, 34, 44))
        d.rounded_rectangle([cx - 2.7 * u - OUT, cy - r - 0.05 * u - OUT, cx + 2.7 * u + OUT, cy - r + 0.55 * u + OUT], radius=0.3 * u, fill=INK)
        d.rounded_rectangle([cx - 2.7 * u, cy - r - 0.05 * u, cx + 2.7 * u, cy - r + 0.55 * u], radius=0.3 * u, fill=hat)
        face_eyes(d, cx, cy - 0.55 * u, u, f, size=0.95, facing=facing)
        if f.brows < 0 and f.blink < 0.6:                                      # heavy, smug eyelids
            for side in (-1, 1):
                ex = cx + side * 0.82 * u + facing * 0.12 * u
                d.chord([ex - 0.56 * u, cy - 1.28 * u, ex + 0.56 * u, cy - 0.4 * u], 180, 360, fill=_shade(gold, 0.9), outline=INK, width=4)
        face_mouth(d, cx + facing * 0.2 * u, cy + 1.15 * u, u * 1.5, f.mouth)
        return (cx - r * 0.95, cy + 0.1 * u), (cx + r * 0.95, cy + 0.1 * u), None
    if ch.kind == "owl":
        cx, cy = hx, hy - 2.7 * u
        br, belly = (132, 92, 58), (236, 218, 184)
        for side in (-1, 1):                                                   # ear tufts
            tx = cx + side * 1.9 * u
            d.polygon([(tx - 0.75 * u, cy - 2.7 * u), (tx + side * 0.6 * u, cy - 4.5 * u), (tx + 0.75 * u, cy - 2.5 * u)],
                      fill=_shade(br, 0.85), outline=INK, width=OUT)
        d.ellipse([cx - 2.9 * u - OUT, cy - 3.6 * u - OUT, cx + 2.9 * u + OUT, cy + 3.4 * u + OUT], fill=INK)
        d.ellipse([cx - 2.9 * u, cy - 3.6 * u, cx + 2.9 * u, cy + 3.4 * u], fill=_shade(br, 0.82))
        d.ellipse([cx - 2.9 * u, cy - 3.6 * u, cx + 2.5 * u, cy + 3.0 * u], fill=br)
        d.ellipse([cx - 1.9 * u, cy + 0.3 * u, cx + 1.9 * u, cy + 3.2 * u], fill=belly)
        for row in range(3):                                                   # chest feathers
            for k in range(3 - row % 2):
                fx2 = cx + (k - 1 + 0.5 * (row % 2)) * 0.9 * u
                fy2 = cy + 1.0 * u + row * 0.65 * u
                d.arc([fx2 - 0.35 * u, fy2 - 0.3 * u, fx2 + 0.35 * u, fy2 + 0.3 * u], 20, 160, fill=_shade(belly, 0.75), width=4)
        d.ellipse([cx - 2.3 * u, cy - 2.5 * u, cx + 2.3 * u, cy + 0.3 * u], fill=_tint(br, 0.25))          # face disc
        for side in (-1, 1):
            ex = cx + side * 1.05 * u
            d.ellipse([ex - 0.9 * u, cy - 1.95 * u, ex + 0.9 * u, cy - 0.15 * u], fill=(252, 250, 242))
            if f.blink < 0.6:
                px = ex + (f.look * 0.2 + facing * 0.08) * u
                pr = 0.34 * u * f.bulge
                d.ellipse([px - pr, cy - 1.05 * u - pr, px + pr, cy - 1.05 * u + pr], fill=INK)
                d.ellipse([px - 0.12 * u, cy - 1.3 * u, px + 0.02 * u, cy - 1.16 * u], fill=(255, 255, 255))
            else:
                d.line([(ex - 0.6 * u, cy - 1.05 * u), (ex + 0.6 * u, cy - 1.05 * u)], fill=INK, width=6)
            d.ellipse([ex - 1.0 * u, cy - 2.05 * u, ex + 1.0 * u, cy - 0.05 * u], outline=(40, 34, 30), width=int(0.16 * u))
        d.line([(cx - 0.1 * u, cy - 1.2 * u), (cx + 0.1 * u, cy - 1.2 * u)], fill=(40, 34, 30), width=int(0.14 * u))
        dy = 0.35 * u * f.brows
        for side in (-1, 1):
            d.line([(cx + side * 0.25 * u, cy - 2.25 * u - dy), (cx + side * 1.8 * u, cy - 2.1 * u)], fill=_shade(br, 0.55), width=int(0.2 * u))
        open_ = f.mouth not in ("X", "A", "smile", "smirk", "frown", "worried")
        d.polygon([(cx - 0.38 * u, cy - 0.2 * u), (cx + 0.38 * u, cy - 0.2 * u), (cx + facing * 0.1 * u, cy + (0.95 if open_ else 0.7) * u)],
                  fill=(236, 168, 50), outline=INK)
        if open_:
            d.line([(cx - 0.3 * u, cy + 0.1 * u), (cx + 0.3 * u, cy + 0.1 * u)], fill=INK, width=4)
        mb = (30, 28, 34)                                                      # mortarboard with tassel
        d.chord([cx - 1.7 * u, cy - 4.3 * u, cx + 1.7 * u, cy - 2.4 * u], 180, 360, fill=mb, outline=INK, width=OUT)
        d.polygon([(cx - 2.6 * u, cy - 3.75 * u), (cx + 0.2 * u, cy - 4.55 * u), (cx + 2.6 * u, cy - 3.75 * u), (cx - 0.2 * u, cy - 3.0 * u)],
                  fill=mb, outline=INK)
        d.line([(cx, cy - 3.78 * u), (cx - facing * 2.1 * u, cy - 3.6 * u), (cx - facing * 2.2 * u, cy - 2.4 * u)], fill=(222, 182, 60), width=int(0.13 * u))
        d.ellipse([cx - facing * 2.2 * u - 0.2 * u, cy - 2.5 * u, cx - facing * 2.2 * u + 0.2 * u, cy - 2.0 * u], fill=(222, 182, 60), outline=INK)
        return (cx - 2.6 * u, cy + 0.4 * u), (cx + 2.6 * u, cy + 0.4 * u), None
    # human torso: rounded body, leaning about the hips
    top = ch.torso_h * u
    pts = []
    for (dx, dy) in [(-1.85, 0.4), (1.85, 0.4), (1.85, -top / u), (-1.85, -top / u)]:
        rx, ry = _rot(dx * u, dy * u, lean * facing)
        pts.append((hx + rx, hy + ry))
    cx = sum(p[0] for p in pts) / 4
    cy = sum(p[1] for p in pts) / 4
    rotated = _torso_sprite(ch.key, round(lean * facing), round(u, 3))
    d._image.alpha_composite(rotated, (int(cx - rotated.width / 2), int(cy - rotated.height / 2)))
    sl = (hx + _rot(-1.55 * u, -(top - 0.5 * u), lean * facing)[0], hy + _rot(-1.55 * u, -(top - 0.5 * u), lean * facing)[1])
    sr = (hx + _rot(1.55 * u, -(top - 0.5 * u), lean * facing)[0], hy + _rot(1.55 * u, -(top - 0.5 * u), lean * facing)[1])
    neck = (hx + _rot(0, -top, lean * facing)[0], hy + _rot(0, -top, lean * facing)[1])
    return sl, sr, neck


@lru_cache(maxsize=2048)
def _torso_sprite(key, ang, u):
    ch = get(key)
    top = ch.torso_h * u
    w, h = 3.7 * u, top + 0.4 * u
    body = Image.new("RGBA", (int(w + 4 * OUT), int(h + 4 * OUT)), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bd.rounded_rectangle([OUT, OUT, w + OUT, h + OUT], radius=0.95 * u, fill=INK)
    bd.rounded_rectangle([2 * OUT, 2 * OUT, w, h], radius=0.95 * u - OUT, fill=ch.coat)
    bd.rounded_rectangle([2 * OUT + w * 0.62, 2 * OUT, w, h], radius=0.95 * u - OUT, fill=_shade(ch.coat, 0.84))     # shaded side
    if ch.host == "atlas":
        for xx in (0.32, 0.68):                                                 # backpack straps, belt, pockets
            bd.line([(w * xx, 2 * OUT), (w * xx, h - 1.4 * u)], fill=(96, 64, 38), width=int(0.3 * u))
        bd.rectangle([2 * OUT, h - 1.25 * u, w, h - 0.85 * u], fill=(96, 64, 38))
        bd.rectangle([w / 2 - 0.25 * u, h - 1.3 * u, w / 2 + 0.25 * u, h - 0.8 * u], outline=(220, 186, 90), width=4)
        for xx in (0.16, 0.58):
            bd.rounded_rectangle([w * xx, h * 0.4, w * xx + 0.8 * u, h * 0.4 + 0.7 * u], radius=6, fill=_shade(ch.coat, 0.9), outline=INK, width=3)
        bd.polygon([(w / 2 - 1.2 * u, 2 * OUT), (w / 2 + 1.2 * u, 2 * OUT), (w / 2 + 0.2 * u, 1.5 * u), (w / 2 - 0.3 * u, 1.4 * u)],
                   fill=(196, 44, 40), outline=INK)                             # red neckerchief
    if ch.host == "stampy":
        bd.rectangle([w / 2 - 1.1 * u, 0.4 * u, w / 2 + 1.1 * u, h - 0.5 * u], fill=(240, 236, 220), outline=INK, width=4)
        bd.line([(w / 2, 0.5 * u), (w / 2, h - 0.6 * u)], fill=(180, 40, 40), width=int(0.3 * u))
    if ch.host == "pike":                                                      # white cross-belts, collar, plate
        for (a0, a1) in (((0.05, 0.08), (0.95, 0.85)), ((0.95, 0.08), (0.05, 0.85))):
            bd.line([(w * a0[0], h * a0[1]), (w * a1[0], h * a1[1])], fill=(244, 240, 228), width=int(0.42 * u))
        bd.ellipse([w / 2 - 0.3 * u, h * 0.42, w / 2 + 0.3 * u, h * 0.42 + 0.6 * u], fill=(222, 186, 80), outline=INK, width=3)
        bd.rectangle([2 * OUT, 2 * OUT, w, 0.6 * u], fill=(40, 40, 60))
        bd.rectangle([2 * OUT, h - 0.9 * u, w, h - 0.5 * u], fill=(244, 240, 228))
    if ch.spec is not None:                                                            # historical costume details
        s = ch.spec
        if not s.robe:
            bd.polygon([(w / 2 - 0.75 * u, OUT * 2), (w / 2 + 0.75 * u, OUT * 2), (w / 2 + 0.45 * u, h - 0.3 * u), (w / 2 - 0.45 * u, h - 0.3 * u)],
                       fill=s.trim, outline=INK)
        if s.sash:
            bd.polygon([(OUT * 2, 0.6 * u), (0.7 * u, 0.2 * u), (w, h - 1.0 * u), (w - 0.5 * u, h - 0.4 * u)], fill=s.sash, outline=INK)
        if s.buttons:
            for k in range(4):
                by = (0.75 + 0.7 * k) * u
                bd.ellipse([w / 2 - 0.14 * u, by - 0.14 * u, w / 2 + 0.14 * u, by + 0.14 * u], fill=(212, 175, 55), outline=INK)
        if s.robe:
            bd.rectangle([w / 2 - 1.3 * u, h - 1.6 * u, w / 2 + 1.3 * u, h - 1.25 * u], fill=s.trim, outline=INK)
    return body.rotate(-ang, resample=Image.BILINEAR, expand=True)


# ------------------------------------------------------------------------------------------------ the frame
def draw_character(ch: Char, p: Pose, s: float = 1.0, flip: bool = False):
    """Returns (tile RGBA at 1x, anchor_x, anchor_y): paste so that the anchor sits on the ground point."""
    u = 40 * s
    f = -1 if flip else 1
    Wt, Ht = int((22 if p.rot else 13) * u), int(17 * u)
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gx, gy = Wt / 2, Ht - 1.2 * u                                                      # ground point
    leg = 0.75 * u * ch.leg_len
    hip_y = gy - (2 * leg + 0.35 * u) - p.y * u
    hx = gx
    # legs: back leg first
    legs = []
    for side, th, kn in ((-1, p.th_r, p.kn_r), (1, p.th_l, p.kn_l)):
        hp = (hx + side * 0.75 * u, hip_y)
        knee = _down(*hp, th, leg, f)
        ankle = _down(*knee, th - kn, leg, f)
        legs.append((hp, knee, ankle, side))
    arm_w, leg_w = 0.85 * u, 0.95 * u
    sleeve = ch.sleeve or ch.coat
    for hp, knee, ankle, side in legs:
        for op in (True, False):
            _seg(d, hp, knee, leg_w, ch.legs, op)
            _seg(d, knee, ankle, leg_w, ch.legs, op)
        ax, ay = ankle
        d.ellipse([ax - 0.8 * u - OUT + f * 0.25 * u, ay - 0.35 * u - OUT, ax + 0.8 * u + OUT + f * 0.25 * u, ay + 0.35 * u + OUT], fill=INK)
        d.ellipse([ax - 0.8 * u + f * 0.25 * u, ay - 0.35 * u, ax + 0.8 * u + f * 0.25 * u, ay + 0.35 * u], fill=ch.boots)
    sl, sr, neck = draw_torso(d, ch, hx, hip_y, u, p.lean, f, p.face)
    hands = {}
    arms = {}
    for key, sh_pt, sh, el in (("r", sl if f > 0 else sr, p.sh_r, p.el_r), ("l", sr if f > 0 else sl, p.sh_l, p.el_l)):
        elbow = _down(*sh_pt, sh, 1.05 * u * ch.arm_len, f)
        hand = _down(*elbow, sh + el, 1.0 * u * ch.arm_len, f)
        arms[key] = (sh_pt, elbow, hand)
        hands[key] = (hand, sh + el)

    def arm(key):
        sh_pt, elbow, hand = arms[key]
        for op in (True, False):
            _seg(d, sh_pt, elbow, arm_w, sleeve, op)
            _seg(d, elbow, hand, arm_w, sleeve, op)
        r = 0.55 * u
        d.ellipse([hand[0] - r - OUT, hand[1] - r - OUT, hand[0] + r + OUT, hand[1] + r + OUT], fill=INK)
        d.ellipse([hand[0] - r, hand[1] - r, hand[0] + r, hand[1] + r], fill=ch.hand)
        prop = p.prop_l if key == "l" else p.prop_r
        if prop:
            draw_prop(d, prop, hand[0], hand[1], u, sh + 0, f)

    arm("r")                                                                          # back arm, then head, then front arm
    if neck is not None:
        hc = (neck[0] + _rot(0, -2.0 * u, (p.lean + p.head) * f)[0], neck[1] + _rot(0, -2.0 * u, (p.lean + p.head) * f)[1])
        spr, ox, oy = _head_rot(ch.key, p.face, flip, s, round((p.lean + p.head) * f))
        im.alpha_composite(spr, (int(hc[0] - ox), int(hc[1] - oy)))
    arm("l")
    bb = im.getbbox() or (0, 0, 2, 2)                                                 # work on the character only, not the empty tile
    x0, y0 = max(0, bb[0] - 4), max(0, bb[1] - 4)
    out = im.crop((x0, y0, min(Wt, bb[2] + 4), min(Ht, bb[3] + 4)))
    ax, ay = gx - x0, gy - y0
    if abs(p.sq - 1.0) > 0.015:                                                       # squash/stretch about the feet
        w0, h0 = out.size
        nw, nh = max(2, int(w0 / math.sqrt(p.sq))), max(2, int(h0 * p.sq))
        out = out.resize((nw, nh), Image.BILINEAR)
        ax, ay = ax * nw / w0, ay * nh / h0
    if p.rot:
        w0, h0 = out.size
        out = out.rotate(-p.rot * f, resample=Image.BILINEAR, expand=True)
        dx, dy = _rot(ax - w0 / 2, ay - h0 / 2, p.rot * f)                            # where the foot point went
        ax, ay = out.width / 2 + dx, out.height / 2 + dy
    if out.width % 2 or out.height % 2:
        out = out.crop((0, 0, out.width + out.width % 2, out.height + out.height % 2))
    return out.reduce(2), ax / 2, ay / 2


@lru_cache(maxsize=6000)
def _head_rot(key, face, flip, s, ang):
    ch = get(key)
    f = -1 if flip else 1
    base = spec_head(key, face, flip, s) if ch.spec is not None else _host_head(ch.host, face, f, s)
    bb = base.getbbox() or (0, 0, 2, 2)
    spr = base.crop(bb)
    cx, cy = base.width / 2 - bb[0], base.height / 2 - bb[1]                         # head centre inside the crop
    if not ang:
        return spr, cx, cy
    w0, h0 = spr.size
    out = spr.rotate(-ang, resample=Image.BILINEAR, expand=True)
    dx, dy = _rot(cx - w0 / 2, cy - h0 / 2, ang)
    return out, out.width / 2 + dx, out.height / 2 + dy


@lru_cache(maxsize=4096)
def _host_head(host, face: Face, facing: int, s: float):
    u = 40 * s
    W, H = int(14 * u), int(14 * u)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    HEADS[host](ImageDraw.Draw(im), W / 2, H / 2, u, face, facing)
    return im


# ------------------------------------------------------------------------------------------------ the cast
HOSTS = {
    "atlas": Char("atlas", coat=(190, 150, 100), sleeve=(180, 140, 92), legs=(112, 86, 62), boots=(92, 60, 38), host="atlas",
                  leg_len=1.7, torso_h=3.7),
    "pike": Char("pike", coat=(176, 36, 42), sleeve=(166, 34, 40), legs=(236, 232, 220), boots=(30, 26, 28), host="pike",
                 hand=(240, 200, 168), leg_len=1.75, torso_h=3.6),
    "stampy": Char("stampy", coat=(126, 92, 60), legs=(96, 74, 54), hand=(120, 186, 96), host="stampy", torso_h=3.3, leg_len=1.35),
    "penny": Char("penny", kind="coin", coat=(236, 186, 52), legs=(34, 30, 30), boots=(24, 22, 24), hand=(255, 255, 255), leg_len=1.4,
                  arm_len=1.05),
    "quill": Char("quill", kind="owl", coat=(132, 92, 58), legs=(236, 168, 50), boots=(236, 168, 50), hand=(132, 92, 58), leg_len=0.8),
}


def from_spec(key: str) -> Char:
    s = P.CAST[key]
    return Char(key, coat=s.coat, legs=s.coat if s.robe else s.trousers, hand=s.skin, spec=s,
                boots=(50, 40, 38), leg_len=1.4 if s.robe else 1.65, torso_h=3.6)


def get(key: str) -> Char:
    return HOSTS[key] if key in HOSTS else from_spec(key)
