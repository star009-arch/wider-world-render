"""English subtitles (.srt) for a Tiny Empires episode, timed WORD BY WORD from the real voice recordings.

  python scripts/cartoon/make_srt.py <module> <out.srt>        e.g. ep03 | ep02 | eic

Each line's word timings come from <voice>/<ID>_words.json (scripts/cartoon/word_times.py). Lines are split into short
subtitles (at most two lines of 42 characters, broken at sentence or comma breaks); each subtitle appears exactly when
its first word is spoken and leaves when its last word ends. Spoken years become digits (fb_cut.SPOKEN).
"""
from __future__ import annotations

import importlib
import json
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MAXC = 84


def ts(t):
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


FUNC = {"a", "an", "the", "of", "to", "in", "on", "at", "and", "or", "but", "is", "was", "are", "were", "this", "that", "with",
        "for", "by", "from", "as", "his", "her", "its", "their", "be", "it", "so", "i", "i'm", "we", "they", "he", "she"}


def _L(ws):
    return len(" ".join(w for w, _, _ in ws))


def _split(ws, maxc):
    """Best break point in a phrase that is too long: near the middle, at a comma if possible, never after a little word."""
    if _L(ws) <= maxc:
        return [ws]
    half = _L(ws) / 2
    best, bi = None, None
    for i in range(1, len(ws)):
        left, right = ws[:i], ws[i:]
        if _L(left) < 12 or _L(right) < 12:
            continue
        last = re.sub(r"[^a-z']", "", ws[i - 1][0].lower())
        score = abs(_L(left) - half)
        score += -40 if re.search(r"[,;:]$", ws[i - 1][0]) else (60 if last in FUNC else 15)
        if best is None or score < best:
            best, bi = score, i
    if bi is None:
        bi = len(ws) // 2
    return _split(ws[:bi], maxc) + _split(ws[bi:], maxc)


def word_chunks(words, maxc=MAXC):
    """Group [[word, start, end], ...] into readable phrases: one per sentence when it fits, long sentences split at the
    most natural point (commas first, never after a little word). Returns [(text, start, end)]."""
    sents, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?]$", w[0]):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    out = []
    for sw in sents:
        out += _split(sw, maxc)
    merged = []                                                                  # glue tiny fragments ("Yes.") to a neighbour
    for c in out:
        if merged and _L(c) < 14 and _L(merged[-1]) + 1 + _L(c) <= maxc:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    return [(" ".join(w for w, _, _ in c), c[0][1], c[-1][2]) for c in merged]


def two_lines(text, width=42):
    """Balanced two-line layout (no single orphan word on the second line)."""
    if len(text) <= width:
        return text
    ws = text.split()
    best, bi = None, 1
    for i in range(1, len(ws)):
        a, b = " ".join(ws[:i]), " ".join(ws[i:])
        if len(a) > width + 4 or len(b) > width + 4:
            continue
        sc = abs(len(a) - len(b)) + (25 if re.sub(r"[^a-z']", "", ws[i - 1].lower()) in FUNC else 0)
        if best is None or sc < best:
            best, bi = sc, i
    return " ".join(ws[:bi]) + "\n" + " ".join(ws[bi:])


def line_chunks(K, lid):
    """Timed phrases for one recorded line (falls back to proportional timing if word times are missing)."""
    import fb_cut as F
    wf = K.VOICE / f"{lid}_words.json"
    if wf.exists():
        words = json.loads(wf.read_text(encoding="utf-8"))
    else:
        toks = K.LINES[lid]["text"].split()
        d = K.dur(lid)
        tot = sum(len(t) + 1 for t in toks)
        acc, words = 0.0, []
        for t in toks:
            a = acc / tot * d
            acc += len(t) + 1
            words.append([t, a, acc / tot * d])
    return [(F.digits(t), a, b) for t, a, b in word_chunks(words)]


def main(module, out):
    E = importlib.import_module(module)
    K = E.K
    ss = K.shots()
    start, acc = {}, 0.0
    for sh in ss:
        start[sh.name] = acc
        acc += sh.dur
    cues = sorted((start[nm] + t0, lid) for nm, lid, t0 in K.CUES)
    rows, n = [], 0
    allc = []
    for t0, lid in cues:
        for text, a, b in line_chunks(K, lid):
            allc.append([t0 + a, t0 + b + 0.25, text])
    for i in range(len(allc) - 1):                                               # readable minimum, but never overlap the next one
        allc[i][1] = max(allc[i][1], allc[i][0] + 0.7)
        allc[i][1] = min(allc[i][1], allc[i + 1][0] - 0.02)
    for a, b, text in allc:
        n += 1
        rows.append(f"{n}\n{ts(a)} --> {ts(b)}\n" + two_lines(text) + "\n")
    Path(out).write_text("\n".join(rows), encoding="utf-8")
    print("wrote", out, n, "subtitles,", len(cues), "lines")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
