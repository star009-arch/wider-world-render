"""Tiny Empires episode 2: "How the Mongols Conquered Almost Everything" (~8.5 min). Engine: ep01.py (scene builder, maps, fx).

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

K.EP = K.ROOT / "projects/tiny-empires/ep02"
K.VOICE = Path(os.environ.get("TE_VOICE", "D:/Temp/cartoon/ep02/voice"))
K.LINES = {ln["id"]: ln for ln in json.loads((K.EP / "lines.json").read_text(encoding="utf-8"))["lines"]}
K.DUR = json.loads((K.VOICE / "durations.json").read_text()) if (K.VOICE / "durations.json").exists() else {}
K.MAPS.update({"m_ca": (50, 32, 76, 46), "m_europe": (8, 38, 62, 60), "m_eurasia": (-12, 8, 146, 68)})
for k in ("m_ca", "m_europe", "m_eurasia"):
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
            K.S_text(d, 960, 860, "Yuan paper money", 60, anchor="mm", color=(255, 224, 140))
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
def shots():
    K.CUES.clear()
    out = []
    L = ["M01", "M02", "M03", "M04", "M05"]
    out.append(scene("s01_hook", "plate:eurasia",
                     [P("penny", 960, G, 2.0, faces=[(0, {"brows": -0.3, "mouth": "smirk"})], acts=[(0.0, "jump", 0.0)]),
                      P("atlas", -200, G, 1.7, walks=[(at(L, 1) - 1.2, 420)], speed=1.6, faces=[(0, {"brows": 0.6, "mouth": "o"})]),
                      P("zed", 2150, G, 1.7, flip=True, walks=[(at(L, 3) - 1.2, 1520)], speed=1.8, faces=[(0, {"mouth": "grin"})])],
                     L, fx=[caption("TINY EMPIRES", at(L, 4) + 2.0)]))
    L = ["M06", "M07"]
    out.append(scene("s02_steppe", "plate:steppe", [P("penny", 1650, G, 1.6, flip=True), P("atlas", 400, G, 1.7)], L,
                     fx=[label("THE MONGOLIAN STEPPE · 1100s", 960, 90, 0.4, 60, (255, 230, 150))]))
    L = ["M08", "M09"]
    out.append(scene("s02_temujin", "plate:camp",
                     [P("temujin", 760, 1000, 1.2, faces=[(0, {"brows": 1.0, "mouth": "worried"})]),
                      P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[label("TEMUJIN · born around 1162", 760, 300, 0.6, 52, (255, 230, 150))]))
    L = ["M10"]
    out.append(scene("s02_rise", "plate:steppe",
                     [P("temujin", -150, 990, 1.5, walks=[(0.4, 900)], speed=1.4, faces=[(0, {"mouth": "smirk", "brows": -0.3})]),
                      *army("mongol", -900, 1000, 6, 2, 120, 28, 0.9, walk=(1.2, 1100), speed=1.4), P("penny", 1720, G, 1.5, flip=True)],
                     L, follow=False))
    L = ["M11"]
    out.append(scene("s02_khan", "plate:steppe",
                     [P("genghis", 960, 960, 1.8, faces=[(0, {"mouth": "grin", "brows": -0.3})], acts=[(0.8, "present", None)]),
                      *army("mongol", 300, 1010, 4, 1, 140, 0, 0.9, acts=[(1.4, "cheer", None)]),
                      *army("mongol", 1300, 1010, 4, 1, 140, 0, 0.9, flip=True, acts=[(1.4, "cheer", None)]),
                      P("quill", 1780, G + 20, 1.5, flip=True)],
                     L, fx=[label("1206 · CHINGGIS KHAN", 960, 110, 0.4, 70, (255, 214, 120))], follow=False))
    L = ["M12", "M13"]
    out.append(scene("s03_tens", "card", [P("zed", 1700, G, 1.6, flip=True), P("penny", 1450, G + 10, 1.4, flip=True)], L,
                     fx=[decimal(at(L, 1) + 0.3)], follow=False))
    L = ["M14"]
    out.append(scene("s03_horses", "plate:steppe", [P("atlas", 1650, G, 1.7, flip=True)], L,
                     fx=[caption("several horses per rider", 0.8)], follow=False))
    L = ["M15", "M16", "M17"]
    turn = at(L, 2) + 1.4
    out.append(scene("s03_retreat", "plate:plassey",
                     [*army("mongol", 900, 760, 4, 2, 90, 40, 0.75, walk=(at(L, 1) - 0.6, 700), speed=2.0),
                      *army("knight", 200, 800, 4, 2, 90, 40, 0.75, walk=(at(L, 1), 900), speed=2.0),
                      P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "o"})]), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[caption("the feigned retreat", at(L, 1)), arrows_volley(1600, 700, 1150, 760, turn)], follow=False))
    L = ["M18"]
    out.append(scene("s03_relay", "plate:mongolia", [P("quill", 1700, G, 1.6, flip=True)], L,
                     fx=[caption("promotion by ability  ·  relay stations across the empire", 0.6)], follow=False))
    L = ["M19", "M20", "M21"]
    out.append(scene("s04_jin", "plate:fort",
                     [*army("jin", 500, 760, 6, 1, 110, 0, 0.6), P("atlas", 1450, G, 1.8, flip=True), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[label("THE JIN DYNASTY · NORTHERN CHINA", 960, 90, 0.4, 56, (255, 230, 150)),
                            caption("siege engineers recruited from conquered lands", at(L, 2) + 0.4)]))
    L = ["M22"]
    out.append(scene("s04_zhongdu", "plate:hall", [P("quill", 1700, G, 1.6, flip=True)], L,
                     fx=[label("ZHONGDU · 1215", 960, 100, 0.4, 70, (255, 214, 120))], follow=False))
    L = ["M23"]
    out.append(scene("s05_khwarazm", "plate:centralasia", [P("penny", 1700, G, 1.6, flip=True)], L,
                     fx=[label("THE KHWARAZMIAN EMPIRE", 960, 100, 0.6, 66, (255, 220, 120))], follow=False))
    L = ["M24", "M25", "M26"]
    out.append(scene("s05_otrar", "plate:city",
                     [P("shah", 620, 980, 1.5, faces=[(0, {"brows": -0.8, "mouth": "smirk"})], acts=[(at(L, 1) + 1.0, "fold", None)]),
                      P("zed", 1150, G, 1.6, flip=True), P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "o"})]),
                      P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[label("OTRAR · 1218", 400, 110, 0.4, 64, (255, 230, 150))]))
    L = ["M27", "M28"]
    out.append(scene("s05_campaign", "m_ca", [P("quill", 1720, G, 1.5, flip=True)], L,
                     fx=[pin("m_ca", 68.3, 42.85, "Otrar", 0.3), pin("m_ca", 64.42, 39.77, "Bukhara 1220", 1.4, dx=-270),
                         pin("m_ca", 66.96, 39.65, "Samarkand 1220", 2.6), pin("m_ca", 61.84, 37.66, "Merv 1221", 3.8),
                         label("1219–1221", 420, 110, 0.4, 70, (255, 214, 120))], follow=False))
    L = ["M29"]
    out.append(scene("s06_1227", "card", [P("penny", 1700, G, 1.6, flip=True)], L,
                     fx=[timeline([("1227", "Genghis Khan|dies"), ("1229", "Ogedei becomes|Great Khan"), ("1230s", "the empire keeps|expanding")], 0.5, 2.0)],
                     follow=False))
    L = ["M30", "M31", "M32", "M33"]
    out.append(scene("s06_europe", "m_europe",
                     [P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[route("m_europe", [(60, 52), (45, 55), (35, 52), (24, 51), (16.16, 51.21)], 0.6, at(L, 1), color=(230, 120, 40), ship=False),
                            pin("m_europe", 16.16, 51.21, "Legnica · 9 Apr 1241", at(L, 1) + 0.3),
                            pin("m_europe", 20.9, 47.95, "Mohi · 11 Apr 1241", at(L, 1) + 1.6),
                            caption("1242: the armies turn back", at(L, 3))], follow=False))
    L = ["X01", "X02"]
    out.append(scene("s07b_karakorum", "plate:steppe", [P("penny", 1700, G, 1.6, flip=True), P("atlas", 420, G, 1.7)], L,
                     fx=[label("KARAKORUM · THE MONGOL CAPITAL", 960, 90, 0.4, 60, (255, 230, 150))]))
    L = ["X03"]
    out.append(scene("s07b_paiza", "card", [P("zed", 1700, G, 1.6, flip=True)], L, fx=[paiza(0.6)], follow=False))
    L = ["X04"]
    out.append(scene("s07b_faiths", "plate:durbar", [P("quill", 1700, G, 1.6, flip=True)], L,
                     fx=[caption("Buddhists · Christians · Muslims · Taoists", 0.8)], follow=False))
    L = ["X05", "X06", "X07"]
    out.append(scene("s07b_sorghaghtani", "plate:hall",
                     [P("sorghaghtani", 820, 990, 1.6, faces=[(0, {"mouth": "smile"})], acts=[(1.2, "present", None)]),
                      P("pike", 1450, G, 1.8, flip=True), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[label("SORGHAGHTANI BEKI", 820, 300, 0.6, 52, (255, 230, 150)), caption("mother of Mongke, Kublai, Hulagu and Ariq Boke", 2.4, at(L, 1))]))
    L = ["M34", "M35"]
    out.append(scene("s07_baghdad", "plate:city",
                     [P("hulagu", 700, 980, 1.6, faces=[(0, {"mouth": "smirk"})], acts=[(1.4, "point", None)]),
                      *army("mongol", 200, 1000, 3, 1, 120, 0, 0.9), P("quill", 1720, G, 1.6, flip=True)],
                     L, fx=[label("BAGHDAD · 1258", 960, 100, 0.4, 70, (255, 214, 120))]))
    L = ["M36"]
    out.append(scene("s07_ainjalut", "plate:plassey",
                     [*army("mongol", 150, 740, 4, 2, 80, 40, 0.65), *army("mamluk", 1000, 720, 7, 3, 80, 36, 0.65, flip=True),
                      P("penny", 1740, G, 1.5, flip=True)],
                     L, fx=[label("AIN JALUT · 1260", 960, 100, 0.4, 70, (255, 214, 120))], follow=False))
    L = ["M37", "M38"]
    out.append(scene("s07_japan", "plate:storm",
                     [P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "grin"})], acts=[(at(L, 1), "celebrate", 0.4)]),
                      P("atlas", 1750, G + 10, 1.6, flip=True)],
                     L, fx=[label("JAPAN · 1274 AND 1281", 760, 100, 0.4, 66, (255, 214, 120)), K.PL_rain]))
    L = ["M39", "M40"]
    out.append(scene("s08_kublai", "plate:hall",
                     [P("kublai", 820, 980, 1.7, faces=[(0, {"mouth": "grin"})], acts=[(1.0, "present", None)]), P("zed", 1450, G, 1.7, flip=True),
                      P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, fx=[label("KUBLAI KHAN · YUAN DYNASTY, 1271", 960, 90, 0.4, 60, (255, 230, 150))]))
    L = ["M41"]
    out.append(scene("s08_khanates", "m_eurasia", [P("penny", 1720, G, 1.5, flip=True)], L,
                     fx=[pin("m_eurasia", 50, 52, "Golden Horde", 1.6, (200, 160, 40)), pin("m_eurasia", 72, 42, "Chagatai Khanate", 2.6, (60, 140, 90)),
                         pin("m_eurasia", 52, 33, "Ilkhanate", 3.6, (60, 100, 180)), pin("m_eurasia", 112, 36, "Yuan dynasty", 4.6, (200, 60, 50)),
                         caption("the four khanates (approximate centres)", 1.2)], follow=False))
    L = ["X08"]
    out.append(scene("s08_money", "card", [P("zed", 1700, G, 1.6, flip=True)], L, fx=[paper_money(0.5)], follow=False))
    L = ["X09"]
    out.append(scene("s08_marco", "plate:hall",
                     [P("kublai", 1100, 980, 1.6, flip=True), P("marco", -200, 990, 1.5, walks=[(0.3, 700)], speed=1.5, acts=[(3.0, "present", None)]),
                      P("quill", 1720, G, 1.6, flip=True)],
                     L, fx=[label("MARCO POLO", 700, 300, 1.5, 52, (255, 230, 150))]))
    L = ["M42", "M43"]
    out.append(scene("s08_silk", "m_eurasia", [P("zed", 1720, G, 1.5, flip=True), P("quill", 1500, G + 10, 1.4, flip=True)], L,
                     fx=[route("m_eurasia", SILK[::-1], 0.6, at(L, 1) + 1.0, color=(240, 200, 80), ship=False),
                         label("THE SILK ROADS", 760, 100, 0.4, 66, (255, 214, 120))], follow=False))
    L = ["M44"]
    out.append(scene("s09_1368", "card", [P("penny", 1700, G, 1.6, flip=True)], L,
                     fx=[timeline([("1300s", "the khanates|weaken"), ("1368", "the Ming drive|the Yuan out of China")], 0.5, 2.4)], follow=False))
    L = ["M45"]
    out.append(scene("s09_legacy", "plate:eurasia", [P("quill", 1700, G, 1.6, flip=True)], L,
                     fx=[caption("people, ideas, goods... and disease", 1.0)], follow=False))
    L = ["M46", "M47"]
    out.append(scene("s09_outro", "plate:mongolia",
                     [P(k, 300 + i * 330, G, 1.6, flip=i > 2, faces=[(0, {"mouth": "grin" if k != "pike" else "worried"})])
                      for i, k in enumerate(["atlas", "penny", "quill", "zed", "pike"])], L, extra=0.8))
    out.append(Shot("s10_endcard", 3.5, "endcard",
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
