"""Tiny Empires hosts, design v3 (owner references, 11 Nov 2026): one renderer for any view from front to profile.

Hosts and roles:
  penny  Main Presenter    slim gold coin, edge visible in 3/4, bow tie, cane, top hat with gold band, white gloves
  atlas  Explorer          pith helmet, khaki shirt and shorts, rolled sleeves, socks and boots, map
  quill  Historian         brown owl, mortarboard, round glasses, book
  zed    Analyst           friendly lime-green alien, antennae, big glossy eyes (replaces the goblin)
  pike   Comic Commentator guard in a tall bearskin, red tunic, gold buttons and belt, rifle

draw(key, pose, s, flip, view) -> (RGBA tile at 1x, anchor x, anchor y). The view runs from 0 (front) through 0.6 (3/4)
to 1 (profile); flip turns the character to face left. Same skeleton and Pose as rig.py, so every motion works.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw

LINE = (34, 40, 50)                                                             # dark slate outline, as in the references
OUT = 6


def shade(c, k=0.8):
    return tuple(int(v * k) for v in c[:3])


def tint(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


def _rot(dx, dy, ang):
    a = math.radians(ang)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def _down(x, y, ang, length, f):
    a = math.radians(ang)
    return x + f * math.sin(a) * length, y + math.cos(a) * length


def rot_sprite(img, pivot, ang):
    if not ang:
        return img, pivot
    w0, h0 = img.size
    out = img.rotate(-ang, resample=Image.BILINEAR, expand=True)
    dx, dy = _rot(pivot[0] - w0 / 2, pivot[1] - h0 / 2, ang)
    return out, (out.width / 2 + dx, out.height / 2 + dy)


def ell(d, cx, cy, rx, ry, fill, line=LINE, w=OUT):
    if line:
        d.ellipse([cx - rx - w, cy - ry - w, cx + rx + w, cy + ry + w], fill=line)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill)


def shaded_ell(d, cx, cy, rx, ry, fill, f=1, line=LINE):
    """Outlined ellipse with a cel-shaded far side and a soft highlight (light from the front-upper side)."""
    ell(d, cx, cy, rx, ry, shade(fill, 0.82), line)
    d.ellipse([cx - rx + (0.12 * rx if f < 0 else 0), cy - ry, cx + rx - (0.12 * rx if f > 0 else 0), cy + ry * 0.9], fill=fill)
    hx = cx + f * rx * 0.35
    d.ellipse([hx - rx * 0.22, cy - ry * 0.72, hx + rx * 0.22, cy - ry * 0.42], fill=tint(fill, 0.35))


def limb(d, pts, widths, colors):
    """Multi-segment limb: all outlines first, then fills (no rings at the joints)."""
    for (a, b), w in zip(zip(pts, pts[1:]), widths):
        d.line([a, b], fill=LINE, width=int(w + 2 * OUT))
        for (x, y) in (a, b):
            r = w / 2 + OUT
            d.ellipse([x - r, y - r, x + r, y + r], fill=LINE)
    for (a, b), w, c in zip(zip(pts, pts[1:]), widths, colors):
        d.line([a, b], fill=c, width=int(w))
        for (x, y) in (a, b):
            r = w / 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)


# ------------------------------------------------------------------------------------------------ faces
def eyes(d, fx, ey, u, face, k, gap=0.55, w=0.36, h=0.46, iris=(70, 46, 30), lids=None):
    """Two eyes around fx; k = facing x view (-1..1). Far eye narrows and hides in profile."""
    look = face.look * 0.5 + k * 0.5
    for side in (-1, 1):
        far = side * k < 0
        if far and abs(k) > 0.85:
            continue
        sq = 1 - 0.45 * abs(k) if far else 1.0
        ex = fx + side * gap * u * (1 - 0.5 * abs(k))
        rx, ry = w * u * sq * face.bulge, h * u * face.bulge * (1 - 0.94 * face.blink)
        if face.blink < 0.6:
            d.ellipse([ex - rx - 3, ey - ry - 3, ex + rx + 3, ey + ry + 3], fill=LINE)
            d.ellipse([ex - rx, ey - ry, ex + rx, ey + ry], fill=(252, 252, 248))
            ir = min(rx, ry) * 0.62
            ix = ex + look * rx * 0.4
            d.ellipse([ix - ir, ey - ir * 1.05, ix + ir, ey + ir * 1.05], fill=iris)
            d.ellipse([ix - ir * 0.55, ey - ir * 0.6, ix + ir * 0.55, ey + ir * 0.6], fill=(20, 18, 22))
            d.ellipse([ix - ir * 0.6, ey - ir * 0.75, ix - ir * 0.1, ey - ir * 0.25], fill=(255, 255, 255))
            if lids is not None and face.brows < -0.3:                          # heavy lids: smug / cross
                d.chord([ex - rx - 3, ey - ry - 3, ex + rx + 3, ey + ry * 0.2], 180, 360, fill=lids, outline=LINE, width=4)
        else:
            d.arc([ex - rx, ey - 0.25 * u, ex + rx, ey + 0.2 * u], 200, 340, fill=LINE, width=max(4, int(0.08 * u)))
        by = ey - ry - 0.22 * u - 0.12 * u * max(0.0, face.brows)
        tilt = 0.16 * u * face.brows
        inner, outer = ex - side * rx * 0.9, ex + side * rx * 1.1
        d.line([(inner, by - tilt), (outer, by + 0.02 * u)], fill=LINE, width=max(4, int(0.11 * u)))


def mouth(d, mx, my, u, m, k=0.0, lip=(120, 50, 50), sz=1.0):
    u = u * sz
    lw = max(4, int(0.09 * u))
    shapes = {"A": None, "X": None, "B": (0.22, 0.09), "C": (0.26, 0.17), "D": (0.3, 0.26), "E": (0.2, 0.2), "F": (0.13, 0.13),
              "G": (0.24, 0.1), "H": (0.24, 0.16), "o": (0.15, 0.2), "wide": (0.34, 0.3)}
    if m in shapes and shapes[m]:
        w, h = shapes[m]
        w *= 1 - 0.35 * abs(k)
        d.ellipse([mx - w * u - 3, my - h * u - 3, mx + w * u + 3, my + h * u + 3], fill=LINE)
        d.ellipse([mx - w * u, my - h * u, mx + w * u, my + h * u], fill=(110, 36, 44))
        if h > 0.12:
            d.ellipse([mx - w * 0.6 * u, my + h * 0.2 * u, mx + w * 0.6 * u, my + h * u], fill=(226, 110, 110))
        if m not in ("o", "F") and h > 0.08:
            d.chord([mx - w * 0.85 * u, my - h * u, mx + w * 0.85 * u, my - h * 0.2 * u], 180, 360, fill=(250, 250, 246))
        return
    w = 0.32 * (1 - 0.3 * abs(k))
    if m == "smile" or m in ("A", "X"):
        depth = 0.18 if m == "smile" else 0.08
        d.arc([mx - w * u, my - depth * u, mx + w * u, my + depth * u], 15, 165, fill=LINE, width=lw)
    elif m == "grin":
        d.chord([mx - w * 1.15 * u - 3, my - 0.12 * u - 3, mx + w * 1.15 * u + 3, my + 0.34 * u + 3], 0, 180, fill=LINE)
        d.chord([mx - w * 1.15 * u, my - 0.12 * u, mx + w * 1.15 * u, my + 0.34 * u], 0, 180, fill=(110, 36, 44))
        d.chord([mx - w * u, my - 0.12 * u, mx + w * u, my + 0.1 * u], 0, 180, fill=(250, 250, 246))
        d.ellipse([mx - w * 0.5 * u, my + 0.12 * u, mx + w * 0.5 * u, my + 0.3 * u], fill=(226, 110, 110))
    elif m == "frown":
        d.arc([mx - w * u, my, mx + w * u, my + 0.3 * u], 200, 340, fill=LINE, width=lw)
    elif m == "worried":
        d.line([(mx - w * u, my + 0.06 * u), (mx - w * 0.35 * u, my - 0.04 * u), (mx + w * 0.3 * u, my + 0.06 * u), (mx + w * u, my - 0.02 * u)],
               fill=LINE, width=lw)
    elif m == "smirk":
        d.line([(mx - w * u, my + 0.04 * u), (mx + w * 0.4 * u, my + 0.02 * u)], fill=LINE, width=lw)
        d.arc([mx, my - 0.2 * u, mx + w * 1.3 * u, my + 0.06 * u], 20, 110, fill=LINE, width=lw)


# ------------------------------------------------------------------------------------------------ heads
def head_atlas(d, cx, cy, u, face, k):
    skin, hair = (242, 204, 166), (122, 76, 42)
    R = 1.75 * u
    for side in (-1, 1):                                                        # ears
        if side * k > 0.5:
            continue
        ex = cx + side * R * 0.98 * (1 - 0.25 * abs(k)) - k * 0.25 * u
        ell(d, ex, cy + 0.15 * u, 0.32 * u, 0.42 * u, shade(skin, 0.92))
    if C("atlas", "hat") == "headcloth":                                        # lappets falling behind the face
        for side in (-1, 1):
            x0 = cx + side * R * 0.75
            d.polygon([(x0 - 0.55 * u, cy - R * 0.3), (x0 + 0.55 * u, cy - R * 0.3), (x0 + side * 0.25 * u + 0.5 * u, cy + R * 1.25),
                       (x0 + side * 0.25 * u - 0.5 * u, cy + R * 1.25)], fill=shade(LINEN, 0.9), outline=LINE)
    d.ellipse([cx - R * 1.05 - OUT, cy - R * 0.95 - OUT, cx + R * 1.05 + OUT, cy + R * 1.05 + OUT], fill=LINE)    # hair back
    d.ellipse([cx - R * 1.05, cy - R * 0.95, cx + R * 1.05, cy + R * 1.05], fill=hair)
    shaded_ell(d, cx + k * 0.12 * u, cy + 0.12 * u, R * (1 - 0.08 * abs(k)), R * 1.02, skin, 1 if k >= 0 else -1)
    d.chord([cx - R * 1.02, cy - R * 1.0, cx + R * 1.02, cy + R * 0.1], 180, 360, fill=hair)                       # hairline
    d.polygon([(cx + k * 0.6 * u - 0.9 * u, cy - 0.55 * u), (cx + k * 0.6 * u + 0.4 * u, cy - 0.95 * u), (cx + k * 0.6 * u + 1.1 * u, cy - 0.4 * u)],
              fill=hair)
    fx = cx + k * 0.75 * u
    eyes(d, fx, cy + 0.05 * u, u, face, k, gap=0.6, iris=(90, 60, 34))
    nx = fx + k * 0.55 * u
    ell(d, nx, cy + 0.55 * u, 0.22 * u, 0.2 * u, shade(skin, 0.9), w=3)
    for side in (-1, 1):
        if abs(k) < 0.85 or side * k > 0:
            d.ellipse([fx + side * 0.95 * u - 0.25 * u, cy + 0.6 * u, fx + side * 0.95 * u + 0.25 * u, cy + 0.85 * u], fill=(240, 166, 150))
    mouth(d, fx + k * 0.25 * u, cy + 1.05 * u, u, face.mouth, k)
    if C("atlas", "hat") == "headcloth":                                        # plain white linen headcloth
        top = cy - R * 0.62
        d.chord([cx - R * 1.1 - OUT, cy - R * 1.12 - OUT, cx + R * 1.1 + OUT, cy + R * 0.5 + OUT], 180, 360, fill=LINE)
        d.chord([cx - R * 1.1, cy - R * 1.12, cx + R * 1.1, cy + R * 0.5], 180, 360, fill=LINEN)
        d.line([(cx - R * 1.0, cy - R * 0.32), (cx + R * 1.0, cy - R * 0.32)], fill=shade(LINEN, 0.8), width=max(4, int(0.12 * u)))
        return
    hat, band = (212, 184, 134), (138, 100, 62)                                 # pith helmet
    top = cy - R * 0.62
    d.ellipse([cx - R * 1.75 - OUT, top - 0.42 * u - OUT, cx + R * 1.75 + OUT, top + 0.42 * u + OUT], fill=LINE)
    d.ellipse([cx - R * 1.75, top - 0.42 * u, cx + R * 1.75, top + 0.42 * u], fill=shade(hat, 0.86))
    d.chord([cx - R * 1.12 - OUT, top - 2.1 * u - OUT, cx + R * 1.12 + OUT, top + 2.1 * u + OUT], 180, 360, fill=LINE)
    d.chord([cx - R * 1.12, top - 2.1 * u, cx + R * 1.12, top + 2.1 * u], 180, 360, fill=hat)
    d.chord([cx - R * 0.95, top - 1.95 * u, cx + R * 0.2, top + 1.95 * u], 200, 250, fill=tint(hat, 0.3))
    d.rectangle([cx - R * 1.1, top - 0.5 * u, cx + R * 1.1, top - 0.08 * u], fill=band)
    d.line([(cx + k * 0.3 * u, top - 2.0 * u), (cx + k * 0.3 * u, top - 0.55 * u)], fill=shade(hat, 0.8), width=4)


def head_pike(d, cx, cy, u, face, k):
    skin = (246, 210, 182)
    R = 1.45 * u
    for side in (-1, 1):
        if side * k > 0.5:
            continue
        ell(d, cx + side * R * 0.98 - k * 0.2 * u, cy + 0.2 * u, 0.26 * u, 0.36 * u, shade(skin, 0.92))
    shaded_ell(d, cx + k * 0.1 * u, cy + 0.1 * u, R * (1 - 0.06 * abs(k)), R * 1.05, skin, 1 if k >= 0 else -1)
    fx = cx + k * 0.6 * u
    face2 = face if face.bulge > 1.05 else type(face)(brows=face.brows, look=face.look, blink=face.blink, mouth=face.mouth, bulge=0.8)
    eyes(d, fx, cy + 0.15 * u, u, face2, k, gap=0.48, w=0.3, h=0.36, iris=(80, 110, 150))
    for side in (-1, 1):
        if abs(k) < 0.85 or side * k > 0:
            d.ellipse([fx + side * 0.75 * u - 0.24 * u, cy + 0.6 * u, fx + side * 0.75 * u + 0.24 * u, cy + 0.86 * u], fill=(240, 150, 140))
    ell(d, fx + k * 0.45 * u, cy + 0.55 * u, 0.16 * u, 0.15 * u, shade(skin, 0.9), w=3)
    mouth(d, fx + k * 0.2 * u, cy + 0.95 * u, u, face.mouth, k, sz=0.85)
    if C("pike", "hat") == "wig":                                               # short black wig, no helmet (Old Kingdom troops)
        wig = (30, 26, 26)
        d.chord([cx - R * 1.12 - OUT, cy - R * 1.2 - OUT, cx + R * 1.12 + OUT, cy + R * 0.55 + OUT], 180, 360, fill=LINE)
        d.chord([cx - R * 1.12, cy - R * 1.2, cx + R * 1.12, cy + R * 0.55], 180, 360, fill=wig)
        for side in (-1, 1):
            if side * k > 0.5:
                continue
            d.rectangle([cx + side * R * 0.82 - 0.3 * u, cy - R * 0.4, cx + side * R * 0.82 + 0.3 * u, cy + R * 0.25], fill=wig)
        return
    d.arc([cx - R * 0.98 + k * 0.1 * u, cy - R * 0.9, cx + R * 0.98 + k * 0.1 * u, cy + R * 1.18], 15, 165, fill=(214, 180, 80), width=max(4, int(0.09 * u)))
    fur = (34, 32, 36)                                                          # bearskin cap
    bx0, bx1, by0, by1 = cx - R * 1.1, cx + R * 1.1, cy - R * 3.25, cy - R * 0.2
    d.rounded_rectangle([bx0 - OUT, by0 - OUT, bx1 + OUT, by1 + OUT], radius=R * 1.1, fill=LINE)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=R * 1.1, fill=fur)
    for i in range(26):                                                         # fur texture
        fxx = bx0 + 0.25 * u + (i % 6) * (bx1 - bx0 - 0.5 * u) / 5
        fyy = by0 + 0.5 * u + (i // 6) * (by1 - by0 - 0.8 * u) / 4.5
        d.arc([fxx - 0.3 * u, fyy - 0.22 * u, fxx + 0.3 * u, fyy + 0.22 * u], 200, 330, fill=(70, 68, 74), width=4)
    d.rounded_rectangle([bx0 + (bx1 - bx0) * (0.55 if k >= 0 else 0.1), by0 + 0.3 * u, bx0 + (bx1 - bx0) * (0.85 if k >= 0 else 0.4), by1 - 0.6 * u],
                        radius=R * 0.5, fill=(46, 44, 50))


def head_zed(d, cx, cy, u, face, k):
    g, gd = (154, 224, 72), (112, 182, 46)
    R = 2.35 * u
    for side in (-1, 1):                                                        # antennae
        ax = cx + side * 0.9 * u + k * 0.4 * u
        tx, ty = ax + side * 0.9 * u, cy - R - 1.9 * u
        d.line([(ax, cy - R * 0.8), (ax + side * 0.25 * u, cy - R - 0.8 * u), (tx, ty)], fill=LINE, width=int(0.36 * u))
        d.line([(ax, cy - R * 0.8), (ax + side * 0.25 * u, cy - R - 0.8 * u), (tx, ty)], fill=gd, width=int(0.2 * u))
        shaded_ell(d, tx, ty, 0.48 * u, 0.48 * u, g, 1)
    shaded_ell(d, cx, cy, R * 1.08 * (1 - 0.06 * abs(k)), R, g, 1 if k >= 0 else -1)
    fx = cx + k * 0.8 * u
    face2 = type(face)(brows=face.brows, look=face.look, blink=face.blink, mouth=face.mouth, bulge=face.bulge)
    eyes(d, fx, cy - 0.1 * u, u, face2, k, gap=0.95, w=0.75, h=0.95, iris=(62, 44, 96), lids=gd)
    for side in (-1, 1):
        if abs(k) < 0.85 or side * k > 0:
            d.ellipse([fx + side * 1.45 * u - 0.28 * u, cy + 0.75 * u, fx + side * 1.45 * u + 0.28 * u, cy + 1.0 * u], fill=(236, 150, 140))
    mouth(d, fx + k * 0.3 * u, cy + 1.2 * u, u, face.mouth if face.mouth != "X" else "smile", k, sz=1.5)


HEADS = {"atlas": (head_atlas, 9.0), "pike": (head_pike, 10.0), "zed": (head_zed, 12.0)}


@lru_cache(maxsize=6000)
def head_sprite(key, face, kq, u, world="default"):
    fn, size = HEADS[key]
    W = int(size * u)
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), W / 2, W * 0.62, u, face, kq / 10)
    bb = im.getbbox()
    return im.crop(bb), W / 2 - bb[0], W * 0.62 - bb[1]


# ------------------------------------------------------------------------------------------------ props
def prop(d, kind, x, y, u, f):
    if kind == "map":
        pts = [(x - 0.2 * u, y - 1.6 * u), (x + f * 2.0 * u, y - 1.85 * u), (x + f * 2.2 * u, y + 0.5 * u), (x, y + 0.7 * u)]
        d.polygon(pts, fill=(246, 244, 236), outline=LINE)
        for t in (0.33, 0.66):
            xa = x - 0.2 * u + (f * 2.2 * u + 0.2 * u) * t
            d.line([(xa, y - 1.7 * u), (xa + 0.05 * u, y + 0.6 * u)], fill=(200, 196, 186), width=4)
        d.line([(x + f * 0.4 * u, y - 0.6 * u), (x + f * 1.1 * u, y - 0.9 * u), (x + f * 1.7 * u, y - 0.3 * u)], fill=(190, 60, 50), width=4)
    elif kind == "cane":
        d.line([(x, y - 0.4 * u), (x + f * 0.1 * u, y + 5.2 * u)], fill=LINE, width=int(0.32 * u))
        d.arc([x - 0.5 * u, y - 0.9 * u, x + 0.5 * u, y + 0.1 * u], 180, 360, fill=LINE, width=int(0.32 * u))
    elif kind == "spear":
        d.line([(x - f * 0.2 * u, y + 2.2 * u), (x + f * 0.3 * u, y - 4.4 * u)], fill=(120, 84, 48), width=int(0.24 * u))
        d.polygon([(x + f * 0.3 * u, y - 4.4 * u), (x + f * 0.15 * u, y - 3.7 * u), (x + f * 0.55 * u, y - 3.75 * u)], fill=(184, 115, 51), outline=LINE)
    elif kind == "staff":
        d.line([(x, y - 0.6 * u), (x + f * 0.05 * u, y + 5.0 * u)], fill=(110, 78, 44), width=int(0.26 * u))
    elif kind == "rifle":
        d.line([(x - f * 0.3 * u, y + 2.0 * u), (x + f * 0.4 * u, y - 4.6 * u)], fill=(40, 40, 46), width=int(0.34 * u))
        d.line([(x - f * 0.35 * u, y + 2.4 * u), (x - f * 0.05 * u, y + 0.2 * u)], fill=(92, 60, 36), width=int(0.6 * u))
    elif kind == "book":
        d.rounded_rectangle([x - 1.0 * u, y - 1.3 * u, x + 1.0 * u, y + 0.3 * u], radius=6, fill=(120, 40, 40), outline=LINE, width=5)
        d.rectangle([x - 0.85 * u, y - 1.15 * u, x + 0.7 * u, y + 0.15 * u], fill=(246, 238, 220))
    elif kind == "stamp":
        d.rectangle([x - 0.35 * u, y - 1.3 * u, x + 0.35 * u, y - 0.45 * u], fill=(120, 70, 40), outline=LINE, width=4)
        d.rounded_rectangle([x - 0.75 * u, y - 0.5 * u, x + 0.75 * u, y - 0.05 * u], radius=6, fill=(190, 40, 40), outline=LINE, width=4)
    elif kind == "seal":
        d.ellipse([x - 0.45 * u, y - 0.45 * u, x + 0.45 * u, y + 0.45 * u], fill=(186, 30, 40), outline=LINE, width=4)
    elif kind == "scroll":
        d.rounded_rectangle([x - 0.3 * u, y - 1.4 * u, x + 0.3 * u, y + 0.4 * u], radius=0.25 * u, fill=(244, 230, 196), outline=LINE, width=5)
    elif kind == "pepper":
        d.ellipse([x - 0.35 * u, y - 0.35 * u, x + 0.35 * u, y + 0.35 * u], fill=(40, 30, 26), outline=LINE, width=3)
    elif kind == "chart":
        d.rounded_rectangle([x - 0.2 * u, y - 2.6 * u, x + f * 2.6 * u if f > 0 else x + 0.2 * u, y], radius=8, fill=(250, 250, 246), outline=LINE, width=5)
        x0 = min(x - 0.2 * u, x + f * 2.6 * u) + 0.4 * u
        for i, h in enumerate((0.6, 1.0, 1.5, 2.0)):
            d.rectangle([x0 + i * 0.55 * u, y - 0.3 * u - h * u, x0 + i * 0.55 * u + 0.35 * u, y - 0.3 * u], fill=(70, 150, 210))


# ------------------------------------------------------------------------------------------------ bodies
@dataclass(frozen=True)
class Build:
    leg: float          # thigh = shin length, head units
    torso: float        # torso height
    sw: float           # half shoulder width
    upper: float = 1.3
    fore: float = 1.2
    arm_w: float = 0.62
    leg_w: float = 0.8
    head_up: float = 1.75   # neck point to head centre


BUILD = {"atlas": Build(leg=1.55, torso=3.3, sw=1.45, upper=1.35, fore=1.3, head_up=1.95),
         "pike": Build(leg=1.5, torso=3.2, sw=1.35, upper=1.3, fore=1.25, head_up=1.6),
         "zed": Build(leg=0.75, torso=2.6, sw=1.2, upper=0.95, fore=0.9, arm_w=0.62, leg_w=0.8, head_up=2.6),
         "penny": Build(leg=1.15, torso=0.0, sw=0.0, upper=1.4, fore=1.3, arm_w=0.3, leg_w=0.34),
         "quill": Build(leg=0.45, torso=0.0, sw=0.0, upper=1.2, fore=1.1, arm_w=0.85, leg_w=0.5)}

KEYS = ("penny", "atlas", "quill", "zed", "pike")

# ------------------------------------------------------------------------------------------------ period costumes
# Each episode's world dresses the hosts in period clothing (visual bibles in projects/tiny-empires/visual_bibles/);
# faces, proportions and silhouettes stay the same. Unlisted fields fall back to the default design.
SKIN_A, SKIN_P = (242, 204, 166), (246, 210, 182)
LINEN = (244, 240, 230)
COSTUMES = {
    "default": {},
    "egypt_ok": {                                   # Old Kingdom Egypt, c. 2600 BC (01_egypt_old_kingdom_2600BC.md)
        "atlas": {"hat": "headcloth", "torso": "bare_kilt", "arms": (SKIN_A, SKIN_A), "legs": (LINEN, SKIN_A), "feet": SKIN_A, "socks": False,
                  "collar": True},
        "pike": {"hat": "wig", "torso": "bare_kilt", "arms": (SKIN_P, SKIN_P), "cuff": None, "legs": (LINEN, SKIN_P), "feet": SKIN_P,
                 "collar": False},
        "penny": {"hat": "nemes", "tie": "collar"},
        "quill": {"hat": "none", "collar": True},
        "zed": {"collar": True},
        "props": {"rifle": "spear", "map": "scroll", "cane": "staff", "chart": "scroll"},
    },
}
WORLD = "default"


def set_world(name):
    """Switch every host into a world's costumes (clears the sprite caches)."""
    global WORLD
    assert name in COSTUMES, name
    WORLD = name
    head_sprite.cache_clear()
    torso_sprite.cache_clear()


def C(key, field, default=None):
    return COSTUMES[WORLD].get(key, {}).get(field, default)


def collar(d, cx, cy, rx, u, n=3):
    """Broad collar (wesekh): bands of faience blue-green, gold and carnelian beads."""
    cols = [(47, 163, 154), (212, 165, 55), (181, 69, 43), (47, 163, 154)]
    for i in range(n, -1, -1):
        r = rx * (0.55 + 0.15 * i)
        d.chord([cx - r - 3, cy - r * 0.55 - 3, cx + r + 3, cy + r * 0.55 + 3], 0, 180, fill=LINE)
        d.chord([cx - r, cy - r * 0.55, cx + r, cy + r * 0.55], 0, 180, fill=cols[i % len(cols)])


def leg_len(key):
    return BUILD[key].leg


def draw(key, p, s=1.0, flip=False, view=0.6):
    u = 40 * s
    f = -1 if flip else 1
    v = max(0.0, min(1.0, view))
    k = f * v
    b = BUILD[key]
    Wt, Ht = int((20 if p.rot else 14) * u), int(16 * u)
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gx, gy = Wt / 2, Ht - 0.9 * u
    L = b.leg * u
    foot_h = 0.3 * u
    hip_y = gy - (2 * L + foot_h) - p.y * u
    hx = gx
    hip_sp = (0.55 if key not in ("penny",) else 0.5) * u * (1 - 0.6 * v)
    legs = []
    for side, th, kn in ((-1, p.th_r, p.kn_r), (1, p.th_l, p.kn_l)):
        hp = (hx + side * hip_sp, hip_y)
        knee = _down(*hp, th, L, f)
        ankle = _down(*knee, th - kn, L, f)
        legs.append((hp, knee, ankle))

    def draw_leg(hp, knee, ankle, back):
        dk = 0.85 if back else 1.0
        if key == "atlas":                                                      # khaki shorts, bare shins, socks, boots
            lc = C("atlas", "legs", ((190, 166, 120), (242, 204, 166)))
            limb(d, [hp, knee, ankle], [b.leg_w * u, 0.62 * u], [shade(lc[0], dk), shade(lc[1], dk)])
            if C("atlas", "socks", True):
                limb(d, [(ankle[0], ankle[1] - 0.4 * u), ankle], [0.7 * u], [shade((236, 228, 210), dk)])
            boot = shade(C("atlas", "feet", (112, 72, 42)), dk)
        elif key == "pike":
            lc = C("pike", "legs", ((40, 40, 48), (40, 40, 48)))
            limb(d, [hp, knee, ankle], [b.leg_w * u, 0.72 * u], [shade(lc[0], dk), shade(lc[1], dk)])
            boot = shade(C("pike", "feet", (24, 24, 28)), dk)
        elif key == "zed":
            limb(d, [hp, knee, ankle], [b.leg_w * u, 0.75 * u], [shade((134, 204, 60), dk)] * 2)
            boot = shade((134, 204, 60), dk)
        elif key == "quill":
            limb(d, [hp, knee, ankle], [b.leg_w * u, 0.4 * u], [shade((236, 170, 52), dk)] * 2)
            boot = (236, 170, 52)
        else:                                                                   # penny: thin dark legs, black shoes
            limb(d, [hp, knee, ankle], [b.leg_w * u, b.leg_w * u], [(34, 40, 50)] * 2)
            boot = (28, 30, 36)
        ax, ay = ankle
        fl = 0.55 * u * (1 - 0.4 * (1 - v)) + 0.25 * u
        ell(d, ax + f * 0.3 * u * v, ay + 0.05 * u, fl, 0.3 * u, boot, w=4)

    draw_leg(*legs[0], True)
    draw_leg(*legs[1], False)
    lean = p.lean * f
    T = b.torso * u

    def body_pt(dx, dy):
        rx, ry = _rot(dx, dy, lean)
        return hx + rx, hip_y + ry

    sw = b.sw * u
    fr_sh = body_pt(f * sw * (1 - 0.8 * v), -(T - 0.5 * u))
    bk_sh = body_pt(-f * sw * (1 - 0.8 * v), -(T - 0.5 * u))
    neck = body_pt(0, -T)
    back_dir = f if v >= 0.3 else -f

    def arm(sh_pt, sh, el, prop_kind, back):
        fdir = back_dir if back else f
        elbow = _down(*sh_pt, sh, b.upper * u, fdir)
        hand = _down(*elbow, sh + el, b.fore * u, fdir)
        dk = 0.84 if back else 1.0
        prop_kind = COSTUMES[WORLD].get("props", {}).get(prop_kind, prop_kind) if prop_kind else prop_kind
        if key == "atlas":
            ac = C("atlas", "arms", ((214, 190, 142), (242, 204, 166)))
            limb(d, [sh_pt, elbow, hand], [b.arm_w * u, 0.5 * u], [shade(ac[0], dk), shade(ac[1], dk)])
            glove = shade((242, 204, 166), dk)
        elif key == "pike":
            cuff = _down(*elbow, sh + el, b.fore * u * 0.75, fdir)
            ac = C("pike", "arms", ((206, 52, 38), (206, 52, 38)))
            cc = C("pike", "cuff", (30, 30, 36)) if "cuff" not in COSTUMES[WORLD].get("pike", {}) else C("pike", "cuff")
            limb(d, [sh_pt, elbow, cuff, hand], [b.arm_w * u, 0.56 * u, 0.6 * u], [shade(ac[0], dk), shade(ac[1], dk), shade(cc or ac[1], dk)])
            glove = shade((246, 210, 182), dk)
        elif key == "zed":
            limb(d, [sh_pt, elbow, hand], [b.arm_w * u, 0.55 * u], [shade((150, 220, 70), dk)] * 2)
            glove = shade((150, 220, 70), dk)
        elif key == "quill":
            limb(d, [sh_pt, elbow, hand], [b.arm_w * u, 0.7 * u], [shade((132, 92, 58), dk)] * 2)
            glove = shade((150, 108, 70), dk)
        else:
            limb(d, [sh_pt, elbow, hand], [b.arm_w * u, b.arm_w * u], [(34, 40, 50)] * 2)
            glove = (252, 252, 250)
        ell(d, hand[0], hand[1], 0.38 * u if key == "penny" else 0.32 * u, 0.38 * u if key == "penny" else 0.32 * u, glove, w=4)
        if prop_kind:
            prop(d, prop_kind, hand[0], hand[1], u, fdir)

    # ---- body
    if key == "penny":
        R = 3.1 * u
        cx, cy = hx, hip_y - R * 0.92
        wf = 1 - 0.5 * v
        th = 0.55 * u * v
        arm(body_pt(-f * (R * wf * 0.9), -R * 0.8), p.sh_r, p.el_r, p.prop_r, True)
        gold, edge = (238, 210, 120), (200, 162, 72)
        if v > 0.05:                                                            # coin edge, milled
            ell(d, cx - f * th, cy, R * wf, R, edge)
            for i in range(14):
                yy = cy - R * 0.9 + i * R * 0.13
                xx = cx - f * th - f * R * wf * math.sqrt(max(0.0, 1 - ((yy - cy) / R) ** 2)) * 0.98
                d.line([(xx, yy), (xx + f * th * 0.9, yy)], fill=shade(edge, 0.8), width=3)
        ell(d, cx, cy, R * wf, R, gold)
        d.ellipse([cx - R * wf * 0.86, cy - R * 0.86, cx + R * wf * 0.86, cy + R * 0.86], outline=shade(gold, 0.85), width=int(0.14 * u))
        d.polygon([(cx - f * R * wf * 0.5, cy - R * 0.75), (cx - f * R * wf * 0.2, cy - R * 0.8), (cx - f * R * wf * 0.75, cy + R * 0.2),
                   (cx - f * R * wf * 0.86, cy - R * 0.2)], fill=tint(gold, 0.45))              # shine streak
        fx = cx + k * R * 0.32
        eyes(d, fx, cy - 0.55 * u, u, p.face, k, gap=0.82, w=0.42, h=0.6, iris=(70, 50, 30), lids=shade(gold, 0.9))
        mouth(d, fx + k * 0.15 * u, cy + 0.75 * u, u, p.face.mouth, k, sz=1.35)
        bx, by = fx, cy + R * 0.62                                              # bow tie
        bw = 0.85 * u * (1 - 0.3 * v)
        if C("penny", "tie") == "collar":
            collar(d, bx, by - 0.2 * u, 1.4 * u * (1 - 0.2 * v), u)
            bw = 0
        if bw:
            d.polygon([(bx, by), (bx - bw, by - 0.42 * u), (bx - bw, by + 0.42 * u)], fill=(28, 30, 36), outline=LINE)
            d.polygon([(bx, by), (bx + bw, by - 0.42 * u), (bx + bw, by + 0.42 * u)], fill=(28, 30, 36), outline=LINE)
            ell(d, bx, by, 0.2 * u, 0.2 * u, (40, 44, 52), w=3)
        if C("penny", "hat") == "nemes":                                        # striped royal headcloth over the coin
            hx0, hy0, hw = cx, cy - R * 0.98, R * wf * 1.0
            pts = [(hx0 - hw * 1.05, hy0 + R * 0.75), (hx0 - hw * 0.8, hy0 - R * 0.2), (hx0, hy0 - R * 0.38), (hx0 + hw * 0.8, hy0 - R * 0.2),
                   (hx0 + hw * 1.05, hy0 + R * 0.75), (hx0 + hw * 0.78, hy0 + R * 0.3), (hx0 - hw * 0.78, hy0 + R * 0.3)]
            d.polygon(pts, fill=(212, 165, 55), outline=LINE)
            for i in range(1, 6):
                yy = hy0 - R * 0.3 + i * R * 0.14
                d.line([(hx0 - hw * 0.95, yy), (hx0 + hw * 0.95, yy)], fill=(47, 100, 154), width=max(4, int(0.12 * u)))
            d.line([(hx0 - hw * 0.78, hy0 + R * 0.3), (hx0 + hw * 0.78, hy0 + R * 0.3)], fill=LINE, width=4)
            arm(body_pt(f * (R * wf + 0.15 * u), -R * 0.8), p.sh_l, p.el_l, p.prop_l, False)
            hat = None
        if C("penny", "hat") == "nemes":
            pass
        else:
          hat, band = (36, 58, 70), (214, 184, 96)                              # top hat, tilted
          hs = Image.new("RGBA", (int(6 * u), int(6 * u)), (0, 0, 0, 0))
          hd = ImageDraw.Draw(hs)
          ox, oy = 3 * u, 5 * u
          hd.rounded_rectangle([ox - 1.25 * u - OUT, oy - 3.6 * u - OUT, ox + 1.25 * u + OUT, oy + OUT], radius=0.25 * u, fill=LINE)
          hd.rounded_rectangle([ox - 1.25 * u, oy - 3.6 * u, ox + 1.25 * u, oy], radius=0.25 * u, fill=hat)
          hd.rectangle([ox - 1.25 * u, oy - 1.0 * u, ox + 1.25 * u, oy - 0.45 * u], fill=band)
          hd.rectangle([ox - 0.85 * u, oy - 3.4 * u, ox - 0.5 * u, oy - 1.1 * u], fill=tint(hat, 0.25))
          hd.ellipse([ox - 2.2 * u - OUT, oy - 0.35 * u - OUT, ox + 2.2 * u + OUT, oy + 0.35 * u + OUT], fill=LINE)
          hd.ellipse([ox - 2.2 * u, oy - 0.35 * u, ox + 2.2 * u, oy + 0.35 * u], fill=shade(hat, 0.9))
          hs, (px, py) = rot_sprite(hs, (ox, oy), 14 * f)
          tx, ty = cx + f * 0.4 * u, cy - R * 0.92
          im.alpha_composite(hs, (int(tx - px), int(ty - py)))
          arm(body_pt(f * (R * wf + 0.15 * u), -R * 0.8), p.sh_l, p.el_l, p.prop_l, False)
    elif key == "quill":
        cx, cy = hx, hip_y - 2.6 * u
        br, belly = (132, 92, 58), (238, 222, 190)
        arm(body_pt(-f * 2.4 * u * (1 - 0.3 * v), -1.7 * u), p.sh_r, p.el_r, p.prop_r, True)
        for side in (-1, 1):
            tx = cx + side * 1.9 * u * (1 - 0.3 * v) + k * 0.4 * u
            d.polygon([(tx - 0.75 * u, cy - 2.6 * u), (tx + side * 0.6 * u, cy - 4.4 * u), (tx + 0.75 * u, cy - 2.4 * u)], fill=shade(br, 0.85), outline=LINE, width=OUT)
        shaded_ell(d, cx, cy, 2.9 * u * (1 - 0.12 * v), 3.5 * u, br, 1 if k >= 0 else -1)
        bx = cx + k * 0.6 * u
        d.ellipse([bx - 1.9 * u * (1 - 0.3 * v), cy + 0.3 * u, bx + 1.9 * u * (1 - 0.3 * v), cy + 3.2 * u], fill=belly)
        for row in range(3):
            for i in range(3 - row % 2):
                fx2 = bx + (i - 1 + 0.5 * (row % 2)) * 0.85 * u * (1 - 0.3 * v)
                fy2 = cy + 1.0 * u + row * 0.65 * u
                d.arc([fx2 - 0.33 * u, fy2 - 0.28 * u, fx2 + 0.33 * u, fy2 + 0.28 * u], 20, 160, fill=shade(belly, 0.75), width=4)
        fcx = cx + k * 0.9 * u
        d.ellipse([fcx - 2.3 * u * (1 - 0.25 * v), cy - 2.5 * u, fcx + 2.3 * u * (1 - 0.25 * v), cy + 0.3 * u], fill=tint(br, 0.25))
        eyes(d, fcx, cy - 1.1 * u, u, p.face, k, gap=1.05, w=0.8, h=0.82, iris=(40, 30, 24))
        for side in (-1, 1):                                                    # round glasses
            if abs(k) > 0.85 and side * k < 0:
                continue
            ex = fcx + side * 1.05 * u * (1 - 0.5 * abs(k))
            d.ellipse([ex - 0.98 * u, cy - 2.08 * u, ex + 0.98 * u, cy - 0.12 * u], outline=(40, 34, 30), width=int(0.15 * u))
        open_ = p.face.mouth not in ("X", "A", "smile", "smirk", "frown", "worried")
        nb = fcx + k * 0.6 * u
        d.polygon([(nb - 0.36 * u, cy - 0.25 * u), (nb + 0.36 * u, cy - 0.25 * u), (nb + k * 0.4 * u, cy + (0.95 if open_ else 0.7) * u)],
                  fill=(238, 170, 52), outline=LINE)
        if C("quill", "collar"):
            collar(d, bx, cy + 0.35 * u, 1.7 * u * (1 - 0.25 * v), u)
        if C("quill", "hat", "mortarboard") == "mortarboard":
            mb = (30, 30, 36)                                                   # mortarboard and tassel
            d.chord([cx - 1.7 * u, cy - 4.3 * u, cx + 1.7 * u, cy - 2.4 * u], 180, 360, fill=mb, outline=LINE, width=OUT)
            d.polygon([(cx - 2.6 * u, cy - 3.75 * u), (cx + 0.2 * u, cy - 4.55 * u), (cx + 2.6 * u, cy - 3.75 * u), (cx - 0.2 * u, cy - 3.0 * u)],
                      fill=mb, outline=LINE)
            d.line([(cx, cy - 3.78 * u), (cx - f * 2.1 * u, cy - 3.6 * u), (cx - f * 2.2 * u, cy - 2.4 * u)], fill=(222, 182, 60), width=int(0.13 * u))
            ell(d, cx - f * 2.2 * u, cy - 2.25 * u, 0.2 * u, 0.25 * u, (222, 182, 60), w=3)
        arm(body_pt(f * 2.75 * u * (1 - 0.12 * v), -1.7 * u), p.sh_l, p.el_l, p.prop_l, False)
    else:
        if v >= 0.3:
            arm(bk_sh, p.sh_r, p.el_r, p.prop_r, True)
        tor, piv = torso_sprite(key, round(lean), round(u, 2), round(k, 1), WORLD)
        im.alpha_composite(tor, (int(hx - piv[0]), int(hip_y - piv[1])))
        if v < 0.3:
            arm(bk_sh, p.sh_r, p.el_r, p.prop_r, True)
        hang = round(lean + p.head * f)
        spr, ox, oy = head_sprite(key, p.face, round(k * 10), round(u, 2), WORLD)
        spr, (ox, oy) = rot_sprite(spr, (ox, oy), hang)
        hdx, hdy = _rot(0, -b.head_up * u, hang)
        im.alpha_composite(spr, (int(neck[0] + hdx - ox), int(neck[1] + hdy - oy)))
        arm(fr_sh, p.sh_l, p.el_l, p.prop_l, False)
    if key not in ("penny", "quill"):
        pass
    # front leg drawn under the body for humans/alien would hide hips; draw it before the torso instead
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


@lru_cache(maxsize=2048)
def torso_sprite(key, ang, u, k, world="default"):
    """Human/alien torso drawn upright for view k, rotated about the hip; returns (image, (hip x, hip y))."""
    b = BUILD[key]
    T = b.torso * u
    v = abs(k)
    f = 1 if k >= 0 else -1
    sw = b.sw * u * (1 - 0.3 * v)
    W = int(2 * sw + 3 * u)
    H = int(T + 1.6 * u)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hx, hy = W / 2, T + 0.6 * u
    top = hy - T
    if key == "zed":
        g = (150, 220, 70)
        shaded_ell(d, hx, hy - T * 0.42, sw * 1.05, T * 0.62, g, f)
        d.ellipse([hx + k * 0.35 * u - sw * 0.62, hy - T * 0.62, hx + k * 0.35 * u + sw * 0.62, hy + 0.05 * u], fill=(206, 242, 150))
        if COSTUMES[world].get("zed", {}).get("collar"):
            collar(d, hx + k * 0.3 * u, hy - T * 0.98, sw * 0.9, u)
        return rot_sprite(im, (hx, hy), ang)
    cs = COSTUMES[world].get(key, {})
    if cs.get("torso") == "bare_kilt":                                          # bare chest, linen kilt, optional broad collar
        skin = cs["arms"][1]
        body = [(hx - sw * 0.88, top), (hx + sw * 0.88, top), (hx + sw * 0.95, top + 0.5 * u), (hx + sw * 0.82, hy + 0.2 * u),
                (hx - sw * 0.82, hy + 0.2 * u), (hx - sw * 0.95, top + 0.5 * u)]
        d.polygon([(x + (OUT if x > hx else -OUT), y + (OUT if y > hy - T / 2 else -OUT)) for x, y in body], fill=LINE)
        d.polygon(body, fill=skin)
        d.polygon([(hx - f * sw * 0.95, top + 0.5 * u), (hx - f * sw * 0.82, hy + 0.2 * u), (hx - f * sw * 0.45, hy + 0.2 * u),
                   (hx - f * sw * 0.55, top + 0.3 * u)], fill=shade(skin, 0.88))
        kt = hy - 0.9 * u                                                       # kilt from the waist down
        d.rectangle([hx - sw * 0.9, kt, hx + sw * 0.9, hy + 0.35 * u], fill=LINEN, outline=LINE, width=4)
        for i in range(1, 6):
            xx = hx - sw * 0.9 + i * sw * 0.3
            d.line([(xx, kt + 0.2 * u), (xx + k * 0.1 * u, hy + 0.3 * u)], fill=shade(LINEN, 0.82), width=3)
        d.rectangle([hx - sw * 0.92, kt - 0.15 * u, hx + sw * 0.92, kt + 0.15 * u], fill=shade(LINEN, 0.9), outline=LINE, width=3)
        if cs.get("collar"):
            collar(d, hx + k * 0.3 * u, top + 0.1 * u, sw * 0.95, u)
        return rot_sprite(im, (hx, hy), ang)
    col = {"atlas": (214, 190, 142), "pike": (206, 52, 38)}[key]
    body = [(hx - sw * 0.92, top), (hx + sw * 0.92, top), (hx + sw, top + 0.5 * u), (hx + sw * 0.9, hy + 0.2 * u),
            (hx - sw * 0.9, hy + 0.2 * u), (hx - sw, top + 0.5 * u)]
    d.polygon([(x + (OUT if x > hx else -OUT), y + (OUT if y > hy - T / 2 else -OUT)) for x, y in body], fill=LINE)
    d.polygon(body, fill=col)
    d.polygon([(hx - f * sw, top + 0.5 * u), (hx - f * sw * 0.9, hy + 0.2 * u), (hx - f * sw * 0.45, hy + 0.2 * u), (hx - f * sw * 0.55, top + 0.3 * u)],
              fill=shade(col, 0.84))
    c = hx + k * sw * 0.45                                                      # centre line turns with the view
    if key == "atlas":
        d.polygon([(c - 0.6 * u, top), (c, top + 0.75 * u), (c + 0.6 * u, top)], fill=(242, 204, 166))
        d.line([(c - 0.6 * u, top), (c, top + 0.75 * u), (c + 0.6 * u, top)], fill=LINE, width=4)
        for side in (-1, 1):                                                    # collar points and chest pockets
            d.polygon([(c + side * 0.6 * u, top), (c + side * 0.15 * u, top + 0.85 * u), (c + side * 1.0 * u, top + 0.3 * u)], fill=shade(col, 0.92), outline=LINE)
            if v > 0.85 and side * k < 0:
                continue
            px0 = c + side * (0.45 if side > 0 else 1.45) * u * (1 - 0.3 * v)
            d.rectangle([px0, top + 1.1 * u, px0 + 0.95 * u * (1 - 0.3 * v), top + 2.0 * u], fill=shade(col, 0.93), outline=LINE, width=3)
            d.polygon([(px0 - 0.05 * u, top + 1.05 * u), (px0 + 1.0 * u * (1 - 0.3 * v), top + 1.05 * u), (px0 + 0.47 * u, top + 1.4 * u)],
                      fill=shade(col, 0.88), outline=LINE)
        d.line([(c, top + 0.8 * u), (c, hy - 0.5 * u)], fill=shade(col, 0.75), width=4)
        d.rectangle([hx - sw * 0.92, hy - 0.55 * u, hx + sw * 0.92, hy - 0.15 * u], fill=(120, 80, 44), outline=LINE, width=3)
        d.rectangle([c - 0.22 * u, hy - 0.6 * u, c + 0.22 * u, hy - 0.1 * u], outline=(220, 190, 110), width=4)
    else:                                                                       # guard's tunic
        d.rectangle([hx - sw * 0.6, top - 0.05 * u, hx + sw * 0.6, top + 0.45 * u], fill=(30, 30, 36))
        for i in range(6):
            by = top + 0.8 * u + i * 0.42 * u
            if by < hy - 0.7 * u:
                ell(d, c, by, 0.12 * u, 0.12 * u, (226, 194, 96), w=2)
        d.rectangle([hx - sw * 0.92, hy - 0.75 * u, hx + sw * 0.92, hy - 0.35 * u], fill=(226, 194, 96), outline=LINE, width=3)
        d.rectangle([c - 0.25 * u, hy - 0.8 * u, c + 0.25 * u, hy - 0.3 * u], fill=(240, 214, 120), outline=LINE, width=3)
    return rot_sprite(im, (hx, hy), ang)
