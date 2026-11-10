"""Maps and charts for the undersea cables film (runs on the render server or the laptop; matplotlib + PIL + ffmpeg).

  python scripts/cables_visuals.py [name ...]     render all (or the named) clips -> <work>/visuals/<name>.mp4

Maps are drawn on Natural Earth (public domain) in a plain equirectangular projection. Cable routes are SCHEMATIC: waypoints
follow each system's published landing points and general path, not its surveyed route, and every map says so on screen.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
W, H, FPS = 1920, 1080, 24
OUT = Path(os.environ.get("YTG_CABLES_VISUALS", ROOT.parent / "work" / "cables" / "visuals"))
NE = ROOT / "data" / "geo" / "naturalearth"
FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_B = "C:/Windows/Fonts/segoeuib.ttf"
FONT_L = "C:/Windows/Fonts/segoeuil.ttf"
OCEAN, LAND, COAST, TEXT, CABLE, HILITE, WARN = "#071726", "#2c4560", "#7f99b3", "#f4f1ea", "#38c6e8", "#f2b134", "#ff7b6b"


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def font(size: int, kind: str = "r") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype({"r": FONT, "b": FONT_B, "l": FONT_L}[kind], size)


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


class Frame:
    """An equirectangular view: bbox (lon0, lat0, lon1, lat1) mapped to the full 1920x1080 frame, latitude stretched by
    1/cos(mid-latitude) so shapes keep roughly true proportions. The bbox is widened to 16:9."""
    def __init__(self, bbox):
        lon0, lat0, lon1, lat1 = bbox
        self.k = 1 / max(0.35, math.cos(math.radians((lat0 + lat1) / 2)))
        cx, cy = (lon0 + lon1) / 2, (lat0 + lat1) / 2
        w, h = lon1 - lon0, (lat1 - lat0) * self.k
        if w / h < W / H:
            w = h * W / H
        else:
            h = w * H / W
        self.lon0, self.lon1 = cx - w / 2, cx + w / 2
        self.lat1 = cy + h / 2 / self.k
        self.sx, self.sy = W / w, H / h

    def xy(self, lon, lat):
        return (lon - self.lon0) * self.sx, (self.lat1 - lat) * self.k * self.sy


def basemap(fr: Frame, scale: float = 1.0) -> Image.Image:
    """Land from Natural Earth admin-0 (1:50m for wide views, 1:10m for close ones), drawn at 2x and reduced (anti-aliased)."""
    import shapefile
    s = 2
    img = Image.new("RGB", (W * s, H * s), OCEAN)
    d = ImageDraw.Draw(img)
    wide = (fr.lon1 - fr.lon0) > 60
    shp = NE / ("ne_50m_admin_0_countries" if wide else "ne_10m_admin_0_countries")
    rd = shapefile.Reader(str(next(shp.glob("*.shp"))))
    for sh in rd.shapes():
        pts, parts = sh.points, list(sh.parts) + [len(sh.points)]
        for a, b in zip(parts, parts[1:]):
            ring = [fr.xy(x, y) for x, y in pts[a:b]]
            if len(ring) > 2:
                d.polygon([(x * s, y * s) for x, y in ring], fill=LAND, outline=COAST, width=1)
    # faint graticule every 15 degrees
    for lon in range(-180, 181, 15):
        x, _ = fr.xy(lon, 0)
        d.line([(x * s, 0), (x * s, H * s)], fill="#0d2236", width=1)
    for lat in range(-75, 76, 15):
        _, y = fr.xy(0, lat)
        d.line([(0, y * s), (W * s, y * s)], fill="#0d2236", width=1)
    img = img.resize((W, H), Image.LANCZOS)
    # vignette
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.38 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.2
    arr = (np.asarray(img).astype(np.float32) * np.clip(v, 0.45, 1)[..., None]).astype(np.uint8)
    return Image.fromarray(arr)


def _split_dateline(route):
    """[(lon, lat)] -> list of segments, split where a leg crosses the 180 meridian (draw the short way round)."""
    segs, cur = [], [route[0]]
    for (x0, y0), (x1, y1) in zip(route, route[1:]):
        if abs(x1 - x0) > 180:
            x1u = x1 - 360 if x1 > x0 else x1 + 360
            edge = 180 if x0 > 0 else -180
            t = (edge - x0) / (x1u - x0)
            ym = y0 + t * (y1 - y0)
            cur.append((edge, ym)); segs.append(cur); cur = [(-edge, ym)]
        cur.append((x1, y1))
    segs.append(cur)
    return segs


def _densify(seg, step=0.5):
    out = [seg[0]]
    for (x0, y0), (x1, y1) in zip(seg, seg[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(1, n + 1)]
    return out


def _smooth(seg, it=3):
    """Chaikin corner cutting, so schematic routes curve instead of zig-zag."""
    for _ in range(it):
        if len(seg) < 3:
            return seg
        new = [seg[0]]
        for (x0, y0), (x1, y1) in zip(seg, seg[1:]):
            new += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        new.append(seg[-1])
        seg = new
    return seg


def draw_route(layer: Image.Image, fr: Frame, route, frac: float, color=CABLE, width=4, head=True):
    """Draw the first `frac` of a route (by length), with a soft glow and a bright moving head."""
    if frac <= 0:
        return
    pts = [[fr.xy(x, y) for x, y in s] for s in _geom(route)]
    lens = [sum(math.dist(a, b) for a, b in zip(p, p[1:])) for p in pts]
    budget = frac * sum(lens)
    gd, d = ImageDraw.Draw(_GLOW[0]), ImageDraw.Draw(layer)
    tip = None
    for p in pts:
        keep = [p[0]]
        for a, b in zip(p, p[1:]):
            seg = math.dist(a, b)
            if budget <= 0:
                break
            if seg > budget:
                t = budget / seg
                keep.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)); budget = 0
                break
            keep.append(b); budget -= seg
        if len(keep) > 1:
            gd.line([(x / 2, y / 2) for x, y in keep], fill=color, width=width * 2, joint="curve")
            d.line(keep, fill=color, width=width, joint="curve")
            tip = keep[-1]
        if budget <= 0:
            break
    if head and tip and frac < 1:
        r = width * 2.2
        d.ellipse([tip[0] - r, tip[1] - r, tip[0] + r, tip[1] + r], fill="#ffffff")


_GLOW: list = [None]          # half-resolution glow buffer for the current frame (blurred once per frame in render())
_GEOM: dict = {}


def _geom(route):
    key = tuple(route)
    if key not in _GEOM:
        _GEOM[key] = [_densify(_smooth(s)) for s in _split_dateline(route)]
    return _GEOM[key]


def _soft(glow: Image.Image) -> Image.Image:
    g = glow.filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR)
    a = np.asarray(g).copy()
    a[..., 3] = (a[..., 3] * 0.45).astype(np.uint8)
    return Image.fromarray(a)


def pin(d: ImageDraw.ImageDraw, fr: Frame, lon, lat, text, alpha=1.0, color=HILITE, side="r", size=30):
    x, y = fr.xy(lon, lat)
    a = int(255 * alpha)
    r = 9
    d.ellipse([x - r - 5, y - r - 5, x + r + 5, y + r + 5], outline=color[:7] + f"{a // 2:02x}", width=3)
    d.ellipse([x - r, y - r, x + r, y + r], fill=color[:7] + f"{a:02x}")
    f = font(size, "b")
    for line_i, line in enumerate(text.split("\n")):
        lw = d.textlength(line, font=f)
        lx = x + 20 if side == "r" else x - 20 - lw
        d.text((lx + 2, y - 20 + line_i * (size + 6) + 2), line, font=f, fill=(0, 0, 0, int(a * 0.7)))
        d.text((lx, y - 20 + line_i * (size + 6)), line, font=f, fill=TEXT[:7] + f"{a:02x}")


def chrome(d: ImageDraw.ImageDraw, title: str, note: str, t: float, dur: float):
    # clean screen (owner 2026-11-10): sources go to the description and end credits; only the accuracy caveat stays
    note = "Routes simplified" if "schematic" in note.lower() else ""
    a = int(255 * min(1, t / 0.6))
    if title:
        d.text((80, 64), title, font=font(54, "b"), fill=TEXT[:7] + f"{a:02x}")
    if note:
        d.text((80, H - 64), note, font=font(22), fill="#c9d6e2" + f"{int(a * 0.8):02x}")


def render(name: str, dur: float, draw_fn, base: Image.Image, zoom=(1.0, 1.06)):
    """Composite each frame (base, slowly pushed in, + overlay from draw_fn(t, layer)) and pipe it to x264."""
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}.mp4"
    # no fade-out and a long hold: a shot in the film may run longer than the animation; holding a faded last frame made
    # charts go dark on screen (owner, 2026-11-10). The film's own dissolves handle every transition.
    dur = max(dur, 30.0 if name == "map_world_routes" else 20.0)
    n = int(dur * FPS)
    p = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                          "-threads", os.environ.get("YTG_X264_THREADS", "3"), str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        z = zoom[0] + (zoom[1] - zoom[0]) * ease(t / dur)
        bw, bh = int(W / z), int(H / z)
        frame = base.crop(((W - bw) // 2, (H - bh) // 2, (W + bw) // 2, (H + bh) // 2)).resize((W, H), Image.BICUBIC).convert("RGBA")
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _GLOW[0] = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
        draw_fn(t, layer, z)
        if _GLOW[0].getbbox():
            frame.alpha_composite(_soft(_GLOW[0]))
        frame.alpha_composite(layer)
        p.stdin.write(frame.convert("RGB").tobytes())
    p.stdin.close()
    if p.wait():
        raise SystemExit(f"ffmpeg failed for {name}")
    print(f"{name}: {dur:.1f}s -> {out}", flush=True)


def zoomed(fr: Frame, z: float) -> Frame:
    """The Frame as seen after the base image is pushed in by z (around the centre), so overlays stay registered."""
    f = Frame.__new__(Frame)
    f.k = fr.k
    f.sx, f.sy = fr.sx * z, fr.sy * z
    f.lon0 = fr.lon0 + (W - W / z) / 2 / fr.sx
    f.lon1 = f.lon0 + W / f.sx
    f.lat1 = fr.lat1 - (H - H / z) / 2 / fr.sy / fr.k
    return f


# --------------------------------------------------------------------------------------------- schematic routes (lon, lat)
NYC, LONDON = (-74.0, 40.7), (-0.13, 51.5)
SINGAPORE, MUMBAI, CHENNAI, MARSEILLE = (103.8, 1.3), (72.88, 19.0), (80.27, 13.08), (5.37, 43.3)
ROUTES = {
    "transatlantic_north": [(-72.9, 40.75), (-63.6, 44.0), (-45, 48.5), (-25, 51.0), (-3.0, 51.3)],
    "dunant": [(-75.98, 36.85), (-60, 39.5), (-40, 42.5), (-20, 45.5), (-1.95, 46.72)],
    "marea": [(-75.98, 36.85), (-55, 38.0), (-30, 40.5), (-10, 43.8), (-2.9, 43.4)],
    "us_brazil": [(-80.2, 25.8), (-73, 21), (-60, 12), (-45, 3), (-38.5, -3.7)],
    "brazil_europe": [(-38.5, -3.7), (-30, 5), (-22, 20), (-14, 32), (-8.9, 37.95)],
    "south_atlantic": [(-38.5, -3.7), (-20, -6), (0, -7.5), (13.2, -8.8)],
    "transpacific_japan": [(-118.4, 33.9), (-140, 33), (-165, 35), (175, 35.5), (150, 35), (139.9, 35.0)],
    "pacific_australia": [(-118.4, 33.9), (-140, 27), (-158, 21.3), (-175, 5), (175, -15), (160, -27), (151.2, -33.9)],
    "asia_australia": [(103.8, 1.3), (106, -6), (110, -15), (113, -25), (115.9, -31.9)],
    "intra_asia": [(103.8, 1.3), (108, 8), (114.2, 22.3), (122, 26), (130, 31), (139.9, 35.0)],
    "smw6": [SINGAPORE, (97.5, 5.5), (88, 5.0), (81.5, 5.2), (76, 7.0), (65, 12.5), (52, 12.2), (43.5, 12.6), (39, 19), (34, 26.5),
             (32.5, 29.9), (32.3, 31.3), (25, 33.5), (14, 36.5), (8, 40), MARSEILLE],
    "smw6_chennai": [(81.5, 5.2), (82.5, 9), CHENNAI],
    "smw6_mumbai": [(76, 7.0), (71.5, 13), MUMBAI],
    "two_africa": [(-3.0, 50.8), (-9.5, 44), (-10.5, 38.0), (-13, 32), (-17.0, 26), (-18.5, 18), (-17.6, 14.7), (-14, 8), (-8, 4.0),
                   (-4.0, 4.6), (0.5, 4.6), (3.4, 5.8), (7.5, 2.5), (9.5, -2), (11.5, -8), (12.5, -16), (15, -27), (18.4, -34.6),
                   (24, -35.3), (31.5, -30.5), (35.5, -24), (40.6, -15), (40.5, -6), (43, 2), (48, 8.5), (45.5, 12.2), (42, 14.5),
                   (38.5, 20), (34, 26.5), (32.5, 29.9), (32.3, 31.3), (24, 34.5), (12, 38), (3.5, 41.0), (2.2, 41.4)],
}
WORLD_BBOX = (-180, -58, 180, 74)
SCHEMATIC = "Major routes drawn schematically, not to scale"


def world_routes(name="map_world_routes", dur=16.0):
    fr = Frame(WORLD_BBOX)
    base = basemap(fr)
    order = ["transatlantic_north", "dunant", "marea", "us_brazil", "brazil_europe", "south_atlantic", "two_africa", "smw6",
             "smw6_mumbai", "smw6_chennai", "intra_asia", "asia_australia", "transpacific_japan", "pacific_australia"]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        for k, r in enumerate(order):
            start = 0.6 + k * 0.55
            draw_route(layer, f, ROUTES[r], ease((t - start) / 2.4), width=3, head=True)
        chrome(ImageDraw.Draw(layer), "", "Cable routes: " + SCHEMATIC + ". Base map: Natural Earth", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.08))


def ny_london(name="map_ny_london", dur=13.0):
    fr = Frame((-97, 24, 12, 62))
    base = basemap(fr)
    r = ROUTES["transatlantic_north"]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_route(layer, f, r, ease((t - 0.8) / 3.0), color=CABLE, width=5)
        pin(d, f, *NYC, "New York", min(1, t / 0.8), side="l")
        pin(d, f, *LONDON, "London", min(1, t / 0.8))
        if t > 4.0:                                       # a pulse goes over and back, then the measured figure
            u = ((t - 4.0) / 2.6) % 2
            frac = u if u <= 1 else 2 - u
            segs = _geom(r)[0]
            i = int(frac * (len(segs) - 1))
            x, y = f.xy(*segs[i])
            d.ellipse([x - 12, y - 12, x + 12, y + 12], fill="#ffffff")
        if t > 6.5:
            a = int(255 * min(1, (t - 6.5) / 0.6))
            d.text((W / 2, H * 0.74), "under 59 milliseconds", font=font(84, "b"), fill=HILITE + f"{a:02x}", anchor="mm")
            d.text((W / 2, H * 0.74 + 70), "New York to London and back, Hibernia Express, 2015", font=font(32), fill=TEXT + f"{a:02x}", anchor="mm")
        chrome(d, "", "Source: Hibernia Networks, 2015. Route schematic", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.05))


def dunant(name="map_dunant", dur=13.0):
    fr = Frame((-100, 20, 24, 60))
    base = basemap(fr)

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_route(layer, f, ROUTES["dunant"], ease((t - 0.8) / 3.2), color=CABLE, width=6)
        pin(d, f, -75.98, 36.85, "Virginia Beach, USA", min(1, t / 0.8), side="l")
        pin(d, f, -1.95, 46.72, "Saint-Hilaire-de-Riez,\nFrance", min(1, t / 0.8))
        if t > 4.6:
            a = int(255 * min(1, (t - 4.6) / 0.6))
            v = 250 * ease((t - 4.6) / 2.2)
            d.text((W / 2, H * 0.74), f"{v:,.0f} terabits a second", font=font(84, "b"), fill=HILITE + f"{a:02x}", anchor="mm")
            d.text((W / 2, H * 0.74 + 70), "Google's Dunant cable, design capacity", font=font(32), fill=TEXT + f"{a:02x}", anchor="mm")
        chrome(d, "", "Source: Google Cloud, 2021. Route schematic", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.05))


def two_africa(name="map_2africa", dur=14.0):
    fr = Frame((-40, -40, 62, 55))
    base = basemap(fr)

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_route(layer, f, ROUTES["two_africa"], ease((t - 0.6) / 7.0), color=CABLE, width=5)
        if t > 7.8:
            a = int(255 * min(1, (t - 7.8) / 0.6))
            d.text((W * 0.08, H * 0.62), "2Africa", font=font(70, "b"), fill=HILITE + f"{a:02x}")
            d.text((W * 0.08, H * 0.62 + 84), "more than 45,000 km\nmore than 30 countries", font=font(38), fill=TEXT + f"{a:02x}", spacing=10)
        chrome(d, "", "Source: 2Africa consortium. Route schematic, simplified", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.06))


def incidents(name="map_incidents", dur=16.0):
    fr = Frame((-60, -35, 75, 45))
    base = basemap(fr)
    events = [(1.0, (-4.0, 5.3), "Côte d'Ivoire, March 2024\nundersea landslide, four cables cut", "r"),
              (5.5, (40.0, 16.5), "Red Sea, 2024\nfour cables damaged", "r")]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        for start, (lon, lat), text, side in events:
            if t > start:
                pin(d, f, lon, lat, text, min(1, (t - start) / 0.6), color=WARN, side=side, size=30)
        chrome(d, "", "Sources: Internet Society; industry reports. Base map: Natural Earth", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.05))


def tonga(name="map_tonga", dur=9.0):
    fr = Frame((174, -27, 196, -13))
    base = basemap_wrapped(fr)

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        x0, y0 = f.xy(-175.2 + 360, -21.1)
        if t > 0.8:
            a = min(1, (t - 0.8) / 0.6)
            pin_xy(d, x0, y0, "Tonga, January 2022\nvolcanic eruption cut its only cable", a, WARN)
        chrome(d, "", "Source: RNZ. Base map: Natural Earth", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.08))


def basemap_wrapped(fr: Frame) -> Image.Image:
    """Like basemap() for a view across the 180 meridian (lon given as 0..360)."""
    import shapefile
    s = 2
    img = Image.new("RGB", (W * s, H * s), OCEAN)
    d = ImageDraw.Draw(img)
    rd = shapefile.Reader(str(next((NE / "ne_10m_admin_0_countries").glob("*.shp"))))
    for sh in rd.shapes():
        pts, parts = sh.points, list(sh.parts) + [len(sh.points)]
        for a, b in zip(parts, parts[1:]):
            ring = [fr.xy(x + 360 if x < 0 else x, y) for x, y in pts[a:b]]
            if len(ring) > 2:
                d.polygon([(x * s, y * s) for x, y in ring], fill=LAND, outline=COAST, width=1)
    return img.resize((W, H), Image.LANCZOS)


def pin_xy(d, x, y, text, alpha, color):
    a = int(255 * alpha)
    d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=color + f"{a // 2:02x}", width=3)
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=color + f"{a:02x}")
    for i, line in enumerate(text.split("\n")):
        d.text((x + 24, y - 20 + i * 38), line, font=font(32, "b"), fill=TEXT + f"{a:02x}")


def india(name="map_india", dur=15.0):
    fr = Frame((55, -6, 108, 32))
    base = basemap(fr)

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_route(layer, f, ROUTES["smw6"], ease((t - 0.6) / 6.0), color=CABLE, width=5)
        draw_route(layer, f, ROUTES["smw6_mumbai"], ease((t - 4.0) / 1.5), color=CABLE, width=5)
        draw_route(layer, f, ROUTES["smw6_chennai"], ease((t - 3.4) / 1.5), color=CABLE, width=5)
        pin(d, f, *MUMBAI, "Mumbai", min(1, max(0, (t - 5.0) / 0.6)), side="l")
        pin(d, f, *CHENNAI, "Chennai", min(1, max(0, (t - 4.6) / 0.6)))
        pin(d, f, *SINGAPORE, "Singapore", min(1, t / 0.8))
        if t > 7.5:
            a = int(255 * min(1, (t - 7.5) / 0.6))
            d.text((W * 0.06, H * 0.12), "SEA-ME-WE 6", font=font(64, "b"), fill=HILITE + f"{a:02x}")
            d.text((W * 0.06, H * 0.12 + 78), "Singapore to Marseille, about 21,700 km", font=font(36), fill=TEXT + f"{a:02x}")
        chrome(d, "", "Sources: SEA-ME-WE 6 consortium; Government of India. Route schematic", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.06))


# ------------------------------------------------------------------------------------------------------------- charts
def card_frames(name, dur, draw_fn):
    base = Image.new("RGB", (W, H), "#0a1622")
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    base = Image.fromarray((np.asarray(base).astype(np.float32) * np.clip(v, 0.5, 1)[..., None]).astype(np.uint8))
    render(name, dur, lambda t, layer, z: draw_fn(t, ImageDraw.Draw(layer)), base, zoom=(1.0, 1.0))


def chart_causes(name="chart_fault_causes", dur=13.0):
    bars = [("Fishing", 44.0, CABLE), ("Anchors", 15.0, CABLE), ("All other causes", 40.5, "#5d7690"), ("Fish bites", 0.5, WARN)]

    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        d.text((160, 120), "What damages undersea cables", font=font(56, "b"), fill=TEXT + f"{a:02x}")
        d.text((160, 196), "Share of 2,162 recorded faults, 1959 to 2006", font=font(32), fill="#c9d6e2" + f"{a:02x}")
        x0, maxw = 560, 1180
        for i, (label, v, col) in enumerate(bars):
            y = 330 + i * 150
            g = ease((t - 0.8 - i * 0.5) / 1.2)
            d.text((160, y + 14), label, font=font(40, "b"), fill=TEXT + f"{a:02x}")
            wpx = max(6, maxw * v / 45 * g)
            d.rounded_rectangle([x0, y, x0 + wpx, y + 70], radius=6, fill=col + f"{a:02x}")
            if g > 0.05:
                d.text((x0 + wpx + 24, y + 12), f"{v * g:.1f}%" if v < 1 else f"{v * g:.0f}%", font=font(40, "b"), fill=TEXT + f"{a:02x}")
    card_frames(name, dur, fn)


def chart_bandwidth(name="chart_bandwidth", dur=11.0):
    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        d.text((160, 150), "Who uses the world's international bandwidth", font=font(54, "b"), fill=TEXT + f"{a:02x}")
        d.text((160, 222), "2024: content and cloud networks such as Google, Meta, Microsoft and Amazon", font=font(32), fill="#c9d6e2" + f"{a:02x}")
        g = ease((t - 0.9) / 2.0)
        x0, y0, w, h = 160, 430, 1600, 150
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=10, fill="#22384f" + f"{a:02x}")
        d.rounded_rectangle([x0, y0, x0 + w * 0.74 * g, y0 + h], radius=10, fill=CABLE + f"{a:02x}")
        if g > 0.6:
            b = int(a * min(1, (g - 0.6) / 0.3))
            d.text((x0 + 40, y0 + 36), "content and cloud networks", font=font(46, "b"), fill="#06202b" + f"{b:02x}")
            d.text((x0 + w * 0.74 + 30, y0 + 36), "everyone else", font=font(40), fill=TEXT + f"{b:02x}")
            d.text((x0, y0 + h + 40), "almost three-quarters", font=font(64, "b"), fill=HILITE + f"{b:02x}")
    card_frames(name, dur, fn)


def counter_card(name, dur, value_fn, big, small, source):
    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        d.text((W / 2, H * 0.44), value_fn(ease((t - 0.5) / 1.8)), font=font(150, "b"), fill=HILITE + f"{a:02x}", anchor="mm")
        d.text((W / 2, H * 0.44 + 120), big, font=font(48, "b"), fill=TEXT + f"{a:02x}", anchor="mm")
        if small:
            d.text((W / 2, H * 0.44 + 190), small, font=font(32), fill="#c9d6e2" + f"{a:02x}", anchor="mm")
    card_frames(name, dur, fn)


def timeline(name="chart_timeline", dur=15.0):
    events = [("1858", "First telegraph cable across the Atlantic", "dead within about a month"),
              ("1866", "The Great Eastern lays a cable that lasts", ""),
              ("1988", "First fibre-optic cable across the Atlantic", "")]

    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        y = H * 0.52
        g = ease((t - 0.4) / 2.5)
        d.line([(200, y), (200 + 1520 * g, y)], fill="#5d7690" + f"{a:02x}", width=4)
        for i, (yr, line1, line2) in enumerate(events):
            x = 230 + i * 620
            b = int(a * ease((t - 1.0 - i * 2.6) / 0.7))
            if b <= 0:
                continue
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=HILITE + f"{b:02x}")
            d.text((x, y - 120), yr, font=font(84, "b"), fill=HILITE + f"{b:02x}", anchor="mm")
            d.multiline_text((x - 20, y + 50), _wrap(line1, 22) + ("\n" + line2 if line2 else ""), font=font(34), fill=TEXT + f"{b:02x}", spacing=8)
    card_frames(name, dur, fn)


def _wrap(s, n):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = f"{line} {w}".strip()
    return "\n".join(out + [line])


ALL = {
    "map_world_routes": world_routes, "map_ny_london": ny_london, "map_dunant": dunant, "map_2africa": two_africa,
    "map_incidents": incidents, "map_tonga": tonga, "map_india": india,
    "chart_fault_causes": chart_causes, "chart_bandwidth": chart_bandwidth, "chart_timeline": timeline,
    "chart_faults_year": lambda: counter_card("chart_faults_year", 9.0, lambda g: f"{int(150 * g)}–{int(200 * g)}",
                                              "cable faults every year", "about three every week", "Source: International Cable Protection Committee"),
    "chart_repair_ships": lambda: counter_card("chart_repair_ships", 9.0, lambda g: f"about {int(60 * g)}",
                                               "cable repair ships ready worldwide", "", "Source: International Cable Protection Committee"),
    "chart_cable_length": lambda: counter_card("chart_cable_length", 9.0, lambda g: f"{1.5 * g:.1f} million km",
                                               "of cable on the seabed", "more than 600 systems, active and planned", "Source: TeleGeography"),
}


if __name__ == "__main__":
    names = sys.argv[1:] or list(ALL)
    for n in names:
        ALL[n]()
