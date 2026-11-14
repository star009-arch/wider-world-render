"""Check translated subtitles against the English original: same cues, same timings, readable lines.

  python scripts/cartoon/check_translations.py <english.srt> <translated.srt> [...]

Fails if the cue count, any cue number or any timestamp line differs, if a cue has no text or more than two lines,
if a line is longer than 46 characters, or if digits for years in the English are missing from the translation.
"""
import re
import sys


def cues(path):
    s = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").strip()
    out = []
    for b in re.split(r"\n\s*\n", s):
        ls = b.split("\n")
        out.append((ls[0].strip(), ls[1].strip(), [x for x in ls[2:] if x.strip()]))
    return out


def check(en_path, tr_path, maxlen=46):
    en, tr = cues(en_path), cues(tr_path)
    errs = []
    if len(en) != len(tr):
        errs.append(f"{len(tr)} cues, English has {len(en)}")
    for (n1, t1, x1), (n2, t2, x2) in zip(en, tr):
        if n1 != n2 or t1 != t2:
            errs.append(f"cue {n1}: number/timing changed")
        if not x2:
            errs.append(f"cue {n1}: empty")
        if len(x2) > 2:
            errs.append(f"cue {n1}: {len(x2)} lines")
        for line in x2:
            if len(line) > maxlen:
                errs.append(f"cue {n1}: line of {len(line)} characters")
        for yr in re.findall(r"\b1\d{3}\b|\b20\d{2}\b", " ".join(x1)):
            if yr not in " ".join(x2):
                errs.append(f"cue {n1}: year {yr} missing")
    return errs


if __name__ == "__main__":
    en = sys.argv[1]
    bad = 0
    for tr in sys.argv[2:]:
        e = check(en, tr)
        print(("PASS " if not e else "FAIL ") + tr + ("" if not e else " :: " + "; ".join(e[:6])))
        bad += bool(e)
    sys.exit(1 if bad else 0)
