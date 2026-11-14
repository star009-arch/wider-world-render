"""Exact word timings for every recorded line (faster-whisper, free, runs on the CPU), saved next to the voice files.

  python scripts/cartoon/word_times.py <voice dir> <lines.json>

Writes <voice dir>/<ID>_words.json = [[word, start, end], ...] using OUR script words: the recogniser's timings are mapped
onto the known text (difflib alignment), so the subtitles always show the exact script, perfectly timed.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def main(vdir, lines_json, model_name="base.en", only=None):
    try:
        import truststore                                                         # Norton re-signs TLS on this machine
        truststore.inject_into_ssl()
    except Exception:
        pass
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    vdir = Path(vdir)
    durs = json.loads((vdir / "durations.json").read_text()) if (vdir / "durations.json").exists() else {}
    lines = json.loads(Path(lines_json).read_text(encoding="utf-8"))["lines"]
    for ln in lines:
        mp3 = vdir / f"{ln['id']}.mp3"
        out = vdir / f"{ln['id']}_words.json"
        if only is not None:
            if ln["id"] not in only:
                continue
        elif not mp3.exists() or (out.exists() and out.stat().st_mtime > mp3.stat().st_mtime):
            continue
        segs, _ = model.transcribe(str(mp3), word_timestamps=True, language="en", initial_prompt=ln["text"])
        heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
        ours = ln["text"].split()
        sm = difflib.SequenceMatcher(a=[norm(w) for w in ours], b=[norm(h[0]) for h in heard], autojunk=False)
        times = [None] * len(ours)
        for a, b, size in sm.get_matching_blocks():
            for k in range(size):
                times[a + k] = (heard[b + k][1], heard[b + k][2])
        # fill words the recogniser heard differently (numbers, names) by interpolating between known neighbours
        known = [i for i, t in enumerate(times) if t]
        end_all = max(heard[-1][2] if heard else 0.0, durs.get(ln["id"], 0.0) - 0.15)   # unheard tail runs to the real end
        for i in range(len(ours)):
            if times[i]:
                continue
            prev = max([k for k in known if k < i], default=None)
            nxt = min([k for k in known if k > i], default=None)
            t0 = times[prev][1] if prev is not None else 0.0
            t1 = times[nxt][0] if nxt is not None else end_all
            span = [j for j in range(prev + 1 if prev is not None else 0, nxt if nxt is not None else len(ours))]
            pos = span.index(i)
            step = (t1 - t0) / max(1, len(span))
            times[i] = (t0 + pos * step, t0 + (pos + 1) * step)
        out.write_text(json.dumps([[w, round(t[0], 3), round(t[1], 3)] for w, t in zip(ours, times)]), encoding="utf-8")
        print(ln["id"], f"{sum(1 for t in known)}/{len(ours)} words matched", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2] if len(a) > 2 else "base.en", set(a[3].split(",")) if len(a) > 3 else None)
