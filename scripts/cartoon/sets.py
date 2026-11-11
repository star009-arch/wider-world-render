"""Backgrounds for the cartoon format, drawn by code (no AI, no stock): palace, fort, battlefield, card, map.

Every set is drawn once per shot on a 2x canvas and downsampled to 1920x1080. Maps use Natural Earth (public domain):
the 1:50m shaded-relief raster for the "satellite" look plus country polygons for the bold fills.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
ROOT = Path(__file__).resolve().parents[2]
NE = ROOT / "data" / "geo" / "naturalearth"
INK = (34, 28, 30)


def font(size, bold=True):
    for f in (["C:/Windows/Fonts/impact.ttf"] if bold == "impact" else []) + \
             ["C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _canvas(color):
    return Image.new("RGB", (W * 2, H * 2), color)


def _down(img):
    return img.resize((W, H), Image.LANCZOS)


def palace(seed=1):
    """Mughal throne room: cusped arches, columns, a carpet, a raised throne platform."""
    im = _canvas((236, 214, 178))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W * 2, 1300], fill=(240, 222, 188))
    for i in range(6):                                                              # arches along the back wall
        x0 = 120 + i * 620
        d.rectangle([x0, 260, x0 + 500, 1300], fill=(222, 196, 156), outline=INK, width=8)
        d.rectangle([x0 + 60, 520, x0 + 440, 1300], fill=(118, 160, 186), outline=INK, width=8)   # sky through the arch
        d.pieslice([x0 + 60, 330, x0 + 440, 710], 180, 360, fill=(118, 160, 186), outline=INK, width=8)
        d.rectangle([x0 + 66, 520, x0 + 434, 528], fill=(118, 160, 186))
        for k in range(3):                                                          # cusps
            cx = x0 + 150 + k * 100
            d.ellipse([cx - 40, 330, cx + 40, 410], fill=(222, 196, 156), outline=INK, width=6)
        d.rectangle([x0 - 40, 240, x0 + 20, 1300], fill=(204, 172, 128), outline=INK, width=6)  # column
    d.rectangle([0, 1300, W * 2, H * 2], fill=(150, 46, 52))                         # floor carpet
    for k in range(10):
        d.line([(0, 1360 + k * 80), (W * 2, 1360 + k * 80)], fill=(176, 70, 66), width=6)
    d.rectangle([0, 1300, W * 2, 1336], fill=(214, 172, 80))
    # throne platform + throne
    d.polygon([(1340, 1460), (2500, 1460), (2620, 1640), (1220, 1640)], fill=(212, 170, 78), outline=INK)
    d.rounded_rectangle([1640, 780, 2200, 1470], radius=120, fill=(200, 40, 56), outline=INK, width=10)
    d.rounded_rectangle([1700, 840, 2140, 1300], radius=90, fill=(232, 196, 92), outline=INK, width=8)
    d.ellipse([1860, 700, 1980, 820], fill=(232, 196, 92), outline=INK, width=8)
    return _down(im)


def fort():
    """A Company fort at Calcutta: brick wall, gate, cannon, the Company's striped flag, river behind."""
    im = _canvas((170, 210, 232))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 900, W * 2, 1200], fill=(96, 148, 176))                          # the river (Hooghly)
    d.rectangle([0, 1200, W * 2, H * 2], fill=(196, 176, 130))
    rnd = random.Random(3)
    d.rectangle([300, 560, 3500, 1500], fill=(176, 92, 70), outline=INK, width=10)   # wall
    for row in range(12):
        y = 580 + row * 78
        off = 0 if row % 2 else 60
        for k in range(28):
            x = 300 + off + k * 120
            if x + 110 < 3500:
                d.rectangle([x, y, x + 110, y + 70], outline=(150, 74, 56), width=5)
    for k in range(14):                                                             # battlements
        x = 300 + k * 240
        d.rectangle([x, 470, x + 130, 570], fill=(176, 92, 70), outline=INK, width=8)
    d.rectangle([1700, 980, 2140, 1500], fill=(80, 54, 40), outline=INK, width=10)   # gate
    d.pieslice([1700, 860, 2140, 1100], 180, 360, fill=(80, 54, 40), outline=INK, width=10)
    # flagpole + Company striped ensign (red and white stripes)
    d.line([(3200, 120), (3200, 480)], fill=INK, width=14)
    for k in range(7):
        d.rectangle([3207, 140 + k * 26, 3560, 166 + k * 26], fill=(196, 40, 44) if k % 2 == 0 else (245, 245, 245))
    d.rectangle([3207, 140, 3380, 244], fill=(245, 245, 245))                       # white canton, red cross (not a US flag)
    d.rectangle([3207, 180, 3380, 204], fill=(196, 40, 44))
    d.rectangle([3282, 140, 3306, 244], fill=(196, 40, 44))
    d.rectangle([3207, 140, 3560, 322], outline=INK, width=6)
    # a cannon on the wall
    d.rounded_rectangle([700, 420, 1100, 500], radius=40, fill=(60, 60, 64), outline=INK, width=8)
    d.ellipse([760, 470, 880, 590], fill=(120, 80, 50), outline=INK, width=8)
    return _down(im)


def battlefield(rain=False):
    """Plassey: green plain, mango grove, low sky; optional rain streaks."""
    im = _canvas((128, 140, 156) if rain else (176, 214, 236))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 860, W * 2, H * 2], fill=(118, 160, 84) if not rain else (96, 132, 76))
    for k in range(9):                                                              # mango grove on the horizon
        x = 120 + k * 430
        d.rectangle([x + 110, 700, x + 150, 900], fill=(96, 66, 40), outline=INK, width=6)
        d.ellipse([x, 540, x + 260, 760], fill=(60, 120, 60), outline=INK, width=8)
        d.ellipse([x + 60, 500, x + 220, 640], fill=(70, 134, 66), outline=INK, width=6)
    for k in range(40):                                                             # grass tufts
        rnd = random.Random(k)
        x, y = rnd.randint(0, W * 2), rnd.randint(1000, H * 2 - 40)
        d.line([(x, y), (x - 14, y - 30)], fill=(80, 120, 60), width=6)
        d.line([(x, y), (x + 12, y - 28)], fill=(80, 120, 60), width=6)
    if rain:
        for k in range(5):                                                          # low rain clouds
            cx = 300 + k * 820
            d.ellipse([cx - 420, 60, cx + 420, 420], fill=(108, 118, 132))
    return _down(im)


def rain_layer(t):
    """Transparent rain streaks that move with time t (seconds)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(11)
    for k in range(260):
        x0, y0 = rnd.randint(-200, W), rnd.randint(0, H)
        y = (y0 + t * 1400) % (H + 100) - 50
        x = x0 + (y - y0) * 0.25
        d.line([(x, y), (x + 8, y + 34)], fill=(220, 230, 245, 150), width=2)
    return lay


def card(color=(250, 247, 240)):
    return Image.new("RGB", (W, H), color)


# --------------------------------------------------------------------------------------------------- maps
def _countries():
    import shapefile                                                                # pyshp
    sf = shapefile.Reader(str(NE / "ne_50m_admin_0_countries" / "ne_50m_admin_0_countries"))
    names = [f[0] for f in sf.fields[1:]]
    i = names.index("ADMIN")
    out = {}
    for rec, shp in zip(sf.iterRecords(), sf.iterShapes()):
        out[rec[i]] = shp
    return out


def _proj(bbox):
    lon0, lat0, lon1, lat1 = bbox
    k = 1 / math.cos(math.radians((lat0 + lat1) / 2))
    w, h = lon1 - lon0, (lat1 - lat0) * k
    if w / h < W / H:
        w = h * W / H
    else:
        h = w * H / W
    cx, cy = (lon0 + lon1) / 2, (lat0 + lat1) / 2
    L0, T = cx - w / 2, cy + h / 2 / k
    return lambda lon, lat: ((lon - L0) / w * W * 2, (T - lat) * k / h * H * 2), (L0, cx + w / 2, T, cy - h / 2 / k)


BENGAL = [(85.8, 21.6), (86.9, 22.6), (88.0, 21.6), (89.0, 21.7), (90.6, 22.2), (91.8, 22.4), (92.3, 21.4), (92.6, 23.0),
          (92.2, 24.2), (91.3, 25.1), (90.0, 25.3), (89.8, 26.2), (88.4, 26.5), (88.1, 25.6), (87.2, 25.3), (86.4, 24.7),
          (85.9, 23.6)]                                                             # simplified Bengal Subah, 1750s


def india_map(highlight="bengal", fill=(54, 98, 214), company=False):
    """Satellite-style relief basemap, the subcontinent in a bold blue, Bengal highlighted (or red for the Company)."""
    bbox = (64, 5, 98, 37)
    proj, (L0, L1, T, B) = _proj(bbox)
    rel = Image.open(NE / "NE1_50M_SR_W" / "NE1_50M_SR_W" / "NE1_50M_SR_W.tif").convert("RGB")
    rw, rh = rel.size
    crop = rel.crop((int((L0 + 180) / 360 * rw), int((90 - T) / 180 * rh), int((L1 + 180) / 360 * rw), int((90 - B) / 180 * rh)))
    im = crop.resize((W * 2, H * 2), Image.BICUBIC)
    im = Image.blend(im, Image.new("RGB", im.size, (20, 40, 70)), 0.25)             # darker, so fills pop
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cs = _countries()
    for name in ("India", "Pakistan", "Bangladesh"):
        shp = cs.get(name)
        if not shp:
            continue
        parts = list(shp.parts) + [len(shp.points)]
        for a, b in zip(parts[:-1], parts[1:]):
            pts = [proj(*p) for p in shp.points[a:b]]
            if len(pts) > 2:                                                        # no modern borders: fill only
                d.polygon(pts, fill=fill + (235,))
    bp = [proj(*p) for p in BENGAL]
    d.polygon(bp, fill=((200, 40, 44, 245) if company else (255, 196, 40, 245)), outline=(255, 255, 255, 255), width=8)
    im = im.convert("RGBA")
    im.alpha_composite(lay)
    return _down(im.convert("RGB")), (lambda lon, lat: tuple(v / 2 for v in proj(lon, lat)))


if __name__ == "__main__":
    out = Path("D:/Temp/cartoon")
    tiles = [palace(), fort(), battlefield(rain=True), india_map()[0]]
    g = Image.new("RGB", (W, H))
    for i, t in enumerate(tiles):
        g.paste(t.resize((W // 2, H // 2)), ((i % 2) * W // 2, (i // 2) * H // 2))
    g.save(out / "sets.png")
    print("ok")


# ------------------------------------------------------------------------------------------- worldwide additions
def tudor_court():
    """Elizabethan hall: oak panelling, red tapestries, leaded windows, a raised throne under a canopy."""
    im = _canvas((120, 82, 50))
    d = ImageDraw.Draw(im)
    for k in range(12):                                                              # oak panels
        x = k * 330
        d.rectangle([x + 10, 200, x + 320, 1300], fill=(132, 92, 56), outline=(80, 52, 30), width=8)
        d.rectangle([x + 50, 260, x + 280, 700], outline=(96, 64, 38), width=6)
        d.rectangle([x + 50, 760, x + 280, 1240], outline=(96, 64, 38), width=6)
    for x in (300, 2900):                                                           # leaded windows
        d.rectangle([x, 260, x + 620, 900], fill=(190, 214, 228), outline=INK, width=10)
        for k in range(1, 6):
            d.line([(x + k * 104, 260), (x + k * 104, 900)], fill=(90, 90, 96), width=5)
        for k in range(1, 6):
            d.line([(x, 260 + k * 107), (x + 620, 260 + k * 107)], fill=(90, 90, 96), width=5)
    d.rectangle([1400, 140, 2440, 1180], fill=(150, 30, 50), outline=INK, width=10)  # canopy of estate
    d.rectangle([1400, 140, 2440, 260], fill=(212, 170, 60), outline=INK, width=8)
    d.rectangle([0, 1300, W * 2, H * 2], fill=(98, 70, 46))                         # floor boards
    for k in range(14):
        d.line([(k * 290, 1300), (k * 290 - 300, H * 2)], fill=(80, 56, 36), width=6)
    d.polygon([(1300, 1340), (2540, 1340), (2700, 1560), (1140, 1560)], fill=(160, 40, 56), outline=INK)   # dais
    return _down(im)


def sea(stormy=False):
    """Open ocean under a big sky; ships are drawn on top as sprites."""
    im = _canvas((150, 200, 236) if not stormy else (120, 136, 156))
    d = ImageDraw.Draw(im)
    for k in range(6):
        cx = 200 + k * 700
        d.ellipse([cx - 260, 160 + (k % 2) * 80, cx + 260, 360 + (k % 2) * 80], fill=(250, 252, 255) if not stormy else (150, 160, 176))
    d.rectangle([0, 1180, W * 2, H * 2], fill=(46, 104, 170))
    for row in range(8):
        y = 1240 + row * 110
        for k in range(18):
            x = k * 240 + (row % 2) * 120
            d.arc([x, y, x + 200, y + 60], 200, 340, fill=(130, 180, 224), width=8)
    return _down(im)


def flag(d, x, y, kind, s=1.0, wave=0.0):
    """Flags on a pole: 'company' (red/white stripes, red-cross canton), 'nawab' (green with a gold crescent),
    'england' (St George's cross). (x, y) = top of the pole in 1x pixels."""
    d.line([(x, y), (x, y + 120 * s)], fill=INK + (255,), width=max(3, int(5 * s)))
    w, h = 90 * s, 58 * s
    off = math.sin(wave) * 4 * s
    if kind == "company":
        for k in range(7):
            d.rectangle([x, y + k * h / 7 + off * (k % 2), x + w, y + (k + 1) * h / 7 + off * (k % 2)], fill=((196, 40, 44) if k % 2 == 0 else (245, 245, 245)) + (255,))
        d.rectangle([x, y, x + w * 0.42, y + h * 0.55], fill=(245, 245, 245, 255))
        d.rectangle([x, y + h * 0.22, x + w * 0.42, y + h * 0.33], fill=(196, 40, 44, 255))
        d.rectangle([x + w * 0.16, y, x + w * 0.26, y + h * 0.55], fill=(196, 40, 44, 255))
    elif kind == "nawab":
        d.rectangle([x, y, x + w, y + h], fill=(30, 120, 70, 255))
        d.ellipse([x + w * 0.3, y + h * 0.18, x + w * 0.7, y + h * 0.82], fill=(232, 196, 92, 255))
        d.ellipse([x + w * 0.4, y + h * 0.14, x + w * 0.78, y + h * 0.74], fill=(30, 120, 70, 255))
    elif kind == "dutch":                                                       # Dutch Republic: orange, white, blue
        for k, c in enumerate([(232, 120, 30), (245, 245, 245), (30, 70, 150)]):
            d.rectangle([x, y + k * h / 3 + off * (k % 2), x + w, y + (k + 1) * h / 3 + off * (k % 2)], fill=c + (255,))
    elif kind == "england":
        d.rectangle([x, y, x + w, y + h], fill=(245, 245, 245, 255))
        d.rectangle([x, y + h * 0.4, x + w, y + h * 0.6], fill=(196, 40, 44, 255))
        d.rectangle([x + w * 0.4, y, x + w * 0.56, y + h], fill=(196, 40, 44, 255))
    d.rectangle([x, y, x + w, y + h], outline=INK + (255,), width=max(2, int(3 * s)))


def ship(d, x, y, s=1.0, t=0.0, flip=False, flag_kind="company"):
    """A three-masted East Indiaman, rocking gently. (x, y) = waterline centre, 1x pixels; s=1 is about 420 px long."""
    rock = math.sin(t * 2.0) * 6 * s
    k = -1 if flip else 1
    hull = [(x - 210 * s, y - 60 * s + rock), (x + 210 * s, y - 70 * s - rock), (x + 170 * s, y + 20 * s - rock), (x - 170 * s, y + 20 * s + rock)]
    if flip:
        hull = [(2 * x - px, py) for px, py in hull]
    d.polygon(hull, fill=(110, 70, 40, 255), outline=INK + (255,))
    d.line([(x - 190 * s, y - 40 * s + rock), (x + 190 * s, y - 48 * s - rock)], fill=(214, 170, 60, 255), width=max(2, int(8 * s)))
    for i in range(5):                                                               # gun ports
        px = x + (-120 + i * 60) * s
        d.rectangle([px - 10 * s, y - 28 * s, px + 10 * s, y - 14 * s], fill=INK + (255,))
    for j, (mx, mh) in enumerate([(-110, 300), (10, 360), (120, 260)]):
        mx = x + k * mx * s
        d.line([(mx, y - 60 * s), (mx, y - (60 + mh) * s)], fill=(80, 54, 34, 255), width=max(3, int(8 * s)))
        for row in range(2):                                                         # square sails
            top = y - (60 + mh - 30 - row * mh * 0.45) * s
            d.polygon([(mx - 70 * s, top), (mx + 70 * s, top), (mx + 80 * s + math.sin(t * 3 + j) * 6 * s, top + mh * 0.38 * s),
                       (mx - 80 * s, top + mh * 0.38 * s)], fill=(250, 246, 232, 255), outline=INK + (255,))
    flag(d, x + k * 10 * s, y - 440 * s, flag_kind, 0.9 * s, t * 4)


def world_map():
    """Europe-Africa-Asia on the relief raster, land lightly tinted; returns (image, projector to 1x pixels)."""
    bbox = (-30, -42, 112, 62)
    proj, (L0, L1, T, B) = _proj(bbox)
    rel = Image.open(NE / "NE1_50M_SR_W" / "NE1_50M_SR_W" / "NE1_50M_SR_W.tif").convert("RGB")
    rw, rh = rel.size
    crop = rel.crop((int((L0 + 180) / 360 * rw), int((90 - T) / 180 * rh), int((L1 + 180) / 360 * rw), int((90 - B) / 180 * rh)))
    im = crop.resize((W * 2, H * 2), Image.BICUBIC)
    im = Image.blend(im, Image.new("RGB", im.size, (20, 40, 70)), 0.18)
    return _down(im), (lambda lon, lat: tuple(v / 2 for v in proj(lon, lat)))


ROUTE_CAPE = [(-0.1, 51.5), (-6, 48), (-14, 30), (-20, 10), (-12, -15), (5, -32), (18.4, -36), (32, -36), (52, -27),
              (58, -10), (64, 5), (71, 17), (72.2, 12), (75, 7), (79.5, 5.5), (82, 9), (81.5, 14), (86, 19), (88.3, 21.8)]       # London - Cape - Bombay - Madras - Bengal
