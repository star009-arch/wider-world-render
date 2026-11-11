"""Tiny Empires pilot (~70 s): "How a company ended up running a country" — Bengal, 1756–1757.

  python scripts/cartoon/pilot.py preview            contact sheet of every shot
  python scripts/cartoon/pilot.py render [i/k]       silent shots to D:/Temp/cartoon/pilot/shots (part i of k)
  python scripts/cartoon/pilot.py mix                dialogue + music + effects -> D:/Temp/cartoon/pilot/pilot.mp4

Dialogue: projects/tiny-empires/pilot/lines.json, recorded by pilot_voice.py (durations + Rhubarb lip-sync).
Facts (two sources each, see pilot_script_v1.md): Calcutta taken June 1756, retaken by Clive 2 Jan 1757; secret
agreement with Mir Jafar; Plassey 23 June 1757; about 3,000 vs about 50,000; rain: Company covered its powder with
tarpaulins, the Nawab's guns fell largely silent; Mir Jafar's troops stayed out; Mir Jafar made Nawab, the Company the
real power; that was Bengal, not India.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402
import pilot_sets as PS  # noqa: E402
import scene as SC  # noqa: E402
import sets as S  # noqa: E402
from scene import Shot, ease, fx_label  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VOICE = Path("D:/Temp/cartoon/pilot/voice")
OUTD = Path("D:/Temp/cartoon/pilot")
DUR = json.loads((VOICE / "durations.json").read_text()) if (VOICE / "durations.json").exists() else {}
LINES = {ln["id"]: ln for ln in json.loads((ROOT / "projects/tiny-empires/pilot/lines.json").read_text(encoding="utf-8"))["lines"]}
for k in PS.SETS:                                                               # register the pilot sets with the scene engine
    SC._BG[k] = PS.SETS[k]().convert("RGBA")
SC._BG["endcard"] = PS.endcard().convert("RGBA")

CUES: list = []                                                                 # (shot index, line id, start in shot) for the mix


def lips(line, t0):
    return M.load_rhubarb(VOICE / f"{line}_lips.json", offset=t0)


def P(key, x, ground, s=2.0, **kw):
    return M.Performer(key, x=x, ground=ground, scale=s, **kw)


def label(text, x, y, t0, size=72, color=(255, 255, 255), t1=99):
    return lambda t, d, f: fx_label(d, text, x, y, size, color, a=min(ease((t - t0) / 0.3), ease((t1 - t) / 0.3))) if t0 <= t < t1 else None


def flag_fx(x, y, t_swap, s=2.2):
    def f(t, d, frame):
        kind = "nawab" if t < t_swap else "company"
        k = min(1.0, abs(t - t_swap) / 0.25)                                    # quick dip-and-raise at the swap
        S.flag(d, x, y + (1 - k) * 60 * s, kind, s, wave=t * 4)
    return f


def drips(x, y, t0, t1):
    def f(t, d, frame):
        if not t0 <= t < t1:
            return
        for k in range(7):
            ph = (t * 1.6 + k * 0.37) % 1.0
            xx = x + (k - 3) * 34
            yy = y + ph * 160
            d.ellipse([xx - 7, yy - 10, xx + 7, yy + 10], fill=(110, 170, 230, int(255 * (1 - ph))))
    return f


def coins(x, y, t0, t1):
    def f(t, d, frame):
        n = int(18 * ease((t - t0) / max(0.01, t1 - t0)))
        for i in range(n):
            col, row = i % 3, i // 3
            cx, cy = x + col * 110 + (row % 2) * 20, y - row * 30
            d.ellipse([cx - 52, cy - 16, cx + 52, cy + 16], fill=(216, 160, 40, 255), outline=(34, 28, 30, 255), width=4)
            d.ellipse([cx - 40, cy - 10, cx + 40, cy + 6], fill=(240, 196, 70, 255))
    return f


def contract(x0, y, t0, t1, x1=2100):
    """The comically long agreement unrolling across the floor."""
    def f(t, d, frame):
        if t < t0:
            return
        xe = x0 + (x1 - x0) * ease((t - t0) / max(0.01, t1 - t0))
        d.polygon([(x0, y - 50), (xe, y - 10), (xe, y + 40), (x0, y + 10)], fill=(248, 240, 214, 255), outline=(34, 28, 30, 255))
        for k in range(int((xe - x0) / 70)):
            xx = x0 + 40 + k * 70
            d.line([(xx, y - 30 + (xx - x0) * 0.02), (xx + 40, y - 28 + (xx - x0) * 0.02)], fill=(140, 130, 110, 255), width=4)
            if k % 4 == 3:
                d.line([(xx, y + 8), (xx + 30, y)], fill=(30, 30, 120, 255), width=4)               # "sign here"
        d.ellipse([xe - 34, y - 20, xe + 34, y + 50], fill=(232, 222, 192, 255), outline=(34, 28, 30, 255), width=4)
    return f


def cannon(x, y, flip, fire_at=(), fizzle_after=99.0):
    def f(t, d, frame):
        k = -1 if flip else 1
        d.polygon([(x, y - 30), (x + k * 150, y - 52), (x + k * 155, y - 22), (x, y)], fill=(60, 60, 66, 255), outline=(20, 20, 24, 255))
        for wx in (x + k * 20, x + k * 80):
            d.ellipse([wx - 32, y - 20, wx + 32, y + 44], fill=(110, 76, 44, 255), outline=(20, 20, 24, 255), width=5)
        for tf in fire_at:
            if tf <= t < tf + 0.6 and tf < fizzle_after:
                r = 30 + (t - tf) * 160
                d.ellipse([x + k * 170 - r, y - 40 - r * 0.7, x + k * 170 + r, y - 40 + r * 0.7], fill=(230, 230, 226, int(220 * (1 - (t - tf) / 0.6))))
        if t >= fizzle_after:                                                   # damp powder: a sad wisp
            ph = (t - fizzle_after) % 1.4
            d.line([(x + k * 150, y - 40), (x + k * 150 + 10 * math.sin(ph * 9), y - 40 - ph * 70)], fill=(200, 200, 200, int(200 * (1 - ph / 1.4))), width=6)
    return f


def tarp(x, y, w, t0):
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 0.35)
        top = y - 560 * k
        d.line([(x - w * 0.42, y), (x - w * 0.42, top)], fill=(110, 76, 44, 255), width=14)
        d.line([(x + w * 0.42, y), (x + w * 0.42, top + 40 * k)], fill=(110, 76, 44, 255), width=14)
        d.polygon([(x - w / 2, top + 60 * k), (x - w * 0.42, top), (x + w * 0.42, top + 40 * k), (x + w / 2, top + 110 * k),
                   (x + w * 0.1, top + 70 * k)], fill=(96, 104, 70, 255), outline=(30, 34, 24, 255))
        for k2 in range(5):                                                     # water running off the edge
            xx = x + w / 2 - 10 - k2 * 18
            yy = top + 110 * k + ((t * 300 + k2 * 40) % 200)
            d.line([(xx, yy), (xx, yy + 20)], fill=(150, 190, 230, 200), width=4)
    return f


def rain_fx(t, d, frame):
    frame.alpha_composite(S.rain_layer(t))


def crown(x, y, t0):
    def f(t, d, frame):
        if t < t0:
            return
        yy = y - 260 * (1 - ease((t - t0) / 0.6))
        d.polygon([(x - 70, yy), (x - 70, yy - 70), (x - 35, yy - 30), (x, yy - 90), (x + 35, yy - 30), (x + 70, yy - 70), (x + 70, yy)],
                  fill=(232, 190, 60, 255), outline=(34, 28, 30, 255))
        d.ellipse([x - 14, yy - 46, x + 14, yy - 18], fill=(190, 30, 50, 255))
    return f


def penny_shadow(x, y, t0, t1):
    """The Company behind the throne: Penny's silhouette (coin and top hat) growing on the wall."""
    def f(t, d, frame):
        if t < t0:
            return
        s = 0.4 + 1.0 * ease((t - t0) / max(0.01, t1 - t0))
        a = int(150 * ease((t - t0) / 0.5))
        r = 230 * s
        d.ellipse([x - r, y - r, x + r, y + r], fill=(30, 18, 30, a))
        d.rectangle([x - 0.5 * r, y - r - 0.95 * r, x + 0.5 * r, y - r + 0.05 * r], fill=(30, 18, 30, a))
        d.rectangle([x - 0.85 * r, y - r - 0.05 * r, x + 0.85 * r, y - r + 0.15 * r], fill=(30, 18, 30, a))
    return f


def sign_card(text, x, y, t0):
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 0.3)
        w, h = 760, 210
        yy = y + (1 - k) * 300
        d.rounded_rectangle([x - w / 2, yy - h / 2, x + w / 2, yy + h / 2], radius=18, fill=(250, 244, 226, 255), outline=(34, 28, 30, 255), width=8)
        lines = text.split("|")
        for i, ln in enumerate(lines):
            d.text((x, yy - 40 + i * 80 - (len(lines) - 2) * 40), ln, font=S.font(58), fill=(150, 30, 30, 255), anchor="mm")
    return f


def army(key, x0, ground, cols, rows, dx, dy, s, flip=False, walk=None, acts=None, speed=1.0):
    out = []
    for r in range(rows):
        for c in range(cols):
            x = x0 + c * dx + (r % 2) * dx / 2
            p = P(key, x, ground + r * dy, s, flip=flip, walks=[(walk[0], x + walk[1])] if walk else [], acts=list(acts or []), speed=speed)
            p.shadow = s > 0.6
            out.append(p)
    return out


# ------------------------------------------------------------------------------------------------ the storyboard
def shots():
    D = DUR
    out = []
    CUES.clear()

    # 1. HOOK: Penny pops up close to camera
    t = 0.55
    CUES.append((len(out), "P01", t))
    out.append(Shot("01_hook", D["P01"] + t + 0.5, "tabletop",
                    actors=[P("penny", 960, 1110, 2.7, lips=lips("P01", t), faces=[(0, {"brows": -0.5, "mouth": "smirk"})],
                              acts=[(0.0, "jump", 0.0), (t + 1.5, "shrug", None)])],
                    camkeys=[(0, 1.1, 0.5, 0.56), (3.5, 1.2, 0.5, 0.56)]))
    # 2. Stampy: "Paperwork." + STAMP
    t = 0.25
    CUES.append((len(out), "P02", t))
    out.append(Shot("02_paperwork", 2.6, "tabletop",
                    actors=[P("stampy", 900, 1090, 2.7, lips=lips("P02", t), faces=[(0, {"mouth": "smirk", "brows": -0.3})],
                              acts=[(1.0, "stamp", None)], props={"prop_l": "stamp"})],
                    camkeys=[(0, 1.12, 0.47, 0.56), (2.6, 1.15, 0.47, 0.56)], shake=[(1.5, 30)]))
    # 3. The five hosts march across the map of Bengal; Pike lags
    t = 0.9
    CUES.append((len(out), "P03", t))
    dur = D["P03"] + t + 0.6
    g = 1010
    out.append(Shot("03_march", dur, "tabletop",
                    actors=[P("atlas", 200, g, 1.7, speed=1.3, walks=[(0.0, 1180)], lips=lips("P03", t), faces=[(0, {"mouth": "smile"})],
                              acts=[(3.6, "present", None)], props={"prop_r": "map"}),
                            P("penny", 0, g + 10, 1.6, speed=1.4, walks=[(0.0, 900)], faces=[(0, {"brows": -0.4, "mouth": "smirk"})]),
                            P("quill", -220, g - 10, 1.6, speed=1.6, walks=[(0.1, 640)], faces=[(0, {"brows": 0.3})], props={"prop_r": "book"}),
                            P("stampy", -440, g, 1.6, speed=1.3, walks=[(0.2, 400)], faces=[(0, {"mouth": "smirk"})], props={"prop_l": "scroll"}),
                            P("pike", -700, g + 15, 1.7, speed=1.5, walks=[(0.9, 140)], faces=[(0, {"brows": 1.0, "mouth": "worried"})],
                              props={"prop_l": "musket"})],
                    camkeys=[(0, 1.0, 0.5, 0.5), (dur, 1.06, 0.55, 0.5)]))
    # 4. Pike trips into the Hooghly
    t = 1.75
    CUES.append((len(out), "P04", t))
    dur = D["P04"] + t + 0.6
    out.append(Shot("04_river", dur, "tabletop",
                    actors=[P("pike", 700, 1080, 2.6, walks=[(0.0, 1000)], faces=[(0, {"brows": 1.0, "mouth": "worried"})],
                              lips=lips("P04", t), acts=[(0.75, "fall", 0.35), (t + 0.2, "flinch", 0.2)], props={"prop_l": "musket"})],
                    fx=[drips(1000, 560, t - 0.1, dur)],
                    camkeys=[(0, 1.35, 0.42, 0.42), (dur, 1.45, 0.5, 0.45)], shake=[(1.1, 16)]))
    # 5. Calcutta: Siraj holds the fort (1756); Clive takes it back (Jan 1757)
    t = 0.6
    CUES.append((len(out), "P05", t))
    dur = D["P05"] + t + 0.9
    sw = t + 4.3
    out.append(Shot("05_calcutta", dur, "fort2",
                    actors=[P("nawab", 1250, 960, 1.6, faces=[(0, {"brows": -0.6, "mouth": "smirk"}), (sw - 0.3, {"brows": 1.0, "mouth": "o"})],
                              acts=[(0.2, "fold", 2.6), (sw - 0.4, "double_take", 0.0)], walks=[(sw + 0.6, 2300)], speed=2.4),
                            P("clive", -250, 980, 1.6, speed=2.2, walks=[(sw - 2.2, 860)], faces=[(0, {"mouth": "grin", "brows": -0.3})],
                              acts=[(sw + 0.2, "point", None)]),
                            *army("csepoy", -800, 990, 3, 1, 150, 0, 1.3, walk=(sw - 2.3, 950), speed=2.2),
                            P("quill", 1700, 1030, 1.9, flip=True, lips=lips("P05", t), faces=[(0, {"brows": 0.4})], acts=[(t + 0.3, "present", None)])],
                    fx=[flag_fx(1600, 30, sw, 2.0), label("1756", 260, 120, 0.3, 90, t1=sw - 0.3), label("JANUARY 1757", 380, 120, sw, 80)],
                    camkeys=[(0, 1.0, 0.5, 0.5), (dur, 1.05, 0.5, 0.5)]))
    # 6. Penny: "Which brings us to... business." Coins pile up
    t = 0.4
    CUES.append((len(out), "P06", t))
    dur = D["P06"] + t + 0.9
    out.append(Shot("06_business", dur, "palace2",
                    actors=[P("penny", 800, 1000, 2.6, lips=lips("P06", t), faces=[(0, {"brows": -0.6, "mouth": "grin"})], acts=[(0.1, "rub", None)])],
                    under=[coins(1150, 960, 0.3, dur - 0.3)],
                    camkeys=[(0, 1.1, 0.48, 0.55), (dur, 1.25, 0.5, 0.58)]))
    # 7. The tent at night: the secret agreement with Mir Jafar; the endless contract
    t = 0.5
    CUES.append((len(out), "P07", t))
    dur = D["P07"] + t + 1.0
    out.append(Shot("07_tent", dur, "tent",
                    actors=[P("mir_jafar", 520, 990, 1.9, faces=[(0, {"brows": 0.2, "mouth": "smirk"}), (t + 3.2, {"brows": 0.8, "mouth": "o"})],
                              acts=[(t + 3.0, "double_take", 0.0)]),
                            P("clive", 1460, 990, 1.9, flip=True, faces=[(0, {"mouth": "smirk", "brows": -0.3})], acts=[(t + 2.0, "present", None)]),
                            P("stampy", 960, 1010, 2.0, lips=lips("P07", t), faces=[(0, {"mouth": "grin"})], acts=[(t + 3.6, "point", None)],
                              props={"prop_l": "seal"})],
                    fx=[label("SECRET AGREEMENT", 960, 120, t + 0.3, 70, (255, 214, 120))],
                    under=[contract(1020, 1000, t + 3.6, dur - 0.2)],
                    camkeys=[(0, 1.0, 0.5, 0.55), (t + 3.4, 1.0, 0.5, 0.55), (dur, 1.12, 0.62, 0.6)]))
    # 8. Plassey, 23 June 1757: a small army faces a huge one
    t = 0.7
    CUES.append((len(out), "P08", t))
    dur = D["P08"] + t + 0.8
    small = army("redcoat", 120, 640, 3, 2, 70, 36, 0.55) + army("csepoy", 150, 712, 4, 2, 70, 36, 0.55)
    big = army("sepoy", 980, 600, 12, 6, 70, 30, 0.5, flip=True)
    out.append(Shot("08_plassey", dur, "plassey",
                    actors=small + big + [P("atlas", 760, 1060, 2.2, lips=lips("P08", t), faces=[(0, {"brows": 0.6, "mouth": "o"})],
                                              acts=[(t + 3.2, "point", 1.0), (t + 5.0, "shrug", None)])],
                    fx=[label("PLASSEY · 23 JUNE 1757", 960, 110, 0.4, 76, (255, 230, 140)),
                        label("about 3,000", 300, 520, t + 3.0, 60), label("about 50,000", 1450, 470, t + 3.6, 60)],
                    camkeys=[(0, 1.12, 0.5, 0.55), (dur, 1.0, 0.5, 0.5)]))
    # 9. Monsoon rain: tarpaulins over the Company's powder; the Nawab's guns fall silent
    t = 0.9
    CUES.append((len(out), "P09", t))
    dur = D["P09"] + t + 0.8
    out.append(Shot("09_rain", dur, "plassey_rain",
                    actors=[P("pike", 520, 1040, 2.2, lips=lips("P09", t), faces=[(0, {"brows": 1.0, "mouth": "worried"})],
                              acts=[(0.3, "cower", None)])],
                    under=[cannon(330, 1000, False), tarp(470, 1060, 640, 0.5), cannon(1500, 900, True, fire_at=(0.4, 1.3), fizzle_after=2.0),
                           cannon(1760, 960, True, fire_at=(0.8,), fizzle_after=2.0)],
                    fx=[rain_fx, label("the Nawab's guns fall silent", 1500, 160, t + 2.6, 54)],
                    camkeys=[(0, 1.0, 0.5, 0.5), (dur, 1.08, 0.4, 0.55)]))
    # 10. Mir Jafar's troops sit it out; Siraj's double take, then he flees
    t = 0.5
    CUES.append((len(out), "P10", t))
    dur = D["P10"] + t + 1.2
    sit = t + 1.6
    troops = army("sepoy", 800, 700, 7, 3, 105, 50, 0.85, flip=True, acts=[(sit, "sit", None)])
    out.append(Shot("10_mir_jafar", dur, "plassey",
                    actors=troops + [P("mir_jafar", 1180, 900, 1.5, flip=True, faces=[(0, {"mouth": "smirk"})], acts=[(sit - 0.2, "fold", None)]),
                                     P("nawab", 560, 930, 1.5, faces=[(0, {"brows": -0.5})], acts=[(sit + 0.8, "double_take", 0.0)],
                                       walks=[(sit + 2.4, -400)], speed=2.4),
                                     P("quill", 1700, 1060, 2.0, flip=True, lips=lips("P10", t), faces=[(0, {"brows": 0.5})])],
                    fx=[label("MIR JAFAR", 1180, 520, 0.4, 56)],
                    camkeys=[(0, 1.0, 0.5, 0.5), (dur, 1.1, 0.45, 0.55)]))
    # 11. Mir Jafar crowned; the Company's shadow (Penny) grows behind the throne
    t = 0.6
    CUES.append((len(out), "P11", t))
    dur = D["P11"] + t + 1.4
    out.append(Shot("11_throne", dur, "palace2",
                    actors=[P("mir_jafar", 960, 890, 1.7, faces=[(0, {"mouth": "grin"}), (t + 1.6, {"brows": 1.0, "mouth": "worried", "look": -0.8})]),
                            P("penny", 1560, 1040, 2.0, flip=True, lips=lips("P11", t), faces=[(0, {"brows": -0.7, "mouth": "smirk"})])],
                    under=[penny_shadow(960, 470, 0.8, dur)],
                    fx=[crown(960, 470, 0.2)],
                    camkeys=[(0, 1.0, 0.5, 0.5), (dur, 1.15, 0.5, 0.45)]))
    # 12. Quill's correction; everyone looks at us
    t = 0.7
    CUES.append((len(out), "P12", t))
    dur = D["P12"] + t + 0.8
    g = 1010
    out.append(Shot("12_actually", dur, "tabletop",
                    actors=[P("atlas", 330, g, 1.8, faces=[(0, {"mouth": "smile"})], acts=[(t + 2.4, "shrug", None)]),
                            P("penny", 640, g + 10, 1.7, faces=[(0, {"brows": -0.4, "mouth": "smirk"})]),
                            P("quill", 960, g - 10, 1.9, lips=lips("P12", t), faces=[(0, {"brows": 0.6})], acts=[(0.15, "hold_up", None)]),
                            P("stampy", 1280, g, 1.7, flip=True, faces=[(0, {"mouth": "smirk"})], acts=[(t + 2.8, "nod", None)]),
                            P("pike", 1590, g + 15, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})], props={"prop_l": "musket"})],
                    fx=[sign_card("NOT all of India.|Just Bengal. For now.", 960, 200, 0.4)],
                    camkeys=[(0, 1.0, 0.5, 0.5), (dur, 1.05, 0.5, 0.52)]))
    # 13. End card
    out.append(Shot("13_end", 3.2, "endcard",
                    actors=[P(k, 360 + i * 300, 1030, 1.5, faces=[(0, {"mouth": "grin" if k != "pike" else "worried"})],
                              acts=[(0.3 + i * 0.12, "cheer" if k != "quill" else "hold_up", None)])
                            for i, k in enumerate(["atlas", "penny", "pike", "quill", "stampy"])]))
    return out


def ffmpeg():
    return SC.ffmpeg()


def preview(out_png):
    from PIL import Image
    ss = shots()
    sheet = Image.new("RGB", (4 * 480, ((len(ss) + 3) // 4) * 270))
    for i, sh in enumerate(ss):
        sheet.paste(SC.render_frame(sh, sh.dur * 0.6).resize((480, 270)), ((i % 4) * 480, (i // 4) * 270))
    sheet.save(out_png)
    print("total", round(sum(s.dur for s in ss), 1), "s")


def render(part=None):
    d = OUTD / "shots"
    d.mkdir(parents=True, exist_ok=True)
    ss = shots()
    for i, sh in enumerate(ss):
        if part and i % part[1] != part[0] - 1:
            continue
        out = d / f"{sh.name}.mp4"
        SC.render_shot(sh, out, threads=2)
        print("rendered", sh.name, flush=True)


def mix():
    """Concatenate shots; place each line; music bed (ducked) and a few synthesised effects; loudness to -14 LUFS."""
    ss = shots()
    starts, acc = [], 0.0
    for sh in ss:
        starts.append(acc)
        acc += sh.dur
    total = acc
    lst = OUTD / "shots.txt"
    lst.write_text("".join(f"file '{(OUTD / 'shots' / (sh.name + '.mp4')).as_posix()}'\n" for sh in ss))
    video = OUTD / "video.mp4"
    subprocess.run([ffmpeg(), "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)],
                   check=True, stdin=subprocess.DEVNULL, timeout=600)
    ff = [ffmpeg(), "-nostdin", "-y", "-loglevel", "error"]
    # pass 1: dialogue bus (every line at its place) -> wav
    ins, flt, labels = [], [], []
    for n, (si, lid, t0) in enumerate(CUES):
        ins += ["-i", str(VOICE / f"{lid}.mp3")]
        ms = int((starts[si] + t0) * 1000)
        flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{n}]")
        labels.append(f"[v{n}]")
    flt.append(f"{''.join(labels)}amix=inputs={len(CUES)}:normalize=0:duration=longest,apad=whole_dur={total:.2f},atrim=0:{total:.2f}[dia]")
    bus = OUTD / "dialogue_bus.wav"
    subprocess.run([*ff, *ins, "-filter_complex", ";".join(flt), "-map", "[dia]", "-ar", "48000", str(bus)],
                   check=True, stdin=subprocess.DEVNULL, timeout=600)
    # pass 2: bus read twice (sidechain key + mix), ducked music, effects, loudness
    flt = [f"[1:a]anull[key]", f"[2:a]anull[dia]",
           f"[3:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume=0.22,afade=t=out:st={total - 2.0:.2f}:d=2[mus]",
           "[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[duck]"]
    sfx = []
    for (si, at, kind) in ((1, 1.5, "thud"), (3, 1.1, "splash"), (8, 0.0, "rain")):
        st = starts[si] + at
        if kind == "thud":
            src = "aevalsrc='0.9*sin(2*PI*55*t)*exp(-9*t)':s=48000:d=0.6"
        elif kind == "splash":
            src = "anoisesrc=d=0.7:c=pink:a=0.5:r=48000,afade=t=out:st=0.1:d=0.6,highpass=f=600"
        else:
            src = f"anoisesrc=d={ss[8].dur:.2f}:c=brown:a=0.25:r=48000,highpass=f=300,afade=t=in:d=0.4,afade=t=out:st={ss[8].dur - 0.5:.2f}:d=0.5"
        ms = int(st * 1000)
        flt.append(f"{src},aformat=channel_layouts=stereo,adelay={ms}|{ms},apad=whole_dur={total:.2f},atrim=0:{total:.2f}[s{len(sfx)}]")
        sfx.append(f"[s{len(sfx)}]")
    flt.append(f"[duck][dia]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9,"
               f"alimiter=limit=0.89,aresample=48000,atrim=0:{total:.2f}[a]")
    out = OUTD / "pilot.mp4"
    subprocess.run([*ff, "-i", str(video), "-i", str(bus), "-i", str(bus), "-stream_loop", "-1", "-i", "D:/Temp/cartoon/sneaky_snitch.mp3",
                    "-filter_complex", ";".join(flt), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{total:.2f}", str(out)], check=True, stdin=subprocess.DEVNULL, timeout=900)
    print("wrote", out, round(total, 1), "s")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if cmd == "preview":
        preview(OUTD / "pilot_sheet.png")
    elif cmd == "render":
        part = tuple(int(x) for x in sys.argv[2].split("/")) if len(sys.argv) > 2 else None
        render(part)
    elif cmd == "mix":
        mix()
