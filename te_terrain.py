"""Terrain data for Tiny Empires 3D maps (free sources, prepared on the render runner).

Elevation: Terrain Tiles on AWS Open Data (Terrarium PNG; built from SRTM, GMTED, ETOPO1 and others; free, attribution).
Colour:    Natural Earth II / NE1 high-resolution land cover with shaded relief and water (public domain).

  python te_terrain.py <ne_hr_tif> <ne_50m_tif> <out_dir>

Writes for each region: <name>_height.png (16-bit, metres + 1000, sea clamped to 0 m), <name>_color.png, <name>_water.png
(white = sea) and <name>.json (bbox, size, max height). All in equirectangular lon/lat so colour and height line up.
"""
import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
TILE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
REGIONS = {                                     # name: (lon0, lat0, lon1, lat1, zoom, width px)
    "india": (60.0, 4.0, 100.0, 38.0, 6, 2400),
    "bengal": (84.5, 20.0, 93.5, 27.5, 8, 2400),
    "spice": (100.0, -12.0, 140.0, 10.0, 6, 2400),
    "mongolia": (86.0, 38.0, 124.0, 54.0, 6, 2400),
    "centralasia": (50.0, 32.0, 76.0, 46.0, 6, 2400),
    "eurasia": (-12.0, 8.0, 146.0, 68.0, 4, 3200),
    "globe": (-180.0, -85.0, 180.0, 85.0, 3, 4096),
}


def fetch(z, x, y, cache):
    p = cache / f"{z}_{x}_{y}.png"
    if p.exists():
        return Image.open(p)
    for attempt in range(5):
        try:
            data = urllib.request.urlopen(TILE.format(z=z, x=x, y=y), timeout=60).read()
            p.write_bytes(data)
            return Image.open(io.BytesIO(data))
        except Exception:
            time.sleep(2 + attempt * 3)
    raise SystemExit(f"tile {z}/{x}/{y} failed")


def merc_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    lat = max(-85.05, min(85.05, lat))
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def height_grid(lon0, lat0, lon1, lat1, z, W, H, cache):
    """Sample Terrarium elevation on an equirectangular W x H grid."""
    x0, y0 = merc_xy(lon0, lat1, z)
    x1, y1 = merc_xy(lon1, lat0, z)
    tx0, tx1, ty0, ty1 = int(x0), int(x1), int(y0), int(y1)
    n = 2 ** z
    mosaic = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256), dtype=np.float32)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            im = np.asarray(fetch(z, tx % n, ty, cache).convert("RGB"), dtype=np.float32)
            h = im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768
            mosaic[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = h
    lons = np.linspace(lon0, lon1, W)
    lats = np.linspace(lat1, lat0, H)
    mx = (lons + 180) / 360 * n
    latr = np.radians(np.clip(lats, -85.05, 85.05))
    my = (1 - np.log(np.tan(latr) + 1 / np.cos(latr)) / np.pi) / 2 * n
    px = np.clip(((mx - tx0) * 256).astype(int), 0, mosaic.shape[1] - 1)
    py = np.clip(((my - ty0) * 256).astype(int), 0, mosaic.shape[0] - 1)
    return mosaic[py[:, None], px[None, :]]


def crop_color(src, lon0, lat0, lon1, lat1, W, H):
    rw, rh = src.size
    box = ((lon0 + 180) / 360 * rw, (90 - lat1) / 180 * rh, (lon1 + 180) / 360 * rw, (90 - lat0) / 180 * rh)
    return src.crop(tuple(int(v) for v in box)).resize((W, H), Image.LANCZOS)


def main():
    hr, lo, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "tiles"
    cache.mkdir(exist_ok=True)
    src_hr = Image.open(hr).convert("RGB")
    src_lo = Image.open(lo).convert("RGB")
    for name, (lon0, lat0, lon1, lat1, z, W) in REGIONS.items():
        mid = math.radians((lat0 + lat1) / 2)
        H = int(W * (lat1 - lat0) / ((lon1 - lon0) * (1 if name == "globe" else math.cos(mid))))
        if name == "globe":
            H = W // 2
            lat0, lat1 = -90.0, 90.0
            h = height_grid(-180, -85, 180, 85, z, W, int(W / 2 * 170 / 180), cache)
            pad = (H - h.shape[0]) // 2
            h = np.pad(h, ((pad, H - h.shape[0] - pad), (0, 0)), mode="edge")
            col = src_lo.resize((W, H), Image.LANCZOS)
        else:
            h = height_grid(lon0, lat0, lon1, lat1, z, W, H, cache)
            col = crop_color(src_hr, lon0, lat0, lon1, lat1, W, H)
        water = (h <= 0.5)
        h = np.clip(h, 0, None)
        Image.fromarray(np.clip(h, 0, 65535).astype(np.uint16)).save(out / f"{name}_height.png")
        col.save(out / f"{name}_color.png")
        Image.fromarray((water * 255).astype(np.uint8)).save(out / f"{name}_water.png")
        meta = {"bbox": [lon0, lat0, lon1, lat1], "size": [W, H], "hmax": float(h.max()), "km_per_deg": 111.32 * math.cos(mid)}
        (out / f"{name}.json").write_text(json.dumps(meta))
        print(name, W, H, "max", round(float(h.max())), "m", flush=True)


if __name__ == "__main__":
    main()
