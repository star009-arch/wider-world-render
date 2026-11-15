"""Flat 2D maps in the Premium 2D style (VOC pilot style guide, Stage 4c).

- land drawn as one shape (all Natural Earth 50m countries filled together, so NO modern borders show)
- one ink colour for the coastline (#2B2118), flat land colour with a soft cel-shade band inside the coast
- sea with animated wave dashes (sea_layer(t)), so a map is never a still picture
- route(), dot() and label helpers that draw on top, frame by frame

  base, proj = flatmap.base((lon0, lat0, lon1, lat1))      1920x1080 RGBA, proj(lon, lat) -> (x, y)
"""
from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

import shapefile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
NE = ROOT / "data/geo/naturalearth/ne_50m_admin_0_countries/ne_50m_admin_0_countries.shp"
W, H, S = 1920, 1080, 2
INK = (43, 33, 24)
SEA = (122, 172, 190)
SEA_DEEP = (96, 148, 172)
LAND = (226, 206, 160)
LAND_SHADE = (196, 170, 120)
FONT = "C:/Windows/Fonts/georgiab.ttf"


def _proj(bb):
    lon0, lat0, lon1, lat1 = bb
    # equirectangular scaled to fill 16:9, centred (keeps shapes honest at these latitudes)
    sx = W / (lon1 - lon0)
    sy = H / (lat1 - lat0)
    k = min(sx, sy)
    cx, cy = (lon0 + lon1) / 2, (lat0 + lat1) / 2
    return lambda lon, lat: (W / 2 + (lon - cx) * k, H / 2 - (lat - cy) * k)


@lru_cache(maxsize=1)
def _shapes():
    r = shapefile.Reader(str(NE))
    out = []
    for sh in r.shapes():
        pts, parts = sh.points, list(sh.parts) + [len(sh.points)]
        for a, b in zip(parts[:-1], parts[1:]):
            out.append(pts[a:b])
    return out


@lru_cache(maxsize=8)
def base(bb):
    pj = _proj(bb)
    big = lambda lon, lat: tuple(v * S for v in pj(lon, lat))
    img = Image.new("RGBA", (W * S, H * S), SEA + (255,))
    d = ImageDraw.Draw(img)
    # deeper water away from the coast: blurred land mask, inverted
    mask = Image.new("L", img.size, 0)
    dm = ImageDraw.Draw(mask)
    polys = []
    for ring in _shapes():
        P = [big(lo, la) for lo, la in ring]
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        if max(xs) < -50 or min(xs) > W * S + 50 or max(ys) < -50 or min(ys) > H * S + 50 or len(P) < 3:
            continue
        polys.append(P)
        dm.polygon(P, fill=255)
    shallow = mask.filter(ImageFilter.GaussianBlur(70 * S))
    deep = Image.new("RGBA", img.size, SEA_DEEP + (255,))
    img = Image.composite(img, deep, shallow.point(lambda v: min(255, v * 3)))
    d = ImageDraw.Draw(img)
    for P in polys:                                                   # 1) ink stroke round every shape
        d.line(P + [P[0]], fill=INK + (255,), width=7 * S, joint="curve")
    for P in polys:                                                   # 2) fills cover inner halves, so shared borders vanish
        d.polygon(P, fill=LAND + (255,))
    # cel-shade band just inside the coast (light from the upper left)
    inner = mask.filter(ImageFilter.MinFilter(19))                     # land shrunk by ~9 px: the band is mask minus inner
    band = Image.composite(Image.new("L", img.size, 0), mask, inner)
    band = band.filter(ImageFilter.GaussianBlur(3 * S)).point(lambda v: int(v * 0.55))
    shade = Image.new("RGBA", img.size, LAND_SHADE + (255,))
    img = Image.composite(shade, img, band)
    img = img.resize((W, H), Image.LANCZOS)
    return img, pj


def sea_waves(bb, t, n=140, seed=4):
    """Animated wave dashes on open water (drawn under the land so they never sit on a coast)."""
    img, pj = base(bb)
    rng = random.Random(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ph = rng.uniform(0, 6.28)
        dx = 14 * math.sin(t * 0.8 + ph)
        a = int(110 + 80 * math.sin(t * 1.3 + ph))
        px = int(x + dx) % W
        c = img.getpixel((px, int(y)))
        if abs(c[0] - SEA[0]) > 30 and abs(c[0] - SEA_DEEP[0]) > 30:  # skip land
            continue
        d.arc([x + dx - 16, y - 5, x + dx + 16, y + 5], 200, 340, fill=(235, 245, 248, max(0, a)), width=3)
    return layer


def font(size):
    return ImageFont.truetype(FONT, size)


def label(d, text, x, y, size=40, a=1.0, color=(250, 240, 214)):
    d.text((x, y), text, font=font(size), fill=color + (int(255 * a),), anchor="mm",
           stroke_width=max(3, size // 9), stroke_fill=INK + (int(255 * a),))


def ease(v):
    v = max(0.0, min(1.0, v))
    return v * v * (3 - 2 * v)


def route(d, pj, pts, frac, color=(200, 46, 40), width=8, dash=26):
    """Draw the first `frac` of a lon/lat polyline as an inked dashed route; return the head point and heading."""
    P = [pj(lo, la) for lo, la in pts]
    seg = [math.dist(a, b) for a, b in zip(P, P[1:])]
    total = sum(seg)
    want = total * max(0.0, min(1.0, frac))
    acc, drawn, head, ang = 0.0, [P[0]], P[0], 0.0
    for (a, b), L in zip(zip(P, P[1:]), seg):
        if acc + L >= want:
            k = (want - acc) / L if L else 0
            head = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
            drawn.append(head)
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            break
        drawn.append(b); acc += L
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        head = b
    # dashed line with an ink edge
    run = 0.0
    for a, b in zip(drawn, drawn[1:]):
        L = math.dist(a, b)
        steps = max(1, int(L // 6))
        for i in range(steps):
            p0 = (a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps)
            p1 = (a[0] + (b[0] - a[0]) * (i + 1) / steps, a[1] + (b[1] - a[1]) * (i + 1) / steps)
            if int(run // dash) % 2 == 0:
                d.line([p0, p1], fill=INK + (255,), width=width + 5)
                d.line([p0, p1], fill=color + (255,), width=width)
            run += L / steps
    return head, ang


def ship_icon(d, x, y, ang, t, s=1.0):
    """A tiny inked ship that bobs and keeps upright, sails filled."""
    bob = 3 * math.sin(t * 3.2)
    face = 1 if math.cos(ang) >= 0 else -1
    y += bob
    hull = [(x - 28 * s, y - 2 * s), (x + 28 * s, y - 2 * s), (x + 20 * s, y + 12 * s), (x - 20 * s, y + 12 * s)]
    d.polygon(hull, fill=(120, 74, 44, 255), outline=INK + (255,))
    d.line([(x - 28 * s, y - 2 * s), (x + 28 * s, y - 2 * s), (x + 20 * s, y + 12 * s), (x - 20 * s, y + 12 * s), (x - 28 * s, y - 2 * s)], fill=INK + (255,), width=3)
    for mx, h in ((-12, 34), (4, 42), (18, 30)):
        X = x + mx * s * face
        d.line([(X, y - 2 * s), (X, y - h * s)], fill=INK + (255,), width=3)
        belly = 4 * s * face * (1 + 0.25 * math.sin(t * 2 + mx))
        sail = [(X - 9 * s, y - (h - 4) * s), (X + 9 * s, y - (h - 4) * s), (X + 9 * s + belly, y - 10 * s), (X - 9 * s + belly, y - 10 * s)]
        d.polygon(sail, fill=(246, 238, 216, 255))
        d.line(sail + [sail[0]], fill=INK + (255,), width=2)
    fx = x + 4 * s * face
    wave = 3 * math.sin(t * 7)
    d.polygon([(fx, y - 44 * s), (fx + 16 * s * face, y - 41 * s + wave), (fx, y - 37 * s)], fill=(224, 110, 40, 255), outline=INK + (255,))


def dot(d, x, y, t, t0, color=(200, 46, 40)):
    if t < t0:
        return
    k = ease((t - t0) / 0.35)
    pulse = 1 + 0.15 * math.sin((t - t0) * 4)
    r = 11 * k * pulse
    d.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=INK + (255,))
    d.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))


def wind_arrow(d, x0, y0, x1, y1, t, n=4, color=(250, 250, 244)):
    """Moving wind streaks along a direction (for the Roaring Forties)."""
    for i in range(n):
        ph = ((t * 0.6) + i / n) % 1.0
        ax = x0 + (x1 - x0) * ph; ay = y0 + (y1 - y0) * ph + 26 * (i - n / 2)
        L = 90
        ang = math.atan2(y1 - y0, x1 - x0)
        bx, by = ax + L * math.cos(ang), ay + L * math.sin(ang)
        a = int(255 * math.sin(math.pi * ph))
        d.line([(ax, ay), (bx, by)], fill=INK + (a,), width=9)
        d.line([(ax, ay), (bx, by)], fill=color + (a,), width=5)
        d.polygon([(bx + 14 * math.cos(ang), by + 14 * math.sin(ang)), (bx + 9 * math.cos(ang + 2.2), by + 9 * math.sin(ang + 2.2)),
                   (bx + 9 * math.cos(ang - 2.2), by + 9 * math.sin(ang - 2.2))], fill=color + (a,))
