"""Period costume kit shared by the hosts (hosts3.py) and the historical cast (people.py), in the v3 cartoon style.

Hats and helmets, hair, beards, neckwear, garments, cloaks, arm pieces, held props, and animals (a stocky Mongolian horse,
a taller European/Mamluk horse, a Bactrian camel) with a walk / gallop / pace leg cycle.
Every piece follows the visual bibles in projects/tiny-empires/visual_bibles/ (04_east_india_company, 05_mongol_empire).

Geometry conventions (same as hosts3/people): u = pixels per head unit at 2x; k = view (-1..1, sign = facing); f = facing
sign; a head is a circle of radius R around (cx, cy); a torso runs from `top` (neck) to the hip line `hy`; hem = robe length
below the hip in u.
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageDraw

from hosts3 import LINE, OUT, ell, shade, tint, limb, _down

GOLD = (212, 170, 64)
IRON = (111, 114, 118)
STEEL = (163, 167, 171)
MAIL = (138, 140, 142)
WHITE = (246, 244, 236)
BUFF = (214, 186, 132)


def poly(d, pts, fill, w=5):
    d.polygon([(float(x), float(y)) for x, y in pts], fill=fill, outline=LINE, width=w)


def band(d, a, b, w, col, ow=4):
    """A thick outlined strap from a to b."""
    d.line([a, b], fill=LINE, width=int(w + 2 * ow))
    d.line([a, b], fill=col, width=max(1, int(w)))


def fur(d, box, col, u):
    x0, y0, x1, y1 = box
    rr = max(1, min((y1 - y0), (x1 - x0)) / 2)
    d.rounded_rectangle([x0 - OUT, y0 - OUT, x1 + OUT, y1 + OUT], radius=rr + OUT, fill=LINE)
    d.rounded_rectangle([x0, y0, x1, y1], radius=rr, fill=col)
    n = max(3, int((x1 - x0) / (0.3 * u)))
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        yy = y0 + (y1 - y0) * (0.38 if i % 2 else 0.62)
        d.arc([x - 0.15 * u, yy - 0.11 * u, x + 0.15 * u, yy + 0.11 * u], 200, 340, fill=shade(col, 0.7), width=3)


def dots(d, pts, r, col, line=True):
    for x, y in pts:
        if line:
            d.ellipse([x - r - 2, y - r - 2, x + r + 2, y + r + 2], fill=LINE)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)


def mail_tex(d, box, u, col=MAIL):
    x0, y0, x1, y1 = box
    s = 0.22 * u
    y, row = y0 + s * 0.5, 0
    while y < y1:
        x = x0 + (s * 0.5 if row % 2 else 0) + s * 0.3
        while x < x1:
            d.arc([x - s * 0.4, y - s * 0.3, x + s * 0.4, y + s * 0.3], 20, 160, fill=shade(col, 0.68), width=2)
            x += s
        y += s * 0.7
        row += 1


# ================================================================================================ hats
HATS = {"mongol_fur", "mongol_flaps", "warming_cap", "mongol_brim", "mongol_helmet", "boqta", "turban", "turban_black", "mughal_turban",
        "bengal_turban", "marwari_turban", "futou", "jin_helmet", "kettle_hat", "great_helm", "kabuto", "kalawta", "mamluk_helmet", "hood",
        "hood_down", "flat_cap", "tudor_bonnet", "capotain", "morion", "monmouth", "tricorne", "fur_cap", "scribe_cap"}
HAT_COL = {"mongol_fur": ((92, 64, 44), (150, 112, 74)), "mongol_flaps": ((70, 58, 52), (170, 132, 90)), "warming_cap": ((242, 240, 232), (236, 230, 216)),
           "mongol_brim": ((60, 50, 44), (110, 84, 60)), "mongol_helmet": (IRON, (90, 42, 30)), "boqta": ((142, 31, 27), GOLD),
           "turban": (WHITE, (156, 42, 42)), "turban_black": ((24, 24, 26), (60, 60, 62)), "mughal_turban": ((236, 226, 200), GOLD),
           "bengal_turban": (WHITE, GOLD), "marwari_turban": ((196, 52, 44), (236, 190, 60)), "futou": ((28, 26, 26), (28, 26, 26)),
           "jin_helmet": ((92, 95, 99), (43, 53, 80)), "kettle_hat": (STEEL, MAIL), "great_helm": (STEEL, GOLD), "kabuto": ((40, 36, 34), (163, 36, 42)),
           "kalawta": ((217, 169, 46), (180, 130, 30)), "mamluk_helmet": (STEEL, MAIL), "hood": ((138, 36, 39), (110, 30, 32)),
           "hood_down": ((120, 100, 80), (120, 100, 80)), "flat_cap": ((30, 30, 34), (60, 60, 64)), "tudor_bonnet": ((24, 24, 28), WHITE),
           "capotain": ((30, 28, 28), (90, 70, 50)), "morion": (STEEL, (200, 160, 70)), "monmouth": ((130, 70, 50), (100, 54, 40)),
           "tricorne": ((26, 26, 30), WHITE), "fur_cap": ((70, 50, 36), (128, 92, 60)), "scribe_cap": ((46, 63, 107), (92, 64, 44))}
TALL_HATS = {"boqta"}


def hat_back(d, kind, cx, cy, R, u, k, c1=None, c2=None):
    """Parts of the headwear behind the head (neck guards, hoods, veils). Call before the head is drawn."""
    if kind not in HATS:
        return
    c1, c2 = c1 or HAT_COL[kind][0], c2 or HAT_COL[kind][1]
    f = 1 if k >= 0 else -1
    if kind == "mongol_helmet":                                                   # lamellar / leather aventail to the shoulders
        box = [cx - 1.2 * R, cy - 0.7 * R, cx + 1.2 * R, cy + 1.35 * R]
        d.rounded_rectangle([box[0] - OUT, box[1] - OUT, box[2] + OUT, box[3] + OUT], radius=0.3 * R + OUT, fill=LINE)
        d.rounded_rectangle(box, radius=0.3 * R, fill=c2)
        for i in range(1, 5):
            y = box[1] + i * (box[3] - box[1]) / 5
            d.line([(box[0] + 4, y), (box[2] - 4, y)], fill=shade(c2, 0.7), width=3)
    elif kind in ("mamluk_helmet", "kettle_hat"):                                 # mail aventail / mail coif
        box = [cx - 1.22 * R, cy - 1.15 * R, cx + 1.22 * R, cy + 1.5 * R]
        d.rounded_rectangle([box[0] - OUT, box[1] - OUT, box[2] + OUT, box[3] + OUT], radius=0.6 * R + OUT, fill=LINE)
        d.rounded_rectangle(box, radius=0.6 * R, fill=c2)
        mail_tex(d, box, u, c2)
    elif kind == "jin_helmet":
        box = [cx - 1.18 * R, cy - 0.7 * R, cx + 1.18 * R, cy + 1.25 * R]
        d.rounded_rectangle([box[0] - OUT, box[1] - OUT, box[2] + OUT, box[3] + OUT], radius=0.4 * R + OUT, fill=LINE)
        d.rounded_rectangle(box, radius=0.4 * R, fill=c2)
    elif kind == "kabuto":                                                        # flaring laced neck guard (shikoro)
        pts = [(cx - 1.12 * R, cy - 0.8 * R), (cx + 1.12 * R, cy - 0.8 * R), (cx + 1.75 * R, cy + 0.65 * R), (cx - 1.75 * R, cy + 0.65 * R)]
        poly(d, pts, c1)
        for i in range(1, 5):
            t = i / 5
            y = cy - 0.8 * R + t * 1.45 * R
            w = 1.12 * R + t * 0.63 * R
            d.line([(cx - w, y), (cx + w, y)], fill=c2, width=max(4, int(0.12 * u)))
    elif kind == "boqta":                                                         # hood behind, tied under the chin
        box = [cx - 1.2 * R, cy - 0.9 * R, cx + 1.2 * R, cy + 1.5 * R]
        d.rounded_rectangle([box[0] - OUT, box[1] - OUT, box[2] + OUT, box[3] + OUT], radius=0.5 * R + OUT, fill=LINE)
        d.rounded_rectangle(box, radius=0.5 * R, fill=shade(c1, 0.75))
    elif kind == "hood":
        ell(d, cx, cy + 0.15 * R, 1.32 * R, 1.48 * R, shade(c1, 0.9))
        band(d, (cx - f * 1.0 * R, cy + 0.4 * R), (cx - f * 1.55 * R, cy + 2.5 * R), 0.32 * R, shade(c1, 0.85))
    elif kind == "hood_down":
        ell(d, cx - f * 0.1 * R, cy + 1.35 * R, 0.95 * R, 0.42 * R, shade(c1, 0.9))


def hat(d, kind, cx, cy, R, u, k, c1=None, c2=None, jewel=False):
    """Headwear on top of the head (after the face). The brow line sits at about cy - 0.48 R."""
    if kind not in HATS:
        return
    c1, c2 = c1 or HAT_COL[kind][0], c2 or HAT_COL[kind][1]
    f = 1 if k >= 0 else -1
    v = abs(k)
    fx = cx + k * 0.35 * R
    if kind in ("mongol_fur", "mongol_flaps", "warming_cap", "fur_cap"):
        tall = 1.95 if kind != "warming_cap" else 1.85
        pts = [(cx - 0.92 * R, cy - 0.6 * R), (cx - 0.86 * R, cy - 1.25 * R), (cx - 0.5 * R, cy - 1.72 * R), (fx, cy - tall * R),
               (cx + 0.5 * R, cy - 1.72 * R), (cx + 0.86 * R, cy - 1.25 * R), (cx + 0.92 * R, cy - 0.6 * R)]
        poly(d, pts, c1)
        d.polygon([(cx - f * 0.86 * R, cy - 1.2 * R), (cx - f * 0.5 * R, cy - 1.65 * R), (cx - f * 0.2 * R, cy - 1.0 * R)], fill=shade(c1, 0.85))
        if kind == "mongol_flaps":
            for side in (-1, 1):
                if side * k > 0.5:
                    continue
                x = cx + side * 0.98 * R
                fur(d, [x - 0.3 * R, cy - 0.75 * R, x + 0.3 * R, cy + 0.55 * R], c2, u)
        fur(d, [cx - 1.13 * R, cy - 0.98 * R, cx + 1.13 * R, cy - 0.42 * R], c2, u)
        if kind == "mongol_fur":
            ell(d, fx, cy - tall * R - 0.12 * R, 0.16 * R, 0.16 * R, (158, 43, 37), w=3)          # red knob
    elif kind in ("mongol_brim", "scribe_cap"):
        pk = (fx, cy - 1.78 * R)
        if kind == "mongol_brim":                                                 # feather sweeping back from the crown
            fp = [pk, (pk[0] - f * 0.7 * R, pk[1] - 0.75 * R), (pk[0] - f * 1.5 * R, pk[1] - 0.55 * R), (pk[0] - f * 1.9 * R, pk[1] + 0.05 * R),
                  (pk[0] - f * 1.3 * R, pk[1] - 0.2 * R), (pk[0] - f * 0.5 * R, pk[1] - 0.1 * R)]
            poly(d, fp, (232, 222, 196), w=4)
            d.line([pk, (pk[0] - f * 1.6 * R, pk[1] - 0.3 * R)], fill=(170, 150, 120), width=3)
        pts = [(cx - 0.74 * R, cy - 0.6 * R), (cx - 0.7 * R, cy - 1.3 * R), (cx - 0.35 * R, cy - 1.7 * R), pk, (cx + 0.35 * R, cy - 1.7 * R),
               (cx + 0.7 * R, cy - 1.3 * R), (cx + 0.74 * R, cy - 0.6 * R)]
        poly(d, pts, c1)
        brim = [(cx - 1.38 * R, cy - 0.95 * R), (cx - 1.12 * R, cy - 0.42 * R), (cx + 1.12 * R, cy - 0.42 * R), (cx + 1.38 * R, cy - 0.95 * R),
                (cx + 0.78 * R, cy - 0.7 * R), (cx - 0.78 * R, cy - 0.7 * R)]
        poly(d, brim, c2)
    elif kind in ("mongol_helmet", "mamluk_helmet"):
        peak = 2.0 if kind == "mongol_helmet" else 2.1
        pts = [(cx - 1.04 * R, cy - 0.45 * R), (cx - 0.98 * R, cy - 1.15 * R), (cx - 0.55 * R, cy - 1.7 * R), (cx, cy - peak * R),
               (cx + 0.55 * R, cy - 1.7 * R), (cx + 0.98 * R, cy - 1.15 * R), (cx + 1.04 * R, cy - 0.45 * R)]
        poly(d, pts, c1)
        d.polygon([(cx - f * 0.9 * R, cy - 1.15 * R), (cx - f * 0.5 * R, cy - 1.6 * R), (cx - f * 0.35 * R, cy - 0.7 * R), (cx - f * 0.9 * R, cy - 0.6 * R)],
                  fill=shade(c1, 0.85))
        d.polygon([(cx + f * 0.25 * R, cy - 1.55 * R), (cx + f * 0.55 * R, cy - 1.3 * R), (cx + f * 0.45 * R, cy - 0.9 * R)], fill=tint(c1, 0.4))
        d.rounded_rectangle([cx - 1.06 * R, cy - 0.66 * R, cx + 1.06 * R, cy - 0.4 * R], radius=4, fill=shade(c1, 0.75), outline=LINE, width=4)
        if kind == "mongol_helmet":
            band(d, (cx, cy - peak * R), (cx, cy - (peak + 0.45) * R), 0.12 * R, shade(c1, 0.7))
            d.polygon([(cx - 0.05 * R, cy - (peak + 0.42) * R), (cx - f * 0.6 * R, cy - (peak + 0.1) * R), (cx - f * 0.75 * R, cy - (peak - 0.4) * R),
                       (cx - f * 0.15 * R, cy - (peak + 0.1) * R)], fill=(143, 42, 34), outline=LINE)   # red horse-hair plume
        else:
            ell(d, cx, cy - peak * R - 0.1 * R, 0.1 * R, 0.14 * R, c1, w=3)
    elif kind == "boqta":
        d.chord([cx - 1.08 * R - OUT, cy - 1.3 * R - OUT, cx + 1.08 * R + OUT, cy + 0.3 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.08 * R, cy - 1.3 * R, cx + 1.08 * R, cy + 0.3 * R], 180, 360, fill=c1)
        tube = [(fx - 0.42 * R, cy - 1.05 * R), (fx - 0.55 * R, cy - 3.7 * R), (fx + 0.55 * R, cy - 3.7 * R), (fx + 0.42 * R, cy - 1.05 * R)]
        for i in range(4):                                                        # feather sprig on the flat top
            a = -0.5 + i * 0.33
            band(d, (fx + a * 0.4 * R, cy - 4.0 * R), (fx + a * 1.2 * R, cy - 5.0 * R), 0.07 * R, (60, 70, 90), ow=2)
            ell(d, fx + a * 1.2 * R, cy - 5.0 * R, 0.12 * R, 0.2 * R, (40, 90, 110), w=2)
        poly(d, tube, c1)
        d.rectangle([fx - 0.5 * R, cy - 2.5 * R, fx + 0.5 * R, cy - 2.25 * R], fill=c2)
        top = [(fx - 0.85 * R, cy - 4.1 * R), (fx + 0.85 * R, cy - 4.1 * R), (fx + 0.62 * R, cy - 3.62 * R), (fx - 0.62 * R, cy - 3.62 * R)]
        poly(d, top, c2)
        dots(d, [(fx, cy - (1.4 + 0.32 * i) * R) for i in range(3)], 0.07 * R, (246, 240, 230), line=False)
        d.line([(cx - 0.95 * R, cy + 0.2 * R), (cx - 0.5 * R, cy + 1.25 * R)], fill=shade(c1, 0.6), width=4)   # chin ties
        d.line([(cx + 0.95 * R, cy + 0.2 * R), (cx + 0.5 * R, cy + 1.25 * R)], fill=shade(c1, 0.6), width=4)
    elif kind in ("turban", "turban_black"):
        if kind == "turban" and jewel:                                            # small coloured cap peak (kulah) in the middle
            d.chord([cx - 0.55 * R, cy - 2.1 * R, cx + 0.55 * R, cy - 0.9 * R], 180, 360, fill=c2, outline=LINE, width=4)
        ell(d, cx, cy - 1.0 * R, 1.22 * R, 0.72 * R, c1)
        for i in range(3):
            y = cy - 1.45 * R + i * 0.32 * R
            d.arc([cx - 1.15 * R, y - 0.25 * R, cx + 1.15 * R, y + 0.55 * R], 200 + i * 6, 330, fill=shade(c1, 0.72) if kind == "turban" else (70, 70, 74),
                  width=4)
        if jewel:
            ell(d, fx, cy - 0.85 * R, 0.16 * R, 0.2 * R, GOLD, w=3)
    elif kind in ("mughal_turban", "bengal_turban", "marwari_turban"):
        hgt = {"mughal_turban": 1.05, "bengal_turban": 0.85, "marwari_turban": 1.2}[kind]
        tilt = -7 * f if kind == "mughal_turban" else 0
        ox, oy = cx, cy - 0.9 * R
        rel = [(-1.1, 0.42), (-1.15, 0.42 - hgt * 0.7), (-0.9, 0.42 - hgt), (0.85, 0.42 - hgt - (0.08 if kind == "mughal_turban" else 0)),
               (1.15, 0.42 - hgt * 0.72), (1.1, 0.42)]
        if kind == "marwari_turban":
            rel = [(-1.1, 0.42), (-1.18, -0.3), (-0.6, 0.42 - hgt), (f * 0.6, 0.42 - hgt - 0.15), (1.2, -0.25), (1.1, 0.42)]

        def P(x, y):
            a = math.radians(tilt)
            x, y = x * R, y * R
            return ox + x * math.cos(a) - y * math.sin(a), oy + x * math.sin(a) + y * math.cos(a)
        pts = [P(*p) for p in rel]
        smooth = []
        for i in range(len(pts)):                                                 # round the corners (Chaikin)
            a, b = pts[i], pts[(i + 1) % len(pts)]
            smooth += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        poly(d, smooth, c1)
        n = 4 if kind != "bengal_turban" else 3
        for i in range(n):                                                        # wraps
            y0 = 0.3 - i * (hgt - 0.1) / n
            if kind == "bengal_turban":
                d.line([P(-1.08, y0), P(1.08, y0 - 0.05)], fill=shade(c1, 0.75), width=4)
            else:
                d.line([P(-1.08, y0), P(1.05, y0 - 0.32)], fill=shade(c1, 0.72), width=4)
        if kind in ("mughal_turban", "marwari_turban"):
            d.line([P(-1.08, 0.12), P(1.08, -0.2)], fill=c2, width=max(4, int(0.12 * R)))          # gold-striped band
        if kind == "marwari_turban":
            for i in range(9):
                x, y = P(-0.9 + (i % 3) * 0.8, 0.2 - (i // 3) * 0.35)
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=c2)
        if jewel:                                                                 # sarpech and heron plume (kalgi)
            jx, jy = P(k * 0.45, 0.2 - hgt * 0.6)
            band(d, (jx, jy), (jx - f * 0.25 * R, jy - 1.15 * R), 0.09 * R, (40, 34, 30), ow=2)
            ell(d, jx - f * 0.28 * R, jy - 1.2 * R, 0.12 * R, 0.22 * R, (40, 34, 30), w=2)
            ell(d, jx, jy, 0.22 * R, 0.28 * R, GOLD, w=3)
            ell(d, jx, jy, 0.1 * R, 0.12 * R, (168, 35, 58), line=None)
            dots(d, [P(k * 0.45 + dx, 0.2 - hgt * 0.6 + 0.35) for dx in (-0.3, 0.0, 0.3)], 0.06 * R, (246, 240, 230), line=False)
    elif kind == "futou":                                                         # black official cap with stiff wings
        wl = 1.6 * (1 - 0.65 * v)
        for side in (-1, 1):
            x0 = cx + side * 0.8 * R
            x1 = cx + side * (0.8 + wl) * R
            d.rectangle([min(x0, x1) - 3, cy - 1.18 * R - 3, max(x0, x1) + 3, cy - 1.0 * R + 3], fill=LINE)
            d.rectangle([min(x0, x1), cy - 1.18 * R, max(x0, x1), cy - 1.0 * R], fill=c1)
        ell(d, cx - f * 0.15 * R, cy - 1.45 * R, 0.6 * R, 0.5 * R, c1)
        d.chord([cx - 1.02 * R - OUT, cy - 1.75 * R - OUT, cx + 1.02 * R + OUT, cy + 0.65 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.02 * R, cy - 1.75 * R, cx + 1.02 * R, cy + 0.65 * R], 180, 360, fill=c1)
    elif kind == "jin_helmet":
        d.chord([cx - 1.06 * R - OUT, cy - 1.9 * R - OUT, cx + 1.06 * R + OUT, cy + 0.95 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.06 * R, cy - 1.9 * R, cx + 1.06 * R, cy + 0.95 * R], 180, 360, fill=c1)
        d.chord([cx - 0.9 * R, cy - 1.75 * R, cx + 0.1 * R, cy + 0.8 * R], 200, 260, fill=tint(c1, 0.3))
        d.rectangle([cx - 1.08 * R, cy - 0.62 * R, cx + 1.08 * R, cy - 0.42 * R], fill=shade(c1, 0.7), outline=LINE, width=3)
        ell(d, cx, cy - 1.95 * R, 0.14 * R, 0.14 * R, GOLD, w=3)
    elif kind == "kettle_hat":
        for side in (-1, 1):                                                      # coif framing the cheeks
            if side * k > 0.6:
                continue
            x = cx + side * 1.0 * R
            d.rounded_rectangle([x - 0.25 * R, cy - 0.6 * R, x + 0.25 * R, cy + 1.0 * R], radius=6, fill=MAIL, outline=LINE, width=3)
        d.chord([cx - 0.98 * R - OUT, cy - 1.9 * R - OUT, cx + 0.98 * R + OUT, cy + 0.0 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 0.98 * R, cy - 1.9 * R, cx + 0.98 * R, cy + 0.0 * R], 180, 360, fill=c1)
        brim = [(cx - 1.6 * R, cy - 0.38 * R), (cx - 0.95 * R, cy - 0.98 * R), (cx + 0.95 * R, cy - 0.98 * R), (cx + 1.6 * R, cy - 0.38 * R),
                (cx + 1.45 * R, cy - 0.25 * R), (cx - 1.45 * R, cy - 0.25 * R)]
        poly(d, brim, shade(c1, 0.88))
        d.line([(cx, cy - 1.88 * R), (cx, cy - 0.98 * R)], fill=shade(c1, 0.7), width=4)
    elif kind == "great_helm":                                                    # flat-topped cylinder, eye slit, breaths
        box = [cx - 1.12 * R, cy - 1.32 * R, cx + 1.12 * R, cy + 1.25 * R]
        d.rounded_rectangle([box[0] - OUT, box[1] - OUT, box[2] + OUT, box[3] + OUT], radius=0.35 * R, fill=LINE)
        d.rounded_rectangle(box, radius=0.3 * R, fill=c1)
        d.rectangle([cx - f * 1.12 * R, box[1] + 4, cx - f * 0.55 * R, box[3] - 4], fill=shade(c1, 0.85))
        d.rectangle([cx - 0.95 * R, cy - 0.1 * R, fx - 0.12 * R, cy + 0.1 * R], fill=(20, 20, 24))
        d.rectangle([fx + 0.12 * R, cy - 0.1 * R, cx + 0.95 * R, cy + 0.1 * R], fill=(20, 20, 24))
        d.rectangle([fx - 0.12 * R, cy - 1.3 * R, fx + 0.12 * R, cy + 1.2 * R], fill=c2, outline=LINE, width=3)
        d.rectangle([fx - 0.7 * R, cy + 0.32 * R, fx + 0.7 * R, cy + 0.5 * R], fill=c2, outline=LINE, width=3)
        for i in range(3):
            for j in range(2):
                x, y = fx + f * (0.35 + 0.22 * i) * R, cy + (0.75 + 0.22 * j) * R
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(20, 20, 24))
    elif kind == "kabuto":
        d.chord([cx - 1.08 * R - OUT, cy - 1.95 * R - OUT, cx + 1.08 * R + OUT, cy + 0.85 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.08 * R, cy - 1.95 * R, cx + 1.08 * R, cy + 0.85 * R], 180, 360, fill=c1)
        for i in range(-2, 3):                                                    # plates and rivets (hoshi)
            x = cx + i * 0.38 * R + k * 0.1 * R
            d.line([(x, cy - 0.6 * R), (cx + i * 0.12 * R, cy - 1.88 * R)], fill=(70, 66, 62), width=3)
            for j in range(3):
                yy = cy - 0.75 * R - j * 0.38 * R
                xx = x + (cx + i * 0.12 * R - x) * (j + 0.5) / 3.5
                d.ellipse([xx - 4, yy - 4, xx + 4, yy + 4], fill=(150, 146, 140))
        for side in (-1, 1):                                                      # fukigaeshi, turned-back wings
            if side * k > 0.6:
                continue
            x = cx + side * 1.1 * R
            poly(d, [(x, cy - 0.65 * R), (x + side * 0.55 * R, cy - 0.95 * R), (x + side * 0.6 * R, cy - 0.2 * R), (x, cy - 0.15 * R)], (163, 36, 42) if c2 is None else c2)
        d.rectangle([cx - 1.08 * R, cy - 0.66 * R, cx + 1.08 * R, cy - 0.46 * R], fill=(60, 56, 52), outline=LINE, width=3)
        for side in (-1, 1):                                                      # gilt kuwagata horns
            pts = [(fx + side * 0.12 * R, cy - 0.7 * R), (fx + side * 0.95 * R, cy - 2.55 * R), (fx + side * 0.75 * R, cy - 2.6 * R),
                   (fx + side * 0.02 * R, cy - 0.95 * R)]
            poly(d, pts, GOLD, w=4)
    elif kind == "kalawta":
        d.chord([cx - 0.95 * R - OUT, cy - 1.75 * R - OUT, cx + 0.95 * R + OUT, cy + 0.65 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 0.95 * R, cy - 1.75 * R, cx + 0.95 * R, cy + 0.65 * R], 180, 360, fill=c1)
        d.rectangle([cx - 1.0 * R, cy - 0.68 * R, cx + 1.0 * R, cy - 0.45 * R], fill=c2, outline=LINE, width=3)
    elif kind == "hood":                                                          # 1270s hood (cappuccio) framing the face
        d.chord([cx - 1.22 * R - OUT, cy - 1.32 * R - OUT, cx + 1.22 * R + OUT, cy + 0.55 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.22 * R, cy - 1.32 * R, cx + 1.22 * R, cy + 0.55 * R], 180, 360, fill=c1)
        for side in (-1, 1):
            if side * k > 0.6:
                continue
            x = cx + side * 1.08 * R
            d.rounded_rectangle([x - 0.2 * R, cy - 0.45 * R, x + 0.2 * R, cy + 1.0 * R], radius=6, fill=c1, outline=LINE, width=3)
        d.arc([cx - 1.05 * R, cy - 1.1 * R, cx + 1.05 * R, cy + 0.5 * R], 200, 340, fill=shade(c1, 0.75), width=4)
    elif kind in ("flat_cap", "tudor_bonnet"):
        d.chord([cx - 1.02 * R - OUT, cy - 1.3 * R - OUT, cx + 1.02 * R + OUT, cy + 0.3 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.02 * R, cy - 1.3 * R, cx + 1.02 * R, cy + 0.3 * R], 180, 360, fill=shade(c1, 0.85))
        ell(d, cx + f * 0.1 * R, cy - 1.12 * R, 1.38 * R, 0.36 * R, c1)
        d.arc([cx + f * 0.1 * R - 1.3 * R, cy - 1.45 * R, cx + f * 0.1 * R + 1.3 * R, cy - 0.85 * R], 20, 160, fill=tint(c1, 0.15), width=4)
        if kind == "tudor_bonnet":                                                # white plume and a pearl jewel
            for i in range(4):
                ell(d, cx - f * (0.3 + 0.38 * i) * R, cy - (1.38 + 0.12 * math.sin(i * 1.7)) * R, 0.32 * R, 0.24 * R, c2, w=3)
            for i in range(4):
                d.arc([cx - f * (0.3 + 0.38 * i) * R - 0.25 * R, cy - 1.55 * R, cx - f * (0.3 + 0.38 * i) * R + 0.25 * R, cy - 1.25 * R], 20, 160,
                      fill=(200, 198, 190), width=2)
            ell(d, cx + f * 0.5 * R, cy - 1.15 * R, 0.16 * R, 0.16 * R, GOLD, w=3)
            dots(d, [(cx + f * (0.05 + 0.2 * i) * R, cy - 0.98 * R) for i in range(5)], 0.06 * R, WHITE, line=False)
    elif kind == "capotain":                                                      # tall-crowned hat, narrow brim
        ell(d, cx, cy - 0.78 * R, 1.62 * R, 0.34 * R, shade(c1, 0.9))
        crown = [(cx - 0.95 * R, cy - 0.8 * R), (cx - 0.72 * R, cy - 1.9 * R), (cx - 0.5 * R, cy - 2.38 * R), (cx - 0.15 * R, cy - 2.5 * R),
                 (cx + 0.3 * R, cy - 2.46 * R), (cx + 0.58 * R, cy - 2.28 * R), (cx + 0.72 * R, cy - 1.9 * R), (cx + 0.95 * R, cy - 0.8 * R)]
        poly(d, crown, c1)
        d.polygon([(cx - 0.9 * R, cy - 1.15 * R), (cx + 0.9 * R, cy - 1.15 * R), (cx + 0.93 * R, cy - 0.9 * R), (cx - 0.93 * R, cy - 0.9 * R)], fill=c2)
        d.polygon([(cx - f * 0.62 * R, cy - 2.1 * R), (cx - f * 0.42 * R, cy - 2.3 * R), (cx - f * 0.5 * R, cy - 1.3 * R), (cx - f * 0.75 * R, cy - 1.3 * R)],
                  fill=tint(c1, 0.12))
    elif kind == "morion":                                                        # comb morion, c. 1600
        comb_w = 0.12 * R + 0.75 * R * v
        d.chord([cx - comb_w - OUT, cy - 2.75 * R - OUT, cx + comb_w + OUT, cy - 0.8 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - comb_w, cy - 2.75 * R, cx + comb_w, cy - 0.8 * R], 180, 360, fill=c1)
        d.chord([cx - 1.0 * R - OUT, cy - 2.0 * R - OUT, cx + 1.0 * R + OUT, cy - 0.05 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.0 * R, cy - 2.0 * R, cx + 1.0 * R, cy - 0.05 * R], 180, 360, fill=c1)
        d.chord([cx - 0.8 * R, cy - 1.85 * R, cx + 0.2 * R, cy - 0.2 * R], 200, 260, fill=tint(c1, 0.4))
        brim = [(cx - 1.7 * R, cy - 1.45 * R), (cx - 1.35 * R, cy - 0.75 * R), (cx - 0.55 * R, cy - 0.5 * R), (cx + 0.55 * R, cy - 0.5 * R),
                (cx + 1.35 * R, cy - 0.75 * R), (cx + 1.7 * R, cy - 1.45 * R), (cx + 1.15 * R, cy - 1.0 * R), (cx - 1.15 * R, cy - 1.0 * R)]
        poly(d, brim, shade(c1, 0.92))
        dots(d, [(cx + i * 0.3 * R, cy - 1.12 * R) for i in range(-3, 4)], 0.05 * R, c2, line=False)
    elif kind == "monmouth":                                                      # knitted sailor's cap
        d.chord([cx - 1.05 * R - OUT, cy - 1.8 * R - OUT, cx + 1.05 * R + OUT, cy + 0.3 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.05 * R, cy - 1.8 * R, cx + 1.05 * R, cy + 0.3 * R], 180, 360, fill=c1)
        d.rounded_rectangle([cx - 1.1 * R, cy - 0.95 * R, cx + 1.1 * R, cy - 0.55 * R], radius=8, fill=c2, outline=LINE, width=4)
        ell(d, cx, cy - 1.82 * R, 0.14 * R, 0.12 * R, c2, w=3)
    elif kind == "tricorne":                                                      # black felt, tape edge, cockade
        d.chord([cx - 0.98 * R - OUT, cy - 1.75 * R - OUT, cx + 0.98 * R + OUT, cy + 0.1 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 0.98 * R, cy - 1.75 * R, cx + 0.98 * R, cy + 0.1 * R], 180, 360, fill=tint(c1, 0.08))
        fc = (cx + k * 0.55 * R, cy - 0.42 * R)
        pts = [(cx - 1.55 * R, cy - 0.95 * R), fc, (cx + 1.55 * R, cy - 0.95 * R), (cx + 1.12 * R, cy - 1.5 * R), (cx + k * 0.55 * R, cy - 1.05 * R),
               (cx - 1.12 * R, cy - 1.5 * R)]
        poly(d, pts, c1)
        d.line([(cx - 1.5 * R, cy - 0.95 * R), fc, (cx + 1.5 * R, cy - 0.95 * R)], fill=c2, width=max(4, int(0.1 * R)))
        d.line([(cx + k * 0.55 * R, cy - 1.05 * R), fc], fill=shade(c1, 1.6) if c1[0] < 60 else shade(c1, 0.7), width=3)
        ell(d, cx + f * 0.95 * R, cy - 1.05 * R, 0.2 * R, 0.2 * R, (20, 20, 22), w=3)
        d.ellipse([cx + f * 0.95 * R - 4, cy - 1.05 * R - 4, cx + f * 0.95 * R + 4, cy - 1.05 * R + 4], fill=c2)


# ================================================================================================ hair
HAIR = {"mongol", "jurchen", "braids", "short", "bob", "tonsure", "queue", "red_curls", "long", "hidden", "boy_mongol"}


def hair_back(d, kind, cx, cy, R, u, k, col):
    f = 1 if k >= 0 else -1
    if kind in ("mongol", "boy_mongol"):                                         # braids looped up behind each ear (Carpini, Rubruck, NPM)
        for side in (-1, 1):
            if side * k > 0.55:
                continue
            x = cx + side * 1.02 * R - k * 0.15 * R
            y = cy + 0.5 * R
            d.ellipse([x - 0.34 * R - 3, y - 0.48 * R - 3, x + 0.34 * R + 3, y + 0.48 * R + 3], outline=LINE, width=int(0.24 * R) + 6)
            d.ellipse([x - 0.34 * R, y - 0.48 * R, x + 0.34 * R, y + 0.48 * R], outline=col, width=int(0.24 * R))
    elif kind == "jurchen":                                                       # back braids tied with coloured ribbons
        for i, dx in enumerate((-0.35, 0.25)):
            x0 = cx - f * 0.7 * R + dx * R
            band(d, (x0, cy - 0.1 * R), (x0 - f * 0.25 * R, cy + 2.2 * R), 0.22 * R, col, ow=3)
            d.rectangle([x0 - f * 0.25 * R - 0.15 * R, cy + 2.1 * R, x0 - f * 0.25 * R + 0.15 * R, cy + 2.45 * R], fill=(170, 40, 40), outline=LINE, width=2)
    elif kind == "braids":                                                        # several Turkic braids
        for dx in (-0.8, -0.3, 0.2, 0.7):
            x0 = cx + dx * R - f * 0.3 * R
            band(d, (x0, cy - 0.3 * R), (x0 + dx * 0.2 * R - f * 0.15 * R, cy + 2.0 * R), 0.2 * R, col, ow=3)
    elif kind == "bob":
        d.rounded_rectangle([cx - 1.18 * R - OUT, cy - 1.1 * R - OUT, cx + 1.18 * R + OUT, cy + 0.75 * R + OUT], radius=0.5 * R, fill=LINE)
        d.rounded_rectangle([cx - 1.18 * R, cy - 1.1 * R, cx + 1.18 * R, cy + 0.75 * R], radius=0.5 * R, fill=col)
    elif kind == "queue":                                                         # 18th-c. tied back, black ribbon
        x = cx - f * 0.78 * R
        band(d, (x, cy + 0.3 * R), (x - f * 0.05 * R, cy + 1.65 * R), 0.2 * R, col, ow=3)
        for side in (-1, 1):                                                      # black ribbon bow
            d.polygon([(x, cy + 0.45 * R), (x + side * 0.32 * R, cy + 0.3 * R), (x + side * 0.32 * R, cy + 0.62 * R)], fill=(24, 24, 26), outline=LINE)
    elif kind == "red_curls":                                                     # Elizabeth's curled red wig
        ell(d, cx, cy - 0.45 * R, 1.4 * R, 1.15 * R, col)
        for i in range(10):
            a = math.pi * (0.9 + 1.2 * i / 9)
            x, y = cx + 1.3 * R * math.cos(a), cy - 0.45 * R + 1.05 * R * math.sin(a)
            d.arc([x - 0.25 * R, y - 0.25 * R, x + 0.25 * R, y + 0.25 * R], 0, 300, fill=shade(col, 0.7), width=3)
    elif kind == "long":
        d.rounded_rectangle([cx - 1.2 * R - OUT, cy - 1.1 * R - OUT, cx + 1.2 * R + OUT, cy + 2.2 * R + OUT], radius=0.6 * R, fill=LINE)
        d.rounded_rectangle([cx - 1.2 * R, cy - 1.1 * R, cx + 1.2 * R, cy + 2.2 * R], radius=0.6 * R, fill=col)


def hair_front(d, kind, cx, cy, R, u, k, col, skin, hatted=False):
    fx = cx + k * 0.35 * R
    if kind in ("mongol", "boy_mongol"):
        for side in (-1, 1):                                                      # hair left long at the sides
            if side * k > 0.55:
                continue
            x = cx + side * 0.9 * R
            d.rounded_rectangle([x - 0.2 * R, cy - 0.7 * R, x + 0.2 * R, cy + 0.15 * R], radius=5, fill=col)
        if not hatted:
            d.chord([cx - 0.98 * R, cy - 1.0 * R, cx + 0.98 * R, cy + 0.3 * R], 190, 350, fill=shade(skin, 0.88))   # shaved crown
            d.polygon([(fx - 0.22 * R, cy - 0.95 * R), (fx + 0.22 * R, cy - 0.95 * R), (fx + 0.05 * R, cy - 0.38 * R), (fx - 0.08 * R, cy - 0.42 * R)],
                      fill=col, outline=LINE)                                     # forelock to the eyebrows
    elif kind == "jurchen" and not hatted:
        d.chord([cx - 0.98 * R, cy - 1.0 * R, cx + 0.98 * R, cy + 0.3 * R], 190, 350, fill=shade(skin, 0.88))
    elif kind in ("short", "braids", "queue", "bob", "long") and not hatted:
        d.chord([cx - 1.1 * R - OUT, cy - 1.15 * R - OUT, cx + 1.1 * R + OUT, cy + 0.3 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.1 * R, cy - 1.15 * R, cx + 1.1 * R, cy + 0.3 * R], 180, 360, fill=col)
        if kind == "bob":
            d.rectangle([cx - 1.05 * R, cy - 0.65 * R, cx + 1.05 * R, cy - 0.42 * R], fill=col)
        elif kind == "long":
            d.line([(fx, cy - 1.12 * R), (fx, cy - 0.55 * R)], fill=shade(col, 0.6), width=3)
        else:
            d.polygon([(fx - 0.6 * R, cy - 0.5 * R), (fx + 0.1 * R, cy - 0.95 * R), (fx + 0.75 * R, cy - 0.42 * R)], fill=col)
        if kind == "queue":                                                       # side rolls
            for side in (-1, 1):
                if side * k > 0.55:
                    continue
                ell(d, cx + side * 0.95 * R, cy - 0.4 * R, 0.17 * R, 0.14 * R, col, w=3)
    elif kind == "queue" and hatted:
        for side in (-1, 1):
            if side * k > 0.55:
                continue
            ell(d, cx + side * 0.95 * R, cy - 0.4 * R, 0.17 * R, 0.14 * R, col, w=3)
    elif kind in ("short", "braids", "bob", "long") and hatted:
        for side in (-1, 1):
            if side * k > 0.55:
                continue
            x = cx + side * 0.92 * R
            d.rounded_rectangle([x - 0.2 * R, cy - 0.65 * R, x + 0.2 * R, cy + (0.6 if kind == "bob" else 0.1) * R], radius=5, fill=col)
    elif kind == "tonsure":                                                       # friar: ring of hair, bald crown
        d.chord([cx - 1.08 * R - OUT, cy - 1.12 * R - OUT, cx + 1.08 * R + OUT, cy + 0.3 * R + OUT], 180, 360, fill=LINE)
        d.chord([cx - 1.08 * R, cy - 1.12 * R, cx + 1.08 * R, cy + 0.3 * R], 180, 360, fill=col)
        d.ellipse([cx - 0.75 * R, cy - 1.2 * R, cx + 0.75 * R, cy - 0.68 * R], fill=shade(skin, 0.95))
    elif kind == "red_curls":                                                     # high curled front with pearls
        for i in range(7):
            x = cx - 1.0 * R + i * 0.333 * R
            for j in range(2):
                y = cy - 0.85 * R - j * 0.38 * R
                ell(d, x + (0.16 * R if j else 0), y, 0.24 * R, 0.21 * R, col, w=3)
                d.arc([x - 0.14 * R + (0.16 * R if j else 0), y - 0.12 * R, x + 0.14 * R + (0.16 * R if j else 0), y + 0.12 * R], 0, 270,
                      fill=shade(col, 0.7), width=3)
        dots(d, [(cx - 0.9 * R + i * 0.36 * R, cy - 1.42 * R) for i in range(6)], 0.08 * R, WHITE)
        ell(d, fx, cy - 1.55 * R, 0.16 * R, 0.2 * R, (168, 35, 58), w=3)


# ================================================================================================ beards
BEARDS = {"sparse", "long", "droop", "pointed", "full2"}


def beard_chin(d, kind, fx, cy, R, u, k, col):
    """Chin beards, drawn before the mouth."""
    if kind == "long":                                                            # Chinggis (NPM portrait): long thin beard
        pts = [(fx - 0.62 * R, cy + 0.7 * R), (fx - 0.3 * R, cy + 1.0 * R), (fx + 0.3 * R, cy + 1.0 * R), (fx + 0.62 * R, cy + 0.7 * R),
               (fx + 0.35 * R, cy + 1.7 * R), (fx + k * 0.15 * R, cy + 2.45 * R), (fx - 0.35 * R, cy + 1.7 * R)]
        poly(d, pts, col)
        for i in (-1, 0, 1):
            d.line([(fx + i * 0.18 * R, cy + 1.1 * R), (fx + i * 0.08 * R + k * 0.1 * R, cy + 2.1 * R)], fill=shade(col, 0.75), width=3)
    elif kind == "sparse":                                                        # small chin tuft
        poly(d, [(fx - 0.18 * R, cy + 0.98 * R), (fx + 0.18 * R, cy + 0.98 * R), (fx + k * 0.08 * R, cy + 1.45 * R)], col, w=3)
    elif kind == "pointed":                                                       # Elizabethan spade beard
        poly(d, [(fx - 0.55 * R, cy + 0.72 * R), (fx - 0.25 * R, cy + 0.98 * R), (fx + 0.25 * R, cy + 0.98 * R), (fx + 0.55 * R, cy + 0.72 * R),
                 (fx + k * 0.15 * R, cy + 1.75 * R)], col, w=4)
    elif kind == "full2":                                                         # full rounded beard below the mouth
        bx, w = fx - k * 0.45 * R, 0.92 * R * (1 - 0.2 * abs(k))                 # follows the jaw, not the nose
        pts = [(bx - w, cy + 0.1 * R), (bx - 0.6 * w, cy + 0.85 * R), (bx + 0.6 * w, cy + 0.85 * R), (bx + w, cy + 0.1 * R),
               (bx + 0.9 * w, cy + 1.2 * R), (bx + k * 0.35 * R, cy + 1.75 * R), (bx - 0.9 * w, cy + 1.2 * R)]
        poly(d, pts, col)
        for i in (-1, 0, 1):
            d.arc([bx + i * 0.35 * w - 0.2 * R, cy + 1.05 * R, bx + i * 0.35 * w + 0.2 * R, cy + 1.4 * R], 20, 160, fill=shade(col, 0.75), width=3)


def moustache(d, kind, fx, my, R, u, k, col):
    """Moustaches, drawn after the mouth (my = mouth y)."""
    w = 1 - 0.3 * abs(k)
    if kind in ("long", "sparse", "pointed", "full2"):
        for side in (-1, 1):
            d.line([(fx + k * 0.1 * R, my - 0.2 * R), (fx + side * 0.42 * R * w, my - 0.12 * R), (fx + side * 0.55 * R * w, my + (0.3 if kind == "long" else 0.12) * R)],
                   fill=col, width=max(4, int(0.12 * R)))
    elif kind == "droop":                                                         # Jahangir: full drooping moustache
        for side in (-1, 1):
            poly(d, [(fx + k * 0.1 * R, my - 0.3 * R), (fx + side * 0.5 * R * w, my - 0.2 * R), (fx + side * 0.62 * R * w, my + 0.45 * R),
                     (fx + side * 0.45 * R * w, my + 0.4 * R), (fx + side * 0.3 * R * w, my - 0.05 * R), (fx + k * 0.1 * R, my - 0.1 * R)], col, w=3)


# ================================================================================================ neckwear
def neck(d, kind, cx, y, u, k, scale=1.0):
    """Collars and neck jewellery at the neck point (cx, y). Drawn on the torso, under the head."""
    s = scale
    if kind == "ruff":                                                            # closed medium ruff
        rx, ry = 1.25 * u * s, 0.45 * u * s
        ox, oy = cx + k * 0.2 * u, y + 0.05 * u
        n = 18
        for i in range(n):
            a = math.pi * 2 * i / n
            ell(d, ox + rx * math.cos(a), oy + ry * math.sin(a), 0.2 * u * s, 0.16 * u * s, WHITE, w=3)
        d.ellipse([ox - rx, oy - ry, ox + rx, oy + ry], fill=WHITE)
        for i in range(n):
            a = math.pi * 2 * (i + 0.5) / n
            d.line([(ox + rx * 0.45 * math.cos(a), oy + ry * 0.45 * math.sin(a)), (ox + rx * 1.02 * math.cos(a), oy + ry * 1.02 * math.sin(a))],
                   fill=(196, 194, 186), width=2)
    elif kind == "falling_band":                                                  # flat lace collar over the shoulders
        d.chord([cx - 1.25 * u - 4, y - 0.5 * u - 4, cx + 1.25 * u + 4, y + 0.75 * u + 4], 0, 180, fill=LINE)
        d.chord([cx - 1.25 * u, y - 0.5 * u, cx + 1.25 * u, y + 0.75 * u], 0, 180, fill=WHITE)
        for i in range(9):
            x = cx - 1.1 * u + i * 0.275 * u
            d.ellipse([x - 4, y + 0.08 * u + 0.5 * u * math.sin(math.pi * i / 8) - 4, x + 4, y + 0.08 * u + 0.5 * u * math.sin(math.pi * i / 8) + 4],
                      outline=(200, 198, 190), width=2)
    elif kind in ("stock", "jabot"):                                              # white stock, small jabot
        d.rectangle([cx - 0.45 * u, y - 0.15 * u, cx + 0.45 * u, y + 0.25 * u], fill=WHITE, outline=LINE, width=3)
        if kind == "jabot":
            poly(d, [(cx + k * 0.2 * u - 0.3 * u, y + 0.2 * u), (cx + k * 0.2 * u + 0.3 * u, y + 0.2 * u), (cx + k * 0.2 * u + 0.4 * u, y + 0.95 * u),
                     (cx + k * 0.2 * u - 0.4 * u, y + 0.95 * u)], WHITE, w=3)
    elif kind == "fur_collar":
        fur(d, [cx - 1.5 * u, y - 0.25 * u, cx + 1.5 * u, y + 0.45 * u], (236, 230, 216), u)
    elif kind == "gorget":                                                        # gilt officer's gorget
        d.chord([cx - 0.55 * u - 3, y - 0.05 * u - 3, cx + 0.55 * u + 3, y + 0.75 * u + 3], 0, 180, fill=LINE)
        d.chord([cx - 0.55 * u, y - 0.05 * u, cx + 0.55 * u, y + 0.75 * u], 0, 180, fill=(226, 190, 90))
    elif kind == "beads":                                                         # coral and turquoise beads
        for i in range(9):
            a = math.pi * (0.12 + 0.76 * i / 8)
            dots(d, [(cx + 0.75 * u * math.cos(a), y + 0.1 * u + 0.5 * u * math.sin(a))], 0.11 * u, (190, 70, 50) if i % 2 else (47, 163, 160))


def pearls(d, cx, y, u, k, n=2, drop=1.4):
    for j in range(n):
        rx, ry = (0.75 + 0.25 * j) * u, (0.6 + drop * 0.5 * j) * u
        pts = [(cx + k * 0.25 * u + rx * math.cos(a), y + ry * math.sin(a)) for a in [math.pi * (0.1 + 0.8 * i / 12) for i in range(13)]]
        dots(d, pts, 0.08 * u, (246, 242, 230))


def chain(d, cx, y, u, k):
    pts = [(cx + k * 0.25 * u + 1.0 * u * math.cos(a), y + 1.1 * u * math.sin(a)) for a in [math.pi * (0.08 + 0.84 * i / 16) for i in range(17)]]
    d.line(pts, fill=LINE, width=8)
    d.line(pts, fill=(226, 190, 90), width=4)


# ================================================================================================ garments
GARMENTS = {"deel", "deel_w", "lamellar", "kazaghand", "mail_surcoat", "oyoroi", "robe_round", "habit", "cotta", "doublet", "buffcoat",
            "farthingale", "slops", "jerkin", "jama", "frock", "redcoat", "sepoy", "dhoti"}
SHOULDER_PIECES = {"lamellar": "pauldron", "oyoroi": "sode"}


def _skirt(d, hx, y0, y1, w0, w1, col, alpha=255, curve=0.12):
    fill = tuple(col[:3]) + (alpha,) if alpha < 255 else col
    pts = [(hx - w0, y0), (hx + w0, y0), (hx + w1, y1 - curve * (y1 - y0) * 0.3), (hx + w1 * 0.7, y1), (hx - w1 * 0.7, y1),
           (hx - w1, y1 - curve * (y1 - y0) * 0.3)]
    d.polygon(pts, fill=fill, outline=LINE, width=5)
    return pts


def _torso(d, hx, top, bottom, sw, u, col, f, waist=0.86, shoulder=0.92):
    pts = [(hx - sw * shoulder, top), (hx + sw * shoulder, top), (hx + sw * 0.99, top + 0.5 * u), (hx + sw * waist, bottom), (hx - sw * waist, bottom),
           (hx - sw * 0.99, top + 0.5 * u)]
    poly(d, pts, col)
    d.polygon([(hx - f * sw * 0.97, top + 0.5 * u), (hx - f * sw * waist * 0.97, bottom - 3), (hx - f * sw * 0.55, bottom - 3), (hx - f * sw * 0.6, top + 0.4 * u)],
              fill=shade(col, 0.88))


def _pattern(d, box, u, col, step=0.7):
    x0, y0, x1, y1 = box
    y, row = y0 + 0.3 * u, 0
    while y < y1 - 0.2 * u:
        x = x0 + (0.35 * u if row % 2 else 0.1 * u)
        while x < x1 - 0.2 * u:
            d.ellipse([x - 0.13 * u, y - 0.13 * u, x + 0.13 * u, y + 0.13 * u], outline=col, width=3)
            x += step * u
        y += step * 0.8 * u
        row += 1


def _lamellae(d, box, u, col, lace, step=0.32):
    x0, y0, x1, y1 = box
    y, row = y0 + step * u, 0
    while y < y1 - 2:
        d.line([(x0 + 3, y), (x1 - 3, y)], fill=shade(col, 0.62), width=3)
        x = x0 + (0.14 * u if row % 2 else 0.0) + 0.14 * u
        while x < x1 - 4:
            d.line([(x, y - step * u + 4), (x, y - 3)], fill=shade(col, 0.78), width=2)
            x += 0.28 * u
        y += step * u
        row += 1
    for i in range(1, 4):
        x = x0 + i * (x1 - x0) / 4
        d.line([(x, y0 + 4), (x, y1 - 4)], fill=lace, width=3)


def _belt(d, hx, y, sw, u, col, plaques=None):
    d.rectangle([hx - sw * 0.9, y - 0.2 * u, hx + sw * 0.9, y + 0.2 * u], fill=col, outline=LINE, width=3)
    if plaques:
        for i in range(-2, 3):
            x = hx + i * sw * 0.36
            d.rectangle([x - 0.1 * u, y - 0.13 * u, x + 0.1 * u, y + 0.13 * u], fill=plaques)


def garment(d, kind, hx, hy, top, sw, u, k, f, c1, c2, c3, hem, flags=(), skin=(200, 150, 110)):
    """Torso (neck to hip) and skirt for one costume. c1 main, c2 trim/second, c3 belt/third; hem = length below the hip in u."""
    v = abs(k)
    c = hx + k * sw * 0.45                                                        # centre line turns with the view
    hemy = hy + hem * u
    fl = set(flags)
    if kind in ("deel", "deel_w"):
        wide = kind == "deel_w"
        w1 = sw * (1.45 if wide else 1.08) + 0.1 * hem * u
        _skirt(d, hx, hy - 0.9 * u, hemy, sw * 0.9, w1, c1)
        if "pattern" in fl:
            _pattern(d, [hx - w1 * 0.85, hy - 0.4 * u, hx + w1 * 0.85, hemy - 0.2 * u], u, shade(c1, 0.75) if "gold" not in fl else c2)
        if "fur" in fl:
            fur(d, [hx - w1 * 0.95, hemy - 0.38 * u, hx + w1 * 0.95, hemy + 0.02 * u], c2, u)
        d.line([(c - 0.72 * sw, hy - 0.5 * u), (c - 0.74 * sw * (1.3 if wide else 1.05), hemy - 0.05 * u)], fill=shade(c1, 0.68), width=4)
        _torso(d, hx, top, hy - 0.45 * u, sw, u, c1, f)
        if "pattern" in fl:
            _pattern(d, [hx - sw * 0.8, top + 0.4 * u, hx + sw * 0.8, hy - 1.0 * u], u, shade(c1, 0.75) if "gold" not in fl else c2)
        a, b = (c + 0.32 * sw * (1 - 0.5 * v), top + 0.02 * u), (c - 0.74 * sw, top + 1.5 * u)
        band(d, a, b, (0.42 if wide else 0.26) * u, c2 if "fur" not in fl else c2)
        if "pleats" in fl:                                                        # pleated-waist riding robe (yaoxian pao)
            d.rectangle([hx - sw * 0.86, hy - 1.45 * u, hx + sw * 0.86, hy - 0.5 * u], fill=shade(c1, 0.92), outline=LINE, width=3)
            for i in range(1, 6):
                y = hy - 1.45 * u + i * 0.16 * u
                d.line([(hx - sw * 0.84, y), (hx + sw * 0.84, y)], fill=shade(c1, 0.7), width=2)
        _belt(d, hx, hy - 0.62 * u, sw, u, c3, plaques=GOLD if "gold_belt" in fl else None)
        if wide:
            d.rectangle([hx - sw * 0.9, hy - 0.85 * u, hx + sw * 0.9, hy - 0.42 * u], fill=c3, outline=LINE, width=3)
    elif kind == "lamellar":
        _skirt(d, hx, hy - 0.6 * u, hemy, sw * 0.9, sw * 1.05 + 0.1 * hem * u, c2)
        _torso(d, hx, top, hy + 0.3 * u, sw, u, c1, f, waist=0.9)
        _lamellae(d, [hx - sw * 0.92, top + 0.2 * u, hx + sw * 0.92, hy + 0.3 * u], u, c1, c3)
        fl_len = min(hem - 0.3, 1.7) * u
        for side in (-1, 1):                                                      # skirt split in two flaps for riding
            x0, x1 = (hx - sw * 0.98, hx - 0.06 * u) if side < 0 else (hx + 0.06 * u, hx + sw * 0.98)
            poly(d, [(x0, hy + 0.1 * u), (x1, hy + 0.1 * u), (x1 + side * 0.1 * u, hy + fl_len), (x0 + side * 0.15 * u, hy + fl_len)], c1)
            _lamellae(d, [min(x0, x1), hy + 0.1 * u, max(x0, x1), hy + fl_len], u, c1, c3)
        _belt(d, hx, hy - 0.05 * u, sw, u, (90, 42, 30), plaques=GOLD if "gold_belt" in fl else None)
        d.chord([c - 0.55 * u, top - 0.25 * u, c + 0.55 * u, top + 0.5 * u], 0, 180, fill=c2, outline=LINE, width=3)
    elif kind == "kazaghand":                                                     # Mamluk: padded coat, silk cover, mail inside
        w1 = sw * 1.08 + 0.1 * hem * u
        _skirt(d, hx, hy - 0.9 * u, hemy, sw * 0.9, w1, c1)
        d.rectangle([hx - w1 * 0.88, hemy - 0.35 * u, hx + w1 * 0.88, hemy - 0.04 * u], fill=c2)
        mail_tex(d, [hx - w1 * 0.88, hemy - 0.35 * u, hx + w1 * 0.88, hemy - 0.04 * u], u, c2)
        _torso(d, hx, top, hy - 0.45 * u, sw, u, c1, f)
        _pattern(d, [hx - sw * 0.8, top + 0.4 * u, hx + w1 * 0.8, hemy - 0.5 * u], u, tint(c1, 0.35), step=0.8)
        band(d, (c + 0.3 * sw, top + 0.02 * u), (c - 0.7 * sw, top + 1.5 * u), 0.22 * u, GOLD)
        _belt(d, hx, hy - 0.62 * u, sw, u, c3)
        d.chord([c - 0.55 * u, top - 0.25 * u, c + 0.55 * u, top + 0.45 * u], 0, 180, fill=c2, outline=LINE, width=3)
    elif kind == "mail_surcoat":                                                  # mail hauberk under a sleeveless surcoat
        _skirt(d, hx, hy - 0.6 * u, hy + min(hem, 1.4) * u, sw * 0.9, sw * 1.05, c2)
        mail_tex(d, [hx - sw, hy - 0.4 * u, hx + sw, hy + min(hem, 1.4) * u], u, c2)
        _torso(d, hx, top, hy, sw, u, c2, f)
        mail_tex(d, [hx - sw * 0.95, top + 0.1 * u, hx + sw * 0.95, hy], u, c2)
        sc = [(hx - sw * 0.7, top + 0.1 * u), (hx + sw * 0.7, top + 0.1 * u), (hx + sw * 0.85, hy - 0.5 * u), (hx + sw * 1.0, hemy),
              (hx + 0.08 * u, hemy), (hx + 0.05 * u, hy + 0.4 * u), (hx - 0.05 * u, hy + 0.4 * u), (hx - 0.08 * u, hemy), (hx - sw * 1.0, hemy),
              (hx - sw * 0.85, hy - 0.5 * u)]
        poly(d, sc, c1)
        if "cross" in fl:
            d.rectangle([c - 0.12 * u, top + 0.5 * u, c + 0.12 * u, top + 1.9 * u], fill=WHITE, outline=LINE, width=2)
            d.rectangle([c - 0.55 * u, top + 0.9 * u, c + 0.55 * u, top + 1.14 * u], fill=WHITE, outline=LINE, width=2)
        if "eagle" in fl:                                                         # Silesian black eagle on gold (simplified)
            ell(d, c, top + 1.3 * u, 0.55 * u, 0.6 * u, (212, 170, 58), w=3)
            d.polygon([(c - 0.45 * u, top + 1.0 * u), (c, top + 1.4 * u), (c + 0.45 * u, top + 1.0 * u), (c + 0.2 * u, top + 1.7 * u), (c - 0.2 * u, top + 1.7 * u)],
                      fill=(26, 26, 26))
        _belt(d, hx, hy - 0.55 * u, sw * 0.95, u, c3)
    elif kind == "oyoroi":                                                        # Kamakura box armour
        for side in (-1, 1):                                                      # kusazuri skirt panels
            x0, x1 = (hx - sw * 1.0, hx - 0.05 * u) if side < 0 else (hx + 0.05 * u, hx + sw * 1.0)
            poly(d, [(x0, hy - 0.3 * u), (x1, hy - 0.3 * u), (x1, hy + 1.45 * u), (x0, hy + 1.45 * u)], c1)
            for i in range(1, 5):
                y = hy - 0.3 * u + i * 0.35 * u
                d.line([(x0 + 3, y), (x1 - 3, y)], fill=c2, width=max(4, int(0.13 * u)))
        poly(d, [(hx - sw * 0.98, top + 0.1 * u), (hx + sw * 0.98, top + 0.1 * u), (hx + sw * 1.0, hy), (hx - sw * 1.0, hy)], c1)
        for i in range(4):
            y = hy - 0.25 * u - i * 0.38 * u
            d.line([(hx - sw * 0.96, y), (hx + sw * 0.96, y)], fill=c2, width=max(4, int(0.14 * u)))
        poly(d, [(hx - sw * 0.85, top + 0.15 * u), (hx + sw * 0.85, top + 0.15 * u), (hx + sw * 0.85, top + 1.25 * u), (hx - sw * 0.85, top + 1.25 * u)], c3)
        _pattern(d, [hx - sw * 0.8, top + 0.2 * u, hx + sw * 0.8, top + 1.2 * u], u, shade(c3, 0.6), step=0.55)
    elif kind == "robe_round":                                                    # round-collared official robe (panling)
        _skirt(d, hx, hy - 0.9 * u, hemy, sw * 0.9, sw * 1.12 + 0.1 * hem * u, c1)
        _torso(d, hx, top, hy - 0.45 * u, sw, u, c1, f)
        d.ellipse([c - 0.62 * u, top - 0.35 * u, c + 0.62 * u, top + 0.55 * u], outline=shade(c1, 0.6), width=5)
        d.arc([c - 0.2 * u, top + 0.2 * u, c + 1.3 * u, top + 1.6 * u], 180, 260, fill=shade(c1, 0.6), width=4)
        d.rectangle([hx - sw * 0.92, hy - 0.55 * u, hx + sw * 0.92, hy - 0.3 * u], fill=c3, outline=LINE, width=3)
        for i in range(-2, 3):
            x = hx + i * sw * 0.35
            d.rectangle([x - 0.12 * u, hy - 0.52 * u, x + 0.12 * u, hy - 0.33 * u], fill=(226, 220, 196))
    elif kind == "habit":                                                         # Franciscan: grey-brown, rope cord
        _skirt(d, hx, hy - 0.9 * u, hemy, sw * 0.9, sw * 1.12, c1)
        _torso(d, hx, top, hy - 0.45 * u, sw, u, c1, f)
        d.line([(hx - sw * 0.88, hy - 0.62 * u), (hx + sw * 0.88, hy - 0.62 * u)], fill=LINE, width=int(0.22 * u) + 6)
        d.line([(hx - sw * 0.88, hy - 0.62 * u), (hx + sw * 0.88, hy - 0.62 * u)], fill=(232, 222, 196), width=int(0.22 * u))
        rx = c + 0.3 * u
        band(d, (rx, hy - 0.62 * u), (rx + 0.1 * u, hy + 1.9 * u), 0.16 * u, (232, 222, 196), ow=3)
        dots(d, [(rx + 0.05 * u, hy + (0.4 + 0.5 * i) * u) for i in range(3)], 0.14 * u, (220, 208, 180))
        d.chord([c - 1.0 * u, top - 0.3 * u, c + 1.0 * u, top + 0.7 * u], 0, 180, fill=shade(c1, 0.85), outline=LINE, width=4)
    elif kind == "cotta":                                                         # Venetian 1270s belted tunic
        _skirt(d, hx, hy - 0.9 * u, hemy, sw * 0.9, sw * 1.05 + 0.08 * hem * u, c1)
        _torso(d, hx, top, hy - 0.45 * u, sw, u, c1, f)
        _belt(d, hx, hy - 0.25 * u, sw * 0.98, u, c3)
        d.rectangle([c + 0.2 * u, hy - 0.1 * u, c + 0.65 * u, hy + 0.5 * u], fill=(110, 70, 40), outline=LINE, width=3)   # purse
        d.arc([c - 0.5 * u, top - 0.3 * u, c + 0.5 * u, top + 0.4 * u], 0, 180, fill=shade(c1, 0.6), width=4)
    elif kind in ("doublet", "buffcoat"):
        if kind == "doublet" and "venetians" not in fl:                           # paned trunk hose round the hips
            d.rounded_rectangle([hx - sw * 1.08 - OUT, hy - 0.5 * u - OUT, hx + sw * 1.08 + OUT, hy + 1.15 * u + OUT], radius=0.6 * u, fill=LINE)
            d.rounded_rectangle([hx - sw * 1.08, hy - 0.5 * u, hx + sw * 1.08, hy + 1.15 * u], radius=0.6 * u, fill=c2)
            for i in range(1, 7):
                x = hx - sw * 1.08 + i * sw * 2.16 / 7
                d.line([(x, hy - 0.4 * u), (x, hy + 1.05 * u)], fill=shade(c2, 0.6), width=4)
        if kind == "buffcoat":
            _skirt(d, hx, hy - 0.8 * u, hy + 1.25 * u, sw * 0.9, sw * 1.12, c1)
            d.line([(c, hy - 0.6 * u), (c, hy + 1.2 * u)], fill=shade(c1, 0.7), width=4)
            _torso(d, hx, top, hy - 0.4 * u, sw, u, c1, f)
            for i in range(6):
                y = top + 0.5 * u + i * 0.45 * u
                d.line([(c - 0.15 * u, y), (c + 0.15 * u, y)], fill=shade(c1, 0.6), width=4)
            band(d, (c + 0.85 * sw, top + 0.2 * u), (c - 0.85 * sw, hy - 0.45 * u), 0.4 * u, c3)   # sash over the shoulder
            ell(d, c - 0.85 * sw, hy - 0.4 * u, 0.3 * u, 0.25 * u, c3, w=4)
        else:
            pts = [(hx - sw * 0.92, top), (hx + sw * 0.92, top), (hx + sw * 0.99, top + 0.5 * u), (hx + sw * 0.82, hy - 0.45 * u), (c, hy + 0.15 * u),
                   (hx - sw * 0.82, hy - 0.45 * u), (hx - sw * 0.99, top + 0.5 * u)]
            poly(d, pts, c1)
            d.polygon([(hx - f * sw * 0.97, top + 0.5 * u), (hx - f * sw * 0.8, hy - 0.5 * u), (hx - f * sw * 0.5, hy - 0.4 * u), (hx - f * sw * 0.6, top + 0.4 * u)],
                      fill=shade(c1, 0.86))
            for i in range(7):
                y = top + 0.35 * u + i * (hy - top - 0.3 * u) / 7.5
                ell(d, c, y, 0.09 * u, 0.09 * u, c3, w=2)
            for i in range(-3, 4):                                                # short skirt tabs at the waist
                x = hx + i * sw * 0.26
                if abs(x - c) < 0.25 * u:
                    continue
                d.rectangle([x - 0.13 * u, hy - 0.5 * u + abs(i) * 0.04 * u, x + 0.13 * u, hy - 0.15 * u], fill=shade(c1, 0.92), outline=LINE, width=2)
    elif kind == "farthingale":                                                   # Elizabeth I: drum farthingale, long pointed bodice
        W = sw * 2.35
        poly(d, [(hx - W, hy - 0.55 * u), (hx + W, hy - 0.55 * u), (hx + W * 1.04, hemy), (hx - W * 1.04, hemy)], c1)
        _pattern(d, [hx - W, hy - 0.3 * u, hx + W, hemy - 0.1 * u], u, c2, step=0.75)
        d.polygon([(hx - f * W, hy - 0.5 * u), (hx - f * W * 1.04, hemy - 3), (hx - f * W * 0.6, hemy - 3), (hx - f * W * 0.6, hy - 0.5 * u)], fill=shade(c1, 0.9))
        ell(d, hx, hy - 0.6 * u, W * 1.03, 0.45 * u, tint(c1, 0.1))               # the drum top, with a frill
        for i in range(16):
            x = hx - W + i * 2 * W / 15
            d.arc([x - 0.2 * u, hy - 0.75 * u, x + 0.2 * u, hy - 0.45 * u], 0, 180, fill=shade(c1, 0.7), width=3)
        body = [(hx - sw * 0.85, top), (hx + sw * 0.85, top), (hx + sw * 0.9, top + 0.5 * u), (hx + sw * 0.55, hy - 0.6 * u), (c, hy + 0.2 * u),
                (hx - sw * 0.55, hy - 0.6 * u), (hx - sw * 0.9, top + 0.5 * u)]
        poly(d, body, c1)
        stom = [(c - sw * 0.45, top + 0.3 * u), (c + sw * 0.45, top + 0.3 * u), (c, hy + 0.1 * u)]
        poly(d, stom, c3, w=4)
        for i in range(5):
            y = top + 0.6 * u + i * 0.48 * u
            dots(d, [(c, y)], 0.1 * u, c2)
    elif kind == "slops":                                                         # sailor: short jacket, wide canvas slops
        d.rounded_rectangle([hx - sw * 1.12 - OUT, hy - 0.5 * u - OUT, hx + sw * 1.12 + OUT, hy + 1.8 * u + OUT], radius=0.5 * u, fill=LINE)
        d.rounded_rectangle([hx - sw * 1.12, hy - 0.5 * u, hx + sw * 1.12, hy + 1.8 * u], radius=0.5 * u, fill=c2)
        d.line([(hx, hy + 0.3 * u), (hx, hy + 1.75 * u)], fill=shade(c2, 0.7), width=4)
        _torso(d, hx, top, hy + 0.1 * u, sw, u, c1, f)
        d.line([(c, top + 0.6 * u), (c, hy)], fill=shade(c1, 0.65), width=4)
        d.chord([c - 0.55 * u, top - 0.3 * u, c + 0.55 * u, top + 0.5 * u], 0, 180, fill=c3, outline=LINE, width=3)
    elif kind == "jerkin":                                                        # shipwright: shirt, leather jerkin, apron
        _torso(d, hx, top, hy + 0.1 * u, sw, u, c2, f)
        poly(d, [(hx - sw * 0.8, top + 0.1 * u), (c - 0.2 * u, top + 0.1 * u), (c - 0.15 * u, hy + 0.1 * u), (hx - sw * 0.86, hy + 0.1 * u)], c1)
        poly(d, [(c + 0.2 * u, top + 0.1 * u), (hx + sw * 0.8, top + 0.1 * u), (hx + sw * 0.86, hy + 0.1 * u), (c + 0.15 * u, hy + 0.1 * u)], c1)
        poly(d, [(hx - sw * 0.7, hy - 0.5 * u), (hx + sw * 0.7, hy - 0.5 * u), (hx + sw * 0.8, hy + hem * u), (hx - sw * 0.8, hy + hem * u)], c3)
        _belt(d, hx, hy - 0.5 * u, sw, u, (80, 56, 36))
    elif kind == "jama":                                                          # Mughal jama, patka sash with end panel
        w1 = sw * 1.25 + 0.14 * hem * u
        _skirt(d, hx, hy - 1.15 * u, hemy, sw * 0.82, w1, c1, alpha=205 if "translucent" in fl else 255, curve=0.0)
        for i in range(1, 7):
            x0 = hx - sw * 0.8 + i * sw * 1.6 / 7
            x1 = hx - w1 * 0.95 + i * w1 * 1.9 / 7
            d.line([(x0, hy - 0.9 * u), (x1, hemy - 0.1 * u)], fill=shade(c1, 0.82), width=3)
        if "pattern" in fl:
            _pattern(d, [hx - w1 * 0.8, hy - 0.6 * u, hx + w1 * 0.8, hemy - 0.2 * u], u, c2 if "gold" in fl else shade(c1, 0.75), step=0.75)
        _torso(d, hx, top, hy - 1.05 * u, sw, u, c1, f, waist=0.8)
        if "pattern" in fl:
            _pattern(d, [hx - sw * 0.75, top + 0.4 * u, hx + sw * 0.75, hy - 1.3 * u], u, c2 if "gold" in fl else shade(c1, 0.75), step=0.75)
        a, b = (c + 0.25 * sw, top + 0.02 * u), (c - 0.75 * sw, top + 1.35 * u)
        d.line([a, b], fill=shade(c1, 0.6), width=4)
        for i in range(2):                                                        # side ties
            y = top + 1.0 * u + i * 0.3 * u
            d.line([(b[0], y), (b[0] - 0.35 * u, y + 0.25 * u)], fill=shade(c1, 0.55), width=3)
        d.rectangle([hx - sw * 0.84, hy - 1.3 * u, hx + sw * 0.84, hy - 0.82 * u], fill=c2, outline=LINE, width=3)
        for i in range(1, 3):
            d.line([(hx - sw * 0.82, hy - 1.3 * u + i * 0.16 * u), (hx + sw * 0.82, hy - 1.3 * u + i * 0.16 * u)], fill=shade(c2, 0.75), width=2)
        pl = min(hem * 0.65, 2.3) * u
        px = c - 0.1 * u
        poly(d, [(px - 0.3 * u, hy - 0.9 * u), (px + 0.3 * u, hy - 0.9 * u), (px + 0.34 * u, hy - 0.9 * u + pl), (px - 0.34 * u, hy - 0.9 * u + pl)], c2, w=4)
        for i in range(3):
            y = hy - 0.9 * u + pl - 0.25 * u - i * 0.3 * u
            d.line([(px - 0.3 * u, y), (px + 0.3 * u, y)], fill=c3, width=max(3, int(0.09 * u)))
        d.rectangle([c + 0.35 * u, hy - 1.55 * u, c + 0.52 * u, hy - 0.95 * u], fill=GOLD, outline=LINE, width=2)   # katar hilt
    elif kind in ("frock", "redcoat"):
        red = kind == "redcoat"
        lining = c2 if red else shade(c1, 0.85)
        sk = hy + hem * u
        for side in (-1, 1):                                                      # coat skirts, split; soldiers' turned back
            x_out, x_in = hx + side * sw * 1.1, c + side * 0.15 * u
            pts = [(hx + side * sw * 0.86, hy - 0.6 * u), (x_in, hy - 0.6 * u), (x_in + side * 0.1 * u, sk), (x_out, sk)]
            poly(d, pts, c1)
            if red:
                poly(d, [(x_in, hy - 0.3 * u), (x_in + side * 0.1 * u, sk), (x_in + side * 0.75 * u, sk)], lining, w=3)
        if "waistcoat" not in fl and not red:
            pass
        _torso(d, hx, top, hy - 0.4 * u, sw, u, c1, f)
        wc = c3
        poly(d, [(c - 0.45 * u, top + 0.2 * u), (c + 0.45 * u, top + 0.2 * u), (c + 0.55 * u, hy + 0.6 * u), (c - 0.55 * u, hy + 0.6 * u)], wc, w=4)
        for i in range(6):
            ell(d, c + 0.05 * u, top + 0.55 * u + i * 0.42 * u, 0.07 * u, 0.07 * u, (226, 194, 96), w=2)
        if red:
            tape = (226, 190, 90) if "officer" in fl else WHITE
            for side in (-1, 1):                                                  # lapels in the facing colour, laced
                xl = c + side * 0.62 * u
                poly(d, [(c + side * 0.35 * u, top + 0.15 * u), (xl + side * 0.25 * u, top + 0.25 * u), (xl + side * 0.15 * u, hy - 1.0 * u),
                         (c + side * 0.42 * u, hy - 1.0 * u)], c2, w=4)
                for i in range(5):
                    y = top + 0.5 * u + i * 0.42 * u
                    d.line([(c + side * 0.48 * u, y), (xl + side * 0.1 * u, y)], fill=tape, width=4)
            if "officer" in fl:
                band(d, (c + 0.85 * sw, top + 0.15 * u), (c - 0.8 * sw, hy - 0.5 * u), 0.36 * u, (170, 24, 48))   # crimson sash, left shoulder
            else:
                band(d, (c + 0.85 * sw, top + 0.15 * u), (c - 0.85 * sw, hy - 0.25 * u), 0.3 * u, BUFF)             # buff shoulder belt
                d.rectangle([hx - sw * 0.9, hy - 0.62 * u, hx + sw * 0.9, hy - 0.4 * u], fill=BUFF, outline=LINE, width=3)
        else:
            for i in range(6):
                ell(d, c - 0.62 * u, top + 0.55 * u + i * 0.42 * u, 0.07 * u, 0.07 * u, (226, 194, 96), w=2)
    elif kind == "sepoy":                                                         # Company sepoy 1757 (bible 6.2, INTERPRETATION)
        _skirt(d, hx, hy - 0.8 * u, hy + 0.9 * u, sw * 0.88, sw * 1.0, c2)
        _torso(d, hx, top, hy - 0.4 * u, sw, u, c2, f)
        for side in (-1, 1):
            poly(d, [(hx + side * sw * 0.92, top), (c + side * 0.35 * u, top), (c + side * 0.5 * u, hy - 0.4 * u), (hx + side * sw * 0.86, hy - 0.4 * u)], c1)
        d.rectangle([hx - sw * 0.9, hy - 0.75 * u, hx + sw * 0.9, hy - 0.35 * u], fill=c3, outline=LINE, width=3)
        band(d, (c + 0.85 * sw, top + 0.15 * u), (c - 0.85 * sw, hy - 0.4 * u), 0.3 * u, BUFF)
    elif kind == "dhoti":                                                         # bare chest, white dhoti
        _torso(d, hx, top, hy + 0.1 * u, sw, u, skin, f)
        _skirt(d, hx, hy - 0.75 * u, hemy, sw * 0.88, sw * 0.95, c1, curve=0.0)
        d.line([(c, hy - 0.5 * u), (c + 0.1 * u, hemy - 0.1 * u)], fill=shade(c1, 0.7), width=4)
        d.arc([c - 0.7 * u, hy - 0.4 * u, c + 0.7 * u, hy + 0.6 * u], 20, 160, fill=shade(c1, 0.7), width=3)
        d.rectangle([hx - sw * 0.88, hy - 0.8 * u, hx + sw * 0.88, hy - 0.55 * u], fill=shade(c1, 0.9), outline=LINE, width=3)
        if "shawl" in fl:
            poly(d, [(c + 0.5 * sw, top), (c + 0.9 * sw, top + 0.1 * u), (c - 0.6 * sw, hy - 0.6 * u), (c - 0.9 * sw, hy - 0.9 * u)], c2, w=4)


def cloak(d, kind, hx, hy, top, sw, u, k, f, col, trim, hem):
    """Outer layer over the garment: long mantle, short cape, merchant's gown, nadiri jacket, shawl, fur coat."""
    if not kind:
        return
    c = hx + k * sw * 0.45
    bottom = hy + hem * u - 0.15 * u
    if kind in ("long", "gown", "fur"):
        for side in (-1, 1):
            xo = hx + side * sw * (1.05 if kind != "gown" else 1.12)
            xi = c + side * (0.55 if kind == "gown" else 0.75) * u
            pts = [(c + side * 0.4 * u, top - 0.05 * u), (hx + side * sw * 0.95, top + 0.05 * u), (xo, top + 0.6 * u), (xo + side * 0.15 * u * hem, bottom),
                   (xi + side * 0.1 * u, bottom), (xi, top + 1.0 * u)]
            poly(d, pts, col)
            if kind == "fur":
                _pattern(d, [min(xo, xi), top + 0.8 * u, max(xo, xi), bottom - 0.2 * u], u, shade(col, 0.82), step=0.6)
            if kind == "gown":                                                    # fur facings down the front edges
                d.line([(xi, top + 1.0 * u), (xi + side * 0.1 * u, bottom)], fill=LINE, width=int(0.42 * u) + 6)
                d.line([(xi, top + 1.0 * u), (xi + side * 0.1 * u, bottom)], fill=trim, width=int(0.42 * u))
        if kind in ("gown", "fur"):
            fur(d, [hx - sw * 1.0, top - 0.25 * u, hx + sw * 1.0, top + 0.5 * u], trim, u)
        else:
            ell(d, c, top + 0.25 * u, 0.2 * u, 0.2 * u, trim, w=3)
    elif kind == "short":                                                         # short cloak worn on the far shoulder
        x0 = hx - f * sw * 1.1
        pts = [(hx - f * sw * 0.2, top - 0.1 * u), (hx - f * sw * 1.0, top), (x0 - f * 0.15 * u, top + 0.6 * u), (x0 - f * 0.25 * u, hy + 0.35 * u),
               (hx - f * sw * 0.15, hy + 0.15 * u), (hx - f * sw * 0.1, top + 0.8 * u)]
        poly(d, pts, col)
        d.line([(hx - f * sw * 0.15, top + 0.9 * u), (hx - f * sw * 0.18, hy + 0.1 * u)], fill=trim, width=max(4, int(0.12 * u)))
    elif kind == "nadiri":                                                        # short overcoat (Jahangir)
        for side in (-1, 1):
            pts = [(c + side * 0.35 * u, top), (hx + side * sw * 0.98, top + 0.05 * u), (hx + side * sw * 1.02, hy - 0.2 * u), (c + side * 0.55 * u, hy - 0.2 * u)]
            poly(d, pts, col)
            d.line([(c + side * 0.42 * u, top + 0.1 * u), (c + side * 0.6 * u, hy - 0.25 * u)], fill=trim, width=max(4, int(0.16 * u)))
            d.line([(hx + side * sw * 1.0, hy - 0.22 * u), (c + side * 0.55 * u, hy - 0.22 * u)], fill=trim, width=max(4, int(0.16 * u)))
    elif kind == "shawl":
        poly(d, [(hx - sw * 1.0, top + 0.1 * u), (hx + sw * 1.0, top + 0.1 * u), (hx + sw * 0.95, top + 0.8 * u), (hx - sw * 0.95, top + 0.8 * u)], col, w=4)
        for side in (-1, 1):
            x = c + side * 0.5 * u
            poly(d, [(x - 0.28 * u, top + 0.3 * u), (x + 0.28 * u, top + 0.3 * u), (x + 0.3 * u, hy - 0.4 * u), (x - 0.3 * u, hy - 0.4 * u)], col, w=4)
            d.line([(x - 0.28 * u, hy - 0.6 * u), (x + 0.28 * u, hy - 0.6 * u)], fill=trim, width=max(4, int(0.12 * u)))
        d.line([(hx - sw * 0.95, top + 0.7 * u), (hx + sw * 0.95, top + 0.7 * u)], fill=trim, width=4)
    elif kind == "cape":                                                          # short shoulder cape (Venetian mantle pinned on the shoulder)
        pts = [(hx - sw * 1.05, top + 0.05 * u), (hx + sw * 1.05, top + 0.05 * u), (hx + sw * 1.15, top + 1.7 * u), (c, top + 1.95 * u),
               (hx - sw * 1.15, top + 1.7 * u)]
        poly(d, pts, col)
        ell(d, hx + f * sw * 0.7, top + 0.3 * u, 0.18 * u, 0.18 * u, trim, w=3)


def arm_piece(d, kind, sh, el, hand, u, c1, c2):
    """Over the upper arm: lamellar shoulder guard, sode, tiraz band, puffed sleeve head."""
    ang = math.atan2(el[1] - sh[1], el[0] - sh[0])
    ca, sa = math.cos(ang), math.sin(ang)

    def P(a, b):                                                                  # a along the arm, b across it
        return sh[0] + a * ca - b * sa, sh[1] + a * sa + b * ca
    if kind == "pauldron":
        pts = [P(-0.25 * u, -0.48 * u), P(-0.25 * u, 0.48 * u), P(0.95 * u, 0.55 * u), P(0.95 * u, -0.55 * u)]
        poly(d, pts, c1, w=4)
        for t in (0.25, 0.55, 0.85):
            d.line([P(t * u, -0.5 * u), P(t * u, 0.5 * u)], fill=c2, width=3)
    elif kind == "sode":                                                          # big flat shoulder board
        pts = [P(-0.3 * u, -0.6 * u), P(-0.3 * u, 0.6 * u), P(1.25 * u, 0.62 * u), P(1.25 * u, -0.62 * u)]
        poly(d, pts, c1, w=4)
        for t in (0.15, 0.5, 0.85, 1.15):
            d.line([P(t * u, -0.58 * u), P(t * u, 0.58 * u)], fill=c2, width=max(4, int(0.13 * u)))
    elif kind == "tiraz":                                                         # inscribed gold band on the upper arm
        d.line([P(0.55 * u, -0.34 * u), P(0.55 * u, 0.34 * u)], fill=LINE, width=int(0.3 * u) + 6)
        d.line([P(0.55 * u, -0.32 * u), P(0.55 * u, 0.32 * u)], fill=GOLD, width=int(0.3 * u))
    elif kind == "puff":
        ell(d, *P(0.25 * u, 0), 0.55 * u, 0.55 * u, c1)


# ================================================================================================ props
def prop(d, kind, x, y, u, f):
    """Held objects; (x, y) = the hand. Returns False if the kind is unknown."""
    wood, steel = (120, 84, 48), (176, 180, 186)
    if kind == "bow":                                                             # composite recurve: rigid ears, string bridge
        tip_t, tip_b = (x + f * 0.05 * u, y - 2.55 * u), (x + f * 0.05 * u, y + 2.55 * u)
        up = [(x, y - 0.3 * u), (x + f * 0.5 * u, y - 1.2 * u), (x + f * 0.42 * u, y - 2.1 * u), tip_t]
        lo = [(x, y + 0.3 * u), (x + f * 0.5 * u, y + 1.2 * u), (x + f * 0.42 * u, y + 2.1 * u), tip_b]
        d.line([tip_t, (x - f * 0.25 * u, y), tip_b], fill=(230, 224, 210), width=3)
        for seg in (up, lo):
            d.line(seg, fill=LINE, width=int(0.3 * u) + 6, joint="curve")
            d.line(seg, fill=(92, 56, 34), width=int(0.3 * u), joint="curve")
        d.rectangle([x - 0.16 * u, y - 0.35 * u, x + 0.16 * u, y + 0.35 * u], fill=(217, 203, 176), outline=LINE, width=3)
    elif kind == "yumi":                                                          # long asymmetric Japanese bow
        pts = [(x + f * 0.1 * u, y + 2.2 * u), (x, y), (x + f * 0.45 * u, y - 3.0 * u), (x + f * 0.2 * u, y - 6.2 * u)]
        d.line([pts[0], (x - f * 0.25 * u, y - 0.8 * u), pts[-1]], fill=(230, 224, 210), width=3)
        d.line(pts, fill=LINE, width=int(0.26 * u) + 6, joint="curve")
        d.line(pts, fill=(36, 30, 28), width=int(0.26 * u), joint="curve")
    elif kind in ("pike", "lance", "lance_y", "spear_i"):
        top = {"pike": 9.0, "lance": 7.0, "lance_y": 7.0, "spear_i": 5.0}[kind]
        a, b = (x - f * 0.25 * u, y + 2.4 * u), (x + f * 0.5 * u, y - top * u)
        d.line([a, b], fill=LINE, width=int(0.26 * u) + 6)
        d.line([a, b], fill=wood, width=int(0.26 * u))
        hx_, hy_ = b
        poly(d, [(hx_ + f * 0.08 * u, hy_ - 0.9 * u), (hx_ + f * 0.3 * u, hy_ + 0.1 * u), (hx_ - f * 0.15 * u, hy_ + 0.12 * u)], steel, w=3)
        if kind == "lance":                                                       # hook below the point, horse-hair tassel
            d.line([(hx_, hy_ + 0.3 * u), (hx_ - f * 0.35 * u, hy_ + 0.1 * u)], fill=steel, width=5)
            poly(d, [(hx_ - 0.05 * u, hy_ + 0.35 * u), (hx_ - f * 0.4 * u, hy_ + 1.3 * u), (hx_ + f * 0.25 * u, hy_ + 1.2 * u)], (30, 28, 26), w=3)
        elif kind == "lance_y":                                                   # yellow pennon (Mamluk)
            poly(d, [(hx_ - f * 0.02 * u, hy_ + 0.3 * u), (hx_ - f * 1.6 * u, hy_ + 0.6 * u), (hx_ - f * 0.05 * u, hy_ + 1.0 * u)], (217, 169, 46), w=3)
        elif kind == "spear_i":
            ell(d, hx_ - f * 0.02 * u, hy_ + 0.35 * u, 0.2 * u, 0.25 * u, (170, 40, 40), w=3)
    elif kind in ("musket", "matchlock"):
        a, b = (x - f * 0.35 * u, y + 2.2 * u), (x + f * 0.45 * u, y - 4.8 * u)
        d.line([a, b], fill=LINE, width=int(0.3 * u) + 6)
        d.line([a, b], fill=(60, 60, 66) if kind == "musket" else (80, 70, 60), width=int(0.3 * u))
        d.line([(x - f * 0.42 * u, y + 2.5 * u), (x - f * 0.08 * u, y + 0.1 * u)], fill=LINE, width=int(0.66 * u) + 6)
        d.line([(x - f * 0.42 * u, y + 2.5 * u), (x - f * 0.08 * u, y + 0.1 * u)], fill=(110, 70, 40), width=int(0.6 * u))
        if kind == "musket":                                                      # socket bayonet
            d.line([b, (b[0] + f * 0.2 * u, b[1] - 1.7 * u)], fill=LINE, width=7)
            d.line([b, (b[0] + f * 0.2 * u, b[1] - 1.7 * u)], fill=steel, width=4)
        else:                                                                     # smouldering match cord
            d.line([(x - f * 0.1 * u, y + 0.6 * u), (x - f * 0.6 * u, y + 1.2 * u), (x - f * 0.4 * u, y + 2.0 * u)], fill=(200, 190, 160), width=3)
            d.ellipse([x - f * 0.4 * u - 5, y + 2.0 * u - 5, x - f * 0.4 * u + 5, y + 2.0 * u + 5], fill=(240, 90, 40))
    elif kind in ("sword", "sabre", "talwar"):
        pts = [(x, y), (x + f * 0.3 * u, y - 1.5 * u), (x + f * 0.4 * u, y - 3.2 * u)]
        if kind == "sword":
            pts = [(x, y), (x + f * 0.2 * u, y - 3.3 * u)]
        elif kind == "talwar":
            pts = [(x, y), (x + f * 0.45 * u, y - 1.6 * u), (x + f * 0.75 * u, y - 3.0 * u)]
        d.line(pts, fill=LINE, width=int(0.24 * u) + 6, joint="curve")
        d.line(pts, fill=steel, width=int(0.24 * u), joint="curve")
        d.line([(x - 0.45 * u, y - 0.15 * u), (x + 0.45 * u, y - 0.15 * u)], fill=LINE, width=int(0.16 * u) + 4)
        d.line([(x - 0.45 * u, y - 0.15 * u), (x + 0.45 * u, y - 0.15 * u)], fill=GOLD, width=int(0.16 * u))
        if kind == "talwar":
            ell(d, x, y + 0.35 * u, 0.22 * u, 0.1 * u, GOLD, w=3)
    elif kind == "whip":
        d.line([(x, y), (x + f * 0.5 * u, y - 1.0 * u)], fill=LINE, width=int(0.18 * u) + 6)
        d.line([(x, y), (x + f * 0.5 * u, y - 1.0 * u)], fill=(90, 56, 34), width=int(0.18 * u))
        d.line([(x + f * 0.5 * u, y - 1.0 * u), (x + f * 1.2 * u, y - 0.6 * u), (x + f * 1.4 * u, y + 0.4 * u)], fill=(70, 46, 30), width=4, joint="curve")
    elif kind == "tuq":                                                           # white nine-tail standard
        a, b = (x - f * 0.1 * u, y + 2.4 * u), (x + f * 0.3 * u, y - 7.5 * u)
        d.line([a, b], fill=LINE, width=int(0.24 * u) + 6)
        d.line([a, b], fill=wood, width=int(0.24 * u))
        tx, ty = b
        for i in range(9):
            dx = (i - 4) * 0.13 * u
            d.line([(tx + dx * 0.3, ty + 0.4 * u), (tx + dx, ty + 1.9 * u)], fill=LINE, width=int(0.2 * u) + 4)
            d.line([(tx + dx * 0.3, ty + 0.4 * u), (tx + dx, ty + 1.9 * u)], fill=(232, 226, 210), width=int(0.2 * u))
        ell(d, tx, ty + 0.35 * u, 0.4 * u, 0.15 * u, (200, 170, 90), w=3)
        for dx in (-0.3, 0, 0.3):
            d.line([(tx + dx * u, ty + 0.3 * u), (tx + dx * u * 1.2, ty - 0.6 * u)], fill=LINE, width=7)
            d.line([(tx + dx * u, ty + 0.3 * u), (tx + dx * u * 1.2, ty - 0.6 * u)], fill=steel, width=4)
    elif kind == "cup":
        poly(d, [(x - 0.35 * u, y - 0.85 * u), (x + 0.35 * u, y - 0.85 * u), (x + 0.15 * u, y - 0.25 * u), (x - 0.15 * u, y - 0.25 * u)], GOLD, w=4)
    elif kind == "chao":                                                          # Yuan paper money
        d.rectangle([x - 0.45 * u, y - 1.5 * u, x + 0.45 * u, y - 0.1 * u], fill=(185, 169, 138), outline=LINE, width=4)
        d.rectangle([x - 0.32 * u, y - 1.35 * u, x + 0.32 * u, y - 0.25 * u], outline=(40, 34, 30), width=2)
        d.rectangle([x - 0.2 * u, y - 0.65 * u, x + 0.05 * u, y - 0.4 * u], fill=(178, 50, 42))
    elif kind == "ledger":                                                        # bahi account book in red cloth
        d.rounded_rectangle([x - 0.45 * u, y - 1.6 * u, x + 0.45 * u, y + 0.2 * u], radius=5, fill=(168, 34, 40), outline=LINE, width=4)
        d.line([(x - 0.45 * u, y - 0.7 * u), (x + 0.45 * u, y - 0.7 * u)], fill=(226, 190, 90), width=3)
    elif kind == "moneybag":
        ell(d, x, y + 0.45 * u, 0.6 * u, 0.55 * u, (226, 214, 186))
        d.polygon([(x - 0.2 * u, y - 0.2 * u), (x + 0.2 * u, y - 0.2 * u), (x, y + 0.1 * u)], fill=(200, 186, 156), outline=LINE)
    elif kind == "bale":
        d.rounded_rectangle([x - 0.8 * u, y - 0.6 * u, x + 0.8 * u, y + 0.7 * u], radius=8, fill=(214, 196, 160), outline=LINE, width=4)
        for i in range(3):
            d.line([(x - 0.8 * u + (i + 1) * 0.4 * u, y - 0.6 * u), (x - 0.8 * u + (i + 1) * 0.4 * u, y + 0.7 * u)], fill=(150, 60, 50), width=4)
    elif kind == "cross":
        d.line([(x, y + 0.3 * u), (x, y - 1.6 * u)], fill=LINE, width=int(0.16 * u) + 4)
        d.line([(x, y + 0.3 * u), (x, y - 1.6 * u)], fill=wood, width=int(0.16 * u))
        d.line([(x - 0.45 * u, y - 1.1 * u), (x + 0.45 * u, y - 1.1 * u)], fill=LINE, width=int(0.16 * u) + 4)
        d.line([(x - 0.45 * u, y - 1.1 * u), (x + 0.45 * u, y - 1.1 * u)], fill=wood, width=int(0.16 * u))
    elif kind == "charter":                                                       # parchment with a hanging red seal
        d.rectangle([x - 0.2 * u, y - 1.6 * u, x + f * 1.4 * u if f > 0 else x + 0.2 * u, y - 0.2 * u], fill=(244, 232, 200), outline=LINE, width=4)
        x0 = min(x - 0.2 * u, x + f * 1.4 * u)
        for i in range(4):
            d.line([(x0 + 0.25 * u, y - 1.35 * u + i * 0.3 * u), (x0 + 1.25 * u, y - 1.35 * u + i * 0.3 * u)], fill=(150, 130, 100), width=2)
        d.line([(x0 + 0.8 * u, y - 0.2 * u), (x0 + 0.8 * u, y + 0.35 * u)], fill=(150, 40, 40), width=3)
        ell(d, x0 + 0.8 * u, y + 0.55 * u, 0.25 * u, 0.25 * u, (170, 30, 36), w=3)
    elif kind == "fan":
        d.pieslice([x - 1.0 * u, y - 1.8 * u, x + 1.0 * u, y + 0.2 * u], 220, 320, fill=WHITE, outline=LINE, width=4)
        d.line([(x, y - 0.8 * u), (x, y + 0.3 * u)], fill=GOLD, width=5)
    elif kind == "oar":
        a, b = (x - f * 0.6 * u, y + 3.0 * u), (x + f * 0.4 * u, y - 3.6 * u)
        d.line([a, b], fill=LINE, width=int(0.22 * u) + 6)
        d.line([a, b], fill=wood, width=int(0.22 * u))
        poly(d, [(a[0] - 0.25 * u, a[1] - 0.9 * u), (a[0] + 0.25 * u, a[1] - 0.9 * u), (a[0] + 0.3 * u, a[1] + 0.3 * u), (a[0] - 0.3 * u, a[1] + 0.3 * u)], wood, w=3)
    elif kind == "cloth":                                                         # a bolt of Bengal muslin
        d.rounded_rectangle([x - 1.0 * u, y - 0.45 * u, x + 1.0 * u, y + 0.45 * u], radius=0.4 * u, fill=(246, 244, 236), outline=LINE, width=4)
        for i in range(4):
            d.arc([x - 1.0 * u + i * 0.5 * u, y - 0.45 * u, x - 0.6 * u + i * 0.5 * u, y + 0.45 * u], 270, 90, fill=(210, 206, 196), width=3)
    elif kind == "adze":
        d.line([(x, y + 0.4 * u), (x + f * 0.3 * u, y - 1.4 * u)], fill=LINE, width=int(0.2 * u) + 6)
        d.line([(x, y + 0.4 * u), (x + f * 0.3 * u, y - 1.4 * u)], fill=wood, width=int(0.2 * u))
        poly(d, [(x + f * 0.2 * u, y - 1.5 * u), (x + f * 1.0 * u, y - 1.3 * u), (x + f * 1.05 * u, y - 0.95 * u), (x + f * 0.3 * u, y - 1.15 * u)], steel, w=3)
    elif kind == "telescope":
        d.line([(x - f * 0.6 * u, y + 0.3 * u), (x + f * 1.6 * u, y - 0.7 * u)], fill=LINE, width=int(0.36 * u) + 6)
        d.line([(x - f * 0.6 * u, y + 0.3 * u), (x + f * 1.6 * u, y - 0.7 * u)], fill=(226, 190, 90), width=int(0.36 * u))
    elif kind == "vina":                                                          # rudra vina: a stick with two gourds
        a, b = (x - f * 1.5 * u, y + 0.9 * u), (x + f * 1.6 * u, y - 1.3 * u)
        ell(d, a[0], a[1] + 0.4 * u, 0.6 * u, 0.6 * u, (176, 110, 60))
        ell(d, b[0], b[1] + 0.4 * u, 0.55 * u, 0.55 * u, (176, 110, 60))
        d.line([a, b], fill=LINE, width=int(0.26 * u) + 6)
        d.line([a, b], fill=(60, 36, 24), width=int(0.26 * u))
    elif kind == "crossbow":
        d.line([(x - f * 0.3 * u, y + 0.8 * u), (x + f * 1.4 * u, y - 0.9 * u)], fill=LINE, width=int(0.24 * u) + 6)
        d.line([(x - f * 0.3 * u, y + 0.8 * u), (x + f * 1.4 * u, y - 0.9 * u)], fill=wood, width=int(0.24 * u))
        d.arc([x + f * 0.9 * u - 1.0 * u, y - 1.4 * u - 1.0 * u, x + f * 0.9 * u + 1.0 * u, y - 1.4 * u + 1.0 * u], 0, 360, fill=None)
        d.line([(x + f * 0.4 * u, y - 1.5 * u), (x + f * 1.8 * u, y - 0.1 * u)], fill=LINE, width=int(0.18 * u) + 4)
        d.line([(x + f * 0.4 * u, y - 1.5 * u), (x + f * 1.8 * u, y - 0.1 * u)], fill=(92, 56, 34), width=int(0.18 * u))
    elif kind == "tablet":                                                        # official's ivory tablet (hu)
        d.rounded_rectangle([x - 0.18 * u, y - 1.7 * u, x + 0.18 * u, y + 0.1 * u], radius=6, fill=(236, 228, 206), outline=LINE, width=4)
    elif kind == "flower":
        d.line([(x, y), (x + f * 0.2 * u, y - 1.0 * u)], fill=(60, 120, 60), width=5)
        ell(d, x + f * 0.2 * u, y - 1.15 * u, 0.25 * u, 0.25 * u, (230, 120, 140), w=3)
    else:
        return False
    return True


# ================================================================================================ animals
# Horses: Mongolian pony 12-14 hands, big head, short thick neck, heavy mane; "big" = European/Mamluk warhorse, taller.
HORSE = {"mongol": dict(B=3.0, ry=1.2, len=6.3, neck=1.85, head=1.95, mane=0.6, arch=(0.75, 0.5), seat=-0.2),
         "big": dict(B=3.75, ry=1.32, len=7.3, neck=2.5, head=2.15, mane=0.32, arch=(0.6, 0.55), seat=-0.2)}
GAITS = {"gallop": (0.38, 34, 75, {"hind_far": 0.0, "hind_near": 0.1, "fore_far": 0.42, "fore_near": 0.52}),
         "walk": (0.62, 18, 50, {"hind_near": 0.0, "fore_near": 0.25, "hind_far": 0.5, "fore_far": 0.75}),
         "pace": (0.55, 20, 55, {"hind_near": 0.0, "fore_near": 0.03, "hind_far": 0.5, "fore_far": 0.53})}


def _leg_angles(name, phase, gait):
    if phase is None:
        return (2.0 if name.startswith("fore") else -2.0), 0.0
    st, A, Bm, offs = GAITS[gait]
    s = (phase + offs[name]) % 1.0
    if s < st:
        return A * (1 - 2 * s / st), 0.0
    t = (s - st) / (1 - st)
    e = t * t * (3 - 2 * t)
    return -A + 2 * A * e, Bm * math.sin(math.pi * t)


def _leg_pts(name, ax, ay, l1, l2, phase, gait):
    a1, bend = _leg_angles(name, phase, gait)
    if name.startswith("fore"):
        knee = _down(ax, ay, a1, l1, 1)
        hoof = _down(*knee, a1 - bend, l2, 1)
    else:                                                                         # hind: thigh angled back, cannon forward (hock)
        knee = _down(ax, ay, a1 - 16, l1, 1)
        hoof = _down(*knee, a1 + 12 - bend, l2, 1)
    return knee, hoof


@lru_cache(maxsize=1500)
def horse_sprite(kind, coat, mane, tack, cloth, phase_q, gait, u, f, stripe=False):
    """Profile horse facing f. Returns (RGBA image, ground anchor x, y, seat x, y). phase_q: gait phase in 1/24ths or -1 standing."""
    g = HORSE[kind]
    phase = None if phase_q < 0 else phase_q / 24
    B, ry, ln, nk, hd = g["B"] * u, g["ry"] * u, g["len"] * u, g["neck"] * u, g["head"] * u
    W, Hh = int(ln + 6 * u), int(B + 2 * ry + nk + hd + 3 * u)
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gx, gy = W / 2 - 0.6 * u * f, Hh - 0.5 * u
    cy0 = gy - B - ry
    attach = 0.45 * ry
    l1 = l2 = (B + ry - attach) / 2
    legs = {"fore_far": (ln / 2 - 0.85 * ry + 0.25 * u, True), "hind_far": (-ln / 2 + 0.95 * ry + 0.2 * u, True),
            "fore_near": (ln / 2 - 0.85 * ry, False), "hind_near": (-ln / 2 + 0.95 * ry, False)}
    low = 0.0
    sol = {}
    for name, (lx, far) in legs.items():
        knee, hoof = _leg_pts(name, lx, cy0 + attach, l1, l2, phase, gait)
        sol[name] = (lx, knee, hoof, far)
        low = max(low, hoof[1])
    drop = min(0.45 * u, max(0.0, gy - low - 0.05 * u))                          # lowest hoof on the ground
    cy = cy0 + drop

    def P(x, y):
        return gx + f * x, y + drop

    def leg(name, dark):
        lx, knee, hoof, far = sol[name]
        col = shade(coat, 0.78) if dark else coat
        a, kn, ho = P(lx, cy0 + attach), P(*knee), P(*hoof)
        limb(d, [a, kn, ho], [0.62 * u * (1.15 if kind == "mongol" else 1.0), 0.36 * u], [col, col])
        ell(d, ho[0] + f * 0.08 * u, ho[1] + 0.02 * u, 0.26 * u, 0.17 * u, (40, 34, 30), w=3)
        if kind == "mongol" or name.startswith("hind"):
            d.line([(kn[0], kn[1] + 0.5 * u), (ho[0], ho[1] - 0.3 * u)], fill=shade(col, 0.85), width=3)
    for n in ("hind_far", "fore_far"):
        leg(n, True)
    sw_ = 0.35 * u * (math.sin(2 * math.pi * (phase or 0)) if phase is not None else 0)  # tail
    tr = P(-ln / 2 + 0.15 * ry, cy0 - 0.55 * ry)
    tail = [tr, P(-ln / 2 - 0.6 * u, cy0 + 0.1 * ry), P(-ln / 2 - 0.7 * u - sw_, cy0 + 1.7 * ry), P(-ln / 2 - 0.1 * u - sw_, cy0 + 1.85 * ry),
            P(-ln / 2 + 0.1 * u, cy0 + 0.3 * ry)]
    poly(d, tail, mane)
    body = coat
    ell(d, *P(-ln / 2 + 0.8 * ry, cy0 - 0.1 * ry), 1.08 * ry, 1.08 * ry, body)   # rump
    ell(d, *P(0, cy0), ln / 2 - 0.4 * ry, ry, body)                             # barrel
    ell(d, *P(ln / 2 - 0.75 * ry, cy0 + 0.05 * ry), 0.98 * ry, 0.98 * ry, body)  # chest
    d.chord([min(P(-ln / 2 + 0.6 * ry, 0)[0], P(ln / 2 - 0.7 * ry, 0)[0]), cy + 0.2 * ry, max(P(-ln / 2 + 0.6 * ry, 0)[0], P(ln / 2 - 0.7 * ry, 0)[0]),
             cy + 1.0 * ry], 0, 180, fill=shade(body, 0.86))
    poll = (ln / 2 + nk * 0.3, cy0 - ry - nk * 0.95)
    neck = [P(ln / 2 - 1.7 * ry, cy0 - 0.8 * ry), P(poll[0] - 0.35 * u, poll[1] + 0.1 * u), P(poll[0] + 0.55 * u, poll[1] + 0.75 * u),
            P(ln / 2 + 0.25 * ry, cy0 + 0.3 * ry), P(ln / 2 - 0.9 * ry, cy0 + 0.2 * ry)]
    poly(d, neck, body)
    mu = (poll[0] + hd * 0.78, poll[1] + hd * 0.9)                               # head: cheek, face, muzzle
    ell(d, *P(poll[0] + 0.2 * u, poll[1] + 0.62 * u), 0.62 * u * hd / (1.55 * u), 0.58 * u * hd / (1.55 * u), body)
    hp = [P(poll[0] - 0.05 * u, poll[1] - 0.05 * u), P(mu[0] + 0.15 * u, mu[1] - 0.3 * u), P(mu[0] + 0.05 * u, mu[1] + 0.35 * u),
          P(poll[0] + 0.25 * u, poll[1] + 1.15 * u)]
    poly(d, hp, body)
    ell(d, *P(*mu), 0.4 * u, 0.4 * u, tint(body, 0.12) if coat[0] < 200 else shade(body, 0.92))
    d.ellipse([P(mu[0] + 0.12 * u, 0)[0] - 4, mu[1] + drop - 0.05 * u - 4, P(mu[0] + 0.12 * u, 0)[0] + 4, mu[1] + drop - 0.05 * u + 4], fill=LINE)
    ex, ey = P(poll[0] + 0.45 * u, poll[1] + 0.4 * u)
    d.ellipse([ex - 0.12 * u, ey - 0.12 * u, ex + 0.12 * u, ey + 0.12 * u], fill=(24, 20, 20))
    d.ellipse([ex - 0.04 * u, ey - 0.09 * u, ex + 0.03 * u, ey - 0.02 * u], fill=(255, 255, 255))
    poly(d, [P(poll[0] - 0.15 * u, poll[1] + 0.05 * u), P(poll[0] - 0.05 * u, poll[1] - 0.65 * u), P(poll[0] + 0.25 * u, poll[1] + 0.05 * u)], body, w=4)
    if stripe:
        d.line([P(poll[0] + 0.5 * u, poll[1] + 0.25 * u), P(mu[0] + 0.05 * u, mu[1] - 0.25 * u)], fill=(240, 236, 228), width=int(0.16 * u))
    mt = g["mane"] * u                                                            # mane along the crest, forelock
    crest = [P(poll[0] - 0.1 * u, poll[1] - 0.15 * u), P(ln / 2 - 1.75 * ry, cy0 - 0.85 * ry)]
    mp = [crest[0], P(poll[0] - 0.1 * u - mt, poll[1] - 0.1 * u - 0.3 * mt), P(ln / 2 - 1.75 * ry - mt * 0.8, cy0 - 0.85 * ry - mt * 0.6), crest[1],
          P(ln / 2 - 1.45 * ry, cy0 - 0.55 * ry), P(poll[0] + 0.05 * u, poll[1] + 0.4 * u)]
    poly(d, mp, mane)
    for i in range(1, 5):
        t = i / 5
        p0 = (crest[0][0] + (crest[1][0] - crest[0][0]) * t, crest[0][1] + (crest[1][1] - crest[0][1]) * t)
        d.line([p0, (p0[0] - f * 0.35 * u, p0[1] - 0.1 * u)], fill=shade(mane, 0.6), width=3)
    poly(d, [P(poll[0] + 0.05 * u, poll[1] - 0.05 * u), P(poll[0] + 0.55 * u, poll[1] + 0.05 * u), P(poll[0] + 0.25 * u, poll[1] + 0.45 * u)], mane, w=3)
    # tack: saddle cloth, saddle with high arches, breast strap, crupper, bridle, reins
    sx = g["seat"] * u
    top = cy0 - ry
    if cloth:
        cl = [P(sx - 1.1 * u, top + 0.05 * u), P(sx + 1.0 * u, top + 0.05 * u), P(sx + 1.15 * u, cy0 + 0.55 * ry), P(sx - 1.25 * u, cy0 + 0.55 * ry)]
        poly(d, cl, cloth)
        for i in range(10):
            xx = P(sx - 1.2 * u + i * 0.26 * u, 0)[0]
            d.line([(xx, cy + 0.55 * ry), (xx, cy + 0.55 * ry + 0.25 * u)], fill=shade(cloth, 0.7), width=3)
    d.line([P(sx + 0.8 * u, top + 0.3 * u), P(ln / 2 + 0.1 * ry, cy0 + 0.1 * ry)], fill=LINE, width=int(0.2 * u) + 4)
    d.line([P(sx + 0.8 * u, top + 0.3 * u), P(ln / 2 + 0.1 * ry, cy0 + 0.1 * ry)], fill=tack, width=int(0.2 * u))
    d.line([P(sx - 0.8 * u, top + 0.2 * u), P(-ln / 2 + 0.2 * ry, cy0 - 0.4 * ry)], fill=LINE, width=int(0.16 * u) + 4)
    d.line([P(sx - 0.8 * u, top + 0.2 * u), P(-ln / 2 + 0.2 * ry, cy0 - 0.4 * ry)], fill=tack, width=int(0.16 * u))
    fa, ba = g["arch"]
    sad = [P(sx - 0.95 * u, top - ba * u), P(sx - 0.7 * u, top + 0.05 * u), P(sx + 0.7 * u, top + 0.05 * u), P(sx + 0.95 * u, top - fa * u),
           P(sx + 0.72 * u, top - fa * u), P(sx + 0.5 * u, top - 0.2 * u), P(sx - 0.55 * u, top - 0.2 * u), P(sx - 0.72 * u, top - ba * u)]
    poly(d, sad, (90, 42, 30) if kind == "mongol" else (110, 72, 44))
    if kind == "mongol":
        ell(d, *P(sx + 0.83 * u, top - fa * u * 0.6), 0.1 * u, 0.12 * u, (199, 201, 204), w=2)        # silver arch plaque
    nb = P(mu[0] - 0.2 * u, mu[1] - 0.05 * u)
    for a, b in ((P(poll[0] + 0.05 * u, poll[1] + 0.05 * u), nb), (P(mu[0] - 0.35 * u, mu[1] - 0.45 * u), P(mu[0] - 0.25 * u, mu[1] + 0.35 * u)),
                 (P(poll[0] + 0.15 * u, poll[1] + 0.1 * u), P(poll[0] + 0.65 * u, poll[1] + 0.15 * u))):
        d.line([a, b], fill=LINE, width=7)
        d.line([a, b], fill=tack, width=4)
    rein_end = P(sx + 0.85 * u, top - 0.4 * u)
    d.line([nb, P(poll[0] - 0.4 * u, poll[1] + 1.4 * u), rein_end], fill=LINE, width=6)
    d.line([nb, P(poll[0] - 0.4 * u, poll[1] + 1.4 * u), rein_end], fill=tack, width=3)
    for n in ("hind_near", "fore_near"):
        leg(n, False)
    seat = P(sx, top - 0.12 * u)
    return im, gx, gy, seat[0], seat[1]


@lru_cache(maxsize=600)
def camel_sprite(coat, phase_q, u, f, load=True):
    """Bactrian camel in profile facing f, pacing; shaggy winter coat on neck, humps and upper legs."""
    phase = None if phase_q < 0 else phase_q / 24
    B, ry, ln = 4.0 * u, 1.15 * u, 5.2 * u
    W, Hh = int(ln + 7 * u), int(B + 2 * ry + 5 * u)
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gx, gy = W / 2 - 0.8 * u * f, Hh - 0.5 * u
    cy0 = gy - B - ry
    attach = 0.5 * ry
    l1 = l2 = (B + ry - attach) / 2
    shag = shade(coat, 0.72)
    legs = {"fore_far": (ln / 2 - 0.8 * ry + 0.25 * u, True), "hind_far": (-ln / 2 + 0.9 * ry + 0.2 * u, True),
            "fore_near": (ln / 2 - 0.8 * ry, False), "hind_near": (-ln / 2 + 0.9 * ry, False)}
    sol, low = {}, 0.0
    for name, (lx, far) in legs.items():
        knee, hoof = _leg_pts(name, lx, cy0 + attach, l1, l2, phase, "pace")
        sol[name] = (lx, knee, hoof)
        low = max(low, hoof[1])
    drop = min(0.4 * u, max(0.0, gy - low - 0.05 * u))
    cy = cy0 + drop

    def P(x, y):
        return gx + f * x, y + drop

    def leg(name, dark):
        lx, knee, hoof = sol[name]
        col = shade(coat, 0.8) if dark else coat
        a, kn, ho = P(lx, cy0 + attach), P(*knee), P(*hoof)
        limb(d, [a, kn, ho], [0.62 * u, 0.36 * u], [col, col])
        ell(d, *kn, 0.26 * u, 0.24 * u, col, w=3)                                # knobby knee
        ell(d, ho[0] + f * 0.1 * u, ho[1] + 0.02 * u, 0.4 * u, 0.17 * u, shade(col, 0.75), w=3)   # broad padded foot
        if name.startswith("fore"):
            fur_pts = [P(lx - 0.35 * u, cy0 + attach), P(lx + 0.4 * u, cy0 + attach), P(knee[0] + 0.25 * u, knee[1] - 0.4 * u), P(knee[0] - 0.3 * u, knee[1] - 0.3 * u)]
            poly(d, fur_pts, shade(shag, 0.85 if dark else 1.0), w=3)
    for n in ("hind_far", "fore_far"):
        leg(n, True)
    d.line([P(-ln / 2 + 0.1 * u, cy0 - 0.3 * ry), P(-ln / 2 - 0.25 * u, cy0 + 1.2 * ry)], fill=LINE, width=int(0.2 * u) + 6)
    d.line([P(-ln / 2 + 0.1 * u, cy0 - 0.3 * ry), P(-ln / 2 - 0.25 * u, cy0 + 1.2 * ry)], fill=coat, width=int(0.2 * u))
    ell(d, *P(-ln / 2 - 0.27 * u, cy0 + 1.35 * ry), 0.18 * u, 0.3 * u, shag, w=3)
    for hx_ in (-1.1 * u, 1.0 * u):                                               # two humps, shaggy tops
        ell(d, *P(hx_, cy0 - ry - 0.55 * u), 0.95 * u, 1.05 * u, coat)
        fur(d, [P(hx_, 0)[0] - 0.75 * u, cy - ry - 1.55 * u, P(hx_, 0)[0] + 0.75 * u, cy - ry - 0.95 * u], shag, u)
    ell(d, *P(0, cy0), ln / 2, ry, coat)
    d.chord([P(-ln / 2 + 0.3 * u, 0)[0] if f > 0 else P(ln / 2 - 0.3 * u, 0)[0], cy + 0.1 * ry, P(ln / 2 - 0.3 * u, 0)[0] if f > 0 else P(-ln / 2 + 0.3 * u, 0)[0],
             cy + ry], 0, 180, fill=shade(coat, 0.86))
    if load:                                                                      # bales in striped cloth between the humps
        bx = P(0, 0)[0]
        for dx in (-0.55, 0.45):
            x = bx + f * dx * u
            d.rounded_rectangle([x - 0.75 * u, cy - ry - 0.6 * u, x + 0.75 * u, cy + 0.35 * ry], radius=10, fill=(206, 186, 146), outline=LINE, width=4)
            for i in range(3):
                yy = cy - ry - 0.35 * u + i * 0.5 * u
                d.line([(x - 0.72 * u, yy), (x + 0.72 * u, yy)], fill=(150, 60, 50), width=5)
        d.line([P(-1.4 * u, cy0 - ry - 0.5 * u), P(1.4 * u, cy0 - ry - 0.5 * u)], fill=(90, 60, 40), width=6)
    neck = [P(ln / 2 - 0.7 * ry, cy0 - 0.6 * ry), P(ln / 2 + 0.6 * u, cy0 - 0.2 * u), P(ln / 2 + 1.6 * u, cy0 - 1.2 * u), P(ln / 2 + 1.85 * u, cy0 - 2.6 * u),
            P(ln / 2 + 2.55 * u, cy0 - 2.55 * u), P(ln / 2 + 2.35 * u, cy0 - 1.0 * u), P(ln / 2 + 1.2 * u, cy0 + 0.75 * u), P(ln / 2 - 0.2 * u, cy0 + 0.6 * ry)]
    poly(d, neck, coat)
    for i in range(5):                                                            # shaggy throat
        x, y = P(ln / 2 + 0.75 * u + i * 0.3 * u, cy0 + 0.35 * u - i * 0.3 * u)
        d.polygon([(x - 0.25 * u, y - 0.1 * u), (x + 0.25 * u, y - 0.3 * u), (x + 0.05 * u, y + 0.45 * u)], fill=shag, outline=LINE)
    hx0, hy0 = ln / 2 + 2.2 * u, cy0 - 2.75 * u
    ell(d, *P(hx0 + 0.5 * u, hy0 + 0.15 * u), 1.05 * u, 0.48 * u, coat)
    ell(d, *P(hx0 + 1.35 * u, hy0 + 0.3 * u), 0.38 * u, 0.36 * u, tint(coat, 0.1))
    fur(d, [P(hx0 - 0.2 * u, 0)[0] - 0.45 * u, hy0 - 0.65 * u + drop, P(hx0 - 0.2 * u, 0)[0] + 0.45 * u, hy0 - 0.2 * u + drop], shag, u)
    poly(d, [P(hx0 - 0.35 * u, hy0 - 0.3 * u), P(hx0 - 0.5 * u, hy0 - 0.75 * u), P(hx0 - 0.1 * u, hy0 - 0.4 * u)], coat, w=3)
    ex, ey = P(hx0 + 0.45 * u, hy0 - 0.05 * u)
    d.ellipse([ex - 0.12 * u, ey - 0.1 * u, ex + 0.12 * u, ey + 0.1 * u], fill=(24, 20, 20))
    d.arc([ex - 0.16 * u, ey - 0.2 * u, ex + 0.16 * u, ey + 0.02 * u], 200, 340, fill=LINE, width=3)
    d.line([P(hx0 + 1.45 * u, hy0 + 0.45 * u), P(hx0 + 1.65 * u, hy0 + 0.4 * u)], fill=LINE, width=3)
    d.line([P(hx0 + 0.9 * u, hy0 - 0.2 * u), P(hx0 + 0.9 * u, hy0 + 0.6 * u)], fill=(150, 40, 40), width=5)        # halter
    d.line([P(hx0 + 0.9 * u, hy0 + 0.6 * u), P(hx0 + 0.6 * u, hy0 + 2.6 * u), P(hx0 + 1.4 * u, hy0 + 4.0 * u)], fill=(120, 90, 60), width=4)
    for n in ("hind_near", "fore_near"):
        leg(n, False)
    return im, gx, gy
