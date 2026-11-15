"""Battle and weather effects for the VOC pilot, drawn in the same inked Premium 2D style.

All effects are functions of time, so they animate frame by frame:
  muzzle(L, x, y, t, t_fire, f)         flash + a smoke puff that grows, drifts with the wind and fades (one shot)
  fire(L, x, y, w, h, t, seed)          flickering inked flame tongues with embers
  explosion(L, x, y, t, t0, s)          flash, fireball, smoke ring, flying debris (powder store)
  dust(L, x, y, t, t0)                  a kick of dust (feet, stakes driven into sand)
  splash(L, x, y, t, t0, s)             water splash (boats landing, men jumping into the surf)
"""
from __future__ import annotations

import math
import random

from PIL import Image

import vocart as A
from vocart import INK, Layer, S, W, H, shade

SMOKE = (226, 222, 214)
FLASH = (255, 236, 150)
FLAME = ((255, 214, 90), (246, 140, 40), (206, 64, 30))


def _puffs(L: Layer, puffs, col=SMOKE, ink=2.4, alpha=255):
    """Powder smoke as a soft painted form: lighter on top, darker underneath, soft edge, no outline."""
    def fn(d, k):
        for px, py, r in puffs:
            d.ellipse([(px - r) * k, (py - r * 0.85) * k, (px + r) * k, (py + r * 0.85) * k], fill=255)
    top = A.mix(col, (255, 252, 244), 0.35)
    bottom = shade(col, 0.72)
    form = A.soft_form(fn, top, bottom, blur=4, a=alpha, rim=((255, 240, 210), 5, -3))
    L.im.alpha_composite(form.resize((W * S, H * S), Image.BILINEAR))


def muzzle(L: Layer, x, y, t, t_fire, f=1, wind=(18, -6), size=1.0, seed=0):
    dt = t - t_fire
    if dt < 0 or dt > 3.2:
        return
    rng = random.Random(seed)
    if dt < 0.09:                                                     # the flash: a short star
        r = 26 * size
        pts = []
        for i in range(10):
            a = i / 10 * math.tau
            rr = r * (1.0 if i % 2 == 0 else 0.45)
            pts.append((x + f * 10 * size + math.cos(a) * rr * 1.3, y + math.sin(a) * rr))
        L.poly(pts, FLASH, 2.4)
        L.ellipse((x + f * 10 * size - 8 * size, y - 8 * size, x + f * 10 * size + 8 * size, y + 8 * size), (255, 255, 236), 0)
    k = min(1.0, dt / 2.6)
    alpha = 255 if dt < 1.0 else int(255 * (1 - (dt - 1.0) / 2.2) ** 1.2)
    if alpha < 8:
        return
    puffs = []
    for i in range(5):
        spread = (0.25 + 0.75 * min(1, dt * 2.5)) * (i + 1) / 5
        px = x + f * (20 + 60 * spread) * size + wind[0] * dt * (1 + 0.3 * i) + rng.uniform(-6, 6)
        py = y + wind[1] * dt * (1 + 0.2 * i) + rng.uniform(-8, 8) - 6 * dt
        r = (10 + 26 * min(1, dt * 1.8) * (0.7 + 0.3 * i / 5)) * size
        puffs.append((px, py, r))
    _puffs(L, puffs, alpha=alpha)


def fire(L: Layer, x, y, w, h, t, seed=0, embers=True):
    """Flickering flames: irregular tongues of different heights, overlapping, licking upwards (inked outer layer)."""
    rng = random.Random(seed)
    n = max(3, int(w / 34))
    tongues = []
    for i in range(n):
        bx = x - w / 2 + w * (i + 0.5) / n + rng.uniform(-10, 10)
        tongues.append((bx, rng.uniform(0, 6.28), rng.uniform(0.45, 1.25), rng.uniform(0.8, 1.4)))
    for layer, col in enumerate(FLAME[::-1]):
        sc = 1.0 - layer * 0.3
        for bx, ph, hk, wk in tongues:
            flick = 0.65 + 0.35 * abs(math.sin(t * (5 + hk * 3) + ph)) + 0.12 * math.sin(t * 17 + ph * 2)
            hh = h * sc * hk * flick
            ww = w / n * 1.5 * sc * wk
            sway = math.sin(t * 6 + ph) * ww * 0.4
            tongue = [(bx - ww / 2, y), (bx - ww * 0.42 + sway * 0.2, y - hh * 0.35), (bx - ww * 0.1 + sway * 0.7, y - hh * 0.75),
                      (bx + sway, y - hh), (bx + ww * 0.2 + sway * 0.6, y - hh * 0.62), (bx + ww * 0.45 + sway * 0.2, y - hh * 0.3), (bx + ww / 2, y)]
            L.blob(tongue, col, 2.0 if layer == 0 else 0, n=5)
    if embers:
        for i in range(10):
            ph = ((t * 0.7) + i / 10 + rng.random()) % 1.0
            ex = x + rng.uniform(-w / 2, w / 2) + math.sin(t * 3 + i) * 12
            ey = y - h * 0.6 - ph * h * 1.8
            r = 3 * (1 - ph) + 1
            L.ellipse((ex - r, ey - r, ex + r, ey + r), (255, 200, 90), 0, a=int(255 * (1 - ph)))


def explosion(L: Layer, x, y, t, t0, s=1.0, seed=3):
    dt = t - t0
    if dt < 0 or dt > 5.0:
        return
    rng = random.Random(seed)
    if dt < 0.5:                                                      # fireball
        k = dt / 0.5
        r = (40 + 160 * k) * s
        for col, f_ in zip(FLAME[::-1], (1.0, 0.75, 0.5)):
            pts = [(x + math.cos(a) * r * f_ * rng.uniform(0.8, 1.15), y - r * 0.4 + math.sin(a) * r * f_ * 0.8 * rng.uniform(0.8, 1.1))
                   for a in (i / 14 * math.tau for i in range(14))]
            L.blob(pts, col, 3 if f_ == 1.0 else 0, n=4, a=int(255 * (1 - k * 0.3)))
    if dt < 0.12:
        L.ellipse((x - 220 * s, y - 260 * s, x + 220 * s, y + 120 * s), (255, 250, 220), 0, a=int(180 * (1 - dt / 0.12)))
    k = min(1.0, dt / 4.5)                                            # smoke column
    puffs = []
    for i in range(9):
        a = i / 9 * math.tau
        rr = (60 + 140 * min(1, dt)) * s
        puffs.append((x + math.cos(a) * rr * 0.7 + 10 * dt, y - 80 * s - 40 * dt * s + math.sin(a) * rr * 0.35, (40 + 50 * min(1, dt)) * s))
    puffs.append((x + 12 * dt, y - (140 + 70 * dt) * s, (60 + 50 * min(1, dt)) * s))
    _puffs(L, puffs, col=(120, 112, 108), alpha=int(255 * (1 - k) ** 0.8))
    for i in range(12):                                               # debris: planks and sacks arcing out
        ang = rng.uniform(-2.8, -0.3)
        v = rng.uniform(300, 640) * s
        px = x + math.cos(ang) * v * dt
        py = y + math.sin(ang) * v * dt + 0.5 * 900 * dt * dt
        if py > y + 40 or dt > 1.6:
            continue
        sz = rng.uniform(6, 14) * s
        rot = dt * rng.uniform(4, 10)
        pts = [(px + math.cos(rot + q) * sz, py + math.sin(rot + q) * sz * 0.5) for q in (0, 1.6, 3.14, 4.7)]
        L.poly(pts, (130, 90, 56) if i % 3 else (220, 200, 160), 2)


def dust(L: Layer, x, y, t, t0, s=1.0, col=(214, 190, 150)):
    dt = t - t0
    if dt < 0 or dt > 1.2:
        return
    puffs = [(x + dx * (8 + 30 * dt) * s, y - (4 + 18 * dt) * s, (6 + 16 * dt) * s) for dx in (-1, -0.4, 0.4, 1)]
    _puffs(L, puffs, col=col, ink=1.6, alpha=int(230 * (1 - dt / 1.2)))


def splash(L: Layer, x, y, t, t0, s=1.0):
    dt = t - t0
    if dt < 0 or dt > 0.9:
        return
    k = dt / 0.9
    for i in range(9):
        a = math.pi + (i + 0.5) / 9 * math.pi
        r = (20 + 70 * k) * s
        px = x + math.cos(a) * r
        py = y + math.sin(a) * r * 0.9 + 140 * k * k * s
        rr = (7 * (1 - k) + 2) * s
        L.ellipse((px - rr, py - rr, px + rr, py + rr), (240, 250, 252), 1.6, a=int(255 * (1 - k)))
    L.d.arc([(x - 50 * s * (0.5 + k)) * S, (y - 8 * s) * S, (x + 50 * s * (0.5 + k)) * S, (y + 10 * s) * S], 0, 180,
            fill=(250, 252, 252, int(220 * (1 - k))), width=int(3 * S))
