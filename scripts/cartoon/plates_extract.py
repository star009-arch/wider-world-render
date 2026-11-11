"""Unpack 3D plate videos (one mp4 per shot) into JPG frame folders for the scene engine.

  python scripts/cartoon/plates_extract.py <mp4_dir> <plates_dir>
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
for mp4 in sorted(src.glob("*.mp4")):
    out = dst / mp4.stem
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-y", "-i", str(mp4), "-q:v", "2",
                    str(out / "%04d.jpg")], check=True, stdin=subprocess.DEVNULL, timeout=900)
    print(mp4.stem, len(list(out.glob("*.jpg"))), "frames")
