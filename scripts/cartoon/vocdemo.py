"""VOC pilot: shots for the style bible and the 2-minute demo, all drawn and animated in code.

  python scripts/cartoon/vocdemo.py still <shot> <t>          one frame -> D:/Temp/cartoon/voc_demo/<shot>_<t>.jpg
  python scripts/cartoon/vocdemo.py clip <shot> [fps]          frames -> mp4 (no audio) for review

Shots are functions shot(t) -> RGB frame. Characters are motions.Performer instances (walk, gesture, blink, lip-sync,
contact + cast shadows, light matching), sets come from vocsets, ships from vocship, effects from vocfx.
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402
import voccast  # noqa: E402,F401  (registers the VOC worlds)
import vocart as A  # noqa: E402
import vocfx as FX  # noqa: E402
import vocsets as VS  # noqa: E402
import vocship as V  # noqa: E402
from vocart import INK, Layer  # noqa: E402

OUT = Path("D:/Temp/cartoon/voc_demo")
FPS = 24
M.STAGE_ON = False                       # we place feet ourselves (subtitles sit over the sand/floor band)

# ---- combat and work clips (added to the shared clip library at import)
M.CLIPS.update({
    "aim_fire": (2.2, [(0.0, {}, {}), (0.35, {"sh_l": 84, "el_l": -8, "lean": 5, "head": 3}, {"brows": -0.6, "mouth": "X"}),
                       (0.95, {"sh_l": 86, "el_l": -6, "lean": 6}, {}), (1.0, {"lean": -9, "head": -7, "sh_l": 96}, {"mouth": "o", "blink": 1.0}),
                       (1.35, {"lean": 3, "head": 0, "sh_l": 86}, {"mouth": "X"}), (2.2, {"sh_l": 86, "el_l": -6, "lean": 4}, {})]),
    "brace": (0.8, [(0.0, {}, {}), (0.4, {"sh_l": 84, "el_l": -8, "lean": 5}, {"brows": -0.5}), (0.8, {"sh_l": 86, "el_l": -6, "lean": 5}, {})]),
    "slash": (1.1, [(0.0, {}, {}), (0.3, {"sh_l": 160, "el_l": 30, "lean": -6, "head": -4}, {"brows": -0.8, "mouth": "D"}),
                    (0.55, {"sh_l": 40, "el_l": -10, "lean": 12, "head": 6}, {}), (1.1, {"sh_l": 60, "el_l": 10, "lean": 6, "head": 0}, {})]),
    "signal": (1.4, [(0.0, {}, {}), (0.3, {"sh_l": 150, "el_l": -6, "head": 4}, {"brows": -0.4, "mouth": "D"}),
                     (0.9, {"sh_l": 100, "el_l": -4, "lean": 8}, {}), (1.4, {"sh_l": 96, "el_l": 0, "lean": 6}, {"mouth": "X"})]),
    "haul": (1.0, [(0.0, {}, {}), (0.25, {"sh_l": 120, "el_l": 10, "sh_r": 110, "el_r": 10, "lean": -12}, {"brows": -0.5}),
                   (0.6, {"sh_l": 70, "el_l": 40, "sh_r": 60, "el_r": 40, "lean": -22}, {"mouth": "X"}), (1.0, {"sh_l": 110, "el_l": 10, "sh_r": 100, "el_r": 10, "lean": -12}, {})]),
})


def P(key, x, ground, scale=1.0, flip=False, **kw):
    return M.Performer(key, x=x, ground=ground, scale=scale, flip=flip, **kw)


def paint_all(frame, t, performers):
    for p in sorted(performers, key=lambda q: q.ground):
        if p.hide and p.hide[0] <= t < p.hide[1]:
            continue
        p.paint(frame, t)


def muzzle_point(p: M.Performer, t):
    """Where the barrel of a levelled musket ends (screen px), for the flash and smoke."""
    x, y = p.pos_at(t)
    y, sk = M.stage(y)
    f = -1 if p.facing(t) else 1
    u = 20 * p.scale * sk
    return x + f * 6.6 * u, y - 6.9 * u


def stakes(L: Layer, x0, x1, base, h, t, seed=4, lean=0.0, col=(150, 108, 66)):
    """A stockade of sharpened logs (inked, cel-shaded, each slightly different)."""
    rng = random.Random(seed)
    x = x0
    while x < x1:
        w = rng.uniform(15, 21)
        hh = h * rng.uniform(0.88, 1.08)
        tip = hh + w * 0.9
        pts = [(x, base), (x, base - hh), (x + w / 2 + lean * hh, base - tip), (x + w, base - hh), (x + w, base)]
        c = A.mix(col, (120, 86, 52), rng.random() * 0.6)
        L.poly(pts, c, 2.6)
        L.shade_poly([(x + w * 0.58, base), (x + w * 0.58, base - hh), (x + w / 2 + lean * hh, base - tip), (x + w, base - hh), (x + w, base)],
                     A.shade(c, 0.78), 255)
        for k in range(2):
            ry = base - hh * rng.uniform(0.2, 0.8)
            L.line([(x + 3, ry), (x + w - 3, ry + 2)], A.shade(c, 0.6), 1.2)
        x += w - 2
    L.line([(x0 - 4, base - h * 0.35), (x1 + 4, base - h * 0.35)], (110, 80, 50), 5)       # lashing rail
    L.line([(x0 - 4, base - h * 0.35), (x1 + 4, base - h * 0.35)], INK, 1.6)


# ------------------------------------------------------------------------------------------------ style bible: battlefield
class BibleBattle:
    """Colachel, 1741 (composition sample): the company stockade on the beach, Travancore's Nair soldiers closing in from
    the palm grove on the land side. Volley smoke drifts inland on the sea breeze."""

    def __init__(self):
        self.set = VS.Set("colachel_camp")
        M.CUR_PLATE = "colachel_camp"
        M.SUN_FROM_RIGHT.add("colachel_camp") if hasattr(M, "SUN_FROM_RIGHT") and isinstance(M.SUN_FROM_RIGHT, set) else None
        g = 930                                                        # ground line inside the stockade
        self.voc = [P("travancore_1741:delannoy", 170, g - 4, 1.62, acts=[(0.6, "point", None)]),
                    P("travancore_1741:voc_soldier", 360, g - 22, 1.55, acts=[(0.3, "aim_fire", None)], props={"prop_l": "musket_aim"}),
                    P("travancore_1741:voc_soldier2", 540, g - 40, 1.5, acts=[(1.1, "aim_fire", None)], props={"prop_l": "musket_aim"}),
                    P("travancore_1741:voc_soldier", 700, g - 58, 1.45, acts=[(1.9, "aim_fire", None)], props={"prop_l": "musket_aim"})]
        self.nair = [P("travancore_1741:nair", 1380, g + 80, 1.7, flip=True, walks=[(0.0, 1200)], acts=[(2.6, "slash", None)]),
                     P("travancore_1741:nair2", 1600, g + 20, 1.55, flip=True, acts=[(0.8, "aim_fire", None)], props={"prop_l": "matchlock_aim"}),
                     P("travancore_1741:nair3", 1760, g + 60, 1.6, flip=True, walks=[(0.4, 1520)]),
                     P("travancore_1741:ramayyan", 1700, g - 60, 1.4, flip=True, acts=[(1.4, "signal", None)]),
                     P("travancore_1741:nair", 1290, g - 110, 1.2, flip=True, walks=[(0.2, 1100)]),
                     P("travancore_1741:nair2", 1480, g - 140, 1.15, flip=True, acts=[(2.0, "aim_fire", None)], props={"prop_l": "matchlock_aim"})]
        self.fires = [(self.voc[1], 1.25), (self.voc[2], 2.05), (self.voc[3], 2.85), (self.nair[1], 1.75), (self.nair[5], 2.95)]

    def frame(self, t):
        def actors(f, t):
            back = Layer()
            stakes(back, 40, 860, 760, 150, t, seed=2)                  # far wall of the stockade (behind the soldiers)
            back.poly([(260, 752), (262, 700), (420, 690), (424, 752)], (196, 170, 120), 2.6)   # palm-leaf store shed
            back.poly([(246, 704), (340, 650), (440, 694)], (150, 140, 80), 2.6)
            f.alpha_composite(back.out())
            fxb = Layer()
            FX.fire(fxb, 340, 700, 130, 100, t, seed=2)                  # the store is burning
            VS.smoke_plume(fxb, 340, 620, t, n=7, col=(110, 104, 100), rise=26, drift=14, size=30, seed=4, a=220)
            f.alpha_composite(fxb.out())
            paint_all(f, t, self.nair)
            paint_all(f, t, self.voc)
            fx = Layer()
            stakes(fx, -20, 880, 1010, 190, t, seed=9)                   # near wall: hides the defenders below the waist
            for p, tf in self.fires:
                mx, my = muzzle_point(p, tf)
                FX.muzzle(fx, mx, my, t, tf, f=-1 if p.facing(tf) else 1, wind=(26, -8), size=1.1, seed=int(tf * 10))
            f.alpha_composite(fx.out())
        return self.set.frame(t, actors).convert("RGB")


SHOTS = {"bible_battle": BibleBattle}


def render_still(name, t):
    s = SHOTS[name]()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}_{t:.2f}.jpg"
    s.frame(t).save(out, quality=90)
    print(out)


def render_clip(name, dur, fps=FPS):
    import imageio_ffmpeg
    s = SHOTS[name]()
    out = OUT / f"{name}.mp4"
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(fps), "-i", "-",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", str(out)], stdin=subprocess.PIPE)
    n = int(dur * fps)
    for i in range(n):
        proc.stdin.write(s.frame(i / fps).tobytes())
        if i % 24 == 0:
            print(f"{name}: {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()
    print(out)


class BibleHarbour:
    """Banda Neira, 1620s (environment sample): an East Indiaman glides into the harbour and opens its gun ports."""

    def __init__(self):
        self.set = VS.Set("banda_harbour")

    def frame(self, t):
        x = 1500 - 70 * t                                             # the ship glides in from the right
        ports = max(0.0, min(1.0, (t - 2.5) / 1.6))
        return self.set.frame(t, lambda f, tt: V.place(f, tt, x, 736, L=760, ports=ports, facing=-1)).convert("RGB")


SHOTS["bible_harbour"] = BibleHarbour


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        render_still(sys.argv[2], float(sys.argv[3]))
    elif cmd == "clip":
        render_clip(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 6.0)
