"""Click-worthy thumbnails (1280x720): a sharp graded 3D set, big expressive characters lit into the scene (no outline),
3-5 huge words with a heavy outline, small channel badge. Two designs per episode (A/B for YouTube "Test & compare").

  python scripts/cartoon/thumb2.py <episode> <variant A|B> <plate.jpg> <out.jpg>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402

W, H = 1280, 720
YEL, WHT, RED = (255, 206, 40), (255, 255, 255), (230, 40, 40)
SHOCK = {"mouth": "o", "brows": 1.2}
GRIN = {"mouth": "grin", "brows": -0.4}
SMIRK = {"mouth": "smirk", "brows": -0.5}

# cast entries: (key, x, ground, scale, flip, face, act) in 1920x1080 coordinates
T = {
    ("ep03", "A"): {"world": "egypt_ok", "words": [("HOW DID THEY", WHT, 108), ("BUILD THIS?", YEL, 140)], "sub": None, "text_at": (56, 46),
                    "cast": [("penny", 1560, 1290, 4.1, True, SHOCK, None), ("zed", 1060, 1270, 3.5, True, GRIN, "point")]},
    ("ep03", "B"): {"world": "egypt_ok", "words": [("NO CRANES?!", YEL, 150)], "sub": ("NO STEEL. NO ENGINES.", WHT, 64), "text_at": (56, 60),
                    "cast": [("penny", 1540, 1290, 4.1, True, SHOCK, None), ("egypt_ok:khufu", 1050, 1250, 3.2, True, GRIN, "point")]},
    ("ep02", "A"): {"world": "mongol_1200", "words": [("ONLY HORSES...", WHT, 110), ("VS EMPIRES", YEL, 140)], "sub": None, "text_at": (56, 50),
                    "cast": [("mongol_1200:genghis_mounted", 1380, 1230, 3.7, True, GRIN, None),
                             ("mongol_1200:rider_mounted", 780, 1180, 2.6, True, GRIN, None)]},
    ("ep02", "B"): {"world": "mongol_1200", "words": [("ABANDONED BOY", WHT, 104), ("TO GREAT KHAN", YEL, 120)], "sub": None, "text_at": (56, 50),
                    "cast": [("mongol_1200:genghis", 1480, 1290, 4.1, True, SMIRK, "present"), ("penny", 930, 1280, 3.2, True, SHOCK, None)]},
    ("eic", "A"): {"world": "bengal_1757", "words": [("A SHOP", WHT, 120), ("WITH AN ARMY?!", YEL, 112)], "sub": None, "text_at": (56, 40),
                   "cast": [("bengal_1757:clive", 1500, 1290, 4.0, True, SMIRK, "point"), ("penny", 900, 1280, 3.2, True, SHOCK, None)]},
    ("eic", "B"): {"world": "bengal_1757", "words": [("SPICE SELLERS", WHT, 104), ("RULED INDIA?", YEL, 128)], "sub": None, "text_at": (56, 50),
                   "cast": [("bengal_1757:nawab", 1520, 1290, 3.8, True, SHOCK, None), ("bengal_1757:clive", 1000, 1270, 3.3, False, SMIRK, "point")]},
}


REEL_HERO = {"ep03": ("penny", 0, 0, 2.9, True, SHOCK, None),
             "ep02": ("mongol_1200:genghis_mounted", 0, 0, 2.3, True, GRIN, None),
             "eic": ("bengal_1757:clive", 0, 0, 2.9, True, SMIRK, "point")}


def font(size):
    for f in ("C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def compose(cfg, plate, cast_override=None, parts=False):
    """Sharp graded 3D set + characters integrated into it (scene-tinted, light-wrapped edges, soft cast shadow), 1920x1080 RGBA.
    parts=True returns (background, characters-with-shadow) so callers can grade the set before the characters go on."""
    M.set_world(cfg["world"])
    import scene as SC
    from scene import Shot, render_frame
    import numpy as np
    bg = Image.open(plate).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    bg = ImageEnhance.Contrast(ImageEnhance.Color(bg).enhance(1.25)).enhance(1.10)
    bg = bg.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=2))  # crisp set, no blur
    t = float(os.environ.get("THUMB_T", "1.7"))
    spec = cast_override or cfg["cast"]

    def shoot(colour):
        SC._BG["thumbbg"] = Image.new("RGBA", (1920, 1080), colour + (255,))
        cast = [M.Performer(k, x=x, ground=g, scale=s_, flip=fl, faces=[(0, fc)], acts=[(0.0, a_, None)] if a_ else [])
                for k, x, g, s_, fl, fc, a_ in spec]
        return render_frame(Shot("thumb", 2.0, "thumbbg", actors=cast, world=cfg["world"], camkeys=[(0.0, 1.0, 0.5, 0.5)]), t).convert("RGB")

    on_k = np.asarray(shoot((0, 0, 0)), dtype=np.float32)
    on_w = np.asarray(shoot((255, 255, 255)), dtype=np.float32)
    al = np.clip(1.0 - (on_w - on_k).mean(axis=2) / 255.0, 0, 1)
    rgb = np.where(al[..., None] > 0.004, on_k / np.maximum(al[..., None], 0.004), 0)
    B = np.asarray(bg, dtype=np.float32)
    amb = np.asarray(bg.filter(ImageFilter.GaussianBlur(60)), dtype=np.float32)    # the scene's light around each character
    rgb = rgb * 0.88 + amb * 0.12                                                  # colour-match to the set
    alpha_img = Image.fromarray((al * 255).astype(np.uint8))
    inner = np.asarray(alpha_img.filter(ImageFilter.MinFilter(9)), dtype=np.float32) / 255.0
    edge = np.clip(al - inner, 0, 1)
    edge = np.asarray(Image.fromarray((edge * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), dtype=np.float32)[..., None] / 255.0
    rgb = rgb * (1 - 0.45 * edge) + amb * 0.45 * edge                              # light wrap: set light spills over the edges
    chars = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al * 255]).astype(np.uint8), "RGBA")
    sh = alpha_img.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.5))
    shadow = Image.new("RGBA", (1920, 1080), (12, 8, 6, 0))
    shadow.putalpha(sh)
    layer = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    layer.alpha_composite(shadow, (34, 26))                                       # soft cast shadow on the set behind
    layer.alpha_composite(chars)
    if parts:
        return bg.convert("RGBA"), layer
    im = bg.convert("RGBA")
    im.alpha_composite(layer)
    return im


def fit_font(d, text, size, maxw):
    while size > 30 and d.textlength(text, font=font(size)) > maxw:
        size -= 4
    return size


def cover(ep, var, plate, out, fmt):
    """Facebook cover: 4x5 (feed, 1080x1350) or 9x16 (Reels, 1080x1920). Characters re-centred, words fitted to the width."""
    cfg = T[(ep, var)]
    OW, OH = (1080, 1350) if fmt == "4x5" else (1080, 1920)
    cw = int(1080 * OW / OH * 1.0)                                               # crop width in the 1920x1080 composite
    if fmt == "9x16":                                                            # Reels: one big hero character
        key, x, g, sc, fl, fc, a_ = REEL_HERO.get(ep, cfg["cast"][0])
        cast = [(key, 960, 1150, sc, fl, fc, a_)]
    else:
        xs = [c[1] for c in cfg["cast"]]
        mid = (min(xs) + max(xs)) / 2
        span = max(xs) - min(xs) + 500
        k = min(1.0, (cw - 60) / span)
        cast = [(key, 960 + (x - mid) * k, 1080 + (g - 1080) * k + 40, sc * k * 1.05, fl, fc, a_) for key, x, g, sc, fl, fc, a_ in cfg["cast"]]
    im = compose(cfg, plate, cast)
    im = im.crop((960 - cw // 2, 0, 960 - cw // 2 + cw, 1080)).resize((OW, int(1080 * OW / cw)), Image.LANCZOS)
    canvas = Image.new("RGBA", (OW, OH))
    canvas.alpha_composite(im, (0, OH - im.height))
    top = Image.open(plate).convert("RGB").resize((OW, OH - im.height + 200)).filter(ImageFilter.GaussianBlur(24))
    band = Image.blend(top, Image.new("RGB", top.size, (14, 10, 12)), 0.55).convert("RGBA")
    canvas.alpha_composite(band, (0, 0))
    fade = Image.new("RGBA", (OW, 200))
    for y in range(200):
        ImageDraw.Draw(fade).line([(0, y), (OW, y)], fill=(14, 10, 12, int(140 * (1 - y / 200))))
    canvas.alpha_composite(im.crop((0, 0, OW, 200)), (0, OH - im.height))
    canvas.alpha_composite(fade, (0, OH - im.height))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([OW / 2 - 170, 40, OW / 2 + 170, 100], radius=14, fill=(178, 34, 34))
    d.text((OW / 2, 70), "TINY EMPIRES", font=font(38), fill=WHT, anchor="mm")
    y = 140 if OH < 1600 else 190
    for text, col, size in cfg["words"]:
        sz = fit_font(d, text, int(size * (1.25 if OH < 1600 else 1.5)), OW - 70)
        d.text((OW / 2 + 5, y + 7), text, font=font(sz), fill=(0, 0, 0, 160), anchor="ma")
        d.text((OW / 2, y), text, font=font(sz), fill=col, anchor="ma", stroke_width=max(6, sz // 13), stroke_fill=(12, 10, 8))
        y += int(sz * 1.05)
    if cfg["sub"]:
        text, col, size = cfg["sub"]
        sz = fit_font(d, text, size, OW - 140)
        tw = d.textlength(text, font=font(sz))
        d.rounded_rectangle([OW / 2 - tw / 2 - 20, y + 10, OW / 2 + tw / 2 + 20, y + sz + 34], radius=12, fill=RED)
        d.text((OW / 2, y + 18), text, font=font(sz), fill=col, anchor="ma")
    canvas.convert("RGB").save(out, quality=95)
    print("wrote", out)


def main(ep, var, plate, out):
    cfg = T[(ep, var)]
    bg, layer = compose(cfg, plate, parts=True)
    im = bg
    shade = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for x in range(1920):                                                         # darker on the text (left) side
        a = int(150 * max(0.0, 1 - x / 1150) ** 1.4)
        sd.line([(x, 0), (x, 1080)], fill=(0, 0, 0, a))
    for y in range(1080):                                                         # vignette at the bottom
        a = int(90 * max(0.0, (y - 760) / 320))
        sd.line([(0, y), (1920, y)], fill=(0, 0, 0, a))
    im.alpha_composite(shade)
    im.alpha_composite(layer)
    im = im.resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    x0, y0 = cfg["text_at"]
    y = y0
    for text, col, size in cfg["words"]:
        f = font(size)
        d.text((x0 + 6, y + 8), text, font=f, fill=(0, 0, 0, 160))               # drop shadow
        d.text((x0, y), text, font=f, fill=col, stroke_width=max(6, size // 13), stroke_fill=(12, 10, 8))
        y += int(size * 1.02)
    if cfg["sub"]:
        text, col, size = cfg["sub"]
        f = font(size)
        tw = d.textlength(text, font=f)
        d.rounded_rectangle([x0 - 6, y + 8, x0 + tw + 26, y + size + 30], radius=12, fill=RED)
        d.text((x0 + 10, y + 16), text, font=f, fill=col)
    bf = font(30)
    bw = d.textlength("TINY EMPIRES", font=bf)
    d.rounded_rectangle([W - bw - 52, H - 62, W - 18, H - 18], radius=10, fill=(178, 34, 34))
    d.text((W - bw - 35, H - 58), "TINY EMPIRES", font=bf, fill=WHT)
    im.convert("RGB").save(out, quality=95)
    print("wrote", out)


if __name__ == "__main__":
    if len(sys.argv) > 5:
        cover(*sys.argv[1:6])
    else:
        main(*sys.argv[1:5])
