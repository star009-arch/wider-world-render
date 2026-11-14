"""Living backgrounds: period people (and camels) going about their day in the distance, so places never look empty.

Version 2 (15 Nov 2026, after the owner's review: "avoid artificial-looking crowds and people standing in identical
groups"). People are placed IN DEPTH: the further away, the higher on screen and the smaller, following each set's horizon.
They come as natural little groups (two people talking, someone walking past, a small knot of three), never in a row,
never two identical figures side by side, and they keep clear of the main cast. They are marked .bg_extra so the Facebook
framing and the text guard ignore them; the quality gate checks their feet like everyone else's.
"""
from __future__ import annotations

import motions as M

FRONT = 855.0            # screen y of the main cast's feet
S_REF = 0.95             # scale of an ordinary person standing on the cast's line (hosts are drawn larger than life)

# set: world, people keys, horizon (screen y where the ground meets the distance), band of screen y they may stand in,
#      x range, number of groups
LIFE = {
    "m_steppe_dawn": dict(world="mongol_1200", keys=["rider", "rider2", "archer", "merchant", "borte"], horizon=545, band=(610, 770), xr=(60, 1860), groups=5),
    "m_karakorum":   dict(world="mongol_1200", keys=["merchant", "scholar", "rubruck", "rider", "archer"], horizon=570, band=(712, 775), xr=(60, 1860), groups=4),
    "m_bukhara":     dict(world="mongol_1200", keys=["merchant", "scholar", "governor", "merchant"], horizon=585, band=(625, 770), xr=(260, 1840), groups=4),
    "m_caravan":     dict(world="mongol_1200", keys=["merchant", "camel_walk", "merchant", "rider"], horizon=580, band=(630, 770), xr=(60, 1860), groups=4),
    "m_baghdad":     dict(world="mongol_1200", keys=["merchant", "scholar"], horizon=575, band=(745, 780), xr=(260, 1700), groups=2),
    "m_zhongdu":     dict(world="mongol_1200", keys=["jin", "rider", "archer", "jin_official"], horizon=585, band=(630, 770), xr=(80, 1840), groups=4),
    "e_calcutta": dict(world="bengal_1757", keys=["boatman", "weaver", "csepoy", "sepoy"], horizon=615, band=(762, 784), xr=(250, 1650), groups=3),
    "e_murshidabad": dict(world="bengal_1757", keys=["weaver", "boatman", "sepoy", "csepoy"], horizon=640, band=(745, 784), xr=(730, 1600), groups=3),
    "e_hooghly": dict(world="bengal_1757", keys=["boatman", "weaver", "csepoy"], horizon=625, band=(705, 782), xr=(140, 1700), groups=4),
    "e_london": dict(world="london_1600", keys=["merchant2", "sailor", "shipwright", "merchant"], horizon=620, band=(690, 782), xr=(300, 1500), groups=4,
                          taper=(880, 2.2, 900, 3.4)),
    "e_surat": dict(world="mughal_1616", keys=["merchant", "courtier2", "guard", "courtier"], horizon=680, band=(715, 782), xr=(700, 1550), groups=4),
}


class _Rand:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def r(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF

    def pick(self, seq, avoid=None):
        for _ in range(6):
            v = seq[int(self.r() * len(seq)) % len(seq)]
            if v != avoid:
                return v
        return v


def _world_y(ys):
    """Screen y of the feet -> the ground value that motions.stage() will map back to it."""
    return ys if ys <= M.STAGE_Y0 else M.STAGE_Y0 + (ys - M.STAGE_Y0) / M.STAGE_KY


def _scale(ys, horizon):
    return max(0.14, round(S_REF * (ys - horizon) / (FRONT - horizon) / 0.04) * 0.04)


def add(shots, enabled=True):
    """Add depth-placed background groups to every shot on a LIFE set (deterministic per shot name)."""
    if not enabled:
        return shots
    for sh in shots:
        if not sh.bg.startswith("plate:") or sh.bg[6:] not in LIFE:
            continue
        cfg = LIFE[sh.bg[6:]]
        rnd = _Rand(sum(map(ord, sh.name)) * 7919)
        mains = []
        for a in sh.actors:
            if hasattr(a, "pos_at"):
                for f in (0.0, 0.5, 1.0):
                    mains.append((a.pos_at(sh.dur * f)[0], 70 + 70 * getattr(a, "scale", 1.5)))
        y0, y1 = cfg["band"]
        x0, x1 = cfg["xr"]
        placed, tries, extras = [], 0, []
        while len(placed) < cfg["groups"] and tries < 80:
            tries += 1
            ys = y0 + (y1 - y0) * rnd.r() ** 1.6                                 # more groups far away than near
            s = _scale(ys, cfg["horizon"])
            gx = x0 + (x1 - x0) * rnd.r()
            if "taper" in cfg:                                                   # a street that narrows into the distance
                vl, kl, vr, kr = cfg["taper"]
                xl_, xr_ = max(x0, vl - (ys - cfg["horizon"]) * kl), min(x1, vr + (ys - cfg["horizon"]) * kr)
                gx = xl_ + (xr_ - xl_) * rnd.r()
            width = 150 * s
            if any(abs(gx - mx) < keep + width for mx, keep in mains):           # keep clear of the main cast
                continue
            if any(abs(gx - px) < 260 * max(s, ps) + 40 and abs(ys - py) < 28 for px, py, ps in placed):
                continue                                                         # groups never line up in a row
            placed.append((gx, ys, s))
            kind = rnd.pick(["pair", "walker", "pair", "trio", "walker"])
            ground = _world_y(ys)
            last = None
            if kind == "walker":
                key = rnd.pick(cfg["keys"])
                left = rnd.r() < 0.5
                dist = (220 + 260 * rnd.r()) * s
                tx = max(x0, gx - dist) if left else min(x1, gx + dist)
                extras.append(M.Performer(f"{cfg['world']}:{key}", x=gx, ground=ground, scale=s, flip=left,
                                          walks=[(0.2 + 1.5 * rnd.r(), tx)], speed=max(0.18, 0.5 * s)))
            else:
                n = 2 if kind == "pair" else 3
                for i in range(n):
                    key = rnd.pick([k for k in cfg["keys"] if not k.startswith("camel")] or cfg["keys"], avoid=last)
                    last = key
                    dx = (i - (n - 1) / 2) * 95 * s
                    dy = (3 if i % 2 else 0) + (6 * rnd.r() if kind == "trio" else 0)
                    extras.append(M.Performer(f"{cfg['world']}:{key}", x=gx + dx, ground=_world_y(ys + dy * s), scale=s,
                                              flip=(dx > 0), acts=[(0.6 + 2.5 * rnd.r(), "nod", None)] if i == 0 else []))
        for p in extras:
            p.bg_extra = True
            sh.actors.insert(0, p)
    return shots
