"""Find on-screen text that falls into the subtitle zone (bottom of the frame), for one episode.

  python scripts/cartoon/text_safe_scan.py <module> [limit_y]

Renders every shot at several moments with ImageDraw.text instrumented, maps each text box through the shot's camera
(zoom and centre), and lists every text whose bottom edge is below limit_y (default 860 of 1080).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from PIL import ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

hits = []
_orig = ImageDraw.ImageDraw.text


def spy(self, xy, text, fill=None, font=None, anchor=None, *a, **kw):
    try:
        box = self.textbbox(xy, text, font=font, anchor=anchor)
        hits.append((text, box))
    except Exception:
        pass
    return _orig(self, xy, text, fill, font, anchor, *a, **kw)


def main(module, limit=860):
    E = importlib.import_module(module)
    import scene as SC
    ImageDraw.ImageDraw.text = spy
    found = {}
    for sh in E.K.shots():
        for frac in (0.15, 0.4, 0.65, 0.92):
            t = sh.dur * frac
            hits.clear()
            SC.render_frame(sh, t)
            z, cx, cy = SC.cam_at(sh, t)
            for text, (x0, y0, x1, y1) in hits:
                yb = (y1 - cy * 1080) * z + 540                                  # where the text bottom lands on screen
                if yb > limit and 0 < y0 < 1080:
                    found.setdefault((sh.name, text), round(yb))
    for (shot, text), yb in sorted(found.items()):
        print(f"{shot:22s} y={yb:5d}  {text[:70]!r}")
    print("TOTAL", len(found))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 860)
