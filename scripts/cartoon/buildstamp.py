"""Fingerprint of the code that draws one episode's film (shared engine + that episode's storyboard), stored in the film's
metadata so the quality gate can detect stale files."""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = ["ep01.py", "fxlib.py", "scene.py", "motions.py", "hosts3.py", "people.py", "costume.py", "rig.py", "sets.py",
          "pilot_sets.py", "puppet.py", "pilot.py"]


def _norm(path):
    return path.read_bytes().replace(b"\r\n", b"\n")


def digest(module=None):
    module = module or Path(sys.argv[0]).stem
    h = hashlib.sha1()
    for f in ENGINE + [f"{module}.py"]:
        p = HERE / f
        if p.exists():
            h.update(_norm(p))
    return h.hexdigest()[:12]


def fb_digest(module):
    """Fingerprint for Facebook videos and clips: the episode's film code plus the cutting/caption code."""
    h = hashlib.sha1(digest(module).encode())
    for f in ("fb_cut.py", "make_srt.py"):
        h.update(_norm(HERE / f))
    return h.hexdigest()[:12]
