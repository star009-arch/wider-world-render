"""Episode thumbnails: a 3D plate frame + period cast and hosts + a two-line hook (white line, gold line), channel badge.

  python scripts/cartoon/thumb.py <episode key> <plate.jpg> <out.jpg>      (episode keys in THUMBS)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motions as M  # noqa: E402

W, H = 1280, 720
# cast: (key, x, ground, scale, flip, face, act)
THUMBS = {
    "ep02": {"world": "mongol_1200", "lines": ["ONE ABANDONED BOY BUILT...", "THE LARGEST CONNECTED EMPIRE"],
             "cast": [("mongol_1200:genghis_mounted", 470, 1070, 2.3, False, {"mouth": "grin", "brows": -0.4}, None),
                      ("pike", 1180, 1070, 2.3, True, {"mouth": "o", "brows": 1.0}, None),
                      ("penny", 1560, 1070, 2.4, True, {"mouth": "smirk", "brows": -0.3}, "present")]},
    "eic": {"world": "bengal_1757", "lines": ["A SHOP... WITH AN ARMY?", "HOW A COMPANY TOOK INDIA"],
            "cast": [("bengal_1757:clive", 380, 1060, 2.2, False, {"mouth": "smirk", "brows": -0.4}, "point"),
                     ("bengal_1757:nawab", 780, 1060, 2.1, True, {"mouth": "o", "brows": 1.0}, None),
                     ("pike", 1200, 1070, 2.3, True, {"mouth": "o", "brows": 1.0}, None),
                     ("penny", 1580, 1070, 2.4, True, {"mouth": "smirk", "brows": -0.3}, "present")]},
}


def font(size):
    for f in ("C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def outlined(d, xy, text, size, fill, anchor="mm"):
    d.text(xy, text, font=font(size), fill=fill, anchor=anchor, stroke_width=max(4, size // 14), stroke_fill=(10, 8, 6))


def main(key, plate, out):
    cfg = THUMBS[key]
    M.set_world(cfg["world"])
    import scene as SC
    from scene import Shot, render_frame
    SC._BG["thumbbg"] = Image.open(plate).convert("RGBA").resize((1920, 1080), Image.LANCZOS)
    cast = [M.Performer(k, x=x, ground=g, scale=s, flip=fl, faces=[(0, fc or {})], acts=[(0.0, a, None)] if a else [])
            for k, x, g, s, fl, fc, a in cfg["cast"]]
    im = render_frame(Shot("thumb", 2.0, "thumbbg", actors=cast, world=cfg["world"]), float(os.environ.get("THUMB_T", "1.7")))
    im = im.convert("RGBA").resize((W, H), Image.LANCZOS)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(300):
        sd.line([(0, y), (W, y)], fill=(0, 0, 0, int(215 * (1 - y / 300) ** 1.2)))
    im.alpha_composite(shade)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 28, 348, 80], radius=10, fill=(178, 34, 34))
    d.text((194, 54), "TINY EMPIRES", font=font(34), fill=(255, 255, 255), anchor="mm")
    l1, l2 = cfg["lines"]
    outlined(d, (700, 128), l1, 74, (255, 255, 255))
    outlined(d, (700, 218), l2, 84, (255, 204, 40))
    im.convert("RGB").save(out, quality=94)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
