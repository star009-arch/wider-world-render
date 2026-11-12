"""Tiny Empires episode 1: "How a Company Took Over India" (~8 min). Hosts design v3; Penny narrates.

  python scripts/cartoon/ep01.py preview                contact sheet (one frame per scene)
  python scripts/cartoon/ep01.py render i/k [outdir]    render part i of k (silent scene clips)
  python scripts/cartoon/ep01.py mix <shots dir> <out>  dialogue + music + effects -> film

Lines: projects/tiny-empires/ep01/lines.json (script_v1.md, fact-checked), recorded by pilot_voice.py --ep ep01.
Every scene: hosts or historical cast, a set or map, camera that moves to whoever speaks, gestures on each line.
Maps are period-safe: relief basemaps, place pins at true coordinates, no invented borders.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402
import pilot_sets as PS  # noqa: E402
import scene as SC  # noqa: E402
import sets as S  # noqa: E402
from scene import Shot, ease, fx_label  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EP = ROOT / "projects/tiny-empires/ep01"
VOICE = Path(os.environ.get("TE_VOICE", "D:/Temp/cartoon/ep01/voice"))
LINES = {ln["id"]: ln for ln in json.loads((EP / "lines.json").read_text(encoding="utf-8"))["lines"]}
DUR = json.loads((VOICE / "durations.json").read_text()) if (VOICE / "durations.json").exists() else {}
CUES: list = []
GAP, LEAD, TAIL = 0.35, 0.45, 0.6
GESTURE = {"penny": ["present", "point", "present", "shrug"], "atlas": ["point", "present", "wave"], "quill": ["hold_up", "think", "present"],
           "zed": ["present", "think", "present"], "pike": ["shrug", "flinch", "shrug"]}
PROPS = {"penny": {"prop_r": "cane"}, "pike": {"prop_l": "rifle"}, "quill": {}, "zed": {}, "atlas": {}}


def dur(lid):
    return DUR.get(lid, max(1.2, len(LINES[lid]["text"]) / 15.0))


# ------------------------------------------------------------------------------------------------ sets
def _relief(bbox, darken=0.2):
    proj, (L0, L1, T, B) = S._proj(bbox)
    rel = Image.open(S.NE / "NE1_50M_SR_W" / "NE1_50M_SR_W" / "NE1_50M_SR_W.tif").convert("RGB")
    rw, rh = rel.size
    crop = rel.crop((int((L0 + 180) / 360 * rw), int((90 - T) / 180 * rh), int((L1 + 180) / 360 * rw), int((90 - B) / 180 * rh)))
    im = crop.resize((3840, 2160), Image.BICUBIC)
    im = Image.blend(im, Image.new("RGB", im.size, (20, 34, 56)), darken)
    return PS._finish(im.resize((1920, 1080), Image.LANCZOS), 0.5), (lambda lon, lat: tuple(v / 2 for v in proj(lon, lat)))


MAPS = {"m_world": (-30, -42, 112, 62), "m_india": (64, 5, 98, 37), "m_spice": (100, -12, 140, 12), "m_ocean": (30, -40, 100, 30)}
PROJ = {}


def register_sets():
    for k, f in PS.SETS.items():
        SC._BG[k] = f().convert("RGBA")
    SC._BG["court"] = PS._finish(S.tudor_court().convert("RGB"), 0.45).convert("RGBA")
    SC._BG["sea"] = PS._finish(S.sea().convert("RGB"), 0.4).convert("RGBA")
    SC._BG["storm"] = PS._finish(S.sea(stormy=True).convert("RGB"), 0.55).convert("RGBA")
    for k, bb in MAPS.items():
        im, pj = _relief(bb, 0.22)
        SC._BG[k] = im.convert("RGBA")
        PROJ[k] = pj
    SC._BG["card"] = PS._grad(1920, 1080, (40, 32, 44), (18, 16, 24)).convert("RGBA")
    SC._BG["endcard"] = PS.endcard().convert("RGBA")


# ------------------------------------------------------------------------------------------------ effects
def label(text, x, y, t0, size=64, color=(255, 255, 255), t1=1e9):
    return lambda t, d, f: fx_label(d, text, x, y, size, color, a=min(ease((t - t0) / 0.3), ease((t1 - t) / 0.3))) if t0 <= t < t1 else None


def caption(text, t0, t1=1e9, y=980):
    """Lower-third style caption on a dark band."""
    def f(t, d, frame):
        if not t0 <= t < t1:
            return
        a = min(ease((t - t0) / 0.3), ease((t1 - t) / 0.3))
        fo = S.font(46)
        w = d.textlength(text, font=fo) + 70
        d.rounded_rectangle([960 - w / 2, y - 42, 960 + w / 2, y + 40], radius=14, fill=(16, 14, 22, int(200 * a)))
        d.text((960, y), text, font=fo, fill=(255, 236, 180, int(255 * a)), anchor="mm")
    return f


def pin(mapkey, lon, lat, name, t0, color=(200, 40, 44), size=40, dx=26):
    def f(t, d, frame):
        if t < t0:
            return
        x, y = PROJ[mapkey](lon, lat)
        k = ease((t - t0) / 0.35)
        r = 14 * k + 4
        d.ellipse([x - r - 4, y - r - 4, x + r + 4, y + r + 4], fill=(20, 20, 24, 255))
        d.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))
        if k > 0.6:
            S_text(d, x + dx, y, name, size, a=k)
    return f


def S_text(d, x, y, text, size, a=1.0, anchor="lm", color=(255, 255, 255)):
    d.text((x, y), text, font=S.font(size), fill=color + (int(255 * a),), stroke_width=max(2, size // 10), stroke_fill=(20, 20, 24, int(255 * a)),
           anchor=anchor)


def route(mapkey, pts, t0, t1, color=(255, 214, 60), ship=True):
    def f(t, d, frame):
        if t < t0:
            return
        P = [PROJ[mapkey](*p) for p in pts]
        seg = [math.dist(a, b) for a, b in zip(P, P[1:])]
        g = ease((t - t0) / max(0.01, t1 - t0)) * sum(seg)
        out, acc = [P[0]], 0.0
        for (a, b), L in zip(zip(P, P[1:]), seg):
            if acc + L <= g:
                out.append(b)
                acc += L
            else:
                r = (g - acc) / L
                out.append((a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r))
                break
        for a, b in zip(out, out[1:]):
            d.line([a, b], fill=(20, 20, 24, 255), width=12)
            d.line([a, b], fill=color + (255,), width=7)
        if ship:
            S.ship(d, out[-1][0], out[-1][1] + 10, 0.2, t)
    return f


def arrow(x0, y0, x1, y1, t0, dur_=0.6, color=(220, 40, 40)):
    return lambda t, d, f: SC.fx_arrow(d, x0, y0, x1, y1, ease((t - t0) / dur_), color) if t >= t0 else None


def flags_on(mapkey, places, kind, t0, step=0.25, s=0.6):
    def f(t, d, frame):
        for i, (lon, lat) in enumerate(places):
            if t >= t0 + i * step:
                x, y = PROJ[mapkey](lon, lat)
                S.flag(d, x, y - 70 * s, kind, s, wave=t * 4)
    return f


def ships(paths, t0, t1):
    """paths: [(x0, y0, x1, y1, scale, flip, flag)]"""
    def f(t, d, frame):
        for x0, y0, x1, y1, s, fl, fk in paths:
            k = ease((t - t0) / max(0.01, t1 - t0))
            S.ship(d, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k + math.sin(t * 2 + x0) * 6, s, t, fl, fk)
    return f


def sinking(x, y, t0):
    def f(t, d, frame):
        k = ease((t - t0) / 1.4) if t >= t0 else 0.0
        S.ship(d, x, y + 160 * k, 0.9, t)
        if k > 0:
            d.rectangle([x - 300, y + 120, x + 300, y + 400], fill=(40, 70, 110, int(255 * min(1, k * 2))))
    return f


def icons_row(items, y, t0, step=0.5):
    """Spice / cloth icons with labels popping in: items = [(kind, label)]."""
    def f(t, d, frame):
        n = len(items)
        for i, (kind, lab) in enumerate(items):
            ts = t0 + i * step
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.45)
            x = 960 + (i - (n - 1) / 2) * 420
            r = 120 * k
            d.ellipse([x - r - 6, y - r - 6, x + r + 6, y + r + 6], fill=(20, 20, 24, 255))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 244, 226, 255))
            if kind == "pepper":
                for j in range(9):
                    a = j / 9 * 6.28
                    px, py = x + math.cos(a) * 45 * k, y + math.sin(a) * 45 * k
                    d.ellipse([px - 18 * k, py - 18 * k, px + 18 * k, py + 18 * k], fill=(40, 30, 26, 255))
            elif kind == "clove":
                for j in range(4):
                    a = j / 4 * 6.28 + 0.4
                    px, py = x + math.cos(a) * 30 * k, y + math.sin(a) * 30 * k
                    d.line([(px, py), (px + 50 * k * math.cos(a), py + 50 * k * math.sin(a))], fill=(120, 60, 30, 255), width=int(14 * k) + 1)
                    d.ellipse([px - 14 * k, py - 14 * k, px + 14 * k, py + 14 * k], fill=(150, 76, 36, 255))
            elif kind == "nutmeg":
                d.ellipse([x - 60 * k, y - 46 * k, x + 60 * k, y + 46 * k], fill=(150, 96, 56, 255), outline=(60, 36, 20, 255), width=6)
                d.arc([x - 40 * k, y - 30 * k, x + 40 * k, y + 30 * k], 200, 340, fill=(200, 60, 40, 255), width=8)
            elif kind == "cloth":
                for j, c in enumerate([(200, 60, 60), (230, 180, 60), (60, 120, 180)]):
                    d.rounded_rectangle([x - 80 * k, y - 60 * k + j * 40 * k, x + 80 * k, y - 25 * k + j * 40 * k], radius=10,
                                        fill=c + (255,), outline=(20, 20, 24, 255), width=4)
            S_text(d, x, y + 175, lab, 50, anchor="mm")
    return f


def bars(left, right, t0, labels=("Company", "Nawab")):
    """Army size comparison bars (people icons)."""
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 1.2)
        for row, (val, lab, col) in enumerate(((left, labels[0], (200, 40, 44)), (right, labels[1], (40, 100, 70)))):
            y = 420 + row * 260
            n = int(round(val / 1000))
            shown = int(n * k)
            S_text(d, 200, y - 80, f"{lab}: about {val:,}", 58, color=(255, 236, 180))
            for i in range(shown):
                x = 220 + (i % 50) * 30
                yy = y + (i // 50) * 44
                d.ellipse([x - 9, yy - 26, x + 9, yy - 8], fill=col + (255,))
                d.rounded_rectangle([x - 12, yy - 8, x + 12, yy + 22], radius=6, fill=col + (255,))
        if k >= 1:
            S_text(d, 960, 960, "each figure = about 1,000 soldiers", 34, anchor="mm", color=(220, 220, 220))
    return f


def timeline(events, t0, step=0.9, y=520):
    """Horizontal timeline: events = [(year label, text)]."""
    def f(t, d, frame):
        if t < t0:
            return
        n = len(events)
        k = ease((t - t0) / 0.8)
        d.line([(160, y), (160 + 1600 * k, y)], fill=(240, 220, 160, 255), width=10)
        for i, (yr, txt) in enumerate(events):
            ts = t0 + 0.4 + i * step
            if t < ts:
                continue
            a = ease((t - ts) / 0.35)
            x = 220 + i * (1480 / max(1, n - 1))
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(200, 60, 40, int(255 * a)), outline=(20, 20, 24, 255), width=5)
            S_text(d, x, y - 80, yr, 64, a=a, anchor="mm", color=(255, 214, 120))
            for j, ln in enumerate(txt.split("|")):
                S_text(d, x, y + 80 + j * 50, ln, 40, a=a, anchor="mm")
    return f


def wall_build(t0, t1):
    """Company workers raising Calcutta's walls: scaffold and rising bricks."""
    def f(t, d, frame):
        k = ease((t - t0) / max(0.01, t1 - t0)) if t >= t0 else 0.0
        x0, x1, y = 300, 1500, 250
        h = 110 * k
        d.rectangle([x0, y - h, x1, y], fill=(190, 90, 70, 255), outline=(20, 20, 24, 255), width=4)
        for row in range(int(h // 22)):
            yy = y - row * 22
            for c in range(int((x1 - x0) / 60)):
                xx = x0 + c * 60 + (row % 2) * 30
                d.rectangle([xx, yy - 22, xx + 58, yy], outline=(140, 60, 50, 255), width=2)
        for xs in (420, 900, 1380):
            d.line([(xs, y), (xs, y - 200)], fill=(120, 84, 50, 255), width=8)
            d.line([(xs - 60, y - 140), (xs + 60, y - 140)], fill=(120, 84, 50, 255), width=8)
    return f


def coins_flow(x0, y0, x1, y1, t0, t1):
    def f(t, d, frame):
        if t < t0:
            return
        for i in range(14):
            ph = ((t - t0) * 0.9 + i / 14) % 1.0
            if t - t0 < i * 0.1:
                continue
            x = x0 + (x1 - x0) * ph
            y = y0 + (y1 - y0) * ph - math.sin(ph * math.pi) * 160
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(232, 190, 60, 255), outline=(20, 20, 24, 255), width=4)
    return f


# ------------------------------------------------------------------------------------------------ scene builder
def P(key, x, ground, s=1.7, **kw):
    kw.setdefault("props", dict(PROPS.get(key, {})))
    return M.Performer(key, x=x, ground=ground, scale=s, **kw)


def scene(name, bg, cast, lines, *, fx=(), under=(), cam_wide=(1.0, 0.5, 0.5), closeup=1.32, follow=True, shake=(), extra=0.0,
          lead=LEAD, gestures=True, cam=None):
    """cast: list of Performers (hosts keyed by .key). lines: line ids in order. The camera eases to each speaker."""
    t = lead
    starts = []
    for lid in lines:
        starts.append(t)
        t += dur(lid) + GAP
    total = t + TAIL + extra
    by_key = {}
    for p in cast:
        by_key.setdefault(p.key, p)
    keys = [(0.0,) + tuple(cam_wide)]
    for i, (lid, ts) in enumerate(zip(lines, starts)):
        who = LINES[lid]["who"]
        CUES.append((name, lid, ts))
        p = by_key.get(who)
        if p is not None:
            p.lips = list(p.lips) + M.load_rhubarb(VOICE / f"{lid}_lips.json", offset=ts) if (VOICE / f"{lid}_lips.json").exists() else p.lips
            if gestures:
                g = GESTURE[who][i % len(GESTURE[who])] if who in GESTURE else None
                if g and not any(abs(a[0] - ts) < 0.5 for a in p.acts):
                    p.acts = list(p.acts) + [(ts + 0.15, g, max(0.2, dur(lid) - 1.4))]
            if follow:
                x, _ = p.pos_at(ts + 0.5)
                cx = min(max(x / 1920, 0.5 / closeup), 1 - 0.5 / closeup)
                cy = min(max((p.ground - 230 * p.scale / 1.7) / 1080, 0.5 / closeup), 1 - 0.5 / closeup)
                keys += [(max(0.0, ts - 0.35), *keys[-1][1:]), (ts + 0.15, closeup, cx, cy)]
        else:
            keys += [(max(0.0, ts - 0.35), *keys[-1][1:]), (ts + 0.15) and (ts + 0.15, *cam_wide)]
    keys.append((total, *keys[-1][1:]))
    clean = []
    for k in keys:
        if clean and k[0] <= clean[-1][0]:
            k = (clean[-1][0] + 0.01,) + tuple(k[1:])
        clean.append(k)
    return Shot(name, total, bg, actors=list(cast), fx=list(fx), under=list(under), camkeys=cam or clean, shake=list(shake))


def at(lines, i, lead=LEAD):
    """Start time of the i-th line in a scene."""
    t = lead
    for lid in lines[:i]:
        t += dur(lid) + GAP
    return t


# ------------------------------------------------------------------------------------------------ the episode
def shots():
    CUES.clear()
    out = []
    G = 1030

    # 1. HOOK
    L = ["E01", "E02", "E03", "E04", "E05"]
    out.append(scene("s01_hook", "plate:globe",
                     [P("penny", 960, G, 2.0, faces=[(0, {"brows": -0.3, "mouth": "smirk"})], acts=[(0.0, "jump", 0.0)]),
                      P("atlas", -200, G, 1.7, walks=[(at(L, 1) - 1.2, 420)], speed=1.6, faces=[(0, {"brows": 0.6, "mouth": "o"})]),
                      P("zed", 2150, G, 1.7, flip=True, walks=[(at(L, 3) - 1.2, 1520)], speed=1.8, faces=[(0, {"mouth": "grin"})])],
                     L, fx=[caption("TINY EMPIRES", at(L, 4) + 1.6)]))
    # 2. LONDON 1600
    L = ["E06", "E07"]
    out.append(scene("s02_charter", "plate:court",
                     [P("queen", 960, 880, 1.5, faces=[(0, {"mouth": "smile"})], acts=[(1.2, "present", None)]),
                      P("merchant", 560, 960, 1.4, faces=[(0, {"mouth": "grin"})]), P("merchant2", 1340, 960, 1.4, flip=True),
                      P("quill", 1650, G, 1.7, flip=True)],
                     L, fx=[label("LONDON · 31 DECEMBER 1600", 960, 90, 0.3, 64, (255, 230, 150))]))
    L = ["E08", "E09"]
    out.append(scene("s02_monopoly", "m_world", [P("zed", 1650, G, 1.6, flip=True)], L,
                     fx=[pin("m_world", -0.1, 51.5, "London", 0.4), pin("m_world", 18.4, -34.4, "Cape of Good Hope", 1.0),
                         label("EAST OF THE CAPE: COMPANY ONLY", 1150, 160, 2.0, 56, (255, 214, 60))]))
    L = ["E10", "E11"]
    out.append(scene("s02_investors", "storm", [P("pike", 1600, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})],
                                                  acts=[(at(L, 1) + 0.2, "flinch", 0.5)])], L,
                     under=[sinking(700, 560, at(L, 0) + 2.2)], fx=[PL_drips(1600, 380, at(L, 1), 99)], follow=False,
                     cam_wide=(1.0, 0.5, 0.5)))
    # 3. SHIPS AND SPICES
    L = ["E12"]
    out.append(scene("s03_spice", "card", [P("penny", 1650, G, 1.6, flip=True)], L,
                     fx=[icons_row([("pepper", "pepper"), ("clove", "cloves"), ("nutmeg", "nutmeg")], 420, 0.6),
                         label("WORTH A FORTUNE IN EUROPE", 760, 760, 2.4, 58, (255, 214, 60))], follow=False))
    L = ["E13"]
    out.append(scene("s03_route", "m_world", [P("atlas", 1700, G, 1.6, flip=True)], L,
                     fx=[route("m_world", S.ROUTE_CAPE, 0.6, dur("E13") + 0.3), pin("m_world", -0.1, 51.5, "London", 0.3)], follow=False))
    L = ["E14", "E15"]
    out.append(scene("s03_lancaster", "plate:ocean", [P("zed", 1650, G, 1.7, flip=True, acts=[(at(L, 1), "celebrate", 0.5)])], L,
                     fx=[label("1601 · JAMES LANCASTER", 700, 120, 0.4, 60, (255, 230, 150)),
                         PL_coins(1200, 980, at(L, 1), at(L, 1) + 1.5)]))
    L = ["E16", "E17"]
    out.append(scene("s03_dutch", "plate:spice", [P("quill", 1720, G, 1.6, flip=True)], L,
                     fx=[label("THE SPICE ISLANDS", 900, 110, 0.4, 64, (255, 220, 120)),
                         caption("Dutch East India Company, founded 1602", 1.2, at(L, 1)),
                         caption("Amboyna, 1623", at(L, 1) + 0.4)]))
    # 4. ARRIVAL IN INDIA
    L = ["E18"]
    out.append(scene("s04_mughal", "plate:india", [P("penny", 1650, G, 1.6, flip=True)], L,
                     fx=[label("THE MUGHAL EMPIRE", 760, 140, 0.6, 76, (255, 220, 120)), caption("India in the early 1600s", 1.4)]))
    L = ["E19", "E20"]
    out.append(scene("s04_court", "plate:durbar",
                     [P("jahangir", 960, 860, 1.6, faces=[(0, {"mouth": "smile"})]),
                      P("merchant", 500, 980, 1.4, acts=[(1.0, "nod", 0.0)]),
                      P("roe", -200, 990, 1.4, walks=[(at(L, 1) - 0.3, 700)], speed=1.5, acts=[(at(L, 1) + 1.8, "present", None)]),
                      P("atlas", 1650, G, 1.7, flip=True)],
                     L, fx=[label("EMPEROR JAHANGIR", 960, 90, 0.4, 60, (255, 230, 150)), caption("Surat, 1613 · under Emperor Jahangir", 1.2, at(L, 1)),
                            caption("Sir Thomas Roe, ambassador", at(L, 1) + 0.5)]))
    L = ["E21"]
    out.append(scene("s04_posts", "m_india", [P("penny", 1680, G, 1.5, flip=True)], L,
                     fx=[pin("m_india", 72.83, 21.17, "Surat 1613", 0.3), pin("m_india", 80.27, 13.08, "Madras 1639", 1.6),
                         pin("m_india", 72.88, 19.08, "Bombay 1668", 3.6), pin("m_india", 88.36, 22.57, "Calcutta 1690", 6.0)], follow=False))
    L = ["E22"]
    out.append(scene("s04_cloth", "m_world", [P("zed", 1700, G, 1.6, flip=True)], L,
                     fx=[icons_row([("cloth", "cotton"), ("cloth", "silk")], 300, 0.3),
                         arrow(*PROJ_or("m_world", 80, 20), *PROJ_or("m_world", 0, 50), 1.2, 1.0, (240, 190, 60))], follow=False))
    L = ["E23", "E24", "E25"]
    out.append(scene("s04_army", "plate:fort",
                     [*PL_army("csepoy", 250, 990, 5, 1, 140, 0, 1.2, walk=(0.3, 500), speed=1.6),
                      P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "o"})]),
                      P("penny", 1750, G + 10, 1.7, flip=True)],
                     L, fx=[caption("Company forts and sepoy soldiers", 0.6, at(L, 1))]))
    # 5. SIRAJ AND BENGAL
    L = ["E26"]
    out.append(scene("s05_1707", "card", [P("penny", 1700, G, 1.6, flip=True)], L,
                     fx=[timeline([("1707", "Aurangzeb dies"), ("after", "Mughal power|weakens"), ("1700s", "regional rulers|grow stronger")], 0.4, 1.6)],
                     follow=False))
    L = ["E27", "E28"]
    out.append(scene("s05_siraj", "plate:durbar",
                     [P("nawab", 960, 880, 1.7, faces=[(0, {"mouth": "smirk"}), (at(L, 1), {"brows": -1.0, "mouth": "frown"})],
                        acts=[(at(L, 1) + 0.3, "fold", None)]),
                      P("atlas", 1650, G, 1.7, flip=True)],
                     L, fx=[label("SIRAJ UD-DAULAH · NAWAB OF BENGAL, 1756", 960, 90, 0.4, 54, (255, 230, 150))]))
    L = ["E29", "E30", "E31"]
    sw = at(L, 0) + 1.0
    out.append(scene("s05_capture", "plate:fort",
                     [P("nawab", -300, 960, 1.5, walks=[(sw - 1.5, 820)], speed=2.0, acts=[(sw + 0.4, "celebrate", None)]),
                      *PL_army("sepoy", -900, 990, 4, 1, 140, 0, 1.2, walk=(sw - 1.6, 900), speed=2.0),
                      P("pike", 1500, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]),
                      P("penny", 1780, G + 10, 1.6, flip=True)],
                     L, fx=[PL_flag(1660, 70, sw, invert=True, s=1.6), label("CALCUTTA · JUNE 1756", 420, 110, 0.3, 60)]))
    # 6. CLIVE AND THE SECRET DEAL
    L = ["E32"]
    out.append(scene("s06_clive", "plate:ocean", [P("clive", 1500, 980, 1.6, flip=True, faces=[(0, {"mouth": "smirk"})])], L,
                     fx=[label("CLIVE'S SOLDIERS · WATSON'S FLEET", 960, 110, 1.0, 58, (255, 230, 150))], follow=False))
    L = ["E33"]
    sw = at(L, 0) + 2.4
    out.append(scene("s06_retake", "plate:fort",
                     [P("clive", -250, 980, 1.6, speed=2.2, walks=[(sw - 2.0, 760)], acts=[(sw + 0.2, "point", None)]),
                      *PL_army("csepoy", -800, 990, 3, 1, 150, 0, 1.3, walk=(sw - 2.1, 900), speed=2.2),
                      P("quill", 1700, G, 1.7, flip=True)],
                     L, fx=[PL_flag(1660, 70, sw, s=1.6), label("2 JANUARY 1757", 400, 110, 0.4, 64, (255, 230, 150))]))
    L = ["E34"]
    out.append(scene("s06_plotters", "plate:durbar",
                     [P("mir_jafar", 700, 900, 1.6, faces=[(0, {"mouth": "smirk", "brows": -0.4})], acts=[(1.4, "think", None)]),
                      P("jagat_seth", 1180, 900, 1.5, flip=True, faces=[(0, {"mouth": "smirk"})]),
                      P("penny", 1720, G, 1.5, flip=True)],
                     L, fx=[label("MIR JAFAR", 700, 300, dur("E34") * 0.45, 52), label("THE JAGAT SETH BANKERS", 1180, 300, dur("E34") * 0.7, 46)]))
    L = ["E35", "E36", "E37", "E38"]
    out.append(scene("s06_deal", "plate:camp",
                     [P("mir_jafar", 520, 990, 1.8, faces=[(0, {"mouth": "smirk"})]),
                      P("clive", 1100, 990, 1.8, flip=True, faces=[(0, {"mouth": "smirk"})]),
                      P("zed", 820, 1040, 1.6), P("pike", 1500, G, 1.7, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]),
                      P("penny", 1780, G + 10, 1.6, flip=True)],
                     L, fx=[label("SECRET AGREEMENT · JUNE 1757", 960, 90, 0.4, 60, (255, 214, 120))],
                     under=[PL_contract(900, 1010, at(L, 1) + 0.5, at(L, 2))]))
    # 7. PLASSEY
    L = ["E39"]
    out.append(scene("s07_plassey", "plate:plassey",
                     [*PL_army("redcoat", 120, 640, 3, 2, 70, 36, 0.55), *PL_army("csepoy", 150, 712, 4, 2, 70, 36, 0.55),
                      *PL_army("sepoy", 980, 600, 12, 6, 70, 30, 0.5, flip=True), P("penny", 1720, G, 1.6, flip=True)],
                     L, fx=[label("PLASSEY · 23 JUNE 1757", 960, 100, 0.4, 76, (255, 230, 140))], follow=False))
    L = ["E40"]
    out.append(scene("s07_numbers", "card", [P("atlas", 1700, G, 1.6, flip=True)], L, fx=[bars(3000, 50000, 0.6)], follow=False))
    L = ["E41", "E42"]
    out.append(scene("s07_rain", "plate:plassey_rain",
                     [P("pike", 520, 1040, 1.9, faces=[(0, {"brows": 1.0, "mouth": "worried"})], acts=[(0.3, "cower", 1.0)])], L,
                     under=[PL_cannon(330, 1000, False), PL_tarp(470, 1060, 640, 0.5), PL_cannon(1500, 900, True, fire_at=(0.4, 1.3), fizzle_after=2.0),
                            PL_cannon(1760, 960, True, fire_at=(0.8,), fizzle_after=2.0)],
                     fx=[PL_rain, label("the Nawab's guns fall silent", 1450, 160, 2.6, 52)]))
    L = ["E43", "E44"]
    sit = at(L, 0) + 1.2
    out.append(scene("s07_betrayal", "plate:plassey",
                     [*PL_army("sepoy", 800, 700, 7, 3, 105, 50, 0.85, flip=True, acts=[(sit, "sit", None)]),
                      P("mir_jafar", 1180, 900, 1.5, flip=True, faces=[(0, {"mouth": "smirk"})], acts=[(sit - 0.2, "fold", None)]),
                      P("nawab", 560, 930, 1.5, acts=[(at(L, 1) - 0.2, "double_take", 0.0)], walks=[(at(L, 1) + 1.2, -400)], speed=2.4),
                      P("quill", 1720, G, 1.7, flip=True)],
                     L, fx=[label("MIR JAFAR", 1180, 520, 0.4, 52)]))
    # 8. POLITICAL POWER
    L = ["E45", "E46"]
    out.append(scene("s08_throne", "plate:durbar",
                     [P("mir_jafar", 960, 890, 1.7, faces=[(0, {"mouth": "grin"}), (at(L, 1), {"brows": 1.0, "mouth": "worried"})]),
                      P("zed", 1650, G, 1.7, flip=True)],
                     L, under=[PL_shadow(960, 470, 0.8, at(L, 1) + dur("E46"))], fx=[PL_crown(960, 560, 0.2)], follow=False,
                     cam_wide=(1.0, 0.5, 0.5)))
    L = ["E47"]
    out.append(scene("s08_buxar", "plate:plassey",
                     [*PL_army("redcoat", 160, 700, 3, 2, 75, 40, 0.6), *PL_army("csepoy", 200, 780, 4, 2, 75, 40, 0.6),
                      *PL_army("sepoy", 1000, 640, 9, 5, 75, 34, 0.55, flip=True), P("penny", 1720, G, 1.5, flip=True)],
                     L, fx=[label("BUXAR · 1764", 960, 100, 0.4, 76, (255, 230, 140)),
                            label("Mir Qasim + Awadh + the Mughal emperor", 1250, 520, dur("E47") * 0.55, 46)], follow=False))
    L = ["E48", "E49", "E50"]
    out.append(scene("s08_diwani", "plate:durbar",
                     [P("shah_alam", 960, 880, 1.6, faces=[(0, {"mouth": "smile"})], acts=[(1.0, "present", None)]),
                      P("clive", 560, 980, 1.6, faces=[(0, {"mouth": "grin"})], acts=[(1.6, "nod", 0.0)]),
                      P("zed", 1450, G, 1.7, flip=True), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[label("THE DIWANI · 1765", 960, 90, 0.4, 64, (255, 230, 150)),
                            caption("right to collect the revenues of Bengal, Bihar and Orissa", 1.4, at(L, 1)),
                            coins_flow(960, 700, 560, 760, at(L, 1), at(L, 2) + 2)]))
    # 9. WHAT HAPPENED NEXT
    L = ["E51"]
    out.append(scene("s09_century", "card", [P("penny", 1700, G, 1.6, flip=True)], L,
                     fx=[timeline([("1757", "Plassey:|Bengal"), ("1764–65", "Buxar and|the diwani"), ("1818–56", "most of the|subcontinent")], 0.5, 2.2)],
                     follow=False))
    L = ["E52"]
    out.append(scene("s09_end", "card", [P("quill", 1700, G, 1.6, flip=True)], L,
                     fx=[timeline([("1857–58", "great uprising;|Crown takes over"), ("1874", "Company|dissolved")], 0.5, 2.6)], follow=False))
    L = ["E53", "E54"]
    out.append(scene("s09_outro", "plate:bengal",
                     [P(k, 300 + i * 330, G, 1.6, flip=i > 2, faces=[(0, {"mouth": "grin" if k != "pike" else "worried"})])
                      for i, k in enumerate(["atlas", "penny", "quill", "zed", "pike"])],
                     L, extra=0.8))
    out.append(Shot("s10_endcard", 3.5, "endcard",
                    actors=[P(k, 360 + i * 300, 1030, 1.4, acts=[(0.3 + i * 0.12, "cheer" if k != "quill" else "hold_up", None)])
                            for i, k in enumerate(["penny", "atlas", "quill", "zed", "pike"])]))
    return out


# helpers borrowed from the pilot (imported lazily so the pilot's own sets are not needed)
def _pl():
    import pilot as PL
    return PL


def PL_drips(*a): return _pl().drips(*a)
def PL_coins(*a): return _pl().coins(*a)
def PL_contract(*a): return _pl().contract(*a)
def PL_cannon(*a, **k): return _pl().cannon(*a, **k)
def PL_tarp(*a): return _pl().tarp(*a)
def PL_rain(t, d, f): return _pl().rain_fx(t, d, f)
def PL_crown(*a): return _pl().crown(*a)
def PL_shadow(*a): return _pl().penny_shadow(*a)


def PL_army(key, x0, ground, cols, rows, dx, dy, s, flip=False, walk=None, acts=None, speed=1.0):
    out = []
    for r in range(rows):
        for c in range(cols):
            x = x0 + c * dx + (r % 2) * dx / 2
            p = M.Performer(key, x=x, ground=ground + r * dy, scale=s, flip=flip, walks=[(walk[0], x + walk[1])] if walk else [],
                            acts=list(acts or []), speed=speed)
            p.shadow = s > 0.6
            out.append(p)
    return out


def PL_flag(x, y, t_swap, invert=False, s=2.0):
    def f(t, d, frame):
        a, b = ("company", "nawab") if invert else ("nawab", "company")
        kind = a if t < t_swap else b
        k = min(1.0, abs(t - t_swap) / 0.25)
        S.flag(d, x, y + (1 - k) * 60 * s, kind, s, wave=t * 4)
    return f


def PROJ_or(key, lon, lat):
    return PROJ[key](lon, lat) if key in PROJ else (lon, lat)


# ------------------------------------------------------------------------------------------------ CLI
def preview(out_png):
    ss = shots()
    cols = 6
    sheet = Image.new("RGB", (cols * 320, ((len(ss) + cols - 1) // cols) * 180))
    for i, sh in enumerate(ss):
        sheet.paste(SC.render_frame(sh, sh.dur * 0.55).resize((320, 180)), ((i % cols) * 320, (i // cols) * 180))
    sheet.save(out_png)
    print("scenes", len(ss), "total", round(sum(s.dur for s in ss), 1), "s")


def render(part, outdir):
    i, k = part
    outdir.mkdir(parents=True, exist_ok=True)
    ss = shots()
    order = sorted(range(len(ss)), key=lambda j: -ss[j].dur)                  # balance parts by length
    mine = [j for n, j in enumerate(order) if n % k == i - 1]
    for j in mine:
        sh = ss[j]
        SC.render_shot(sh, outdir / f"{sh.name}.mp4", threads=int(os.environ.get("TE_THREADS", "2")))
        print("rendered", sh.name, round(sh.dur, 1), flush=True)


def two_pass_loudnorm(ff, inputs, graph, out_args, timeout=1800):
    """Run an ffmpeg filtergraph containing {LN} twice: measure loudness, then apply it linearly. Single-pass loudnorm adapts its
    gain while playing, which makes the first seconds swell and pump; the measured linear pass keeps the whole film steady."""
    import re as _re
    pre = [*ff, *inputs, "-filter_complex", graph.replace("{LN}", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json"), "-map", "[a]", "-f", "null", "-"]
    r = subprocess.run([x for x in pre if x not in ("-loglevel", "error")], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout)
    m = json.loads(_re.findall(r"\{[^{}]*\}", r.stderr)[-1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run([*ff, *inputs, "-filter_complex", graph.replace("{LN}", ln), *out_args], check=True, stdin=subprocess.DEVNULL, timeout=timeout)


def mix(shots_dir: Path, out: Path, music: Path):
    ss = shots()
    start, acc = {}, 0.0
    for sh in ss:
        start[sh.name] = acc
        acc += sh.dur
    total = acc
    ff = [SC.ffmpeg(), "-nostdin", "-y", "-loglevel", "error"]
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.parent / "concat.txt"
    lst.write_text("".join(f"file '{(shots_dir.resolve() / (sh.name + '.mp4')).as_posix()}'\n" for sh in ss))
    video = out.parent / "video.mp4"
    subprocess.run([*ff, "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)], check=True, stdin=subprocess.DEVNULL, timeout=1800)
    bus = out.parent / "dialogue_bus.wav"                                       # pass 1: dialogue bus
    ins, flt, labs = [], [], []
    for n, (nm, lid, t0) in enumerate(CUES):
        ins += ["-i", str(VOICE / f"{lid}.mp3")]
        ms = int((start[nm] + t0) * 1000)
        flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{n}]")
        labs.append(f"[v{n}]")
    flt.append(f"{''.join(labs)}amix=inputs={len(CUES)}:normalize=0:duration=longest,apad=whole_dur={total:.2f},atrim=0:{total:.2f}[dia]")
    subprocess.run([*ff, *ins, "-filter_complex", ";".join(flt), "-map", "[dia]", "-ar", "48000", str(bus)], check=True,
                   stdin=subprocess.DEVNULL, timeout=1800)
    flt = ["[1:a]anull[key]", "[2:a]anull[dia]",
           f"[3:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume=0.2,afade=t=in:d=2.0,"
           f"afade=t=out:st={total - 3:.2f}:d=3[mus]",
           "[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck]",
           f"[duck][dia]amix=inputs=2:normalize=0:duration=first,{{LN}},alimiter=limit=0.89,aresample=48000,afade=t=in:d=0.15,"
           f"atrim=0:{total:.2f}[a]"]
    two_pass_loudnorm(ff, ["-i", str(video), "-i", str(bus), "-i", str(bus), "-stream_loop", "-1", "-i", str(music)], ";".join(flt),
                      ["-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", str(out)])
    print("wrote", out, round(total, 1), "s")


register_sets()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if cmd == "preview":
        preview(Path(sys.argv[2]) if len(sys.argv) > 2 else Path("D:/Temp/cartoon/ep01/preview.png"))
    elif cmd == "render":
        part = tuple(int(x) for x in sys.argv[2].split("/"))
        render(part, Path(sys.argv[3]) if len(sys.argv) > 3 else Path("D:/Temp/cartoon/ep01/shots"))
    elif cmd == "mix":
        mix(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]) if len(sys.argv) > 4 else Path("D:/Temp/cartoon/sneaky_snitch.mp3"))
