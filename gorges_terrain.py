"""Terrain + colour for the Three Gorges 3D shots (free sources).

  python scripts/gorges_terrain.py [out_dir]          (default D:/Temp/tg_terrain)

Elevation: Terrain Tiles on AWS Open Data (Terrarium PNG). Over China at this zoom it is SRTM (flown Feb 2000), so the
           valley is the river BEFORE the reservoir: exactly what the "water rises" shot needs.
Colour:    EOX "Sentinel-2 cloudless 2016" (s2maps.eu), CC BY 4.0 -- credit: "Sentinel-2 cloudless - https://s2maps.eu by
           EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016)". Only the 2016 layer is CC BY (later
           years are NC): never switch the layer.
           The 2016 picture shows the full reservoir, so reservoir water is repainted as rock/forest wherever the 2000
           ground is above the old river (the Blender water plane then rises over it).

Writes <name>_height.png (16-bit, metres * 10), <name>_color.png, <name>_water.png (white = water in 2016),
<name>.json (bbox, size, min/max m). Equirectangular lon/lat grids so everything lines up.
"""
from __future__ import annotations

import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

try:
    import truststore
    truststore.inject_into_ssl()          # Norton re-signs TLS on the laptop
except Exception:
    pass

UA = {"User-Agent": "TheWiderWorldDocumentaryBot/1.0 (https://www.youtube.com/@TheWiderWorldDocs)"}
DEM = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
FULL_POOL = 175.0
DAM_LON = 111.004                       # Sandouping axis (30.82 N): west of it = upstream
S2 = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg"

# name: (lon0, lat0, lon1, lat1, dem zoom, colour zoom, width px)
REGIONS = {
    "gorge": (110.25, 30.70, 111.12, 31.12, 12, 13, 3200),      # Badong -> Xiling Gorge -> Sandouping (the dam)
    "dam": (110.93, 30.78, 111.07, 30.87, 13, 15, 2400),        # the dam site close up
    "basin": (104.0, 27.5, 122.5, 33.5, 8, 9, 3600),             # Chongqing -> Shanghai: the river and its lakes
}


def get(url: str, cache: Path) -> Image.Image:
    if cache.exists():
        return Image.open(cache)
    for attempt in range(6):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            cache.write_bytes(data)
            return Image.open(io.BytesIO(data))
        except Exception as e:                      # noqa: BLE001
            err = e
            time.sleep(2 + attempt * 3)
    raise SystemExit(f"{url}: {err}")


def tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def mosaic(lon0, lat0, lon1, lat1, z, W, H, url, cache: Path, mode):
    """Sample a web-mercator tile pyramid onto an equirectangular W x H grid."""
    x0, y0 = tile_xy(lon0, lat1, z)
    x1, y1 = tile_xy(lon1, lat0, z)
    tx0, ty0, tx1, ty1 = int(x0), int(y0), int(x1), int(y1)
    big = Image.new(mode, ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            im = get(url.format(z=z, x=tx, y=ty), cache / f"{z}_{tx}_{ty}.{'png' if mode == 'RGB' and 'terrarium' in url else 'jpg'}")
            big.paste(im.convert(mode), ((tx - tx0) * 256, (ty - ty0) * 256))
    arr = np.asarray(big).astype(np.float32)
    lons = np.linspace(lon0, lon1, W)
    lats = np.linspace(lat1, lat0, H)
    px = np.array([tile_xy(lo, lats[0], z)[0] for lo in lons]) - tx0
    py = np.array([tile_xy(lons[0], la, z)[1] for la in lats]) - ty0
    xs = np.clip(px * 256, 0, arr.shape[1] - 1.001)
    ys = np.clip(py * 256, 0, arr.shape[0] - 1.001)
    X, Y = np.meshgrid(xs, ys)
    xi, yi = X.astype(int), Y.astype(int)
    fx, fy = (X - xi)[..., None], (Y - yi)[..., None]
    a = arr if arr.ndim == 3 else arr[..., None]
    v = (a[yi, xi] * (1 - fx) * (1 - fy) + a[yi, xi + 1] * fx * (1 - fy) + a[yi + 1, xi] * (1 - fx) * fy
         + a[yi + 1, xi + 1] * fx * fy)
    return v


def _noise(W, H, seed, scales=(3, 12, 40)):
    rng = np.random.default_rng(seed)
    out = np.zeros((H, W), np.float32)
    for k, sc in enumerate(scales):
        small = rng.standard_normal((max(2, H // sc), max(2, W // sc))).astype(np.float32)
        im = Image.fromarray(((small + 3) * 40).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        out += (np.asarray(im).astype(np.float32) / 40 - 3) * (0.5 ** k)
    return out / 1.6


def paint(h, W, H, lon0, lon1, lat0, lat1):
    """Procedural colour (no imagery): forest by height and aspect, bare limestone on cliffs, silt on the river banks.
    The 2000 river (lowest connected ground) is marked as water for the downstream plane."""
    m_per_px = (lon1 - lon0) * 111320 * math.cos(math.radians((lat0 + lat1) / 2)) / W
    gy, gx = np.gradient(h, m_per_px)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    n1, n2 = _noise(W, H, 1), _noise(W, H, 2, (2, 6, 20))
    forest_lo = np.array([46, 78, 40], np.float32)        # subtropical broadleaf, valley floors
    forest_hi = np.array([70, 92, 52], np.float32)        # drier, higher slopes
    farm = np.array([122, 128, 76], np.float32)           # terraces on gentle slopes
    rock = np.array([168, 156, 134], np.float32)          # pale Triassic limestone of the gorges
    silt = np.array([150, 132, 104], np.float32)
    rel = np.clip((h - np.percentile(h, 2)) / (np.percentile(h, 98) - np.percentile(h, 2) + 1), 0, 1)[..., None]
    col = forest_lo * (1 - rel) + forest_hi * rel
    gentle = np.clip((14 - slope) / 10, 0, 1) * np.clip(n2 * 0.8 + 0.3, 0, 1) * np.clip((900 - h) / 300, 0, 1)
    col = col * (1 - gentle[..., None] * 0.6) + farm * gentle[..., None] * 0.6
    cliff = np.clip((slope - 32 + n1 * 6) / 12, 0, 1)[..., None]
    col = col * (1 - cliff) + rock * cliff
    river_level = float(np.percentile(h, 0.5))
    bank = np.clip((river_level + 25 - h) / 25, 0, 1)[..., None]
    col = col * (1 - bank * 0.7) + silt * bank * 0.7
    col = col * (1 + n1[..., None] * 0.07) + n2[..., None] * 4
    water = h < river_level + 4
    return np.clip(col, 0, 255), water, river_level


def centreline(h, lon0, lat0, lon1, lat1, step=20):
    """The river as [lon, lat, metres] every `step` columns: lowest ground per column, tracked within a moving band so
    tributaries do not capture it. Assumes the river crosses the region from west to east (true for these regions)."""
    from PIL import ImageFilter as _F
    H, W = h.shape
    k = 9
    c = np.cumsum(np.cumsum(np.pad(h.astype(np.float64), k // 2 + 1, mode='edge'), 0), 1)
    hs = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k])[:H, :W] / (k * k)
    out, row = [], int(np.argmin(hs[:, 0]))
    for x in range(0, W, step):
        lo, hi = max(0, row - 60), min(H, row + 61)
        row = lo + int(np.argmin(hs[lo:hi, x]))
        out.append([round(lon0 + (lon1 - lon0) * x / (W - 1), 5), round(lat1 - (lat1 - lat0) * row / (H - 1), 5), round(float(hs[row, x]), 1)])
    return out


def build(name, out: Path):
    lon0, lat0, lon1, lat1, zd, zc, W = REGIONS[name]
    H = int(round(W * (lat1 - lat0) / ((lon1 - lon0) * math.cos(math.radians((lat0 + lat1) / 2)))))
    cache = out / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    t = mosaic(lon0, lat0, lon1, lat1, zd, W, H, DEM, cache, "RGB")
    h = t[..., 0] * 256 + t[..., 1] + t[..., 2] / 256 - 32768          # Terrarium decoding, metres
    h = np.clip(h, -50, 9000)
    col, water, river_level = paint(h, W, H, lon0, lon1, lat0, lat1)
    dry = water
    Image.fromarray(col.astype(np.uint8)).save(out / f"{name}_color.png")
    Image.fromarray(((h - h.min()) * 10).clip(0, 65535).astype(np.uint16)).save(out / f"{name}_height.png")
    Image.fromarray((water * 255).astype(np.uint8)).save(out / f"{name}_water.png")
    meta = dict(bbox=[lon0, lat0, lon1, lat1], size=[W, H], min_m=float(h.min()), max_m=float(h.max()),
                river_level_m=float(river_level), height_scale="png value / 10 + min_m",
                km_per_deg=111.32 * math.cos(math.radians((lat0 + lat1) / 2)), river=centreline(h, lon0, lat0, lon1, lat1))
    (out / f"{name}.json").write_text(json.dumps(meta, indent=1))
    print(name, W, H, f"{h.min():.0f}..{h.max():.0f} m, old river ~{river_level:.0f} m, repainted {dry.mean() * 100:.1f}%")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1] in REGIONS else "D:/Temp/tg_terrain")
    names = [a for a in sys.argv[1:] if a in REGIONS] or list(REGIONS)
    out.mkdir(parents=True, exist_ok=True)
    for n in names:
        build(n, out)
