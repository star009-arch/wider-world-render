"""Fingerprint of the code that draws a film, stored in the film's metadata so the quality gate can detect stale files."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["ep01.py", "ep02.py", "ep03.py", "eic.py", "fxlib.py", "scene.py", "motions.py", "hosts3.py", "people.py", "costume.py",
         "rig.py", "sets.py", "pilot_sets.py", "puppet.py", "pilot.py"]


def digest():
    h = hashlib.sha1()
    for f in FILES:
        p = HERE / f
        if p.exists():
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]
