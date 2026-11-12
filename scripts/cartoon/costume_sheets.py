"""Costume reference sheets: the five hosts in a world's period costume plus that world's historical cast, labelled.

  python scripts/cartoon/costume_sheets.py [world ...]        -> D:/Temp/cartoon/costumes_<world>.png
  python scripts/cartoon/costume_sheets.py mounted            -> D:/Temp/cartoon/costumes_mounted.png (riders, camel, gallop cycle)

Check every sheet against the visual bible (projects/tiny-empires/visual_bibles/) before an episode uses the world.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hosts3 as H  # noqa: E402
import motions as M  # noqa: E402
import people as PP  # noqa: E402
import rig as R  # noqa: E402

OUT = Path("D:/Temp/cartoon")
WORLDS = ("mongol_1200", "london_1600", "mughal_1616", "bengal_1757")
HOST_PROPS = {"penny": {"prop_r": "cane"}, "pike": {"prop_l": "rifle"}, "quill": {"prop_l": "book"}, "atlas": {"prop_l": "map"}, "zed": {}}
BG = (236, 230, 216)


def font(size):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def grid(cells, cols, cw, ch, title):
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch + 70), BG)
    d = ImageDraw.Draw(sheet)
    d.text((20, 18), title, fill=(40, 34, 30), font=font(34))
    for i, (tile, ax, ay, label) in enumerate(cells):
        x0, y0 = (i % cols) * cw, 70 + (i // cols) * ch
        d.rectangle([x0 + 4, y0 + 4, x0 + cw - 4, y0 + ch - 4], outline=(200, 190, 170), width=2)
        gy = y0 + ch - 44
        d.ellipse([x0 + cw / 2 - 60, gy - 8, x0 + cw / 2 + 60, gy + 8], fill=(214, 204, 184))
        sheet.paste(tile, (int(x0 + cw / 2 - ax), int(gy - ay)), tile)
        d.text((x0 + cw / 2, y0 + ch - 20), label, fill=(40, 34, 30), font=font(17), anchor="mm")
    return sheet


def pose(**kw):
    return R.Pose(face=R.Face(mouth="smile"), sh_l=14, el_l=10, sh_r=10, el_r=8, **kw)


def world_sheet(world, s=1.0):
    M.set_world(world)
    cells = []
    for view, tag in ((0.6, ""), (0.0, " front"), (1.0, " profile")):
        for key in H.KEYS:
            if tag and key in ("quill",):
                continue
            tile, ax, ay = H.draw(key, pose(**HOST_PROPS[key]), s, False, view)
            cells.append((tile, ax, ay, key + tag))
    for name, per in PP.WORLDS.get(world, {}).items():
        if per.mount or per.creature:
            continue
        tile, ax, ay = PP.draw(per, pose(), s, False, 0.6)
        cells.append((tile, ax, ay, name))
    sheet = grid(cells, 8, 250, 400, f"{world}: hosts (3/4, front, profile) and period cast")
    out = OUT / f"costumes_{world}.png"
    sheet.save(out)
    print(out, len(cells))


def mounted_sheet(s=0.9):
    cells = []
    for world, per_map in PP.WORLDS.items():
        for name, per in per_map.items():
            if not (per.mount or per.creature):
                continue
            key = f"{world}:{name}"
            p = M.Performer(key, x=0, ground=0, scale=s, walks=[(0.5, 4000)])
            t1 = p.segs[0][1] if p.segs else 3.0
            for i, t in enumerate((0.0, t1 * 0.4, t1 * 0.4 + 0.11, t1 * 0.4 + 0.22, t1 * 0.4 + 0.33)):
                ps, fl = p.pose_at(t)
                tile, ax, ay = M.tile_for(key, ps, s, fl, p.view)
                cells.append((tile, ax, ay, f"{name} t={t:.2f}" if i else f"{name} (standing)"))
    sheet = grid(cells, 5, 380, 420, "mounted riders and animals: standing, then four frames of the moving cycle")
    out = OUT / "costumes_mounted.png"
    sheet.save(out)
    print(out, len(cells))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:] or list(WORLDS) + ["mounted"]
    for a in args:
        if a == "mounted":
            mounted_sheet()
        else:
            world_sheet(a)
