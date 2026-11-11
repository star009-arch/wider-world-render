"""Natural-style characters (owner feedback 11 Nov 2026: no big chibi heads; natural faces, proportions and colours).

Same skeleton and Pose as rig.py, so every motion (walks with planted feet, gestures, lip-sync) works unchanged.
Proportions: head ~1/6 of height. Faces: oval head, ears, hair, small eyes with lids, brows, nose, lips.
Look: natural skin tones, muted costume colours, two-tone cel shading, thin dark-brown outlines.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw


def _dark(c, k=0.55):
    return tuple(int(v * k) for v in c[:3])


def _rot(dx, dy, ang):
    a = math.radians(ang)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def _down(x, y, ang, length, f):
    a = math.radians(ang)
    return x + f * math.sin(a) * length, y + math.cos(a) * length


def rot_sprite(img, pivot, ang):
    """Rotate img by ang degrees (clockwise, y down) about pivot; returns (image, new pivot position)."""
    if not ang:
        return img, pivot
    w0, h0 = img.size
    out = img.rotate(-ang, resample=Image.BILINEAR, expand=True)
    dx, dy = _rot(pivot[0] - w0 / 2, pivot[1] - h0 / 2, ang)
    return out, (out.width / 2 + dx, out.height / 2 + dy)


@dataclass(frozen=True)
class Look:
    skin: tuple = (226, 184, 150)
    hair: tuple = (78, 54, 40)
    hair_style: str = "short"       # short | wig | swept | none | long
    facial: str = ""                # moustache | beard | stubble
    hat: str = ""                   # fieldcap | helmet | tricorn | turban | bicorne
    hat_col: tuple = (120, 100, 70)
    coat: tuple = (60, 104, 112)
    coat2: tuple = (230, 224, 210)  # shirt / waistcoat / facings
    trousers: tuple = (78, 74, 70)
    shoes: tuple = (58, 42, 34)
    sash: tuple | None = None
    belt: tuple | None = None
    buttons: bool = False
    robe: float = 0.0               # robe length below the hips, in head units (0 = coat and trousers)
    lapel: tuple | None = None
    eye: tuple = (70, 50, 36)
    glasses: str = ""               # spectacles | monocle
    lashes: bool = False
    lip: tuple | None = None
    earring: tuple | None = None
    tie: tuple | None = None
    vest: tuple | None = None       # waistcoat shown in the coat opening
    build: float = 1.0              # shoulder width multiplier
    height: float = 1.0             # leg length multiplier


LOOKS = {
    "penny": Look(skin=(196, 146, 108), hair=(34, 26, 24), hair_style="bun", lashes=True, lip=(150, 60, 70), earring=(214, 180, 80), hat="tophat", hat_col=(34, 32, 36),
                  glasses="monocle", coat=(46, 44, 56), coat2=(240, 236, 226), vest=(196, 156, 60), trousers=(52, 50, 60),
                  lapel=(30, 30, 38), eye=(60, 40, 28), build=0.9),
    "quill": Look(skin=(234, 200, 170), hair=(196, 192, 186), hair_style="swept", glasses="spectacles", coat=(52, 70, 112),
                  coat2=(236, 230, 214), vest=(120, 96, 70), trousers=(70, 66, 70), lapel=(40, 54, 88), eye=(70, 90, 110), build=0.95),
    "stampy": Look(skin=(150, 106, 76), hair=(28, 24, 22), hair_style="short", hat="visor", hat_col=(60, 140, 100), coat=(236, 232, 220),
                   coat2=(236, 232, 220), vest=(120, 84, 54), tie=(160, 40, 40), trousers=(90, 74, 60), eye=(46, 32, 24), build=1.05),
    "atlas": Look(skin=(222, 178, 142), hair=(96, 66, 44), hat="fieldcap", hat_col=(150, 124, 84), coat=(54, 98, 104),
                  coat2=(226, 220, 204), trousers=(92, 84, 72), belt=(96, 66, 40)),
    "pike": Look(skin=(214, 170, 134), hair=(140, 98, 60), hat="helmet", hat_col=(104, 112, 86), coat=(110, 116, 88),
                 coat2=(150, 150, 120), trousers=(100, 104, 80), belt=(90, 70, 46), build=0.92, eye=(80, 96, 110)),
    "clive": Look(skin=(234, 196, 168), hair=(214, 210, 200), hair_style="wig", hat="tricorn", hat_col=(36, 32, 34),
                  coat=(168, 38, 40), coat2=(236, 228, 204), trousers=(232, 226, 210), sash=(60, 80, 150), buttons=True,
                  lapel=(30, 60, 120), eye=(90, 80, 70)),
    "nawab": Look(skin=(176, 128, 92), hair=(30, 24, 22), hair_style="none", facial="moustache", hat="turban", hat_col=(238, 230, 214),
                  coat=(40, 104, 80), coat2=(212, 176, 80), trousers=(220, 206, 178), robe=3.6, sash=(212, 176, 80), eye=(46, 32, 24)),
    "mir_jafar": Look(skin=(170, 124, 90), hair=(70, 66, 64), hair_style="none", facial="beard", hat="turban", hat_col=(200, 70, 60),
                      coat=(196, 170, 120), coat2=(120, 60, 50), trousers=(220, 206, 178), robe=3.8, build=1.08, eye=(46, 32, 24)),
    "redcoat": Look(skin=(228, 186, 154), hair=(110, 80, 50), hat="tricorn", hat_col=(36, 32, 34), coat=(164, 40, 40),
                    coat2=(236, 228, 204), trousers=(232, 226, 210), belt=(236, 232, 220), buttons=True),
    "sepoy": Look(skin=(160, 116, 84), hair=(26, 22, 20), facial="moustache", hat="turban", hat_col=(40, 40, 52), coat=(164, 40, 40),
                  coat2=(236, 228, 204), trousers=(236, 230, 214), belt=(236, 232, 220)),
}


# ------------------------------------------------------------------------------------------------ head
def _eye(d, x, y, u, face, scale, look_dx, eye_col, line):
    s = scale * face.bulge
    w, h = 0.19 * u * s, 0.12 * u * s * (1 - 0.95 * face.blink)
    if face.blink < 0.7:
        d.ellipse([x - w, y - h, x + w, y + h], fill=(250, 248, 242))
        r = 0.085 * u * min(1.0, s)
        ix = x + look_dx * 0.07 * u
        d.ellipse([ix - r, y - r * 1.05, ix + r, y + r * 1.05], fill=eye_col)
        d.ellipse([ix - r * 0.5, y - r * 0.55, ix + r * 0.5, y + r * 0.45], fill=(24, 18, 16))
        d.ellipse([ix - r * 0.15 - 0.03 * u, y - r * 0.6, ix - r * 0.15 + 0.03 * u, y - r * 0.6 + 0.06 * u], fill=(255, 255, 255))
    d.arc([x - w * 1.08, y - h - 0.05 * u, x + w * 1.08, y + h + 0.05 * u], 190, 350, fill=line, width=max(3, int(0.06 * u)))
    if face.blink >= 0.7:
        d.line([(x - w, y), (x + w, y)], fill=line, width=max(3, int(0.05 * u)))


def _mouth(d, x, y, u, m, line, skin):
    lip = _dark(skin, 0.72)
    inside = (92, 38, 42)
    open_ = {"B": (0.13, 0.05), "C": (0.15, 0.09), "D": (0.17, 0.14), "E": (0.12, 0.1), "F": (0.08, 0.07), "G": (0.14, 0.05),
             "H": (0.14, 0.08), "o": (0.08, 0.1), "wide": (0.19, 0.16)}
    lw = max(3, int(0.05 * u))
    if m in open_:
        w, h = open_[m]
        d.ellipse([x - w * u, y - h * u, x + w * u, y + h * u], fill=inside, outline=lip, width=lw)
        if h > 0.06 and m not in ("o", "F"):
            d.chord([x - w * 0.8 * u, y - h * u, x + w * 0.8 * u, y - h * 0.2 * u], 180, 360, fill=(245, 242, 236))
        return
    if m == "smile":
        d.arc([x - 0.2 * u, y - 0.14 * u, x + 0.2 * u, y + 0.08 * u], 15, 165, fill=line, width=lw)
    elif m == "grin":
        d.chord([x - 0.22 * u, y - 0.08 * u, x + 0.22 * u, y + 0.16 * u], 0, 180, fill=(245, 242, 236), outline=lip, width=lw)
    elif m == "frown":
        d.arc([x - 0.18 * u, y + 0.0 * u, x + 0.18 * u, y + 0.2 * u], 200, 340, fill=line, width=lw)
    elif m == "worried":
        d.line([(x - 0.17 * u, y + 0.04 * u), (x - 0.05 * u, y - 0.01 * u), (x + 0.07 * u, y + 0.03 * u), (x + 0.17 * u, y - 0.01 * u)],
               fill=line, width=lw)
    elif m == "smirk":
        d.line([(x - 0.15 * u, y + 0.02 * u), (x + 0.1 * u, y + 0.0 * u)], fill=line, width=lw)
        d.arc([x + 0.0 * u, y - 0.12 * u, x + 0.22 * u, y + 0.04 * u], 20, 110, fill=line, width=lw)
    else:                                                                       # X, A: closed, relaxed
        d.line([(x - 0.15 * u, y), (x + 0.15 * u, y + 0.01 * u)], fill=line, width=lw)
        d.line([(x - 0.1 * u, y + 0.07 * u), (x + 0.1 * u, y + 0.07 * u)], fill=lip, width=max(2, lw - 1))


def _hair_back(d, L: Look, cx, cy, u, fc, line):
    if L.hair_style == "wig":                                                   # 18th-century wig: side roll and tied queue
        bx = cx - fc * 0.7 * u
        d.ellipse([bx - 0.3 * u, cy - 0.15 * u, bx + 0.3 * u, cy + 0.25 * u], fill=L.hair, outline=line, width=3)
        d.line([(cx - fc * 0.74 * u, cy - 0.35 * u), (cx - fc * 0.86 * u, cy + 0.3 * u)], fill=L.hair, width=int(0.1 * u))
        d.polygon([(cx - fc * 0.8 * u, cy - 0.12 * u), (cx - fc * 0.98 * u, cy - 0.02 * u), (cx - fc * 0.95 * u, cy + 0.06 * u)], fill=(30, 30, 30))
    if L.hair_style == "bun":
        bx = cx - fc * 0.55 * u
        d.ellipse([bx - 0.36 * u, cy - 1.0 * u, bx + 0.36 * u, cy - 0.35 * u], fill=L.hair, outline=line, width=3)
    if L.hair_style == "long":
        d.rounded_rectangle([cx - 0.95 * u, cy - 0.9 * u, cx + 0.95 * u, cy + 1.0 * u], radius=0.5 * u, fill=L.hair, outline=line, width=3)


def _hair_front(d, L: Look, cx, cy, u, fc, line, rx, ry):
    if L.hair_style in ("short", "swept", "long", "bun"):
        fy = cy - (0.5 if L.hair_style != "swept" else 0.6) * u
        poly = _hairline(cx, cy, rx, ry, fc, u, fy)
        d.polygon(poly, fill=L.hair, outline=_dark(L.hair, 0.6))
    elif L.hair_style == "wig":
        poly = _hairline(cx, cy, rx, ry, fc, u, cy - 0.55 * u, lift=1.09)
        d.polygon(poly, fill=L.hair, outline=_dark(L.hair, 0.7))


def _hat(d, L: Look, cx, cy, u, fc, line):
    hc, lw = L.hat_col, 4
    top = cy - 0.8 * u
    if L.hat == "fieldcap":                                                     # soft explorer's cap with goggles
        d.chord([cx - 0.92 * u, top - 0.45 * u, cx + 0.92 * u, top + 0.75 * u], 180, 360, fill=hc, outline=line, width=lw)
        d.polygon([(cx + fc * 0.3 * u, top + 0.12 * u), (cx + fc * 1.35 * u, top + 0.24 * u), (cx + fc * 0.3 * u, top + 0.32 * u)],
                  fill=_dark(hc, 0.8), outline=line)
        for k in (-0.32, 0.22):
            gx = cx + fc * k * u
            d.ellipse([gx - 0.2 * u, top - 0.25 * u, gx + 0.2 * u, top + 0.08 * u], fill=(160, 196, 206), outline=(70, 60, 50), width=4)
    elif L.hat == "helmet":                                                     # broad steel helmet
        d.chord([cx - 0.95 * u, top - 0.55 * u, cx + 0.95 * u, top + 0.9 * u], 180, 360, fill=hc, outline=line, width=lw)
        d.ellipse([cx - 1.35 * u, top + 0.1 * u, cx + 1.35 * u, top + 0.42 * u], fill=_dark(hc, 0.85), outline=line, width=lw)
    elif L.hat == "tricorn":
        t2 = top + 0.32 * u
        d.chord([cx - 0.8 * u, t2 - 0.55 * u, cx + 0.8 * u, t2 + 0.45 * u], 180, 360, fill=hc)
        d.polygon([(cx - 1.12 * u, t2 + 0.12 * u), (cx - 0.3 * u, t2 - 0.42 * u), (cx + 0.3 * u, t2 - 0.42 * u),
                   (cx + 1.12 * u, t2 + 0.12 * u), (cx + fc * 0.1 * u, t2 + 0.02 * u)], fill=hc, outline=(196, 166, 80))
        d.ellipse([cx + fc * 0.45 * u - 0.09 * u, t2 - 0.25 * u, cx + fc * 0.45 * u + 0.09 * u, t2 - 0.07 * u], fill=(30, 30, 30), outline=(196, 166, 80))
    elif L.hat == "tophat":
        t2 = top + 0.22 * u
        d.rounded_rectangle([cx - 1.0 * u, t2 + 0.05 * u, cx + 1.0 * u, t2 + 0.3 * u], radius=0.12 * u, fill=hc, outline=line, width=3)
        d.rectangle([cx - 0.62 * u, t2 - 1.25 * u, cx + 0.62 * u, t2 + 0.12 * u], fill=hc, outline=line, width=3)
        d.rectangle([cx - 0.62 * u, t2 - 0.22 * u, cx + 0.62 * u, t2 - 0.04 * u], fill=(150, 36, 44))
    elif L.hat == "visor":
        t2 = top + 0.5 * u
        d.line([(cx - 0.76 * u, t2 + 0.02 * u), (cx + 0.76 * u, t2 + 0.02 * u)], fill=_dark(hc, 0.6), width=int(0.1 * u))
        d.polygon([(cx + fc * 0.1 * u, t2 - 0.02 * u), (cx + fc * 0.78 * u, t2 - 0.02 * u), (cx + fc * 1.3 * u, t2 + 0.26 * u),
                   (cx + fc * 0.25 * u, t2 + 0.2 * u)], fill=hc, outline=_dark(hc, 0.55))
    elif L.hat == "turban":                                                     # wrapped turban fitted to the head
        dark = _dark(hc, 0.82)
        d.chord([cx - 0.8 * u, top - 0.6 * u, cx + 0.8 * u, top + 0.75 * u], 180, 360, fill=hc, outline=_dark(hc, 0.55), width=3)
        d.rounded_rectangle([cx - 0.84 * u, top + 0.02 * u, cx + 0.84 * u, top + 0.4 * u], radius=0.18 * u, fill=hc, outline=_dark(hc, 0.55), width=3)
        for k in range(3):                                                      # diagonal folds of the wrap
            x0 = cx - fc * 0.45 * u + fc * k * 0.38 * u
            d.line([(x0, top + 0.34 * u), (x0 + fc * 0.3 * u, top - 0.22 * u)], fill=dark, width=max(3, int(0.05 * u)))
        jx, jy = cx + fc * 0.25 * u, top + 0.02 * u
        d.ellipse([jx - 0.09 * u, jy - 0.09 * u, jx + 0.09 * u, jy + 0.09 * u], fill=(190, 30, 50), outline=(210, 175, 80), width=3)
        d.arc([jx - fc * 0.05 * u - 0.25 * u, jy - 0.6 * u, jx - fc * 0.05 * u + 0.25 * u, jy + 0.1 * u], 200 if fc > 0 else 250, 300 if fc > 0 else 340,
              fill=(240, 236, 226), width=max(4, int(0.08 * u)))


def head_outline(cx, cy, rx, ry, fc, u, n=48, lo=0.0, hi=2 * math.pi):
    """Cranium ellipse narrowing into a jaw and chin, chin pushed towards the facing side (3/4 view)."""
    pts = []
    for i in range(n + 1):
        a = lo + (hi - lo) * i / n
        c = math.cos(a)                                                         # +1 at the chin, -1 at the crown
        jaw = max(0.0, c) ** 2
        x = rx * math.sin(a) * (1 - 0.17 * jaw) + fc * 0.08 * u * jaw
        y = ry * c * (1 + 0.04 * jaw)
        pts.append((cx + x, cy + y))
    return pts


def _hairline(cx, cy, rx, ry, fc, u, fringe_y, lift=1.06):
    """Hair cap: outer edge follows the skull, inner edge is a soft, slightly uneven fringe swept to the facing side."""
    outer = [(cx + rx * lift * math.sin(a), cy - ry * lift * math.cos(a) * -1 * -1) for a in []]
    outer = []
    for i in range(25):
        a = math.pi * 0.5 + math.pi * i / 24                                    # from the back side over the crown to the front
        outer.append((cx + rx * lift * math.cos(a) * -fc * -1, cy - ry * lift * abs(math.sin(a)) if False else cy - ry * lift * math.sin(a - math.pi * 0.5 + math.pi * 0.5)))
    pts = []
    for i in range(25):
        t = i / 24
        a = math.pi * (1 - t) + 0.2 * math.pi * t                               # pi (back) -> ~36 deg (front, at the fringe)
        x = cx + rx * lift * math.cos(a) * fc * -1 * -1
        y = cy - ry * lift * math.sin(a)
        pts.append((x, y))
    # fringe back across the forehead (front -> back), wavy, higher at the front
    fr = []
    for i in range(13):
        t = i / 12
        x = cx + fc * rx * (0.95 - 1.9 * t)
        y = fringe_y - 0.12 * u * (1 - t) + 0.05 * u * math.sin(t * 9)
        fr.append((x, y))
    side = [(cx - fc * rx * 1.0, cy + 0.15 * u), (cx - fc * rx * 0.86, cy + 0.15 * u)]          # sideburn
    return pts + fr + [(cx - fc * rx * 0.86, fringe_y + 0.1 * u)] + side[::-1]


@lru_cache(maxsize=6000)
def head_sprite(key: str, face, flip: bool, u: float):
    """Natural head on its own canvas; returns (image, centre x, centre y)."""
    L = LOOKS[key]
    fc = -1 if flip else 1
    W = int(3.2 * u)
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, W / 2 + 0.15 * u
    line = _dark(L.skin, 0.45)
    shade = _dark(L.skin, 0.84)
    rx, ry = 0.74 * u, 0.98 * u
    _hair_back(d, L, cx, cy, u, fc, line)
    ex = cx - fc * 0.72 * u                                                     # the visible (back) ear in 3/4 view
    d.ellipse([ex - 0.13 * u, cy - 0.12 * u, ex + 0.13 * u, cy + 0.26 * u], fill=shade, outline=line, width=3)
    d.polygon(head_outline(cx, cy, rx + 3, ry + 3, fc, u), fill=line)                              # outline
    d.polygon(head_outline(cx, cy, rx, ry, fc, u), fill=shade)                                      # shaded far side
    d.polygon(head_outline(cx + fc * 0.08 * u, cy - 0.01 * u, rx * 0.88, ry * 0.985, fc, u), fill=L.skin)
    fx = cx + fc * 0.2 * u                                                      # features shifted for the 3/4 turn
    ey = cy + 0.0 * u
    look = face.look + fc * 0.5
    _eye(d, fx - 0.3 * u, ey, u, face, 0.86 if fc > 0 else 1.0, look, L.eye, line)
    _eye(d, fx + 0.3 * u, ey, u, face, 1.0 if fc > 0 else 0.86, look, L.eye, line)
    if L.lashes and face.blink < 0.7:
        for ex2 in (fx - 0.3 * u, fx + 0.3 * u):
            d.line([(ex2 + 0.17 * u, ey - 0.08 * u), (ex2 + 0.26 * u, ey - 0.15 * u)], fill=line, width=max(3, int(0.045 * u)))
    if L.glasses == "spectacles":
        for ex2 in (fx - 0.3 * u, fx + 0.3 * u):
            d.ellipse([ex2 - 0.22 * u, ey - 0.18 * u, ex2 + 0.22 * u, ey + 0.18 * u], outline=(60, 50, 44), width=max(3, int(0.05 * u)))
        d.line([(fx - 0.08 * u, ey - 0.03 * u), (fx + 0.08 * u, ey - 0.03 * u)], fill=(60, 50, 44), width=3)
        d.line([(fx - fc * 0.52 * u, ey - 0.03 * u), (cx - fc * 0.7 * u, ey - 0.08 * u)], fill=(60, 50, 44), width=3)
    if L.glasses == "monocle":
        mx2 = fx + 0.3 * u
        d.ellipse([mx2 - 0.24 * u, ey - 0.22 * u, mx2 + 0.24 * u, ey + 0.22 * u], outline=(206, 170, 70), width=max(4, int(0.06 * u)))
        d.line([(mx2 + 0.1 * u, ey + 0.22 * u), (mx2 + 0.2 * u, ey + 1.0 * u)], fill=(206, 170, 70), width=2)
    bw = max(3, int(0.07 * u))
    for side in (-1, 1):                                                        # brows: + worried/raised, - angry
        bx = fx + side * 0.3 * u
        inner_up = 0.06 * u * face.brows
        by = ey - 0.27 * u - 0.05 * u * max(0.0, face.brows) * 0.5
        inner, outer = bx - side * 0.15 * u, bx + side * 0.17 * u
        d.line([(inner, by - inner_up), (outer, by + 0.02 * u)], fill=_dark(L.hair, 0.8) if L.hair_style != "wig" else (110, 100, 90), width=bw)
    nx = fx + fc * 0.02 * u
    d.line([(nx - fc * 0.02 * u, ey + 0.05 * u), (nx + fc * 0.08 * u, ey + 0.22 * u), (nx + fc * 0.12 * u, ey + 0.32 * u)], fill=_dark(L.skin, 0.7), width=max(3, int(0.045 * u)))
    d.arc([nx - 0.08 * u, ey + 0.24 * u, nx + 0.13 * u, ey + 0.4 * u], 20 if fc > 0 else 0, 160 if fc > 0 else 180, fill=line, width=max(3, int(0.045 * u)))
    my = cy + 0.58 * u
    if L.facial == "moustache":
        d.polygon([(nx - 0.22 * u, my - 0.02 * u), (nx, my - 0.13 * u), (nx + 0.22 * u, my - 0.02 * u), (nx, my - 0.07 * u)], fill=L.hair)
    if L.facial == "beard":
        jaw = head_outline(cx, cy, rx * 1.04, ry * 1.06, fc, u, n=24, lo=-1.25, hi=1.25)
        d.polygon(jaw + [(cx + fc * 0.5 * u, my - 0.12 * u), (cx - fc * 0.55 * u, my - 0.12 * u)], fill=L.hair, outline=_dark(L.hair, 0.6))
        d.polygon([(nx - 0.24 * u, my - 0.02 * u), (nx, my - 0.15 * u), (nx + 0.24 * u, my - 0.02 * u), (nx, my - 0.07 * u)], fill=_dark(L.hair, 0.8))
        d.ellipse([fx - 0.13 * u + fc * 0.03 * u, my - 0.07 * u, fx + 0.17 * u + fc * 0.03 * u, my + 0.1 * u], fill=_dark(L.skin, 0.75))
    _mouth(d, fx + fc * 0.03 * u, my, u, face.mouth, L.lip or line, L.skin)
    if L.earring:
        ex3 = cx - fc * 0.72 * u
        d.ellipse([ex3 - 0.07 * u, cy + 0.3 * u, ex3 + 0.07 * u, cy + 0.44 * u], fill=L.earring, outline=_dark(L.earring, 0.6))
    _hair_front(d, L, cx, cy, u, fc, line, rx, ry)
    _hat(d, L, cx, cy, u, fc, line)
    bb = im.getbbox()
    spr = im.crop(bb)
    return spr, cx - bb[0], cy - bb[1]


# ------------------------------------------------------------------------------------------------ torso
@lru_cache(maxsize=2048)
def torso_sprite(key: str, ang: int, u: float, flip: bool):
    """Torso (and robe) drawn upright, rotated about the hip; returns (image, hip x, hip y)."""
    L = LOOKS[key]
    fc = -1 if flip else 1
    T = 4.3 * u
    R = L.robe * u
    sw = 1.42 * u * L.build                                                     # half shoulder width
    W = int(4.2 * u * L.build + 2 * u)
    H = int(T + R + 0.8 * u)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hx, hy = W / 2, T + 0.3 * u
    line = _dark(L.coat, 0.45)
    top = hy - T
    body = [(hx - sw + 0.2 * u, top + 0.05 * u), (hx + sw - 0.2 * u, top + 0.05 * u), (hx + sw, top + 0.45 * u), (hx + sw * 0.82, top + 2.6 * u),
            (hx + sw * 0.92, hy + 0.3 * u), (hx - sw * 0.92, hy + 0.3 * u), (hx - sw * 0.82, top + 2.6 * u), (hx - sw, top + 0.45 * u)]
    if R:                                                                       # long robe (jama): flares to the knees
        body = body[:4] + [(hx + sw * 1.15, hy + R), (hx - sw * 1.15, hy + R)] + body[6:]
    d.polygon(body, fill=L.coat, outline=line, width=4)
    back = [(hx - fc * sw, top + 0.45 * u), (hx - fc * sw * 0.82, top + 2.6 * u), (hx - fc * sw * (1.1 if R else 0.92), hy + (R or 0.3 * u)),
            (hx - fc * sw * 0.6, hy + (R or 0.3 * u)), (hx - fc * sw * 0.55, top + 0.5 * u)]
    d.polygon(back, fill=_dark(L.coat, 0.84))                                   # shaded back half
    d.polygon([(hx - 0.32 * u, top + 0.05 * u), (hx + 0.32 * u, top + 0.05 * u), (hx + fc * 0.05 * u, top + 1.35 * u)], fill=L.coat2, outline=line)
    if L.vest:
        d.polygon([(hx - 0.55 * u, top + 0.5 * u), (hx + 0.55 * u, top + 0.5 * u), (hx + 0.62 * u, hy - 0.2 * u), (hx - 0.62 * u, hy - 0.2 * u)],
                  fill=L.vest, outline=line)
        d.polygon([(hx - 0.32 * u, top + 0.05 * u), (hx + 0.32 * u, top + 0.05 * u), (hx + fc * 0.05 * u, top + 1.1 * u)], fill=L.coat2, outline=line)
    if L.tie:
        d.polygon([(hx - 0.1 * u, top + 0.15 * u), (hx + 0.1 * u, top + 0.15 * u), (hx + 0.16 * u, top + 1.7 * u), (hx, top + 1.95 * u),
                   (hx - 0.16 * u, top + 1.7 * u)], fill=L.tie, outline=_dark(L.tie, 0.6))
    if L.lapel:
        for side in (-1, 1):
            d.polygon([(hx + side * 0.32 * u, top + 0.05 * u), (hx + side * 0.75 * u, top + 0.2 * u), (hx + side * 0.45 * u, top + 2.4 * u),
                       (hx + side * 0.12 * u, top + 1.4 * u)], fill=L.lapel, outline=line)
    if L.buttons:
        for k in range(5):
            by = top + 1.5 * u + k * 0.45 * u
            d.ellipse([hx + fc * 0.25 * u - 0.07 * u, by - 0.07 * u, hx + fc * 0.25 * u + 0.07 * u, by + 0.07 * u], fill=(214, 184, 96))
    if L.sash:
        d.polygon([(hx - sw * 0.85, top + 0.6 * u), (hx - sw * 0.55, top + 0.4 * u), (hx + sw * 0.85, top + 3.0 * u), (hx + sw * 0.7, top + 3.4 * u)],
                  fill=L.sash, outline=_dark(L.sash, 0.6))
    if L.belt:
        d.rectangle([hx - sw * 0.86, hy - 0.55 * u, hx + sw * 0.86, hy - 0.25 * u], fill=L.belt, outline=_dark(L.belt, 0.6))
    if R:
        d.rectangle([hx - sw * 0.84, top + 2.5 * u, hx + sw * 0.84, top + 2.85 * u], fill=L.coat2)
    return rot_sprite(im, (hx, hy), ang)


# ------------------------------------------------------------------------------------------------ the frame
def _limb(d, a, b, w, fill, line):
    d.line([a, b], fill=line, width=int(w + 6))
    for (x, y) in (a, b):
        r = w / 2 + 3
        d.ellipse([x - r, y - r, x + r, y + r], fill=line)
    d.line([a, b], fill=fill, width=int(w))
    for (x, y) in (a, b):
        r = w / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _limb2(d, a, b, c, w1, w2, fill, line):
    """Two-segment limb: all outlines first, then all fills, so joints show no rings."""
    for (p, q, w) in ((a, b, w1), (b, c, w2)):
        d.line([p, q], fill=line, width=int(w + 6))
        for (x, y) in (p, q):
            r = w / 2 + 3
            d.ellipse([x - r, y - r, x + r, y + r], fill=line)
    for (p, q, w) in ((a, b, w1), (b, c, w2)):
        d.line([p, q], fill=fill, width=int(w))
        for (x, y) in (p, q):
            r = w / 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


LEG_LEN = 3.4                     # rig leg_len for natural characters: thigh = shin = 2.55 head units
HEAD_K = 1.28                     # head size relative to the body unit


def draw(key, p, s=1.0, flip=False):
    """Natural-style character frame; same contract as rig.draw_character: (RGBA tile at 1x, anchor x, anchor y)."""
    import rig as R
    L = LOOKS[key]
    u = 40 * s
    f = -1 if flip else 1
    Wt, Ht = int((17 if p.rot else 10) * u), int(15 * u)
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gx, gy = Wt / 2, Ht - 0.8 * u
    leg = 0.75 * u * LEG_LEN * L.height
    hip_y = gy - (2 * leg + 0.3 * u) - p.y * u
    hx = gx
    legs = []
    for side, th, kn in ((-1, p.th_r, p.kn_r), (1, p.th_l, p.kn_l)):
        hp = (hx + side * 0.35 * u, hip_y)
        knee = _down(*hp, th, leg, f)
        ankle = _down(*knee, th - kn, leg, f)
        legs.append((hp, knee, ankle, side))
    tline = _dark(L.trousers, 0.45)
    for i, (hp, knee, ankle, side) in enumerate(legs):
        col = _dark(L.trousers, 0.85) if i == 0 else L.trousers
        _limb2(d, hp, knee, ankle, 1.0 * u, 0.82 * u, col, tline)
        ax, ay = ankle
        d.ellipse([ax - 0.45 * u + f * 0.25 * u - 3, ay - 0.05 * u - 3, ax + 0.6 * u + f * 0.25 * u + 3, ay + 0.42 * u + 3], fill=(30, 22, 18))
        d.ellipse([ax - 0.45 * u + f * 0.25 * u, ay - 0.05 * u, ax + 0.6 * u + f * 0.25 * u, ay + 0.42 * u], fill=L.shoes)
    lean = p.lean * f
    tor, piv = torso_sprite(key, round(lean), round(u, 3), flip)
    im.alpha_composite(tor, (int(hx - piv[0]), int(hip_y - piv[1])))
    T = 4.3 * u
    sw = 1.25 * u * L.build

    def body_pt(dx, dy):
        rx, ry = _rot(dx, dy, lean)
        return hx + rx, hip_y + ry

    front_sh = body_pt(f * sw, -(T - 0.45 * u))
    back_sh = body_pt(-f * sw * 0.75, -(T - 0.45 * u))
    neck = body_pt(0, -T)
    cline = _dark(L.coat, 0.45)

    def arm(sh_pt, sh, el, prop, back):
        elbow = _down(*sh_pt, sh, 1.85 * u, f)
        hand = _down(*elbow, sh + el, 1.7 * u, f)
        col = _dark(L.coat, 0.82) if back else L.coat
        _limb2(d, sh_pt, elbow, hand, 0.7 * u, 0.6 * u, col, cline)
        r = 0.3 * u
        d.ellipse([hand[0] - r - 3, hand[1] - r - 3, hand[0] + r + 3, hand[1] + r + 3], fill=_dark(L.skin, 0.45))
        d.ellipse([hand[0] - r, hand[1] - r, hand[0] + r, hand[1] + r], fill=L.skin)
        if prop:
            R.draw_prop(d, prop, hand[0], hand[1], u * 0.6, sh + el, f)

    arm(back_sh, p.sh_r, p.el_r, p.prop_r, True)
    # neck and head
    nb, nt = neck, body_pt(0, -T - 0.45 * u)
    d.line([nb, nt], fill=_dark(L.skin, 0.84), width=int(0.5 * u))
    hang = round(lean + p.head * f)
    spr, ox, oy = head_sprite(key, p.face, flip, round(u * HEAD_K, 3))
    spr, (ox, oy) = rot_sprite(spr, (ox, oy), hang)
    hc_dx, hc_dy = _rot(0, -0.92 * u * HEAD_K, hang)
    im.alpha_composite(spr, (int(nt[0] + hc_dx - ox), int(nt[1] + hc_dy - oy)))
    arm(front_sh, p.sh_l, p.el_l, p.prop_l, False)
    # crop, squash/stretch, fall rotation, 2x -> 1x
    bb = im.getbbox() or (0, 0, 2, 2)
    x0, y0 = max(0, bb[0] - 4), max(0, bb[1] - 4)
    out = im.crop((x0, y0, min(Wt, bb[2] + 4), min(Ht, bb[3] + 4)))
    ax, ay = gx - x0, gy - y0
    if abs(p.sq - 1.0) > 0.015:
        w0, h0 = out.size
        nw, nh = max(2, int(w0 / math.sqrt(p.sq))), max(2, int(h0 * p.sq))
        out = out.resize((nw, nh), Image.BILINEAR)
        ax, ay = ax * nw / w0, ay * nh / h0
    if p.rot:
        out, (ax, ay) = rot_sprite(out, (ax, ay), p.rot * f)
    if out.width % 2 or out.height % 2:
        out = out.crop((0, 0, out.width + out.width % 2, out.height + out.height % 2))
    return out.reduce(2), ax / 2, ay / 2
