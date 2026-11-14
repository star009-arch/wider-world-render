"""Fingerprint of the code that draws one episode's film (shared engine + that episode's storyboard), stored in the film's
metadata so the quality gate can detect stale files."""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = ["ep01.py", "fxlib.py", "scene.py", "motions.py", "hosts3.py", "people.py", "costume.py", "rig.py", "sets.py",
          "pilot_sets.py", "puppet.py", "pilot.py"]


def digest(module=None):
    module = module or Path(sys.argv[0]).stem
    h = hashlib.sha1()
    for f in ENGINE + [f"{module}.py"]:
        p = HERE / f
        if p.exists():
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]
