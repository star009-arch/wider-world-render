"""Tiny Empires episode 1 (release order): "How the Egyptians Built the Great Pyramids" (~8 min). Engine: ep01.py.

  python scripts/cartoon/ep03.py preview | render i/k [outdir] | mix <shots dir> <out> [music]

Lines: projects/tiny-empires/ep03/lines.json (script_v1.md fact-checked; Y01-Y08 "a day at Giza" fact-checked separately).
Period standard: projects/tiny-empires/visual_bibles/01_egypt_old_kingdom_2600BC.md. Hosts wear Old Kingdom costume (hosts3 world
"egypt_ok"); historical cast from people.py ("egypt_ok:*"). Plates: release te-3d-egypt-v1 (Blender, Poly Haven textures).
QC anachronisms to avoid: horses, camels, wheels for hauling, pulleys/cranes, iron, coins, shaduf, palm/papyrus columns, obelisks, pylons.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

from PIL import ImageDraw  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep01 as K  # noqa: E402
import motions as M  # noqa: E402
import scene as SC  # noqa: E402
from scene import Shot, ease  # noqa: E402

M.set_world("egypt_ok")
K.EP = K.ROOT / "projects/tiny-empires/ep03"
K.VOICE = Path(os.environ.get("TE_VOICE", "D:/Temp/cartoon/ep03/voice"))
K.LINES = {ln["id"]: ln for ln in json.loads((K.EP / "lines.json").read_text(encoding="utf-8"))["lines"]}
K.DUR = json.loads((K.VOICE / "durations.json").read_text()) if (K.VOICE / "durations.json").exists() else {}
K.MAPS.update({"m_egypt": (24.5, 21.5, 37.5, 32.5)})
im, pj = K._relief(K.MAPS["m_egypt"], 0.22)
SC._BG["m_egypt"] = im.convert("RGBA")
K.PROJ["m_egypt"] = pj

P, at, label, caption, pin, route, timeline = K.P, K.at, K.label, K.caption, K.pin, K.route, K.timeline


def scene(*a, **kw):
    """Engine scene, plus a slow push-in on any shot that would otherwise hold a frozen frame."""
    sh = K.scene(*a, **kw)
    if kw.get("follow", True) is False and kw.get("cam") is None:
        sh.camkeys = [(0.0, 1.0, 0.5, 0.5), (sh.dur, 1.045, 0.5, 0.5)]
    return sh
G = 1030
GOLD, SAND, INK = (255, 214, 120), (226, 196, 140), (30, 24, 20, 255)


def E(key, x, ground=1000, s=1.5, **kw):
    """A period person from people.py (Old Kingdom Egypt)."""
    return M.Performer(f"egypt_ok:{key}", x=x, ground=ground, scale=s, **kw)


def crew(keys, x0, ground, dx, s, flip=False, walk=None, speed=1.0, acts=None):
    out = []
    for i, k in enumerate(keys):
        x = x0 + i * dx
        p = M.Performer(f"egypt_ok:{k}", x=x, ground=ground + (i % 2) * 14, scale=s, flip=flip,
                        walks=[(walk[0] + i * 0.08, x + walk[1])] if walk else [], speed=speed, acts=list(acts or []))
        p.shadow = s > 0.6
        out.append(p)
    return out


def T(d, x, y, text, size, a=1.0, anchor="lm", color=(255, 255, 255)):
    K.S_text(d, x, y, text, size, a=a, anchor=anchor, color=color)


# ------------------------------------------------------------------------------------------------ episode fx
def local_map(t0):
    """Schematic of the Memphis region in Khufu's time: river, floodplain, desert edges, sites (bible table 'Places')."""
    sites = [("Giza", "pyramid site", 0, 0.30, "w"), ("Saqqara", "Djoser's step pyramid", 0.6, 0.52, "w"),
             ("Dahshur", "Sneferu's pyramids", 1.2, 0.72, "w"), ("Memphis", "the capital", 1.8, 0.60, "f"),
             ("Tura", "white limestone", 2.4, 0.44, "e")]

    def f(t, d, frame):
        if t < t0:
            return
        a = ease((t - t0) / 0.6)
        x0, x1, y0, y1 = 260, 1560, 140, 960
        d.rectangle([x0, y0, x1, y1], fill=(206, 176, 120, int(255 * a)))                        # desert
        d.rectangle([x0 + 430, y0, x0 + 900, y1], fill=(92, 120, 64, int(255 * a)))              # floodplain
        pts = [(x0 + 690 + 40 * math.sin(i / 3), y0 + i * 41) for i in range(21)]
        d.line(pts, fill=(60, 110, 170, int(255 * a)), width=34)                                   # the Nile
        T(d, x0 + 30, y0 + 40, "WESTERN DESERT", 34, a, color=(90, 66, 40))
        T(d, x1 - 300, y0 + 40, "EASTERN DESERT", 34, a, color=(90, 66, 40))
        T(d, x0 + 760, y0 + 90, "NILE", 40, a, color=(220, 236, 255))
        T(d, x1, y0 - 30, "schematic, not to scale  ·  north is up", 30, a, anchor="rm", color=(220, 210, 190))
        for i, (nm, sub, dt, fy, side) in enumerate(sites):
            if t < t0 + 0.6 + dt:
                continue
            k = M.ease_out_back((t - t0 - 0.6 - dt) / 0.4)
            x = {"w": x0 + 330, "f": x0 + 560, "e": x0 + 1010}[side]
            y = y0 + fy * (y1 - y0)
            r = 16 * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 40, 44, 255), outline=INK, width=4)
            tx = x - 30 if side == "w" else x + 30
            T(d, tx, y - 18, nm, 46, color=GOLD, anchor="rm" if side == "w" else "lm")
            T(d, tx, y + 26, sub, 30, color=(240, 232, 214), anchor="rm" if side == "w" else "lm")
    return f


def _pyr(d, cx, base_y, w, h, kind, k, col=(236, 226, 200)):
    """Profiles: step (6 layers), bent, red (smooth, gentler), great."""
    h *= k
    if kind == "step":
        for i in range(6):
            ww = w * (1 - i * 0.14)
            y = base_y - (i + 1) * h / 6
            d.rectangle([cx - ww / 2, y, cx + ww / 2, y + h / 6], fill=col, outline=INK, width=3)
    elif kind == "bent":
        mid = base_y - h * 0.42
        hw = w / 2
        d.polygon([(cx - hw, base_y), (cx + hw, base_y), (cx + hw * 0.70, mid), (cx, base_y - h * 0.9), (cx - hw * 0.70, mid)],
                  fill=col, outline=INK)
    else:
        d.polygon([(cx - w / 2, base_y), (cx + w / 2, base_y), (cx, base_y - h)], fill=col, outline=INK)


def evolution(t0, which=("step", "bent", "red", "great"), step=None):
    names = {"step": ("Step Pyramid", "Djoser · Saqqara"), "bent": ("Bent Pyramid", "Sneferu · Dahshur"),
             "red": ("Red Pyramid", "Sneferu · Dahshur"), "great": ("Great Pyramid", "Khufu · Giza"),
             "khafre": ("Khafre", "~144 m · Giza"), "menkaure": ("Menkaure", "~65 m · Giza"), "khufu": ("Khufu", "~146 m · Giza")}
    dims = {"step": (300, 200), "bent": (300, 230), "red": (330, 230), "great": (340, 330),
            "khufu": (340, 330), "khafre": (318, 325), "menkaure": (150, 147)}
    cols = {"step": (230, 218, 190), "bent": (236, 226, 200), "red": (236, 226, 200), "great": (246, 240, 224),
            "khufu": (246, 240, 224), "khafre": (240, 232, 214), "menkaure": (214, 160, 130)}

    def f(t, d, frame):
        for i, kind in enumerate(which):
            ts = t0 + (step[i] if step else i * 1.0)
            if t < ts:
                continue
            k = ease((t - ts) / 0.6)
            cx = 260 + i * 330 if len(which) == 4 else 420 + i * 420
            w, h = dims[kind]
            _pyr(d, cx, 670, w * 0.85, h, kind, k, cols[kind])
            if k > 0.8:
                T(d, cx, 725, names[kind][0], 40, anchor="mm", color=GOLD)
                T(d, cx, 770, names[kind][1], 30, anchor="mm")
        d.line([(80, 670), (1440, 670)], fill=(120, 96, 60, 255), width=4)
    return f


def stats(t0, items, step=1.6, x=180, y=230):
    def f(t, d, frame):
        for i, (big, small) in enumerate(items):
            ts = t0 + i * step
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.45)
            yy = y + i * 200
            d.rounded_rectangle([x, yy, x + 980 * k, yy + 160], radius=26, fill=(30, 24, 20, 220), outline=(214, 172, 72, 255), width=4)
            if k > 0.9:
                T(d, x + 40, yy + 62, big, 72, color=GOLD)
                T(d, x + 40, yy + 126, small, 34, color=(236, 228, 210))
    return f


def compass(t0, cx=760, cy=520):
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 0.6)
        r = 240 * k
        d.polygon([(cx - r, cy + r * 0.55), (cx + r, cy + r * 0.55), (cx + r * 0.0, cy - r * 0.1)], fill=(236, 226, 200, 255), outline=INK)
        d.rectangle([cx - r, cy - r * 0.95, cx + r, cy + r * 0.95], outline=(255, 214, 120, 255), width=4)
        if k > 0.9:
            for lab, (dx, dy) in (("N", (0, -1.12)), ("S", (0, 1.12)), ("E", (1.1, 0)), ("W", (-1.1, 0))):
                T(d, cx + dx * 240, cy + dy * 240, lab, 56, anchor="mm", color=GOLD)
            T(d, cx, cy + 275, "sides aligned to the four directions", 38, anchor="mm")
    return f


def sledge(t0, water_t, travel=600.0, x_start=1400.0, y=820.0, rope_y=None):
    """Sledge on sand with a big block; a worker pours water ahead (Djehutihotep painting, later; Fall et al. 2014)."""
    def f(t, d, frame):
        if t < t0:
            return
        x = x_start - min(1.0, (t - t0) / 9.0) * travel
        d.rectangle([0, y + 10, 1920, y + 60], fill=(206, 176, 120, 255))
        d.rectangle([x - 240, y - 16, x + 240, y + 10], fill=(120, 82, 46, 255), outline=INK, width=4)
        d.polygon([(x - 260, y + 10), (x - 240, y - 16), (x - 290, y - 50)], fill=(120, 82, 46, 255), outline=INK)
        d.rectangle([x - 190, y - 230, x + 190, y - 16], fill=(214, 196, 160, 255), outline=INK, width=4)
        for i in range(3):
            ry = (y - 120) if rope_y is None else rope_y
            d.line([(x - 290, y - 40 - i * 4), (x - 700, ry + i * 14)], fill=(150, 120, 70, 255), width=5)
        if t >= water_t:
            for j in range(10):
                ph = ((t - water_t) * 2 + j / 10) % 1
                d.ellipse([x - 330 - ph * 40, y - 60 + ph * 60, x - 320 - ph * 40, y - 48 + ph * 60], fill=(110, 170, 230, 255))
            d.rectangle([x - 420, y + 10, x - 280, y + 24], fill=(150, 116, 76, 255))
    return f


def force_bars(t0):
    def f(t, d, frame):
        if t < t0:
            return
        for i, (lab, v, col) in enumerate((("dry sand", 1.0, (200, 120, 60)), ("wet sand", 0.5, (90, 150, 210)))):
            ts = t0 + i * 0.9
            if t < ts:
                continue
            k = ease((t - ts) / 0.6)
            y = 320 + i * 170
            T(d, 160, y + 50, lab, 46, color=GOLD)
            d.rectangle([480, y, 480 + 760 * v * k, y + 100], fill=col + (255,), outline=INK, width=4)
        if t > t0 + 2.2:
            T(d, 160, 700, "pulling force needed (roughly)", 38)
    return f


def ramps(t0):
    def f(t, d, frame):
        for i, (nm, kind) in enumerate((("straight", 0), ("zig-zag", 1), ("internal spiral", 2))):
            ts = t0 + i * 1.2
            if t < ts:
                continue
            k = ease((t - ts) / 0.6)
            cx, by, w, h = 420 + i * 430, 700, 320, 270
            d.polygon([(cx - w / 2, by), (cx + w / 2, by), (cx, by - h * k)], fill=(236, 226, 200, 255), outline=INK)
            c = (200, 120, 60, 255)
            if kind == 0:
                d.polygon([(cx - w / 2 - 160, by), (cx - w / 2 + 20, by), (cx - 30, by - h * 0.8 * k)], fill=c, outline=INK)
            elif kind == 1:
                for j in range(4):
                    y0, y1 = by - j * h * 0.2 * k, by - (j + 1) * h * 0.2 * k
                    xl, xr = cx - w / 2 * (1 - j * 0.2), cx + w / 2 * (1 - (j + 1) * 0.2)
                    if j % 2:
                        xl, xr = xr, xl
                    d.line([(xl, y0), (xr, y1)], fill=c, width=14)
            else:
                for j in range(4):
                    yy = by - (j + 0.5) * h * 0.2 * k
                    ww = w / 2 * (1 - (j + 0.5) * 0.2) * 0.75
                    d.line([(cx - ww, yy), (cx + ww, yy - 18)], fill=c, width=8)
                d.line([(cx - w / 2 * 0.75, by - 10), (cx - w / 2 * 0.62, by - h * 0.8 * k)], fill=(120, 96, 60, 255), width=3)
            if k > 0.8:
                T(d, cx, 770, nm, 40, anchor="mm", color=GOLD)
        if t > t0 + 3.6:
            T(d, 960, 815, "still debated: maybe a mix of several", 38, anchor="mm")
    return f


def crew_marks(t0):
    """Red-paint gang names on a hidden block (relieving chambers above the King's Chamber)."""
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 0.6)
        d.rectangle([260, 260, 1260, 760], fill=(222, 204, 168, 255), outline=INK, width=6)
        for i in range(1, 4):
            d.line([(260, 260 + i * 125), (1260, 260 + i * 125)], fill=(190, 170, 130, 255), width=3)
        if k > 0.3:
            T(d, 760, 470, "\"Friends of Khufu\"", int(84 * min(1, k)), anchor="mm", color=(170, 40, 30))
            T(d, 760, 600, "a crew name in red paint", 40, anchor="mm", color=(90, 60, 40))
        if t > t0 + 1.2:
            T(d, 760, 805, "found on blocks sealed inside the pyramid", 38, anchor="mm")
    return f


def bread_pots(t0):
    def f(t, d, frame):
        if t < t0:
            return
        for i in range(5):
            ts = t0 + i * 0.25
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.4)
            cx, by = 330 + i * 230, 760
            w, h = 150 * k, 190 * k
            d.polygon([(cx - w / 2, by), (cx + w / 2, by), (cx + w * 0.22, by - h), (cx - w * 0.22, by - h)], fill=(176, 96, 56, 255), outline=INK)
            d.ellipse([cx - w * 0.24, by - h - 12 * k, cx + w * 0.24, by - h + 12 * k], fill=(140, 70, 40, 255), outline=INK)
            for j in range(4):
                fx = cx - 50 + j * 30
                d.polygon([(fx - 10, by + 30), (fx + 10, by + 30), (fx + 14 * math.sin(t * 12 + j), by + 6)], fill=(255, 150, 40, 200))
        if t > t0 + 1.6:
            T(d, 760, 800, "bell-shaped bread pots (bedja)", 44, anchor="mm", color=GOLD)
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


def giza_plan(t0):
    """Plan of Giza in Khufu's reign (bible A1): pyramid, queens' pyramids east, mastaba rows W and E, boat pits, causeway, harbour."""
    def f(t, d, frame):
        if t < t0:
            return
        a = ease((t - t0) / 0.5)
        d.rectangle([140, 120, 1480, 960], fill=(206, 176, 120, int(255 * a)))
        d.rectangle([1250, 120, 1480, 960], fill=(92, 120, 64, int(255 * a)))
        steps = [
            (0.3, lambda: (d.rectangle([620, 380, 900, 660], fill=(246, 240, 224, 255), outline=INK, width=4),
                           d.line([(620, 380), (900, 660)], fill=(200, 190, 170, 255), width=2), d.line([(900, 380), (620, 660)], fill=(200, 190, 170, 255), width=2),
                           T(d, 760, 520, "Khufu", 44, anchor="mm", color=(60, 40, 20)))),
            (1.2, lambda: [d.rectangle([180 + c * 64, 260 + r * 70, 228 + c * 64, 300 + r * 70], fill=(226, 214, 186, 255), outline=INK, width=2)
                           for r in range(8) for c in range(5)] + [T(d, 340, 220, "officials' tombs", 32, anchor="mm", color=(60, 40, 20))]),
            (1.6, lambda: [d.rectangle([1010 + c * 56, 150 + r * 50, 1050 + c * 56, 182 + r * 50], fill=(226, 214, 186, 255), outline=INK, width=2)
                           for r in range(4) for c in range(3)] + [T(d, 1090, 370, "royal family tombs", 30, anchor="mm", color=(60, 40, 20))]),
            (2.6, lambda: [(d.rectangle([930, 400 + i * 62, 975, 445 + i * 62], fill=(246, 240, 224, 255), outline=INK, width=3)) for i in range(3)]
                          + [T(d, 1110, 470, "queens' pyramids", 32, anchor="mm", color=(60, 40, 20))]),
            (3.6, lambda: [d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=12, fill=(120, 82, 46, 255), outline=INK, width=2)
                           for x0, y0, w, h in ((640, 680, 110, 22), (780, 680, 110, 22))]
                          + [T(d, 700, 740, "boat pits", 30, anchor="mm", color=(60, 40, 20))]),
            (4.6, lambda: (d.line([(900, 640), (1260, 760)], fill=(160, 130, 90, 255), width=14),
                           d.rectangle([1250, 730, 1300, 790], fill=(120, 110, 100, 255), outline=INK, width=3),
                           d.ellipse([1290, 680, 1450, 840], fill=(60, 110, 170, 255), outline=INK, width=3),
                           T(d, 1370, 650, "harbour (probable)", 30, anchor="mm", color=(240, 236, 220)))),
        ]
        for dt, draw in steps:
            if t >= t0 + dt:
                draw()
        T(d, 1480, 100, "plan, not to scale · north is up", 28, anchor="rm", color=(220, 210, 190))
    return f


def khufu_ship(t0):
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 0.8)
        cx, y = 760, 560
        w = 1200 * k
        d.polygon([(cx - w / 2, y - 90), (cx - w / 2 + 120 * k, y + 40), (cx + w / 2 - 120 * k, y + 40), (cx + w / 2, y - 110)], fill=(150, 104, 60, 255), outline=INK)
        d.line([(cx - w / 2 + 40, y - 60), (cx + w / 2 - 40, y - 70)], fill=(110, 74, 40, 255), width=6)
        if k > 0.9:
            d.rectangle([cx - 140, y - 190, cx + 160, y - 70], fill=(170, 122, 72, 255), outline=INK, width=4)
            for i in range(-4, 5):
                d.line([(cx + i * 100, y - 40), (cx + i * 100 - 40, y + 120)], fill=(110, 74, 40, 255), width=6)
            d.line([(cx - 600, y + 200), (cx + 600, y + 200)], fill=(255, 214, 120, 255), width=4)
            T(d, cx, y + 250, "about 43 metres", 52, anchor="mm", color=GOLD)
            T(d, cx, 180, "KHUFU'S SHIP · found 1954 · 1,224 pieces", 52, anchor="mm", color=GOLD)
    return f


def no_list(t0, xs_t, yes_t):
    """'No steel tools. No cranes. No engines.' crossed out one by one, then 'copper · rope · muscle'."""
    words = ["STEEL TOOLS", "CRANES", "ENGINES"]

    def f(t, d, frame):
        for i, w in enumerate(words):
            ts = t0 + xs_t[i]
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.3)
            x, y = 330 + i * 470, 250
            d.rounded_rectangle([x - 200 * k, y - 60 * k, x + 200 * k, y + 60 * k], radius=22, fill=(30, 24, 20, 230), outline=(230, 80, 60, 255), width=5)
            if k > 0.8:
                T(d, x, y, w, 50, anchor="mm")
                if t > ts + 0.35:
                    d.line([(x - 180, y + 40), (x + 180, y - 40)], fill=(230, 50, 40, 255), width=12)
        if t >= t0 + yes_t:
            k = M.ease_out_back((t - t0 - yes_t) / 0.35)
            d.rounded_rectangle([960 - 520 * k, 400 - 70 * k, 960 + 520 * k, 400 + 70 * k], radius=26, fill=(30, 24, 20, 230),
                                outline=(214, 172, 72, 255), width=5)
            if k > 0.8:
                T(d, 960, 400, "COPPER  ·  ROPE  ·  MUSCLE", 64, anchor="mm", color=GOLD)
    return f


def year_counter(t0, t1):
    """Years tick from c. 2560 BC to the AD 1300s while the pyramid stays the tallest."""
    def f(t, d, frame):
        if t < t0:
            return
        k = min(1.0, (t - t0) / max(0.1, t1 - t0))
        y = -2560 + int(ease(k) * 3860)
        txt = f"{-y} BC" if y < 0 else f"AD {max(1, y)}"
        d.rounded_rectangle([90, 70, 900, 260], radius=26, fill=(30, 24, 20, 220), outline=(214, 172, 72, 255), width=4)
        T(d, 130, 140, "STILL THE TALLEST BUILDING:", 44)
        T(d, 130, 214, txt, 72, color=GOLD)
    return f


def budget(t0):
    def f(t, d, frame):
        if t < t0:
            return
        k = M.ease_out_back((t - t0) / 0.3)
        x, y = 1180, 360
        d.polygon([(x - 150 * k, y - 190 * k), (x + 150 * k, y - 190 * k), (x + 150 * k, y + 170 * k), (x - 150 * k, y + 190 * k)],
                  fill=(244, 238, 224, 255), outline=INK)
        if k > 0.8:
            T(d, x, y - 140, "BUDGET", 44, anchor="mm", color=(60, 40, 20))
            for i in range(4):
                d.line([(x - 110, y - 70 + i * 50), (x + 110, y - 70 + i * 50)], fill=(170, 160, 140, 255), width=4)
            T(d, x, y + 120, "???", 64, anchor="mm", color=(200, 40, 40))
    return f


def title_sting(t0):
    """Channel logo punches in, then the episode title."""
    def f(t, d, frame):
        if t < t0:
            return
        k = M.ease_out_back((t - t0) / 0.45)
        d.rectangle([0, 0, 1920, 1080], fill=(12, 10, 16, int(150 * min(1, (t - t0) / 0.3))))
        sz = int(150 * k)
        if sz > 10:
            T(d, 960, 380, "TINY EMPIRES", sz, anchor="mm", color=GOLD)
        if t > t0 + 0.6:
            a = ease((t - t0 - 0.6) / 0.4)
            T(d, 960, 540, "How the Egyptians Built the Great Pyramids", 64, a=a, anchor="mm")
    return f


def next_time(t0):
    """End tease: the next episode (no weekday: release days can change)."""
    def f(t, d, frame):
        if t < t0:
            return
        k = M.ease_out_back((t - t0) / 0.4)
        d.rounded_rectangle([960 - 560 * k, 70, 960 + 560 * k, 250], radius=28, fill=(30, 24, 20, 225), outline=(214, 172, 72, 255), width=5)
        if k > 0.8:
            T(d, 960, 125, "NEXT ON TINY EMPIRES", 50, anchor="mm", color=(255, 236, 190))
            T(d, 960, 200, "THE MONGOLS", 80, anchor="mm", color=GOLD)
    return f


def tomb_goods(t0):
    """Hetepheres-style burial goods (bible E1): bed, carrying chair, headrest, jars, linen chest."""
    items = [("bed", "bed"), ("chair", "carrying chair"), ("rest", "headrest"), ("jar", "food & oil jars"), ("box", "linen chest")]

    def icon(d, kind, x, y, k):
        g = (214, 172, 72, 255)
        if kind == "bed":
            d.rectangle([x - 90 * k, y - 20 * k, x + 90 * k, y], fill=g, outline=INK, width=4)
            for dx in (-80, 70):
                d.rectangle([x + dx * k, y, x + (dx + 12) * k, y + 50 * k], fill=g, outline=INK, width=3)
        elif kind == "chair":
            d.rectangle([x - 50 * k, y - 70 * k, x + 50 * k, y + 10 * k], fill=g, outline=INK, width=4)
            d.line([(x - 100 * k, y + 10 * k), (x + 100 * k, y + 10 * k)], fill=(120, 82, 46, 255), width=10)
        elif kind == "rest":
            d.arc([x - 60 * k, y - 80 * k, x + 60 * k, y - 10 * k], 0, 180, fill=(236, 226, 200, 255), width=14)
            d.rectangle([x - 12 * k, y - 20 * k, x + 12 * k, y + 40 * k], fill=(236, 226, 200, 255), outline=INK, width=3)
            d.rectangle([x - 50 * k, y + 40 * k, x + 50 * k, y + 52 * k], fill=(236, 226, 200, 255), outline=INK, width=3)
        elif kind == "jar":
            for dx in (-40, 40):
                d.ellipse([x + dx * k - 32 * k, y - 60 * k, x + dx * k + 32 * k, y + 40 * k], fill=(176, 96, 56, 255), outline=INK, width=4)
        else:
            d.rectangle([x - 70 * k, y - 50 * k, x + 70 * k, y + 40 * k], fill=(150, 104, 60, 255), outline=INK, width=4)
            d.line([(x - 70 * k, y - 20 * k), (x + 70 * k, y - 20 * k)], fill=INK, width=3)

    def f(t, d, frame):
        for i, (kind, name) in enumerate(items):
            ts = t0 + i * 0.9
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.35)
            x, y = 220 + i * 290, 520
            d.rounded_rectangle([x - 130, y - 140, x + 130, y + 140], radius=22, fill=(30, 24, 20, 200), outline=(214, 172, 72, 255), width=3)
            icon(d, kind, x, y - 10, k)
            if k > 0.8:
                T(d, x, y + 110, name, 30, anchor="mm", color=(255, 236, 190))
    return f


def sun_rays(t0):
    def f(t, d, frame):
        if t < t0:
            return
        a = ease((t - t0) / 1.0)
        for i in range(9):
            x0 = 300 + i * 160
            d.polygon([(860, -60), (900, -60), (x0 + 40, 700), (x0 - 40, 700)], fill=(255, 236, 160, int(46 * a)))
        d.ellipse([800, -140, 960, 20], fill=(255, 230, 140, int(220 * a)))
    return f


def icons_bbm(t0):
    """Wages in food: bread, beer, meat."""
    def f(t, d, frame):
        for i, (nm, col) in enumerate((("BREAD", (214, 160, 90)), ("BEER", (200, 150, 60)), ("MEAT", (190, 80, 70)))):
            ts = t0 + i * 0.6
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.35)
            x, y = 430 + i * 330, 260
            d.ellipse([x - 110 * k, y - 110 * k, x + 110 * k, y + 110 * k], fill=col + (255,), outline=INK, width=5)
            if k > 0.8:
                T(d, x, y, nm, 46, anchor="mm")
    return f


def hatnub(t0):
    """The 2018 Hatnub find: a steep ramp flanked by two staircases with post holes for hauling."""
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 1.0)
        bx, by, top = 300, 820, 300
        d.polygon([(bx, by), (bx + 1000, by), (bx + 1000, top)], fill=(206, 176, 120, 255), outline=INK)
        x1 = bx + 120 + 880 * k
        y1 = by - (by - top) * 0.88 * k
        for off, col, w in ((-26, (150, 120, 80), 14), (0, (200, 120, 60), 26), (26, (150, 120, 80), 14)):
            d.line([(bx + 120, by + off * 0.3), (x1, y1 + off * 0.3)], fill=col + (255,), width=w)
        if k > 0.6:
            for i in range(1, 9):
                px = bx + 120 + i * 880 / 9
                py = by - (by - top) * 0.88 * i / 9 - 34
                d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=INK)
            T(d, 760, 200, "steep ramp + stairs + post holes for hauling", 38, anchor="mm", color=(255, 236, 190))
    return f


# ------------------------------------------------------------------------------------------------ the episode
def shots():
    K.CUES.clear()
    out = []
    # HOOK (the first ~30 s decide retention): voice within 0.2 s over the most striking image, a new picture on every line,
    # the mystery ("no cranes... so how?") before the title sting.
    H0 = 0.2
    L = ["G01"]
    w_ = scene("s00_wow", "plate:giza_later",
               [P("penny", 1560, G, 1.9, flip=True, faces=[(0, {"brows": -0.3, "mouth": "smirk"})])],
               L, lead=H0, follow=False, cam=[(0.0, 1.0, 0.5, 0.5), (4.2, 1.1, 0.47, 0.48)],
               fx=[shine(0.0), label("GIZA · ABOUT 4,600 YEARS AGO", 760, 110, 0.0, 60, GOLD)])
    rest = w_.dur - 4.2
    w_.dur = 4.2                                                                 # "...people in Egypt" | cut | "stacked millions of blocks"
    out.append(w_)
    out.append(Shot("s00_blocks", rest, "plate:giza_build",
                    actors=crew(["worker", "worker2", "worker", "worker2", "worker"], 200, 1040, 150, 1.3, walk=(0.0, 260), speed=0.45),
                    fx=[label("MILLIONS OF STONE BLOCKS", 960, 110, 0.4, 60, GOLD)], camkeys=[(0.0, 1.3, 0.38, 0.6), (rest, 1.05, 0.5, 0.52)]))
    L = ["G02"]
    out.append(scene("s00_no", "plate:giza_build",
                     [*crew(["worker", "worker2", "worker", "worker2"], 120, 1040, 140, 1.25, walk=(0.0, 180), speed=0.4),
                      P("atlas", 1620, G, 1.8, flip=True, faces=[(0, {"brows": 0.6, "mouth": "o"})])],
                     L, lead=H0, follow=False, cam=[(0.0, 1.08, 0.5, 0.5), (at(L, 1, H0) + 0.6, 1.0, 0.5, 0.5)],
                     fx=[no_list(H0, [0.0, 1.2, 2.2], 3.2)]))
    L = ["G03", "G04"]
    out.append(scene("s00_tallest", "plate:giza_later",
                     [P("penny", 1300, G, 1.8, flip=True),
                      P("zed", 2150, G, 1.7, flip=True, walks=[(at(L, 1, H0) - 3.0, 1640)], speed=1.8, faces=[(0, {"mouth": "grin"})],
                        acts=[(at(L, 1, H0), "hold_up", None)])],
                     L, lead=H0, follow=False, cam=[(0.0, 1.0, 0.5, 0.5), (at(L, 2, H0) + 0.6, 1.1, 0.55, 0.5)],
                     fx=[year_counter(H0 + 0.3, at(L, 1, H0) - 0.3), budget(at(L, 1, H0) + 0.2)]))
    L = ["G05"]
    out.append(scene("s01_title", "plate:giza_build",
                     [P(k, 420 + i * 270, G, 1.5, faces=[(0, {"mouth": "grin" if k != "pike" else "o"})], acts=[(0.4 + i * 0.1, "wave", 0.6)])
                      for i, k in enumerate(["atlas", "quill", "penny", "zed", "pike"])],
                     L, lead=H0, follow=False, extra=0.6, fx=[title_sting(H0 + 3.0)]))
    L = ["G06"]
    out.append(scene("s02_nile_map", "m_egypt", [P("penny", 1720, G, 1.5, flip=True)], L,
                     fx=[route("m_egypt", [(32.9, 24.1), (32.7, 25.7), (31.9, 26.6), (30.8, 28.1), (31.25, 29.85), (31.0, 31.0)], 0.6, 4.6,
                               color=(110, 170, 240), ship=False),
                         pin("m_egypt", 31.25, 29.85, "Memphis, the capital", 2.2), pin("m_egypt", 32.9, 24.09, "Aswan · First Cataract", 3.2),
                         label("ANCIENT EGYPT · NO MODERN BORDERS", 520, 100, 0.4, 50, GOLD)], follow=False))
    L = ["G07"]
    out.append(scene("s02_flood", "plate:fields",
                     [P("atlas", 1600, G, 1.7, flip=True), *crew(["worker", "woman", "worker2"], 180, 980, 220, 1.1, acts=[(2.0, "nod", None)])],
                     L, fx=[caption("the yearly flood: black soil, big harvests", 1.2)]))
    L = ["G08"]
    out.append(scene("s02_pharaoh", "plate:palace",
                     [E("khufu", 760, 1000, 1.7, faces=[(0, {"mouth": "smirk"})], acts=[(1.0, "present", None)]),
                      E("official", 300, 1000, 1.5, acts=[(1.6, "nod", None)]), P("penny", 1700, G, 1.6, flip=True)],
                     L, fx=[label("THE PHARAOH", 760, 120, 0.6, 64, GOLD)]))
    L = ["G09"]
    out.append(scene("s02_oldkingdom", "card", [P("quill", 1700, G, 1.6, flip=True)], L,
                     fx=[timeline([("c. 2650 BC", "Djoser's|step pyramid"), ("c. 2600 BC", "Sneferu's|pyramids"),
                                   ("c. 2600–2550", "Khufu's|Great Pyramid")], 0.5, 1.8),
                         label("THE OLD KINGDOM", 760, 140, 0.3, 70, GOLD)], follow=False))
    L = ["G10"]
    out.append(scene("s03_why", "plate:saqqara2", [P("penny", 1600, G, 1.7, flip=True)], L, follow=False,
                     fx=[label("WHY BUILD A MOUNTAIN FOR A TOMB?", 760, 110, 0.3, 58, GOLD), caption("death = a journey", 2.6)]))
    L = ["G11"]
    out.append(scene("s03_goods", "plate:palace", [P("quill", 1720, G, 1.6, flip=True)], L, follow=False,
                     fx=[tomb_goods(1.2), label("WHAT A KING TOOK WITH HIM", 760, 110, 0.4, 56, GOLD)]))
    L = ["G12", "G13"]
    out.append(scene("s03_sun", "plate:giza_later",
                     [P("zed", 1450, G, 1.6, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(0.4, "point", None)]), P("penny", 1760, G, 1.6, flip=True)],
                     L, fx=[sun_rays(at(L, 1) + 0.6), caption("the shape may echo the sun's rays", at(L, 1) + 1.6)]))
    L = ["G14"]
    out.append(scene("s04_practice", "card", [P("penny", 1700, G, 1.6, flip=True)], L, fx=[evolution(0.4, step=(0.2, 1.0, 1.8, 2.6))],
                     follow=False))
    L = ["G15"]
    out.append(scene("s04_djoser", "plate:saqqara2",
                     [E("djoser", 520, 1000, 1.6, acts=[(1.0, "present", None)]), E("imhotep", 860, 1000, 1.5, acts=[(at(L, 0) + 4.0, "hold_up", None)]),
                      P("atlas", 1650, G, 1.7, flip=True)],
                     L, fx=[label("SAQQARA · c. 2650 BC", 960, 100, 0.4, 62, GOLD), label("IMHOTEP, the architect", 860, 320, 4.0, 46, (255, 236, 190))]))
    L = ["G16"]
    out.append(scene("s04_sneferu", "card", [E("sneferu", 1250, 1000, 1.6, flip=True, acts=[(1.0, "present", None)]), P("penny", 1720, G, 1.6, flip=True)],
                     L, fx=[evolution(0.4, which=("bent",), step=(3.0,)), label("KING SNEFERU · DAHSHUR", 760, 120, 0.4, 62, GOLD)], follow=False))
    L = ["G17", "G18"]
    out.append(scene("s04_red", "card",
                     [P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "o"})], acts=[(0.3, "double_take", None)]),
                      P("quill", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[evolution(0.0, which=("bent", "red"), step=(0.0, at(L, 1) + 3.0)), label("DAHSHUR", 760, 120, 0.0, 66, GOLD)],
                     follow=False))
    L = ["G19"]
    out.append(scene("s05_khufu", "plate:giza_build",
                     [E("khufu", 700, 1000, 1.7, faces=[(0, {"mouth": "grin"})], acts=[(2.0, "point", None)]),
                      E("official", 380, 1000, 1.5), P("penny", 1700, G, 1.6, flip=True)],
                     L, fx=[label("KHUFU", 700, 300, 0.8, 70, GOLD)], follow=False))
    L = ["G20"]
    out.append(scene("s05_region", "card", [P("penny", 1740, G, 1.5, flip=True)], L, fx=[local_map(0.2)], follow=False))
    L = ["G21"]
    out.append(scene("s05_numbers", "card", [P("zed", 1720, G, 1.6, flip=True)], L,
                     fx=[stats(0.6, [("~2,300,000", "blocks (most estimates)"), ("~2.5 tonnes", "average weight per block"),
                                     ("~146 m", "original height")], step=3.4)], follow=False))
    L = ["G22"]
    out.append(scene("s05_level", "card", [P("atlas", 1700, G, 1.7, flip=True)], L,
                     fx=[compass(2.0), label("BASE: MORE THAN 5 HECTARES", 760, 110, 0.4, 56, GOLD)], follow=False))
    L = ["G23", "G24"]
    out.append(scene("s05_years", "plate:giza_build",
                     [P("quill", 1150, G, 1.6), P("pike", 1500, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})],
                                                      acts=[(at(L, 1) + 1.5, "facepalm", None)])],
                     L, fx=[caption("about 20 years of work", 1.0, at(L, 1))]))
    L = ["G25"]
    out.append(scene("s06_myth", "card", [P("penny", 1700, G, 1.6, flip=True)], L,
                     fx=[label("THE MYTH: SLAVES UNDER WHIPS", 760, 380, 0.5, 60, (230, 120, 100)),
                         label("THE EVIDENCE SAYS OTHERWISE", 760, 560, 3.2, 60, GOLD)], follow=False))
    L = ["G26", "G27"]
    out.append(scene("s06_town", "plate:workers_street",
                     [*crew(["baker", "worker", "woman", "worker2"], 160, 990, 200, 1.1), P("atlas", 1350, G, 1.7, flip=True),
                      P("quill", 1700, G, 1.6, flip=True)],
                     L, fx=[label("THE WORKERS' TOWN · GIZA", 760, 100, 0.4, 60, GOLD)]))
    L = ["G28"]
    out.append(scene("s06_crews", "plate:giza_build",
                     [*crew(["worker", "worker2", "worker", "worker2", "worker"], 120, 1030, 150, 1.15, walk=(0.5, 200), speed=0.4),
                      P("penny", 1700, G, 1.6, flip=True)],
                     L, follow=False, fx=[icons_bbm(1.2), caption("rotated in and out of the site", 5.0)]))
    L = ["G29", "G30"]
    out.append(scene("s06_names", "plate:workers_street",
                     [*crew(["worker", "worker2", "worker"], 200, 1000, 170, 1.2, acts=[(at(L, 1), "cheer", None)]),
                      P("zed", 1400, G, 1.6, flip=True), P("pike", 1720, G, 1.8, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(at(L, 1) + 0.4, "shrug", None)])],
                     L, fx=[label("\"FRIENDS OF KHUFU\"", 600, 330, 2.0, 72, (230, 90, 70))]))
    L = ["Y01", "Y02"]
    out.append(scene("s06b_morning", "plate:workers_street",
                     [*crew(["worker", "worker2", "baker"], 200, 990, 230, 1.15, walk=(1.0, 300), speed=0.8), P("penny", 1300, G, 1.6, flip=True),
                      P("atlas", 1650, G, 1.7, flip=True)],
                     L, fx=[label("A DAY AT GIZA", 760, 100, 0.4, 66, GOLD)]))
    L = ["Y03"]
    out.append(scene("s06b_bakery", "plate:house_interior", [E("baker", 600, 1000, 1.5, acts=[(1.0, "present", None)]), P("zed", 1700, G, 1.6, flip=True)],
                     L, fx=[bread_pots(1.0)], follow=False))
    L = ["Y04"]
    out.append(scene("s06b_names", "card", [P("quill", 1720, G, 1.6, flip=True)], L, fx=[crew_marks(0.6)], follow=False))
    L = ["Y05", "Y06"]
    out.append(scene("s06b_care", "plate:workers_street",
                     [E("worker", 600, 1000, 1.4, faces=[(0, {"mouth": "smile"})]), E("scribe", 820, 1000, 1.4),
                      P("pike", 1400, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]), P("penny", 1720, G, 1.6, flip=True)],
                     L, fx=[caption("healed fractures: someone set the bones", at(L, 1) + 3.0)]))
    L = ["Y07", "Y08"]
    out.append(scene("s06b_cemetery", "plate:giza_later",
                     [P("atlas", 1300, G, 1.7, flip=True), P("pike", 1650, G, 1.8, flip=True, acts=[(at(L, 1) + 1.0, "celebrate", 0.4)])],
                     L, fx=[caption("the workers' cemetery, south of the pyramids", 0.6, at(L, 1))]))
    L = ["G31"]
    out.append(scene("s07_quarry", "plate:quarry",
                     [*crew(["worker", "worker2", "worker"], 200, 1000, 200, 1.1), P("penny", 1700, G, 1.6, flip=True)],
                     L, fx=[label("LOCAL LIMESTONE · QUARRIED AT GIZA", 760, 100, 0.4, 54, GOLD)], follow=False))
    L = ["G32"]
    out.append(scene("s07_tura", "plate:tura", [*crew(["worker2", "worker"], 300, 1000, 220, 1.1), P("atlas", 1700, G, 1.7, flip=True)], L,
                     fx=[label("TURA · FINE WHITE LIMESTONE", 760, 100, 0.2, 60, GOLD),
                         caption("granite beams from Aswan, ~850 km upriver", at(L, 0) + 4.5)], follow=False))
    L = ["G33"]
    out.append(scene("s07_papyri", "m_egypt", [P("quill", 1720, G, 1.5, flip=True)], L,
                     fx=[pin("m_egypt", 32.6, 28.9, "Wadi al-Jarf · Red Sea harbour", 1.0), pin("m_egypt", 31.13, 29.98, "Giza", 2.4, dx=-140),
                         caption("2013: the oldest inscribed papyri ever found", 3.0, y=110)], follow=False))
    L = ["G34"]
    out.append(scene("s07_merer", "plate:harbour",
                     [E("merer", 640, 1000, 1.6, acts=[(1.0, "hold_up", None)]), *crew(["boatman", "worker"], 220, 1000, 200, 1.2),
                      P("penny", 1700, G, 1.6, flip=True)],
                     L, fx=[label("THE DIARY OF MERER", 760, 100, 0.4, 62, GOLD), caption("Tura to Giza, by boat, on canals and the flood", 4.0)]))
    L = ["G35"]
    out.append(scene("s07_diary", "plate:tura", [P("zed", 1500, G, 1.8, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(0.3, "hold_up", None)])], L,
                     follow=False, cam=[(0.0, 1.2, 0.7, 0.55), (5.0, 1.05, 0.6, 0.5)], fx=[caption("c. 2560 BC: a delivery log", 0.5)]))
    L = ["G36"]
    out.append(scene("s08_problem", "plate:giza_build", [P("penny", 1700, G, 1.6, flip=True)], L, follow=False))
    L = ["G37"]
    out.append(scene("s08_sledge", "card",
                     [*crew(["worker", "worker2", "worker", "worker2"], 330, 890, 70, 1.0, flip=True, walk=(0.3, -120), speed=0.12),
                      E("worker2", 760, 890, 1.0, flip=True), P("atlas", 1720, 890, 1.6, flip=True)],
                     L, fx=[sledge(0.3, 1.2, travel=120, x_start=1100, y=M.stage(890)[0] - 10, rope_y=M.stage(890)[0] - 120), label("HAULING ON A WOODEN SLEDGE", 760, 110, 0.3, 58, GOLD),
                            caption("a later tomb painting: water poured ahead of a sledge", 4.5)], follow=False))
    L = ["G38"]
    out.append(scene("s08_wet", "card", [P("zed", 1720, G, 1.6, flip=True)], L, fx=[force_bars(0.5)], follow=False))
    L = ["G39"]
    out.append(scene("s08_ramps", "card", [P("penny", 1720, G, 1.6, flip=True)], L, fx=[ramps(1.5)], follow=False))
    L = ["G40"]
    out.append(scene("s08_hatnub", "card", [P("quill", 1720, G, 1.6, flip=True)], L,
                     fx=[hatnub(0.8), label("HATNUB ALABASTER QUARRY · FOUND 2018", 760, 100, 0.3, 54, GOLD)], follow=False))
    L = ["G41", "G42"]
    out.append(scene("s08_tired", "plate:giza_build",
                     [*crew(["worker", "worker2", "worker"], 200, 1030, 170, 1.15, acts=[(at(L, 1) + 0.8, "sit", None)]),
                      P("pike", 1400, G, 1.8, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(0.4, "shrug", None)]), P("penny", 1720, G, 1.6, flip=True)],
                     L))
    L = ["G43"]
    out.append(scene("s09_shine", "plate:giza_later", [P("penny", 1720, G, 1.6, flip=True)], L,
                     fx=[shine(0.5), caption("polished white Tura limestone", 1.0)], follow=False))
    L = ["Z01", "Z02"]
    out.append(scene("s09b_plan", "card", [P("penny", 1810, G, 1.3, flip=True), P("atlas", 1640, G + 10, 1.3, flip=True)], L,
                     fx=[giza_plan(at(L, 1) - 0.6), label("GIZA IN KHUFU'S TIME", 760, 70, 0.3, 56, GOLD)], follow=False))
    L = ["Z03"]
    out.append(scene("s09b_ship", "card", [P("quill", 1720, G, 1.5, flip=True)], L, fx=[khufu_ship(0.8)], follow=False))
    L = ["Z04", "Z05"]
    out.append(scene("s09b_harbour", "plate:harbour",
                     [*crew(["boatman", "worker", "worker2"], 200, 1000, 210, 1.1), P("zed", 1400, G, 1.6, flip=True),
                      P("pike", 1720, G, 1.8, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(at(L, 1) + 0.5, "celebrate", 0.4)])],
                     L, fx=[caption("a probable harbour basin at the foot of the plateau", 1.0, at(L, 1))]))
    L = ["G44"]
    out.append(scene("s09_family", "card", [P("atlas", 1720, G, 1.7, flip=True)], L,
                     fx=[label("GIZA: THREE KINGS", 760, 120, 0.3, 64, GOLD), evolution(0.6, which=("khufu", "khafre", "menkaure"), step=(0.3, 1.8, 3.6))],
                     follow=False))
    L = ["G45"]
    out.append(scene("s09_wonder", "plate:giza_later", [P("quill", 1700, G, 1.6, flip=True)], L, follow=False,
                     cam=[(0.0, 1.22, 0.55, 0.5), (at(L, 1) + 0.6, 1.0, 0.5, 0.5)],
                     fx=[shine(0.0), caption("the last of the Seven Wonders still standing", 3.5)]))
    # ending: payoff on Giza, then the tease cuts to next week's world while Penny keeps talking (one line spans the cut)
    L = ["G46"]
    cut = 0.2 + 3.9
    a_ = scene("s09_outro", "plate:giza_later",
               [P(k, 300 + i * 330, G, 1.6, flip=i > 2, faces=[(0, {"mouth": "grin"})], acts=[(0.6 + i * 0.12, "cheer", None)])
                for i, k in enumerate(["atlas", "penny", "quill", "zed", "pike"])], L, lead=0.2, follow=False)
    rest = a_.dur - cut + 0.4
    a_.dur = cut
    out.append(a_)
    riders = []
    for r in range(2):                                                           # Mongol horsemen (same cast as the Mongols episode)
        for c in range(5):
            x = -1200 + c * 300 + r * 150
            p = M.Performer("mongol_1200:" + ("rider_mounted" if (c + r) % 2 else "rider2_mounted"), x=x, ground=1000 + r * 50, scale=1.15,
                            walks=[(0.0 + c * 0.05, x + 2400)], speed=2.4)
            p.shadow = True
            riders.append(p)
    out.append(Shot("s09_next", rest, "plate:steppe", actors=riders,
                    fx=[next_time(0.4)], camkeys=[(0.0, 1.0, 0.5, 0.5), (rest, 1.12, 0.5, 0.55)]))
    out.append(Shot("s10_endcard", 3.5, "endcard",
                    actors=[P(k, 360 + i * 300, 1030, 1.4, acts=[(0.3 + i * 0.12, "cheer" if k != "quill" else "hold_up", None)])
                            for i, k in enumerate(["penny", "atlas", "quill", "zed", "pike"])]))
    return out


K.shots = shots

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if cmd == "preview":
        K.preview(Path(sys.argv[2]) if len(sys.argv) > 2 else Path("D:/Temp/cartoon/ep03/preview.png"))
    elif cmd == "render":
        K.render(tuple(int(x) for x in sys.argv[2].split("/")), Path(sys.argv[3]) if len(sys.argv) > 3 else Path("D:/Temp/cartoon/ep03/shots"))
    elif cmd == "mix":
        K.mix(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]) if len(sys.argv) > 4 else Path("D:/Temp/cartoon/sneaky_snitch.mp3"))
