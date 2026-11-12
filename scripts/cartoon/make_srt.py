"""English subtitles (.srt) for a Tiny Empires episode, timed from the storyboard's own cue sheet (exact voice start times).

  python scripts/cartoon/make_srt.py <module> <out.srt>        e.g. ep03 | ep02 | eic

Long lines are split at sentence or comma breaks into chunks of at most two 42-character lines, timed in proportion to
their length. Spoken years become digits (fb_cut.SPOKEN), as viewers expect in captions.
"""
from __future__ import annotations

import importlib
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MAXC = 84


def ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunks(text):
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    out = []
    for p in parts:
        if len(p) <= MAXC:
            out.append(p)
            continue
        cur = ""
        for piece in re.split(r"(?<=[,;:])\s+", p):
            if cur and len(cur) + 1 + len(piece) > MAXC:
                out.append(cur)
                cur = piece
            else:
                cur = f"{cur} {piece}".strip()
        if len(cur) > MAXC:                                                      # no comma to break on: balanced split by words
            k = -(-len(cur) // MAXC)
            out += textwrap.wrap(cur, -(-len(cur) // k) + 6)
        elif cur:
            out.append(cur)
    merged = []                                                                  # glue very short fragments to the previous chunk
    for c in out:
        if merged and len(c) < 18 and len(merged[-1]) + 1 + len(c) <= MAXC:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def main(module, out):
    import fb_cut as F
    E = importlib.import_module(module)
    K = E.K
    ss = K.shots()
    start, acc = {}, 0.0
    for sh in ss:
        start[sh.name] = acc
        acc += sh.dur
    cues = sorted((start[nm] + t0, lid) for nm, lid, t0 in K.CUES)
    n, rows = 0, []
    for t0, lid in cues:
        text = F.digits(K.LINES[lid]["text"])
        d = K.dur(lid)
        cs = chunks(text)
        tot = sum(len(c) for c in cs)
        t = t0
        for c in cs:
            dt = d * len(c) / tot
            n += 1
            body = "\n".join(textwrap.wrap(c, 42))
            rows.append(f"{n}\n{ts(t)} --> {ts(t + dt - 0.04)}\n{body}\n")
            t += dt
    Path(out).write_text("\n".join(rows), encoding="utf-8")
    print("wrote", out, n, "subtitles,", len(cues), "lines")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
