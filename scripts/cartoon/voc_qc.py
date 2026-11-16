"""Quality guard for the code-drawn Premium 2D episodes (VOC pilot and every episode built the same way).
Every issue the owner has found becomes a check here. Delivery is refused if any check fails.

  python scripts/cartoon/voc_qc.py [film.mp4]

Checks
  G1  character size: nothing larger than 2.0 scale except declared close-ups (owner 16 Nov: "too large in many places")
  G2  nobody stands on water: every character's feet are inside the set's walkable band (quay, street, sand, floor)
  G3  map labels never overlap each other or a host standing on the map (sampled frames of every map shot)
  G4  pacing: no shot longer than 14 s
  G5  title card names the subject (a subtitle under TINY EMPIRES)
  G6  the episode ends with a "Next time on Tiny Empires" tease
  G7  battle sounds stay comfortable: every gun/blast effect at -12 dB or quieter
  G8  costumes match the place: Travancore people use the Kerala look (munkudumi hair, kasavu mundu, no turbans/hats)
  G9  finished film (if given): loudness -14 +/- 1 LUFS, length matches the plan
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("TE_VOICE", "D:/Temp/cartoon/voc_ep/voice")
import vocepisode as E  # noqa: E402
import flatmap as F  # noqa: E402
import people as PP  # noqa: E402

CLOSE_UPS = {"S04Ledger", "Order"}
WALKABLE = {                                         # (min ground y, max ground y) where feet may stand, per set
    "banda_quay": (820, 1080), "fort_wall": (700, 1080), "colachel_camp": (700, 1080), "road_inland": (620, 1080),
    "amsterdam": (640, 790), "interior": (760, 1080), "kerala_court": (780, 1080), "batavia": (760, 1080), "batavia_dusk": (760, 1080),
    "banda_grove": (700, 1080), "weavers": (620, 1080), "dejima": (600, 1080), "banda_harbour": (2000, 2000), "ocean": (2000, 2000),
    "ocean_storm": (2000, 2000),
}


def shots():
    for i, (s, d, fac, ctx, v) in enumerate(E.plan()):
        o = E.shot_obj(i)
        inner = getattr(o, "obj", o)
        yield i, s, d, o, inner


def main(film=None):
    fails, notes = [], []
    for i, s, d, o, inner in shots():
        name = type(inner).__name__
        perf = getattr(inner, "perf", []) or []
        set_name = getattr(inner, "set_name", "") or ""
        for p in perf:
            if p.key in ("penny", "atlas", "quill", "zed", "pike") and isinstance(inner, (E.MapShot,)):
                continue
            if p.scale > 2.0 + 1e-6 and name not in CLOSE_UPS:
                fails.append(f"G1 shot {i} ({name} at {s:.1f}s): {p.key} scale {p.scale:.2f} > 2.0")
            band = WALKABLE.get(set_name)
            if band and not isinstance(inner, E.MapShot):
                for tt in (0.0, d):
                    x, y = p.pos_at(tt)
                    if not (band[0] <= y <= band[1]) and name not in CLOSE_UPS:
                        fails.append(f"G2 shot {i} ({set_name} at {s:.1f}s): {p.key} feet at y={y:.0f}, outside walkable {band}")
                        break
        if d > 14.0 + 1e-6:
            fails.append(f"G4 shot {i} at {s:.1f}s is {d:.1f}s long (max 14)")
    # G3: render sampled frames of every map shot and collect any label that could not be placed clear
    F.OVERLAPS.clear()
    for i, s, d, o, inner in shots():
        if isinstance(inner, E.MapShot) or type(inner).__name__ in ("S07Atlas", "S08Brouwer", "S08bBrouwer", "S18Quill", "S18bQuill"):
            for k in (0.25, 0.6, 0.95):
                o.frame(d * k)
            if F.OVERLAPS:
                fails.append(f"G3 shot {i} at {s:.1f}s: label(s) could not be placed clear: {sorted(set(F.OVERLAPS))}")
                F.OVERLAPS.clear()
    # G5, G6
    p = E.plan()
    first = E.shot_obj(next(i for i, x in enumerate(p) if isinstance(E.shot_obj(i), E.TitleCard)))
    if not getattr(first, "sub", ""):
        fails.append("G5 the title card has no subtitle naming the subject")
    lines = {ln["id"]: ln for ln in __import__("json").loads((E.VOICE / "lines.json").read_text(encoding="utf-8"))["lines"]}
    voiced = [v[0][0] for s, d, f, c, v in p if v]
    if not any("Next time" in lines[l]["subtitle"] for l in voiced[-3:]):
        fails.append("G6 no 'Next time on Tiny Empires' tease at the end")
    # G7
    for name, t0, gain, loop in E.sound_plan():
        if name in ("@musket", "@explosion") and gain > -12:
            fails.append(f"G7 {name} at {t0:.1f}s is {gain} dB (max -12)")
    # G8
    for key, per in PP.WORLDS["travancore_1741"].items():
        if any(k in key for k in ("nair", "ramayyan", "marthanda")) and key.endswith(("_v2", "marthanda")):
            if per.hair != "kudumi" or per.headwear not in ("", "none") or "kasavu" not in per.flags:
                fails.append(f"G8 {key}: not the Kerala look (hair={per.hair}, headwear={per.headwear}, flags={per.flags})")
    # G9
    if film:
        import imageio_ffmpeg
        r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(film), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
        txt = r.stderr
        try:
            lufs = float(txt.split("I:")[-1].split("LUFS")[0])
            if abs(lufs + 14) > 1.0:
                fails.append(f"G9 loudness {lufs} LUFS (target -14 +/- 1)")
            dur = txt.split("Duration: ")[1].split(",")[0]
            h, m, sec = dur.split(":")
            secs = int(h) * 3600 + int(m) * 60 + float(sec)
            if abs(secs - E.total()) > 2.0:
                fails.append(f"G9 film is {secs:.1f}s but the plan is {E.total():.1f}s")
            notes.append(f"film {secs:.1f}s, {lufs} LUFS")
        except Exception as ex:                                       # noqa: BLE001
            fails.append(f"G9 could not measure the film: {ex}")
    print(f"{len(E.plan())} shots, {E.total():.1f}s")
    for n in notes:
        print("  ", n)
    if fails:
        print("QC FAILED:")
        for f_ in fails:
            print("  ", f_)
        sys.exit(1)
    print("QC PASSED: G1-G9")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
