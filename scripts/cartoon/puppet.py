"""Code-drawn cut-out characters for The Wider World cartoon format (no AI images, no drawing by hand).

A character = a spec (colours, hat, hair, beard, costume details). A pose = how it looks this frame (brows, eyes, mouth,
arm angles, blink, bob). draw(img, spec, pose, x, y, scale) paints it with its feet at (x, y).
Style: our own design in the limited-animation genre — big round head, large white eyes with pupils, small stout body,
thick dark outline, flat colours with one soft shade. Pillow only; draw on a 2x canvas and downsample for clean edges.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

INK = (34, 28, 30)
OUT = 7                                  # outline width at scale 1 (2x canvas pixels)


@dataclass
class Spec:
    name: str
    skin: tuple = (243, 214, 178)
    coat: tuple = (180, 40, 40)
    trim: tuple = (240, 225, 180)
    trousers: tuple = (240, 236, 222)
    hat: str = "none"                    # none | tricorne | turban | helmet | cap
    hat_color: tuple = (40, 40, 48)
    jewel: tuple | None = None
    hair: str = "none"                   # none | wig | black | grey
    beard: str = "none"                  # none | moustache | short | long
    beard_color: tuple = (40, 34, 30)
    sash: tuple | None = None
    buttons: bool = False
    epaulettes: bool = False
    robe: bool = False                   # long robe instead of coat + trousers
    ruff: bool = False                   # Tudor ruff collar


@dataclass(frozen=True)
class Pose:
    brows: float = 0.0                   # -1 angry .. 0 neutral .. 1 worried
    look: float = 0.0                    # -1 left .. 1 right
    blink: float = 0.0                   # 0 open .. 1 closed
    mouth: str = "closed"                # closed | smile | open | wide | o | frown | grin
    arm_l: float = 15.0                  # degrees from hanging down, + = outwards/up
    arm_r: float = 15.0
    bob: float = 0.0                     # vertical offset in head units (breathing, hops)
    tilt: float = 0.0                    # head sideways offset in head units
    flip: bool = False                   # face left


def _shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def _limb(d, x0, y0, length, width, ang, fill, hand):
    """An arm as a rounded capsule rotated about the shoulder, with a round hand."""
    a = math.radians(ang)
    x1, y1 = x0 + math.sin(a) * length, y0 + math.cos(a) * length
    d.line([(x0, y0), (x1, y1)], fill=INK, width=int(width + 2 * OUT))
    d.ellipse([x0 - (width / 2 + OUT), y0 - (width / 2 + OUT), x0 + width / 2 + OUT, y0 + width / 2 + OUT], fill=INK)
    d.line([(x0, y0), (x1, y1)], fill=fill, width=int(width))
    d.ellipse([x0 - width / 2, y0 - width / 2, x0 + width / 2, y0 + width / 2], fill=fill)
    r = width * 0.62
    d.ellipse([x1 - r - OUT, y1 - r - OUT, x1 + r + OUT, y1 + r + OUT], fill=INK)
    d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=hand)


def draw(img: Image.Image, s: Spec, p: Pose, x: float, y: float, scale: float = 1.0, head_only: bool = False):
    """Paint the character with feet centre at (x, y). One head unit u = 40 px * scale (2x canvas)."""
    u = 40 * scale
    d = ImageDraw.Draw(img)
    sx = -1 if p.flip else 1
    y = y - p.bob * u
    if not head_only:                                                                # the rig draws its own body
        # --- feet and legs
        leg_col = s.coat if s.robe else s.trousers
        for side in (-1, 1):
            fx = x + side * 0.75 * u
            d.rounded_rectangle([fx - 0.55 * u - OUT, y - 1.2 * u - OUT, fx + 0.55 * u + OUT, y + OUT], radius=0.3 * u, fill=INK)
            d.rounded_rectangle([fx - 0.55 * u, y - 1.2 * u, fx + 0.55 * u, y], radius=0.3 * u, fill=leg_col)
            d.ellipse([fx - 0.75 * u - OUT + sx * 0.2 * u, y - 0.45 * u - OUT, fx + 0.75 * u + OUT + sx * 0.2 * u, y + 0.25 * u + OUT], fill=INK)
            d.ellipse([fx - 0.75 * u + sx * 0.2 * u, y - 0.45 * u, fx + 0.75 * u + sx * 0.2 * u, y + 0.25 * u], fill=(50, 40, 38))
        # --- back arm (behind the body)
        sh_y = y - 4.3 * u
        back = (p.arm_r if not p.flip else p.arm_l)
        _limb(d, x + sx * 1.55 * u, sh_y, 2.1 * u, 0.85 * u, sx * back, _shade(s.coat, 0.82), s.skin)
        # --- body
        top, bot = y - 4.9 * u, y - (0.6 if not s.robe else 0.4) * u
        d.rounded_rectangle([x - 1.85 * u - OUT, top - OUT, x + 1.85 * u + OUT, bot + OUT], radius=0.95 * u, fill=INK)
        d.rounded_rectangle([x - 1.85 * u, top, x + 1.85 * u, bot], radius=0.95 * u, fill=s.coat)
        d.rounded_rectangle([x + sx * 0.5 * u - 1.35 * u, top + 0.15 * u, x + sx * 0.5 * u + 1.2 * u, bot - 0.1 * u],
                            radius=0.8 * u, fill=_shade(s.coat, 0.9))                      # one soft shade
        if not s.robe:                                                                    # waistcoat / lapels
            d.polygon([(x - 0.75 * u, top + 0.1 * u), (x + 0.75 * u, top + 0.1 * u), (x + 0.45 * u, bot - 0.3 * u),
                       (x - 0.45 * u, bot - 0.3 * u)], fill=s.trim, outline=INK)
        if s.buttons:
            for k in range(4):
                by = top + (0.75 + 0.75 * k) * u
                d.ellipse([x - 0.14 * u, by - 0.14 * u, x + 0.14 * u, by + 0.14 * u], fill=(212, 175, 55), outline=INK)
        if s.sash:
            d.polygon([(x - 1.7 * u, top + 0.6 * u), (x - 1.1 * u, top + 0.2 * u), (x + 1.8 * u, bot - 1.0 * u), (x + 1.4 * u, bot - 0.4 * u)],
                      fill=s.sash, outline=INK)
        if s.robe:
            d.rectangle([x - 1.3 * u, y - 2.6 * u, x + 1.3 * u, y - 2.25 * u], fill=s.trim, outline=INK)   # belt
        if s.epaulettes:
            for side in (-1, 1):
                ex = x + side * 1.45 * u
                d.ellipse([ex - 0.55 * u, top - 0.15 * u, ex + 0.55 * u, top + 0.35 * u], fill=(222, 184, 64), outline=INK, width=3)
        # --- front arm
        front = (p.arm_l if not p.flip else p.arm_r)
        _limb(d, x - sx * 1.55 * u, sh_y, 2.1 * u, 0.85 * u, -sx * front, s.coat, s.skin)
    # --- head
    hx, hy, r = x + p.tilt * u, y - 7.0 * u, 2.25 * u
    if s.ruff:                                                                       # Tudor ruff under the chin
        for k in range(14):
            ang = math.pi * (0.05 + 0.9 * k / 13)
            cx, cy = hx - math.cos(ang) * 2.0 * u, hy + 1.9 * u + math.sin(ang) * 0.35 * u
            d.ellipse([cx - 0.5 * u, cy - 0.42 * u, cx + 0.5 * u, cy + 0.42 * u], fill=(250, 250, 246), outline=INK, width=3)
    if s.hair in ("wig", "black", "grey", "red"):
        hc = {"wig": (236, 236, 236), "black": (34, 30, 30), "grey": (170, 170, 170), "red": (196, 92, 44)}[s.hair]
        d.ellipse([hx - r * 1.08 - OUT, hy - r * 1.02 - OUT, hx + r * 1.08 + OUT, hy + r * 0.85 + OUT], fill=INK)
        d.ellipse([hx - r * 1.08, hy - r * 1.02, hx + r * 1.08, hy + r * 0.85], fill=hc)
        if s.hair == "wig":                                                          # side curls
            for side in (-1, 1):
                cx = hx + side * r * 1.02
                d.ellipse([cx - 0.45 * u, hy - 0.1 * u, cx + 0.45 * u, hy + 0.75 * u], fill=hc, outline=INK, width=4)
    d.ellipse([hx - r - OUT, hy - r - OUT, hx + r + OUT, hy + r + OUT], fill=INK)
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=s.skin)
    d.ellipse([hx - r * 0.2, hy - r * 0.95, hx + r * 0.95, hy + r * 0.8], fill=_shade(s.skin, 0.95))     # soft shade
    for side in (-1, 1):                                                             # cheeks
        cx = hx + side * 1.15 * u + sx * 0.15 * u
        d.ellipse([cx - 0.36 * u, hy + 0.35 * u, cx + 0.36 * u, hy + 0.7 * u], fill=(236, 160, 150))
    # --- eyes (large whites with pupils; blink squashes them)
    lk = p.look * 0.16 * u + sx * 0.12 * u
    for side in (-1, 1):
        ex, ey = hx + side * 0.82 * u + sx * 0.18 * u, hy - 0.25 * u
        eh = 0.62 * u * (1 - 0.9 * p.blink)
        d.ellipse([ex - 0.5 * u, ey - eh, ex + 0.5 * u, ey + eh], fill=(255, 255, 255), outline=INK, width=4)
        if p.blink < 0.6:
            d.ellipse([ex + lk - 0.24 * u, ey - 0.24 * u + 0.08 * u, ex + lk + 0.24 * u, ey + 0.24 * u + 0.08 * u], fill=INK)
            d.ellipse([ex + lk - 0.06 * u, ey - 0.06 * u, ex + lk + 0.04 * u, ey + 0.04 * u], fill=(255, 255, 255))
        # brows: angry slants inwards-down, worried slants inwards-up
        by = ey - 0.85 * u
        inner, outer = (ex - side * 0.35 * u), (ex + side * 0.45 * u)
        dy = 0.32 * u * p.brows
        d.line([(inner, by - dy), (outer, by + dy)], fill=INK, width=int(0.17 * u))
    # --- nose
    nx = hx + sx * 0.25 * u
    d.ellipse([nx - 0.22 * u, hy + 0.3 * u, nx + 0.22 * u, hy + 0.62 * u], fill=_shade(s.skin, 0.84))
    # --- beard / moustache
    if s.beard in ("short", "long"):                                                  # on the face, down to a point
        tip = (0.9 if s.beard == "short" else 1.9) * u
        pts = [(hx - r * 0.93, hy + 0.15 * r), (hx - r * 0.75, hy + 0.7 * r), (hx - r * 0.35, hy + r + 0.25 * u),
               (hx, hy + r + tip), (hx + r * 0.35, hy + r + 0.25 * u), (hx + r * 0.75, hy + 0.7 * r), (hx + r * 0.93, hy + 0.15 * r),
               (hx + r * 0.55, hy + 0.55 * r), (hx, hy + 0.62 * r), (hx - r * 0.55, hy + 0.55 * r)]
        d.polygon(pts, fill=s.beard_color, outline=INK, width=4)
    # --- mouth
    mx, my = hx + sx * 0.25 * u, hy + 1.15 * u
    m = p.mouth
    if m == "closed":
        d.line([(mx - 0.38 * u, my), (mx + 0.38 * u, my)], fill=INK, width=int(0.13 * u))
    elif m == "smile":
        d.arc([mx - 0.5 * u, my - 0.45 * u, mx + 0.5 * u, my + 0.25 * u], 20, 160, fill=INK, width=int(0.13 * u))
    elif m == "grin":
        d.chord([mx - 0.6 * u, my - 0.4 * u, mx + 0.6 * u, my + 0.45 * u], 0, 180, fill=(255, 255, 255), outline=INK, width=5)
    elif m == "frown":
        d.arc([mx - 0.45 * u, my - 0.05 * u, mx + 0.45 * u, my + 0.55 * u], 200, 340, fill=INK, width=int(0.13 * u))
    elif m in ("open", "wide", "o"):
        w, h = {"open": (0.42, 0.26), "wide": (0.55, 0.42), "o": (0.24, 0.3)}[m]
        d.ellipse([mx - w * u, my - h * u, mx + w * u, my + h * u], fill=(110, 40, 46), outline=INK, width=5)
    if s.beard == "moustache" or s.beard in ("short", "long"):
        for side in (-1, 1):
            d.chord([mx - 0.05 * u + (side < 0) * -0.6 * u, my - 0.42 * u, mx + 0.05 * u + (side > 0) * 0.6 * u, my + 0.05 * u],
                    180, 360, fill=s.beard_color, outline=INK, width=3)
    # --- hats
    if s.hat == "tricorne":
        d.polygon([(hx - 2.7 * u, hy - 1.4 * u), (hx, hy - 3.3 * u), (hx + 2.7 * u, hy - 1.4 * u), (hx + 1.6 * u, hy - 1.75 * u),
                   (hx, hy - 1.35 * u), (hx - 1.6 * u, hy - 1.75 * u)], fill=s.hat_color, outline=INK)
        d.line([(hx - 2.5 * u, hy - 1.5 * u), (hx, hy - 3.15 * u), (hx + 2.5 * u, hy - 1.5 * u)], fill=(212, 175, 55), width=int(0.12 * u))
        d.ellipse([hx + 0.9 * u, hy - 2.45 * u, hx + 1.45 * u, hy - 1.9 * u], fill=(240, 240, 240), outline=INK, width=3)   # cockade
    elif s.hat == "turban":
        d.ellipse([hx - 2.45 * u - OUT, hy - 3.6 * u - OUT, hx + 2.45 * u + OUT, hy - 0.75 * u + OUT], fill=INK)
        d.ellipse([hx - 2.45 * u, hy - 3.6 * u, hx + 2.45 * u, hy - 0.75 * u], fill=s.hat_color)
        for k in range(3):                                                           # wraps
            d.arc([hx - 2.3 * u, hy - 3.3 * u + k * 0.55 * u, hx + 2.3 * u, hy - 1.1 * u + k * 0.25 * u], 200, 340,
                  fill=_shade(s.hat_color, 0.75), width=int(0.12 * u))
        if s.jewel:
            jx, jy = hx, hy - 2.15 * u
            d.ellipse([jx - 0.4 * u, jy - 0.4 * u, jx + 0.4 * u, jy + 0.4 * u], fill=s.jewel, outline=INK, width=4)
            d.polygon([(jx, jy - 0.4 * u), (jx - 0.25 * u, jy - 1.6 * u), (jx + 0.35 * u, jy - 1.3 * u)], fill=(245, 245, 245), outline=INK)  # plume
    elif s.hat == "helmet":
        d.chord([hx - 2.35 * u, hy - 3.2 * u, hx + 2.35 * u, hy + 0.6 * u], 180, 360, fill=s.hat_color, outline=INK, width=OUT)
        d.polygon([(hx - 0.15 * u, hy - 3.2 * u), (hx, hy - 3.9 * u), (hx + 0.15 * u, hy - 3.2 * u)], fill=s.hat_color, outline=INK)
    elif s.hat == "capotain":                                                       # tall Tudor/Jacobean merchant hat
        d.rounded_rectangle([hx - 2.9 * u, hy - 1.75 * u, hx + 2.9 * u, hy - 1.25 * u], radius=0.2 * u, fill=s.hat_color, outline=INK, width=OUT)
        d.polygon([(hx - 1.7 * u, hy - 1.6 * u), (hx - 1.35 * u, hy - 4.1 * u), (hx + 1.35 * u, hy - 4.1 * u), (hx + 1.7 * u, hy - 1.6 * u)],
                  fill=s.hat_color, outline=INK)
        d.rectangle([hx - 1.62 * u, hy - 2.1 * u, hx + 1.62 * u, hy - 1.75 * u], fill=(150, 120, 60))
    elif s.hat == "crown":
        pts = [(hx - 1.6 * u, hy - 1.7 * u), (hx - 1.7 * u, hy - 3.3 * u), (hx - 0.9 * u, hy - 2.5 * u), (hx, hy - 3.6 * u),
               (hx + 0.9 * u, hy - 2.5 * u), (hx + 1.7 * u, hy - 3.3 * u), (hx + 1.6 * u, hy - 1.7 * u)]
        d.polygon(pts, fill=(232, 190, 60), outline=INK)
        for jx in (-0.9, 0, 0.9):
            d.ellipse([hx + jx * u - 0.22 * u, hy - 2.25 * u, hx + jx * u + 0.22 * u, hy - 1.85 * u], fill=(200, 30, 60), outline=INK, width=3)
    elif s.hat == "cap":
        d.chord([hx - 2.3 * u, hy - 2.9 * u, hx + 2.3 * u, hy - 0.2 * u], 180, 360, fill=s.hat_color, outline=INK, width=OUT)


# ------------------------------------------------------------------------------------------------- the cast
CAST = {
    "nawab": Spec("Siraj ud-Daulah", skin=(214, 168, 120), coat=(36, 120, 86), trim=(232, 196, 92), robe=True,
                  hat="turban", hat_color=(240, 236, 226), jewel=(200, 30, 60), beard="moustache", sash=(232, 196, 92)),
    "clive": Spec("Robert Clive", coat=(190, 36, 40), trim=(245, 240, 225), hat="tricorne", hat_color=(32, 32, 40),
                  hair="wig", buttons=True, epaulettes=True, sash=(40, 70, 150)),
    "mir_jafar": Spec("Mir Jafar", skin=(205, 160, 116), coat=(120, 60, 110), trim=(220, 190, 120), robe=True,
                      hat="turban", hat_color=(230, 120, 40), beard="long", beard_color=(150, 150, 150)),
    "queen": Spec("Elizabeth I", skin=(248, 228, 214), coat=(200, 160, 60), trim=(150, 30, 50), robe=True, hat="crown",
                  hair="red", ruff=True, sash=(150, 30, 50)),
    "merchant": Spec("London merchant", coat=(40, 40, 46), trim=(230, 226, 214), hat="capotain", hat_color=(30, 30, 34),
                     ruff=True, beard="short", beard_color=(110, 74, 44)),
    "merchant2": Spec("London merchant", skin=(236, 200, 166), coat=(70, 50, 40), trim=(230, 226, 214), hat="capotain",
                      hat_color=(46, 36, 30), ruff=True, beard="moustache", beard_color=(60, 40, 30)),
    "redcoat": Spec("Company soldier", coat=(196, 40, 44), trim=(245, 245, 240), hat="tricorne", hat_color=(30, 30, 36), buttons=True),
    "sepoy": Spec("Nawab's soldier", skin=(210, 165, 118), coat=(60, 90, 160), trim=(230, 230, 230), robe=True,
                  hat="helmet", hat_color=(150, 156, 166), beard="moustache"),
    "jahangir": Spec("Emperor Jahangir", skin=(206, 160, 116), coat=(214, 176, 72), trim=(150, 40, 60), robe=True, hat="turban",
                     hat_color=(240, 232, 214), jewel=(190, 30, 60), beard="short", beard_color=(40, 34, 30), sash=(150, 40, 60)),
    "roe": Spec("Sir Thomas Roe", skin=(240, 210, 180), coat=(40, 40, 60), trim=(236, 232, 220), hat="capotain", hat_color=(30, 30, 36),
                beard="short", beard_color=(120, 80, 50), ruff=True),
    "shah_alam": Spec("Emperor Shah Alam II", skin=(210, 166, 124), coat=(236, 226, 200), trim=(200, 160, 60), robe=True, hat="turban",
                      hat_color=(214, 176, 72), jewel=(40, 120, 70), beard="long", beard_color=(70, 64, 60), sash=(200, 160, 60)),
    "jagat_seth": Spec("Jagat Seth banker", skin=(208, 160, 116), coat=(244, 238, 222), trim=(214, 176, 72), robe=True, hat="turban",
                       hat_color=(200, 60, 50), beard="moustache", beard_color=(40, 34, 30)),
    "csepoy": Spec("Company sepoy", skin=(200, 150, 104), coat=(196, 40, 44), trim=(245, 245, 240), hat="turban",
                   hat_color=(40, 44, 70), beard="moustache", buttons=True),
}


def sheet(path: str):
    """Character sheet: the cast in a row, then the nawab's expressions."""
    W, H = 3840, 2160
    img = Image.new("RGB", (W, H), (250, 247, 240))
    for i, k in enumerate(CAST):
        draw(img, CAST[k], Pose(arm_l=20, arm_r=-10 if k != "clive" else 120, mouth="smile"), 420 + i * 750, 1000, 1.6)
    exprs = [("neutral", Pose()), ("angry", Pose(brows=-1, mouth="frown", arm_l=60)), ("worried", Pose(brows=1, mouth="o", look=-1)),
             ("shocked", Pose(brows=1, mouth="wide", arm_l=150, arm_r=150)), ("happy", Pose(mouth="grin", arm_l=40)),
             ("blink", Pose(blink=1, mouth="closed"))]
    for i, (_, p) in enumerate(exprs):
        draw(img, CAST["nawab"], p, 360 + i * 620, 2050, 1.15)
    img.resize((W // 2, H // 2), Image.LANCZOS).save(path)


if __name__ == "__main__":
    import sys
    sheet(sys.argv[1] if len(sys.argv) > 1 else "cast_sheet.png")
