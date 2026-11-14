"""Tiny Empires episode 2: "How the Mongols Conquered Almost Everything" (~8.5 min). Rebuilt to the period standard (bible 05):
hosts in Mongol dress (hosts3 world "mongol_1200"), cast from people.py, Mongol-era 3D sets (te-3d-mongol-v1), pacing rule (hook, tease ending). Engine: ep01.py (scene builder, maps, fx).

  python scripts/cartoon/ep02.py preview | render i/k [outdir] | mix <shots dir> <out> [music]

Lines: projects/tiny-empires/ep02/lines.json (script_v1.md, fact-checked; extra section X01–X09 fact-checked separately).
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep01 as K  # noqa: E402
import motions as M  # noqa: E402
import scene as SC  # noqa: E402
import sets as S  # noqa: E402
from scene import Shot, ease  # noqa: E402
import fxlib as FX  # noqa: E402

M.set_world("mongol_1200")
GOLD = (255, 214, 120)

K.EP = K.ROOT / "projects/tiny-empires/ep02"
K.VOICE = Path(os.environ.get("TE_VOICE", "D:/Temp/cartoon/ep02/voice"))
K.LINES = {ln["id"]: ln for ln in json.loads((K.EP / "lines.json").read_text(encoding="utf-8"))["lines"]}
K.DUR = json.loads((K.VOICE / "durations.json").read_text()) if (K.VOICE / "durations.json").exists() else {}
K.MAPS.update({"m_ca": (50, 32, 76, 46), "m_europe": (8, 38, 62, 60), "m_eurasia": (-12, 8, 146, 68), "m_levant": (29, 27, 41, 37)})
for k in ("m_ca", "m_europe", "m_eurasia", "m_levant"):
    im, pj = K._relief(K.MAPS[k], 0.22)
    SC._BG[k] = im.convert("RGBA")
    K.PROJ[k] = pj

P, scene, at, dur, label, caption, pin, route = K.P, K.scene, K.at, K.dur, K.label, K.caption, K.pin, K.route
army, timeline = K.PL_army, K.timeline
G = 1030


# ------------------------------------------------------------------------------------------------ episode fx
def decimal(t0):
    """Units of 10, 100, 1,000, 10,000: rows of riders that multiply."""
    def f(t, d, frame):
        for i, (n, lab) in enumerate(((10, "10  ·  arban"), (100, "100  ·  jaghun"), (1000, "1,000  ·  mingghan"), (10000, "10,000  ·  tumen"))):
            ts = t0 + i * 1.1
            if t < ts:
                continue
            a = ease((t - ts) / 0.4)
            y = 240 + i * 170
            K.S_text(d, 180, y, lab, 56, a=a, color=(255, 224, 140))
            dots = min(60, n // (1 if n <= 10 else 10 if n <= 100 else 100 if n <= 1000 else 1000) * (1 if n <= 10 else 6))
            dots = (10, 30, 45, 60)[i]
            for j in range(int(dots * a)):
                x = 760 + (j % 30) * 30
                yy = y - 22 + (j // 30) * 34
                d.ellipse([x - 9, yy - 9, x + 9, yy + 9], fill=(200, 70, 50, 255), outline=(20, 20, 24, 255))
    return f


def paiza(t0):
    def f(t, d, frame):
        if t < t0:
            return
        k = M.ease_out_back((t - t0) / 0.5)
        cx, cy, w, h = 760, 520, 300 * k, 520 * k
        d.rounded_rectangle([cx - w / 2 - 8, cy - h / 2 - 8, cx + w / 2 + 8, cy + h / 2 + 8], radius=60, fill=(30, 24, 20, 255))
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=55, fill=(214, 172, 72, 255))
        d.ellipse([cx - 40 * k, cy - h / 2 + 20 * k, cx + 40 * k, cy - h / 2 + 100 * k], fill=(30, 24, 20, 255))
        for i in range(5):
            y = cy - 120 * k + i * 70 * k
            d.line([(cx - 60 * k, y), (cx - 60 * k, y + 50 * k)], fill=(120, 80, 30, 255), width=8)
            d.line([(cx + 10 * k, y), (cx + 10 * k, y + 50 * k)], fill=(120, 80, 30, 255), width=8)
        if k > 0.9:
            K.S_text(d, 1180, 420, "PAIZA", 80, color=(255, 214, 120))
            K.S_text(d, 1180, 520, "a metal pass:", 46)
            K.S_text(d, 1180, 580, "fresh horses and supplies", 46)
            K.S_text(d, 1180, 640, "at every relay station", 46)
    return f


def paper_money(t0):
    def f(t, d, frame):
        if t < t0:
            return
        for i in range(5):
            ts = t0 + i * 0.25
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.4)
            x, y = 420 + i * 200, 520 + (i % 2) * 40
            w, h = 150 * k, 240 * k
            d.rectangle([x - w / 2 - 5, y - h / 2 - 5, x + w / 2 + 5, y + h / 2 + 5], fill=(30, 24, 20, 255))
            d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=(220, 200, 160, 255))
            d.rectangle([x - w / 2 + 10 * k, y - h / 2 + 10 * k, x + w / 2 - 10 * k, y + h / 2 - 10 * k], outline=(150, 40, 30, 255), width=5)
            d.rectangle([x - 30 * k, y + 40 * k, x + 30 * k, y + 100 * k], fill=(190, 40, 40, 255))
            for j in range(4):
                d.line([(x - 40 * k, y - 80 * k + j * 25 * k), (x + 40 * k, y - 80 * k + j * 25 * k)], fill=(60, 50, 40, 255), width=4)
        if t >= t0 + 1.5:
            K.S_text(d, 960, 230, "Yuan paper money", 60, anchor="mm", color=(255, 224, 140))
    return f


def arrows_volley(x0, y0, x1, y1, t0, n=12):
    def f(t, d, frame):
        if t < t0:
            return
        for i in range(n):
            ph = ((t - t0) * 1.2 + i / n) % 1.0
            if t - t0 < i * 0.05:
                continue
            x = x0 + (x1 - x0) * ph + (i % 4) * 30
            y = y0 + (y1 - y0) * ph - math.sin(ph * math.pi) * 180 + (i // 4) * 25
            ang = math.atan2((y1 - y0) - math.cos(ph * math.pi) * 180 * math.pi, x1 - x0)
            d.line([(x, y), (x - 40 * math.cos(ang), y - 40 * math.sin(ang))], fill=(40, 30, 24, 255), width=4)
    return f


SILK = [(108.9, 34.3), (103.8, 36.1), (94.7, 40.1), (87.6, 43.8), (76.0, 39.5), (67.0, 39.7), (61.8, 37.7), (51.4, 35.7), (44.4, 33.3),
        (36.3, 33.5), (28.98, 41.0)]


# ------------------------------------------------------------------------------------------------ the episode
W_ = "mongol_1200"
MK = {"rider": "rider_mounted", "genghis": "genghis_mounted", "knight": "knight_mounted", "mamluk": "mamluk_mounted", "camel": "camel"}


def E(key, x, ground=1000, s=1.5, **kw):
    """A period person from people.py (Mongol world)."""
    return M.Performer(f"{W_}:{key}", x=x, ground=ground, scale=s, **kw)


def riders(x0, ground, n, dx, s, flip=False, walk=None, speed=2.2, key="rider", rows=1, dy=40):
    out = []
    for r in range(rows):
        out += FX.people(W_, [MK.get(key, key)] * n, x0 + (r % 2) * dx / 2, ground + r * dy, dx, s, flip=flip, walk=walk, speed=speed)
    return out


def split(first, cut, bg, actors=(), fx=(), camkeys=None, name=None):
    """Cut a one-line shot in two (the voice keeps running across the cut): first part on `first`, the rest on a new picture."""
    rest = first.dur - cut
    first.dur = cut
    return [first, Shot(name or first.name + "_b", rest, bg, actors=list(actors), fx=list(fx),
                        camkeys=camkeys or [(0.0, 1.0, 0.5, 0.5), (rest, 1.06, 0.5, 0.5)])]


def frac(mapkey, lon, lat):
    x, y = K.PROJ[mapkey](lon, lat)
    return x / 1920, y / 1080


def scene(*a, **kw):
    """Engine scene + a slow push-in on any shot that would otherwise hold a frozen frame."""
    sh = K.scene(*a, **kw)
    if kw.get("follow", True) is False and kw.get("cam") is None:
        sh.camkeys = [(0.0, 1.0, 0.5, 0.5), (sh.dur, 1.045, 0.5, 0.5)]
    return sh


def shots():
    K.CUES.clear()
    out = []
    H0 = 0.2
    # ---- HOOK: voice in 0.2 s, a new picture on every line, the mystery, then the title sting (~25 s)
    L = ["M01"]
    a_ = scene("s00_ride", "plate:m_steppe_dawn", [*riders(-900, 1010, 6, 210, 1.15, walk=(0.0, 2600), rows=2)], L, lead=H0, follow=False,
               cam=[(0.0, 1.0, 0.5, 0.5), (4.0, 1.08, 0.55, 0.5)], fx=[label("MONGOLIA · 1200s", 960, 110, 0.0, 60, GOLD)])
    mx, my = frac("m_eurasia", 104, 47)
    out += split(a_, 3.8, "m_eurasia",
                 fx=[pin("m_eurasia", 102.8, 47.2, "Karakorum", 0.1), pin("m_eurasia", 127.0, 37.5, "Korea", 1.2),
                     pin("m_eurasia", 30.5, 50.45, "Kyiv", 2.0, dx=-120), pin("m_eurasia", 19.0, 47.5, "Hungary", 2.8, dx=-170),
                     label("THE LARGEST CONNECTED LAND EMPIRE IN HISTORY", 960, 100, 0.6, 50, GOLD)],
                 camkeys=[(0.0, 1.8, mx, my), (3.6, 1.0, 0.5, 0.5)], name="s00_map")
    L = ["M02"]
    out.append(scene("s00_reach", "m_eurasia", [P("atlas", 1700, G, 1.6, flip=True, faces=[(0, {"brows": 0.6, "mouth": "o"})])], L, lead=H0,
                     follow=False, fx=[route("m_eurasia", [(127, 37.5), (104, 47), (75, 43), (50, 48), (30.5, 50.45), (19, 47.5)], 0.3, 2.6,
                                             color=(230, 120, 40), ship=False)]))
    L = ["M03"]
    out.append(scene("s00_horses", "plate:m_steppe_dawn",
                     [*riders(200, 1030, 4, 230, 1.2, key="rider", walk=(3.6, 160), speed=0.6), P("penny", 1700, G, 1.8, flip=True)],
                     L, lead=H0, follow=False, fx=[FX.no_list(H0, ["GREAT CITIES", "NAVY", "FACTORIES"], [0.0, 1.4, 2.2], "HORSES", 3.6)]))
    L = ["M04"]
    out.append(scene("s00_model", "plate:m_steppe_dawn",
                     [P("zed", 1300, G, 2.0, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(0.3, "think", None)]),
                      *riders(-300, 1020, 1, 200, 1.3, walk=(0.0, 900), speed=1.0)], L, lead=H0, follow=False,
                     cam=[(0.0, 1.15, 0.6, 0.55), (4.0, 1.25, 0.65, 0.55)]))
    L = ["M05"]
    out.append(scene("s01_title", "plate:m_steppe_dawn",
                     [P(k, 420 + i * 270, G, 1.5, faces=[(0, {"mouth": "grin" if k != "pike" else "o"})], acts=[(0.4 + i * 0.1, "wave", 0.6)])
                      for i, k in enumerate(["atlas", "quill", "penny", "zed", "pike"])],
                     L, lead=H0, follow=False, extra=0.6, fx=[FX.title_sting(H0 + 4.4, "How the Mongols Conquered Almost Everything")]))
    # ---- 1. the steppe and Temujin
    L = ["M06"]
    out.append(scene("s02_steppe", "plate:m_steppe_dawn", [*riders(-200, 1010, 3, 260, 1.0, walk=(0.5, 700), speed=0.5), P("penny", 1700, G, 1.6, flip=True)],
                     L, follow=False, fx=[label("THE MONGOLIAN STEPPE · 1100s", 760, 110, 0.4, 58, GOLD)]))
    L = ["M07"]
    out.append(scene("s02_ger", "plate:m_ger_inside",
                     [E("hoelun", 520, 1000, 1.4), E("temujin_boy", 760, 1000, 1.1), P("atlas", 1650, G, 1.7, flip=True)],
                     L, follow=False, fx=[caption("a ger: a round felt tent you can pack onto a cart", 2.0)]))
    L = ["M08", "M09"]
    out.append(scene("s02_temujin", "plate:m_steppe_dawn",
                     [E("hoelun", 500, 1000, 1.4, faces=[(0, {"mouth": "worried"})]), E("temujin_boy", 720, 1000, 1.1, faces=[(0, {"brows": 1.0, "mouth": "worried"})]),
                      P("pike", 1400, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]), P("penny", 1720, G, 1.6, flip=True)],
                     L, fx=[label("TEMUJIN · born around 1162", 620, 300, 0.6, 50, GOLD), caption("his father poisoned, his family abandoned", 6.0, at(L, 1))]))
    L = ["M10"]
    out.append(scene("s02_rise", "plate:m_steppe_dawn",
                     [E("temujin", 700, 1000, 1.6, faces=[(0, {"mouth": "smirk", "brows": -0.3})], acts=[(1.0, "point", None)]),
                      *riders(-1100, 1030, 5, 180, 1.0, walk=(1.5, 1100), speed=1.4), P("penny", 1720, G, 1.5, flip=True)],
                     L, follow=False, fx=[caption("rivals defeated... and absorbed into his people", 5.0)]))
    L = ["M11"]
    out.append(scene("s02_khan", "plate:m_steppe_dawn",
                     [E("genghis", 960, 1000, 1.8, faces=[(0, {"mouth": "grin", "brows": -0.3})], acts=[(0.8, "present", None)]),
                      *FX.people(W_, ["rider", "rider2", "archer"], 250, 1010, 140, 1.0, acts=[(1.4, "cheer", None)]),
                      *FX.people(W_, ["rider2", "rider", "archer"], 1250, 1010, 140, 1.0, flip=True, acts=[(1.4, "cheer", None)]),
                      P("quill", 1800, G + 20, 1.4, flip=True)],
                     L, follow=False, fx=[label("1206 · CHINGGIS KHAN", 960, 110, 0.4, 70, GOLD)]))
    # ---- 2. the army
    L = ["M12"]
    out.append(scene("s03_odds", "card", [P("penny", 1720, G, 1.6, flip=True)], L,
                     fx=[FX.bars(0.6, [("Mongols (perhaps)", 1.0, (200, 70, 50)), ("Jin China", 40.0, (90, 120, 170))], unit="")], follow=False))
    L = ["M13"]
    out.append(scene("s03_tens", "card", [P("zed", 1720, G, 1.6, flip=True)], L, fx=[decimal(0.3)], follow=False))
    L = ["M14"]
    out.append(scene("s03_remounts", "plate:m_steppe_dawn",
                     [*riders(-900, 1000, 3, 300, 1.15, walk=(0.0, 2400), speed=1.8), *FX.people(W_, ["rider2_mounted"] * 3, -700, 1040, 260, 1.0, walk=(0.0, 2200),
                                                                                               speed=1.8),
                      P("atlas", 1720, G, 1.7, flip=True)],
                     L, follow=False, fx=[caption("several horses per rider: always a fresh one", 1.0)]))
    L = ["M15", "M16", "M17"]
    turn = at(L, 2) + 1.4
    out.append(scene("s03_retreat", "plate:m_mohi",
                     [*riders(900, 900, 4, 120, 0.7, walk=(at(L, 1) - 0.6, 700), speed=2.0),
                      *riders(200, 940, 4, 120, 0.7, key="knight", walk=(at(L, 1), 900), speed=2.0),
                      P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "o"})]), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[caption("composite bows, from the saddle", 1.0, at(L, 1)), caption("the feigned retreat", at(L, 1)),
                            arrows_volley(1600, 700, 1150, 760, turn)], follow=False))
    L = ["M18"]
    a_ = scene("s03_merit", "plate:m_karakorum", [P("quill", 1720, G, 1.6, flip=True), E("rider", 600, 1000, 1.4, acts=[(1.0, "nod", None)])], L,
               follow=False, fx=[caption("promotion by ability, not just birth", 1.0)])
    out += split(a_, 5.2, "plate:m_caravan", actors=riders(-400, 1010, 1, 200, 1.4, walk=(0.0, 2400), speed=2.6),
                 fx=[label("THE YAM: RELAY STATIONS ACROSS THE EMPIRE", 960, 110, 0.2, 54, GOLD)], name="s03_yam")
    # ---- 3. China
    L = ["M19"]
    out.append(scene("s04_jin", "plate:m_zhongdu", [*FX.people(W_, ["jin"] * 4, 300, 1000, 150, 1.0), P("penny", 1720, G, 1.6, flip=True)], L,
                     follow=False, fx=[label("THE JIN DYNASTY · NORTHERN CHINA", 760, 110, 0.4, 56, GOLD)]))
    L = ["M20", "M21"]
    out.append(scene("s04_siege", "plate:m_zhongdu",
                     [*riders(200, 1030, 3, 200, 1.1), P("atlas", 1400, G, 1.7, flip=True, acts=[(0.6, "shrug", None)]), E("jin_official", 980, 1000, 1.3)],
                     L, fx=[caption("engineers recruited from conquered lands: siege engines", at(L, 1) + 1.0)]))
    L = ["M22"]
    out.append(scene("s04_zhongdu", "plate:m_zhongdu", [P("quill", 1720, G, 1.6, flip=True)], L, follow=False,
                     fx=[label("ZHONGDU · 1215", 760, 110, 0.4, 70, GOLD), caption("today its ruins lie inside Beijing", 9.0)]))
    # ---- 4. Khwarazm
    L = ["M23"]
    out.append(scene("s05_khwarazm", "m_ca", [P("penny", 1720, G, 1.6, flip=True)], L, follow=False,
                     fx=[pin("m_ca", 64.42, 39.77, "Bukhara", 1.4), pin("m_ca", 66.96, 39.65, "Samarkand", 2.2), pin("m_ca", 60.36, 41.55, "Urgench", 3.0),
                         label("THE KHWARAZMIAN EMPIRE", 760, 100, 0.4, 62, GOLD)]))
    L = ["M24"]
    out.append(scene("s05_caravan", "plate:m_caravan",
                     [*FX.people(W_, [MK["camel"], "merchant", MK["camel"]], -500, 1010, 260, 1.1, walk=(0.2, 900), speed=0.5),
                      P("zed", 1720, G, 1.6, flip=True)], L, follow=False, fx=[label("1218 · A TRADE CARAVAN", 760, 110, 0.4, 60, GOLD)]))
    L = ["M25", "M26"]
    out.append(scene("s05_otrar", "plate:m_bukhara",
                     [E("governor", 520, 1000, 1.5, faces=[(0, {"brows": -0.8, "mouth": "smirk"})]), E("shah", 820, 1000, 1.6, acts=[(5.0, "fold", None)]),
                      P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "o"})]), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[label("OTRAR · 1218", 520, 300, 0.4, 56, GOLD), label("THE SHAH", 820, 300, 4.6, 50, (255, 236, 190))]))
    L = ["M27"]
    out.append(scene("s05_campaign", "m_ca", [P("penny", 1720, G, 1.5, flip=True)], L, follow=False,
                     fx=[pin("m_ca", 68.3, 42.85, "Otrar 1219", 0.3), pin("m_ca", 64.42, 39.77, "Bukhara 1220", 1.6, dx=-270),
                         pin("m_ca", 66.96, 39.65, "Samarkand 1220", 2.8), pin("m_ca", 61.84, 37.66, "Merv 1221", 4.0),
                         label("1219–1221", 420, 110, 0.4, 70, GOLD)]))
    L = ["M28"]
    out.append(scene("s05_ruin", "plate:m_bukhara", [P("quill", 1720, G, 1.6, flip=True)], L, follow=False,
                     fx=[caption("historians argue about the numbers; the destruction was real", 6.0)]))
    # ---- 5. after Genghis: Europe
    L = ["M29"]
    out.append(scene("s06_1227", "card", [P("penny", 1720, G, 1.6, flip=True)], L,
                     fx=[timeline([("1227", "Genghis Khan|dies"), ("1229", "Ogedei becomes|Great Khan"), ("1230s", "the empire keeps|expanding")], 0.5, 2.0)],
                     follow=False))
    L = ["M30"]
    out.append(scene("s06_ogedei", "plate:m_karakorum", [E("ogedei", 760, 1000, 1.7, acts=[(1.0, "present", None)]), P("atlas", 1700, G, 1.7, flip=True)],
                     L, follow=False, fx=[label("OGEDEI · GREAT KHAN", 760, 300, 0.6, 56, GOLD)]))
    L = ["M31"]
    out.append(scene("s06_mohi", "plate:m_mohi",
                     [*riders(-600, 960, 5, 170, 0.85, walk=(0.4, 900), speed=1.6), *riders(1500, 980, 4, 160, 0.85, key="knight", flip=True),
                      P("quill", 1780, G + 20, 1.4, flip=True)],
                     L, follow=False, fx=[label("LEGNICA · 9 APRIL 1241", 760, 110, 0.4, 56, GOLD), label("MOHI · 11 APRIL 1241", 760, 190, 4.0, 56, GOLD),
                                          arrows_volley(500, 700, 1300, 760, 2.0)]))
    L = ["M32", "M33"]
    out.append(scene("s06_turn", "m_europe",
                     [P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, follow=False, fx=[route("m_europe", [(60, 52), (45, 55), (35, 52), (24, 51), (16.16, 51.21)], 0.2, 1.6, color=(230, 120, 40), ship=False),
                                          route("m_europe", [(20.9, 47.95), (30, 47), (45, 48), (55, 50)], at(L, 1) + 2.0, at(L, 1) + 5.0,
                                                color=(120, 200, 120), ship=False),
                                          caption("1242: the armies turn back", at(L, 1) + 0.5)]))
    # ---- 6. running an empire
    L = ["X01", "X02"]
    out.append(scene("s07_karakorum", "plate:m_karakorum",
                     [*FX.people(W_, ["merchant", "rubruck", "scholar"], 200, 1000, 210, 1.2, walk=(0.5, 250), speed=0.5),
                      P("penny", 1400, G, 1.6, flip=True), P("atlas", 1720, G, 1.7, flip=True)],
                     L, fx=[label("KARAKORUM · THE MONGOL CAPITAL", 760, 100, 0.4, 58, GOLD), caption("a walled town of palaces, markets and temples", 4.0)]))
    L = ["X03"]
    out.append(scene("s07_paiza", "card", [P("zed", 1720, G, 1.6, flip=True)], L, fx=[paiza(0.6)], follow=False))
    L = ["X04"]
    out.append(scene("s07_faiths", "plate:m_karakorum", [*FX.people(W_, ["rubruck", "scholar", "jin_official", "merchant"], 250, 1000, 220, 1.2),
                                                         P("quill", 1720, G, 1.6, flip=True)],
                     L, follow=False, fx=[caption("Buddhists · Christians · Muslims · Taoists", 1.0)]))
    L = ["X05"]
    a_ = scene("s07_sorghaghtani", "plate:m_ger_inside",
               [E("sorghaghtani", 760, 1000, 1.7, faces=[(0, {"mouth": "smile"})], acts=[(1.2, "present", None)]), P("penny", 1720, G, 1.6, flip=True)],
               L, follow=False, fx=[label("SORGHAGHTANI BEKI", 760, 300, 0.6, 54, GOLD)])
    out += split(a_, 7.6, "card", actors=[P("penny", 1720, G, 1.5, flip=True)],
                 fx=[FX.family(0.2, "Sorghaghtani Beki", [("Mongke", "Great Khan"), ("Kublai", "Great Khan"), ("Hulagu", "ruled Persia"),
                                                          ("Ariq Boke", "")], step=1.6)], name="s07_sons")
    L = ["X06", "X07"]
    out.append(scene("s07_mum", "plate:m_ger_inside", [P("pike", 1300, G, 1.9, flip=True, faces=[(0, {"mouth": "grin"})]), P("penny", 1700, G, 1.6, flip=True)],
                     L, follow=False))
    # ---- 7. Baghdad, Ain Jalut, Japan
    L = ["M34"]
    out.append(scene("s08_hulagu", "plate:m_baghdad", [E("hulagu", 600, 1000, 1.6, acts=[(1.4, "point", None)]), *riders(-300, 1030, 2, 200, 1.0),
                                                     P("penny", 1720, G, 1.6, flip=True)],
                     L, follow=False, fx=[label("BAGHDAD · SEAT OF THE ABBASID CALIPHS", 760, 100, 0.4, 54, GOLD)]))
    L = ["M35"]
    out.append(scene("s08_1258", "plate:m_baghdad", [E("caliph", 700, 1000, 1.5, faces=[(0, {"mouth": "worried"})]), P("quill", 1720, G, 1.6, flip=True)],
                     L, follow=False, fx=[label("1258", 760, 110, 0.3, 90, GOLD)]))
    L = ["M36"]
    out.append(scene("s08_ainjalut", "m_levant",
                     [*riders(150, 980, 4, 150, 0.8), *riders(1100, 980, 5, 150, 0.8, key="mamluk", flip=True), P("penny", 1780, G, 1.4, flip=True)],
                     L, follow=False, fx=[pin("m_levant", 35.36, 32.55, "Ain Jalut · 1260", 0.6), label("THE MAMLUKS OF EGYPT WIN", 760, 110, 3.6, 56, GOLD)]))
    L = ["M37", "M38"]
    out.append(scene("s08_japan", "plate:m_hakata",
                     [E("samurai", 600, 1000, 1.5, acts=[(1.0, "present", None)]),
                      P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "grin"})], acts=[(at(L, 1), "celebrate", 0.4)]),
                      P("atlas", 1750, G + 10, 1.6, flip=True)],
                     L, fx=[label("HAKATA BAY, JAPAN · 1274 AND 1281", 760, 100, 0.4, 54, GOLD), K.PL_rain]))
    # ---- 8. Kublai and the khanates
    L = ["M39"]
    out.append(scene("s09_kublai", "plate:m_dadu_hall", [E("kublai", 820, 1000, 1.8, faces=[(0, {"mouth": "grin"})], acts=[(1.0, "present", None)]),
                                                       P("penny", 1720, G, 1.6, flip=True)],
                     L, follow=False, fx=[label("KUBLAI KHAN · YUAN DYNASTY, 1271", 760, 100, 0.4, 56, GOLD)]))
    L = ["X08"]
    out.append(scene("s09_money", "card", [P("zed", 1720, G, 1.6, flip=True)], L, fx=[paper_money(0.5)], follow=False))
    L = ["X09"]
    out.append(scene("s09_marco", "plate:m_dadu_hall",
                     [E("kublai", 1100, 1000, 1.6, flip=True), E("marco", -200, 1000, 1.5, walks=[(0.3, 700)], speed=1.5, acts=[(3.0, "present", None)]),
                      P("quill", 1720, G, 1.6, flip=True)],
                     L, fx=[label("MARCO POLO", 700, 300, 1.5, 52, GOLD), caption("how much is true? historians still debate", 8.0)]))
    L = ["M40"]
    out.append(scene("s09_size", "card", [P("zed", 1720, G, 1.6, flip=True)], L, follow=False,
                     fx=[FX.bars(0.8, [("Mongol Empire (peak)", 23.5, (200, 70, 50)), ("North America", 24.7, (90, 120, 170))], unit="{:.1f}M km²")]))
    L = ["M41"]
    out.append(scene("s09_khanates", "m_eurasia", [P("penny", 1720, G, 1.5, flip=True)], L, follow=False,
                     fx=[pin("m_eurasia", 50, 52, "Golden Horde", 1.6, (200, 160, 40)), pin("m_eurasia", 72, 42, "Chagatai Khanate", 2.6, (60, 140, 90)),
                         pin("m_eurasia", 52, 33, "Ilkhanate", 3.6, (60, 100, 180)), pin("m_eurasia", 112, 36, "Yuan dynasty", 4.6, (200, 60, 50)),
                         caption("the four khanates (approximate centres)", 1.2)]))
    L = ["M42"]
    out.append(scene("s09_caravan", "plate:m_caravan",
                     [*FX.people(W_, [MK["camel"], "merchant", MK["camel"], "marco"], -700, 1010, 240, 1.1, walk=(0.2, 1100), speed=0.6),
                      P("quill", 1720, G, 1.6, flip=True)], L, follow=False, fx=[label("THE SILK ROADS", 760, 110, 0.4, 66, GOLD)]))
    L = ["M43"]
    out.append(scene("s09_silk", "m_eurasia", [P("zed", 1720, G, 1.5, flip=True)], L, follow=False,
                     fx=[route("m_eurasia", SILK[::-1], 0.3, 4.0, color=(240, 200, 80), ship=False)]))
    # ---- 9. the end of the empire and its legacy
    L = ["M44"]
    out.append(scene("s10_1368", "card", [P("penny", 1720, G, 1.6, flip=True)], L,
                     fx=[timeline([("1300s", "the khanates|weaken"), ("1368", "the Ming drive|the Yuan out of China")], 0.5, 2.4)], follow=False))
    L = ["M45"]
    a_ = scene("s10_legacy", "plate:m_caravan", [P("quill", 1720, G, 1.6, flip=True)], L, follow=False,
               fx=[caption("people, ideas, goods...", 1.0)])
    out += split(a_, 6.2, "m_eurasia", actors=[P("quill", 1720, G, 1.5, flip=True)],
                 fx=[caption("...and, many historians believe, the Black Death", 0.3),
                     route("m_eurasia", [(75, 43), (50, 48), (34, 45), (15, 42), (2, 47)], 0.3, 5.0, color=(150, 40, 40), ship=False)], name="s10_plague")
    # ---- ending: payoff, then the tease cuts to next week's world while Penny keeps talking
    L = ["M46"]
    out.append(scene("s11_payoff", "plate:m_steppe_dawn",
                     [E("temujin_boy", 600, 1000, 1.1), *riders(-900, 1040, 5, 200, 1.05, walk=(1.5, 2600), speed=1.6), P("atlas", 1720, G, 1.6, flip=True)],
                     L, follow=False, cam=[(0.0, 1.15, 0.4, 0.55), (6.0, 1.0, 0.5, 0.5)]))
    L = ["M47"]
    a_ = scene("s11_outro", "plate:m_steppe_dawn",
               [P(k, 300 + i * 330, G, 1.6, flip=i > 2, faces=[(0, {"mouth": "grin"})], acts=[(0.4 + i * 0.12, "cheer", None)])
                for i, k in enumerate(["atlas", "penny", "quill", "zed", "pike"])], L, lead=0.2, follow=False)
    out += split(a_, 2.2, "plate:e_spice_quay", fx=[FX.next_time(0.3, "THE EAST INDIA COMPANY")],
                 camkeys=None, name="s11_next")
    out[-1].dur += 0.8
    out.append(Shot("s12_endcard", 3.5, "endcard",
                    actors=[P(k, 360 + i * 300, 1030, 1.4, acts=[(0.3 + i * 0.12, "cheer" if k != "quill" else "hold_up", None)])
                            for i, k in enumerate(["penny", "atlas", "quill", "zed", "pike"])]))
    return out


K.shots = shots                                                                  # the engine's preview/render/mix use this episode

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if cmd == "preview":
        K.preview(Path(sys.argv[2]) if len(sys.argv) > 2 else Path("D:/Temp/cartoon/ep02/preview.png"))
    elif cmd == "render":
        K.render(tuple(int(x) for x in sys.argv[2].split("/")), Path(sys.argv[3]) if len(sys.argv) > 3 else Path("D:/Temp/cartoon/ep02/shots"))
    elif cmd == "mix":
        K.mix(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]) if len(sys.argv) > 4 else Path("D:/Temp/cartoon/sneaky_snitch.mp3"))
