"""Maps, charts and diagrams for "The Three Gorges Dam Was Built to Stop Floods. Did It?"

  python scripts/gorges_visuals.py [name ...]      (all when no names); output dir: env YTG_CABLES_VISUALS

Engine: cables_visuals.py (Natural Earth basemap, pins, glowing routes, counter cards). Rivers and lakes: Natural Earth
1:10m (public domain). Every figure on screen is from data/research/three_gorges/script_v2.md claim table (fact-checked
20 Nov 2026). State/operator figures are labelled as such.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cables_visuals import (CABLE, H, HILITE, NE, TEXT, W, WARN, Frame, ImageDraw, basemap, card_frames, chrome,  # noqa: E402
                            counter_card, draw_route, ease, font, pin, render, zoomed)

MUTED = "#c9d6e2"
WATER = "#38c6f4"
DAM = (111.003, 30.823)
CHONGQING, YICHANG, WUHAN, SHANGHAI, NANJING = (106.55, 29.56), (111.29, 30.69), (114.30, 30.59), (121.47, 31.23), (118.78, 32.06)
SOURCE = (98.54, 31.69)                  # where the Natural Earth line begins (Jinsha, coming off the Tibetan Plateau)
MOUTH = (121.78, 31.42)
CASCADE = [("Wudongde", 102.62, 26.33), ("Baihetan", 102.90, 27.22), ("Xiluodu", 103.65, 28.26), ("Xiangjiaba", 104.40, 28.64)]


def _shapes(layer, names):
    import shapefile
    rd = shapefile.Reader(str(next((NE / layer).glob("*.shp"))))
    fields = [f[0] for f in rd.fields[1:]]
    out = []
    for rec, sh in zip(rd.records(), rd.shapes()):
        d = dict(zip(fields, rec))
        if names is None or d.get("name") in names or d.get("name_en") in names:
            pts, parts = sh.points, list(sh.parts) + [len(sh.points)]
            for a, b in zip(parts, parts[1:]):
                out.append((d.get("name"), [tuple(p) for p in pts[a:b]]))
    return out


def yangtze_line():
    """One west->east polyline: Jinsha + Chang Jiang + lower Yangtze (Natural Earth), extended to the mouth."""
    segs = [s for _, s in _shapes("ne_10m_rivers_lake_centerlines", {"Jinsha", "Chang Jiang", "Yangtze"}) if len(s) >= 5]
    segs = [s if s[0][0] < s[-1][0] else s[::-1] for s in segs]
    segs.sort(key=lambda s: s[0][0])
    line = []
    for s in segs:
        line += s
    line += [(120.3, 31.95), (121.0, 31.72), MOUTH]          # Jiangyin -> the mouth (NE line ends near Zhenjiang)
    return line


def tributaries():
    return _shapes("ne_10m_rivers_lake_centerlines", {"Han", "Xiang", "Gan", "Yuan", "Jialing", "Wu", "Yalong", "Min"})


def lakes(bbox):
    lon0, lat0, lon1, lat1 = bbox
    return [ring for _, ring in _shapes("ne_10m_lakes", None)
            if any(lon0 <= x <= lon1 and lat0 <= y <= lat1 for x, y in ring[::5])]


def draw_poly(d, f, ring, fill, outline=None):
    d.polygon([f.xy(x, y) for x, y in ring], fill=fill, outline=outline)


def draw_line(d, f, pts, color, width):
    d.line([f.xy(x, y) for x, y in pts], fill=color, width=width, joint="curve")


def dam_mark(d, f, alpha=1.0, label=True, side="r"):
    x, y = f.xy(*DAM)
    a = int(255 * alpha)
    d.rectangle([x - 4, y - 16, x + 4, y + 16], fill="#ffffff" + f"{a:02x}")
    if label:
        pin(d, f, DAM[0], DAM[1] + 0.0001, "Three Gorges Dam", alpha * 0.999, color="#ffffffff", side=side)


# ------------------------------------------------------------------------------------------------ maps
def map_yangtze(name="map_yangtze", dur=14.0):
    fr = Frame((86, 22, 124, 38))
    base = basemap(fr)
    river = yangtze_line()

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_route(layer, f, river, ease((t - 0.6) / 5.0), color=HILITE, width=6, head=False)
        pin(d, f, *SOURCE, "from the\nTibetan Plateau", min(1, t / 0.8), side="l")
        if t > 3.2:
            pin(d, f, *CHONGQING, "Chongqing", min(1, (t - 3.2) / 0.6), side="l")
        if t > 4.0:
            dam_mark(d, f, min(1, (t - 4.0) / 0.6), label=True, side="l")
        if t > 4.8:
            pin(d, f, *WUHAN, "Wuhan", min(1, (t - 4.8) / 0.6), side="r")
        if t > 5.6:
            pin(d, f, *SHANGHAI, "Shanghai", min(1, (t - 5.6) / 0.6), side="l")
        if t > 6.4:
            a = int(255 * min(1, (t - 6.4) / 0.8))
            d.text((W / 2, 110), "The Yangtze: about 6,300 km", font=font(52, "b"), fill=TEXT[:7] + f"{a:02x}", anchor="mm")
            d.text((W / 2, 172), "third-longest river on Earth, after the Nile and the Amazon", font=font(32), fill=MUTED + f"{a:02x}", anchor="mm")
        chrome(d, "", "", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.05))


def map_reservoir(name="map_reservoir", dur=13.0):
    fr = Frame((104.8, 28.2, 113.2, 32.2))
    base = basemap(fr)
    river = [p for p in yangtze_line() if 104 < p[0] < 114]
    res = [p for p in river if CHONGQING[0] - 0.05 <= p[0] <= DAM[0]]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_line(d, f, river, "#7f99b3ff", 4)
        draw_route(layer, f, res[::-1], ease((t - 1.0) / 3.5), color=WATER + "ff", width=12, head=False)
        dam_mark(d, f, min(1, t / 0.8), label=True, side="r")
        pin(d, f, *CHONGQING, "Chongqing", min(1, t / 0.8), side="l")
        if t > 4.6:
            a = int(255 * min(1, (t - 4.6) / 0.8))
            d.text((W / 2, H - 150), "The reservoir: more than 600 km long", font=font(48, "b"), fill=TEXT[:7] + f"{a:02x}", anchor="mm")
            d.text((W / 2, H - 92), "water held at up to 175 m above sea level", font=font(32), fill=MUTED + f"{a:02x}", anchor="mm")
        chrome(d, "", "", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.04))


def map_rain_below(name="map_rain_below", dur=16.0):
    """1998: the rivers joining BELOW the dam carried more than twice the water that came from above it."""
    bbox = (104.0, 26.0, 122.5, 33.8)
    fr = Frame(bbox)
    base = basemap(fr)
    river = yangtze_line()
    tribs = tributaries()
    lk = lakes(bbox)
    below = [(111.4, 32.9), (113.2, 33.3), (115.4, 32.6), (117.4, 31.2), (118.0, 29.6), (117.4, 27.4), (115.6, 26.0),
             (113.6, 25.6), (111.6, 26.2), (110.0, 27.6), (110.4, 29.4), (111.2, 30.6)]   # middle basin below the dam (schematic)

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        if t > 3.0:
            a = int(60 * min(1, (t - 3.0) / 1.0))
            draw_poly(d, f, below, "#5b8cff" + f"{a:02x}")
        for _, s in tribs:
            draw_line(d, f, s, "#7fa6c8" + f"{int(200 * min(1, t / 1.0)):02x}", 3)
        for ring in lk:
            draw_poly(d, f, ring, WATER + "ff")
        draw_route(layer, f, river, 1.0, color=HILITE, width=7, head=False)
        dam_mark(d, f, 1.0, label=True, side="l")
        if t > 1.2:
            a = min(1, (t - 1.2) / 0.6)
            pin(d, f, 112.9, 29.3, "Dongting Lake", a, color=WATER + "ff", side="l", size=26)
            d.text(f.xy(114.3, 27.2), "the middle basin,\nbelow the dam", font=font(30, "b"), fill="#dfe8ff" + f"{int(255 * a):02x}", anchor="mm", align="center")
            pin(d, f, 116.2, 29.1, "Poyang Lake", a, color=WATER + "ff", side="r", size=26)
            pin(d, f, 112.6, 32.4, "Han River", a, color="#7fa6c8ff", side="r", size=26)
        if t > 4.5:
            a = int(255 * min(1, (t - 4.5) / 0.8))
            d.text((W / 2, 96), "1998: below the dam, the joining rivers carried", font=font(44, "b"), fill=TEXT[:7] + f"{a:02x}", anchor="mm")
            d.text((W / 2, 156), "more than twice the water that came from above it", font=font(44, "b"), fill=HILITE[:7] + f"{a:02x}", anchor="mm")
        chrome(d, "", "schematic", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.04))


def map_cascade(name="map_cascade", dur=13.0):
    fr = Frame((99.5, 24.5, 113.5, 33.0))
    base = basemap(fr)
    river = [p for p in yangtze_line() if 98 < p[0] < 114]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_route(layer, f, river, 1.0, color=HILITE, width=6, head=False)
        dam_mark(d, f, 1.0, label=True, side="l")
        for i, (nm, lo, la) in enumerate(CASCADE):
            if t > 1.0 + i * 0.8:
                lab = nm + ("\n16 GW: second-largest hydro plant" if nm == "Baihetan" else "")
                pin(d, f, lo, la, lab, min(1, (t - 1.0 - i * 0.8) / 0.6), side="r" if i % 2 else "l", size=28)
        if t > 5.0:
            a = int(255 * min(1, (t - 5.0) / 0.8))
            d.text((W / 2, 100), "Four more giant dams upstream", font=font(50, "b"), fill=TEXT[:7] + f"{a:02x}", anchor="mm")
        chrome(d, "", "", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.04))


# ------------------------------------------------------------------------------------------------ cards
def bars(name, dur, title, sub, rows, unit_fn, vmax, foot=""):
    """rows: [(label, value, colour)]"""
    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        d.text((160, 120), title, font=font(56, "b"), fill=TEXT + f"{a:02x}")
        if sub:
            d.text((160, 196), sub, font=font(32), fill=MUTED + f"{a:02x}")
        x0, maxw = 640, 1000
        for i, (label, v, col) in enumerate(rows):
            y = 330 + i * 150
            g = ease((t - 0.8 - i * 0.5) / 1.2)
            d.multiline_text((160, y + 4), label, font=font(36, "b"), fill=TEXT + f"{a:02x}", spacing=4)
            wpx = max(6, maxw * v / vmax * g)
            d.rounded_rectangle([x0, y, x0 + wpx, y + 70], radius=6, fill=col + f"{a:02x}")
            if g > 0.05:
                d.text((x0 + wpx + 24, y + 12), unit_fn(v * g), font=font(40, "b"), fill=TEXT + f"{a:02x}")
        if foot:
            d.text((160, H - 110), foot, font=font(26), fill=MUTED + f"{a:02x}")
    card_frames(name, dur, fn)


def timeline6(name, dur, events, title="", shown=None, already=0, margin=None):
    """Timeline card. shown = how many events are on this card (rest hidden); the first `already` appear at once
    (they were revealed on an earlier card), the rest animate in. margin keeps edge labels inside the frame."""
    n_all = len(events)
    shown = shown or n_all
    margin = margin if margin is not None else (330 if n_all <= 3 else 190)

    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        if title:
            d.text((W / 2, 130), title, font=font(52, "b"), fill=TEXT + f"{a:02x}", anchor="mm")
        y = H * 0.48
        span = W - 2 * margin
        step = span / (n_all - 1)
        done = (already - 1) / (n_all - 1) if already else 0.0
        target = (shown - 1) / (n_all - 1)
        g = done + (target - done) * ease((t - 0.4) / (1.0 + 0.9 * (shown - already)))
        d.line([(margin, y), (margin + span * g, y)], fill="#5d7690" + f"{a:02x}", width=4)
        for i, (yr, l1, l2) in enumerate(events[:shown]):
            x = margin + i * step
            b = a if i < already else int(a * ease((t - 0.8 - (i - already) * 0.9) / 0.6))
            if b <= 0:
                continue
            d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=HILITE + f"{b:02x}")
            d.text((x, y - 70), yr, font=font(56, "b"), fill=HILITE + f"{b:02x}", anchor="mm")
            d.multiline_text((x, y + 40), l1 + ("\n" + l2 if l2 else ""), font=font(27), fill=TEXT + f"{b:02x}", anchor="ma",
                             align="center", spacing=6)
    card_frames(name, dur, fn)


ARGUMENT = [("1919", "Sun Yat-sen", "imagines a dam"),
            ("1944", "US engineer", "John Savage surveys"),
            ("1956", "Mao's poem:", "'walls of stone'"),
            ("1970", "Gezhouba approved", "as a rehearsal"),
            ("1988", "Canada-World Bank", "study"),
            ("1992", "the vote", "")]


def floods_card(name="chart_floods", dur=13.0):
    timeline6(name, dur, [("1931", "hundreds of thousands dead", "estimates run into the millions"),
                          ("1954", "about 30,000 dead", ""),
                          ("1998", "more than 3,000 dead", "about 15 million homeless")], title="The Yangtze's great floods")


def argument_card(name="chart_argument", dur=16.0):
    timeline6(name, dur, [("1919", "Sun Yat-sen", "imagines a dam"),
                          ("1944", "US engineer", "John Savage surveys"),
                          ("1956", "Mao's poem:", "'walls of stone'"),
                          ("1970", "Gezhouba approved", "as a rehearsal"),
                          ("1988", "Canada-World Bank", "study"),
                          ("1992", "the vote", "")], title="An eighty-year argument")


def vote_card(name="chart_vote", dur=12.0):
    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        d.text((W / 2, 170), "National People's Congress, 3 April 1992", font=font(52, "b"), fill=TEXT + f"{a:02x}", anchor="mm")
        g = ease((t - 0.8) / 1.8)
        x0, y0, w, h = 160, 420, 1600, 150
        yes = 1767 / 2633
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=10, fill="#22384f" + f"{a:02x}")
        d.rounded_rectangle([x0, y0, x0 + w * yes * g, y0 + h], radius=10, fill=CABLE + f"{a:02x}")
        if g > 0.7:
            b = int(a * min(1, (g - 0.7) / 0.3))
            d.text((x0 + 36, y0 + 40), "1,767 voted yes", font=font(50, "b"), fill="#06202b" + f"{b:02x}")
            d.text((x0 + w * yes + 30, y0 + 22), "about a third", font=font(42, "b"), fill=HILITE + f"{b:02x}")
            d.text((x0 + w * yes + 30, y0 + 80), "against, abstained or no vote", font=font(28), fill=TEXT + f"{b:02x}")
            d.text((W / 2, y0 + h + 110), "an unusually divided vote for a parliament that almost never says no", font=font(34), fill=MUTED + f"{b:02x}", anchor="mm")
    card_frames(name, dur, fn)


def locks_diagram(name="diagram_locks", dur=14.0):
    """Five-step staircase, 113 m in all, vs the ship lift (one step)."""
    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        d.text((W / 2, 110), "Getting ships past the dam", font=font(54, "b"), fill=TEXT + f"{a:02x}", anchor="mm")
        base_y, top_y = 900, 420
        x0, stepw = 180, 200
        for i in range(5):                                       # chambers, water rising step by step
            yb = base_y - i * (base_y - top_y) / 5
            d.rectangle([x0 + i * stepw, yb - 90, x0 + (i + 1) * stepw - 10, yb], outline="#7f99b3" + f"{a:02x}", width=4,
                        fill="#123352" + f"{a:02x}")
        k = ease((t - 1.5) / 6.0) * 4.999                          # a ship climbs
        i = int(k)
        yb = base_y - k * (base_y - top_y) / 5
        sx = x0 + i * stepw + 40 + (k - i) * 60
        d.polygon([(sx, yb - 30), (sx + 110, yb - 30), (sx + 95, yb - 8), (sx + 12, yb - 8)], fill=HILITE + f"{a:02x}")
        d.text((x0 + 500, base_y + 50), "five-step locks: 113 m, three to four hours", font=font(36, "b"), fill=TEXT + f"{a:02x}", anchor="mm")
        if t > 6.5:                                               # the lift
            b = int(a * min(1, (t - 6.5) / 0.6))
            lx = 1400
            d.rectangle([lx, top_y - 90, lx + 240, base_y], outline="#7f99b3" + f"{b:02x}", width=4)
            g = ease((t - 7.0) / 3.0)
            ly = base_y - g * (base_y - top_y)
            d.rectangle([lx + 20, ly - 70, lx + 220, ly], fill="#123352" + f"{b:02x}", outline=WATER + f"{b:02x}", width=3)
            d.polygon([(lx + 60, ly - 40), (lx + 170, ly - 40), (lx + 155, ly - 18), (lx + 72, ly - 18)], fill=HILITE + f"{b:02x}")
            d.text((lx + 120, base_y + 50), "ship lift: about 8 minutes", font=font(36, "b"), fill=TEXT + f"{b:02x}", anchor="mm")
            d.text((lx + 120, base_y + 100), "ships up to 3,000 tonnes", font=font(28), fill=MUTED + f"{b:02x}", anchor="mm")
        d.text((1700, 1030), "Simplified, not to scale", font=font(22), fill=MUTED + f"{int(a * 0.8):02x}", anchor="mm")
    card_frames(name, dur, fn)


def drowned_card(name="chart_drowned", dur=12.0):
    items = [("13", "cities"), ("140", "towns"), ("1,350", "villages")]

    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        d.text((W / 2, 200), "Covered by the reservoir, in whole or in part", font=font(48, "b"), fill=TEXT + f"{a:02x}", anchor="mm")
        for i, (n, lab) in enumerate(items):
            b = int(a * ease((t - 0.9 - i * 0.7) / 0.6))
            if b <= 0:
                continue
            x = 400 + i * 560
            d.text((x, 520), n, font=font(150, "b"), fill=HILITE + f"{b:02x}", anchor="mm")
            d.text((x, 640), lab, font=font(48, "b"), fill=TEXT + f"{b:02x}", anchor="mm")
    card_frames(name, dur, fn)


ALL = {
    "map_yangtze": map_yangtze,
    "map_reservoir": map_reservoir,
    "map_rain_below": map_rain_below,
    "map_cascade": map_cascade,
    "chart_floods": floods_card,
    "chart_argument_1": lambda: timeline6("chart_argument_1", 9.0, ARGUMENT, "An eighty-year argument", shown=2),
    "chart_argument_2": lambda: timeline6("chart_argument_2", 9.0, ARGUMENT, "An eighty-year argument", shown=4, already=2),
    "chart_argument_3": lambda: timeline6("chart_argument_3", 9.0, ARGUMENT, "An eighty-year argument", shown=6, already=4),
    "chart_vote": vote_card,
    "diagram_locks": locks_diagram,
    "chart_drowned": drowned_card,
    "chart_size": lambda: counter_card("chart_size", 9.0, lambda g: f"{181 * g:.0f} m high", "about 2.3 km long",
                                       "one of the largest concrete structures ever built", ""),
    "chart_power": lambda: counter_card("chart_power", 9.0, lambda g: f"{22.5 * g:.1f} GW", "the largest power station on Earth",
                                        "32 main turbines of 700 MW, plus two small ones", ""),
    "chart_record": lambda: counter_card("chart_record", 9.0, lambda g: f"{111.8 * g:.1f} TWh", "generated in 2020",
                                         "a world record for a single plant (operator figure)", ""),
    "chart_moved": lambda: counter_card("chart_moved", 9.0, lambda g: f"{1.31 * g:.2f} million", "people moved",
                                        "official final count; the plan said 1.13 million", ""),
    "chart_cost": lambda: bars("chart_cost", 11.0, "What did it cost?", "Depends on what you count",
                               [("Official\nestimate", 31.8, CABLE), ("Reuters\n(2012)", 59.0, HILITE)], lambda v: f"${v:.0f} bn", 62),
    "chart_flood2020": lambda: bars("chart_flood2020", 12.0, "20 August 2020: the biggest flood peak since the dam was built",
                                    "cubic metres per second (official Chinese figures)",
                                    [("Into the\nreservoir", 75000, WARN), ("Let through\nthe dam", 49400, CABLE)],
                                    lambda v: f"{v:,.0f}", 80000),
    "chart_sediment": lambda: bars("chart_sediment", 13.0, "Mud carried down the lower Yangtze", "million tonnes a year, at Datong (Yang et al. 2015)",
                                   [("1950-1968", 507, "#8a6a44"), ("1993-2002", 320, "#8a6a44"), ("2003-2012", 145, HILITE)],
                                   lambda v: f"{v:.0f}", 540, foot="About 80% of the mud from upstream now settles behind the dam"),
    "chart_day": lambda: counter_card("chart_day", 9.0, lambda g: f"{0.06 * g:.2f} µs", "longer day, calculated",
                                      "NASA geophysicist's estimate for this much water: real, but far too small to notice", ""),
}

if __name__ == "__main__":
    for n in sys.argv[1:] or list(ALL):
        ALL[n]()
