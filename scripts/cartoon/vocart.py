"""Premium 2D drawing toolkit for the VOC pilot (style guide Stage 4c): all artwork drawn in code, no generated images.

Style: one warm ink outline (#2B2118), flat colour with one cel-shade step and a soft highlight, layered depth with
atmospheric haze, light from a fixed sun direction per scene. Everything is drawn at 2x (S) and reduced for clean edges.

Building blocks used by vocsets.py (backgrounds), vocship.py (ships, boats) and vocdemo.py (shots):
  Layer             a 2x RGBA canvas with inked shape helpers (blob, poly, smooth path, ellipse, line)
  smooth(pts)       Catmull-Rom curve through points (organic outlines)
  sky()             vertical gradient sky with sun glow
  water_band()      animated outlined wave crests over a water area (call every frame)
  palm()            coconut palm with swaying fronds (call every frame with t)
  cloud()           outlined cartoon cloud
  haze()            depth haze over a finished layer
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

W, H, S = 1920, 1080, 2
INK = (43, 33, 24)


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def shade(c, k=0.78):
    """Cel-shade colour: darker and slightly cooler/warmer like the approved Test 2 shading."""
    return (int(c[0] * k * 0.96), int(c[1] * k * 0.98), int(min(255, c[2] * k * 1.06)))


def light(c, k=0.25):
    return mix(c, (255, 250, 236), k)


def smooth(pts, n=8, closed=True):
    """Catmull-Rom spline through the points."""
    P = list(pts)
    if len(P) < 3:
        return P
    out = []
    m = len(P)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = P[(i - 1) % m] if closed or i > 0 else P[0]
        p1 = P[i]
        p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if closed or i + 2 < m else P[-1]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(P[-1])
    return out


class Layer:
    """A 2x canvas. Coordinates passed to helpers are in 1x units (1920x1080)."""

    def __init__(self, w=W, h=H, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * S, h * S), fill)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def _P(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def poly(self, pts, fill, ink=4.0, ink_col=INK, a=255):
        P = self._P(pts)
        if fill is not None:
            self.d.polygon(P, fill=tuple(fill[:3]) + (a,))
        if ink:
            self.d.line(P + [P[0]], fill=ink_col + (a,), width=max(1, int(ink * S)), joint="curve")
            r = ink * S / 2
            for x, y in P[::max(1, len(P) // 24)]:
                pass

    def blob(self, pts, fill, ink=4.0, n=8, a=255, ink_col=INK):
        self.poly(smooth(pts, n), fill, ink, ink_col=ink_col, a=a)

    def line(self, pts, col=INK, w=4.0, a=255, curve=False):
        P = self._P(smooth(pts, 8, closed=False) if curve else pts)
        self.d.line(P, fill=tuple(col[:3]) + (a,), width=max(1, int(w * S)), joint="curve")

    def ellipse(self, box, fill, ink=4.0, a=255):
        x0, y0, x1, y1 = box
        self.d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=None if fill is None else tuple(fill[:3]) + (a,),
                       outline=INK + (a,) if ink else None, width=max(1, int(ink * S)) if ink else 0)

    def rect(self, box, fill, ink=4.0, a=255):
        x0, y0, x1, y1 = box
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, ink, a=a)

    def shade_poly(self, pts, col, a=255):
        """A shade or highlight shape without outline (drawn inside an already inked shape)."""
        self.d.polygon(self._P(pts), fill=tuple(col[:3]) + (a,))

    def out(self, scale=True):
        return self.im.resize((self.w, self.h), Image.LANCZOS) if scale else self.im


def sky(top, mid, bottom, horizon=620, sun=None, sun_col=(255, 236, 190)):
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = min(1.0, y / horizon)
        c = mix(top, mid, min(1, t / 0.6)) if t < 0.6 else mix(mid, bottom, (t - 0.6) / 0.4)
        d.line([(0, y), (W, y)], fill=c + (255,))
    if sun:
        g = Image.new("L", (W, H), 0)
        ImageDraw.Draw(g).ellipse([sun[0] - 260, sun[1] - 260, sun[0] + 260, sun[1] + 260], fill=150)
        g = g.filter(ImageFilter.GaussianBlur(120))
        im = Image.composite(Image.new("RGBA", (W, H), sun_col + (255,)), im, g)
    return im


def haze(im, col, k):
    """Atmospheric perspective: blend a finished layer towards the sky colour (keeps its alpha)."""
    r, g, b, a = im.split()
    flat = Image.merge("RGB", (r, g, b))
    flat = Image.blend(flat, Image.new("RGB", im.size, col), k)
    out = flat.convert("RGBA")
    out.putalpha(a)
    return out


def cloud(L: Layer, cx, cy, s, col=(255, 248, 236), shade_col=None, ink=3.0):
    shade_col = shade_col or shade(col, 0.88)
    bumps = ((0, 0, 1.0), (-0.95, 0.22, 0.7), (0.95, 0.24, 0.74), (-0.42, -0.34, 0.66), (0.48, -0.28, 0.6))
    pts = []
    for i in range(48):
        a = i / 48 * math.tau
        best = 0
        for bx, by, r in bumps:
            # radial extent of the union of circles along angle a
            dx, dy = math.cos(a), math.sin(a) * 0.62
            proj = bx * dx + by * dy
            disc = proj * proj - (bx * bx + by * by - r * r)
            if disc >= 0:
                best = max(best, proj + math.sqrt(disc))
        y = math.sin(a) * best * 0.62 * 60 * s
        pts.append((cx + math.cos(a) * best * 60 * s, cy + min(y, 18 * s)))
    L.poly(pts, col, ink)
    L.shade_poly([(x, max(y, cy + 2 * s)) for x, y in pts if y >= cy - 4 * s], shade_col, 200)
    L.line([(x, y) for x, y in pts if y >= cy + 17 * s] or [(cx, cy)], INK, ink)


def palm(L: Layer, x, y, h, t, lean=0.0, sway=1.0, trunk=(150, 112, 76), leaf=(79, 127, 58), seed=0, ink=3.0, nuts=True):
    """Coconut palm: curved ringed trunk, crown of fronds that sway with the wind (t in seconds)."""
    rng = random.Random(seed)
    wind = sway * (math.sin(t * 1.3 + seed) * 0.6 + math.sin(t * 2.9 + seed * 2) * 0.25)
    top = (x + lean * h + wind * 6, y - h)
    # trunk: a tapering curved band
    pts_l, pts_r = [], []
    for i in range(13):
        k = i / 12
        bend = math.sin(k * math.pi * 0.5) * (lean * h + wind * 6 * k * k)
        cxk, cyk = x + bend, y - h * k
        w = (h * 0.055) * (1 - 0.45 * k)
        pts_l.append((cxk - w, cyk)); pts_r.append((cxk + w, cyk))
    L.poly(pts_l + pts_r[::-1], trunk, ink)
    L.shade_poly(pts_l[:] + [(p[0] + (r[0] - p[0]) * 0.45, p[1]) for p, r in zip(pts_l[::-1], pts_r[::-1])], shade(trunk, 0.8), 170)
    for i in range(1, 12):
        L.line([pts_l[i], pts_r[i]], shade(trunk, 0.65), 1.6)
    # fronds
    n = 9
    for i in range(n):
        base = -math.pi / 2 + (i - (n - 1) / 2) * (math.pi * 1.25 / n) + rng.uniform(-0.08, 0.08)
        ln = h * rng.uniform(0.42, 0.55)
        fl = wind * 0.09 * (1 + i % 3 * 0.3)
        spine = []
        for k in range(9):
            q = k / 8
            ang = base + fl * q + (q * q) * 1.1 * (1 if math.cos(base) >= 0 else -1) * 0.9
            droop = q * q * ln * 0.55
            spine.append((top[0] + math.cos(base + fl * q) * ln * q, top[1] + math.sin(base + fl * q) * ln * q * 0.75 + droop))
        left, right = [], []
        for k, (sx, sy) in enumerate(spine):
            q = k / 8
            wdt = ln * 0.13 * math.sin(math.pi * min(1, q * 1.15)) + 1
            if k + 1 < len(spine):
                dx, dy = spine[k + 1][0] - sx, spine[k + 1][1] - sy
            else:
                dx, dy = sx - spine[k - 1][0], sy - spine[k - 1][1]
            nrm = math.hypot(dx, dy) or 1
            nx, ny = -dy / nrm, dx / nrm
            left.append((sx + nx * wdt, sy + ny * wdt)); right.append((sx - nx * wdt * 0.8, sy - ny * wdt * 0.8))
        col = leaf if i % 2 else shade(leaf, 0.86)
        L.poly(left + right[::-1], col, ink * 0.8)
        L.line(spine, shade(leaf, 0.6), 1.6)
        # leaflet cuts: short ink ticks along the frond edge
        for k in range(2, 8):
            L.line([left[k], (left[k][0] + (left[k][0] - spine[k][0]) * 0.5, left[k][1] + (left[k][1] - spine[k][1]) * 0.5 + 4)], INK, 1.4)
    if nuts:
        for dx in (-7, 4, 12):
            L.ellipse((top[0] + dx - 7, top[1] + 4, top[0] + dx + 7, top[1] + 18), (110, 128, 52), 2)


def water_band(L: Layer, y0, y1, t, base, crest=(240, 250, 248), speed=18.0, rows=9, seed=1, ink=2.4, persp=True, density=1.0):
    """Animated sea: rows of crests that drift steadily (each crest keeps its identity, so nothing jumps between frames).
    Crests are irregular in size and spacing, larger and faster near the viewer (perspective)."""
    for r in range(rows):
        rng = random.Random(seed * 1000 + r)
        k = r / max(1, rows - 1)
        y = y0 + (y1 - y0) * (k ** 1.6 if persp else k)
        size = 9 + 30 * k
        spacing = (90 + 260 * k) / density
        n = int(W / spacing) + 3
        offs = [rng.uniform(0, spacing * 0.8) for _ in range(n)]
        sizes = [rng.uniform(0.55, 1.35) for _ in range(n)]
        keep = [rng.random() < 0.82 for _ in range(n)]
        drift = (t * speed * (0.4 + 1.2 * k)) % (spacing * n)
        dark = shade(base, 0.8)
        for i in range(n):
            if not keep[i]:
                continue
            cx = (i * spacing + offs[i] + drift) % (spacing * n) - spacing
            sz = size * sizes[i]
            bob = math.sin(t * 1.6 + i * 1.3 + r) * 2.5 * (0.3 + k)
            life = 0.55 + 0.45 * math.sin(t * 0.9 + i * 2.1 + r)           # crests swell and fade
            cy = y + bob
            L.d.arc([(cx - sz * 1.7) * S, (cy - sz * 0.32) * S, (cx + sz * 1.7) * S, (cy + sz * 0.5) * S],
                    205, 335, fill=dark + (int(170 * life),), width=max(2, int((1.8 + 2.6 * k) * S)))
            L.d.arc([(cx - sz) * S, (cy - sz * 0.42) * S, (cx + sz) * S, (cy + sz * 0.28) * S],
                    215, 325, fill=crest + (int((120 + 110 * k) * life),), width=max(2, int((1.4 + 2.4 * k) * S)))


def gradient_rect(L: Layer, box, top, bottom):
    x0, y0, x1, y1 = box
    for y in range(int(y0 * S), int(y1 * S)):
        k = (y / S - y0) / max(1, (y1 - y0))
        L.d.line([(x0 * S, y), (x1 * S, y)], fill=mix(top, bottom, k) + (255,))


def ground_texture(L: Layer, box, col, n=220, seed=3, a=110):
    """Small inked tufts and pebbles so ground is never a flat fill."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        k = 0.4 + (y - y0) / max(1, y1 - y0)
        if rng.random() < 0.6:
            for dx in (-1, 0, 1):
                L.line([(x, y), (x + dx * 5 * k, y - 9 * k)], shade(col, 0.7), 1.4 * k, a)
        else:
            L.ellipse((x - 3 * k, y - 2 * k, x + 3 * k, y + 2 * k), shade(col, 0.85), 1.0, a)


def glow(size, col, r):
    g = Image.new("RGBA", size, col + (0,))
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse([size[0] / 2 - r, size[1] / 2 - r, size[0] / 2 + r, size[1] / 2 + r], fill=255)
    g.putalpha(m.filter(ImageFilter.GaussianBlur(r / 2)))
    return g


def union_shape(draw_fn, col, shade_col=None, ink=3.0, a=255, shade_dy=0.35, size=(W, H)):
    """Draw overlapping round shapes as ONE inked form (clouds, smoke, foliage): draw_fn(d, k) draws filled shapes on a
    2x 'L' mask (k = 2x scale factor). Returns an RGBA layer at 1x: fill, a cel-shaded underside and an outer ink line only."""
    w, h = size
    m = Image.new("L", (w * S, h * S), 0)
    draw_fn(ImageDraw.Draw(m), S)
    edge = m.filter(ImageFilter.MaxFilter(max(3, int(ink * S) | 1)))
    out = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", out.size, INK + (a,)), (0, 0), edge)
    out.paste(Image.new("RGBA", out.size, tuple(col[:3]) + (a,)), (0, 0), m)
    if shade_col:
        off = int(shade_dy * 40 * S)
        sh = Image.new("L", m.size, 0)
        sh.paste(m, (0, 0))
        up = Image.new("L", m.size, 0)
        up.paste(m, (int(-0.15 * off), -off))
        from PIL import ImageChops
        under = ImageChops.subtract(m, up)
        out.paste(Image.new("RGBA", out.size, tuple(shade_col[:3]) + (a,)), (0, 0), under)
    return out.resize((w, h), Image.LANCZOS)


def puff_cloud(cx, cy, s, rng_seed=0, col=(255, 246, 236), shade_col=None, ink=3.0):
    """A bumpy cartoon cloud as one inked form, with a flat-ish base and shaded underside."""
    rng = random.Random(rng_seed)
    bumps = [(-1.2, 0.15, 0.55), (-0.6, -0.2, 0.75), (0.1, -0.38, 0.85), (0.8, -0.15, 0.7), (1.35, 0.15, 0.5)]
    bumps += [(rng.uniform(-1.0, 1.0), rng.uniform(-0.25, 0.05), rng.uniform(0.4, 0.6)) for _ in range(3)]

    def fn(d, k):
        for bx, by, r in bumps:
            R = r * 60 * s
            d.ellipse([(cx + bx * 60 * s - R) * k, (cy + by * 60 * s - R) * k, (cx + bx * 60 * s + R) * k, (cy + by * 60 * s + R) * k], fill=255)
        d.ellipse([(cx - 1.75 * 60 * s) * k, (cy - 0.1 * 60 * s) * k, (cx + 1.75 * 60 * s) * k, (cy + 0.5 * 60 * s) * k], fill=255)
    return union_shape(fn, col, shade_col or shade(col, 0.88), ink, shade_dy=0.22)



def grade(frame, sun=(1500, 200), warm=(255, 226, 170), strength=0.22, vignette=0.32, cool_shadow=(40, 50, 80)):
    """Cinematic finish: a warm glow from the sun side, and a soft cool vignette."""
    w, h = frame.size
    g = Image.new("L", (w // 4, h // 4), 0)
    ImageDraw.Draw(g).ellipse([sun[0] / 4 - 260, sun[1] / 4 - 200, sun[0] / 4 + 260, sun[1] / 4 + 200], fill=255)
    g = g.filter(ImageFilter.GaussianBlur(70)).resize((w, h), Image.BILINEAR).point(lambda v: int(v * strength))
    out = Image.composite(Image.new("RGBA", (w, h), warm + (255,)), frame, g)
    v = Image.new("L", (w // 4, h // 4), 0)
    ImageDraw.Draw(v).ellipse([-w / 4 * 0.12, -h / 4 * 0.2, w / 4 * 1.12, h / 4 * 1.2], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(60)).resize((w, h), Image.BILINEAR)
    dark = Image.blend(out, Image.new("RGBA", (w, h), cool_shadow + (255,)), vignette)
    return Image.composite(out, dark, v)


# ------------------------------------------------------------------------------------------------ v2 finish: texture, grain, grade
def noise_tex(size, scale=60, seed=0, octaves=3):
    """Soft painted-texture noise (L image, mid-grey 128 +/-) for large surfaces: ground, walls, sky."""
    import numpy as np
    w, h = size
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype="float32")
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale / (2 ** o)))
        small = rng.standard_normal((h // s + 2, w // s + 2)).astype("float32")
        im = Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-6) * 255).astype("uint8")).resize((w + 2 * s, h + 2 * s), Image.BICUBIC)
        acc += amp * (np.asarray(im, dtype="float32")[s:s + h, s:s + w] - 128)
        tot += amp
        amp *= 0.5
    acc = acc / tot
    return Image.fromarray(np.clip(128 + acc * 1.6, 0, 255).astype("uint8"))


def texturize(im, tex, strength=0.14):
    """Modulate the brightness of an RGBA layer by a texture (keeps alpha)."""
    import numpy as np
    a = np.asarray(im).astype("float32")
    t = (np.asarray(tex.resize(im.size)).astype("float32") - 128) / 128 * strength
    a[..., :3] = np.clip(a[..., :3] * (1 + t[..., None]), 0, 255)
    return Image.fromarray(a.astype("uint8"), "RGBA")


_GRAIN = {}


def grade2(frame, sun=(1600, 240), t=0.0, sat=1.18, contrast=1.12, warm=(255, 214, 150), cool=(40, 70, 110), vignette=0.38, grain=0.035,
           glow=0.30):
    """Cinematic finish v2: sun bloom, contrast S-curve, saturation, split toning (warm highlights / cool shadows),
    vignette and fine film grain (changes every frame)."""
    import numpy as np
    from PIL import ImageEnhance
    f = frame.convert("RGB")
    w, h = f.size
    g = Image.new("L", (w // 4, h // 4), 0)
    ImageDraw.Draw(g).ellipse([sun[0] / 4 - 220, sun[1] / 4 - 170, sun[0] / 4 + 220, sun[1] / 4 + 170], fill=255)
    g = g.filter(ImageFilter.GaussianBlur(60)).resize((w, h), Image.BILINEAR).point(lambda v: int(v * glow))
    f = Image.composite(Image.new("RGB", (w, h), warm), f, g)
    f = ImageEnhance.Color(f).enhance(sat)
    a = np.asarray(f).astype("float32") / 255.0
    a = np.clip(0.5 + (a - 0.5) * contrast, 0, 1)
    lum = a.mean(axis=2, keepdims=True)
    wc = np.array(warm, dtype="float32") / 255.0
    cc = np.array(cool, dtype="float32") / 255.0
    a = a + (wc - 0.5) * 0.10 * np.clip(lum - 0.5, 0, 1) * 2 + (cc - 0.5) * 0.14 * np.clip(0.5 - lum, 0, 1) * 2
    yy, xx = np.mgrid[0:h, 0:w].astype("float32")
    d = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2)
    a = a * (1 - vignette * np.clip(d - 0.55, 0, 1)[..., None] ** 1.4)
    key = (w, h, int(t * 24) % 6)
    if key not in _GRAIN:
        _GRAIN[key] = np.random.default_rng(key[2]).normal(0, 1, (h, w, 1)).astype("float32")
    a = a + _GRAIN[key] * grain * 0.5
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"), "RGB")



def soft_form(draw_fn, top, bottom, blur=5, a=255, rim=None, size=(W, H)):
    """A soft painted form (smoke, cloud) with no ink line: gradient from top colour to bottom colour, soft edge,
    optional bright rim on the sun side. draw_fn(d, k) draws filled shapes on a 2x mask."""
    import numpy as np
    w, h = size
    m = Image.new("L", (w * S, h * S), 0)
    draw_fn(ImageDraw.Draw(m), S)
    m = m.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
    arr = np.asarray(m)
    ys = np.where(arr.max(axis=1) > 8)[0]
    if len(ys) == 0:
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y0, y1 = ys.min(), ys.max() + 1
    grad = Image.new("RGB", (1, max(2, y1 - y0)))
    for i in range(grad.height):
        grad.putpixel((0, i), mix(top, bottom, (i / (grad.height - 1)) ** 0.8))
    col = Image.new("RGB", (w, h), top)
    col.paste(grad.resize((w, y1 - y0)), (0, int(y0)))
    out = col.convert("RGBA")
    out.putalpha(m.point(lambda v: v * a // 255))
    if rim:                                                           # sun-side rim light
        col2, dx, dy = rim
        sh = Image.new("L", (w, h), 0)
        sh.paste(m, (int(-dx), int(-dy)))
        from PIL import ImageChops
        edge = ImageChops.subtract(m, sh).filter(ImageFilter.GaussianBlur(2)).point(lambda v: min(255, v * 2) * a // 255)
        out.paste(Image.new("RGBA", (w, h), col2 + (255,)), (0, 0), edge)
    return out


def soft_cloud(cx, cy, s, seed=0, top=(255, 238, 206), bottom=(178, 168, 166), rim=(255, 248, 226)):
    rng = random.Random(seed)
    bumps = [(rng.uniform(-1.6, 1.6), rng.uniform(-0.5, 0.15), rng.uniform(0.35, 0.8)) for _ in range(9)]

    def fn(d, k):
        for bx, by, r in bumps:
            R = r * 60 * s
            d.ellipse([(cx + bx * 60 * s - R) * k, (cy + by * 60 * s - R * 0.8) * k, (cx + bx * 60 * s + R) * k, (cy + by * 60 * s + R * 0.8) * k], fill=255)
        d.ellipse([(cx - 2.0 * 60 * s) * k, (cy - 0.05 * 60 * s) * k, (cx + 2.0 * 60 * s) * k, (cy + 0.35 * 60 * s) * k], fill=255)
    return soft_form(fn, top, bottom, blur=3, a=245, rim=(rim, 6, -4))
