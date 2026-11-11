"""Pilot sets (Tiny Empires): richer backgrounds with gradients, depth layers and vignette lighting.

tabletop()  the show's signature: a parchment map of Bengal on a wooden table, the hosts walk on it
fort_v2()   Calcutta: Fort William by the river, warm afternoon
tent()      night: the secret meeting, a lantern-lit tent
plassey(rain)  the field at Plassey with its mango grove; grey storm version for the rain
palace_v2() the Nawab's durbar hall
endcard()   Tiny Empires logo card
All 1920x1080 RGB, drawn at 2x and reduced for clean edges. Free: Natural Earth for the coastline, Pillow for the rest.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

import sets as S

W, H = 1920, 1080
INK = (34, 28, 30)


def _grad(w, h, top, bottom):
    im = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)))
    return im


@lru_cache(maxsize=4)
def vignette(strength=0.55):
    """Dark corners, light centre, as an RGBA overlay."""
    m = Image.new("L", (W // 4, H // 4), 0)
    d = ImageDraw.Draw(m)
    for i in range(60):
        k = i / 60
        a = int(255 * strength * (1 - k) ** 2)
        d.ellipse([-W // 8 + k * W // 8, -H // 8 + k * H // 8, W // 4 + W // 8 - k * W // 8, H // 4 + H // 8 - k * H // 8], outline=a, width=3)
    m = m.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    ov = Image.new("RGBA", (W, H), (20, 12, 8, 0))
    ov.putalpha(m)
    return ov


def _finish(im, vig=0.5):
    im = im.convert("RGBA")
    im.alpha_composite(vignette(vig))
    return im.convert("RGB")


def _hills(d, y, color, amp, seed, w=W * 2):
    rnd = random.Random(seed)
    pts = [(0, y)]
    ph = [rnd.uniform(0, 6) for _ in range(3)]
    for x in range(0, w + 40, 40):
        yy = y - amp * (0.5 + 0.3 * math.sin(x / 260 + ph[0]) + 0.2 * math.sin(x / 97 + ph[1]))
        pts.append((x, yy))
    pts += [(w, H * 2), (0, H * 2)]
    d.polygon(pts, fill=color)


def _tree(d, x, y, s, leaf=(64, 128, 70), mango=True):
    d.rectangle([x - 9 * s, y - 70 * s, x + 9 * s, y], fill=(96, 64, 40))
    for (dx, dy, r) in ((0, -110, 62), (-48, -86, 46), (48, -86, 46), (-24, -140, 44), (26, -140, 44)):
        d.ellipse([x + (dx - r) * s, y + (dy - r) * s, x + (dx + r) * s, y + (dy + r) * s], fill=leaf, outline=INK, width=max(2, int(4 * s)))
    d.ellipse([x - 40 * s, y - 150 * s, x + 4 * s, y - 120 * s], fill=tuple(min(255, c + 30) for c in leaf))
    if mango:
        for (dx, dy) in ((-30, -80), (20, -100), (40, -70)):
            d.ellipse([x + (dx - 7) * s, y + (dy - 9) * s, x + (dx + 7) * s, y + (dy + 9) * s], fill=(236, 170, 50))


# ------------------------------------------------------------------------------------------------ the sets
@lru_cache(maxsize=1)
def tabletop():
    """Parchment map of lower Bengal on a wooden table: the Ganges delta, the Hooghly, Calcutta and Plassey marked."""
    big = Image.new("RGB", (W * 2, H * 2), (120, 78, 46))
    d = ImageDraw.Draw(big)
    for k in range(0, H * 2, 28):                                               # wood grain
        d.line([(0, k), (W * 2, k + 18 * math.sin(k / 90))], fill=(108, 70, 40), width=6)
    px0, py0, px1, py1 = 140, 120, W * 2 - 140, H * 2 - 120                     # the parchment
    d.rectangle([px0 + 24, py0 + 30, px1 + 24, py1 + 30], fill=(70, 44, 26))    # shadow on the table
    d.rectangle([px0, py0, px1, py1], fill=(238, 222, 184))
    sea = (176, 200, 196)
    lon0, lon1, lat0, lat1 = 85.0, 92.5, 20.6, 26.4                             # lower Bengal

    def P(lon, lat):
        return (px0 + (lon - lon0) / (lon1 - lon0) * (px1 - px0), py0 + (lat1 - lat) / (lat1 - lat0) * (py1 - py0))
    d.rectangle([px0, py0, px1, py1], fill=sea)
    try:
        for poly in S._countries():                                            # coastline only; no modern borders
            pts = [P(x, y) for x, y in poly]
            if len(pts) > 2:
                d.polygon(pts, fill=(236, 220, 180))
    except Exception:
        pass
    d.polygon([P(*p) for p in S.BENGAL], fill=(230, 196, 120))                  # the region in question, tinted
    rivers = [[(88.1, 21.6), (88.2, 22.2), (88.35, 22.57), (88.4, 23.0), (88.25, 23.8), (88.1, 24.4), (88.0, 25.0)],      # Hooghly-Bhagirathi
              [(88.0, 25.0), (88.6, 24.5), (89.4, 24.0), (90.2, 23.6), (90.6, 23.0), (91.0, 22.3)],                      # Padma
              [(85.0, 25.4), (86.5, 25.3), (87.5, 25.2), (88.0, 25.0)]]
    for r in rivers:
        d.line([P(*p) for p in r], fill=(110, 156, 190), width=26, joint="curve")
    rnd = random.Random(3)
    for _ in range(900):                                                        # paper texture
        x, y = rnd.uniform(px0, px1), rnd.uniform(py0, py1)
        c = rnd.randint(196, 226)
        d.point((x, y), fill=(c, c - 14, c - 46))
    for k in range(12):                                                         # worn edges
        d.rectangle([px0 + k, py0 + k, px1 - k, py1 - k], outline=(214 - k * 5, 192 - k * 5, 150 - k * 5))
    f = S.font(64)
    for name, lon, lat in (("CALCUTTA", 88.36, 22.57), ("PLASSEY", 88.25, 23.8), ("MURSHIDABAD", 88.27, 24.18)):
        x, y = P(lon, lat)
        d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(170, 40, 40), outline=INK, width=5)
        d.text((x + 34, y), name, font=f, fill=(70, 44, 30), anchor="lm")
    d.text(P(89.6, 24.9), "BENGAL", font=S.font(130), fill=(120, 80, 40), anchor="mm")
    d.text(P(89.2, 21.0), "Bay of Bengal", font=S.font(70), fill=(70, 100, 120), anchor="mm")
    cx, cy = px1 - 230, py0 + 230                                               # compass rose
    d.polygon([(cx, cy - 150), (cx + 30, cy), (cx, cy + 150), (cx - 30, cy)], fill=(120, 80, 40))
    d.polygon([(cx - 150, cy), (cx, cy - 30), (cx + 150, cy), (cx, cy + 30)], fill=(150, 110, 60))
    d.text((cx, cy - 190), "N", font=S.font(60), fill=(90, 60, 30), anchor="mm")
    im = big.resize((W, H), Image.LANCZOS)
    return _finish(im, 0.6)


@lru_cache(maxsize=1)
def fort_v2():
    base = S.fort().convert("RGB")
    sky = _grad(W, 420, (150, 196, 232), (236, 220, 190))
    mask = Image.new("L", (W, 420), 0)
    mk = ImageDraw.Draw(mask)
    px = base.load()
    for y in range(420):                                                        # repaint only the flat sky colour
        for x in range(0, W):
            if px[x, y] == base.getpixel((5, 5)):
                mk.point((x, y), 255)
    base.paste(sky, (0, 0), mask)
    d = ImageDraw.Draw(base)
    for k in range(5):                                                          # shimmer on the river
        y = 470 + k * 14
        d.line([(60 + k * 80, y), (300 + k * 80, y)], fill=(200, 226, 236), width=4)
    return _finish(base, 0.45)


@lru_cache(maxsize=1)
def tent():
    big = _grad(W * 2, H * 2, (16, 20, 52), (44, 40, 74))
    d = ImageDraw.Draw(big)
    rnd = random.Random(7)
    for _ in range(220):
        x, y, r = rnd.uniform(0, W * 2), rnd.uniform(0, H * 0.9), rnd.choice((2, 3, 4))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(240, 236, 210))
    d.ellipse([W * 2 - 520, 140, W * 2 - 300, 360], fill=(244, 238, 210))                                  # moon
    d.ellipse([W * 2 - 470, 120, W * 2 - 270, 330], fill=(18, 22, 54))
    _hills(d, 1380, (26, 34, 50), 160, 2)
    d.rectangle([0, 1560, W * 2, H * 2], fill=(36, 44, 40))
    glow = Image.new("L", (W * 2, H * 2), 0)                                    # lantern glow inside the tent
    gd = ImageDraw.Draw(glow)
    for i in range(40):
        r = 900 - i * 20
        gd.ellipse([W - r, 1100 - r * 0.7, W + r, 1100 + r * 0.7], fill=int(4 + i * 4.5))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    tent_l = [(W - 1250, 1700), (W, 300), (W + 1250, 1700)]
    d.polygon([(p[0] + 30, p[1] + 20) for p in tent_l], fill=(14, 12, 20))
    d.polygon(tent_l, fill=(186, 150, 96), outline=INK, width=10)
    d.polygon([(W - 520, 1700), (W, 640), (W + 520, 1700)], fill=(96, 62, 34))  # open flap, warm interior
    for k in (-1, 1):
        d.polygon([(W, 640), (W + k * 520, 1700), (W + k * 700, 1700)], fill=(214, 176, 112), outline=INK)
    warm = Image.new("RGB", (W * 2, H * 2), (255, 190, 90))
    big = Image.composite(warm, big, glow.point(lambda v: int(v * 0.45)))
    d = ImageDraw.Draw(big)
    d.rectangle([W - 40, 860, W + 40, 960], fill=(60, 44, 30), outline=INK, width=6)                    # lantern
    d.ellipse([W - 30, 880, W + 30, 950], fill=(255, 220, 120))
    d.rectangle([0, 1700, W * 2, H * 2], fill=(52, 46, 40))
    im = big.resize((W, H), Image.LANCZOS)
    return _finish(im, 0.65)


@lru_cache(maxsize=2)
def plassey(rain=False):
    top, bot = ((92, 104, 120), (150, 156, 160)) if rain else ((128, 186, 230), (232, 226, 200))
    big = _grad(W * 2, H * 2, top, bot)
    d = ImageDraw.Draw(big)
    if rain:
        rnd = random.Random(5)
        for _ in range(16):
            x, y, r = rnd.uniform(0, W * 2), rnd.uniform(40, 420), rnd.uniform(140, 260)
            d.ellipse([x - r * 1.6, y - r * 0.6, x + r * 1.6, y + r * 0.6], fill=(76, 84, 98))
    _hills(d, 880, (150, 170, 150) if not rain else (110, 120, 116), 120, 1)
    _hills(d, 1000, (118, 152, 92) if not rain else (92, 112, 80), 90, 4)
    d.rectangle([0, 1080, W * 2, H * 2], fill=(124, 160, 84) if not rain else (96, 120, 70))
    rnd = random.Random(11)
    for x in range(-60, W * 2 + 120, 150):                                      # the mango grove (Lakshabagh) at the back
        _tree(d, x + rnd.uniform(-30, 30), 1090 + rnd.uniform(-10, 20), 1.05, leaf=(56, 116, 64) if not rain else (48, 92, 56))
    for _ in range(300):                                                        # grass tufts
        x, y = rnd.uniform(0, W * 2), rnd.uniform(1180, H * 2)
        d.line([(x, y), (x - 6, y - 18), (x + 2, y), (x + 8, y - 16)], fill=(92, 128, 64) if not rain else (74, 100, 56), width=4)
    im = big.resize((W, H), Image.LANCZOS)
    return _finish(im, 0.6 if rain else 0.45)


@lru_cache(maxsize=1)
def palace_v2():
    base = S.palace().convert("RGB")
    d = ImageDraw.Draw(base, "RGBA")
    for x in range(0, W, 320):                                                  # light shafts through the arches
        d.polygon([(x + 70, 140), (x + 170, 140), (x + 330, 880), (x + 150, 880)], fill=(255, 240, 200, 40))
    return _finish(base, 0.5)


@lru_cache(maxsize=1)
def endcard():
    im = _grad(W, H, (60, 40, 30), (24, 16, 14))
    d = ImageDraw.Draw(im)
    for r in range(600, 0, -20):
        d.ellipse([W / 2 - r * 1.6, 420 - r * 0.6, W / 2 + r * 1.6, 420 + r * 0.6], fill=(70 + (600 - r) // 12, 46 + (600 - r) // 18, 30))
    f = S.font(170)
    d.text((W / 2 + 8, 300 + 10), "TINY EMPIRES", font=f, fill=(20, 12, 8), anchor="mm")
    d.text((W / 2, 300), "TINY EMPIRES", font=f, fill=(250, 206, 80), stroke_width=8, stroke_fill=(90, 40, 20), anchor="mm")
    d.text((W / 2, 440), "Big stories. Small characters.", font=S.font(64), fill=(244, 232, 206), anchor="mm")
    return im


SETS = {"tabletop": tabletop, "fort2": fort_v2, "tent": tent, "plassey": lambda: plassey(False), "plassey_rain": lambda: plassey(True),
        "palace2": palace_v2, "endcard": endcard}
