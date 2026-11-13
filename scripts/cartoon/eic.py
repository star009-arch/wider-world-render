"""Tiny Empires episode 3 (release order): "How a Company Took Over India" (~8.5 min). Engine: ep01.py.

Rebuilt to the period standard (visual bible 04_east_india_company_1600-1765.md): hosts change costume by era (hosts3 worlds
"london_1600", "mughal_1616", "bengal_1757", set per shot), historical cast from people.py, period 3D sets (release te-3d-eic-v1),
and the pacing rule (voice in 0.2 s, a new picture on every hook line, title sting after the mystery, tease ending).

  python scripts/cartoon/eic.py preview | render i/k [outdir] | mix <shots dir> <out> [music]

Lines: projects/tiny-empires/ep01/lines.json (E01-E54 fact-checked; C01-C08 "what the Company bought" fact-checked separately).
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep01 as K  # noqa: E402
import fxlib as FX  # noqa: E402
import motions as M  # noqa: E402
import scene as SC  # noqa: E402
from scene import Shot, ease  # noqa: E402

P, at, dur, label, caption, pin, route, timeline = K.P, K.at, K.dur, K.label, K.caption, K.pin, K.route, K.timeline
G = 1030
GOLD = (255, 214, 120)
LON, MUG, BEN = "london_1600", "mughal_1616", "bengal_1757"
M.set_world(LON)


def E(world, key, x, ground=1000, s=1.5, **kw):
    return M.Performer(f"{world}:{key}", x=x, ground=ground, scale=s, **kw)


def scene(*a, **kw):
    """Engine scene + a slow push-in on any still shot."""
    sh = K.scene(*a, **kw)
    if kw.get("follow", True) is False and kw.get("cam") is None:
        sh.camkeys = [(0.0, 1.0, 0.5, 0.5), (sh.dur, 1.045, 0.5, 0.5)]
    return sh


def split(first, cut, bg, actors=(), fx=(), camkeys=None, name=None):
    """One line across a cut: the voice keeps running while the picture changes."""
    rest = first.dur - cut
    first.dur = cut
    return [first, Shot(name or first.name + "_b", rest, bg, actors=list(actors), fx=list(fx), world=first.world,
                        camkeys=camkeys or [(0.0, 1.0, 0.5, 0.5), (rest, 1.06, 0.5, 0.5)])]


# ------------------------------------------------------------------------------------------------ episode fx
def charter(t0, stamp_t):
    """The royal charter of 31 Dec 1600 unrolls; the great seal stamps down."""
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 0.7)
        x0, x1, y0 = 560, 1360, 170
        h = 640 * k
        d.rectangle([x0, y0, x1, y0 + h], fill=(236, 222, 186, 255), outline=(30, 24, 20, 255), width=5)
        for xx in (x0, x1):
            d.ellipse([xx - 26, y0 - 26, xx + 26, y0 + 26], fill=(150, 104, 60, 255), outline=(30, 24, 20, 255), width=4)
            d.ellipse([xx - 26, y0 + h - 26, xx + 26, y0 + h + 26], fill=(150, 104, 60, 255), outline=(30, 24, 20, 255), width=4)
        if k > 0.9:
            K.S_text(d, 960, y0 + 80, "Governor and Company of Merchants", 40, anchor="mm", color=(60, 40, 20))
            K.S_text(d, 960, y0 + 130, "of London, trading into the East Indies", 40, anchor="mm", color=(60, 40, 20))
            for i in range(6):
                d.line([(x0 + 70, y0 + 210 + i * 46), (x1 - 70, y0 + 210 + i * 46)], fill=(150, 130, 100, 255), width=4)
        if t >= stamp_t:
            s = M.ease_out_back((t - stamp_t) / 0.3)
            r = 70 * (2.2 - 1.2 * min(1, s))
            cx, cy = 1180, y0 + 560
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(170, 30, 30, 255), outline=(90, 10, 10, 255), width=6)
            if s > 0.9:
                K.S_text(d, cx, cy, "1600", 34, anchor="mm", color=(255, 220, 200))
    return f


def calico(t0):
    """Calico, chintz and muslin swatches."""
    items = [("CALICO", (238, 228, 205), None), ("CHINTZ", (240, 226, 200), (200, 60, 60)), ("MUSLIN", (250, 250, 248), None)]

    def f(t, d, frame):
        for i, (nm, base, flower) in enumerate(items):
            ts = t0 + i * 0.9
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.4)
            x, y = 360 + i * 420, 420
            a = 110 if nm == "MUSLIN" else 255
            d.rounded_rectangle([x - 160 * k, y - 200 * k, x + 160 * k, y + 200 * k], radius=16, fill=base + (a,), outline=(30, 24, 20, 255), width=4)
            if flower and k > 0.8:
                for j in range(9):
                    fx_, fy_ = x - 100 + (j % 3) * 100, y - 120 + (j // 3) * 120
                    for q in range(5):
                        ang = q / 5 * 6.28
                        d.ellipse([fx_ + 18 * math.cos(ang) - 12, fy_ + 18 * math.sin(ang) - 12, fx_ + 18 * math.cos(ang) + 12,
                                   fy_ + 18 * math.sin(ang) + 12], fill=flower + (255,))
                    d.ellipse([fx_ - 8, fy_ - 8, fx_ + 8, fy_ + 8], fill=(230, 180, 50, 255))
            if k > 0.8:
                K.S_text(d, x, y + 250, nm, 50, anchor="mm", color=GOLD)
        if t > t0 + 2.6:
            K.S_text(d, 760, 900, "Bengal muslin: \"woven air\"", 44, anchor="mm")
    return f


def goods(t0):
    items = [("INDIGO", (40, 50, 140)), ("SALTPETRE", (235, 235, 230)), ("TEA (CHINA)", (90, 120, 50))]

    def f(t, d, frame):
        for i, (nm, col) in enumerate(items):
            ts = t0 + i * 1.0
            if t < ts:
                continue
            k = M.ease_out_back((t - ts) / 0.35)
            x, y = 380 + i * 400, 420
            d.polygon([(x - 120 * k, y + 140 * k), (x + 120 * k, y + 140 * k), (x + 90 * k, y - 120 * k), (x - 90 * k, y - 120 * k)],
                      fill=(170, 130, 80, 255), outline=(30, 24, 20, 255))
            d.ellipse([x - 90 * k, y - 160 * k, x + 90 * k, y - 80 * k], fill=col + (255,), outline=(30, 24, 20, 255), width=4)
            if k > 0.8:
                K.S_text(d, x, y + 210, nm, 46, anchor="mm", color=GOLD)
    return f


def table_throne(t0):
    """The famous improvisation at Allahabad, 1765: an armchair set on a table as the emperor's throne."""
    def f(t, d, frame):
        if t < t0:
            return
        k = ease((t - t0) / 0.6)
        x, y = 960, 760
        d.rectangle([x - 200, y - 120 * k, x + 200, y - 120 * k + 30], fill=(130, 90, 50, 255), outline=(30, 24, 20, 255), width=4)
        for dx in (-180, 160):
            d.rectangle([x + dx, y - 90 * k, x + dx + 20, y + 40], fill=(110, 76, 40, 255), outline=(30, 24, 20, 255), width=3)
    return f


# ------------------------------------------------------------------------------------------------ the episode
def shots():
    K.CUES.clear()
    out = []
    H0 = 0.2
    # ---- HOOK
    L = ["E01"]
    a_ = scene("s00_spice", "plate:e_spice_quay", [P("penny", 1600, G, 1.8, flip=True, faces=[(0, {"brows": -0.3, "mouth": "smirk"})])], L,
               lead=H0, follow=False, cam=[(0.0, 1.0, 0.5, 0.5), (4.0, 1.1, 0.45, 0.5)], world=LON,
               fx=[label("THE SPICE TRADE · 1600", 760, 110, 0.0, 60, GOLD)])
    out += split(a_, 3.3, "plate:e_calcutta", actors=FX.people(BEN, ["csepoy"] * 5, -500, 1020, 170, 1.2, walk=(0.0, 900), speed=1.0),
                 fx=[label("...AND ENDING UP RULING MILLIONS", 960, 110, 0.0, 56, GOLD)], name="s00_rule")
    L = ["E02"]
    out.append(scene("s00_impossible", "plate:e_calcutta", [P("atlas", 1300, G, 2.0, flip=True, faces=[(0, {"brows": 0.8, "mouth": "o"})])], L,
                     lead=H0, follow=False, cam=[(0.0, 1.2, 0.62, 0.55), (3.0, 1.28, 0.64, 0.55)], world=BEN))
    L = ["E03"]
    out.append(scene("s00_paper", "plate:e_whitehall", [P("penny", 1720, G, 1.6, flip=True)], L, lead=H0, follow=False, world=LON,
                     fx=[charter(0.6, at(L, 1, H0) - 1.2)]))
    L = ["E04"]
    out.append(scene("s00_always", "plate:e_whitehall", [P("zed", 1300, G, 2.0, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(0.3, "shrug", None)])],
                     L, lead=H0, follow=False, cam=[(0.0, 1.2, 0.62, 0.55), (3.0, 1.26, 0.64, 0.55)], world=LON))
    L = ["E05"]
    out.append(scene("s01_title", "plate:e_london",
                     [P(k, 420 + i * 270, G, 1.5, faces=[(0, {"mouth": "grin" if k != "pike" else "o"})], acts=[(0.4 + i * 0.1, "wave", 0.6)])
                      for i, k in enumerate(["atlas", "quill", "penny", "zed", "pike"])],
                     L, lead=H0, follow=False, extra=0.6, world=LON, fx=[FX.title_sting(H0 + 3.0, "How a Company Took Over India")]))
    # ---- 1. London 1600
    L = ["E06"]
    out.append(scene("s02_london", "plate:e_london", [*FX.people(LON, ["merchant", "merchant2", "sailor"], 200, 1000, 230, 1.3, walk=(0.4, 200), speed=0.5),
                                                     P("penny", 1720, G, 1.6, flip=True)],
                     L, follow=False, world=LON, fx=[label("LONDON · 31 DECEMBER 1600", 760, 110, 0.3, 60, GOLD)]))
    L = ["E07"]
    out.append(scene("s02_charter", "plate:e_whitehall",
                     [E(LON, "queen", 900, 960, 1.6, faces=[(0, {"mouth": "smile"})], acts=[(1.2, "present", None)]),
                      E(LON, "smythe", 520, 1000, 1.4), E(LON, "merchant", 1250, 1000, 1.4, flip=True), P("quill", 1720, G, 1.6, flip=True)],
                     L, world=LON, fx=[label("QUEEN ELIZABETH I GRANTS THE CHARTER", 760, 100, 0.3, 54, GOLD)]))
    L = ["E08", "E09"]
    out.append(scene("s02_monopoly", "m_world", [P("zed", 1700, G, 1.6, flip=True)], L, follow=False, world=LON,
                     fx=[pin("m_world", -0.1, 51.5, "London", 0.4), pin("m_world", 18.4, -34.4, "Cape of Good Hope", 1.0),
                         label("EAST OF THE CAPE: COMPANY ONLY", 1150, 160, 2.0, 56, (255, 214, 60))]))
    L = ["E10", "E11"]
    out.append(scene("s02_investors", "plate:ocean", [P("pike", 1600, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})],
                                                        acts=[(at(L, 1) + 0.2, "flinch", 0.5)])], L, world=LON,
                     fx=[caption("investors share the risk of each voyage", 1.0, at(L, 1)), K.PL_drips(1600, 380, at(L, 1), 99)], follow=False))
    # ---- 2. ships and spices
    L = ["E12"]
    out.append(scene("s03_spice", "plate:e_spice_quay", [P("penny", 1720, G, 1.6, flip=True)], L, follow=False, world=LON,
                     fx=[K.icons_row([("pepper", "pepper"), ("clove", "cloves"), ("nutmeg", "nutmeg")], 380, 0.6),
                         label("WORTH A FORTUNE IN EUROPE", 760, 700, 2.4, 58, GOLD)]))
    L = ["E13"]
    out.append(scene("s03_route", "m_world", [P("atlas", 1700, G, 1.6, flip=True)], L, follow=False, world=LON,
                     fx=[route("m_world", K.S.ROUTE_CAPE, 0.6, dur("E13") + 0.3), pin("m_world", -0.1, 51.5, "London", 0.3)]))
    L = ["E14"]
    out.append(scene("s03_lancaster", "plate:e_deptford", [*FX.people(LON, ["shipwright", "sailor"], 300, 1000, 240, 1.3), P("penny", 1720, G, 1.6, flip=True)],
                     L, follow=False, world=LON, fx=[label("1601 · THE FIRST FLEET · JAMES LANCASTER", 760, 110, 0.4, 52, GOLD)]))
    L = ["E15"]
    out.append(scene("s03_profit", "plate:ocean", [P("zed", 1300, G, 2.0, flip=True, acts=[(0.2, "celebrate", 0.5)])], L, lead=0.2, follow=False, world=LON,
                     fx=[K.PL_coins(1200, 980, 0.3, 2.0)]))
    L = ["E16", "E17"]
    out.append(scene("s03_dutch", "plate:spice", [P("quill", 1720, G, 1.6, flip=True)], L, follow=False, world=LON,
                     fx=[label("THE SPICE ISLANDS", 900, 110, 0.4, 64, GOLD), caption("Dutch East India Company, founded 1602", 1.2, at(L, 1)),
                         caption("Amboyna, 1623", at(L, 1) + 0.4)]))
    # ---- 3. Mughal India
    L = ["E18"]
    out.append(scene("s04_mughal", "plate:india", [P("penny", 1700, G, 1.6, flip=True)], L, follow=False, world=MUG,
                     fx=[label("THE MUGHAL EMPIRE", 760, 140, 0.6, 76, GOLD), caption("one of the richest states in the world", 2.0)]))
    L = ["E19"]
    out.append(scene("s04_surat", "plate:e_surat", [*FX.people(MUG, ["merchant", "guard"], 300, 1000, 260, 1.3), E(LON, "merchant", 900, 1000, 1.3, flip=True),
                                                   P("atlas", 1720, G, 1.7, flip=True)],
                     L, follow=False, world=MUG, fx=[label("SURAT · 1613", 760, 110, 0.4, 66, GOLD)]))
    L = ["E20"]
    out.append(scene("s04_roe", "plate:e_ajmer_court",
                     [E(MUG, "jahangir", 960, 900, 1.6, faces=[(0, {"mouth": "smile"})]), E(MUG, "courtier", 560, 1000, 1.3), E(MUG, "guard", 1300, 1000, 1.3, flip=True),
                      E(MUG, "roe", -200, 1000, 1.4, walks=[(0.3, 760)], speed=1.5, acts=[(3.0, "present", None)]), P("quill", 1720, G, 1.6, flip=True)],
                     L, world=MUG, fx=[label("EMPEROR JAHANGIR · AJMER, 1616", 960, 90, 0.4, 56, GOLD), caption("Sir Thomas Roe, ambassador", 2.0)]))
    L = ["E21"]
    out.append(scene("s04_posts", "m_india", [P("penny", 1700, G, 1.5, flip=True)], L, follow=False, world=MUG,
                     fx=[pin("m_india", 72.83, 21.17, "Surat 1613", 0.3), pin("m_india", 80.27, 13.08, "Madras 1639", 1.6),
                         pin("m_india", 72.88, 19.08, "Bombay 1668", 3.6), pin("m_india", 88.36, 22.57, "Calcutta 1690", 6.0)]))
    L = ["E22"]
    out.append(scene("s04_cloth", "plate:e_surat", [E(BEN, "weaver", 500, 1000, 1.4), P("zed", 1720, G, 1.6, flip=True)], L, follow=False, world=MUG,
                     fx=[K.icons_row([("cloth", "cotton"), ("cloth", "silk")], 340, 0.4)]))
    # ---- 3b. what the Company bought (C01-C08)
    L = ["C01", "C02"]
    out.append(scene("s04b_cloth", "plate:e_surat", [P("penny", 1400, G, 1.6, flip=True), P("atlas", 1720, G, 1.7, flip=True)], L, world=MUG,
                     fx=[calico(at(L, 1) + 1.0)]))
    L = ["C03", "C04"]
    out.append(scene("s04b_fashion", "plate:e_london",
                     [*FX.people(LON, ["merchant", "merchant2"], 400, 1000, 260, 1.4), P("zed", 1400, G, 1.6, flip=True),
                      P("pike", 1720, G, 1.8, flip=True, faces=[(0, {"mouth": "o", "brows": 1.0})], acts=[(at(L, 1), "double_take", None)])],
                     L, world=LON, fx=[caption("by c. 1700: most of what the Company shipped home was cloth", 1.0, at(L, 1))]))
    L = ["C05"]
    out.append(scene("s04b_ban", "plate:e_london", [*FX.people(LON, ["sailor", "shipwright", "merchant2", "sailor"], 150, 1010, 200, 1.2,
                                                              acts=[(1.0, "stamp", None)]), P("quill", 1720, G, 1.6, flip=True)],
                     L, follow=False, world=LON, fx=[label("WEAVERS RIOT · 1719", 700, 110, 0.4, 60, GOLD), label("THE CALICO ACT · 1721", 700, 190, 4.5, 56, (230, 120, 100))]))
    L = ["C06"]
    out.append(scene("s04b_goods", "card", [P("penny", 1720, G, 1.6, flip=True)], L, follow=False, world=MUG, fx=[goods(0.6)]))
    L = ["C07", "C08"]
    out.append(scene("s04b_writer", "plate:e_surat",
                     [E(BEN, "officer", 700, 1000, 1.3, acts=[(1.4, "think", None)]), P("atlas", 1400, G, 1.7, flip=True),
                      P("pike", 1720, G, 1.8, flip=True, faces=[(0, {"mouth": "grin"})], acts=[(at(L, 1) + 0.4, "shrug", None)])],
                     L, world=MUG, fx=[label("THE COMPANY'S CLERKS: \"WRITERS\"", 760, 110, 0.4, 56, GOLD), caption("Robert Clive, aged 18, Madras 1744", 4.0, at(L, 1))]))
    # ---- 4. forts and soldiers
    L = ["E23", "E24", "E25"]
    out.append(scene("s05_army", "plate:e_calcutta",
                     [*FX.people(BEN, ["csepoy"] * 5, 250, 1000, 140, 1.2, walk=(0.3, 500), speed=1.6),
                      P("pike", 1450, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "o"})]), P("penny", 1750, G + 10, 1.7, flip=True)],
                     L, world=BEN, fx=[caption("Company forts and sepoy soldiers", 0.6, at(L, 1))]))
    # ---- 5. Siraj and Calcutta
    L = ["E26"]
    out.append(scene("s06_1707", "card", [P("penny", 1720, G, 1.6, flip=True)], L, follow=False, world=BEN,
                     fx=[timeline([("1707", "Aurangzeb dies"), ("after", "Mughal power|weakens"), ("1700s", "regional rulers|grow stronger")], 0.4, 1.6)]))
    L = ["E27", "E28"]
    out.append(scene("s06_siraj", "plate:e_murshidabad",
                     [E(BEN, "nawab", 900, 960, 1.7, faces=[(0, {"mouth": "smirk"}), (at(L, 1), {"brows": -1.0, "mouth": "frown"})], acts=[(at(L, 1) + 0.3, "fold", None)]),
                      E(BEN, "sepoy", 500, 1000, 1.3), P("atlas", 1700, G, 1.7, flip=True)],
                     L, world=BEN, fx=[label("SIRAJ UD-DAULAH · NAWAB OF BENGAL, 1756", 960, 90, 0.4, 54, GOLD)]))
    L = ["E29", "E30", "E31"]
    sw = at(L, 0) + 1.0
    out.append(scene("s06_capture", "plate:e_calcutta",
                     [E(BEN, "nawab", -300, 960, 1.5, walks=[(sw - 1.5, 820)], speed=2.0, acts=[(sw + 0.4, "celebrate", None)]),
                      *FX.people(BEN, ["sepoy"] * 4, -900, 1000, 140, 1.2, walk=(sw - 1.6, 900), speed=2.0),
                      P("pike", 1500, G, 1.8, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]), P("penny", 1780, G + 10, 1.6, flip=True)],
                     L, world=BEN, fx=[label("CALCUTTA · JUNE 1756", 420, 110, 0.3, 60), caption("the Nawab takes Calcutta", sw + 0.6)]))
    # ---- 6. Clive and the secret deal
    L = ["E32"]
    out.append(scene("s07_clive", "plate:ocean", [E(BEN, "clive", 1100, 1000, 1.7, flip=True, faces=[(0, {"mouth": "smirk"})]), P("penny", 1720, G, 1.6, flip=True)],
                     L, follow=False, world=BEN, fx=[label("CLIVE'S SOLDIERS · WATSON'S FLEET", 760, 110, 1.0, 56, GOLD)]))
    L = ["E33"]
    sw = at(L, 0) + 2.4
    out.append(scene("s07_retake", "plate:e_calcutta",
                     [E(BEN, "clive", -250, 1000, 1.6, speed=2.2, walks=[(sw - 2.0, 760)], acts=[(sw + 0.2, "point", None)]),
                      *FX.people(BEN, ["csepoy", "redcoat", "csepoy"], -800, 1010, 150, 1.3, walk=(sw - 2.1, 900), speed=2.2), P("quill", 1720, G, 1.7, flip=True)],
                     L, world=BEN, fx=[label("2 JANUARY 1757", 400, 110, 0.4, 64, GOLD), caption("Clive and Watson retake Calcutta", sw + 0.4)]))
    L = ["E34"]
    out.append(scene("s07_plotters", "plate:e_murshidabad",
                     [E(BEN, "mir_jafar", 700, 1000, 1.6, faces=[(0, {"mouth": "smirk", "brows": -0.4})], acts=[(1.4, "think", None)]),
                      E(BEN, "jagat_seth", 1100, 1000, 1.5, flip=True, faces=[(0, {"mouth": "smirk"})]), P("penny", 1720, G, 1.5, flip=True)],
                     L, follow=False, world=BEN, fx=[label("MIR JAFAR", 700, 300, dur("E34") * 0.45, 52), label("THE JAGAT SETH BANKERS", 1100, 300, dur("E34") * 0.7, 46)]))
    L = ["E35", "E36"]
    out.append(scene("s07_deal", "plate:e_murshidabad",
                     [E(BEN, "mir_jafar", 520, 1000, 1.7, faces=[(0, {"mouth": "smirk"})]), E(BEN, "clive", 1050, 1000, 1.7, flip=True, faces=[(0, {"mouth": "smirk"})]),
                      P("zed", 1450, G, 1.6, flip=True), P("penny", 1760, G + 10, 1.6, flip=True)],
                     L, world=BEN, fx=[label("SECRET AGREEMENT · JUNE 1757", 960, 90, 0.4, 60, GOLD)], under=[K.PL_contract(800, 1010, at(L, 1) + 0.5, at(L, 1) + 4.0)]))
    L = ["E37", "E38"]
    out.append(scene("s07_bought", "plate:e_murshidabad", [P("pike", 1300, G, 1.9, flip=True, faces=[(0, {"brows": 1.0, "mouth": "worried"})]), P("penny", 1700, G, 1.6, flip=True)],
                     L, follow=False, world=BEN))
    # ---- 7. Plassey
    L = ["E39"]
    out.append(scene("s08_plassey", "plate:e_plassey",
                     [*FX.people(BEN, ["redcoat"] * 3 + ["csepoy"] * 5, 100, 780, 70, 0.6), *FX.people(BEN, ["sepoy"] * 12, 900, 740, 70, 0.55, flip=True),
                      P("penny", 1720, G, 1.6, flip=True)],
                     L, follow=False, world=BEN, fx=[label("PLASSEY · 23 JUNE 1757", 960, 100, 0.4, 76, GOLD)]))
    L = ["E40"]
    out.append(scene("s08_numbers", "card", [P("atlas", 1720, G, 1.6, flip=True)], L, follow=False, world=BEN, fx=[K.bars(3000, 50000, 0.6)]))
    L = ["E41", "E42"]
    out.append(scene("s08_rain", "plate:plassey_rain",
                     [P("pike", 520, 1040, 1.9, faces=[(0, {"brows": 1.0, "mouth": "worried"})], acts=[(0.3, "cower", 1.0)])], L, world=BEN,
                     under=[K.PL_cannon(330, 1000, False), K.PL_tarp(470, 1060, 640, 0.5), K.PL_cannon(1500, 900, True, fire_at=(0.4, 1.3), fizzle_after=2.0),
                            K.PL_cannon(1760, 960, True, fire_at=(0.8,), fizzle_after=2.0)],
                     fx=[K.PL_rain, label("the Nawab's guns fall silent", 1450, 160, 2.6, 52)]))
    L = ["E43", "E44"]
    sit = at(L, 0) + 1.2
    out.append(scene("s08_betrayal", "plate:e_plassey",
                     [*FX.people(BEN, ["sepoy"] * 7, 800, 900, 105, 0.85, flip=True, acts=[(sit, "sit", None)]),
                      E(BEN, "mir_jafar", 1180, 1000, 1.5, flip=True, faces=[(0, {"mouth": "smirk"})], acts=[(sit - 0.2, "fold", None)]),
                      E(BEN, "nawab", 560, 1000, 1.5, acts=[(at(L, 1) - 0.2, "double_take", 0.0)], walks=[(at(L, 1) + 1.2, -400)], speed=2.4),
                      P("quill", 1720, G, 1.7, flip=True)],
                     L, world=BEN, fx=[label("MIR JAFAR", 1180, 560, 0.4, 52)]))
    # ---- 8. political power
    L = ["E45", "E46"]
    out.append(scene("s09_throne", "plate:e_murshidabad",
                     [E(BEN, "mir_jafar", 960, 1000, 1.7, faces=[(0, {"mouth": "grin"}), (at(L, 1), {"brows": 1.0, "mouth": "worried"})]),
                      P("zed", 1700, G, 1.7, flip=True)],
                     L, follow=False, world=BEN, fx=[K.PL_crown(960, 560, 0.2), caption("the Company: money, rulers and an army", at(L, 1) + 0.6)]))
    L = ["E47"]
    out.append(scene("s09_buxar", "plate:e_plassey",
                     [*FX.people(BEN, ["redcoat"] * 3 + ["csepoy"] * 4, 120, 800, 75, 0.6), *FX.people(BEN, ["sepoy"] * 10, 950, 760, 75, 0.55, flip=True),
                      P("penny", 1720, G, 1.5, flip=True)],
                     L, follow=False, world=BEN, fx=[label("BUXAR · 1764", 960, 100, 0.4, 76, GOLD),
                                                     label("Mir Qasim + Awadh + the Mughal emperor", 1150, 520, dur("E47") * 0.55, 46)]))
    L = ["E48"]
    out.append(scene("s09_diwani", "plate:e_allahabad",
                     [E(BEN, "shah_alam", 960, 880, 1.5, faces=[(0, {"mouth": "smile"})], acts=[(1.0, "present", None)]),
                      E(BEN, "clive", 560, 1000, 1.6, faces=[(0, {"mouth": "grin"})], acts=[(1.6, "nod", 0.0)]), P("quill", 1720, G, 1.6, flip=True)],
                     L, world=BEN, under=[table_throne(0.0)],
                     fx=[label("ALLAHABAD · AUGUST 1765 · THE DIWANI", 960, 90, 0.4, 54, GOLD),
                         caption("the right to collect the revenues of Bengal, Bihar and Orissa", 3.0)]))
    L = ["E49", "E50"]
    out.append(scene("s09_tax", "plate:e_allahabad", [P("zed", 1300, G, 1.8, flip=True), P("penny", 1700, G, 1.6, flip=True)], L, world=BEN,
                     fx=[K.coins_flow(300, 700, 1100, 760, 0.3, at(L, 1) + 2)]))
    # ---- 9. what happened next
    L = ["E51"]
    out.append(scene("s10_century", "card", [P("penny", 1720, G, 1.6, flip=True)], L, follow=False, world=BEN,
                     fx=[timeline([("1757", "Plassey:|Bengal"), ("1764–65", "Buxar and|the diwani"), ("1818–56", "most of the|subcontinent")], 0.5, 2.2)]))
    L = ["E52"]
    out.append(scene("s10_end", "card", [P("quill", 1720, G, 1.6, flip=True)], L, follow=False, world=BEN,
                     fx=[timeline([("1857–58", "great uprising;|Crown takes over"), ("1874", "Company|dissolved")], 0.5, 2.6)]))
    # ---- ending: payoff, then the tease
    L = ["E53"]
    out.append(scene("s11_payoff", "plate:e_hooghly", [P("atlas", 1700, G, 1.7, flip=True)], L, follow=False, world=BEN,
                     cam=[(0.0, 1.15, 0.4, 0.5), (5.0, 1.0, 0.5, 0.5)], fx=[caption("from spices... to an empire... to closing down", 0.4)]))
    L = ["E54"]
    a_ = scene("s11_outro", "plate:e_hooghly",
               [P(k, 300 + i * 330, G, 1.6, flip=i > 2, faces=[(0, {"mouth": "grin"})], acts=[(0.4 + i * 0.12, "cheer", None)])
                for i, k in enumerate(["atlas", "penny", "quill", "zed", "pike"])], L, lead=0.2, follow=False, world=BEN)
    out += split(a_, 2.4, "plate:india", fx=[FX.next_time(0.3, "THE LOST CITIES OF THE INDUS")], name="s11_next")
    out[-1].dur += 0.8
    out.append(Shot("s12_endcard", 3.5, "endcard", world=BEN,
                    actors=[P(k, 360 + i * 300, 1030, 1.4, acts=[(0.3 + i * 0.12, "cheer" if k != "quill" else "hold_up", None)])
                            for i, k in enumerate(["penny", "atlas", "quill", "zed", "pike"])]))
    return out


K.shots = shots

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if cmd == "preview":
        K.preview(Path(sys.argv[2]) if len(sys.argv) > 2 else Path("D:/Temp/cartoon/ep01/preview_eic.png"))
    elif cmd == "render":
        K.render(tuple(int(x) for x in sys.argv[2].split("/")), Path(sys.argv[3]) if len(sys.argv) > 3 else Path("D:/Temp/cartoon/ep01/shots"))
    elif cmd == "mix":
        K.mix(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]) if len(sys.argv) > 4 else Path("D:/Temp/cartoon/sneaky_snitch.mp3"))
