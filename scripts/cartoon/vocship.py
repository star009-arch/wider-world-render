"""Code-drawn ships for the VOC pilot (Premium 2D style). Side view, facing right; every part animates.

  ship(t, L=900, ports=0.0, era=1620, sails=1.0, flag_era=1620) -> (RGBA image, (ax, ay))
      ax, ay = the waterline centre inside the image. Composite with the pitch/heave from motion(t).
  motion(t, sea=1.0) -> (pitch_degrees, heave_px)
  longboat(t, L=260, rowers=0, oar_phase=t) -> (RGBA image, (ax, ay))

1620s East Indiaman (visual research section 1): three masts, square sails on fore and main (course + topsail +
small topgallant), a lateen on the mizzen, a spritsail under the bowsprit, NO jibs; high square stern with carving;
ochre/varnished upper works over tarred black lower hull; red-inside gun-port lids; the orange-white-blue flag before
about 1630 (red-white-blue for the 1740s).
"""
from __future__ import annotations

import math

from PIL import Image

import vocart as A

INK = A.INK
TAR = (40, 34, 30)
WOOD = (176, 122, 66)
WOOD_D = (128, 84, 44)
OCHRE = (204, 160, 82)
GREEN = (46, 92, 70)
RED = (168, 52, 40)
CANVAS = A.hexc("#D8C9A3")
CANVAS_L = (240, 232, 210)
GOLD = (214, 172, 70)


def motion(t, sea=1.0):
    pitch = sea * (1.6 * math.sin(t * 0.9) + 0.5 * math.sin(t * 2.1 + 1.0))
    heave = sea * (6 * math.sin(t * 0.9 + 0.7) + 2 * math.sin(t * 1.7))
    return pitch, heave


def _flag(Lr: A.Layer, x, y, w, h, t, colours, ink=2.5, phase=0.0):
    """A waving flag attached at its left edge (x, y top). Stripes top to bottom."""
    n = 10
    rows = len(colours)
    for r, col in enumerate(colours):
        top, bot = [], []
        for i in range(n + 1):
            k = i / n
            wave = math.sin(t * 5 + k * 5 + phase) * h * 0.12 * k
            top.append((x + w * k, y + h * r / rows + wave))
            bot.append((x + w * k, y + h * (r + 1) / rows + wave))
        Lr.poly(top + bot[::-1], col, 0)
    edge_t = [(x + w * i / n, y + math.sin(t * 5 + i / n * 5 + phase) * h * 0.12 * i / n) for i in range(n + 1)]
    edge_b = [(px, py + h) for px, py in edge_t]
    Lr.line(edge_t, INK, ink); Lr.line(edge_b, INK, ink)
    Lr.line([edge_t[-1], edge_b[-1]], INK, ink); Lr.line([(x, y), (x, y + h)], INK, ink)


def _pennant(Lr, x, y, ln, t, col=(200, 60, 40), phase=0.0):
    pts_t, pts_b = [], []
    for i in range(12):
        k = i / 11
        wave = math.sin(t * 6 - k * 6 + phase) * 7 * k
        w = 7 * (1 - k) + 1
        pts_t.append((x - ln * k, y + wave - w / 2)); pts_b.append((x - ln * k, y + wave + w / 2))
    Lr.poly(pts_t + pts_b[::-1], col, 1.8)


def _square_sail(Lr, cx, top, bottom, w_top, w_bot, billow, t, phase=0.0):
    """A square sail seen from the side-ish 3/4: a trapezoid whose leading edge bellies forward with the wind."""
    flutter = math.sin(t * 2.3 + phase) * 0.12 + 1
    b = billow * flutter
    pts = []
    n = 8
    for i in range(n + 1):                                            # top edge (yard)
        k = i / n
        pts.append((cx - w_top / 2 + w_top * k, top))
    for i in range(1, n + 1):                                         # leading (right) edge bulging forward
        k = i / n
        pts.append((cx + w_top / 2 + (w_bot - w_top) / 2 * k + b * math.sin(math.pi * k) * 0.55, top + (bottom - top) * k))
    for i in range(1, n + 1):                                         # foot, curving up in the middle
        k = i / n
        pts.append((cx + w_bot / 2 - w_bot * k, bottom - b * 0.25 * math.sin(math.pi * k)))
    for i in range(1, n):                                             # trailing edge
        k = i / n
        pts.append((cx - w_bot / 2 + (w_bot - w_top) / 2 * k - b * 0.15 * math.sin(math.pi * k), bottom - (bottom - top) * k))
    Lr.poly(pts, CANVAS, 3.0)
    # cel shade: the belly in shadow (light from upper left), a highlight strip near the yard
    sh = [(x + (cx - x) * 0.0, y) for x, y in pts]
    mid = [(cx + (x - cx) * 0.35 + b * 0.2, y) for x, y in pts[n:2 * n + 1]]
    Lr.shade_poly(pts[n:2 * n + 1] + mid[::-1], A.shade(CANVAS, 0.82), 220)
    Lr.shade_poly([(cx - w_top / 2 + 6, top + 4), (cx + w_top / 2 - 6, top + 4), (cx + w_top / 2 - 10, top + 12), (cx - w_top / 2 + 10, top + 12)], CANVAS_L, 200)
    # seams
    for i in range(1, 4):
        k = i / 4
        x0 = cx - w_top / 2 + w_top * k
        x1 = cx - w_bot / 2 + w_bot * k + b * 0.25
        Lr.line([(x0, top + 3), ((x0 + x1) / 2 + b * 0.2, (top + bottom) / 2), (x1, bottom - 3)], A.shade(CANVAS, 0.7), 1.2, curve=True)
    Lr.line([(cx - w_top / 2 - 10, top), (cx + w_top / 2 + 10, top)], INK, 5)   # the yard


def ship(t, L=900, ports=0.0, era=1620, sails=1.0, billow=None):
    """Returns the ship sprite and its waterline centre. Coordinates below are in units of L/100."""
    u = L / 100.0
    PW, PH = int(L * 1.5), int(L * 1.3)
    Lr = A.Layer(PW, PH)
    ax, ay = PW * 0.5, PH * 0.78                                      # waterline centre
    X = lambda v: ax + v * u
    Y = lambda v: ay - v * u
    billow = (9 * u * sails) if billow is None else billow

    # ---- masts and rigging behind the sails
    masts = [(-26, 70), (2, 82), (28, 58)]                            # (x, height) fore, main, mizzen (bow is to the right)
    masts = [(-mx, h) for mx, h in masts]                             # bow to the right: fore mast at +26
    # shrouds (behind)
    for mx, h in masts:
        for k in (-4, -1.5, 1.5, 4):
            Lr.line([(X(mx + k), Y(9)), (X(mx), Y(h * 0.55))], A.shade(TAR, 1.2), 1.4)
            Lr.line([(X(mx + k * 0.6), Y(h * 0.58)), (X(mx), Y(h * 0.86))], A.shade(TAR, 1.2), 1.2)
    # stays (bow-ward)
    Lr.line([(X(masts[0][0]), Y(masts[0][1] * 0.86)), (X(50), Y(14))], A.shade(TAR, 1.2), 1.6)
    Lr.line([(X(masts[1][0]), Y(masts[1][1] * 0.86)), (X(masts[0][0]), Y(masts[0][1] * 0.5))], A.shade(TAR, 1.2), 1.4)
    Lr.line([(X(masts[2][0]), Y(masts[2][1] * 0.86)), (X(masts[1][0]), Y(masts[1][1] * 0.48))], A.shade(TAR, 1.2), 1.4)
    for mx, h in masts:
        Lr.poly([(X(mx) - 0.9 * u, Y(8)), (X(mx) + 0.9 * u, Y(8)), (X(mx) + 0.5 * u, Y(h)), (X(mx) - 0.5 * u, Y(h))], WOOD, 2.5)
        Lr.rect((X(mx) - 2.4 * u, Y(h * 0.56) - 0.8 * u, X(mx) + 2.4 * u, Y(h * 0.56) + 0.6 * u), WOOD_D, 2)   # top (platform)
    # bowsprit
    Lr.poly([(X(40), Y(12)), (X(64), Y(26)), (X(64.6), Y(25)), (X(41), Y(10.5))], WOOD, 2.5)

    # ---- sails (back to front): mizzen lateen, main, fore, spritsail
    if sails > 0:
        mmx, mh = masts[2]
        sw = math.sin(t * 2.0) * 0.6
        lat = [(X(mmx - 12), Y(14)), (X(mmx + 9), Y(mh * 0.86)), (X(mmx + 6 + sw), Y(mh * 0.55)), (X(mmx + 3), Y(20))]
        Lr.blob(lat, CANVAS, 3, n=4)
        Lr.line([(X(mmx - 13), Y(13)), (X(mmx + 10), Y(mh * 0.88))], INK, 4)
        for (mx, h), ph in zip(masts[:2][::-1], (0.0, 1.3)):
            _square_sail(Lr, X(mx), Y(h * 0.52), Y(18), 15 * u, 19 * u, billow, t, ph)          # course
            _square_sail(Lr, X(mx), Y(h * 0.84), Y(h * 0.56), 11 * u, 14 * u, billow * 0.8, t, ph + 0.7)  # topsail
            _square_sail(Lr, X(mx), Y(h * 0.98), Y(h * 0.87), 6 * u, 8 * u, billow * 0.5, t, ph + 1.5)    # topgallant
        _square_sail(Lr, X(54), Y(22), Y(11), 7 * u, 8 * u, billow * 0.5, t, 2.0)                  # spritsail

    # ---- hull (explicit curves; bow to the right, y up from the waterline)
    def bez(p0, p1, p2, n=10):
        return [((1 - k) ** 2 * p0[0] + 2 * (1 - k) * k * p1[0] + k * k * p2[0],
                 (1 - k) ** 2 * p0[1] + 2 * (1 - k) * k * p1[1] + k * k * p2[1]) for k in (i / n for i in range(n + 1))]

    def sheer(x):                                                     # deck line: low waist, rising to stern and bow
        return 15 + (0.0042 * (x + 8) ** 2 if x < -8 else 0.0026 * (x + 8) ** 2) + (5 if x < -30 else 0)

    stern_top = [(-46, 31), (-38.5, 31)]
    deck = [(x, sheer(x)) for x in range(-38, 45, 2)]
    bow = bez((44, sheer(44)), (51, 14), (49, 5)) + bez((49, 5), (46, -3), (36, -6))
    bottom = bez((36, -6), (0, -9), (-36, -6))
    stern = bez((-36, -6), (-44, -3), (-45, 6)) + [(-46, 18), (-46, 31)]
    outline = stern_top + deck + bow[1:] + bottom[1:] + stern[1:]
    HP = [(X(x), Y(y)) for x, y in outline]
    Lr.poly(HP, OCHRE, 4.0)
    # tarred bottom band at the waterline (mostly under water)
    tar = [(X(x), Y(y)) for x, y in bez((48.6, 3.5), (46, -3), (36, -6)) + bottom[1:] + bez((-36, -6), (-44, -3), (-45, 3.5))[1:]]
    Lr.poly(tar, TAR, 0)
    Lr.line([(X(-45), Y(3.5)), (X(48.6), Y(3.5))], INK, 2.4)
    # hull shading: lower half of the side in cel shadow (sun from the upper left), highlight under the rail
    Lr.shade_poly([(X(x), Y(8.5 + 0.35 * (sheer(x) - 15))) for x in range(-45, 47, 3)] + [(X(47.5), Y(3.6)), (X(-45), Y(3.6))], A.shade(OCHRE, 0.8), 255)
    # wales: three dark bands following the sheer
    for off, wcol, wid in ((-6.0, TAR, 2.6), (-2.6, TAR, 2.2), (0.0, GREEN, 3.4)):
        pts = [(X(x), Y(sheer(x) + off)) for x in range(-45, 46, 3)]
        Lr.line(pts, INK, wid + 1.6)
        Lr.line(pts, wcol, wid)
    # painted bulwark band (green with gold trim) between the top wale and the rail
    band = [(X(x), Y(sheer(x) + 0.6)) for x in range(-38, 44, 2)] + [(X(x), Y(sheer(x) + 3.2)) for x in range(43, -39, -2)]
    Lr.poly(band, GREEN, 1.6)
    Lr.line([(X(x), Y(sheer(x) + 3.4)) for x in range(-38, 44, 2)], GOLD, 1.6)
    for x in range(-34, 42, 6):                                       # gold roundels on the band
        Lr.ellipse((X(x) - 0.55 * u, Y(sheer(x) + 1.9) - 0.55 * u, X(x) + 0.55 * u, Y(sheer(x) + 1.9) + 0.55 * u), GOLD, 1.2)
    # stern castle: raked transom with windows and carving
    # stern: a stern gallery with lit windows set into the raised poop, and a carved gold rail on top
    Lr.poly([(X(-45.6), Y(29.5)), (X(-36), Y(29.5)), (X(-36), Y(24)), (X(-45.8), Y(24))], WOOD_D, 2.4)
    for wx in (-43.6, -40.8, -38.0):
        Lr.rect((X(wx) - 0.8 * u, Y(26.8) - 1.2 * u, X(wx) + 0.8 * u, Y(26.8) + 1.2 * u), (250, 206, 110), 1.6)
    Lr.line([(X(-46), Y(31.2)), (X(-40), Y(32.2)), (X(-34), Y(sheer(-34) + 3.9))], GOLD, 2.6)
    for px in (-45, -42, -39):
        Lr.line([(X(px), Y(31.4)), (X(px), Y(29.6))], GOLD, 1.6)
    # beakhead with a red lion figurehead
    Lr.poly([(X(47), Y(14.5)), (X(55), Y(16)), (X(55.5), Y(14)), (X(49.5), Y(10))], OCHRE, 2.6)
    Lr.ellipse((X(54.4) - 1.5 * u, Y(16.5) - 1.5 * u, X(54.4) + 1.5 * u, Y(16.5) + 1.5 * u), (196, 66, 40), 2.2)
    # gun ports on the gun deck (lids hinge at the top; ripple open from stern to bow; muzzles roll out)
    for gx in range(-32, 40, 8):
        gy = sheer(gx) - 4.3
        x0, y0, x1, y1 = X(gx) - 1.5 * u, Y(gy) - 1.4 * u, X(gx) + 1.5 * u, Y(gy) + 1.4 * u
        k = max(0.0, min(1.0, ports * 1.5 - (gx + 32) / 72 * 0.5))
        Lr.rect((x0, y0, x1, y1), (34, 20, 16) if k > 0.02 else WOOD_D, 2)
        if k > 0.02:
            mz = 2.2 * u * min(1, k * 1.4)
            Lr.rect((X(gx) - 0.4 * u, Y(gy) - 0.55 * u, X(gx) + mz, Y(gy) + 0.55 * u), (58, 58, 64), 1.6)
            lift = 2.8 * u * k                                        # lid swings up and outwards
            Lr.poly([(x0, y0), (x1, y0), (x1 + 0.4 * u * k, y0 - lift), (x0 + 0.4 * u * k, y0 - lift)], RED, 1.8)
    # deck rail line and stern lantern
    Lr.line([(X(x), Y(sheer(x) + 3.9)) for x in range(-38, 44, 2)], INK, 2.0)
    Lr.line([(X(-46.8), Y(34)), (X(-46.8), Y(36.5))], INK, 2)
    Lr.ellipse((X(-46.8) - 1.1 * u, Y(38.2) - 1.6 * u, X(-46.8) + 1.1 * u, Y(38.2) + 1.6 * u), (250, 214, 120), 2)

    # ---- flags: stern ensign and masthead pennants
    fcols = [(224, 116, 40), (246, 242, 230), (40, 70, 140)] if era < 1640 else [(178, 40, 40), (246, 242, 230), (40, 70, 140)]
    Lr.line([(X(-46), Y(31)), (X(-50), Y(46))], WOOD_D, 3)
    _flag(Lr, X(-50) - 13 * u, Y(46), 13 * u, 8.5 * u, t, fcols, phase=0.0)
    # (flag hangs to the left: draw mirrored by placing it left of the staff; wave goes leftwards)
    for (mx, h), ph in zip(masts, (0.3, 0.9, 1.6)):
        _pennant(Lr, X(mx), Y(h) - 1, 16 * u, t, (214, 72, 40), ph)
    img = Lr.out()
    return img, (int(ax), int(ay))


def longboat(t, L=260, rowers=0, oar_phase=None, cloth=((240, 236, 222), (40, 60, 120))):
    """An open boat seen from the side with oars that sweep (rowers drawn by the caller, or simple hats/backs here)."""
    u = L / 100.0
    PW, PH = int(L * 1.4), int(L * 0.9)
    Lr = A.Layer(PW, PH)
    ax, ay = PW * 0.5, PH * 0.6
    X = lambda v: ax + v * u
    Y = lambda v: ay - v * u
    ph = t * 3.6 if oar_phase is None else oar_phase
    for i in range(3):                                                # oars behind
        ox = -24 + i * 22
        a = math.sin(ph + i * 0.2)
        Lr.line([(X(ox), Y(8)), (X(ox - 14 - a * 12), Y(-10 + abs(a) * 6))], WOOD_D, 3.2)
    for i in range(rowers):                                           # simple rower silhouettes (backs, hats)
        rx = -22 + i * (44 / max(1, rowers - 1))
        lean = math.sin(ph) * 3
        Lr.blob([(X(rx - 4 + lean), Y(8)), (X(rx - 3 + lean), Y(19)), (X(rx + 3 + lean), Y(19)), (X(rx + 4 + lean), Y(8))], cloth[i % 2], 2.4, n=3)
        Lr.ellipse((X(rx + lean) - 3.4 * u, Y(24) - 3.4 * u, X(rx + lean) + 3.4 * u, Y(24) + 3.4 * u), (226, 186, 150), 2.2)
        Lr.poly([(X(rx + lean - 6), Y(26)), (X(rx + lean + 6), Y(26)), (X(rx + lean), Y(31))], (30, 30, 34), 2)
    hull = [(-46, 14), (-40, 2), (-20, -3), (20, -3), (40, 2), (48, 16), (30, 11), (-30, 11)]
    Lr.blob(hull, (150, 100, 58), 3.2, n=5)
    Lr.line([(X(-44), Y(12)), (X(0), Y(9.5)), (X(46), Y(14))], (96, 62, 34), 2.6, curve=True)
    Lr.shade_poly([(X(-40), Y(4)), (X(40), Y(4)), (X(20), Y(-2.5)), (X(-20), Y(-2.5))], (0, 0, 0), 50)
    for i in range(3):                                                # oars in front
        ox = -14 + i * 22
        a = math.sin(ph + i * 0.2 + 0.4)
        Lr.line([(X(ox), Y(10)), (X(ox - 16 - a * 14), Y(-12 + abs(a) * 7))], WOOD, 3.6)
    return Lr.out(), (int(ax), int(ay))


def place(frame, t, x, y, L=760, ports=0.0, facing=-1, sea=1.0, water=(47, 163, 163), era=1620, wake=True):
    """Composite a sailing ship onto a frame so it SITS in the water: pitch and heave, hull cut at the waterline,
    a reflection, a foam line, a bow wave and a wake. (x, y) = waterline centre on the frame. facing -1 = sailing left."""
    from PIL import ImageDraw, ImageChops
    im, (ax, ay) = ship(t, L=L, ports=ports, era=era)
    if facing < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        ax = im.width - ax
    pitch, heave = motion(t, sea)
    im = im.rotate(pitch * (-facing), resample=Image.BICUBIC, center=(ax, ay))
    ox, oy = int(x - ax), int(y - ay + heave)
    # reflection: the hull and sails flipped, squashed and tinted with the water, under the waterline
    refl = im.transpose(Image.FLIP_TOP_BOTTOM).resize((im.width, int(im.height * 0.34)))
    tint = Image.new("RGBA", refl.size, water + (255,))
    fade = Image.linear_gradient("L").resize(refl.size).point(lambda v: int(max(0, 255 - v * 1.6)))   # strong near the hull, gone below
    from PIL import ImageChops as _C
    alpha = _C.multiply(refl.getchannel("A").point(lambda v: v * 0.3), fade)
    refl = Image.blend(refl, tint, 0.55)
    refl.putalpha(alpha)
    ry = int(y + heave) - int(refl.height * (1 - ay / im.height)) + 4
    frame.alpha_composite(refl, (ox, ry))
    # cut the hull at the waterline
    cut = Image.new("L", im.size, 255)
    ImageDraw.Draw(cut).rectangle([0, int(ay + 6 - heave * 0), im.width, im.height], fill=0)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), cut))
    frame.alpha_composite(im, (ox, oy))
    # foam along the waterline, a bow wave and a wake
    d = ImageDraw.Draw(frame, "RGBA")
    u = L / 100
    wl = y + heave + 6
    bow = x + facing * 50 * u
    pts = [(x - 48 * u + i * 4 * u, wl + 3 * math.sin(t * 4 + i)) for i in range(25)]
    d.line(pts, fill=(250, 252, 250, 200), width=int(2 + u * 0.3))
    for i in range(6):
        k = i / 5
        sx = bow + facing * (4 + 10 * k) * u * 0.6
        d.arc([sx - 14 * u * (0.5 + k), wl - 4 * u * (0.4 + k), sx + 14 * u * (0.5 + k), wl + 4 * u * (0.4 + k)],
              200 if facing < 0 else 270, 270 if facing < 0 else 340, fill=(250, 252, 250, int(220 * (1 - k))), width=3)
    if wake:
        for i in range(8):
            ph = (t * 0.6 + i / 8) % 1.0
            wx = x - facing * (48 + ph * 90) * u
            r = (6 + 30 * ph) * u * 0.5
            d.arc([wx - r * 2, wl - r * 0.3 + 2, wx + r * 2, wl + r * 0.5 + 2], 190, 350, fill=(250, 252, 250, int(200 * (1 - ph))), width=3)
