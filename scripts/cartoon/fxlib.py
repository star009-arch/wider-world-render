"""Shared on-screen effects for Tiny Empires episodes (cards, hook graphics, title sting, next-episode tease).

Every function returns fx(t, draw, frame) for scene.Shot.fx. Text uses ep01.S_text (house font).
"""
from __future__ import annotations

import math

import motions as M
from scene import ease

GOLD, INK = (255, 214, 120), (30, 24, 20, 255)
PANEL = (30, 24, 20, 225)
EDGE = (214, 172, 72, 255)


def _T(d, x, y, text, size, a=1.0, anchor="lm", color=(255, 255, 255)):
    import ep01 as K
    K.S_text(d, x, y, text, size, a=a, anchor=anchor, color=color)


def no_list(t0, words, times, final, final_t, y=250):
    """Words pop up in red boxes and are struck out one by one, then the gold answer appears."""
    n = len(words)
    gap = 1700 / max(1, n)

    def f(t, d, frame):
        for i, w in enumerate(words):
            ts = t0 + times[i]
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.3)
            x = 110 + gap * (i + 0.5)
            hw = min(220, gap / 2 - 16)
            d.rounded_rectangle([x - hw * k, y - 60 * k, x + hw * k, y + 60 * k], radius=22, fill=(30, 24, 20, 230), outline=(230, 80, 60, 255), width=5)
            if k > 0.8:
                _T(d, x, y, w, 48, anchor="mm")
                if t > ts + 0.35:
                    d.line([(x - hw + 20, y + 40), (x + hw - 20, y - 40)], fill=(230, 50, 40, 255), width=12)
        if t >= t0 + final_t:
            k = M.ease_out_back((t - t0 - final_t) / 0.35)
            d.rounded_rectangle([960 - 460 * k, y + 150 - 75 * k, 960 + 460 * k, y + 150 + 75 * k], radius=26, fill=(30, 24, 20, 230), outline=EDGE, width=5)
            if k > 0.8:
                _T(d, 960, y + 150, final, 72, anchor="mm", color=GOLD)
    return f


def title_sting(t0, title, sub=None):
    """Channel name punches in over a darkened frame, then the episode title."""
    def f(t, d, frame):
        if t < t0:
            return
        k = M.ease_out_back((t - t0) / 0.45)
        d.rectangle([0, 0, 1920, 1080], fill=(12, 10, 16, int(150 * min(1, (t - t0) / 0.3))))
        sz = int(150 * k)
        if sz > 10:
            _T(d, 960, 380, "TINY EMPIRES", sz, anchor="mm", color=GOLD)
        if t > t0 + 0.6:
            a = ease((t - t0 - 0.6) / 0.4)
            _T(d, 960, 540, title, 64, a=a, anchor="mm")
            if sub:
                _T(d, 960, 620, sub, 42, a=a, anchor="mm", color=(255, 236, 190))
    return f


def next_time(t0, title, kicker="NEXT SATURDAY"):
    def f(t, d, frame):
        if t < t0:
            return
        k = M.ease_out_back((t - t0) / 0.4)
        w = max(560, 30 * len(title))
        d.rounded_rectangle([960 - w * k, 70, 960 + w * k, 250], radius=28, fill=PANEL, outline=EDGE, width=5)
        if k > 0.8:
            _T(d, 960, 125, kicker, 50, anchor="mm", color=(255, 236, 190))
            _T(d, 960, 200, title, 72, anchor="mm", color=GOLD)
    return f


def stats(t0, items, step=1.6, x=180, y=230):
    def f(t, d, frame):
        for i, (big, small) in enumerate(items):
            ts = t0 + i * step
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.45)
            yy = y + i * 200
            d.rounded_rectangle([x, yy, x + 980 * k, yy + 160], radius=26, fill=(30, 24, 20, 220), outline=EDGE, width=4)
            if k > 0.9:
                _T(d, x + 40, yy + 62, big, 72, color=GOLD)
                _T(d, x + 40, yy + 126, small, 34, color=(236, 228, 210))
    return f


def bars(t0, rows, unit="", y0=330, maxw=900):
    """Horizontal comparison bars: rows = [(label, value, (r,g,b)), ...]."""
    vmax = max(v for _, v, _ in rows) or 1

    def f(t, d, frame):
        for i, (lab, v, col) in enumerate(rows):
            ts = t0 + i * 0.8
            if t < ts:
                continue
            k = ease((t - ts) / 0.6)
            y = y0 + i * 170
            _T(d, 140, y + 50, lab, 44, color=GOLD)
            d.rectangle([560, y, 560 + maxw * v / vmax * k, y + 100], fill=col + (255,), outline=INK, width=4)
            if k > 0.95 and unit:
                _T(d, 580 + maxw * v / vmax, y + 50, unit.format(v), 40)
    return f


def family(t0, root, children, step=0.8):
    """A small family tree: root box, then children boxes appearing one by one."""
    def f(t, d, frame):
        if t < t0:
            return
        k = M.ease_out_back((t - t0) / 0.35)
        d.rounded_rectangle([760 - 260 * k, 170, 760 + 260 * k, 290], radius=20, fill=PANEL, outline=EDGE, width=4)
        if k > 0.8:
            _T(d, 760, 230, root, 50, anchor="mm", color=GOLD)
        n = len(children)
        for i, (name, note) in enumerate(children):
            ts = t0 + 0.6 + i * step
            if t < ts:
                continue
            kk = M.ease_out_back((t - ts) / 0.35)
            x = 760 + (i - (n - 1) / 2) * 340
            d.line([(760, 290), (x, 420)], fill=EDGE, width=4)
            d.rounded_rectangle([x - 150 * kk, 420, x + 150 * kk, 560], radius=18, fill=PANEL, outline=EDGE, width=3)
            if kk > 0.8:
                _T(d, x, 470, name, 42, anchor="mm")
                _T(d, x, 525, note, 28, anchor="mm", color=(255, 236, 190))
    return f


def shine(t0):
    def f(t, d, frame):
        if t < t0:
            return
        ph = ((t - t0) * 0.45) % 1
        x = 300 + ph * 1300
        for i in range(6):
            d.line([(x + i * 14, 120), (x - 260 + i * 14, 900)], fill=(255, 255, 240, 40 - i * 6), width=10)
    return f


def smoke(x0, y0, t0, n=6, col=(70, 64, 60)):
    """Rising smoke plumes over a city (sack/siege scenes): soft puffs that drift, widen and fade."""
    import random as _r
    rnd = _r.Random(7)
    seeds = [(rnd.uniform(-60, 60), rnd.uniform(0.15, 0.3), rnd.uniform(0, 1)) for _ in range(n * 10)]

    def f(t, d, frame):
        if t < t0:
            return
        for j in range(n):
            for i in range(10):
                jx, sp, off = seeds[j * 10 + i]
                ph = ((t - t0) * sp + off) % 1
                x = x0 + j * 110 + jx * 0.3 + ph * 160 + math.sin(ph * 5 + j) * 25
                y = y0 - ph * 460
                r = 26 + ph * 110
                a = int(70 * (1 - ph) * min(1.0, ph * 6))
                d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=col + (a,))
    return f


def people(world, keys, x0, ground, dx, s, flip=False, walk=None, speed=1.0, acts=None, stagger=14):
    """A row of period people from people.py ("<world>:<key>")."""
    out = []
    for i, k in enumerate(keys):
        x = x0 + i * dx
        p = M.Performer(f"{world}:{k}", x=x, ground=ground + (i % 2) * stagger, scale=s, flip=flip,
                        walks=[(walk[0] + i * 0.06, x + walk[1])] if walk else [], speed=speed, acts=list(acts or []))
        p.shadow = s > 0.6
        out.append(p)
    return out
