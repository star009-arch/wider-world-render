"""Tiny Empires - "How a Company Took Over India" (English East India Company, 1600-1765): 3D background plates.

Loaded by blender_te.py (exec'd in its namespace, so mat/add/ph_sky/sun/camera_path/... are available). Every helper here is
prefixed eic_ so it cannot collide with other episode packs. Historical source: visual_bibles/04_east_india_company_1600-1765.md.

  e_spice_quay   Bantam/Banda-style spice port c.1600 at golden hour (opening shot)
  e_london       Thames-side London street c.1600: jettied timber houses, spireless Old St Paul's, London Bridge, ships
  e_whitehall    Elizabethan presence chamber: panelling, tapestries, carved screen, mullioned windows, cloth of estate
  e_deptford     Thames dockyard c.1600-10: galleon-type East Indiaman fitting out, treadwheel crane, timber, barrels
  e_ajmer_court  Jahangir's durbar at Ajmer 1616: red sandstone, jharokha, gilt rail, canopies, Lahore carpets
  e_surat        the English factory at Surat 1610s-50s: courtyard haveli, teak balconies, calico and indigo, the Tapti
  e_calcutta     old Fort William 1756 on the Hooghly: brick fort with corner bastions, warehouses, 1707 Union flag
  e_murshidabad  the Nawab's palace court c.1756: cusped arcades, Bengal chala roof, masnad, the Bhagirathi
  e_plassey      Plassey 23 June 1757: mango grove in rows inside its bank, hunting lodge, river, monsoon sky
  e_allahabad    Clive's tent, Aug 1765: chair-on-table throne under chintz, carpets, camp and fort outside
  e_hooghly      the Hooghly at golden hour: country boats, ghat, temple, palms and bamboo, distant factory
Generic period reconstructions, not exact replicas.
"""
import bmesh
import numpy as np
from mathutils import Matrix
from mathutils import noise as eic_noise

EIC_M = {}
EIC_SKY = {}


# ================================================================================================ colour + numpy patterns
def eic_srgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def eic_lin(h):
    return tuple(float(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92) for v in eic_srgb(h))


def eic_frac(a):
    return a - np.floor(a)


def eic_lt(d, aa):
    """Anti-aliased mask of d < 0."""
    return np.clip(0.5 - d / aa, 0.0, 1.0).astype(np.float32)


def eic_put(img, mask, col):
    c = eic_srgb(col) if isinstance(col, str) else np.asarray(col, np.float32)
    m = np.asarray(mask, np.float32)[..., None]
    img *= (1.0 - m)
    img += m * c


def eic_grid(W, H):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    return (x + 0.5) / W, (y + 0.5) / H


def eic_ell(X, Y, cx, cy, rx, ry, ang=0.0):
    c, s = np.cos(ang), np.sin(ang)
    dx, dy = X - cx, Y - cy
    a = (dx * c + dy * s) / rx
    b = (-dx * s + dy * c) / ry
    return np.sqrt(a * a + b * b) - 1.0


def eic_blur(img, k=1):
    out = img.copy()
    n = 1
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            if dx or dy:
                out += np.roll(np.roll(img, dy, 0), dx, 1)
                n += 1
    return out / n


def eic_weave(img, rng, cell=6, amt=0.08, knot=0.035):
    H, W = img.shape[:2]
    nz = rng.random((H // cell + 2, W // cell + 2)).astype(np.float32)
    nz = np.kron(nz, np.ones((cell, cell), np.float32))[:H, :W]
    nz = eic_blur(nz[..., None], 2)[..., 0]
    abr = 1.0 + 0.045 * np.sin(np.linspace(0, rng.uniform(3, 8), H) + rng.uniform(0, 6)).astype(np.float32)
    yi, xi = np.mgrid[0:H, 0:W]
    img *= ((1 - amt / 2) + amt * nz)[..., None] * abr[:, None, None]
    img *= (1.0 - knot * ((xi + yi) % 2))[..., None]
    return img


def eic_pat_carpet(W=512, H=768, seed=1, style="medallion", field="#8F2430", border="#203A63", gold="#D2A645",
                   ivory="#EFE3C8", green="#3C6B45", dark="#1B1F3A", extra="#C76A2A", sky="#4E7BA8"):
    """Knotted-pile carpet: 'medallion' (Persian/Mughal), 'pictorial' (Lahore c.1600: animals and trees on a red field),
    'ushak' (Turkey carpet: Star Ushak)."""
    rng = np.random.default_rng(seed)
    u, v = eic_grid(W, H)
    asp = H / W
    X, Y = u, v * asp
    aa = 1.6 / W
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(field)
    e = np.minimum(np.minimum(X, 1 - X), np.minimum(Y, asp - Y))
    cx0, cy0 = 0.5, asp / 2
    if style == "medallion":
        a, b = (X + Y) / 0.1, (X - Y) / 0.1
        fa, fb = eic_frac(a) - 0.5, eic_frac(b) - 0.5
        lat = np.minimum(np.abs(fa), np.abs(fb))
        eic_put(img, eic_lt(lat - 0.03, 0.03), green)
        rr = np.hypot(fa, fb)
        th = np.arctan2(fb, fa)
        cid = (np.floor(a) + 2 * np.floor(b)) % 3
        for k, col in enumerate((gold, ivory, sky)):
            eic_put(img, eic_lt(rr - 0.21 * (1 + 0.3 * np.cos(6 * th)), 0.03) * (cid == k), col)
        eic_put(img, eic_lt(rr - 0.06, 0.03), dark)
        dx, dy = (X - cx0) / 0.3, (Y - cy0) / 0.42
        r, t = np.hypot(dx, dy), np.arctan2(dy, dx)
        lob = 1 + 0.07 * np.cos(16 * t)
        for f, col in ((1.07, ivory), (1.0, dark), (0.72, gold), (0.66, field), (0.44, green), (0.38, ivory), (0.18, field), (0.08, gold)):
            eic_put(img, eic_lt(r - f * lob, 0.012), col)
        for sg in (-1, 1):
            d = eic_ell(X, Y, cx0, cy0 + sg * 0.52, 0.07, 0.055)
            eic_put(img, eic_lt(d, 0.05), ivory)
            eic_put(img, eic_lt(d + 0.3, 0.05), dark)
        for qx in (0.125, 0.875):
            for qy in (0.125, asp - 0.125):
                dx, dy = (X - qx) / 0.22, (Y - qy) / 0.22
                r, t = np.hypot(dx, dy), np.arctan2(dy, dx)
                lob = 1 + 0.07 * np.cos(14 * t)
                for f, col in ((1.06, ivory), (1.0, dark), (0.62, gold), (0.42, field)):
                    eic_put(img, eic_lt(r - f * lob, 0.02), col)
    elif style == "pictorial":
        placed = []
        for k in range(40):
            for _ in range(40):
                px, py = rng.uniform(0.2, 0.8), rng.uniform(0.2, asp - 0.2)
                if all(np.hypot(px - a_, py - b_) > 0.115 for a_, b_ in placed):
                    break
            placed.append((px, py))
            kind = ("tree", "animal", "animal", "bird", "bush")[k % 5]
            s = rng.uniform(0.045, 0.07)
            if kind == "tree":
                eic_put(img, (np.abs(X - px) < s * 0.1) & (Y > py - s * 0.3) & (Y < py + s * 1.0), "#5A3A22")
                eic_put(img, eic_lt(eic_ell(X, Y, px, py - s * 0.55, s * 0.75, s * 0.6), 0.06), green)
                for _ in range(5):
                    eic_put(img, eic_lt(eic_ell(X, Y, px + rng.uniform(-0.5, 0.5) * s, py - s * 0.55 + rng.uniform(-0.4, 0.4) * s,
                                                s * 0.1, s * 0.1), 0.2), (gold, ivory, "#7FA65A")[_ % 3])
            elif kind == "animal":
                col = (extra, ivory, gold, "#3A2A22")[rng.integers(0, 4)]
                dr = rng.choice([-1, 1])
                for lx in (-0.5, -0.3, 0.3, 0.5):
                    eic_put(img, (np.abs(X - (px + lx * s)) < s * 0.07) & (Y > py) & (Y < py + s * 0.6), col)
                eic_put(img, eic_lt(eic_ell(X, Y, px, py, s * 0.75, s * 0.32), 0.06), col)
                eic_put(img, eic_lt(eic_ell(X, Y, px + dr * s * 0.75, py - s * 0.32, s * 0.24, s * 0.18, 0.4 * dr), 0.08), col)
                eic_put(img, eic_lt(eic_ell(X, Y, px - dr * s * 0.85, py - s * 0.15, s * 0.3, s * 0.05, -0.7 * dr), 0.15), col)
                if col in (gold, extra):
                    for _ in range(4):
                        eic_put(img, eic_lt(eic_ell(X, Y, px + rng.uniform(-0.5, 0.5) * s, py + rng.uniform(-0.15, 0.15) * s, s * 0.07,
                                                    s * 0.07), 0.3), dark)
            elif kind == "bird":
                col = (ivory, sky, gold)[rng.integers(0, 3)]
                eic_put(img, eic_lt(eic_ell(X, Y, px, py, s * 0.4, s * 0.2), 0.08), col)
                eic_put(img, eic_lt(eic_ell(X, Y, px - s * 0.1, py - s * 0.22, s * 0.35, s * 0.1, 0.6), 0.1), dark)
                eic_put(img, eic_lt(eic_ell(X, Y, px + s * 0.42, py - s * 0.12, s * 0.12, s * 0.1), 0.15), col)
            else:
                eic_put(img, (np.abs(X - px) < s * 0.04) & (Y > py - s * 0.6) & (Y < py + s * 0.5), green)
                for j in range(6):
                    ang = j / 6 * 6.28
                    eic_put(img, eic_lt(eic_ell(X, Y, px + np.cos(ang) * s * 0.4, py - s * 0.3 + np.sin(ang) * s * 0.3, s * 0.13, s * 0.13),
                                        0.15), ("#E7B9B0", ivory, gold)[j % 3])
    elif style == "ushak":
        R = 0.2
        rows = int((asp - 0.25) / 0.42) + 2
        for j in range(rows):
            cy = 0.125 + 0.21 + j * 0.42
            xs = (0.5,) if j % 2 == 0 else (0.125, 0.875)
            for cx in xs:
                dx, dy = (X - cx) / R, (Y - cy) / R
                r, t = np.hypot(dx, dy), np.arctan2(dy, dx)
                star = 0.62 + 0.38 * np.abs(np.cos(4 * t)) ** 3
                eic_put(img, eic_lt(r - star * 1.08, 0.03), gold)
                eic_put(img, eic_lt(r - star, 0.03), dark)
                eic_put(img, eic_lt(r - 0.42 * (1 + 0.15 * np.cos(8 * t)), 0.03), field)
                eic_put(img, eic_lt(r - 0.2, 0.04), gold)
            for cx in ((0.125, 0.875) if j % 2 == 0 else (0.5,)):
                cyl = cy
                d = (np.abs(X - cx) + np.abs(Y - cyl)) - 0.07
                eic_put(img, eic_lt(d, aa), dark)
                eic_put(img, eic_lt(d + 0.035, aa), gold)
        for _ in range(60):
            px, py = rng.uniform(0.14, 0.86), rng.uniform(0.14, asp - 0.14)
            eic_put(img, eic_lt(eic_ell(X, Y, px, py, 0.012, 0.005, rng.uniform(0, 3)), 0.2), gold)
    # borders (common)

    def band(a_, b_):
        return eic_lt(a_ - e, aa) * eic_lt(e - b_, aa)
    eic_put(img, band(-1, 0.014), dark)
    eic_put(img, band(0.014, 0.026), gold)
    bb = band(0.026, 0.108)
    eic_put(img, bb, border)
    along = np.where(np.minimum(X, 1 - X) < np.minimum(Y, asp - Y), Y, X)
    dd = e - 0.067
    per = 0.1
    lc = (eic_frac(along / per) - 0.5) * per
    r = np.hypot(lc, dd)
    t = np.arctan2(dd, lc)
    vine = np.abs(dd - 0.022 * np.sin(along / per * 2 * np.pi)) - 0.0035
    eic_put(img, bb * eic_lt(vine, aa), ivory)
    eic_put(img, bb * eic_lt(r - 0.027 * (1 + 0.25 * np.cos(8 * t)), aa), gold)
    eic_put(img, bb * eic_lt(r - 0.013, aa), field)
    eic_put(img, bb * eic_lt(r - 0.005, aa), ivory)
    eic_put(img, band(0.108, 0.118), gold)
    eic_put(img, band(0.118, 0.125), dark)
    img = eic_weave(eic_blur(img, 1), rng)
    return np.clip(img, 0, 1)


def eic_pat_tapestry(W=768, H=512, seed=3, field="#2E4A45"):
    """Flemish-style verdure tapestry: dense blue-green foliage, a few trees and flowers, a fruit-garland border."""
    rng = np.random.default_rng(seed)
    u, v = eic_grid(W, H)
    asp = H / W
    X, Y = u, v * asp
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(field)
    img *= (0.85 + 0.3 * v)[..., None]
    for k in range(5):
        tx = rng.uniform(0.15, 0.85)
        eic_put(img, (np.abs(X - tx - 0.01 * np.sin(Y * 30)) < 0.012) & (Y > asp * 0.25), "#5B4632")
    leaves = ("#3E6B4F", "#5C7F4E", "#2F5148", "#7C8F5A", "#4D6B63", "#8EA06A", "#35584A")
    for k in range(420):
        px, py = rng.uniform(0, 1), rng.uniform(0, asp)
        s = rng.uniform(0.012, 0.03) * (1.3 if py < asp * 0.5 else 1.0)
        ang = rng.uniform(0, 3.14)
        sl = (slice(max(0, int((py - s * 2) / asp * H)), min(H, int((py + s * 2) / asp * H) + 1)),
              slice(max(0, int((px - s * 2) * W)), min(W, int((px + s * 2) * W) + 1)))
        d = eic_ell(X[sl], Y[sl], px, py, s, s * 0.45, ang)
        sub = img[sl]
        eic_put(sub, eic_lt(d, 0.15), leaves[rng.integers(0, len(leaves))])
        eic_put(sub, eic_lt(np.abs(eic_ell(X[sl], Y[sl], px, py, s, s * 0.05, ang)), 0.5) * 0.4, "#22352F")
    for k in range(40):
        px, py = rng.uniform(0.05, 0.95), rng.uniform(asp * 0.55, asp * 0.97)
        eic_put(img, eic_lt(eic_ell(X, Y, px, py, 0.007, 0.007), 0.3), ("#A3262A", "#E6DCC6", "#C9A24A")[k % 3])
    e = np.minimum(np.minimum(X, 1 - X), np.minimum(Y, asp - Y))
    bb = eic_lt(e - 0.07, 0.003)
    eic_put(img, bb, "#5E2124")
    along = np.where(np.minimum(X, 1 - X) < np.minimum(Y, asp - Y), Y, X)
    lc = (eic_frac(along / 0.045) - 0.5) * 0.045
    dd = e - 0.035
    for f, col in ((0.016, "#C9A24A"), (0.009, "#A3262A")):
        eic_put(img, bb * eic_lt(np.hypot(lc, dd) - f, 0.003), col)
    eic_put(img, bb * eic_lt(np.abs(np.hypot(lc - 0.022, dd)) - 0.006, 0.003), "#6E8A4F")
    eic_put(img, eic_lt(np.abs(e - 0.07) - 0.004, 0.003), "#C9A24A")
    eic_put(img, eic_lt(e - 0.006, 0.003), "#2B1A14")
    img *= (0.95 + 0.05 * np.sin(np.arange(H) * np.pi * 0.9))[:, None, None]
    img = eic_weave(img, rng, 4, 0.12, 0.0)
    return np.clip(img * 1.05, 0, 1)


def eic_pat_damask(W=512, H=768, base="#8E1B23", gold="#C9A24A", fringe=True):
    u, v = eic_grid(W, H)
    asp = H / W
    X, Y = u, v * asp
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(base)
    gx, gy = X / 0.25, Y / 0.36
    fx, fy = eic_frac(gx), eic_frac(gy)
    for sg in (1, -1):
        eic_put(img, eic_lt(np.abs(fx - (0.5 + sg * 0.32 * np.sin(2 * np.pi * fy))) - 0.025, 0.02), gold)
    for ox, oy in ((0.5, 0.5), (0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)):
        dx, dy = (fx - ox) / 0.17, (fy - oy) / 0.2
        r, t = np.hypot(dx, dy), np.arctan2(dy, dx)
        eic_put(img, eic_lt(r - (1 + 0.15 * np.cos(7 * t)), 0.06), gold)
        eic_put(img, eic_lt(r - 0.6, 0.06), base)
        eic_put(img, eic_lt(r - 0.3, 0.1), gold)
    img *= (0.9 + 0.1 * eic_blur(np.random.default_rng(2).random((H, W, 1)).astype(np.float32), 1))
    if fringe:
        eic_put(img, (v > 0.965) & (eic_frac(u * 90) < 0.6), gold)
        eic_put(img, (v > 0.94) & (v < 0.965), gold)
    return np.clip(img, 0, 1)


def eic_pat_flag(kind, W=640, H=320):
    """'george' (St George), 'union1707' (St George + St Andrew; no St Patrick), 'eic1600' (Company stripes, St George
    canton), 'eic1707' (stripes, 1707 Union canton)."""
    img = np.ones((H, W, 3), np.float32)
    red, blue, white = "#C1272D", "#1F3270", "#F4F1EA"

    def george(im, w, h):
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        eic_put(im, np.ones((h, w)), white)
        eic_put(im, (np.abs(x - w / 2) < h / 10) | (np.abs(y - h / 2) < h / 10), red)

    def union(im, w, h):
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        eic_put(im, np.ones((h, w)), blue)
        n = np.hypot(w, h)
        d1 = np.abs(y * w - x * h) / n
        d2 = np.abs(y * w - (w - x) * h) / n
        eic_put(im, (d1 < h * 0.1) | (d2 < h * 0.1), white)
        eic_put(im, (np.abs(x - w / 2) < h / 6) | (np.abs(y - h / 2) < h / 6), white)
        eic_put(im, (np.abs(x - w / 2) < h / 10) | (np.abs(y - h / 2) < h / 10), red)
    if kind == "george":
        george(img, W, H)
    elif kind == "union1707":
        union(img, W, H)
    else:
        y = np.arange(H)[:, None] * np.ones((1, W))
        stripe = (np.floor(y / (H / 13)) % 2 == 0)
        eic_put(img, stripe, red)
        eic_put(img, ~stripe, white)
        ch, cw = int(H * 7 / 13), int(W * 0.42)
        sub = img[:ch, :cw]
        (george if kind == "eic1600" else union)(sub, cw, ch)
    return img


def eic_pat_chintz(W=512, H=512, seed=5, ground="#F0E6D0", red="#C04A36", blue="#2B4C7E", green="#5E7B45"):
    rng = np.random.default_rng(seed)
    u, v = eic_grid(W, H)
    X, Y = u, v
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(ground)
    for k in range(70):
        px, py = rng.uniform(0, 1), rng.uniform(0, 1)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                cx, cy = px + ox, py + oy
                if not (-0.1 < cx < 1.1 and -0.1 < cy < 1.1):
                    continue
                if k % 3 == 0:
                    dx, dy = (X - cx) / 0.045, (Y - cy) / 0.045
                    r, t = np.hypot(dx, dy), np.arctan2(dy, dx)
                    eic_put(img, eic_lt(r - (1 + 0.25 * np.cos(6 * t)), 0.1), red)
                    eic_put(img, eic_lt(r - 0.45, 0.1), "#7A1F1A")
                    eic_put(img, eic_lt(r - 0.2, 0.15), "#E0B04A")
                elif k % 3 == 1:
                    a = rng.uniform(0, 3)
                    eic_put(img, eic_lt(eic_ell(X, Y, cx, cy, 0.035, 0.013, a), 0.1), blue if k % 2 else green)
                else:
                    eic_put(img, eic_lt(eic_ell(X, Y, cx, cy, 0.008, 0.008), 0.2), red)
    img *= (0.93 + 0.07 * eic_blur(rng.random((H, W, 1)).astype(np.float32), 1))
    return np.clip(img, 0, 1)


def eic_pat_qanat(W=512, H=512, base="#B0252A", line="#6E1218", accent="#E0B04A", n=4):
    """Block-printed cloth with arched panels (Mughal qanat screens, tent linings)."""
    u, v = eic_grid(W, H)
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(base)
    fx = eic_frac(u * n) - 0.5
    yy = 1 - v
    archtop = 0.62 + 0.22 * (1 - np.abs(fx * 2.4) ** 1.0).clip(0, 1) ** 0.6
    inside = (np.abs(fx) < 0.36) & (yy > 0.12) & (yy < archtop)
    edge = np.abs(np.where(np.abs(fx) < 0.36, yy - archtop, 9)) < 0.015
    eic_put(img, inside, line)
    eic_put(img, edge | ((np.abs(np.abs(fx) - 0.36) < 0.012) & (yy > 0.12) & (yy < archtop)), accent)
    dx, dy = fx / 0.14, (yy - 0.4) / 0.2
    r, t = np.hypot(dx, dy), np.arctan2(dy, dx)
    eic_put(img, inside * eic_lt(r - (1 + 0.3 * np.cos(6 * t)), 0.1), accent)
    eic_put(img, inside * eic_lt(r - 0.35, 0.1), base)
    eic_put(img, (yy < 0.08) | (yy > 0.94), line)
    eic_put(img, (np.abs(yy - 0.04) < 0.01) | (np.abs(yy - 0.97) < 0.01), accent)
    img *= (0.92 + 0.08 * eic_blur(np.random.default_rng(1).random((H, W, 1)).astype(np.float32), 1))
    return np.clip(img, 0, 1)


def eic_pat_valance(W=512, H=128, base="#9E1B32", gold="#D1A63E"):
    """Canopy valance: velvet with gold border and a scalloped, fringed lower edge (alpha)."""
    u, v = eic_grid(W, H)
    img = np.ones((H, W, 4), np.float32)
    img[..., :3] = eic_srgb(base)
    yy = 1 - v
    fx = eic_frac(u * 12) - 0.5
    scal = 0.22 + 0.18 * np.sqrt(np.clip(1 - (fx * 2) ** 2, 0, 1))
    eic_put(img[..., :3], (np.abs(yy - 0.85) < 0.05) | (np.abs(yy - scal - 0.06) < 0.04), gold)
    eic_put(img[..., :3], eic_lt(np.hypot(fx * 2.0, (yy - 0.55) * 1.6) - 0.22, 0.05), gold)
    fr = (yy < scal) & (yy > scal - 0.16) & (eic_frac(u * 220) < 0.55)
    eic_put(img[..., :3], fr, gold)
    img[..., 3] = ((yy >= scal) | fr).astype(np.float32)
    return img


def eic_pat_brocade(W=256, H=256, base="#C9A13C", c1="#A8233A", c2="#1F7A52"):
    u, v = eic_grid(W, H)
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(base)
    fx, fy = eic_frac(u * 6) - 0.5, eic_frac(v * 6 + 0.5 * (np.floor(u * 6) % 2)) - 0.5
    eic_put(img, eic_lt(eic_ell(fx, fy, 0, 0.05, 0.16, 0.24), 0.1), c1)
    eic_put(img, eic_lt(eic_ell(fx, fy, 0.12, -0.18, 0.1, 0.05, 0.6), 0.1), c2)
    img *= (0.85 + 0.3 * eic_frac(u * 90 + v * 3)[..., None] ** 2)
    return np.clip(img, 0, 1)


def eic_pat_leaded(W=256, H=512, pane=0.11, glass="#C9D3C4"):
    """Diamond-pane leaded casement: RGBA with alpha = lead (opaque)."""
    u, v = eic_grid(W, H)
    X, Y = u, v * H / W
    a, b = (X + Y * 0.75) / pane, (X - Y * 0.75) / pane
    lead = (np.maximum(np.abs(eic_frac(a) - 0.5), np.abs(eic_frac(b) - 0.5)) > 0.43)
    edge = (u < 0.03) | (u > 0.97) | (v < 0.015) | (v > 0.985)
    rng = np.random.default_rng(4)
    cell = (np.floor(a) * 7 + np.floor(b) * 13) % 11 / 11.0
    img = np.ones((H, W, 4), np.float32)
    img[..., :3] = eic_srgb(glass) * (0.85 + 0.25 * cell)[..., None]
    m = (lead | edge).astype(np.float32)
    eic_put(img[..., :3], m, "#2A2A2A")
    img[..., 3] = m
    return np.clip(img, 0, 1)


def eic_pat_inlay(W=512, H=512, cell=0.25, line="#EFE9DE", fill="#2A2522", t=0.03):
    """Akbari geometric inlay (white marble lines, black star centres) as RGBA decal."""
    u, v = eic_grid(W, H)
    cx, cy = eic_frac(u / cell) - 0.5, eic_frac(v / cell) - 0.5
    d1 = np.maximum(np.abs(cx), np.abs(cy))
    d2 = np.maximum(np.abs(cx + cy), np.abs(cx - cy)) / np.sqrt(2)
    star = np.minimum(d1, d2)
    octa = np.maximum(d1, d2)
    a = 0.3
    img = np.zeros((H, W, 4), np.float32)
    lines = eic_lt(np.abs(star - a) - t, 0.01) + eic_lt(np.abs(d1 - 0.5) - t * 0.7, 0.01) + eic_lt(np.abs(octa - a * 0.62) - t * 0.6, 0.01)
    lines = np.clip(lines, 0, 1)
    cen = eic_lt(star - 0.12, 0.01)
    img[..., :3] = eic_srgb(line)
    eic_put(img[..., :3], cen, fill)
    img[..., 3] = np.clip(lines + cen, 0, 1)
    return img


def eic_pat_rush(W=512, H=512):
    """Plaited rush matting: sewn strips of chevron braid."""
    u, v = eic_grid(W, H)
    sw = 1 / 8
    sy = eic_frac(v / sw)
    ch = eic_frac(u * 24 + np.abs(sy - 0.5) * 1.6)
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb("#B9A16B")
    img *= (0.8 + 0.3 * (ch < 0.5) + 0.12 * np.sin(ch * np.pi * 2))[..., None]
    eic_put(img, np.abs(sy - 0.5) < 0.03, "#8A7444")
    eic_put(img, (sy < 0.03) | (sy > 0.97), "#6E5A34")
    img *= (0.9 + 0.12 * eic_blur(np.random.default_rng(7).random((H, W, 1)).astype(np.float32), 2))
    return np.clip(img, 0, 1)


def eic_pat_panels(W=512, H=512, nx=3, ny=2, oak="#6A4A2E"):
    """Oak wainscot: stiles and rails with recessed fielded panels (colour; luminance doubles as bump)."""
    u, v = eic_grid(W, H)
    fx, fy = eic_frac(u * nx), eic_frac(v * ny)
    d = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(oak)
    shade = np.where(d < 0.12, 1.0, np.where(d < 0.17, 0.62 + 0.4 * (fy > 0.5), 0.86 + 0.12 * np.clip((d - 0.17) * 4, 0, 1)))
    img *= shade[..., None]
    grain = 0.9 + 0.1 * np.sin(u * 300 + 6 * np.sin(v * 9 + u * 20))
    img *= grain[..., None]
    return np.clip(img, 0, 1)


def eic_pat_canvas(W=512, H=512, base="#E3D7BC", seams=14, horiz=False):
    rng = np.random.default_rng(9)
    u, v = eic_grid(W, H)
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(base)
    s = v if horiz else u
    img *= (1 - 0.12 * (np.abs(eic_frac(s * seams) - 0.5) > 0.47))[..., None]
    img *= (0.9 + 0.1 * eic_blur(rng.random((H // 8, W // 8, 1)).astype(np.float32), 1).repeat(8, 0).repeat(8, 1)[:H, :W])
    img *= (1 - 0.15 * np.clip(1 - v * 4, 0, 1) * 0.5)[..., None]
    return np.clip(img, 0, 1)


def eic_pat_matsail(W=256, H=512, base="#B08A52", battens=0, strip=18):
    u, v = eic_grid(W, H)
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb(base)
    img *= (0.82 + 0.25 * (eic_frac(u * strip) < 0.5) + 0.08 * np.sin(v * 400 + u * 40))[..., None]
    if battens:
        eic_put(img, np.abs(eic_frac(v * battens) - 0.5) > 0.47, "#3A2618")
    img *= (0.9 + 0.12 * eic_blur(np.random.default_rng(3).random((H, W, 1)).astype(np.float32), 2))
    return np.clip(img, 0, 1)


def eic_pat_stripes(W=256, H=256, cols=("#2B3F6E", "#E9DFC9", "#A4302A", "#E9DFC9"), n=12):
    u, v = eic_grid(W, H)
    idx = (np.floor(u * n * len(cols) / 4) % len(cols)).astype(int)
    img = np.stack([eic_srgb(c) for c in cols])[idx]
    img *= (0.94 + 0.06 * np.sin(v * 600))[..., None]
    return np.clip(img, 0, 1)


def eic_pat_hull(era, W=1024, H=256, L=34.0, zmin=-4.5, zmax=10.0):
    """Paint scheme along the hull: u = stern->bow, v = height (zmin..zmax)."""
    u, v = eic_grid(W, H)
    x = u * L
    z = zmax - v * (zmax - zmin)
    img = np.empty((H, W, 3), np.float32)
    if era == "1600":
        img[:] = eic_srgb("#2B2620")
        eic_put(img, z < -0.15, "#D9D2BE")
        a, b = (x / 1.1 + z / 0.55), (x / 1.1 - z / 0.55)
        loz = (np.abs(eic_frac(a) - 0.5) + np.abs(eic_frac(b) - 0.5))
        upper = (z > 3.0)
        cid = (np.floor(a) + np.floor(b)) % 3
        eic_put(img, upper, "#1E1A16")
        for k, col in enumerate(("#A7372A", "#D5A73A", "#3E6B4F")):
            eic_put(img, upper & (cid == k) & (np.abs(eic_frac(a) - 0.5) < 0.42) & (np.abs(eic_frac(b) - 0.5) < 0.42), col)
        eic_put(img, upper & (np.abs(eic_frac(a) - 0.5) > 0.42) | upper & (np.abs(eic_frac(b) - 0.5) > 0.42), "#E8DFC8")
        ports = [(1.7, 2.4), (3.6, 4.2)]
        bands = [(0.5, 0.75), (1.25, 1.5), (2.75, 3.0)]
    else:
        img[:] = eic_srgb("#1E1C1A")
        eic_put(img, z < -0.15, "#D9D2BE")
        eic_put(img, (z > 1.45) & (z < 2.85), "#C89B3C")
        ports = [(1.8, 2.5), (3.7, 4.3)]
        bands = [(0.5, 0.75), (1.2, 1.45), (2.85, 3.05)]
    eic_put(img, (z > -0.15) & (np.abs(eic_frac(z / 0.32) - 0.5) > 0.46), "#15120F")
    for z0, z1 in bands:
        eic_put(img, (z > z0) & (z < z1), "#3A3128")
    for i, (z0, z1) in enumerate(ports):
        px = eic_frac((x - 5.0) / 2.6)
        inb = (x > 7) & (x < L - 7.5)
        eic_put(img, inb & (z > z0 - 0.06) & (z < z1 + 0.06) & (px > 0.36) & (px < 0.64), "#A7372A")
        eic_put(img, inb & (z > z0) & (z < z1) & (px > 0.39) & (px < 0.61), "#0E0C0A")
    img *= (0.92 + 0.08 * eic_blur(np.random.default_rng(1).random((H, W, 1)).astype(np.float32), 1))
    return np.clip(img, 0, 1)


def eic_pat_streaks(W=256, H=512, seed=8):
    """Rain curtain: RGBA vertical streaks."""
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W, 4), np.float32)
    img[..., :3] = 0.75
    cols = rng.random(W) ** 3
    a = np.tile(cols[None, :], (H, 1)) * (0.6 + 0.4 * rng.random((H, 1)))
    u, v = eic_grid(W, H)
    img[..., 3] = np.clip(a * 0.5 * np.clip(v * 3, 0, 1) + 0.12 * np.clip(v * 2 - 0.2, 0, 1), 0, 1)
    return img


# ================================================================================================ blender: images + materials
def eic_image(name, arr):
    arr = np.asarray(arr, np.float32)
    H, W = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((H, W, 1), np.float32)], 2)
    img = bpy.data.images.new(name, W, H, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).ravel())
    d = TEXDIR / "eic_gen"
    d.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(d / f"{name}.png")
    img.file_format = "PNG"
    img.save()
    return img


def eic_cache(key, fn):
    m = EIC_M.get(key)
    try:
        if m is not None and m.name:
            return m
    except ReferenceError:
        pass
    m = fn()
    EIC_M[key] = m
    return m


def eic_m(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, val in enumerate((a, b)):
        if val is None:
            continue
        if isinstance(val, (int, float)):
            n.inputs[i].default_value = float(val)
        else:
            nt.links.new(val, n.inputs[i])
    return n.outputs[0]


def eic_alpha_out(m, nt, shader_socket, alpha_socket):
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.name = "EIC_ALPHAMIX"
    nt.links.new(alpha_socket, mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(shader_socket, mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])


def eic_imat(name, img, rough=0.8, bump=0.0, metal=0.0, alpha=False, emit=0.0, sheen=0.0, uv_scale=(1.0, 1.0), translucent=0.0,
             box=None, coat=0.0, transmit=False, spec=0.5):
    """Material from a generated image. UV-mapped (planes, grids) unless box=scale (world box projection)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mp = nt.nodes.new("ShaderNodeMapping")
    if box:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        mp.inputs["Scale"].default_value = (box, box, box)
        nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
        tex.projection = "BOX"
        tex.projection_blend = 0.2
    else:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp.inputs["Scale"].default_value = (uv_scale[0], uv_scale[1], 1)
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
        b.inputs["Sheen Roughness"].default_value = 0.4
    if bump:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.02
        nt.links.new(tex.outputs["Color"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    if emit:
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    shader = b.outputs[0]
    if translucent:
        tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
        nt.links.new(tex.outputs["Color"], tl.inputs["Color"])
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = translucent
        nt.links.new(shader, mx.inputs[1])
        nt.links.new(tl.outputs[0], mx.inputs[2])
        shader = mx.outputs[0]
        nt.links.new(shader, nt.nodes["Material Output"].inputs["Surface"])
    if alpha:
        eic_alpha_out(m, nt, shader, tex.outputs["Alpha"])
    if transmit:                                                                 # leaded glass: clear where alpha (lead) is 0
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        tr.inputs["Color"].default_value = (0.92, 0.95, 0.9, 1)
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.name = "EIC_ALPHAMIX"
        mx2 = nt.nodes.new("ShaderNodeMixShader")
        mx2.inputs[0].default_value = 0.25
        nt.links.new(tr.outputs[0], mx2.inputs[1])
        nt.links.new(shader, mx2.inputs[2])
        nt.links.new(tex.outputs["Alpha"], mx.inputs[0])
        nt.links.new(mx2.outputs[0], mx.inputs[1])
        nt.links.new(shader, mx.inputs[2])
        nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


def eic_pmat(key, fn, **kw):
    """Cached material from a numpy pattern generator."""
    return eic_cache(("p", key), lambda: eic_imat(key, eic_image(key, fn()), **kw))


def eic_ph(name, asset, scale=1.0, tint=None, rough_mult=1.0, res="1k", vary=0.18, nstr=0.8, fallback=(0.6, 0.5, 0.4)):
    """Poly Haven CC0 material, world box-projected, with large-scale tone variation against visible tiling."""
    def build():
        paths = {}
        try:
            f = _ph_files(asset)
            for k, fn in (("Diffuse", "diff"), ("nor_gl", "nor"), ("Rough", "rough")):
                try:
                    paths[k] = _fetch(f[k][res]["jpg"]["url"], TEXDIR / asset / f"{fn}_{res}.jpg")
                except Exception:
                    paths[k] = None
        except Exception as e:
            print("polyhaven fallback", asset, e)
        if not paths.get("Diffuse"):
            fb = tuple(c * (tint[i] if tint else 1) for i, c in enumerate(fallback))
            return noisy(name, fb, tuple(min(1, c * 1.2) for c in fb), 2, 0.85, 0.2)
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale, scale, scale)
        nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])

        def img(path, color=True):
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = bpy.data.images.load(str(path), check_existing=True)
            if not color:
                n.image.colorspace_settings.name = "Non-Color"
            n.projection = "BOX"
            n.projection_blend = 0.25
            nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
            return n
        col = img(paths["Diffuse"]).outputs["Color"]
        if tint:
            mr = nt.nodes.new("ShaderNodeMixRGB")
            mr.blend_type = "MULTIPLY"
            mr.inputs["Fac"].default_value = 1.0
            mr.inputs["Color2"].default_value = (*tint, 1)
            nt.links.new(col, mr.inputs["Color1"])
            col = mr.outputs["Color"]
        if vary:
            nz = nt.nodes.new("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = 0.09
            nz.inputs["Detail"].default_value = 3
            nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
            mrg = nt.nodes.new("ShaderNodeMapRange")
            mrg.inputs["From Min"].default_value = 0.3
            mrg.inputs["From Max"].default_value = 0.7
            mrg.inputs["To Min"].default_value = 1 - vary
            mrg.inputs["To Max"].default_value = 1 + vary * 0.6
            nt.links.new(nz.outputs["Fac"], mrg.inputs["Value"])
            mr2 = nt.nodes.new("ShaderNodeMixRGB")
            mr2.blend_type = "MULTIPLY"
            mr2.inputs["Fac"].default_value = 1.0
            nt.links.new(col, mr2.inputs["Color1"])
            nt.links.new(mrg.outputs["Result"], mr2.inputs["Color2"])
            col = mr2.outputs["Color"]
        nt.links.new(col, b.inputs["Base Color"])
        if paths.get("Rough"):
            mm = eic_m(nt, "MULTIPLY", img(paths["Rough"], False).outputs["Color"], rough_mult)
            nt.links.new(mm, b.inputs["Roughness"])
        else:
            b.inputs["Roughness"].default_value = min(1.0, 0.8 * rough_mult)
        if paths.get("nor_gl"):
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.inputs["Strength"].default_value = nstr
            nt.links.new(img(paths["nor_gl"], False).outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        return m
    return eic_cache(("ph", name), build)


def eic_col(name, hexcol, rough=0.6, metal=0.0, emit=0.0, coat=0.0):
    def build():
        m = mat(name, eic_lin(hexcol), rough, metal)
        b = m.node_tree.nodes["Principled BSDF"]
        if emit:
            b.inputs["Emission Color"].default_value = (*eic_lin(hexcol), 1)
            b.inputs["Emission Strength"].default_value = emit
        if coat:
            b.inputs["Coat Weight"].default_value = coat
        return m
    return eic_cache(("c", name), build)


def eic_gold():
    return eic_col("gold", "#D9A441", 0.28, 1.0)


def eic_leaf_mat(name="leaf", dark="#1F3F22", light="#4C7A33", scale=5.0, trans=0.25):
    def build():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        vo = nt.nodes.new("ShaderNodeTexVoronoi")
        vo.inputs["Scale"].default_value = scale
        nt.links.new(geo.outputs["Position"], vo.inputs["Vector"])
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 0.35
        nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMixRGB")
        mr.inputs["Color1"].default_value = (*eic_lin(dark), 1)
        mr.inputs["Color2"].default_value = (*eic_lin(light), 1)
        fac = eic_m(nt, "MULTIPLY", vo.outputs["Distance"], nz.outputs["Fac"])
        fac = eic_m(nt, "MULTIPLY", fac, 2.2)
        nt.links.new(fac, mr.inputs["Fac"])
        nt.links.new(mr.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.5
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.8
        nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
        nt.links.new(mr.outputs["Color"], tl.inputs["Color"])
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = trans
        nt.links.new(b.outputs[0], mx.inputs[1])
        nt.links.new(tl.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        return m
    return eic_cache(("leaf", name), build)


def eic_frond_mat(name="frond", c1="#3F6A2A", c2="#8A9A3A", density=38.0, fill=0.6, tear=False):
    """Pinnate palm/bamboo leaf strip: UV u along the frond, v across; leaflets cut with alpha."""
    def build():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["UV"], sep.inputs[0])
        u, v = sep.outputs[0], sep.outputs[1]
        c = eic_m(nt, "ABSOLUTE", eic_m(nt, "SUBTRACT", v, 0.5))
        c = eic_m(nt, "MULTIPLY", c, 2.0)
        f = eic_m(nt, "FRACT", eic_m(nt, "ADD", eic_m(nt, "MULTIPLY", u, density), eic_m(nt, "MULTIPLY", c, 2.2)))
        leaf = eic_m(nt, "LESS_THAN", f, fill)
        rib = eic_m(nt, "LESS_THAN", c, 0.07)
        mask = eic_m(nt, "MAXIMUM", leaf, rib)
        mask = eic_m(nt, "MULTIPLY", mask, eic_m(nt, "LESS_THAN", c, 0.97))
        mask = eic_m(nt, "MULTIPLY", mask, eic_m(nt, "LESS_THAN", u, 0.985))
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 3.0
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMixRGB")
        mr.inputs["Color1"].default_value = (*eic_lin(c1), 1)
        mr.inputs["Color2"].default_value = (*eic_lin(c2), 1)
        fac = eic_m(nt, "ADD", eic_m(nt, "MULTIPLY", u, 0.5), eic_m(nt, "MULTIPLY", nz.outputs["Fac"], 0.6))
        nt.links.new(eic_m(nt, "SUBTRACT", fac, 0.25), mr.inputs["Fac"])
        nt.links.new(mr.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.45
        tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
        nt.links.new(mr.outputs["Color"], tl.inputs["Color"])
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = 0.3
        nt.links.new(b.outputs[0], mx.inputs[1])
        nt.links.new(tl.outputs[0], mx.inputs[2])
        eic_alpha_out(m, nt, mx.outputs[0], mask)
        return m
    return eic_cache(("frond", name), build)


def eic_water_mat(name, hexcol, rough=0.05, wave=0.25, scale=0.5, stretch=3.0, speed=0.25):
    def build():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*eic_lin(hexcol), 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Specular IOR Level"].default_value = 0.6
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale, scale * stretch, scale)
        nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.noise_dimensions = "4D"
        nz.inputs["Scale"].default_value = 1.0
        nz.inputs["Detail"].default_value = 6
        nz.inputs["Roughness"].default_value = 0.6
        nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
        w = nz.inputs["W"]
        w.default_value = 0.0
        w.keyframe_insert("default_value", frame=1)
        w.default_value = SECONDS * speed
        w.keyframe_insert("default_value", frame=N)
        try:
            for fc in nt.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except Exception:
            pass
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = wave
        bp.inputs["Distance"].default_value = 0.3
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        return m
    return eic_cache(("water", name), build)


# ================================================================================================ blender: geometry
def eic_link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def eic_mesh(name, verts, faces, m=None, uvs=None, loc=(0, 0, 0), rot=(0, 0, 0), smooth_=False, recalc=False, mats=None, mat_idx=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    if smooth_:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    o = bpy.data.objects.new(name, me)
    eic_link(o)
    o.location = loc
    o.rotation_euler = rot
    if mats:
        for mm in mats:
            me.materials.append(mm)
        if mat_idx:
            me.polygons.foreach_set("material_index", mat_idx)
    elif m:
        me.materials.append(m)
    return o


def eic_gridm(name, nu, nv, fn, m=None, **kw):
    verts, uvs = [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            verts.append(fn(u, v))
            uvs.append((u, v))
    faces = [(j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i) for j in range(nv) for i in range(nu)]
    return eic_mesh(name, verts, faces, m, uvs, **kw)


def eic_tube(name, pts, radii, m, nv=8, cap=True):
    P = [Vector(p) for p in pts]
    if isinstance(radii, (int, float)):
        radii = [radii] * len(P)
    verts, faces, uvs = [], [], []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        n1 = t.cross(a).normalized()
        n2 = t.cross(n1).normalized()
        for k in range(nv):
            ang = 2 * math.pi * k / nv
            verts.append(p + (n1 * math.cos(ang) + n2 * math.sin(ang)) * radii[i])
            uvs.append((k / nv, i / max(1, len(P) - 1)))
    for i in range(len(P) - 1):
        for k in range(nv):
            faces.append((i * nv + k, i * nv + (k + 1) % nv, (i + 1) * nv + (k + 1) % nv, (i + 1) * nv + k))
    if cap:
        faces.append(tuple(range((len(P) - 1) * nv, len(P) * nv)))
    return eic_mesh(name, verts, faces, m, uvs, smooth_=True)


def eic_rod(a, b, r, m, nv=8, r2=None):
    return eic_tube("rod", [a, b], [r, r if r2 is None else r2], m, nv)


def eic_prism(name, poly, thick, m, loc=(0, 0, 0), rz=0.0):
    """Extrude a 2D outline [(x, z)] along local y (thickness) - arches, gables, spandrels."""
    n = len(poly)
    verts = [(x, -thick / 2, z) for x, z in poly] + [(x, thick / 2, z) for x, z in poly]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return eic_mesh(name, verts, faces, m, loc=loc, rot=(0, 0, rz), recalc=True)


def eic_arch_curve(w, hs, ha, n=32, p=1.0, q=0.62, lobes=0, depth=0.0):
    """Arch intrados from the left springing to the right: pointed (p~1), round (p=2, q=0.5), multifoil (lobes>0)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        xn = -1 + 2 * t
        x = xn * w
        z = hs + ha * max(0.0, 1 - abs(xn) ** p) ** q
        if lobes:
            f = (t * lobes) % 1.0
            off = depth * (1 - math.sin(math.pi * f))
            dx, dz = -x, hs + ha * 0.25 - z
            d = math.hypot(dx, dz) or 1
            x, z = x + dx / d * off, z + dz / d * off
        pts.append((x, z))
    return pts


def eic_arch_bay(cx, cy, w, hs, ha, top, thick, m, rz=0.0, **kw):
    """Spandrel block over an arch opening (half-width w, springing hs, rise ha) up to height top."""
    curve = eic_arch_curve(w, hs, ha, **kw)
    poly = [(-w, top)] + curve + [(w, top)]
    poly = [(-w, top), (-w, hs)] + curve[1:-1] + [(w, hs), (w, top)]
    return eic_prism("arch", poly, thick, m, (cx, cy, 0), rz)


def eic_arcade(x0, y0, n, bay, hs, ha, top, thick, pier, m, rz=0.0, z0=0.0, cap_m=None, **kw):
    """n arches along local x starting at (x0, y0), rotated rz about that point."""
    objs = []
    c, s = math.cos(rz), math.sin(rz)

    def P(lx, ly=0.0):
        return (x0 + lx * c - ly * s, y0 + lx * s + ly * c)
    for i in range(n + 1):
        px, py = P(i * bay)
        objs.append(add("cube", (px, py, z0 + top / 2), (pier / 2, thick / 2 + 0.02, top / 2), (0, 0, rz), m=m))
        if cap_m:
            objs.append(add("cube", (px, py, z0 + hs + 0.1), (pier / 2 + 0.08, thick / 2 + 0.08, 0.1), (0, 0, rz), m=cap_m))
    for i in range(n):
        px, py = P(i * bay + bay / 2)
        o = eic_arch_bay(px, py, bay / 2 - pier / 2, hs, ha, top, thick, m, rz, **kw)
        o.location.z = z0
        objs.append(o)
    return objs


def eic_gable(cx, cy, z0, lx, ly, h, roof_m, wall_m=None, rz=0.0, over=0.35):
    """Gable roof, ridge along local x; gable triangles in wall material."""
    ex, ey = lx + over, ly + over
    verts = [(-ex, -ey, -over * h / ly), (ex, -ey, -over * h / ly), (ex, 0, h), (-ex, 0, h),
             (ex, ey, -over * h / ly), (-ex, ey, -over * h / ly),
             (-lx, -ly, 0), (-lx, ly, 0), (-lx, 0, h - 0.02), (lx, -ly, 0), (lx, ly, 0), (lx, 0, h - 0.02)]
    faces = [(0, 1, 2, 3), (3, 2, 4, 5), (6, 8, 7), (9, 10, 11)]
    mats = [roof_m, wall_m or roof_m]
    return eic_mesh("gable", verts, faces, loc=(cx, cy, z0), rot=(0, 0, rz), mats=mats, mat_idx=[0, 0, 1, 1], recalc=True)


def eic_hip(cx, cy, z0, lx, ly, h, m, rz=0.0, ridge=0.45, over=0.6):
    ex, ey = lx + over, ly + over
    r = ex * ridge
    dz = -over * h / ly
    verts = [(-ex, -ey, dz), (ex, -ey, dz), (ex, ey, dz), (-ex, ey, dz), (-r, 0, h), (r, 0, h)]
    faces = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)]
    return eic_mesh("hip", verts, faces, m, loc=(cx, cy, z0), rot=(0, 0, rz), recalc=True)


def eic_chala(cx, cy, z0, lx, ly, h, m, four=False, droop=0.5, bulge=0.35, rz=0.0, n=16):
    """Bengal curved roof: do-chala (two curved slopes, ridge along x) or char-chala (four slopes to an apex)."""
    objs = []
    if not four:
        for sg in (-1, 1):
            def fn(u, v, sg=sg):
                xn = -1 + 2 * u
                eave = -droop * xn * xn
                ridge = h - droop * 0.8 * xn * xn
                y = sg * ly * (1 - v)
                z = eave + v * (ridge - eave) + bulge * math.sin(math.pi * v)
                return (xn * lx * (1 + 0.04 * (1 - v)), y, z)
            objs.append(eic_gridm("chala", n, 6, fn, m, loc=(cx, cy, z0), rot=(0, 0, rz)))
    else:
        corners = [(-lx, -ly), (lx, -ly), (lx, ly), (-lx, ly)]
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            mx, my = (ax + bx) / 2, (ay + by) / 2
            nl = math.hypot(mx, my)

            def fn(u, v, ax=ax, ay=ay, bx=bx, by=by, mx=mx, my=my, nl=nl):
                xn = -1 + 2 * u
                ex, ey = ax + (bx - ax) * u, ay + (by - ay) * u
                ez = -droop * xn * xn
                x = ex * (1 - v)
                y = ey * (1 - v)
                z = ez * (1 - v) + h * v + bulge * math.sin(math.pi * v)
                return (x, y, z)
            objs.append(eic_gridm("chala4", n, 6, fn, m, loc=(cx, cy, z0), rot=(0, 0, rz)))
    for o in objs:
        sd = o.modifiers.new("t", "SOLIDIFY")
        sd.thickness = 0.12
    return objs


def eic_group(objs, loc=(0, 0, 0), rz=0.0, s=1.0):
    bpy.ops.object.empty_add(location=(0, 0, 0))
    e = bpy.context.active_object
    for o in objs:
        if o.parent is None:
            o.parent = e
    e.location = loc
    e.rotation_euler = (0, 0, rz)
    e.scale = (s, s, s)
    return e


def eic_join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return o


def eic_proto(objs, name):
    o = eic_join(objs, name)
    o.location = (0, 0, -500)
    o.hide_render = True
    return o


def eic_inst(src, x, y, z=0.0, rz=0.0, s=1.0, sz=None):
    o = src.copy()
    eic_link(o)
    o.location = (x, y, z)
    o.rotation_euler = (0, 0, rz)
    o.scale = (s, s, s if sz is None else sz)
    o.hide_render = False
    return o


def eic_cloth(loc, w, h, m, rot=(math.radians(90), 0, 0), folds=8, amp=0.06, sag=0.0, nu=40, nv=6):
    """Hanging cloth in local XZ (after rot), vertical folds, optional sag of the top edge."""
    def fn(u, v):
        x = (u - 0.5) * w
        y = amp * math.sin(u * folds * 2 * math.pi) * (0.4 + 0.6 * (1 - v))
        z = (v - 0.5) * h - sag * math.sin(math.pi * u) * v
        return (x, z, -y)
    return eic_gridm("cloth", nu, nv, fn, m, loc=loc, rot=rot)


def eic_flag(x, y, z, w, h, kind, rz=0.0, ripple=0.18):
    m = eic_pmat("flag_" + kind, lambda: eic_pat_flag(kind), rough=0.8, sheen=0.3, translucent=0.15)

    def fn(u, v):
        return (-u * w, ripple * w * math.sin(u * 7.5 + v * 1.2) * u, v * h)
    return eic_gridm("flag", 24, 4, fn, m, loc=(x, y, z), rot=(0, 0, rz))


def eic_hill(x, y, rx, ry, h, m, seed=0):
    o = add("sphere", (x, y, 0), (rx, ry, h), m=m, segments=48, ring_count=24)
    for v in o.data.vertices:
        if v.co.z < 0:
            v.co.z = -0.05
        else:
            v.co.z *= 1 + 0.25 * eic_noise.noise(Vector((v.co.x * 2 + seed, v.co.y * 2, 0)))
    smooth(o)
    return o


# ------------------------------------------------------------------------------------------------ sky, sun, aerial haze
def eic_sky(hdri, strength=0.8, sun_az=200.0, res="2k"):
    """HDRI sky rotated so its sun sits at world azimuth sun_az (deg, 0 = +X, 90 = +Y = into the scene). Returns the sun
    elevation found in the image and stores the horizon colour (for the aerial haze)."""
    w = ph_sky(hdri, strength, 0.0, res)
    EIC_SKY.clear()
    EIC_SKY["el"] = 25.0
    EIC_SKY["horizon"] = (0.6, 0.65, 0.7)
    try:
        env = [n for n in w.node_tree.nodes if n.type == "TEX_ENVIRONMENT"][0]
        mp = [n for n in w.node_tree.nodes if n.type == "MAPPING"][0]
        img = env.image
        W, H = img.size
        px = np.empty(W * H * 4, np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(H, W, 4)[..., :3]
        lum = px.sum(2)
        lum[: H // 2] = 0
        j, i = np.unravel_index(np.argmax(lum), lum.shape)
        u, v = (i + 0.5) / W, (j + 0.5) / H
        phi_img = -(u - 0.5) * 2 * math.pi
        el = math.degrees((v - 0.5) * math.pi)
        rot = phi_img - math.radians(sun_az)
        mp.inputs["Rotation"].default_value = (0, 0, rot)
        phi_view = math.radians(90) + rot                                       # where the camera's +Y lands in the image
        uc = (0.5 - phi_view / (2 * math.pi)) % 1.0
        cols = [int(((uc + d) % 1.0) * W) for d in np.linspace(-0.07, 0.07, 15)]
        rows = slice(int(H * 0.515), int(H * 0.545))
        hz = px[rows][:, cols].reshape(-1, 3).mean(0) * strength
        EIC_SKY["el"] = el
        EIC_SKY["horizon"] = tuple(float(c) for c in hz)
        print("eic sky", hdri, "sun el", round(el, 1), "horizon", EIC_SKY["horizon"])
    except Exception as e:
        print("eic sky detect failed", e)
    return EIC_SKY["el"]


def eic_sun(az, strength=3.0, color=(1, 0.9, 0.75), el=None, lo=8, hi=55, angle=1.5):
    e = EIC_SKY.get("el", 25.0) if el is None else el
    e = max(lo, min(hi, e))
    return sun(e, az + 90, strength, color, angle)


def eic_aerial(start=30.0, depth=500.0, maxf=0.85, tint=(1.0, 1.0, 1.0), gain=1.0, color=None):
    """Aerial perspective on every material: mix towards the horizon colour with camera distance."""
    col = color or EIC_SKY.get("horizon", (0.6, 0.65, 0.7))
    col = [max(1e-4, c * t * gain) for c, t in zip(col, tint)]
    st = max(col)
    col = [c / st for c in col]
    for m in list(bpy.data.materials):
        if not m.use_nodes or m.get("eic_nofog"):
            continue
        nt = m.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out is None:
            continue
        tgt = nt.nodes.get("EIC_ALPHAMIX")
        sock = tgt.inputs[2] if tgt else out.inputs["Surface"]
        if not sock.links:
            continue
        src = sock.links[0].from_socket
        cam = nt.nodes.new("ShaderNodeCameraData")
        d = eic_m(nt, "MAXIMUM", eic_m(nt, "SUBTRACT", cam.outputs["View Distance"], start), 0.0)
        f = eic_m(nt, "SUBTRACT", 1.0, eic_m(nt, "EXPONENT", eic_m(nt, "DIVIDE", d, -depth)))
        f = eic_m(nt, "MULTIPLY", f, maxf)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*col, 1)
        em.inputs["Strength"].default_value = st
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(f, mx.inputs[0])
        nt.links.new(src, mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], sock)


def eic_water(loc, size, hexcol, name="water", **kw):
    return add("plane", loc, (size[0], size[1], 1), m=eic_water_mat(name, hexcol, **kw))


def eic_poly_ground(pts, z, m, bottom=-3.0, name="land"):
    """Flat land with a polygon outline [(x, y)] (counter-clockwise) and vertical edges down to bottom."""
    n = len(pts)
    verts = [(x, y, z) for x, y in pts] + [(x, y, bottom) for x, y in pts]
    faces = [tuple(range(n))] + [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    o = eic_mesh(name, verts, faces, m, recalc=True)
    return o


# ------------------------------------------------------------------------------------------------ plants
def eic_palm_proto(seed, h=10.0, lean=0.18, nfr=13):
    rng = random.Random(seed)
    bark = eic_ph("palmbark", "palm_tree_bark", 1.2, tint=(0.85, 0.78, 0.68), fallback=(0.4, 0.33, 0.25))
    fm = eic_frond_mat("palmfrond", "#3B5E22", "#8C9A3C")
    ang = rng.uniform(0, 6.28)
    dx, dy = math.cos(ang), math.sin(ang)
    pts = [(lean * h * t * t * dx, lean * h * t * t * dy, h * t) for t in [i / 9 for i in range(10)]]
    parts = [eic_tube("trunk", pts, [0.26 - 0.09 * (i / 9) for i in range(10)], bark, 9)]
    top = Vector(pts[-1])
    for k in range(nfr):
        az = k * 2 * math.pi / nfr + rng.uniform(-0.2, 0.2)
        e0 = math.radians(rng.uniform(-10, 50))
        L = rng.uniform(3.8, 5.2)
        dr = rng.uniform(0.09, 0.15)

        def fn(u, v, az=az, e0=e0, L=L, dr=dr):
            s = u * L
            hd = s * math.cos(e0)
            z = s * math.sin(e0) - dr * s * s
            w = 0.8 * math.sin(math.pi * min(1.0, u * 0.95 + 0.05)) ** 0.7
            off = (v - 0.5) * 2 * w
            z -= abs(v - 0.5) * 2 * w * 0.45
            return (top.x + math.cos(az) * hd - math.sin(az) * off, top.y + math.sin(az) * hd + math.cos(az) * off, top.z + z)
        parts.append(eic_gridm("frond", 10, 2, fn, fm))
    nut = eic_col("coconut", "#5A4A22", 0.6)
    for k in range(5):
        a = k * 1.3
        parts.append(add("sphere", (top.x + 0.35 * math.cos(a), top.y + 0.35 * math.sin(a), top.z - 0.35), (0.16, 0.16, 0.19), m=nut,
                         segments=8, ring_count=6))
    return eic_proto(parts, "palm")


def eic_tree_proto(seed, h=7.0, crown=4.5, leaf=None, n=14, flat=0.55):
    """Broad dense tree (mango, neem): trunk with branches and a domed canopy of noise-displaced lumps."""
    rng = random.Random(seed)
    bark = eic_ph("bark", "bark_brown_02", 1.0, tint=(0.8, 0.72, 0.62), fallback=(0.3, 0.22, 0.15))
    leaf = leaf or eic_leaf_mat("mango", "#16301A", "#3F6B2C", 5.0)
    th = h * 0.42
    parts = [eic_tube("trunk", [(0, 0, 0), (0.1, 0, th * 0.6), (0, 0.1, th)], [0.4, 0.3, 0.26], bark, 9)]
    for k in range(4):
        a = k * 1.57 + rng.uniform(-0.3, 0.3)
        parts.append(eic_tube("br", [(0, 0, th * 0.9), (math.cos(a) * crown * 0.35, math.sin(a) * crown * 0.35, th + crown * 0.35)],
                              [0.18, 0.1], bark, 6))
    for i in range(n):
        a = rng.uniform(0, 6.28)
        rr = rng.uniform(0, crown * 0.55)
        z = th + crown * (0.25 + 0.55 * (1 - rr / crown) * rng.uniform(0.6, 1.0))
        r = crown * rng.uniform(0.32, 0.5)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(math.cos(a) * rr, math.sin(a) * rr, z))
        o = bpy.context.active_object
        for v in o.data.vertices:
            p = v.co
            nv = p.normalized()
            d = eic_noise.noise(Vector((p.x * 0.9 + seed * 3.1 + a, p.y * 0.9, p.z * 0.9))) * r * 0.32
            d += eic_noise.noise(Vector((p.x * 3 + seed, p.y * 3, p.z * 3))) * r * 0.08
            v.co = p + nv * d
            if v.co.z < -r * flat:
                v.co.z = -r * flat + (v.co.z + r * flat) * 0.25
        o.data.materials.append(leaf)
        smooth(o)
        parts.append(o)
    return eic_proto(parts, "tree")


def eic_bamboo_proto(seed, n=20, h=11.0):
    rng = random.Random(seed)
    culm = eic_col("bamboo", "#8C9440", 0.45)
    fm = eic_frond_mat("bambooleaf", "#4E6E2A", "#9AA845", density=14.0, fill=0.7)
    parts = []
    for k in range(n):
        a = rng.uniform(0, 6.28)
        r0 = rng.uniform(0, 1.0)
        bx, by = math.cos(a) * r0, math.sin(a) * r0
        hh = h * rng.uniform(0.75, 1.1)
        lean = rng.uniform(0.15, 0.4)
        pts = [(bx + math.cos(a) * lean * hh * t * t, by + math.sin(a) * lean * hh * t * t, hh * t) for t in [i / 6 for i in range(7)]]
        parts.append(eic_tube("culm", pts, [0.06 - 0.04 * i / 6 for i in range(7)], culm, 6))
        for j in range(6):
            t = 0.45 + 0.55 * j / 5
            p = Vector(pts[0]).lerp(Vector(pts[-1]), t)
            p.x += math.cos(a) * lean * hh * (t * t - t)
            p.y += math.sin(a) * lean * hh * (t * t - t)
            az = a + rng.uniform(-1.2, 1.2)
            L = rng.uniform(1.6, 2.6)

            def fn(u, v, p=p, az=az, L=L):
                s = u * L
                w = 0.45 * math.sin(math.pi * min(1.0, u + 0.05))
                off = (v - 0.5) * 2 * w
                return (p.x + math.cos(az) * s * 0.9 - math.sin(az) * off, p.y + math.sin(az) * s * 0.9 + math.cos(az) * off,
                        p.z - 0.25 * s * s + 0.2 * s - abs(v - 0.5) * w * 0.6)
            parts.append(eic_gridm("spray", 6, 2, fn, fm))
    return eic_proto(parts, "bamboo")


def eic_banana_proto(seed):
    rng = random.Random(seed)
    stem = eic_col("bananastem", "#6E7A3A", 0.6)
    fm = eic_frond_mat("bananaleaf", "#3E6E2A", "#7FA040", density=9.0, fill=0.93)
    parts = [eic_tube("stem", [(0, 0, 0), (0, 0, 2.4)], [0.16, 0.12], stem, 8)]
    for k in range(8):
        az = k * 0.8 + rng.uniform(-0.2, 0.2)
        e0 = math.radians(rng.uniform(20, 60))
        L = rng.uniform(1.8, 2.6)

        def fn(u, v, az=az, e0=e0, L=L):
            s = u * L
            w = 0.38 * math.sin(math.pi * min(1.0, u * 0.9 + 0.1)) ** 0.5
            off = (v - 0.5) * 2 * w
            hd = s * math.cos(e0)
            z = 2.3 + s * math.sin(e0) - 0.35 * s * s
            return (math.cos(az) * hd - math.sin(az) * off, math.sin(az) * hd + math.cos(az) * off, z - abs(v - 0.5) * w * 0.3)
        parts.append(eic_gridm("bleaf", 8, 2, fn, fm))
    return eic_proto(parts, "banana")


# ------------------------------------------------------------------------------------------------ ships and boats
def eic_hull(name, L, B, D, H, m=None, n=26, stern_w=0.0, sheer_bow=0.0, sheer_stern=0.0, keel_rise=0.5, tumble=0.86, zr=None, uv=False):
    """Lofted hull at the origin, bow towards +x, waterline z=0. Returns (object, half-beam function, top-height function)."""
    fr = [0.0, 0.1, 0.28, 0.5, 0.7, 0.86, 1.0]
    wf = [0.04, 0.5, 0.82, 0.97, 1.0, 0.97, tumble]

    def hb(xn):
        if xn >= 0:
            return B / 2 * max(0.0, 1 - xn ** 2.2) ** 0.55
        return B / 2 * (stern_w + (1 - stern_w) * max(0.0, 1 - xn * xn) ** 0.5)

    def top(xn):
        return H + sheer_bow * max(0, xn) ** 2 + sheer_stern * max(0, -xn) ** 2
    rows = len(fr)
    ring = 2 * rows - 1
    verts, uvs = [], []
    zmin, zmax = (zr or (-D, H + max(sheer_bow, sheer_stern)))
    for i in range(n + 1):
        xn = -1 + 2 * i / n
        x = xn * L / 2
        b = max(hb(xn), 0.02)
        t = top(xn)
        bot = -D * (1 - keel_rise * max(0.0, abs(xn) - 0.55) / 0.45)
        pts = [(x, b * wf[k], bot + (t - bot) * fr[k]) for k in reversed(range(rows))] + \
              [(x, -b * wf[k], bot + (t - bot) * fr[k]) for k in range(1, rows)]
        for p in pts:
            verts.append(p)
            uvs.append(((p[0] + L / 2) / L, (p[2] - zmin) / (zmax - zmin)))
    faces = [(i * ring + k, i * ring + k + 1, (i + 1) * ring + k + 1, (i + 1) * ring + k) for i in range(n) for k in range(ring - 1)]
    faces.append(tuple(range(ring)))
    dk = len(verts)                                                             # deck
    for i in range(n + 1):
        xn = -1 + 2 * i / n
        b = max(hb(xn), 0.02) * tumble * 0.98
        z = top(xn) - 0.9
        verts += [(xn * L / 2, b, z), (xn * L / 2, -b, z)]
        uvs += [(0.5, (0.2 - zmin) / (zmax - zmin))] * 2
    faces += [(dk + 2 * i, dk + 2 * i + 2, dk + 2 * i + 3, dk + 2 * i + 1) for i in range(n)]
    o = eic_mesh(name, verts, faces, m, uvs if uv else None, recalc=True)
    return o, (lambda x: hb(2 * x / L)), (lambda x: top(2 * x / L))


def eic_sail(p00, p10, p01, p11, belly, m, nu=8, nv=8, axis=(1, 0, 0)):
    """Quad sail between four corners (u: left->right, v: bottom->top) bellied along axis."""
    A, Bv, C, D = Vector(p00), Vector(p10), Vector(p01), Vector(p11)
    ax = Vector(axis)

    def fn(u, v):
        p = (A.lerp(Bv, u)).lerp(C.lerp(D, u), v)
        return tuple(p + ax * belly * math.sin(math.pi * u) * (0.35 + 0.65 * math.sin(math.pi * min(1.0, v * 0.85 + 0.1))))
    return eic_gridm("sail", nu, nv, fn, m)


def eic_ship(x, y, rz=0.0, s=1.0, era="1600", sails="furled", flags=True, z=0.0, masts=True, yards=True):
    """Galleon-type East Indiaman (era '1600': lateen mizzen, beakhead, painted upper works) or ship-rigged 1750s
    Indiaman (era '1750': black and ochre, gaff mizzen). Built bow +x and placed with an empty."""
    L, B, D, H = 34.0, 9.6, 3.8, 3.2
    paint = eic_pmat("hull" + era, lambda: eic_pat_hull(era, L=L, zmin=-D, zmax=H + 2.0), rough=0.55, bump=0.05)
    wood = eic_ph("shipwood", "dark_wood", 0.7, tint=(0.75, 0.62, 0.5), fallback=(0.25, 0.18, 0.12))
    canvas = eic_pmat("canvas", lambda: eic_pat_canvas(), rough=0.85, translucent=0.25, sheen=0.2)
    rope = eic_col("rope", "#2E261C", 0.8)
    parts = []
    hull, hb, top = eic_hull("hull", L, B, D, H, paint, stern_w=0.6 if era == "1600" else 0.66, sheer_bow=1.1, sheer_stern=1.6,
                             zr=(-D, H + 2.0), uv=True)
    parts.append(hull)

    def uvbox(o):
        mw = Matrix.LocRotScale(o.location, o.rotation_euler, o.scale)
        me = o.data
        uvl = me.uv_layers[0] if len(me.uv_layers) else me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                p = mw @ me.vertices[me.loops[li].vertex_index].co
                uvl.data[li].uv = ((p.x + L / 2) / L, (p.z + D) / (H + 2.0 + D))
        return o
    if era == "1600":
        sc_ = add("cube", (-13.2, 0, 5.4), (3.8, 3.3, 2.0), m=paint)            # tall narrow stern castle
        for v in sc_.data.vertices:
            if v.co.z > 0:
                v.co.y *= 0.8
        parts.append(uvbox(sc_))
        parts.append(uvbox(add("cube", (-14.8, 0, 7.9), (2.2, 2.4, 0.6), m=paint)))
        fc = add("cube", (12.0, 0, 4.4), (3.4, 2.7, 0.9), m=paint)
        for v in fc.data.vertices:
            if v.co.x > 0:
                v.co.y *= 0.55
        parts.append(uvbox(fc))
        bh = eic_mesh("beak", [(16.5, 1.2, 2.6), (16.5, -1.2, 2.6), (16.5, 1.0, 4.0), (16.5, -1.0, 4.0), (22.5, 0, 3.2), (22.5, 0, 3.6)],
                      [(0, 1, 4), (2, 3, 5), (0, 2, 5, 4), (1, 4, 5, 3), (0, 1, 3, 2)], wood, recalc=True)
        parts.append(bh)
        lanterns = [(-17.4, 0, 9.4), (-17.2, 1.6, 9.0), (-17.2, -1.6, 9.0)]
    else:
        qd = add("cube", (-11.5, 0, 4.6), (5.6, 3.9, 1.2), m=paint)
        for v in qd.data.vertices:
            if v.co.z > 0:
                v.co.y *= 0.93
        parts.append(uvbox(qd))
        gal = add("cube", (-17.2, 0, 4.4), (0.5, 3.2, 1.0), m=eic_col("gallery", "#C89B3C", 0.5))
        parts.append(gal)
        for k in range(5):
            parts.append(add("cube", (-17.75, -2.4 + k * 1.2, 4.5), (0.05, 0.4, 0.5), m=eic_col("galwin", "#2A2E30", 0.2)))
        parts.append(eic_mesh("head", [(16.5, 1.0, 2.6), (16.5, -1.0, 2.6), (16.5, 0.8, 3.8), (16.5, -0.8, 3.8), (19.5, 0, 3.0), (19.5, 0, 3.8)],
                              [(0, 1, 4), (2, 3, 5), (0, 2, 5, 4), (1, 4, 5, 3), (0, 1, 3, 2)], wood, recalc=True))
        lanterns = [(-17.6, 0, 6.6)]
    for p in lanterns:
        parts.append(add("cyl", p, (0.25, 0.25, 0.4), m=eic_gold(), vertices=8))
    if masts:
        base = H - 0.9
        spec = [(9.5, 19, 11, 15.5, "fore"), (-0.5, 22, 13, 18.0, "main"), (-11.0, 13, 7 if era == "1750" else 0, 10.0, "miz")]
        shrouds = []
        for mx, lo, tp, yl, nm in spec:
            ztop = base + lo
            parts.append(eic_rod((mx, 0, base - 1), (mx, 0, ztop), 0.42 * (lo / 22), wood, 10, 0.3 * (lo / 22)))
            parts.append(add("cyl", (mx, 0, ztop - 1.2), (1.3, 1.3, 0.12), m=wood, vertices=14))
            zt = ztop
            if tp:
                parts.append(eic_rod((mx, 0, ztop - 2.0), (mx, 0, ztop + tp), 0.22, wood, 8, 0.11))
                zt = ztop + tp
            for sg in (1, -1):
                hy = hb(mx) * 0.97
                for k in range(5):
                    shrouds.append(((mx - 2.6 + k * 0.7, sg * hy, top(mx) + 0.1), (mx, sg * 1.1, ztop - 1.2)))
                if tp:
                    for k in range(3):
                        shrouds.append(((mx - 0.6 + k * 0.6, sg * 1.25, ztop - 1.15), (mx, sg * 0.1, zt - 1.0)))
            if nm == "miz" and era == "1600":
                ya, yb = (mx + 6.0, 0, base + 4.0), (mx - 8.0, 0, base + lo + 4.5)
                if yards:
                    parts.append(eic_rod(ya, yb, 0.17, wood, 6, 0.1))
                if sails == "set":
                    parts.append(eic_sail(ya, (mx - 7.0, 0, base + 1.6), yb, yb, 0.0, canvas, 6, 6, (0, 1, 0)))
                elif sails == "furled" and yards:
                    parts.append(eic_rod(ya, yb, 0.3, canvas, 8, 0.18))
                continue
            if nm == "miz":                                                     # 1750: gaff and boom
                parts.append(eic_rod((mx, 0, base + lo - 1), (mx - 7, 0, base + lo + 1.5), 0.13, wood, 6))
                parts.append(eic_rod((mx, 0, base + 2.2), (mx - 9.5, 0, base + 2.6), 0.15, wood, 6))
                if sails == "set":
                    parts.append(eic_sail((mx, 0, base + 2.4), (mx - 9.3, 0, base + 2.8), (mx, 0, base + lo - 1), (mx - 7, 0, base + lo + 1.5),
                                          0.8, canvas, 6, 6, (0, 1, 0)))
                elif sails == "furled":
                    parts.append(eic_rod((mx - 0.5, 0, base + lo - 0.9), (mx - 6.5, 0, base + lo + 1.3), 0.28, canvas, 8))
            if not yards:
                continue
            zc = base + lo - 2.2
            ztp = zt - 1.6 if tp else zc
            for zy, ly, kind in ((zc, yl, "course"), (ztp, yl * 0.62, "top")):
                if kind == "top" and not tp:
                    continue
                parts.append(eic_rod((mx + 0.5, -ly / 2, zy), (mx + 0.5, ly / 2, zy), 0.2, wood, 6, 0.2))
                shrouds += [((mx + 0.5, sg * ly / 2, zy), (mx, 0, zy + (tp * 0.7 if kind == "course" and tp else 2.5))) for sg in (1, -1)]
                if sails == "set":
                    bot = (base + 1.8 if kind == "course" else zc + 0.4)
                    w2 = ly / 2 * (1.05 if kind == "course" else 1.35)
                    parts.append(eic_sail((mx + 0.6, -w2, bot), (mx + 0.6, w2, bot), (mx + 0.6, -ly / 2, zy), (mx + 0.6, ly / 2, zy),
                                          1.6 if kind == "course" else 1.1, canvas, 8, 8))
                elif sails == "furled":
                    parts.append(eic_rod((mx + 0.55, -ly / 2 * 0.92, zy - 0.3), (mx + 0.55, ly / 2 * 0.92, zy - 0.3), 0.32, canvas, 8))
        bs0, bs1 = (14.5, 0, 4.2), (27.5 if era == "1600" else 26.0, 0, 9.0)
        parts.append(eic_rod(bs0, bs1, 0.38, wood, 8, 0.16))
        if yards:
            parts.append(eic_rod((23.0, -4, 6.6), (23.0, 4, 6.6), 0.13, wood, 6))
            if sails == "set":
                parts.append(eic_sail((23.2, -4.2, 2.6), (23.2, 4.2, 2.6), (23.2, -4, 6.6), (23.2, 4, 6.6), 0.9, canvas, 6, 6))
            elif sails == "furled":
                parts.append(eic_rod((23.1, -3.6, 6.3), (23.1, 3.6, 6.3), 0.26, canvas, 8))
        fz, mz = base + spec[0][1], base + spec[1][1]
        shrouds += [((9.5, 0, fz - 1.2), (24.0, 0, 7.4)), ((-0.5, 0, mz - 1.2), (9.5, 0, base + 1.5)), ((-11, 0, base + 13 - 1.2), (-0.5, 0, base + 5)),
                    ((9.5, 0, fz + 9), (bs1[0], 0, bs1[2])), ((-0.5, 0, mz + 11), (9.5, 0, fz + 1)), ((-11, 0, base + 13), (-17.5, 0, 8.5))]
        cu = bpy.data.curves.new("rig", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.045
        cu.bevel_resolution = 0
        for a, b in shrouds:
            sp = cu.splines.new("POLY")
            sp.points.add(1)
            sp.points[0].co = (*a, 1)
            sp.points[1].co = (*b, 1)
        rig = bpy.data.objects.new("rig", cu)
        eic_link(rig)
        cu.materials.append(rope)
        parts.append(rig)
        if flags:
            if era == "1600":
                parts.append(eic_flag(-0.5, 0, mz + 13.2, 3.2, 1.9, "george"))
                parts.append(eic_flag(9.5, 0, fz + 11.2, 2.6, 1.5, "george"))
                parts.append(eic_rod((-17.0, 0, 8.4), (-18.5, 0, 12.8), 0.07, wood, 6))
                parts.append(eic_flag(-18.5, 0, 10.6, 4.2, 2.4, "eic1600"))
            else:
                parts.append(eic_flag(-0.5, 0, mz + 11.0, 3.0, 1.6, "eic1707"))
                parts.append(eic_rod((-17.4, 0, 5.6), (-19.0, 0, 10.5), 0.07, wood, 6))
                parts.append(eic_flag(-19.0, 0, 8.0, 5.0, 2.8, "eic1707"))
                parts.append(eic_flag(bs1[0], 0, bs1[2], 1.6, 1.0, "union1707"))
    return eic_group(parts, (x, y, z), rz, s)


def eic_boat(x, y, rz=0.0, kind="perahu", s=1.0, z=0.0, sail=True, seed=0):
    rng = random.Random(seed)
    wood = eic_ph("boatwood", "weathered_brown_planks", 0.8, tint=(0.8, 0.68, 0.55), fallback=(0.35, 0.26, 0.18))
    pole = eic_col("pole", "#5A4630", 0.7)
    parts = []
    if kind == "perahu":
        h, _, _ = eic_hull("perahu", 12, 2.3, 0.7, 0.75, wood, 18, 0.0, 1.5, 1.5, 0.3, 0.9)
        parts.append(h)
        for xb in (-2.0, 2.0):
            parts.append(eic_rod((xb, -3.8, 0.9), (xb, 3.8, 0.9), 0.07, pole, 6))
        for sg in (1, -1):
            parts.append(eic_rod((-4.5, sg * 3.7, 0.15), (4.5, sg * 3.7, 0.15), 0.12, pole, 6))
        parts.append(add("cube", (-3.4, 0, 1.25), (1.4, 1.0, 0.05), m=eic_ph("atap", "reed_roof_04", 0.5, tint=(0.95, 0.85, 0.65))))
        if sail:
            sm = eic_pmat("tanja", lambda: eic_pat_matsail(base="#B5864E"), rough=0.9, translucent=0.2)
            parts.append(eic_rod((0.6, 0, 0.6), (1.0, 0, 7.5), 0.08, pole, 6))
            parts.append(eic_sail((-2.8, 0, 1.4), (4.6, 0, 2.4), (-1.0, 0, 7.4), (6.2, 0, 8.9), 0.5, sm, 6, 6, (0, 1, 0)))
            parts.append(eic_rod((-2.9, 0, 1.4), (4.7, 0, 2.4), 0.07, pole, 6))
            parts.append(eic_rod((-1.1, 0, 7.4), (6.3, 0, 8.9), 0.07, pole, 6))
    elif kind == "junk":
        h, _, _ = eic_hull("junk", 22, 6.0, 2.0, 2.4, wood, 20, 0.75, 1.2, 3.2, 0.4, 0.92)
        parts.append(h)
        parts.append(add("cube", (-8.5, 0, 4.8), (2.6, 2.6, 0.9), m=wood))
        parts.append(add("cube", (0, 0, 2.6), (11.3, 3.05, 0.08), m=eic_col("junkrail", "#7A2A1E", 0.6)))
        sm = eic_pmat("junksail", lambda: eic_pat_matsail(base="#8A4A2E", battens=9, strip=30), rough=0.9, translucent=0.15)
        for mx, mh, w_ in ((3.0, 17, 8.5), (-4.0, 13, 6.5), (8.5, 10, 4.5)):
            parts.append(eic_rod((mx, 0, 1.5), (mx, 0, mh), 0.18, pole, 8, 0.1))
            if sail:
                parts.append(eic_sail((mx - w_ * 0.7, 0, 3.2), (mx + w_ * 0.3, 0, 3.2), (mx - w_ * 0.75, 0, mh - 0.6), (mx + w_ * 0.35, 0, mh - 1.6),
                                      0.4, sm, 6, 8, (0, 1, 0)))
    elif kind in ("country", "budgerow", "dhow", "wherry", "lighter"):
        dims = {"country": (13, 3.0, 0.8, 1.0, 0.9, 1.8), "budgerow": (17, 4.4, 1.0, 1.3, 0.9, 1.6), "dhow": (18, 5.0, 1.6, 2.0, 1.4, 2.4),
                "wherry": (7, 1.6, 0.4, 0.5, 0.35, 0.45), "lighter": (12, 4.0, 0.7, 0.9, 0.2, 0.3)}[kind]
        Lh, Bh, Dh, Hh, sb, ss = dims
        h, hb, top = eic_hull(kind, Lh, Bh, Dh, Hh, wood, 18, 0.35 if kind in ("dhow", "wherry") else 0.1, sb, ss, 0.35, 0.92)
        parts.append(h)
        if kind == "country":
            hood = eic_ph("hood", "reed_roof_03", 0.7, tint=(0.9, 0.78, 0.55))
            parts.append(eic_gridm("hood", 8, 8, lambda u, v: (-3.5 + u * 5.0, math.cos(math.pi * v) * 1.35, 1.0 + math.sin(math.pi * v) * 1.3),
                                   hood))
            if sail:
                sm = eic_pmat("bengalsail", lambda: eic_pat_canvas(base="#D8C49A", seams=9), rough=0.9, translucent=0.25)
                parts.append(eic_rod((2.5, 0, 0.8), (2.5, 0, 9.5), 0.09, pole, 6))
                parts.append(eic_sail((2.7, -2.2, 2.4), (2.7, 2.2, 2.4), (2.7, -1.9, 9.2), (2.7, 1.9, 9.2), 0.8, sm, 6, 6))
                parts.append(eic_rod((2.7, -2.1, 9.2), (2.7, 2.1, 9.2), 0.06, pole, 6))
            parts.append(eic_rod((-6.0, 0.3, 2.6), (-7.4, 0.9, -0.3), 0.07, pole, 6))
        elif kind == "budgerow":
            cab = eic_pmat("budgcabin", lambda: eic_pat_budgerow(), rough=0.6)
            c = add("cube", (-2.5, 0, 2.3), (4.2, 1.9, 1.1), m=cab)
            parts.append(c)
            parts.append(add("cube", (-2.5, 0, 3.45), (4.5, 2.1, 0.08), m=eic_col("budroof", "#E8DFC8", 0.7)))
            parts.append(add("cube", (-2.5, 0, 3.6), (4.3, 1.9, 0.06), m=eic_pmat("awnstripe", lambda: eic_pat_stripes(cols=("#2E6B4A", "#E9DFC9", "#2E6B4A", "#E9DFC9")),
                                                                                    rough=0.8)))
            for k in range(4):
                for sg in (1, -1):
                    parts.append(eic_rod((3.0 + k * 1.2, sg * 2.0, 1.3), (3.4 + k * 1.2, sg * 4.0, -0.2), 0.05, pole, 5))
            if sail:
                sm = eic_pmat("bengalsail", lambda: eic_pat_canvas(base="#D8C49A", seams=9), rough=0.9, translucent=0.25)
                parts.append(eic_rod((4.0, 0, 1.0), (4.0, 0, 10.0), 0.1, pole, 6))
                parts.append(eic_sail((4.2, -2.4, 4.0), (4.2, 2.4, 4.0), (4.2, -2.1, 9.6), (4.2, 2.1, 9.6), 0.7, sm, 6, 6))
            parts.append(eic_flag(-6.6, 0, 4.0, 1.0, 0.6, "eic1707"))
            parts.append(eic_rod((-6.6, 0, 3.3), (-6.6, 0, 4.7), 0.03, pole, 5))
        elif kind == "dhow":
            sm = eic_pmat("dhowsail", lambda: eic_pat_canvas(base="#E3D2B0", seams=12), rough=0.9, translucent=0.25)
            parts.append(eic_rod((1.5, 0, 1.5), (2.6, 0, 13.0), 0.16, pole, 8, 0.09))
            ya, yb = (9.5, 0, 4.0), (-7.5, 0, 15.5)
            parts.append(eic_rod(ya, yb, 0.12, pole, 6, 0.07))
            if sail:
                parts.append(eic_sail(ya, (-5.5, 0, 2.6), yb, yb, 0.0, sm, 8, 6, (0, 1, 0)))
                sail_o = parts[-1]
                for v in sail_o.data.vertices:
                    v.co.y += 1.2 * math.sin(math.pi * min(1, max(0, (v.co.x + 7) / 17))) * 0.8
        elif kind == "wherry":
            parts.append(add("cube", (-2.2, 0, 0.45), (0.6, 0.6, 0.05), m=eic_col("cushion", "#7A2A2A", 0.8)))
            for sg in (1, -1):
                parts.append(eic_rod((0.3, sg * 0.7, 0.55), (0.9, sg * 3.4, -0.05), 0.04, pole, 5))
        elif kind == "lighter":
            bale = eic_bale_mat()
            for k in range(6):
                parts.append(add("cube", (-3.5 + (k % 3) * 2.6, -0.9 + (k // 3) * 1.8, 1.25), (1.1, 0.75, 0.5), (0, 0, rng.uniform(-0.1, 0.1)), m=bale))
    return eic_group(parts, (x, y, z), rz, s)


def eic_pat_budgerow(W=512, H=128):
    u, v = eic_grid(W, H)
    img = np.empty((H, W, 3), np.float32)
    img[:] = eic_srgb("#E8DFC8")
    fx = eic_frac(u * 10)
    win = (fx > 0.25) & (fx < 0.75) & (v > 0.25) & (v < 0.75)
    eic_put(img, win, "#2E6B4A")
    eic_put(img, win & (np.abs(eic_frac(v * 8) - 0.5) > 0.35), "#1E3A2A")
    eic_put(img, (v < 0.08) | (v > 0.92), "#2E6B4A")
    return img


def eic_bale_mat():
    return eic_ph("bale", "hessian_230", 1.6, tint=(1.0, 0.92, 0.8), fallback=(0.7, 0.6, 0.45))


# ------------------------------------------------------------------------------------------------ props
def eic_sack(x, y, z=0.0, s=1.0, rz=0.0, m=None):
    o = add("sphere", (x, y, z + 0.32 * s), (0.42 * s, 0.32 * s, 0.36 * s), (0, 0, rz), m=m or eic_bale_mat(), segments=12, ring_count=8)
    for v in o.data.vertices:
        if v.co.z < -0.6:
            v.co.z = -0.6 - (v.co.z + 0.6) * 0.15
        v.co.z += 0.06 * eic_noise.noise(Vector((v.co.x * 3 + x, v.co.y * 3 + y, v.co.z * 3)))
    smooth(o)
    return o


def eic_basket(x, y, z=0.0, r=0.4, h=0.35, fill=None, m=None):
    bm_ = m or eic_ph("basket", "bamboo_wall_02", 3.0, tint=(1.0, 0.85, 0.6), fallback=(0.6, 0.45, 0.25))
    add("cyl", (x, y, z + h / 2), (r, r, h / 2), m=bm_, vertices=20)
    add("torus", (x, y, z + h), (1, 1, 1), m=bm_, major_radius=r, minor_radius=0.03, major_segments=20, minor_segments=6)
    if fill:
        o = add("sphere", (x, y, z + h), (r * 0.95, r * 0.95, r * 0.45), m=fill, segments=16, ring_count=8)
        for v in o.data.vertices:
            if v.co.z < 0:
                v.co.z *= 0.1
        smooth(o)


def eic_spice_mat(name, hexcol, scale=40.0):
    def build():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        vo = nt.nodes.new("ShaderNodeTexVoronoi")
        vo.inputs["Scale"].default_value = scale
        nt.links.new(geo.outputs["Position"], vo.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMixRGB")
        c = eic_lin(hexcol)
        mr.inputs["Color1"].default_value = (*[v * 0.45 for v in c], 1)
        mr.inputs["Color2"].default_value = (*c, 1)
        nt.links.new(eic_m(nt, "MULTIPLY", vo.outputs["Distance"], 2.0), mr.inputs["Fac"])
        nt.links.new(mr.outputs["Color"], b.inputs["Base Color"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.9
        nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        b.inputs["Roughness"].default_value = 0.6
        return m
    return eic_cache(("spice", name), build)


def eic_barrel(x, y, z=0.0, s=1.0, lying=False):
    wood = eic_ph("barrel", "rough_wood", 2.0, tint=(0.75, 0.55, 0.35), fallback=(0.4, 0.28, 0.16))
    hoop = eic_col("hoop", "#2E2A26", 0.5, 0.6)
    rot = (0, math.radians(90), 0) if lying else (0, 0, 0)
    o = add("cyl", (x, y, z + (0.42 if lying else 0.5) * s), (0.42 * s, 0.42 * s, 0.5 * s), rot, m=wood, vertices=16)
    for v in o.data.vertices:
        f = 1 + 0.14 * (1 - (v.co.z) ** 2)
        v.co.x *= f
        v.co.y *= f
    smooth(o)
    if not lying:
        for hz in (0.12, 0.88):
            add("torus", (x, y, z + hz * s), (s, s, s), m=hoop, major_radius=0.46, minor_radius=0.025, major_segments=18, minor_segments=4)
    return o


def eic_chest(x, y, z=0.0, rz=0.0, s=1.0):
    wood = eic_ph("chestwood", "dark_wood", 2.0, tint=(0.8, 0.6, 0.45), fallback=(0.3, 0.18, 0.1))
    add("cube", (x, y, z + 0.32 * s), (0.6 * s, 0.38 * s, 0.32 * s), (0, 0, rz), m=wood)
    add("cube", (x, y, z + 0.66 * s), (0.62 * s, 0.4 * s, 0.03 * s), (0, 0, rz), m=eic_col("iron", "#2B2826", 0.45, 0.7))


def eic_carpet(x, y, w, l, style, seed=1, rz=0.0, z=0.012, **kw):
    key = f"carpet_{style}_{seed}"
    m = eic_pmat(key, lambda: eic_pat_carpet(seed=seed, style=style, **kw), rough=0.95, sheen=0.6, bump=0.15)
    return add("plane", (x, y, z), (w / 2, l / 2, 1), (0, 0, rz), m=m)


def eic_table_carpet(x, y, z, w, l, drop, style="ushak", seed=2, **kw):
    """A knotted carpet laid over a table: top plus four hanging sides."""
    m = eic_pmat(f"carpet_{style}_{seed}", lambda: eic_pat_carpet(seed=seed, style=style, **kw), rough=0.95, sheen=0.6, bump=0.15)
    add("plane", (x, y, z + 0.01), (w / 2, l / 2, 1), m=m)
    for sg in (1, -1):
        eic_cloth((x + sg * (w / 2 + 0.02), y, z - drop / 2), l, drop, m, rot=(math.radians(90), 0, math.radians(90)), folds=4, amp=0.03)
        eic_cloth((x, y + sg * (l / 2 + 0.02), z - drop / 2), w, drop, m, folds=3, amp=0.03)


def eic_canopy(x, y, z, w, d, m_top, m_val, pole_m, drop=0.6, poles=True, rz=0.0):
    objs = [add("cube", (0, 0, z), (w / 2, d / 2, 0.04), m=m_top)]
    for sg in (1, -1):
        objs.append(eic_cloth((0, sg * (d / 2 + 0.01), z - drop / 2), w, drop, m_val, folds=10, amp=0.025, nv=2))
        objs.append(eic_cloth((sg * (w / 2 + 0.01), 0, z - drop / 2), d, drop, m_val, rot=(math.radians(90), 0, math.radians(90)), folds=7,
                              amp=0.025, nv=2))
    if poles:
        for sx in (1, -1):
            for sy in (1, -1):
                objs.append(eic_rod((sx * w / 2, sy * d / 2, 0), (sx * w / 2, sy * d / 2, z + 0.25), 0.05, pole_m, 8))
                objs.append(add("sphere", (sx * w / 2, sy * d / 2, z + 0.3), (0.1, 0.1, 0.14), m=pole_m, segments=10, ring_count=6))
    return eic_group(objs, (x, y, 0), rz)


def eic_rain(x, y, w, h, rz=0.0):
    m = eic_pmat("rain", lambda: eic_pat_streaks(), rough=1.0, alpha=True, uv_scale=(3, 1))
    return add("plane", (x, y, h / 2), (w / 2, h / 2, 1), (math.radians(90), 0, rz), m=m)


# ================================================================================================ building kits
def eic_begin():
    sc = reset()
    sc.cycles.transparent_max_bounces = 24
    sc.cycles.sample_clamp_indirect = 6.0
    EIC_M.clear()
    return sc


def eic_area(loc, energy, color=(1, 0.88, 0.7), size=4.0, rot=(0, 0, 0), size_y=None):
    bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
    l = bpy.context.active_object
    l.data.energy = energy
    l.data.color = color
    if size_y:
        l.data.shape = "RECTANGLE"
        l.data.size, l.data.size_y = size, size_y
    else:
        l.data.size = size
    return l


def eic_tudor_house(xf, y, w, d, floors, rng, mats, sign=None):
    """Jettied timber-framed London house, street face towards +x at xf, gable to the street."""
    infill, timber, roof, win, brick, dark = mats
    hf, j = 2.9, 0.42
    for f in range(floors):
        x1, x0, z0 = xf + f * j, xf - d, f * hf
        add("cube", ((x0 + x1) / 2, y, z0 + hf / 2), ((x1 - x0) / 2, w / 2, hf / 2), m=infill)
        fx = x1 + 0.04
        npst = max(3, int(w / 0.95))
        for k in range(npst + 1):
            add("cube", (fx, y - w / 2 + k * w / npst, z0 + hf / 2), (0.06, 0.08, hf / 2), m=timber)
        for zz in (0.1, hf * 0.42, hf - 0.1):
            add("cube", (fx, y, z0 + zz), (0.07, w / 2 + 0.02, 0.08), m=timber)
        for sg in (-1, 1):
            add("cube", (fx, y + sg * (w / 2 - w / npst / 2), z0 + hf * 0.71), (0.05, 0.05, hf * 0.33), (math.radians(32 * sg), 0, 0), m=timber)
        if f > 0:
            add("cube", (x1 - 0.1, y, z0 + 0.06), (0.22, w / 2 + 0.06, 0.13), m=timber)
            ww = w * (0.62 if f == 1 else 0.5)
            add("cube", (fx + 0.06, y, z0 + hf * 0.6), (0.03, ww / 2, 0.52), m=win)
            for k in range(5):
                add("cube", (fx + 0.1, y - ww / 2 + k * ww / 4, z0 + hf * 0.6), (0.035, 0.035, 0.56), m=timber)
            add("cube", (fx + 0.12, y, z0 + hf * 0.6 - 0.56), (0.12, ww / 2 + 0.1, 0.05), m=timber)
        else:
            add("cube", (fx + 0.02, y - w * 0.12, 1.2), (0.03, w * 0.28, 0.75), m=dark)
            add("cube", (fx + 0.5, y - w * 0.12, 0.78), (0.48, w * 0.3, 0.04), m=timber)
            add("cube", (fx + 0.03, y + w * 0.33, 1.0), (0.04, 0.45, 1.0), m=timber)
    x0, x1 = xf - d, xf + (floors - 1) * j
    eic_gable((x0 + x1) / 2 + 0.1, y, floors * hf, (x1 - x0) / 2 + 0.15, w / 2, w * 0.72, roof, infill, over=0.25)
    gx = x1 + 0.2
    add("cube", (gx, y, floors * hf + w * 0.3), (0.06, 0.08, w * 0.3), m=timber)
    add("cube", (gx, y, floors * hf + 0.15), (0.07, w / 2, 0.08), m=timber)
    add("cube", (gx + 0.03, y, floors * hf + w * 0.24), (0.03, w * 0.18, 0.38), m=win)
    add("cube", (x0 + 1.2, y + w / 2 - 0.7, floors * hf + w * 0.55), (0.45, 0.5, w * 0.35 + 0.8), m=brick)
    if sign:
        sy = y - w / 2 + 0.5
        eic_rod((x1 + 0.05, sy, hf + 0.5), (x1 + 1.6, sy, hf + 0.5), 0.03, eic_col("iron", "#2B2826", 0.45, 0.7), 5)
        add("cube", (x1 + 1.0, sy, hf + 0.05), (0.42, 0.03, 0.36), m=sign)


def eic_pillar(x, y, z0, h, m, cap=None):
    """Akbari trabeate pillar: square base, octagonal mid shaft, stepped bracket capital."""
    cap = cap or m
    add("cube", (x, y, z0 + 0.25), (0.42, 0.42, 0.25), m=m)
    add("cube", (x, y, z0 + 0.5 + h * 0.18), (0.27, 0.27, h * 0.18), m=m)
    add("cyl", (x, y, z0 + 0.5 + h * 0.36 + h * 0.2), (0.27, 0.27, h * 0.2), (0, 0, math.radians(22.5)), m=m, vertices=8)
    add("cube", (x, y, z0 + 0.5 + h * 0.76 + (h * 0.24 - 0.5) / 2), (0.27, 0.27, (h * 0.24 - 0.5) / 2), m=m)
    zt = z0 + h
    for k, r in enumerate((0.45, 0.7, 0.95)):
        add("cube", (x, y, zt - 0.36 + k * 0.12), (r, 0.22, 0.06), m=cap)
        add("cube", (x, y, zt - 0.36 + k * 0.12), (0.22, r, 0.06), m=cap)


def eic_chhatri(x, y, z, r, m, dome_m, fin=None):
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("cube", (x + sx * r * 0.75, y + sy * r * 0.75, z + r * 0.9), (0.12 * r, 0.12 * r, r * 0.9), m=m)
    add("cube", (x, y, z + r * 1.85), (r * 1.05, r * 1.05, r * 0.08), m=m)
    d = add("sphere", (x, y, z + r * 1.9), (r * 0.85, r * 0.85, r * 0.95), m=dome_m, segments=24, ring_count=12)
    for v in d.data.vertices:
        if v.co.z < 0:
            v.co.z = 0
    smooth(d)
    add("cone", (x, y, z + r * 3.0), (0.12 * r, 0.12 * r, 0.3 * r), m=fin or eic_gold(), vertices=10)


def eic_baluster_row(p0, p1, step, src):
    a, b = Vector(p0), Vector(p1)
    n = max(1, int((b - a).length / step))
    for k in range(n + 1):
        p = a.lerp(b, k / n)
        eic_inst(src, p.x, p.y, p.z)


def eic_draped(x, y, z, w, l, drop, m, folds=4):
    add("plane", (x, y, z + 0.01), (w / 2, l / 2, 1), m=m)
    for sg in (1, -1):
        eic_cloth((x + sg * (w / 2 + 0.02), y, z - drop / 2), l, drop, m, rot=(math.radians(90), 0, math.radians(90)), folds=folds, amp=0.025)
        eic_cloth((x, y + sg * (l / 2 + 0.02), z - drop / 2), w, drop, m, folds=folds, amp=0.025)


def eic_table(x, y, w, l, h, m):
    add("cube", (x, y, h - 0.03), (w / 2, l / 2, 0.03), m=m)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("cube", (x + sx * (w / 2 - 0.08), y + sy * (l / 2 - 0.08), (h - 0.06) / 2), (0.04, 0.04, (h - 0.06) / 2), m=m)


def eic_jav_house(x, y, w, d, rz=0.0, h=2.8, stilt=1.0, roof_h=4.6, z=0.0, tier=False):
    wall = eic_ph("javplank", "weathered_brown_planks", 0.7, tint=(0.82, 0.68, 0.52), fallback=(0.35, 0.25, 0.16))
    post = eic_col("javpost", "#4A3524", 0.7)
    thatch = eic_ph("ijuk", "thatch_roof_angled", 0.4, tint=(0.7, 0.58, 0.45), fallback=(0.4, 0.32, 0.22))
    dark = eic_col("darkdoor", "#16110D", 0.9)
    objs = []
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            objs.append(eic_rod((sx * (w / 2 - 0.2), sy * (d / 2 - 0.2), 0), (sx * (w / 2 - 0.2), sy * (d / 2 - 0.2), stilt), 0.13, post, 6))
    objs.append(add("cube", (0, 0, stilt + 0.08), (w / 2, d / 2, 0.08), m=wall))
    objs.append(add("cube", (0, 0, stilt + 0.16 + h / 2), (w / 2 - 0.15, d / 2 - 0.15, h / 2), m=wall))
    objs.append(add("cube", (0, -d / 2 + 0.12, stilt + 0.16 + 1.0), (0.7, 0.05, 1.0), m=dark))
    objs.append(add("cube", (w * 0.3, -d / 2 + 0.12, stilt + 1.6), (0.45, 0.05, 0.35), m=dark))
    objs.append(eic_hip(0, 0, stilt + 0.16 + h, w / 2, d / 2, roof_h, thatch, ridge=0.3, over=1.1))
    if tier:
        objs.append(eic_hip(0, 0, stilt + 0.16 + h + roof_h * 0.62, w * 0.22, d * 0.18, roof_h * 0.55, thatch, ridge=0.2, over=0.5))
    objs.append(add("cube", (0, -d / 2 - 0.7, 0.35), (1.0, 0.6, 0.06), m=wall))
    return eic_group(objs, (x, y, z), rz)


def eic_chunam_house(x, y, w, d, h, rz, plaster, accent, z=0.0):
    """Flat-roofed lime-plastered house with a veranda on its local -x face (Calcutta, 1750s)."""
    objs = [add("cube", (0, 0, h / 2), (d / 2, w / 2, h / 2), m=plaster),
            add("cube", (0, 0, h + 0.05), (d / 2 + 0.15, w / 2 + 0.15, 0.1), m=plaster),
            add("cube", (0, 0, h + 0.5), (d / 2 + 0.05, w / 2 + 0.05, 0.42), m=plaster)]
    vh = h * 0.5
    vx = -d / 2 - 1.8
    nc = max(3, int(w / 2.2))
    for k in range(nc + 1):
        objs.append(add("cyl", (vx, -w / 2 + 0.4 + k * (w - 0.8) / nc, vh / 2), (0.17, 0.17, vh / 2), m=plaster, vertices=12))
    objs.append(add("cube", (vx + 0.9, 0, vh + 0.1), (1.1, w / 2, 0.12), m=plaster))
    for k in range(nc):
        yy = -w / 2 + 0.4 + (k + 0.5) * (w - 0.8) / nc
        objs.append(add("cube", (-d / 2 - 0.02, yy, vh * 0.42), (0.03, 0.45, vh * 0.38), m=accent))
        objs.append(add("cube", (-d / 2 - 0.02, yy, vh + (h - vh) * 0.5), (0.03, 0.4, (h - vh) * 0.3), m=accent))
    objs.append(add("cube", (vx + 0.6, 0, 0.12), (1.4, w / 2 + 0.2, 0.12), m=plaster))
    return eic_group(objs, (x, y, z), rz)


def eic_hut(x, y, rz, z=0.0, s=1.0):
    mud = eic_ph("mudwall", "clay_plaster", 0.4, tint=(0.85, 0.7, 0.52), fallback=(0.6, 0.48, 0.34))
    thatch = eic_ph("hutthatch", "thatch_roof_angled", 0.4, tint=(0.85, 0.72, 0.5), fallback=(0.55, 0.45, 0.3))
    objs = [add("cube", (0, 0, 1.1), (2.4, 1.7, 1.1), m=mud), add("cube", (0, -1.72, 0.85), (0.4, 0.04, 0.85), m=eic_col("darkdoor", "#16110D", 0.9))]
    objs += eic_chala(0, 0, 2.15, 2.9, 2.2, 1.7, thatch, droop=0.45, bulge=0.25)
    return eic_group(objs, (x, y, z), rz, s)


def eic_volcano(x, y, r, h, m, seed=1):
    o = add("sphere", (x, y, 0), (r, r, h), m=m, segments=64, ring_count=32)
    for v in o.data.vertices:
        rn = min(1.0, math.hypot(v.co.x, v.co.y))
        if v.co.z < 0:
            v.co.z = -0.02
            continue
        n = eic_noise.noise(Vector((v.co.x * 4 + seed, v.co.y * 4, 0)))
        v.co.z = max(0.0, (1 - rn) ** 1.6 * (1 + 0.12 * n))
    smooth(o)
    return o


def eic_boats_z(objs, z):
    for o in objs:
        o.location.z = z


# ================================================================================================ shots
def eic_shot_spice_quay():
    """Bantam/Banda-style spice port, c.1600, late afternoon: pepper, nutmeg, mace and cloves on the quay, Javanese
    warehouses and palms, perahus and a junk, an English galleon at anchor, a volcano island beyond (Gunung Api)."""
    sc = eic_begin()
    eic_sky("kloppenheim_06_puresky", 0.85, sun_az=150)
    eic_sun(150, 3.4, (1, 0.8, 0.55), lo=10, hi=22)
    exposure(-0.35)
    sand = eic_ph("quaysand", "coast_sand_01", 0.22, tint=(1.0, 0.9, 0.75), fallback=(0.75, 0.62, 0.45))
    planks = eic_ph("wharf", "weathered_planks", 0.45, tint=(0.85, 0.72, 0.58), fallback=(0.45, 0.35, 0.25))
    post = eic_col("pilepost", "#3A2C20", 0.8)
    edge = [(-300, -60), (300, -60), (300, 4), (40, 8), (14, 12), (-6, 20), (-30, 34), (-300, 60)]
    eic_poly_ground(edge, 1.0, sand)
    for (ax, ay), (bx, by) in zip(edge[2:-1], edge[3:]):                        # timber revetment along the water
        L = math.hypot(bx - ax, by - ay)
        add("cube", ((ax + bx) / 2, (ay + by) / 2, 0.2), (L / 2, 0.25, 0.85), (0, 0, math.atan2(by - ay, bx - ax)), m=planks)
    eic_water((0, 300, 0.0), (900, 900), "#2E6A6A", rough=0.04, wave=0.16, scale=0.3)
    add("cube", (9, 38, 1.0), (2.0, 26, 0.12), m=planks)                        # pier
    for k in range(14):
        for sx in (-2.1, 2.1):
            eic_rod((9 + sx, 13 + k * 3.9, -1.5), (9 + sx, 13 + k * 3.9, 1.5), 0.14, post, 6)
    eic_jav_house(-24, 30, 9, 7, rz=0.25, z=1.0, tier=True)
    eic_jav_house(-36, 22, 8, 6, rz=-0.15, z=1.0)
    eic_jav_house(-20, 48, 10, 7, rz=0.1, z=1.0, roof_h=5.2)
    eic_jav_house(-46, 40, 9, 7, rz=0.3, z=1.0, tier=True)
    palms = [eic_palm_proto(s, h=random.Random(s).uniform(8.5, 12.0)) for s in (1, 2, 3)]
    rng = random.Random(21)
    for px, py in ((-14, 26), (-30, 14), (-12, 40), (-40, 30), (-28, 58), (-52, 18), (-8, 30), (-60, 50), (-34, 70), (-18, 64), (-70, 36)):
        eic_inst(palms[rng.randrange(3)], px + rng.uniform(-1, 1), py + rng.uniform(-1, 1), 1.0, rng.uniform(0, 6.28), rng.uniform(0.85, 1.15))
    banana = eic_banana_proto(4)
    for px, py in ((-17, 18), (-20, 20), (-31, 40)):
        eic_inst(banana, px, py, 1.0, rng.uniform(0, 6), rng.uniform(0.9, 1.2))
    for k in range(60):                                                         # palm-lined far shore to the left
        eic_inst(palms[k % 3], rng.uniform(-420, -90), rng.uniform(70, 260), 0.8, rng.uniform(0, 6.28), rng.uniform(0.9, 1.3))
    hillm = eic_ph("hillgreen", "forest_ground_04", 0.02, tint=(0.55, 0.75, 0.45), fallback=(0.2, 0.32, 0.15))
    eic_hill(-300, 330, 260, 160, 45, hillm, 2)
    eic_volcano(-120, 1100, 480, 330, hillm, 3)
    eic_hill(380, 900, 300, 200, 60, hillm, 5)
    bale = eic_bale_mat()
    pepper = eic_spice_mat("pepper", "#2B231D", 60)
    nutmeg = eic_spice_mat("nutmeg", "#6B4426", 18)
    mace = eic_spice_mat("mace", "#C8461E", 30)
    clove = eic_spice_mat("clove", "#4A2418", 70)
    for i in range(6):
        for j in range(2):
            eic_sack(-13 + i * 0.85, 15 + j * 0.8, 1.0, rng.uniform(0.95, 1.1), rng.uniform(-0.3, 0.3), bale)
    for i in range(5):
        eic_sack(-12.6 + i * 0.85, 15.4, 1.55, 1.0, rng.uniform(-0.3, 0.3), bale)
    for i in range(3):
        eic_sack(-12.2 + i * 0.85, 15.4, 2.1, 0.95, rng.uniform(-0.3, 0.3), bale)
    fills = [pepper, nutmeg, mace, clove, pepper, mace, nutmeg]
    for k, (bx, by) in enumerate(((-6.5, 11), (-5.6, 11.7), (-4.7, 10.9), (-6.1, 10.0), (-4.0, 12.1), (-7.3, 12.0), (-5.0, 13.0))):
        eic_basket(bx, by, 1.0, rng.uniform(0.33, 0.42), 0.32, fills[k])
    add("plane", (-9.5, 10.0, 1.02), (1.3, 1.8, 1), (0, 0, 0.2), m=mace)
    add("plane", (-11.2, 7.2, 1.02), (1.2, 1.6, 1), (0, 0, -0.1), m=pepper)
    add("plane", (-8.0, 6.6, 1.02), (1.1, 1.4, 1), (0, 0, 0.3), m=clove)
    jar = eic_col("martaban", "#4A2E1C", 0.25)
    for jx, jy in ((-14.5, 9.5), (-15.2, 10.6), (-14.0, 11.2), (-15.9, 9.2)):
        o = add("sphere", (jx, jy, 1.55), (0.42, 0.42, 0.55), m=jar, segments=16, ring_count=10)
        smooth(o)
        add("cyl", (jx, jy, 2.15), (0.16, 0.16, 0.1), m=jar, vertices=12)
    stripe = eic_pmat("batik", lambda: eic_pat_stripes(cols=("#24305E", "#E9DFC9", "#A4302A", "#E9DFC9")), rough=0.85, translucent=0.3)
    eic_canopy(-8.0, 13.0, 3.3, 6.0, 4.0, stripe, stripe, eic_col("pole", "#5A4630", 0.7), drop=0.4).location.z = 1.0
    eic_chest(-3.2, 15.8, 1.0, 0.3)
    eic_chest(-2.4, 16.9, 1.0, -0.2)
    for k, (bx, by) in enumerate(((-2.8, 3.0), (-3.6, 3.9), (-1.9, 4.3))):
        eic_basket(bx, by, 1.0, 0.36, 0.3, (nutmeg, mace, pepper)[k])
    eic_sack(-4.4, 2.6, 1.0, 1.05, 0.4, bale)
    eic_boat(4.6, 25, math.radians(92), "perahu", sail=False, seed=1)
    eic_boat(13.6, 31, math.radians(88), "perahu", sail=True, seed=2)
    eic_boat(4.4, 46, math.radians(95), "perahu", sail=False, seed=3)
    eic_boat(-30, 120, math.radians(15), "perahu", sail=True, seed=4)
    eic_boat(42, 80, math.radians(150), "junk", s=1.0)
    eic_boat(-90, 160, math.radians(20), "junk", s=0.9)
    eic_ship(60, 215, math.radians(195), 1.0, "1600", "furled")
    eic_ship(-70, 390, math.radians(160), 0.95, "1600", "furled")
    eic_aerial(45, 700, 0.8)
    camera_path([(0.0, (6, -12, 2.7)), (1.0, (8.2, -9.9, 2.65))], lens=30, target_keys=[(0.0, (-2, 40, 3.4)), (1.0, (1, 42, 3.5))])
    return sc


def eic_st_pauls(x, y, stone, lead):
    """Old St Paul's after 1561: long Gothic nave, transepts and a squat flat-topped crossing tower (no spire)."""
    add("cube", (x, y, 15), (62, 10, 15), m=stone)
    eic_gable(x, y, 30, 62, 10, 9, lead, stone, over=0.2)
    for sg in (-1, 1):
        add("cube", (x, y + sg * 14, 8), (60, 4, 8), m=stone)
        for k in range(20):
            add("cube", (x - 57 + k * 6, y + sg * 18.4, 7), (0.8, 0.8, 7.5), m=stone)
            add("cube", (x - 54 + k * 6, y + sg * 10.05, 20), (0.6, 0.05, 4.0), m=eic_col("lancet", "#1A1C20", 0.4))
    add("cube", (x + 18, y, 15), (9, 30, 15), m=stone)
    eic_gable(x + 18, y, 30, 30, 9, 8, lead, stone, rz=math.radians(90), over=0.2)
    add("cube", (x + 18, y, 38), (10, 10, 38), m=stone)
    add("cube", (x + 18, y, 76.5), (10.6, 10.6, 0.6), m=stone)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("cube", (x + 18 + sx * 9.6, y + sy * 9.6, 40), (1.2, 1.2, 40), m=stone)
            add("cone", (x + 18 + sx * 9.6, y + sy * 9.6, 82), (1.3, 1.3, 2.5), m=lead, vertices=8)
    for k in range(3):
        add("cube", (x + 18 - 10.05, y - 5 + k * 5, 58), (0.05, 1.1, 7), m=eic_col("lancet", "#1A1C20", 0.4))


def eic_london_bridge(x0, x1, y, z_water, stone, mats, rng):
    n = 19
    bay = (x1 - x0) / n
    eic_arcade(x0, y, n, bay, 1.5, bay * 0.3, 6.6, 10, bay * 0.42, stone, z0=z_water, p=1.2, q=0.6)
    for i in range(n + 1):
        add("cube", (x0 + i * bay, y, z_water + 0.3), (bay * 0.26, 8.5, 0.7), m=stone)
    infill, timber, roof = mats
    xx = x0 + 2
    while xx < x1 - 4:
        w = rng.uniform(4.5, 8)
        if rng.random() < 0.85:
            for sg in (-1, 1):
                h = rng.uniform(9, 14)
                add("cube", (xx + w / 2, y + sg * 3.6, z_water + 6.6 + h / 2), (w / 2 - 0.1, 2.6, h / 2), m=infill)
                eic_gable(xx + w / 2, y + sg * 3.6, z_water + 6.6 + h, w / 2 - 0.1, 2.6, 2.8, roof, infill, over=0.2)
        xx += w
    nx = x0 + (x1 - x0) * 0.82                                                  # Nonsuch House
    ns = eic_col("nonsuch", "#D8C9A8", 0.7)
    add("cube", (nx, y, z_water + 6.6 + 8), (9, 7, 8), m=ns)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("cyl", (nx + sx * 9, y + sy * 7, z_water + 6.6 + 9), (1.8, 1.8, 9), m=ns, vertices=12)
            add("sphere", (nx + sx * 9, y + sy * 7, z_water + 6.6 + 19.5), (2.0, 2.0, 2.6), m=eic_col("cupola", "#4E5A52", 0.5), segments=12, ring_count=8)
            add("cone", (nx + sx * 9, y + sy * 7, z_water + 6.6 + 23), (0.4, 0.4, 1.4), m=eic_gold(), vertices=8)
    gx = x1 - 6
    add("cube", (gx, y, z_water + 6.6 + 7), (5, 8, 7), m=stone)
    for sg in (-1, 1):
        add("cyl", (gx, y + sg * 8, z_water + 6.6 + 8), (2.6, 2.6, 8), m=stone, vertices=12)


def eic_shot_london():
    sc = eic_begin()
    eic_sky("kloofendal_28d_misty_puresky", 0.95, sun_az=150)
    eic_sun(150, 2.4, (1, 0.88, 0.72), lo=15, hi=30)
    exposure(-0.25)
    rng = random.Random(16)
    cob = eic_ph("cobbles", "cobblestone_floor_03", 0.4, tint=(0.82, 0.74, 0.64), fallback=(0.4, 0.37, 0.33))
    mud = eic_ph("bankmud", "brown_mud_dry", 0.1, tint=(0.8, 0.75, 0.65), fallback=(0.35, 0.3, 0.24))
    stone = eic_ph("londonstone", "castle_wall_varriation", 0.12, tint=(0.95, 0.9, 0.8), fallback=(0.6, 0.56, 0.5))
    lead = eic_col("leadroof", "#6C7074", 0.5, 0.3)
    infills = [eic_ph("limewash", "white_plaster_rough_01", 0.3, tint=(0.92, 0.87, 0.77), fallback=(0.85, 0.8, 0.7)),
               eic_ph("ochre", "white_plaster_rough_02", 0.3, tint=(0.86, 0.68, 0.45), fallback=(0.75, 0.6, 0.4))]
    timber = eic_ph("oakframe", "medieval_wood", 0.6, tint=(0.62, 0.52, 0.44), fallback=(0.3, 0.24, 0.18))
    roof = eic_ph("tiles", "clay_roof_tiles", 0.5, tint=(0.95, 0.75, 0.62), fallback=(0.55, 0.3, 0.2))
    win = eic_pmat("leaded_ext", lambda: eic_pat_leaded(glass="#4A5560"), rough=0.15, uv_scale=(2, 1))
    brick = eic_ph("chimney", "medieval_red_brick", 0.6, tint=(0.9, 0.75, 0.65), fallback=(0.45, 0.22, 0.15))
    dark = eic_col("shopdark", "#15110E", 0.9)
    signs = [eic_col("sign" + c, c, 0.6) for c in ("#7A2A1E", "#2B3F6E", "#2E5A3A", "#B08A3A")]
    eic_poly_ground([(-500, -60), (8, -60), (8, 700), (-500, 700)], 0.0, cob)
    eic_poly_ground([(240, -60), (700, -60), (700, 700), (240, 700)], 0.0, mud, name="southwark")
    add("cube", (8.4, 200, -1.4), (0.5, 260, 1.4), m=stone)
    for k in range(40):
        eic_rod((8.9, -8 + k * 3, -2.2), (8.9, -8 + k * 3, 0.5), 0.13, timber, 6)
    eic_water((120, 300, -1.6), (300, 500), "#56675E", rough=0.06, wave=0.12, scale=0.35)
    y = -8.0
    k = 0
    while y < 125:
        w = rng.uniform(4.8, 6.8)
        eic_tudor_house(-5.2 + rng.uniform(-0.3, 0.3), y + w / 2, w, 9.0, rng.choice([3, 3, 4]), rng,
                        (infills[k % 2 if rng.random() < 0.7 else 0], timber, roof, win, brick, dark), signs[k % 4] if k % 3 == 1 else None)
        y += w + 0.05
        k += 1
    protos = []
    for i in range(3):
        a = add("cube", (0, 0, 4.5 + i), (4, 3, 4.5 + i), m=infills[i % 2])
        b = eic_gable(0, 0, 9 + 2 * i, 4, 3, 3.2, roof, infills[i % 2])
        protos.append(eic_proto([a, b], f"cityhouse{i}"))
    for _ in range(260):
        hx, hy = rng.uniform(-260, -16), rng.uniform(5, 520)
        if hx > -22 and hy < 130:
            continue
        eic_inst(protos[rng.randrange(3)], hx, hy, 0, rng.choice([0, 1.5708]) + rng.uniform(-0.1, 0.1), rng.uniform(0.9, 1.3))
    for _ in range(70):
        eic_inst(protos[rng.randrange(3)], rng.uniform(250, 520), rng.uniform(40, 520), 0, rng.choice([0, 1.5708]), rng.uniform(0.8, 1.1))
    for cx, cy, h in ((-45, 150, 22), (-95, 110, 26), (-30, 255, 20), (-140, 210, 24), (290, 260, 20)):
        add("cube", (cx, cy, h / 2), (2.8, 2.8, h / 2), m=stone)
        add("cone", (cx, cy, h + 3), (2.2, 2.2, 3), m=lead, vertices=8)
    eic_st_pauls(-120, 360, stone, lead)
    eic_london_bridge(8, 240, 230, -1.6, stone, (infills[1], timber, roof), rng)
    add("cyl", (280, 120, 6), (15, 15, 6), m=infills[0], vertices=20)
    add("cyl", (280, 120, 12.6), (15.6, 15.6, 0.8), m=eic_ph("globethatch", "thatch_roof_angled", 0.3, tint=(0.8, 0.68, 0.5)), vertices=20)
    eic_rod((280, 120, 12), (280, 120, 19.6), 0.08, timber)
    eic_flag(280, 120, 18, 3, 1.6, "george")
    eic_ship(55, 70, math.radians(98), 0.95, "1600", "furled", z=-1.6)
    eic_ship(100, 135, math.radians(84), 0.85, "1600", "furled", z=-1.6)
    eic_ship(160, 185, math.radians(92), 0.7, "1600", "furled", z=-1.6)
    for k in range(9):
        eic_boat(rng.uniform(12, 60), rng.uniform(4, 150), math.radians(rng.uniform(60, 120)), "wherry", z=-1.6, seed=k)
    eic_aerial(18, 260, 0.88)
    camera_path([(0.0, (1.5, -14, 1.85)), (1.0, (2.5, -11.6, 1.85))], lens=30, target_keys=[(0.0, (-1, 60, 5.2)), (1.0, (0, 62, 5.3))])
    return sc


def eic_shot_whitehall():
    sc = eic_begin()
    sc.cycles.max_bounces = 6
    flat_world((0.78, 0.83, 0.9), 1.4)
    sun(28, 197 + 90, 5.5, (1, 0.9, 0.75), 1.0)
    exposure(0.2)
    plaster = eic_ph("hallplaster", "white_plaster_rough_01", 0.3, tint=(0.93, 0.87, 0.77), fallback=(0.85, 0.8, 0.7))
    oak = eic_ph("hall_oak", "dark_wood", 0.8, tint=(0.8, 0.6, 0.45), fallback=(0.25, 0.16, 0.1))
    stonew = eic_ph("winstone", "white_sandstone_blocks_02", 0.4, tint=(0.95, 0.9, 0.82))
    panels = eic_pmat("wainscot", lambda: eic_pat_panels(), rough=0.45, bump=0.6, coat=0.2, uv_scale=(10, 1))
    rush = eic_pmat("rush", lambda: eic_pat_rush(), rough=0.9, bump=0.3, uv_scale=(6, 11.2))
    tap = eic_pmat("tapestry", lambda: eic_pat_tapestry(), rough=0.95, sheen=0.5)
    tap2 = eic_pmat("tapestry2", lambda: eic_pat_tapestry(seed=8, field="#3A4A3C"), rough=0.95, sheen=0.5)
    dam = eic_pmat("damask", lambda: eic_pat_damask(), rough=0.55, sheen=0.6)
    val = eic_pmat("valance_c", lambda: eic_pat_valance(base="#8E1B23", gold="#C9A24A"), rough=0.6, sheen=0.5, alpha=True)
    glass = eic_pmat("leaded", lambda: eic_pat_leaded(), rough=0.2, transmit=True, uv_scale=(3, 3))
    velvet = eic_col("velvet", "#7E1620", 0.75)
    add("plane", (0, 4, 0), (7.5, 14, 1), m=rush)
    add("plane", (0, 4, 9.5), (7.5, 14, 1), (math.radians(180), 0, 0), m=plaster)
    for k in range(14):
        add("cube", (0, -9 + k * 2, 9.3), (7.5, 0.14, 0.2), m=oak)
    for x in (-3.75, 0, 3.75):
        add("cube", (x, 4, 9.25), (0.14, 14, 0.25), m=oak)
    add("cube", (0, 18.3, 4.75), (7.8, 0.3, 4.75), m=plaster)
    add("cube", (0, -10.3, 4.75), (7.8, 0.3, 4.75), m=plaster)
    wins = [-2.0, 5.0, 12.0]                                                    # left wall with three mullioned windows
    add("cube", (-7.8, 4, 1.1), (0.3, 14, 1.1), m=plaster)
    add("cube", (-7.8, 4, 8.5), (0.3, 14, 1.0), m=plaster)
    edges = [-10] + [v for c in wins for v in (c - 1.3, c + 1.3)] + [18]
    for a, b in zip(edges[0::2], edges[1::2]):
        add("cube", (-7.8, (a + b) / 2, 4.85), (0.3, (b - a) / 2, 2.65), m=plaster)
    for c in wins:
        add("plane", (-7.65, c, 4.85), (2.6 / 2, 5.3 / 2, 1), (math.radians(90), 0, math.radians(90)), m=glass)
        for dy in (-0.43, 0.43):
            add("cube", (-7.62, c + dy, 4.85), (0.12, 0.08, 2.65), m=stonew)
        add("cube", (-7.62, c, 5.9), (0.12, 1.3, 0.08), m=stonew)
        add("cube", (-7.45, c, 2.15), (0.3, 1.4, 0.06), m=stonew)
    add("plane", (-7.48, 4, 1.1), (14, 1.1, 1), (math.radians(90), 0, math.radians(90)), m=panels)
    for a, b in ((-10, 0), (7.4, 18)):                                          # right wall, screen, tapestries
        add("cube", (7.8, (a + b) / 2, 4.75), (0.3, (b - a) / 2, 4.75), m=plaster)
        add("plane", (7.48, (a + b) / 2, 1.5), ((b - a) / 2, 1.5, 1), (math.radians(90), 0, math.radians(-90)), m=panels)
    add("cube", (7.8, 3.7, 7.1), (0.3, 3.7, 2.4), m=plaster)
    eic_arcade(7.4, 0.1, 3, 2.43, 2.5, 1.2, 4.3, 0.35, 0.5, oak, rz=math.radians(90), p=2, q=0.5)
    add("cube", (7.3, 3.75, 4.55), (0.35, 3.8, 0.28), m=oak)
    for k in range(4):
        add("cube", (7.12, 0.1 + k * 2.43, 2.0), (0.1, 0.18, 2.0), m=oak)
        add("sphere", (7.2, 0.1 + k * 2.43, 5.05), (0.16, 0.16, 0.22), m=oak, segments=10, ring_count=6)
    for k in range(9):
        add("cube", (7.12, 0.4 + k * 0.85, 4.95), (0.05, 0.12, 0.12), (math.radians(45), 0, 0), m=oak)
    add("cube", (10.0, 3.7, 3), (0.2, 3.8, 3), m=plaster)
    add("plane", (8.8, 3.7, 0.01), (1.4, 3.8, 1), m=rush)
    add("plane", (8.8, 3.7, 4.9), (1.4, 3.8, 1), (math.radians(180), 0, 0), m=oak)
    light("POINT", (8.8, 3.7, 3.0), 60, (1, 0.75, 0.45), 0.5)
    eic_cloth((7.45, 10.2, 4.9), 4.4, 3.2, tap, rot=(math.radians(90), 0, math.radians(-90)), folds=5, amp=0.03)
    eic_cloth((7.45, 15.0, 4.9), 4.4, 3.2, tap2, rot=(math.radians(90), 0, math.radians(-90)), folds=5, amp=0.03)
    add("plane", (0, 17.98, 1.5), (7.5, 1.5, 1), (math.radians(90), 0, 0), m=panels)        # dais end
    eic_cloth((-5.0, 17.95, 4.9), 4.2, 3.2, tap2, folds=5, amp=0.03)
    eic_cloth((5.0, 17.95, 4.9), 4.2, 3.2, tap, folds=5, amp=0.03)
    eic_cloth((0, 17.9, 3.7), 3.6, 5.2, dam, folds=6, amp=0.04)
    add("cube", (0, 16.3, 6.35), (2.0, 1.7, 0.12), m=dam)
    eic_cloth((0, 14.58, 5.98), 4.0, 0.62, val, folds=10, amp=0.02, nv=2)
    for sg in (-1, 1):
        eic_cloth((sg * 2.02, 16.3, 5.98), 3.4, 0.62, val, rot=(math.radians(90), 0, math.radians(90)), folds=8, amp=0.02, nv=2)
    add("cube", (0, 15.7, 0.15), (3.3, 2.5, 0.15), m=oak)
    add("cube", (0, 16.3, 0.42), (2.5, 1.7, 0.12), m=oak)
    eic_carpet(0, 16.2, 4.4, 3.0, "ushak", seed=7, z=0.55, field="#9C2A2A", border="#1E2E5A")
    cx, cy, cz = 0, 16.9, 0.54                                                  # chair of estate
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("cube", (cx + sx * 0.42, cy + sy * 0.35, cz + 0.25), (0.05, 0.05, 0.25), m=eic_gold())
        add("cube", (cx + sx * 0.46, cy, cz + 0.75), (0.05, 0.38, 0.05), m=eic_gold())
        add("cube", (cx + sx * 0.42, cy + 0.38, cz + 1.0), (0.05, 0.05, 0.5), m=eic_gold())
        add("sphere", (cx + sx * 0.42, cy + 0.38, cz + 1.58), (0.08, 0.08, 0.1), m=eic_gold(), segments=10, ring_count=6)
    add("cube", (cx, cy, cz + 0.52), (0.48, 0.42, 0.07), m=velvet)
    add("cube", (cx, cy + 0.4, cz + 1.05), (0.42, 0.05, 0.45), m=velvet)
    add("cube", (cx, cy - 0.05, cz + 0.64), (0.44, 0.36, 0.06), m=dam)
    eic_table(-5.3, 8.0, 1.0, 2.2, 0.85, oak)                                   # tables with Turkey carpets
    eic_table_carpet(-5.3, 8.0, 0.86, 1.25, 2.5, 0.6, "ushak", seed=2, field="#9C2A2A", border="#1B1F3A")
    eic_table(5.1, 12.8, 1.0, 2.0, 0.85, oak)
    eic_table_carpet(5.1, 12.8, 0.86, 1.25, 2.3, 0.6, "medallion", seed=3, field="#8F2430", border="#203A63")
    eic_chest(-6.6, 13.5, 0, math.radians(90))
    flame = eic_col("flame", "#FFB060", 0.5, emit=25)
    wax = eic_col("wax", "#EDE6D2", 0.6)
    for by in (3.5, 10.5):                                                      # candle beams
        eic_rod((0, by, 6.6), (0, by, 9.4), 0.02, eic_col("iron", "#2B2826", 0.45, 0.7), 5)
        for rz in (0, math.radians(90)):
            add("cube", (0, by, 6.6), (1.3, 0.07, 0.07), (0, 0, rz), m=oak)
        for k in range(8):
            a = k * math.pi / 4
            r = 1.2 if k % 2 == 0 else 0.6
            px, py = math.cos(a) * r, by + math.sin(a) * r
            add("cyl", (px, py, 6.78), (0.035, 0.035, 0.12), m=wax, vertices=8)
            add("sphere", (px, py, 6.95), (0.025, 0.025, 0.05), m=flame, segments=8, ring_count=4)
        light("POINT", (0, by, 6.8), 120, (1, 0.72, 0.4), 1.0)
    eic_area((0, 6, 9.0), 900, (1, 0.88, 0.7), 10, size_y=20)
    eic_area((0, -9.5, 4.5), 500, (1, 0.9, 0.78), 6, rot=(math.radians(90), 0, 0))
    eic_area((0, 13.5, 5.5), 250, (1, 0.8, 0.6), 3, rot=(math.radians(60), 0, 0))
    camera_path([(0.0, (1.2, -8.5, 1.9)), (1.0, (0.4, -6.8, 1.9))], lens=24, target_keys=[(0.0, (0, 16, 2.6)), (1.0, (0, 16, 2.5))])
    return sc


def eic_tread_crane(x, y, rz, wood, roof):
    rope = eic_col("rope", "#2E261C", 0.8)
    objs = []
    for sx in (-1, 1):
        objs.append(add("torus", (sx * 0.65, 0, 2.9), (1, 1, 1), (0, math.radians(90), 0), m=wood, major_radius=2.5, minor_radius=0.09,
                        major_segments=40, minor_segments=6))
        for k in range(8):
            objs.append(add("cube", (sx * 0.65, 0, 2.9), (0.05, 2.45, 0.05), (k * math.pi / 8, 0, 0), m=wood))
    for k in range(20):
        a = k * 2 * math.pi / 20
        objs.append(add("cube", (0, math.cos(a) * 2.5, 2.9 + math.sin(a) * 2.5), (0.7, 0.07, 0.03), (a, 0, 0), m=wood))
    objs.append(eic_rod((-1.6, 0, 2.9), (1.6, 0, 2.9), 0.18, wood))
    for sx in (-1.4, 1.4):
        for sy in (-2.9, 2.9):
            objs.append(add("cube", (sx, sy, 3.3), (0.12, 0.12, 3.3), m=wood))
    objs.append(add("cube", (0, 0, 6.6), (1.6, 3.1, 0.12), m=wood))
    objs.append(eic_gable(0, 0, 6.7, 1.7, 3.3, 1.6, roof, wood, rz=math.radians(90)))
    objs.append(eic_rod((1.5, 0, 6.0), (8.5, 0, 10.0), 0.16, wood, 6, 0.1))
    objs.append(eic_rod((1.5, 0, 4.0), (8.5, 0, 10.0), 0.1, wood, 6))
    objs.append(eic_rod((8.5, 0, 10.0), (8.5, 0, 3.2), 0.03, rope, 5))
    objs.append(eic_rod((0, 0.5, 3.0), (8.4, 0, 9.9), 0.03, rope, 5))
    objs.append(eic_barrel(8.5, 0, 2.0, 0.9))
    return eic_group(objs, (x, y, 0), rz)


def eic_ship_frame(x, y, rz, wood):
    """Hull in frame on the slip: keel, stem, sternpost, ribs and ribbands, scaffold poles."""
    objs = [add("cube", (0, 0, 1.0), (16, 0.3, 0.35), m=wood)]
    for k in range(9):
        objs.append(add("cube", (-14 + k * 3.5, 0, 0.35), (0.6, 0.8, 0.35), m=wood))
    objs.append(eic_tube("stem", [(16, 0, 1.0), (18, 0, 3.5), (19.5, 0, 6.5), (20, 0, 8.5)], 0.25, wood, 6))
    objs.append(eic_rod((-16, 0, 1.0), (-17.5, 0, 9.5), 0.28, wood, 6))
    for k in range(17):
        xk = -14 + k * 1.75
        b = 4.6 * max(0.15, 1 - (xk / 16) ** 2) ** 0.5
        pts = [(xk, -b * 0.88, 8.0), (xk, -b, 5.5), (xk, -b * 0.92, 3.4), (xk, -b * 0.6, 1.9), (xk, 0, 1.3), (xk, b * 0.6, 1.9), (xk, b * 0.92, 3.4),
               (xk, b, 5.5), (xk, b * 0.88, 8.0)]
        objs.append(eic_tube("rib", pts, 0.13, wood, 5, cap=False))
    for sg in (-1, 1):
        for zz, f in ((3.4, 0.92), (5.5, 1.0)):
            objs.append(eic_tube("ribband", [(xx, sg * (4.6 * max(0.15, 1 - (xx / 16) ** 2) ** 0.5 * f + 0.12), zz) for xx in range(-14, 15, 2)],
                                 0.1, wood, 5, cap=False))
        for k in range(6):
            objs.append(eic_rod((-12 + k * 5, sg * 6.2, 0), (-12 + k * 5, sg * 6.2, 9.5), 0.09, wood, 5))
        objs.append(eic_rod((-13, sg * 6.2, 6), (13, sg * 6.2, 6), 0.07, wood, 5))
    return eic_group(objs, (x, y, 0), rz)


def eic_windmill(x, y, z, wood, cloth):
    objs = [eic_rod((0, 0, 0), (0, 0, 4), 0.3, wood), add("cube", (0, 0, 6.5), (2.0, 1.6, 2.5), m=wood)]
    objs.append(eic_gable(0, 0, 9.0, 2.0, 1.6, 1.2, wood, wood))
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        objs.append(add("cube", (0, -1.8, 7.5), (0.12, 0.05, 5.5), (0, a, 0), m=wood))
        objs.append(add("plane", (math.sin(a) * 3.2, -1.85, 7.5 + math.cos(a) * 3.2), (0.7, 2.4, 1), (math.radians(90), a, 0), m=cloth))
    return eic_group(objs, (x, y, z), 0.3)


def eic_shot_deptford():
    sc = eic_begin()
    eic_sky("kloofendal_48d_partly_cloudy_puresky", 0.8, sun_az=140)
    eic_sun(140, 3.0, (1, 0.9, 0.78), lo=22, hi=40)
    exposure(-0.4)
    rng = random.Random(5)
    mud = eic_ph("yardmud", "brown_mud_dry", 0.18, tint=(0.85, 0.78, 0.66), fallback=(0.4, 0.33, 0.25))
    chips = eic_ph("chips", "wood_chips", 0.5, tint=(0.9, 0.8, 0.65), fallback=(0.55, 0.45, 0.3))
    stone = eic_ph("quaystone", "stone_wall", 0.25, tint=(0.85, 0.82, 0.75), fallback=(0.5, 0.48, 0.44))
    wood = eic_ph("yardwood", "rough_wood", 0.5, tint=(0.82, 0.68, 0.52), fallback=(0.4, 0.3, 0.2))
    bark = eic_ph("logbark", "bark_brown_01", 0.8, tint=(0.8, 0.7, 0.6), fallback=(0.3, 0.22, 0.15))
    roof = eic_ph("tiles", "clay_roof_tiles", 0.5, tint=(0.95, 0.75, 0.62), fallback=(0.55, 0.3, 0.2))
    brick = eic_ph("storebrick", "medieval_red_brick", 0.45, tint=(0.92, 0.75, 0.65), fallback=(0.45, 0.22, 0.15))
    grass = eic_ph("marsh", "leafy_grass", 0.05, tint=(0.75, 0.85, 0.6), fallback=(0.25, 0.35, 0.15))
    canvas = eic_pmat("canvas", lambda: eic_pat_canvas(), rough=0.85, translucent=0.25, sheen=0.2)
    eic_poly_ground([(-300, -60), (300, -60), (300, 20), (-12, 20), (-12, 75), (-300, 75)], 0.0, mud)
    add("plane", (-30, 45, 0.02), (16, 24, 1), m=chips)
    add("cube", (144, 20.4, -1.3), (156, 0.4, 1.3), m=stone)
    add("cube", (-12.4, 47.5, -1.3), (0.4, 27.5, 1.3), m=stone)
    for k in range(50):
        eic_rod((-10 + k * 3.2, 20.9, -2.6), (-10 + k * 3.2, 20.9, 0.6), 0.15, wood, 6)
    eic_water((100, 300, -2.2), (500, 400), "#4E5E56", rough=0.06, wave=0.12, scale=0.35)
    eic_poly_ground([(-600, 230), (600, 230), (600, 900), (-600, 900)], -1.2, grass, name="isledogs")
    tree = eic_tree_proto(3, h=8, crown=5, leaf=eic_leaf_mat("elm", "#24391E", "#4E6A33", 4))
    for k in range(40):
        eic_inst(tree, rng.uniform(-400, 400), rng.uniform(260, 600), -1.2, rng.uniform(0, 6), rng.uniform(0.8, 1.4))
    eic_windmill(-60, 300, -1.2, wood, canvas)
    eic_windmill(140, 340, -1.2, wood, canvas)
    eic_ship(19, 33, math.radians(180), 1.0, "1600", "none", flags=False, z=-2.2, yards=False)   # fitting out: masts stepped, no sails yet
    eic_ship(130, 150, math.radians(10), 0.8, "1600", "set", flags=True, z=-2.2)
    eic_ship(-80, 120, math.radians(-15), 0.75, "1600", "furled", flags=True, z=-2.2)
    rope = eic_col("rope", "#2E261C", 0.8)
    for sx in (10.5, 17.5):                                                     # sheer legs over the hull
        eic_rod((sx, 18.6, 0), (14, 28, 22), 0.22, wood, 8, 0.15)
    eic_rod((14, 28, 22), (14, -2, 0), 0.04, rope, 5)
    eic_rod((14, 28, 22), (14, 28, 6), 0.04, rope, 5)
    add("cube", (14, 28, 5.8), (0.25, 0.18, 0.35), m=wood)
    eic_tread_crane(-4, 15.5, math.radians(90), wood, roof)
    for r in range(3):                                                          # log stack
        for i in range(5 - r):
            yy = 5.5 + i * 0.68 + r * 0.34
            eic_rod((-21, yy, 0.32 + r * 0.58), (-11.5, yy, 0.32 + r * 0.58), 0.33, bark, 10)
    for k in range(12):                                                         # plank stacks
        add("cube", (-8.6, 11.5, 0.05 + k * 0.055), (0.32, 2.4, 0.025), (0, 0, rng.uniform(-0.03, 0.03)), m=wood)
        add("cube", (-9.4, 13.2, 0.05 + k * 0.055), (1.6, 0.3, 0.025), (0, 0, rng.uniform(-0.03, 0.03)), m=wood)
    for bx, by in ((-1.5, 14.0), (-0.6, 14.4), (-1.1, 15.2), (0.3, 15.0), (3.6, 16.2), (4.5, 16.0), (4.1, 17.0)):
        eic_barrel(bx, by, 0, rng.uniform(0.9, 1.05))
    eic_barrel(-1.0, 14.6, 1.02, 0.95)
    eic_barrel(2.2, 13.6, 0, 1.0, lying=True)
    for cx, cy in ((6.5, 15.5), (7.3, 16.6)):
        for k in range(5):
            add("torus", (cx, cy, 0.06 + k * 0.1), (1, 1, 1), m=rope, major_radius=0.55, minor_radius=0.05, major_segments=20, minor_segments=5)
    add("cube", (-30, 2, 3.5), (5, 14, 3.5), m=brick)                          # storehouse
    eic_gable(-30, 2, 7.0, 14, 5, 4, roof, brick, rz=math.radians(90), over=0.4)
    for k in range(4):
        add("cube", (-24.95, -8 + k * 6, 1.4), (0.05, 1.2, 1.4), m=eic_col("barndoor", "#3A2A1C", 0.8))
    add("cube", (-30, 30, 3), (5, 6, 3), m=brick)
    eic_gable(-30, 30, 6.0, 6, 5, 3.2, roof, brick, rz=math.radians(90), over=0.4)
    eic_ship_frame(-35, 52, math.radians(8), wood)
    eic_aerial(40, 600, 0.8)
    camera_path([(0.0, (-3, -12, 2.6)), (1.0, (-0.8, -10, 2.6))], lens=28, target_keys=[(0.0, (6, 34, 6.5)), (1.0, (8, 34, 6.6))])
    return sc


def eic_shot_ajmer_court():
    """Jahangir's darbar at Ajmer, 1616 (Roe): red sandstone with white-marble geometric inlay, trabeate pillared halls,
    the jharokha above, a gilt inner rail round a carpeted platform under velvet canopies, red qanats."""
    sc = eic_begin()
    eic_sky("citrus_orchard_puresky", 0.75, sun_az=235)
    eic_sun(235, 3.4, (1, 0.88, 0.7), lo=34, hi=48)
    exposure(-0.4)
    red = eic_ph("redstone", "red_sandstone_wall", 0.35, tint=(1.0, 0.8, 0.68), fallback=(0.6, 0.3, 0.2))
    red2 = eic_ph("redstone2", "red_sandstone_tiles", 0.5, tint=(1.0, 0.8, 0.7), fallback=(0.6, 0.32, 0.22))
    pave = eic_ph("redpave", "red_sandstone_pavement", 0.22, tint=(1.0, 0.85, 0.75), fallback=(0.6, 0.35, 0.25))
    marble = eic_ph("marble", "marble_01", 0.6, tint=(1.0, 0.98, 0.95), fallback=(0.9, 0.88, 0.84))
    gold = eic_gold()
    inlay = eic_pmat("inlay", lambda: eic_pat_inlay(), rough=0.3, alpha=True, uv_scale=(2, 2))
    inlay_b = eic_pmat("inlayband", lambda: eic_pat_inlay(cell=0.5), rough=0.3, alpha=True, uv_scale=(12, 1))
    velvet = eic_pmat("velvet_c", lambda: eic_pat_brocade(base="#9E1B32", c1="#C9A13C", c2="#1F7A52"), rough=0.6, sheen=0.7)
    val = eic_pmat("valance", lambda: eic_pat_valance(), rough=0.6, sheen=0.5, alpha=True)
    broc = eic_pmat("brocade", lambda: eic_pat_brocade(), rough=0.35, metal=0.4, sheen=0.4)
    qanat = eic_pmat("qanat", lambda: eic_pat_qanat(), rough=0.85, sheen=0.3)
    marbleband = eic_col("marbleband", "#EFE9DE", 0.35)
    add("plane", (0, 0, 0), (120, 120, 1), m=pave)
    add("cube", (0, 25.0, 6.5), (28, 1.0, 6.5), m=red)                         # palace wall
    add("cube", (0, 23.9, 0.4), (28, 0.2, 0.4), m=red2)
    for k in range(36):
        add("cube", (-27.3 + k * 1.56, 24.4, 13.4), (0.5, 0.5, 0.45), m=red2)
    add("cube", (0, 23.6, 11.6), (28, 0.9, 0.08), (math.radians(-12), 0, 0), m=red2)
    for k in range(29):
        add("cube", (-28 + k * 2, 24.1, 11.1), (0.12, 0.45, 0.35), m=red2)
    add("plane", (0, 23.98, 12.4), (26, 0.5, 1), (math.radians(90), 0, 0), m=inlay_b)
    add("plane", (0, 23.98, 0.95), (26, 0.12, 1), (math.radians(90), 0, 0), m=marbleband)
    for cx in (-21.5, -15.5, -9.5, 9.5, 15.5, 21.5):                           # blind arched niches with inlay
        eic_arch_bay(cx, 23.82, 1.6, 3.6, 1.5, 6.4, 0.36, red2)
        for sg in (-1, 1):
            add("cube", (cx + sg * 1.78, 23.82, 3.3), (0.18, 0.18, 3.1), m=red2)
        add("plane", (cx, 23.99, 2.6), (1.5, 1.8, 1), (math.radians(90), 0, 0), m=inlay)
        eic_arch_bay(cx, 23.82, 1.1, 8.6, 0.9, 10.2, 0.3, red2)
        for sg in (-1, 1):
            add("cube", (cx + sg * 1.25, 23.82, 8.3), (0.15, 0.15, 1.6), m=red2)
        add("plane", (cx, 23.99, 7.7), (1.05, 0.8, 1), (math.radians(90), 0, 0), m=inlay)
        add("plane", (cx, 23.99, 3.62), (1.6, 0.04, 1), (math.radians(90), 0, 0), m=marbleband)
    for cx in (-4.6, 4.6):
        add("plane", (cx, 23.98, 5.2), (1.4, 3.6, 1), (math.radians(90), 0, 0), m=inlay)
    jy = 22.7                                                                   # jharokha
    add("cube", (0, jy, 5.0), (3.0, 1.3, 0.16), m=red2)
    for bx in (-2.4, -0.8, 0.8, 2.4):
        for dy, dz, hy in ((0.0, -0.32, 1.1), (0.4, -0.64, 0.75), (0.75, -0.96, 0.4)):
            add("cube", (bx, jy + dy + 0.15, 5.0 + dz), (0.16, hy, 0.16), m=red2)
    for px in (-2.6, -0.9, 0.9, 2.6):
        add("cyl", (px, jy - 1.05, 6.4), (0.12, 0.12, 1.25), m=marble, vertices=12)
        add("cube", (px, jy - 1.05, 7.7), (0.22, 0.22, 0.08), m=gold)
    add("cube", (0, jy - 1.15, 5.55), (2.9, 0.06, 0.4), m=marble)
    add("plane", (0, jy - 1.2, 5.55), (2.85, 0.38, 1), (math.radians(90), 0, 0), m=inlay)
    add("cube", (0, jy, 7.8), (3.0, 1.3, 0.1), m=red2)
    eic_chala(0, jy - 0.1, 7.9, 3.0, 1.45, 1.0, gold, droop=0.45, bulge=0.2)
    add("cone", (0, jy - 0.1, 9.3), (0.12, 0.12, 0.45), m=gold, vertices=10)
    add("plane", (0, 23.97, 6.4), (2.9, 1.4, 1), (math.radians(90), 0, 0), m=broc)
    for sg in (-1, 1):
        eic_cloth((sg * 2.15, jy - 0.85, 6.55), 0.9, 2.1, broc, folds=4, amp=0.05)
    eic_rod((-2.3, 23.5, 5.55), (2.3, 23.5, 5.55), 0.28, velvet, 12)
    for sx in (-1, 1):                                                          # rooftop chhatris
        eic_chhatri(sx * 21, 24.6, 13.0, 1.6, red2, marble)
        eic_chhatri(sx * 8, 24.6, 13.0, 1.1, red2, marble)
    add("cube", (0, 13.5, 0.36), (11.2, 5.6, 0.36), m=red2)                    # raised platform
    add("plane", (0, 7.88, 0.36), (11.2, 0.34, 1), (math.radians(90), 0, 0), m=inlay_b)
    eic_carpet(-5.3, 13.6, 6.6, 10.4, "pictorial", seed=4, z=0.735)
    eic_carpet(5.3, 13.6, 6.6, 10.4, "pictorial", seed=9, z=0.735)
    bal = eic_proto([add("cyl", (0, 0, 0.45), (0.04, 0.04, 0.45), m=gold, vertices=8),
                     add("sphere", (0, 0, 0.93), (0.07, 0.07, 0.08), m=gold, segments=8, ring_count=5)], "baluster")
    z = 0.72
    for a, b in (((-11, 8.1, z), (-1.0, 8.1, z)), ((1.0, 8.1, z), (11, 8.1, z)), ((-11, 8.1, z), (-11, 18.8, z)), ((11, 8.1, z), (11, 18.8, z))):
        eic_baluster_row(a, b, 0.42, bal)
        eic_rod((a[0], a[1], z + 0.92), (b[0], b[1], z + 0.92), 0.045, gold, 8)
    lac = eic_col("lacquer", "#8E2A1E", 0.35)
    balr = eic_proto([add("cyl", (0, 0, 0.5), (0.05, 0.05, 0.5), m=lac, vertices=8)], "baluster_red")
    for a, b in (((-14, 4.2, 0), (-2.0, 4.2, 0)), ((2.0, 4.2, 0), (14, 4.2, 0))):
        eic_baluster_row(a, b, 0.6, balr)
        eic_rod((a[0], a[1], 1.0), (b[0], b[1], 1.0), 0.05, lac, 8)
    for cx in (-6.2, 6.2):
        eic_canopy(cx, 14.0, 4.1, 4.6, 4.2, velvet, val, gold, drop=0.55)
    cols = ("#E3A23B", "#8DB255", "#A8233A", "#E7B9B0")
    for sg in (-1, 1):                                                          # pillared halls either side
        add("cube", (sg * 19.5, 11.5, 0.3), (5.0, 12.5, 0.3), m=red2)
        for k in range(8):
            yy = -0.5 + k * 3.4
            eic_pillar(sg * 15.5, yy, 0.6, 5.2, red)
            eic_pillar(sg * 20.0, yy, 0.6, 5.2, red)
        add("cube", (sg * 19.4, 11.5, 6.05), (5.4, 12.6, 0.25), m=red2)
        add("cube", (sg * 14.4, 11.5, 5.75), (0.9, 12.6, 0.07), (0, sg * math.radians(-14), 0), m=red2)
        for k in range(16):
            add("cube", (sg * 14.9, -0.8 + k * 1.6, 6.6), (0.25, 0.5, 0.35), m=red2)
        add("cube", (sg * 24.2, 11.5, 3.5), (0.3, 12.6, 3.5), m=red)
        eic_cloth((sg * 23.85, 11.5, 2.4), 24, 3.4, qanat, rot=(math.radians(90), 0, math.radians(90)), folds=20, amp=0.06, nu=80)
        for k in range(7):
            yy = -0.5 + (k + 0.5) * 3.4
            add("cyl", (sg * 15.3, yy, 5.45), (0.14, 0.14, 1.45), (math.radians(90), 0, 0), m=eic_col("silk" + str(k % 4), cols[k % 4], 0.45),
                vertices=10)
        add("plane", (sg * 14.95, 11.5, 0.3), (12.5, 0.3, 1), (math.radians(90), 0, math.radians(90)), m=inlay_b)
        eic_cloth((sg * 19.5, 23.6, 1.6), 9.0, 3.2, qanat, folds=8, amp=0.05, nu=50)
    eic_carpet(0.8, -2.0, 7.0, 10.5, "medallion", seed=11)
    eic_aerial(60, 900, 0.5)
    camera_path([(0.0, (1.5, -13, 2.5)), (1.0, (0.3, -10.8, 2.5))], lens=26, target_keys=[(0.0, (0, 22, 5.0)), (1.0, (0, 22, 5.1))])
    return sc


def eic_balcony(xf, y, z, w, sg, teak, jali):
    """Carved teak balcony projecting from a facade at x=xf towards sg (+1/-1)."""
    out = 1.0
    add("cube", (xf + sg * out / 2, y, z), (out / 2 + 0.05, w / 2, 0.1), m=teak)
    for by in (-w / 2 + 0.3, 0, w / 2 - 0.3):
        for dx, dz, hx in ((0.05, -0.25, 0.45), (0.0, -0.5, 0.3), (-0.05, -0.75, 0.15)):
            add("cube", (xf + sg * (hx + dx), y + by, z + dz), (hx, 0.09, 0.12), m=teak)
    add("cube", (xf + sg * (out + 0.02), y, z + 0.5), (0.05, w / 2, 0.42), m=teak)
    add("plane", (xf + sg * (out + 0.08), y, z + 0.5), (w / 2 - 0.1, 0.35, 1), (math.radians(90), 0, math.radians(90)), m=jali)
    for sy in (-1, -0.33, 0.33, 1):
        add("cyl", (xf + sg * out, y + sy * (w / 2 - 0.08), z + 1.15), (0.06, 0.06, 1.05), m=teak, vertices=8)
    add("cube", (xf + sg * (out / 2 + 0.15), y, z + 2.3), (out / 2 + 0.35, w / 2 + 0.2, 0.06), (0, sg * math.radians(-12), 0), m=teak)
    add("cube", (xf + sg * 0.02, y, z + 1.1), (0.04, w / 2 - 0.3, 1.0), m=eic_col("darkdoor", "#16110D", 0.9))


def eic_shot_surat():
    sc = eic_begin()
    eic_sky("evening_road_01_puresky", 0.8, sun_az=25)
    eic_sun(25, 3.3, (1, 0.86, 0.66), lo=28, hi=45)
    exposure(-0.35)
    rng = random.Random(8)
    plaster = eic_ph("limeplaster", "white_plaster_rough_02", 0.3, tint=(0.95, 0.87, 0.74), fallback=(0.85, 0.78, 0.66))
    brick = eic_ph("suratbrick", "red_brick_03", 0.5, tint=(0.9, 0.72, 0.6), fallback=(0.5, 0.3, 0.2))
    teak = eic_ph("teak", "dark_wood", 1.0, tint=(0.85, 0.62, 0.42), fallback=(0.3, 0.2, 0.12))
    floor = eic_ph("courtfloor", "brick_floor", 0.3, tint=(0.95, 0.82, 0.7), fallback=(0.55, 0.38, 0.28))
    jali = eic_pmat("jali_teak", lambda: eic_pat_inlay(cell=0.33, line="#5A3A22", fill="#3A2416", t=0.05), rough=0.6, alpha=True, uv_scale=(4, 1))
    stone = eic_ph("castlestone", "old_stone_wall", 0.2, tint=(0.95, 0.88, 0.75), fallback=(0.6, 0.55, 0.45))
    dark = eic_col("darkdoor", "#16110D", 0.9)
    W_ = -1.2
    eic_poly_ground([(-200, -60), (200, -60), (200, 30), (-200, 30)], 0.0, floor)
    eic_water((0, 200, W_), (400, 175), "#5E6A5A", rough=0.06, wave=0.14, scale=0.35)
    eic_poly_ground([(-500, 360), (500, 360), (500, 900), (-500, 900)], -0.6, eic_ph("farbank", "dry_ground_01", 0.05, tint=(0.8, 0.75, 0.55)), name="far")
    for k in range(6):
        add("cube", (0, 30.3 + k * 0.5, -0.1 - k * 0.2), (40, 0.25, 0.1), m=stone)
    for sg in (-1, 1):                                                          # the two house wings
        xf = sg * 9.0
        add("cube", (sg * 13.5, 1.5, 6.0), (4.5, 15.5, 6.0), m=plaster)
        add("cube", (sg * 13.5, 1.5, 1.2), (4.55, 15.55, 1.2), m=brick)
        add("cube", (xf + sg * 0.15, 1.5, 12.0), (0.25, 15.6, 0.15), m=teak)
        for k in range(14):
            add("cube", (xf + sg * 0.05, -13.5 + k * 2.2, 12.5), (0.25, 0.6, 0.35), m=plaster)
        for k in range(7):
            yy = -11 + k * 4
            add("cube", (xf - sg * 0.01, yy, 1.45), (0.04, 1.2, 1.45), m=dark)
            add("cube", (xf + sg * 0.06, yy, 3.0), (0.08, 1.5, 0.12), m=teak)
            for dy in (-1.3, 1.3):
                add("cube", (xf + sg * 0.06, yy + dy, 1.45), (0.08, 0.1, 1.45), m=teak)
        add("cube", (xf + sg * 0.1, 1.5, 3.6), (0.12, 15.6, 0.1), m=teak)
        add("cube", (xf + sg * 0.1, 1.5, 7.2), (0.12, 15.6, 0.1), m=teak)
        for fl, ys in ((1, (-9, -1, 7, 13)), (2, (-12, -5, 3, 10))):
            z = 3.6 * fl + 0.25
            for yy in ys:
                eic_balcony(xf, yy, z, 2.6, sg, teak, jali)
            for yy in [v for v in range(-13, 16, 3) if all(abs(v - q) > 2.2 for q in ys)]:
                add("cube", (xf + sg * 0.02, yy, z + 1.2), (0.05, 0.5, 0.75), m=dark)
                add("cube", (xf + sg * 0.08, yy, z + 1.2), (0.04, 0.6, 0.85), m=teak)
    add("cube", (0, 17.3, 0.12), (9, 0.6, 0.12), m=brick)                      # back arcade towards the river
    eic_arcade(-9, 17.2, 5, 3.6, 3.0, 1.6, 5.6, 0.9, 0.85, plaster, p=1.1, q=0.6)
    add("cube", (0, 17.2, 5.75), (9.2, 0.6, 0.15), m=teak)
    for k in range(10):
        add("cube", (-8.6 + k * 1.92, 17.2, 6.2), (0.35, 0.4, 0.3), m=plaster)
    eic_boat(-14, 75, math.radians(5), "dhow", z=W_, seed=1)
    eic_boat(22, 125, math.radians(-12), "dhow", s=0.9, z=W_, seed=2)
    eic_boat(5, 42, math.radians(3), "lighter", z=W_, seed=3)
    eic_boat(-28, 50, math.radians(-8), "country", sail=False, z=W_, seed=4)
    eic_boat(36, 60, math.radians(170), "dhow", s=0.8, z=W_, seed=5)
    eic_ship(-55, 210, math.radians(15), 0.6, "1600", "furled", z=W_)
    cxs, cys = 16, 80                                                           # Surat Castle
    add("cube", (cxs, cys, 8), (12, 10, 8), m=stone)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("cyl", (cxs + sx * 12, cys + sy * 10, 9.5), (4.2, 4.2, 9.5), m=stone, vertices=20)
            for k in range(10):
                a = k * 2 * math.pi / 10
                add("cube", (cxs + sx * 12 + math.cos(a) * 4.0, cys + sy * 10 + math.sin(a) * 4.0, 19.4), (0.6, 0.6, 0.45), (0, 0, a), m=stone)
    for k in range(10):
        add("cube", (cxs - 11 + k * 2.4, cys - 10.1, 16.4), (0.6, 0.4, 0.45), m=stone)
    palms = [eic_palm_proto(s, h=10) for s in (5, 6)]
    for k in range(30):
        eic_inst(palms[k % 2], rng.uniform(-300, 300), rng.uniform(380, 520), -0.6, rng.uniform(0, 6), rng.uniform(0.9, 1.3))
    tree = eic_tree_proto(7, h=7, crown=3.4, leaf=eic_leaf_mat("neem", "#2A4A22", "#6A8E3A", 7))
    eic_inst(tree, 6.6, 12.8, 0, 0.5, 1.0)
    eic_inst(tree, -40, 34, 0, 1.0, 1.4)
    calico = eic_ph("calico", "rough_linen", 2.0, tint=(1.0, 0.96, 0.88), fallback=(0.9, 0.86, 0.78))
    cord = eic_col("cord", "#5A4630", 0.8)
    for i in range(4):                                                          # calico bales
        for j in range(2):
            for k in range(3 - j):
                if k >= 2 and i % 2:
                    continue
                bx, by, bz = -7.6 + j * 1.2, 1.0 + i * 1.6, 0.3 + k * 0.62
                add("cube", (bx, by, bz), (0.55, 0.75, 0.3), (0, 0, rng.uniform(-0.05, 0.05)), m=calico)
                for dy in (-0.35, 0.35):
                    add("cube", (bx, by + dy, bz), (0.57, 0.03, 0.31), m=cord)
    mat_ = eic_ph("drymat", "reed_roof_04", 0.6, tint=(1.0, 0.9, 0.7), fallback=(0.7, 0.6, 0.4))
    indigo = eic_col("indigo", "#202A55", 0.8)
    add("plane", (-3.8, 11.0, 0.02), (1.3, 1.0, 1), (0, 0, 0.15), m=mat_)
    for k in range(46):
        add("cube", (-3.8 + rng.uniform(-1.1, 1.1), 11.0 + rng.uniform(-0.85, 0.85), 0.09), (0.08, 0.08, 0.07), (0, 0, rng.uniform(0, 1.5)), m=indigo)
    for bx, by in ((-2.0, 12.4), (-1.3, 11.6), (-5.6, 12.6)):
        eic_basket(bx, by, 0.0, 0.38, 0.34, indigo)
    eic_chest(-6.2, 13.0, 0, 0.2)
    eic_chest(-5.9, 14.1, 0, -0.1)
    pole = eic_col("pole", "#5A4630", 0.7)
    for a in (0, 2.1, 4.2):                                                     # the great scale
        eic_rod((-1.0 + math.cos(a) * 1.2, 14.6 + math.sin(a) * 1.2, 0), (-1.0, 14.6, 2.8), 0.05, pole, 6)
    eic_rod((-1.8, 14.6, 2.4), (-0.2, 14.6, 2.4), 0.04, teak, 6)
    for sx in (-1.8, -0.2):
        eic_rod((sx, 14.6, 2.4), (sx, 14.6, 1.3), 0.01, cord, 4)
        add("cyl", (sx, 14.6, 1.28), (0.28, 0.28, 0.03), m=eic_col("brass", "#B08A3A", 0.3, 1.0), vertices=16)
    jar = eic_col("waterjar", "#8A4A2A", 0.6)
    for jx, jy in ((7.4, 8.0), (7.6, 9.0), (6.9, 8.6)):
        o = add("sphere", (jx, jy, 0.45), (0.35, 0.35, 0.45), m=jar, segments=14, ring_count=8)
        smooth(o)
    eic_aerial(40, 600, 0.7)
    camera_path([(0.0, (1.4, -12, 1.9)), (1.0, (0.2, -10, 1.9))], lens=24, target_keys=[(0.0, (0, 40, 3.4)), (1.0, (0, 40, 3.4))])
    return sc


def eic_shot_calcutta():
    sc = eic_begin()
    eic_sky("wasteland_clouds_puresky", 0.8, sun_az=192)
    eic_sun(192, 3.4, (1, 0.82, 0.6), lo=16, hi=26)
    exposure(-0.35)
    rng = random.Random(56)
    strand = eic_ph("strand", "dry_ground_01", 0.22, tint=(0.88, 0.78, 0.62), fallback=(0.5, 0.42, 0.3))
    brick = eic_ph("fortbrick", "medieval_red_brick", 0.45, tint=(0.92, 0.72, 0.6), fallback=(0.45, 0.22, 0.15))
    chunam = eic_ph("chunam", "white_stucco", 0.4, tint=(1.0, 0.96, 0.88), fallback=(0.9, 0.88, 0.82))
    worn = eic_ph("wornplaster", "rough_plaster_brick", 0.35, tint=(1.0, 0.93, 0.82), fallback=(0.8, 0.72, 0.6))
    green = eic_col("shutter", "#2E5A3A", 0.6)
    dark = eic_col("darkdoor", "#16110D", 0.9)
    G = 1.4
    eic_poly_ground([(-5, -80), (500, -80), (500, 700), (-20, 700), (-12, 300), (-5, 160)], G, strand)
    eic_water((-200, 300, 0.0), (300, 500), "#6E6448", rough=0.07, wave=0.15, scale=0.3)
    eic_poly_ground([(-1500, -80), (-430, -80), (-440, 700), (-1500, 700)], 0.8, eic_ph("farbank2", "leafy_grass", 0.03, tint=(0.7, 0.8, 0.5)),
                    name="howrah")
    fx0, fx1, fy0, fy1 = -3.0, 66.0, 46.0, 150.0                               # Old Fort William
    add("cube", (3.5, (fy0 + fy1) / 2, G + 4.6), (6.0, 45.0, 4.6), m=worn)
    add("cube", (3.5, (fy0 + fy1) / 2, G + 9.3), (6.15, 45.15, 0.12), m=chunam)
    add("cube", (3.5, (fy0 + fy1) / 2, G + 9.75), (6.0, 45.0, 0.4), m=chunam)
    eic_arcade(-3.2, 53.0, 12, 7.5, 2.8, 1.5, 4.6, 0.7, 1.6, chunam, rz=math.radians(90), z0=G, p=2, q=0.5)
    add("cube", (-3.4, 98, G + 4.75), (0.5, 45.0, 0.15), m=chunam)
    for k in range(30):
        add("cube", (-2.55, 52.5 + k * 3.0, G + 6.8), (0.05, 0.55, 0.9), m=green)
    for wy in (fy0, fy1):
        add("cube", ((fx0 + fx1) / 2 + 6, wy, G + 3.2), ((fx1 - fx0) / 2 - 6, 1.1, 3.2), m=brick)
        for k in range(24):
            add("cube", (fx0 + 10 + k * 2.4, wy, G + 6.8), (0.6, 1.0, 0.4), m=brick)
    add("cube", (fx1, (fy0 + fy1) / 2, G + 3.2), (1.1, (fy1 - fy0) / 2, 3.2), m=brick)
    eic_arch_bay(30, fy0 - 0.2, 1.8, 2.8, 1.6, 6.2, 2.6, chunam).location.z = G
    add("cube", (30, fy0 - 0.2, G + 1.4), (1.85, 0.4, 1.4), m=dark)
    gun = eic_col("gun", "#202020", 0.4, 0.6)
    for bx, by in ((fx0, fy0), (fx0, fy1), (fx1, fy0), (fx1, fy1)):
        add("cube", (bx, by, G + 3.8), (7.0, 7.0, 3.8), (0, 0, math.radians(45)), m=brick)
        add("cube", (bx, by, G + 7.8), (7.3, 7.3, 0.2), (0, 0, math.radians(45)), m=brick)
        for k in range(4):
            a = math.radians(45) + k * math.pi / 2
            add("cube", (bx + math.cos(a) * 6.6, by + math.sin(a) * 6.6, G + 8.4), (1.6, 0.6, 0.5), (0, 0, a + math.pi / 2), m=brick)
            eic_rod((bx + math.cos(a + 0.5) * 6.0, by + math.sin(a + 0.5) * 6.0, G + 8.1), (bx + math.cos(a + 0.5) * 8.6, by + math.sin(a + 0.5) * 8.6, G + 8.2),
                    0.18, gun, 8)
    add("cube", (33, 103, G + 6.8), (12, 7, 6.8), m=chunam)                    # Governor's house
    add("cube", (33, 103, G + 13.9), (12.2, 7.2, 0.35), m=chunam)
    for k in range(9):
        add("cyl", (22.5 + k * 2.6, 95.2, G + 4.5), (0.3, 0.3, 4.5), m=chunam, vertices=12)
        add("cube", (22.5 + k * 2.6, 95.9, G + 10.5), (0.45, 0.04, 0.9), m=green)
    add("cube", (33, 95.0, G + 9.1), (12, 0.6, 0.15), m=chunam)
    pole = eic_col("flagpole", "#3A2E22", 0.6)
    eic_rod((-4.2, 98, G), (-4.2, 98, G + 26), 0.18, pole, 8, 0.1)
    eic_rod((-4.2, 96, G + 22), (-4.2, 100, G + 22), 0.06, pole)
    eic_flag(-4.2, 98, G + 21.0, 7.0, 3.6, "union1707", ripple=0.12)
    add("cube", (-4.2, 98, G + 0.5), (1.2, 1.2, 0.5), m=chunam)
    add("cube", (44, 172, G + 4.5), (11, 5.5, 4.5), m=chunam)                  # St Anne's Church
    eic_gable(44, 172, G + 9, 11, 5.5, 3.5, eic_col("roofgrey", "#7A7468", 0.7), chunam)
    add("cube", (30, 172, G + 9), (3.2, 3.2, 9), m=chunam)
    add("cone", (30, 172, G + 18 + 7), (2.6, 2.6, 7), m=eic_col("spire", "#6E6A62", 0.5), vertices=8)
    for hx, hy, w, d, h in ((24, 10, 13, 10, 8.5), (40, 30, 12, 11, 9.5), (58, 8, 14, 10, 8.0), (78, 30, 12, 10, 7.5), (21, 32, 9, 8, 7.0)):
        eic_chunam_house(hx, hy, w, d, h, 0.0, chunam if rng.random() < 0.6 else worn, green, z=G)
    for hx, hy in ((95, 8), (102, 22), (88, 44), (110, 40), (70, -8)):
        eic_hut(hx, hy, rng.uniform(-0.3, 0.3), z=G)
    palms = [eic_palm_proto(s, h=rng.uniform(9, 12)) for s in (11, 12, 13)]
    for px, py in ((17, -2), (31, 20), (50, 18), (66, 22), (36, 44), (15, 40), (85, 15), (60, -4), (97, 32), (49, 42), (72, 44)):
        eic_inst(palms[rng.randrange(3)], px, py, G, rng.uniform(0, 6), rng.uniform(0.9, 1.2))
    tree = eic_tree_proto(17, h=9, crown=6, leaf=eic_leaf_mat("banyan", "#1E3A1E", "#4E7232", 4))
    eic_inst(tree, 13, 26, G, 0.3, 1.2)
    eic_inst(tree, 75, 60, G, 1.3, 1.3)
    for k in range(60):
        eic_inst(palms[k % 3], rng.uniform(-900, -450), rng.uniform(-50, 600), 0.8, rng.uniform(0, 6), rng.uniform(0.9, 1.3))
    for k in range(14):
        eic_inst(tree, rng.uniform(-900, -460), rng.uniform(0, 600), 0.8, rng.uniform(0, 6), rng.uniform(0.8, 1.2))
    bale = eic_bale_mat()
    for k in range(8):
        add("cube", (-1.4 + (k % 4) * 1.15, 40 + (k // 4) * 1.6, G + 0.32), (0.5, 0.7, 0.32), (0, 0, rng.uniform(-0.1, 0.1)), m=bale)
    for bx, by in ((1.6, 43.5), (2.4, 42.6), (2.0, 44.6)):
        eic_barrel(bx, by, G, 0.9)
    eic_boat(-14, 22, math.radians(100), "budgerow", sail=False)
    eic_boat(-30, 48, math.radians(80), "country", seed=2)
    eic_boat(-50, 100, math.radians(95), "country", seed=3)
    eic_boat(-9, 66, math.radians(92), "lighter", seed=4)
    eic_boat(-22, 140, math.radians(85), "country", sail=False, seed=5)
    eic_ship(-95, 110, math.radians(86), 1.0, "1750", "furled")
    eic_ship(-170, 230, math.radians(80), 0.95, "1750", "furled")
    eic_aerial(45, 650, 0.8)
    camera_path([(0.0, (8, -12, G + 1.65)), (1.0, (10, -9.5, G + 1.65))], lens=30, target_keys=[(0.0, (-4, 70, 6.5)), (1.0, (-2, 72, 6.6))])
    return sc


def eic_shot_murshidabad():
    sc = eic_begin()
    eic_sky("rocky_ridge_puresky", 0.8, sun_az=325)
    eic_sun(325, 3.2, (1, 0.84, 0.62), lo=20, hi=32)
    exposure(-0.35)
    rng = random.Random(33)
    lime = eic_ph("lime", "white_stucco", 0.35, tint=(1.0, 0.95, 0.86), fallback=(0.9, 0.88, 0.8))
    ochre = eic_ph("ochreplaster", "yellow_plaster", 0.3, tint=(1.0, 0.93, 0.8), fallback=(0.82, 0.7, 0.48))
    floor = eic_ph("courtstone", "stone_tiles_02", 0.3, tint=(0.95, 0.88, 0.78), fallback=(0.7, 0.65, 0.55))
    brick = eic_ph("ghatbrick", "red_brick_03", 0.5, tint=(0.92, 0.72, 0.6), fallback=(0.5, 0.3, 0.2))
    gold = eic_gold()
    chandni = eic_ph("chandni", "rough_linen", 1.5, tint=(1.0, 0.99, 0.96), fallback=(0.95, 0.94, 0.9))
    broc = eic_pmat("brocade_red", lambda: eic_pat_brocade(base="#A8233A", c1="#D1A63E", c2="#1F7A52"), rough=0.4, sheen=0.5)
    stripes = eic_pmat("shamiana", lambda: eic_pat_stripes(cols=("#A8233A", "#D1A63E", "#A8233A", "#F1ECE0")), rough=0.8, translucent=0.3)
    val = eic_pmat("valance", lambda: eic_pat_valance(), rough=0.6, sheen=0.5, alpha=True)
    dark = eic_col("darkdoor", "#16110D", 0.9)
    eic_poly_ground([(-200, -60), (10, -60), (10, 200), (-200, 200)], 0.0, floor)
    eic_poly_ground([(10, -60), (14, -60), (14, 200), (10, 200)], -0.4, brick, name="ghat")
    eic_water((200, 100, -2.5), (190, 300), "#5E5A42", rough=0.06, wave=0.14, scale=0.3)
    eic_poly_ground([(390, -300), (900, -300), (900, 600), (390, 600)], -1.8, eic_ph("farbank2", "leafy_grass", 0.03, tint=(0.7, 0.8, 0.5)), name="far")
    add("cube", (10.3, 5, 0.45), (0.3, 30, 0.45), m=lime)
    for k in range(38):
        add("cube", (10.3, -24 + k * 1.6, 1.05), (0.32, 0.3, 0.18), m=lime)
    for k in range(8):
        add("cube", (12 + k * 0.6, 1.5, -0.35 - k * 0.28), (0.3, 3.0, 0.14), m=brick)
    kw = dict(p=1.1, q=0.62, lobes=7, depth=0.16)                               # left wing: multifoil arcades
    eic_arcade(-14, -12, 9, 3.6, 2.6, 1.6, 4.7, 0.7, 0.75, lime, rz=math.radians(90), **kw)
    add("cube", (-17.8, 4.2, 4.5), (0.3, 16.5, 4.5), m=ochre)
    for k in range(9):
        add("cube", (-17.45, -10.2 + k * 3.6, 1.3), (0.06, 0.6, 1.3), m=dark)
    add("cube", (-15.9, 4.2, 4.85), (2.2, 16.6, 0.16), m=lime)
    add("cube", (-13.55, 4.2, 4.85), (0.2, 16.6, 0.25), m=lime)
    eic_arcade(-14, -12, 9, 3.6, 2.0, 1.2, 3.6, 0.5, 0.7, lime, rz=math.radians(90), z0=5.0, **kw)
    add("cube", (-15.9, 4.2, 8.75), (2.2, 16.6, 0.15), m=lime)
    for k in range(21):
        add("cube", (-14.0, -12 + k * 1.62, 9.2), (0.25, 0.35, 0.32), m=lime)
    for cy in (-12, 20.4):
        eic_chhatri(-15.2, cy, 8.9, 1.2, lime, lime, gold)
    add("cube", (-2, 25.5, 0.6), (10.2, 4.6, 0.6), m=lime)                     # audience pavilion
    for k in range(3):
        add("cube", (-2, 20.4 - k * 0.45, (3 - k) * 0.2), (4, 0.3, (3 - k) * 0.2), m=lime)
    eic_arcade(-11.0, 21.6, 5, 3.6, 3.0, 1.9, 5.4, 0.6, 0.55, lime, z0=1.2, p=1.1, q=0.62, lobes=9, depth=0.2)
    for k in range(6):
        for dx in (-0.22, 0.22):
            add("cyl", (-11.0 + k * 3.6 + dx, 21.2, 1.2 + 1.6), (0.1, 0.1, 1.6), m=lime, vertices=12)
    add("cube", (-2, 25.5, 6.75), (10.4, 4.7, 0.18), m=lime)
    add("cube", (-2, 21.3, 6.6), (10.6, 0.5, 0.1), (math.radians(14), 0, 0), m=lime)
    for k in range(27):
        add("cube", (-12.2 + k * 0.79, 21.5, 7.2), (0.2, 0.25, 0.28), m=lime)
    for cx in (-11.0, 7.0):
        eic_chhatri(cx, 22.0, 6.9, 1.0, lime, lime, gold)
    add("cube", (-2, 30.0, 3.5), (10.2, 0.3, 3.5), m=ochre)
    for k in range(5):
        eic_arch_bay(-9.2 + k * 3.6, 29.6, 1.2, 1.8, 1.2, 4.6, 0.3, lime, lobes=7, depth=0.12).location.z = 1.2
    eic_carpet(-2, 25.6, 7.2, 17.2, "medallion", seed=21, z=1.215, rz=math.radians(90), field="#7E1F2E")
    add("plane", (-2, 26.6, 1.24), (4.0, 2.2, 1), m=chandni)                   # masnad: chandni, bolster, cushions
    add("cube", (-2, 27.0, 1.32), (3.6, 1.6, 0.08), m=chandni)
    eic_rod((-5.2, 28.2, 1.75), (1.2, 28.2, 1.75), 0.38, broc, 14)
    for sx in (-5.0, 1.0):
        add("sphere", (sx, 27.3, 1.62), (0.35, 0.5, 0.25), m=broc, segments=12, ring_count=8)
    bidri = eic_col("bidri", "#2A2A2C", 0.35, 0.5)
    hx, hy = 1.9, 25.4
    o = add("sphere", (hx, hy, 1.42), (0.22, 0.22, 0.2), m=bidri, segments=16, ring_count=10)
    smooth(o)
    eic_rod((hx, hy, 1.6), (hx, hy, 2.15), 0.03, eic_col("silver", "#C5C6C2", 0.3, 1.0))
    add("cone", (hx, hy, 2.25), (0.1, 0.1, 0.1), m=eic_col("clay", "#7A3A22", 0.7), vertices=10)
    eic_tube("pipe", [(hx, hy, 1.9), (hx - 0.6, hy - 0.1, 1.3), (hx - 1.2, hy + 0.4, 1.28), (hx - 1.6, hy + 1.0, 1.35)], 0.025,
             eic_col("pipe", "#7A2A2A", 0.6), 6)
    eic_canopy(-2.0, 18.0, 4.4, 8.0, 4.6, stripes, val, gold, drop=0.5)
    add("cube", (-6.5, 5.5, 0.25), (2.8, 4.2, 0.25), m=lime)                   # tank
    eic_water((-6.5, 5.5, 0.4), (2.5, 3.9), "#3E5A5A", name="tank", rough=0.02, wave=0.05)
    for sx in (-1, 1):                                                          # Bengal-roofed pavilion
        for sy in (-1, 1):
            add("cube", (6.8 + sx * 1.9, 22.0 + sy * 1.9, 1.6), (0.25, 0.25, 1.6), m=lime)
    add("cube", (6.8, 22.0, 3.3), (2.3, 2.3, 0.15), m=lime)
    eic_chala(6.8, 22.0, 3.4, 2.4, 2.2, 1.6, ochre, droop=0.5, bulge=0.3)
    palms = [eic_palm_proto(s, h=11) for s in (31, 32)]
    for k in range(40):
        eic_inst(palms[k % 2], rng.uniform(400, 700), rng.uniform(-100, 400), -1.8, rng.uniform(0, 6), rng.uniform(0.9, 1.3))
    tree = eic_tree_proto(37, h=8, crown=5, leaf=eic_leaf_mat("mango", "#16301A", "#3F6B2C", 5.0))
    for k in range(12):
        eic_inst(tree, rng.uniform(400, 700), rng.uniform(-50, 300), -1.8, rng.uniform(0, 6), rng.uniform(0.8, 1.2))
    eic_inst(palms[0], -20, 28, 0, 0.3, 1.0)
    eic_inst(palms[1], -24, 22, 0, 1.3, 1.1)
    eic_boat(60, 50, math.radians(85), "budgerow", z=-2.5)
    eic_boat(130, 120, math.radians(95), "country", z=-2.5, seed=2)
    eic_boat(200, 30, math.radians(80), "country", z=-2.5, seed=3)
    eic_aerial(50, 700, 0.7)
    camera_path([(0.0, (2.5, -12, 2.2)), (1.0, (1.0, -10, 2.2))], lens=26, target_keys=[(0.0, (-1, 22, 3.5)), (1.0, (-1.5, 22, 3.5))])
    return sc


def eic_shot_plassey():
    sc = eic_begin()
    eic_sky("kloofendal_overcast_puresky", 0.55, sun_az=25)
    eic_sun(25, 1.6, (1, 0.84, 0.62), el=14)
    exposure(0.0)
    rng = random.Random(57)
    grass = eic_ph("wetgrass", "leafy_grass", 0.3, tint=(0.8, 1.0, 0.7), fallback=(0.2, 0.35, 0.12))
    mud = eic_ph("plmud", "brown_mud", 0.3, tint=(0.85, 0.78, 0.65), fallback=(0.35, 0.28, 0.2))
    brick = eic_ph("lodgebrick", "medieval_red_brick", 0.45, tint=(0.92, 0.72, 0.6), fallback=(0.45, 0.22, 0.15))
    lime = eic_ph("lime", "white_stucco", 0.35, tint=(1.0, 0.95, 0.86))
    puddle = eic_water_mat("puddle", "#3A4048", rough=0.03, wave=0.04)
    eic_poly_ground([(-800, -100), (48, -100), (60, 300), (40, 700), (-800, 700)], 0.0, grass)
    eic_poly_ground([(125, -100), (900, -100), (900, 700), (110, 700), (130, 300)], 0.0, grass, name="farbank")
    eic_water((90, 300, -0.6), (90, 400), "#6B6247", rough=0.06, wave=0.12, scale=0.3)
    for px, py, sx_, sy_ in ((-8, 2, 2.6, 1.6), (5, 8, 1.8, 1.1), (-16, 16, 3.5, 2.0), (12, 22, 2.4, 1.4), (-30, 30, 4, 2.2), (2, 30, 3, 1.5)):
        r_ = rng.uniform(0, 1)
        add("plane", (px, py, 0.015), (sx_ * 1.4, sy_ * 1.5, 1), (0, 0, r_), m=mud)
        add("plane", (px, py, 0.03), (sx_, sy_, 1), (0, 0, r_), m=puddle)
    protos = [eic_tree_proto(s, h=8.5, crown=5.5) for s in (61, 62, 63)]
    for i in range(12):                                                         # Lakshabagh: mango trees in rows
        for j in range(10):
            eic_inst(protos[(i + j) % 3], -78 + i * 8.5 + rng.uniform(-0.8, 0.8), 52 + j * 8.5 + rng.uniform(-0.8, 0.8), 0, rng.uniform(0, 6.28),
                     rng.uniform(0.9, 1.15))
    add("cyl", (-31, 46, -0.4), (1.6, 1.6, 50), (0, math.radians(90), 0), m=grass, vertices=16)      # earthen bank and ditch
    add("cyl", (-84, 92, -0.4), (1.6, 1.6, 48), (math.radians(90), 0, 0), m=grass, vertices=16)
    add("cyl", (22, 92, -0.4), (1.6, 1.6, 48), (math.radians(90), 0, 0), m=grass, vertices=16)
    add("plane", (-31, 42.6, 0.02), (50, 1.4, 1), m=mud)
    add("plane", (-31, 42.6, 0.04), (49, 0.6, 1), m=puddle)
    lx, ly = 36, 96                                                             # the Nawab's hunting lodge
    add("cube", (lx, ly, 4.2), (6.5, 5.0, 4.2), m=brick)
    add("cube", (lx, ly, 8.55), (6.7, 5.2, 0.15), m=lime)
    for k in range(14):
        add("cube", (lx - 6.2 + k * 0.95, ly - 5.0, 9.0), (0.22, 0.25, 0.3), m=brick)
    eic_arcade(lx - 6.5, ly - 5.4, 3, 4.33, 2.0, 1.2, 3.6, 0.8, 0.7, brick, p=2, q=0.5)
    add("cube", (lx, ly - 4.95, 1.4), (5.8, 0.05, 1.4), m=eic_col("darkdoor", "#16110D", 0.9))
    for sx in (-1, 1):
        for sy in (-1, 1):
            eic_chhatri(lx + sx * 5.8, ly + sy * 4.3, 8.7, 0.8, brick, lime)
    rough_tree = eic_tree_proto(71, h=7, crown=4.5)
    palms = [eic_palm_proto(s, h=11) for s in (72, 73)]
    for k in range(50):
        eic_inst(rough_tree if k % 3 else palms[k % 2], rng.uniform(140, 600), rng.uniform(-50, 600), 0, rng.uniform(0, 6), rng.uniform(0.8, 1.3))
    for k in range(70):
        eic_inst(protos[k % 3] if k % 4 else palms[k % 2], rng.uniform(-700, 40), rng.uniform(260, 700), 0, rng.uniform(0, 6), rng.uniform(0.8, 1.2))
    for k in range(10):
        eic_inst(palms[k % 2], rng.uniform(42, 52), rng.uniform(40, 200), 0, rng.uniform(0, 6), rng.uniform(0.9, 1.2))
    eic_rain(-260, 520, 420, 140, 0.15)
    eic_rain(320, 760, 360, 140, -0.2)
    eic_aerial(40, 380, 0.85)
    camera_path([(0.0, (-6, -22, 2.3)), (1.0, (-2.5, -20, 2.3))], lens=30, target_keys=[(0.0, (-12, 80, 5.0)), (1.0, (-8, 80, 5.0))])
    return sc


def eic_shot_allahabad():
    sc = eic_begin()
    sc.cycles.max_bounces = 6
    eic_sky("kloofendal_48d_partly_cloudy_puresky", 0.9, sun_az=30)
    eic_sun(30, 4.5, (1, 0.9, 0.75), el=58)
    exposure(0.1)
    rng = random.Random(65)
    ground = eic_ph("campground", "dry_ground_01", 0.2, tint=(0.88, 0.78, 0.62), fallback=(0.5, 0.42, 0.3))
    lining = eic_pmat("tentlining", lambda: eic_pat_qanat(base="#E9DFC9", line="#C9B48E", accent="#A4302A", n=3), rough=0.9, translucent=0.45,
                      uv_scale=(3, 1))
    roofl = eic_pmat("tentroof", lambda: eic_pat_stripes(cols=("#A4302A", "#E9DFC9", "#A4302A", "#E9DFC9"), n=10), rough=0.9, translucent=0.45,
                     uv_scale=(2, 1))
    canvas = eic_ph("tentcanvas", "rough_linen", 0.6, tint=(0.95, 0.9, 0.78), fallback=(0.85, 0.8, 0.7))
    dhurrie = eic_pmat("dhurrie", lambda: eic_pat_stripes(cols=("#2B3F6E", "#E9DFC9", "#2B3F6E", "#D8C9A8"), n=14), rough=0.95, uv_scale=(3, 4))
    chintz = eic_pmat("chintz", lambda: eic_pat_chintz(), rough=0.8, sheen=0.3, uv_scale=(2, 2))
    mahog = eic_ph("mahogany", "dark_wood", 1.5, tint=(0.95, 0.55, 0.4), fallback=(0.3, 0.12, 0.08))
    stone = eic_ph("fortstone", "old_stone_wall", 0.15, tint=(0.95, 0.88, 0.75), fallback=(0.6, 0.55, 0.45))
    gold = eic_gold()
    add("plane", (0, 0, 0), (400, 400, 1), m=ground)
    add("plane", (0, 2, 0.01), (6, 8, 1), m=dhurrie)
    W, Y0, Y1, HW, HR = 6.0, -6.0, 10.0, 2.6, 5.6
    eic_cloth((-W, 2, HW / 2), Y1 - Y0, HW, lining, rot=(math.radians(90), 0, math.radians(90)), folds=14, amp=0.04, nu=60)
    eic_cloth((W, 2, HW / 2), Y1 - Y0, HW, lining, rot=(math.radians(90), 0, math.radians(-90)), folds=14, amp=0.04, nu=60)
    eic_cloth((0, Y0, HW / 2), 2 * W, HW, lining, folds=10, amp=0.04, nu=50)
    eic_cloth((-1.6, Y1, HW / 2), 8.8, HW, lining, folds=8, amp=0.04, nu=40)
    eic_cloth((5.6, Y1, HW / 2), 0.8, HW, lining, folds=1, amp=0.03, nu=6)
    for sg in (-1, 1):
        eic_gridm("roof", 30, 8, lambda u, v, sg=sg: (sg * W * (1 - v), Y0 + (Y1 - Y0) * u, HW + (HR - HW) * v - 0.15 * math.sin(math.pi * v)), roofl)
    eic_gridm("gableback", 12, 4, lambda u, v: ((u - 0.5) * 2 * W * (1 - v), Y1, HW + (HR - HW) * v), lining)
    eic_gridm("gablefront", 12, 4, lambda u, v: ((u - 0.5) * 2 * W * (1 - v), Y0, HW + (HR - HW) * v), lining)
    pole = eic_ph("tentpole", "rough_wood", 1.0, tint=(0.7, 0.5, 0.35))
    for py in (-1.0, 6.0):
        eic_rod((0, py, 0), (0, py, HR + 0.5), 0.09, pole, 10)
        add("sphere", (0, py, HR + 0.6), (0.14, 0.14, 0.18), m=gold, segments=10, ring_count=6)
    eic_rod((0, Y0, HR - 0.05), (0, Y1, HR - 0.05), 0.07, pole)
    add("cyl", (3.4, Y1 - 0.05, HW - 0.15), (0.16, 0.16, 1.4), (0, math.radians(90), 0), m=lining, vertices=10)
    eic_carpet(-1.2, 7.3, 4.6, 3.2, "medallion", seed=31, z=0.02, field="#8F2430")       # the throne: armchair on the table
    eic_table(-1.2, 7.6, 3.0, 1.2, 0.78, mahog)
    eic_draped(-1.2, 7.6, 0.79, 3.06, 1.26, 0.55, chintz, folds=5)
    cx, cy, cz = -1.2, 7.75, 0.8
    for sx in (-1, 1):
        for sy in (-1, 1):
            eic_rod((cx + sx * 0.3, cy + sy * 0.26, cz), (cx + sx * 0.28, cy + sy * 0.24, cz + 0.45), 0.03, mahog, 6)
        eic_rod((cx + sx * 0.3, cy - 0.26, cz + 0.45), (cx + sx * 0.3, cy - 0.26, cz + 0.72), 0.025, mahog, 6)
        add("cube", (cx + sx * 0.3, cy - 0.02, cz + 0.74), (0.04, 0.3, 0.03), m=mahog)
    add("cube", (cx, cy, cz + 0.48), (0.34, 0.3, 0.05), m=chintz)
    add("cube", (cx, cy + 0.3, cz + 0.95), (0.32, 0.04, 0.45), m=chintz)
    add("cube", (cx, cy + 0.32, cz + 1.42), (0.36, 0.05, 0.05), m=mahog)
    eic_cloth((cx, cy + 0.36, cz + 0.85), 0.8, 1.0, chintz, folds=3, amp=0.03, nu=12, nv=6)
    add("cube", (cx, cy, cz + 0.56), (0.3, 0.26, 0.04), m=eic_col("cushion_gold", "#C9A13C", 0.5))
    eic_carpet(0.2, 1.6, 4.2, 6.2, "pictorial", seed=33, z=0.02)
    eic_carpet(-3.8, 3.0, 2.4, 3.6, "ushak", seed=34, z=0.025, rz=0.06)
    leather = eic_col("leather", "#5A2A1A", 0.6)
    for sx_, sy_ in ((2.9, 5.6), (-4.2, 5.4)):                                 # folding camp chairs
        for sgn in (-1, 1):
            eic_rod((sx_ - 0.25, sy_ + sgn * 0.2, 0), (sx_ + 0.25, sy_ - sgn * 0.2, 0.45), 0.02, mahog, 5)
            eic_rod((sx_ + 0.25 * sgn, sy_ + 0.22, 0.45), (sx_ + 0.25 * sgn, sy_ + 0.3, 0.95), 0.02, mahog, 5)
        add("cube", (sx_, sy_, 0.46), (0.27, 0.24, 0.015), m=leather)
        add("cube", (sx_, sy_ + 0.29, 0.82), (0.27, 0.015, 0.13), m=leather)
    eic_chest(-4.9, 8.9, 0, 0.0)
    eic_chest(4.6, 8.4, 0, 0.3, 0.9)
    eic_table(3.6, 3.4, 1.0, 0.7, 0.75, mahog)
    add("cube", (3.6, 3.4, 0.78), (0.32, 0.22, 0.03), m=eic_col("paper", "#EDE3C8", 0.8))
    add("cube", (3.4, 3.5, 0.8), (0.1, 0.06, 0.04), m=eic_col("inkwell", "#2A2A2A", 0.3, 0.5))
    eic_rod((0, 2.5, HR - 0.1), (0, 2.5, 4.3), 0.01, eic_col("iron", "#2B2826", 0.45, 0.7), 4)
    add("cube", (0, 2.5, 4.1), (0.13, 0.13, 0.2), m=eic_col("lanternglass", "#FFD9A0", 0.3, emit=3.0))
    light("POINT", (0, 2.5, 4.0), 40, (1, 0.75, 0.45), 0.3)
    for tx, ty, tr in ((6, 20, 0.2), (14, 28, -0.1), (-2, 32, 0.4), (22, 22, 0.1), (10, 42, 0.0)):   # camp outside
        t = eic_mesh("tent", [(-2, -1.6, 0), (2, -1.6, 0), (2, 1.6, 0), (-2, 1.6, 0), (-2, 0, 2.6), (2, 0, 2.6)],
                     [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)], canvas, recalc=True)
        eic_group([t], (tx, ty, 0), tr, 1.4)
    eic_rod((8.5, 26, 0), (8.5, 26, 12), 0.08, pole)
    eic_flag(8.5, 26, 9.6, 3.0, 1.6, "union1707")
    add("cube", (60, 150, 8), (70, 4, 8), m=stone)                             # Akbar's fort beyond
    for k in range(6):
        add("cyl", (0 + k * 24, 147, 10), (4, 4, 10), m=stone, vertices=16)
    for k in range(40):
        add("cube", (-8 + k * 3.4, 148, 16.6), (0.8, 3.0, 0.6), m=stone)
    trees = eic_tree_proto(81, h=8, crown=5)
    for k in range(10):
        eic_inst(trees, rng.uniform(-40, 120), rng.uniform(60, 130), 0, rng.uniform(0, 6), rng.uniform(0.8, 1.2))
    eic_area((0, 2.0, HR - 0.4), 300, (1, 0.86, 0.68), 3, size_y=12)
    eic_area((0, Y0 + 0.6, 1.8), 150, (1, 0.9, 0.78), 4, rot=(math.radians(90), 0, 0))
    camera_path([(0.0, (-0.6, -4.6, 1.75)), (1.0, (0.1, -3.4, 1.72))], lens=24, target_keys=[(0.0, (-0.5, 10, 1.75)), (1.0, (-0.2, 10, 1.72))])
    return sc


def eic_shot_hooghly():
    sc = eic_begin()
    eic_sky("qwantani_sunset_puresky", 0.9, sun_az=55)
    eic_sun(55, 2.8, (1, 0.7, 0.42), lo=6, hi=14)
    exposure(-0.25)
    rng = random.Random(77)
    G = 1.65
    bank = eic_ph("bankgrass", "brown_mud_leaves_01", 0.25, tint=(0.85, 0.85, 0.7), fallback=(0.35, 0.3, 0.2))
    brick = eic_ph("ghatbrick", "red_brick_03", 0.5, tint=(0.92, 0.72, 0.6), fallback=(0.5, 0.3, 0.2))
    terra = eic_ph("terracotta", "red_brick_03", 0.9, tint=(1.0, 0.68, 0.48), fallback=(0.6, 0.3, 0.18))
    lime = eic_ph("chunam", "white_stucco", 0.4, tint=(1.0, 0.96, 0.88))
    dark = eic_col("darkdoor", "#16110D", 0.9)
    eic_poly_ground([(-400, -80), (400, -80), (400, -4), (12, -4), (12, 2), (-8, 2), (-8, -4), (-400, -4)], G - 0.05, bank)
    add("cube", (2, -9, G - 0.02), (10, 11, 0.06), m=brick)                    # ghat platform and steps
    for k in range(9):
        add("cube", (2, 2.35 + k * 0.7, G - 0.2 * (k + 1)), (10, 0.35, 0.2 * (k + 1) / 2 + 0.05), m=brick)
    for sx in (-8.4, 12.4):
        add("cube", (sx, 2.0, G), (0.4, 6.0, 0.55), m=brick)
        add("cube", (sx, -3.5, G + 0.9), (0.6, 0.6, 0.9), m=lime)
        add("sphere", (sx, -3.5, G + 2.0), (0.5, 0.5, 0.45), m=lime, segments=12, ring_count=8)
    eic_water((0, 300, 0.0), (900, 320), "#6E6142", rough=0.05, wave=0.16, scale=0.25, stretch=4)
    tx, ty = -16, -7                                                            # terracotta char-chala temple
    add("cube", (tx, ty, G + 0.4), (3.4, 3.4, 0.4), m=terra)
    add("cube", (tx, ty, G + 0.8 + 1.8), (2.7, 2.7, 1.8), m=terra)
    for k in range(3):
        eic_arch_bay(tx - 1.6 + k * 1.6, ty + 2.72, 0.55, 1.4, 0.6, 2.8, 0.2, terra, lobes=5, depth=0.08).location.z = G + 0.8
        add("cube", (tx - 1.6 + k * 1.6, ty + 2.66, G + 0.8 + 0.95), (0.5, 0.04, 0.95), m=dark)
    eic_chala(tx, ty, G + 4.4, 3.0, 3.0, 2.6, terra, four=True, droop=0.55, bulge=0.45)
    add("cyl", (tx, ty, G + 7.3), (0.35, 0.35, 0.3), m=terra, vertices=12)
    add("sphere", (tx, ty, G + 7.9), (0.3, 0.3, 0.35), m=terra, segments=12, ring_count=8)
    palms = [eic_palm_proto(s, h=rng.uniform(9, 12)) for s in (91, 92, 93)]
    bamboo = eic_bamboo_proto(94)
    banana = eic_banana_proto(95)
    for px, py, s in ((-23, -11, 1.1), (-29, -2, 1.0), (-20, -18, 0.95), (-36, -12, 1.15), (-45, -3, 1.0), (30, -12, 1.0)):
        eic_inst(palms[rng.randrange(3)], px, py, G, rng.uniform(0, 6), s)
    for px, py in ((-28, -20), (-42, -8), (-58, -14)):
        eic_inst(bamboo, px, py, G, rng.uniform(0, 6), rng.uniform(0.9, 1.1))
    for px, py in ((-11, -13), (-12.5, -15.5), (-26, -6)):
        eic_inst(banana, px, py, G, rng.uniform(0, 6), rng.uniform(0.9, 1.2))
    eic_poly_ground([(-1500, 430), (1500, 430), (1500, 1200), (-1500, 1200)], 1.0, eic_ph("farbank2", "leafy_grass", 0.03, tint=(0.7, 0.8, 0.5)), name="far")
    for k in range(90):
        eic_inst(palms[k % 3], rng.uniform(-700, 700), rng.uniform(435, 520), 1.0, rng.uniform(0, 6), rng.uniform(0.9, 1.4))
    for k in range(20):
        eic_inst(bamboo, rng.uniform(-700, 700), rng.uniform(440, 520), 1.0, rng.uniform(0, 6), rng.uniform(0.9, 1.3))
    for k in range(14):
        hx = rng.uniform(-300, 300)
        if abs(hx - 110) < 30:
            continue
        eic_hut(hx, rng.uniform(440, 470), rng.uniform(-0.3, 0.3), z=1.0, s=1.3)
    fx, fy = 110, 450                                                           # the European factory on the far bank
    add("cube", (fx, fy, 1.0 + 5.5), (17, 7, 5.5), m=lime)
    add("cube", (fx, fy, 1.0 + 11.3), (17.2, 7.2, 0.3), m=lime)
    for k in range(13):
        add("cyl", (fx - 15 + k * 2.5, fy - 9.5, 1.0 + 2.6), (0.3, 0.3, 2.6), m=lime, vertices=10)
    add("cube", (fx, fy - 8.3, 1.0 + 5.3), (16.5, 1.6, 0.2), m=lime)
    for k in range(12):
        add("cube", (fx - 14 + k * 2.55, fy - 7.02, 1.0 + 8.4), (0.03, 0.55, 0.9), m=eic_col("shutter", "#2E5A3A", 0.6))
    eic_rod((fx + 20, fy - 6, 1.0), (fx + 20, fy - 6, 23), 0.15, eic_col("flagpole", "#3A2E22", 0.6))
    eic_flag(fx + 20, fy - 6, 19.5, 7, 3.8, "eic1707", rz=math.radians(180))
    eic_boat(18, 60, math.radians(8), "country", seed=1)
    eic_boat(-45, 130, math.radians(-12), "country", seed=2)
    eic_boat(95, 230, math.radians(5), "country", s=1.1, seed=3)
    eic_boat(-120, 290, math.radians(175), "country", seed=4)
    eic_boat(-20, 40, math.radians(160), "budgerow", sail=False)
    eic_boat(15, 9.6, math.radians(80), "country", s=0.6, sail=False, seed=5)
    eic_boat(-11, 10.5, math.radians(100), "country", s=0.55, sail=False, seed=6)
    eic_aerial(70, 700, 0.8)
    camera_path([(0.0, (2, -17, G + 1.65)), (1.0, (3.6, -15, G + 1.6))], lens=30, target_keys=[(0.0, (4, 200, 3.2)), (1.0, (6, 200, 3.2))])
    return sc


SHOTS.update({"e_spice_quay": eic_shot_spice_quay, "e_london": eic_shot_london, "e_whitehall": eic_shot_whitehall,
              "e_deptford": eic_shot_deptford, "e_ajmer_court": eic_shot_ajmer_court, "e_surat": eic_shot_surat,
              "e_calcutta": eic_shot_calcutta, "e_murshidabad": eic_shot_murshidabad, "e_plassey": eic_shot_plassey,
              "e_allahabad": eic_shot_allahabad, "e_hooghly": eic_shot_hooghly})
