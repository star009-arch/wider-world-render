"""Cartoon scene engine: a storyboard of shots -> 1920x1080 frames -> ffmpeg. CPU only, free (runs on GitHub Actions).

Shot = background + actors (puppets with timed poses, entrances, talking, blinking) + effects (labels, arrows, captions,
armies, rain, map pins) + a slow camera move. Timings are seconds inside the shot; shot lengths come from the narration.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import puppet as P  # noqa: E402
import sets as S  # noqa: E402

W, H, FPS = 1920, 1080, 30


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


@dataclass
class Actor:
    who: str
    x: float
    y: float
    scale: float = 1.0
    flip: bool = False
    poses: list = field(default_factory=list)       # [(t, {pose fields})] applied from t onwards
    talk: list = field(default_factory=list)        # [(t0, t1)] mouth flaps
    enter: tuple | None = None                      # (dx, t0, t1): slide in from x+dx
    move: tuple | None = None                       # (dx, t0, t1): walk/slide by dx
    hop: tuple | None = None                        # (t0, t1): bouncing (marching, celebrating)

    def pose_at(self, t):
        p = P.Pose(flip=self.flip)
        for t0, kw in sorted(self.poses, key=lambda a: a[0]):
            if t >= t0:
                p = replace(p, **kw)
        if any(a <= t < b for a, b in self.talk):
            p = replace(p, mouth=["open", "closed", "wide", "closed"][int(t * 9) % 4])
        ph = (hash(self.who) % 97) / 97 * 3.0                       # each actor blinks on its own rhythm
        if (t + ph) % 3.2 < 0.12:
            p = replace(p, blink=1.0)
        p = replace(p, bob=p.bob + 0.06 * math.sin(t * 2.2 + ph))   # breathing
        if self.hop and self.hop[0] <= t < self.hop[1]:
            p = replace(p, bob=p.bob + 0.35 * abs(math.sin(t * 7)))
        return p

    def pos_at(self, t):
        x = self.x
        if self.enter:
            dx, t0, t1 = self.enter
            x += dx * (1 - ease((t - t0) / max(0.01, t1 - t0)))
        if self.move:
            dx, t0, t1 = self.move
            x += dx * ease((t - t0) / max(0.01, t1 - t0))
        return x, self.y


_TILES: dict = {}


def _tile(who, pose, scale):
    key = (who, pose, round(scale, 3))
    if key not in _TILES:
        u = 40 * scale
        tw, th = int(9 * u), int(13 * u)
        im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        P.draw(im, P.CAST[who], pose, tw / 2, th - 0.6 * u, scale)
        _TILES[key] = im.resize((tw // 2, th // 2), Image.LANCZOS)
        if len(_TILES) > 3000:
            _TILES.clear()
    return _TILES[key]


def paste_actor(frame, who, pose, x, y, scale):
    q = replace(pose, bob=round(pose.bob, 2), look=round(pose.look, 1))
    t = _tile(who, q, scale)
    frame.alpha_composite(t, (int(x - t.width / 2), int(y - t.height + 0.3 * 20 * scale)))


# ------------------------------------------------------------------------------------------------ effects
def fx_label(d, text, x, y, size=72, color=(255, 255, 255), stroke=(20, 20, 24), a=1.0):
    f = S.font(size, "impact")
    d.text((x, y), text, font=f, fill=color + (int(255 * a),), stroke_width=max(2, size // 12), stroke_fill=stroke + (int(255 * a),), anchor="mm")


def fx_bubble(d, text, x, y, a=1.0):
    f = S.font(30)
    w = d.textlength(text, font=f) + 36
    d.rounded_rectangle([x - w / 2, y - 30, x + w / 2, y + 26], radius=18, fill=(255, 255, 255, int(235 * a)), outline=(30, 30, 30, int(255 * a)), width=3)
    d.text((x, y - 2), text, font=f, fill=(30, 30, 30, int(255 * a)), anchor="mm")


def fx_arrow(d, x0, y0, x1, y1, frac=1.0, color=(220, 40, 40)):
    xe, ye = x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac
    d.line([(x0, y0), (xe, ye)], fill=(20, 20, 20, 255), width=26)
    d.line([(x0, y0), (xe, ye)], fill=color + (255,), width=16)
    if frac > 0.95:
        ang = math.atan2(ye - y0, xe - x0)
        pts = [(xe + 34 * math.cos(ang), ye + 34 * math.sin(ang)),
               (xe + 34 * math.cos(ang + 2.4), ye + 34 * math.sin(ang + 2.4)),
               (xe + 34 * math.cos(ang - 2.4), ye + 34 * math.sin(ang - 2.4))]
        d.polygon(pts, fill=color + (255,), outline=(20, 20, 20, 255))


# ------------------------------------------------------------------------------------------------ shots
@dataclass
class Shot:
    name: str
    dur: float
    bg: str                                         # palace | fort | field | rain | card | map | map_company
    actors: list = field(default_factory=list)
    fx: list = field(default_factory=list)           # callables fx(t, draw, frame) on the RGBA overlay
    cam: tuple = (1.0, 1.0, 0.5, 0.5)               # zoom from, zoom to, centre x, centre y (fractions)
    camkeys: list | None = None                      # [(t, zoom, cx, cy)] eased between keys (close-ups, pans)
    shake: list = field(default_factory=list)        # [(t, amplitude px)] decaying camera shakes
    under: list = field(default_factory=list)        # fx drawn on the set before the actors (shadows, props on the ground)
    world: str | None = None                         # period world for host costumes (hosts3.COSTUMES); None keeps the current one


_BG: dict = {}


def background(key):
    if key not in _BG:
        if key == "palace":
            _BG[key] = S.palace()
        elif key == "fort":
            _BG[key] = S.fort()
        elif key == "field":
            _BG[key] = S.battlefield()
        elif key == "rain":
            _BG[key] = S.battlefield(rain=True)
        elif key == "card":
            _BG[key] = S.card()
        elif key in ("map", "map_company"):
            _BG[key], _BG[key + "_proj"] = S.india_map(company=(key == "map_company"))
    return _BG[key]


PLATES = Path(os.environ.get("TE_PLATES", "D:/Temp/cartoon/plates"))
_PF: dict = {}


def _plate_img(name, i):
    key = (name, i)
    if key not in _PF:
        if len(_PF) > 64:
            _PF.clear()
        _PF[key] = Image.open(PLATES / name / f"{i:04d}.jpg").convert("RGBA").resize((W, H), Image.BICUBIC)
    return _PF[key]


def plate_frame(name, t, dur):
    """A 3D plate stretched smoothly over the whole shot (frames blended), so slow camera moves never judder."""
    n = len(list((PLATES / name).glob("*.jpg")))
    pos = max(0.0, min(1.0, t / max(0.01, dur))) * (n - 1)
    i = int(pos)
    a = _plate_img(name, i + 1)
    if i + 1 < n and pos - i > 0.02:
        return Image.blend(a, _plate_img(name, i + 2), pos - i)
    return a.copy()


def render_frame(shot: Shot, t: float) -> Image.Image:
    if shot.world:
        import hosts3 as _H3
        if _H3.WORLD != shot.world:
            import motions as _M
            _M.set_world(shot.world)
    if shot.bg.startswith("plate:"):
        frame = plate_frame(shot.bg[6:], t, shot.dur)
    else:
        frame = background(shot.bg).convert("RGBA").copy()
    if shot.bg == "rain":
        frame.alpha_composite(S.rain_layer(t))
    if shot.under:
        ul = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ud = ImageDraw.Draw(ul)
        for f in shot.under:
            f(t, ud, frame)
        frame.alpha_composite(ul)
    for a in sorted(shot.actors, key=lambda a: a.y):
        if getattr(a, "hide", None) and a.hide[0] <= t < a.hide[1]:
            continue
        if hasattr(a, "paint"):
            a.paint(frame, t)
            continue
        x, y = a.pos_at(t)
        paste_actor(frame, a.who, a.pose_at(t), x, y, a.scale)
    z, cx, cy = cam_at(shot, t)
    sx = sy = 0.0
    for t0, amp in shot.shake:
        if t0 <= t < t0 + 0.6:
            k = amp * (1 - (t - t0) / 0.6) ** 2
            sx += k * math.sin((t - t0) * 73)
            sy += k * math.cos((t - t0) * 61)
    if shot.shake and abs(z - 1) < 1e-3 and (sx or sy):
        z = 1.03                                                     # a little headroom so shakes never show edges
    if abs(z - 1) > 1e-3:
        w, h = W / z, H / z
        x0 = min(max(0, cx * W - w / 2 + sx), W - w)
        y0 = min(max(0, cy * H - h / 2 + sy), H - h)
        frame = frame.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((W, H), Image.BICUBIC)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))                     # labels, bubbles, arrows: screen space, never cropped
    d = ImageDraw.Draw(lay)
    for f in shot.fx:
        f(t, d, frame)
    frame.alpha_composite(lay)
    return frame.convert("RGB")


def cam_at(shot: Shot, t: float):
    if not shot.camkeys:
        z0, z1, cx, cy = shot.cam
        return z0 + (z1 - z0) * ease(t / shot.dur), cx, cy
    ks = sorted(shot.camkeys)
    if t <= ks[0][0]:
        return ks[0][1:]
    for a, b in zip(ks, ks[1:]):
        if a[0] <= t <= b[0]:
            e = ease((t - a[0]) / max(1e-6, b[0] - a[0]))
            return tuple(a[i] + (b[i] - a[i]) * e for i in (1, 2, 3))
    return ks[-1][1:]


def render_shot(shot: Shot, out: Path, threads=2):
    n = int(round(shot.dur * FPS))
    p = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                          "-pix_fmt", "yuv420p", "-threads", str(threads), str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(render_frame(shot, i / FPS).tobytes())
    p.stdin.close()
    if p.wait():
        raise SystemExit(f"ffmpeg failed on {shot.name}")


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()
