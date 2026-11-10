"""Maps, counters and the vault diagram for "The Arctic Island That Backs Up Civilization" (Svalbard).

  python scripts/svalbard_visuals.py [name ...]      (all when no names); output dir: env YTG_CABLES_VISUALS

Reuses the cables film's map engine (cables_visuals.py): Natural Earth basemap, pins, routes, counter cards. Every figure on
screen is from projects/svalbard-full/research (two sources each). Routes are schematic.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cables_visuals import (CABLE, H, HILITE, TEXT, W, Frame, ImageDraw, basemap, card_frames, chrome, counter_card,  # noqa: E402
                            draw_route, ease, font, pin, render, zoomed)

LYR = (15.63, 78.22)          # Longyearbyen
ANDOYA = (16.05, 69.30)
HARSTAD = (16.54, 68.80)
BODO = (14.40, 67.28)
JAN_MAYEN = (-8.47, 70.98)
ALEPPO = (37.16, 36.20)
LEBANON = (35.90, 33.85)      # ICARDA, Terbol (Beqaa valley)
MOROCCO = (-6.84, 34.02)      # Rabat
OSLO = (10.75, 59.91)
POLE = (15.0, 89.0)           # drawn near the top edge of a polar-ish frame


def svalbard_location(name="map_svalbard_location", dur=12.0):
    fr = Frame((-12, 56, 42, 84))
    base = basemap(fr)

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        pin(d, f, *OSLO, "Oslo", min(1, t / 0.8), side="l")
        if t > 1.2:
            pin(d, f, *LYR, "Longyearbyen", min(1, (t - 1.2) / 0.8))
        if t > 2.6:
            a = int(255 * min(1, (t - 2.6) / 0.8))
            x, y = f.xy(15.6, 78.2)
            d.text((x + 40, y + 46), "78° N", font=font(44, "b"), fill=HILITE[:7] + f"{a:02x}")
        if t > 4.0:
            a = int(255 * min(1, (t - 4.0) / 0.8))
            d.text((W / 2, 110), "Roughly halfway between mainland Norway and the North Pole", font=font(36),
                   fill=TEXT[:7] + f"{a:02x}", anchor="mm")
        chrome(d, "", "", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.08))


def aleppo_withdrawal(name="map_aleppo_withdrawal", dur=14.0):
    fr = Frame((-16, 24, 48, 86))
    base = basemap(fr)
    r_leb = [LYR, (20.0, 60.0), (30.0, 45.0), LEBANON]
    r_mor = [LYR, (5.0, 60.0), (-6.0, 45.0), MOROCCO]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        pin(d, f, *ALEPPO, "Aleppo, Syria", min(1, t / 0.8), color="#e05a4fff")
        pin(d, f, *LYR, "Svalbard", min(1, t / 0.8))
        if t > 1.5:
            draw_route(layer, f, r_leb, ease((t - 1.5) / 2.5), color=HILITE, width=5)
            draw_route(layer, f, r_mor, ease((t - 1.8) / 2.5), color=HILITE, width=5)
        if t > 4.0:
            pin(d, f, *LEBANON, "Lebanon", min(1, (t - 4.0) / 0.6), side="r")
            pin(d, f, *MOROCCO, "Morocco", min(1, (t - 4.0) / 0.6), side="l")
        if t > 5.5:
            a = int(255 * min(1, (t - 5.5) / 0.6))
            d.text((W / 2, 110), "September 2015: more than 38,000 samples withdrawn", font=font(40, "b"),
                   fill=TEXT[:7] + f"{a:02x}", anchor="mm")
        chrome(d, "", "Routes simplified", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.05))


def svalbard_cables(name="map_svalbard_cables", dur=14.0):
    fr = Frame((-14, 64, 34, 81))
    base = basemap(fr)
    c1 = [LYR, (13.8, 76.0), (13.6, 72.5), (15.2, 70.2), ANDOYA, HARSTAD]
    c2 = [LYR, (16.6, 76.0), (17.2, 72.5), (17.0, 70.2), (16.6, 69.25), HARSTAD]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        pin(d, f, *LYR, "Longyearbyen", min(1, t / 0.8))
        pin(d, f, *HARSTAD, "Mainland Norway", min(1, t / 0.8), side="l")
        draw_route(layer, f, c1, ease((t - 0.8) / 3.0), color=CABLE, width=5)
        draw_route(layer, f, c2, ease((t - 1.1) / 3.0), color=CABLE, width=5)
        if t > 4.2:
            a = int(255 * min(1, (t - 4.2) / 0.6))
            d.text((W / 2, H - 150), "Two cables, about 1,400 km each, laid in 2003", font=font(42, "b"),
                   fill=TEXT[:7] + f"{a:02x}", anchor="mm")
            d.text((W / 2, H - 100), "as deep as 2,700 metres", font=font(32), fill="#c9d6e2" + f"{a:02x}", anchor="mm")
        chrome(d, "", "Routes simplified", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.05))


def arctic_way(name="map_arctic_way", dur=14.0):
    fr = Frame((-20, 64, 34, 81))
    base = basemap(fr)
    old = [LYR, (15.0, 74.0), ANDOYA, HARSTAD]
    new = [BODO, (0.0, 68.5), JAN_MAYEN, (5.0, 76.0), LYR]

    def fn(t, layer, z):
        f = zoomed(fr, z)
        d = ImageDraw.Draw(layer)
        draw_route(layer, f, old, 1.0, color="#6f8fa8ff", width=4, head=False)
        pin(d, f, *LYR, "Svalbard", min(1, t / 0.8))
        pin(d, f, *BODO, "Bodø", min(1, t / 0.8), side="l")
        draw_route(layer, f, new, ease((t - 1.0) / 3.5), color=HILITE, width=6)
        if t > 2.6:
            pin(d, f, *JAN_MAYEN, "Jan Mayen", min(1, (t - 2.6) / 0.6), side="l")
        if t > 4.8:
            a = int(255 * min(1, (t - 4.8) / 0.6))
            d.text((W / 2, H - 150), "Arctic Way: about 2,350 km, due 2028", font=font(44, "b"), fill=TEXT[:7] + f"{a:02x}", anchor="mm")
            d.text((W / 2, H - 100), "the old cables stay as backup", font=font(32), fill="#c9d6e2" + f"{a:02x}", anchor="mm")
        chrome(d, "", "Routes simplified", t, dur)
    render(name, dur, fn, base, zoom=(1.0, 1.05))


def vault_section(name="diagram_vault", dur=14.0):
    """Side view of the mountain: entrance at ~130 m above sea level, tunnel more than 100 m in, three halls at -18 C."""
    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        sea_y, ground = 900, [(0, 900), (260, 860), (520, 700), (900, 470), (1250, 300), (1600, 330), (1920, 420)]
        d.polygon(ground + [(1920, 1080), (0, 1080)], fill="#2b3a4a" + f"{a:02x}")
        d.line(ground, fill="#9fb3c6" + f"{a:02x}", width=4)
        d.rectangle([0, sea_y, 260, 1080], fill="#123352" + f"{a:02x}")
        ex, ey = 520, 700                                         # entrance on the slope
        g = ease((t - 1.0) / 2.0)                                 # tunnel grows into the rock
        tx = ex + int(560 * g)
        d.rectangle([ex, ey - 26, tx, ey + 4], fill="#d8e3ec" + f"{a:02x}")
        if t > 3.0:
            b = int(255 * min(1, (t - 3.0) / 0.6))
            for i in range(3):                                    # three halls
                x0 = 1080 + i * 150
                d.rectangle([x0, ey - 70, x0 + 120, ey + 30], outline=HILITE[:7] + f"{b:02x}", width=5, fill="#1d4c6e" + f"{b // 2:02x}")
            d.text((1305, ey - 120), "three halls, −18 °C", font=font(50, "b"), fill=TEXT[:7] + f"{b:02x}", anchor="mm")
        if t > 4.5:
            b = int(255 * min(1, (t - 4.5) / 0.6))
            d.text((800, ey + 70), "tunnel: more than 100 m into the rock", font=font(40, "b"), fill="#c9d6e2" + f"{b:02x}", anchor="mm")
            d.line([(ex, ey + 40), (ex, sea_y)], fill="#9fb3c6" + f"{b:02x}", width=2)
            d.text((ex - 20, (ey + sea_y) / 2 + 20), "about 130 m\nabove sea level", font=font(38, "b"), fill="#c9d6e2" + f"{b:02x}", anchor="rm")
        if t > 6.0:
            b = int(255 * min(1, (t - 6.0) / 0.8))
            d.text((W / 2, 120), "If the power fails, the permafrost keeps the seeds frozen", font=font(40, "b"),
                   fill=TEXT[:7] + f"{b:02x}", anchor="mm")
        d.text((1700, 1030), "Simplified, not to scale", font=font(22), fill="#c9d6e2" + f"{int(a * 0.8):02x}", anchor="mm")
    card_frames(name, dur, fn)


def film_frame(name="diagram_archive_film", dur=12.0):
    """A strip of film whose frames fill with a QR-like data pattern (deterministic, our own graphic)."""
    import random
    rnd = random.Random(7)
    cells = [[rnd.random() > 0.5 for _ in range(24)] for _ in range(24)]

    def fn(t, d):
        a = int(255 * min(1, t / 0.6))
        y0, fh = 300, 480
        shift = int(t * 60) % 520
        d.rectangle([0, y0 - 60, W, y0 + fh + 60], fill="#1a1a1a" + f"{a:02x}")
        for k in range(-1, 5):                                   # sprocket holes + frames scrolling left
            x = k * 520 - shift + 120
            for hy in (y0 - 40, y0 + fh + 20):
                for j in range(6):
                    d.rectangle([x + j * 80, hy, x + j * 80 + 40, hy + 22], fill="#0a0a0a" + f"{a:02x}")
            d.rectangle([x, y0, x + 480, y0 + fh], fill="#f2efe6" + f"{a:02x}")
            c = 480 / 24
            for i in range(24):
                for j in range(24):
                    if cells[i][j] ^ ((k + i) % 3 == 0 and j % 5 == 0):
                        d.rectangle([x + j * c, y0 + i * c, x + (j + 1) * c - 1, y0 + (i + 1) * c - 1], fill="#111111" + f"{a:02x}")
        if t > 3.0:
            b = int(255 * min(1, (t - 3.0) / 0.6))
            d.text((W / 2, 140), "Data written on film as dense, QR-like patterns", font=font(44, "b"), fill=TEXT[:7] + f"{b:02x}", anchor="mm")
            d.text((W / 2, 940), "readable with light and a lens", font=font(34), fill="#c9d6e2" + f"{b:02x}", anchor="mm")
        d.text((1700, 1030), "Illustration", font=font(22), fill="#c9d6e2" + f"{int(a * 0.8):02x}", anchor="mm")
    card_frames(name, dur, fn)


ALL = {
    "map_svalbard_location": svalbard_location,
    "map_aleppo_withdrawal": aleppo_withdrawal,
    "map_svalbard_cables": svalbard_cables,
    "map_arctic_way": arctic_way,
    "diagram_vault": vault_section,
    "diagram_archive_film": film_frame,
    "chart_seed_samples": lambda: counter_card("chart_seed_samples", 9.0, lambda g: f"{1.4 * g:.1f} million",
                                               "seed samples stored", "room for 4.5 million", ""),
    "chart_warming": lambda: counter_card("chart_warming", 9.0, lambda g: f"{max(1, round(7 * g))}×",
                                          "faster warming than the global average", "Svalbard, since 1991", ""),
    "chart_code_vault": lambda: counter_card("chart_code_vault", 9.0, lambda g: f"{round(21 * g)} TB",
                                             "of open-source code, on 186 reels of film", "GitHub Arctic Code Vault, July 2020", ""),
    "chart_passes": lambda: counter_card("chart_passes", 9.0, lambda g: f"{round(14 * g)} passes a day",
                                         "of a polar-orbiting satellite, all visible from Svalbard", "", ""),
    "chart_trawler": lambda: counter_card("chart_trawler", 9.0, lambda g: f"{round(140 * g)}+",
                                          "times a Russian trawler crossed the cable", "as reported by NRK; the owners deny involvement", ""),
}

if __name__ == "__main__":
    for n in sys.argv[1:] or list(ALL):
        ALL[n]()
