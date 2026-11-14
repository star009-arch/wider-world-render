"""Living backgrounds: small period people (and camels) going about their day behind the action, so places never look empty.

Each 3D set listed in LIFE gets a few background walkers on its own street/ground (behind the main cast, smaller, slow),
added to every shot on that set by add(shots). They are marked .bg_extra so the Facebook framing ignores them. The quality
gate checks their feet like everyone else's (on the floor, never in water or on walls).
"""
from __future__ import annotations

import motions as M

# set: (world, [keys], ground band (min, max) in world y, x range, how many, scale)
LIFE = {
    "m_steppe_dawn": ("mongol_1200", ["rider", "rider2", "archer", "merchant"], (835, 860), (150, 1750), 5, 0.62),
    "m_karakorum":   ("mongol_1200", ["merchant", "scholar", "rubruck", "rider"], (835, 860), (150, 1750), 4, 0.62),
    "m_bukhara":     ("mongol_1200", ["merchant", "scholar", "merchant"], (840, 860), (200, 1700), 3, 0.62),
    "m_caravan":     ("mongol_1200", ["camel_walk", "merchant", "camel_walk"], (830, 850), (150, 1750), 4, 0.6),
    "m_baghdad":     ("mongol_1200", ["merchant", "scholar"], (850, 865), (300, 1650), 2, 0.62),
    "e_calcutta":    ("bengal_1757", ["boatman", "weaver", "csepoy", "sepoy"], (845, 865), (250, 1650), 4, 0.62),
    "e_murshidabad": ("bengal_1757", ["weaver", "boatman", "sepoy"], (850, 865), (300, 1600), 2, 0.6),
    "e_hooghly":     ("bengal_1757", ["boatman", "weaver"], (840, 860), (300, 1600), 2, 0.62),
    "e_london":      ("london_1600", ["merchant2", "sailor", "shipwright", "merchant"], (840, 860), (300, 1500), 4, 0.62),
    "e_deptford":    ("london_1600", ["sailor", "shipwright"], (850, 865), (200, 1300), 2, 0.62),
    "e_surat":       ("mughal_1616", ["merchant", "courtier2", "guard"], (845, 865), (250, 1650), 4, 0.62),
}


def _rand(seed):
    x = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return x / 0x7FFFFFFF


def add(shots, enabled=True):
    """Add background walkers to every shot on a LIFE set (deterministic per shot name)."""
    if not enabled:
        return shots
    for sh in shots:
        if not sh.bg.startswith("plate:") or sh.bg[6:] not in LIFE:
            continue
        world, keys, (g0, g1), (x0, x1), n, s = LIFE[sh.bg[6:]]
        seed = sum(map(ord, sh.name))
        for i in range(n):
            r1, r2, r3 = _rand(seed + 7 * i), _rand(seed + 13 * i + 1), _rand(seed + 29 * i + 2)
            x = x0 + (x1 - x0) * (i + 0.5 * r1) / n
            ground = g0 + (g1 - g0) * r2
            left = r3 < 0.5
            span = 120 + 140 * r2
            target = max(x0, x - span) if left else min(x1, x + span)
            p = M.Performer(f"{world}:{keys[(seed + i) % len(keys)]}", x=x, ground=ground, scale=s, flip=left,
                            walks=[(0.3 + r1, target)], speed=0.45)
            p.bg_extra = True
            sh.actors.insert(0, p)
    return shots
