"""Quality gate for a Tiny Empires episode: every check that guards an issue we have hit. Run before any delivery.

  python scripts/cartoon/qc_episode.py <module> "<WATCH_ME episode folder>"      e.g. eic "WATCH_ME/Tiny Empires/Episode 03 - ..."

Exit code 0 = all checks pass. Each FAIL names the file and what to fix.
"""
from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

WEEKDAYS = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
results = []


def check(name, ok, detail=""):
    results.append((ok, name, detail))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail else ""), flush=True)


def ff():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path):
    r = subprocess.run([ff(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    v = re.search(r"Video: h264 \((\w+)\)[^,]*, (\w+)[^,]*?, (\d+)x(\d+)", r)
    a = re.search(r"Audio: aac \((\w+)\)[^,]*, (\d+) Hz, (\w+)", r)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    dur = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else 0
    head = open(path, "rb").read(1 << 20)
    moov, mdat = head.find(b"moov"), head.find(b"mdat")
    decodes = subprocess.run([ff(), "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True).stderr.strip() == ""
    return {"profile": v.group(1) if v else None, "pix": v.group(2) if v else None, "w": int(v.group(3)) if v else 0,
            "h": int(v.group(4)) if v else 0, "aac": a.group(1) if a else None, "hz": int(a.group(2)) if a else 0,
            "ch": a.group(3) if a else None, "dur": dur, "fast": moov != -1 and (mdat == -1 or moov < mdat), "decodes": decodes}


def media_ok(name, path, w, h, dur=None, tol=0.6):
    if not path.exists():
        check(name, False, f"missing {path.name}")
        return
    p = probe(path)
    bad = []
    if (p["w"], p["h"]) != (w, h):
        bad.append(f"size {p['w']}x{p['h']} (want {w}x{h})")
    if p["profile"] not in ("High", "Main") or p["pix"] != "yuv420p":
        bad.append(f"video {p['profile']}/{p['pix']}")
    if p["aac"] != "LC" or p["hz"] != 48000 or p["ch"] != "stereo":
        bad.append(f"audio {p['aac']} {p['hz']} {p['ch']}")
    if not p["fast"]:
        bad.append("no quick-start (moov after mdat)")
    if not p["decodes"]:
        bad.append("decode errors")
    if dur is not None and abs(p["dur"] - dur) > tol:
        bad.append(f"duration {p['dur']:.1f}s, storyboard {dur:.1f}s")
    check(name, not bad, "; ".join(bad) or f"{p['w']}x{p['h']} {p['dur']:.1f}s")
    return p


def main(module, folder):
    folder = Path(folder)
    E = importlib.import_module(module)
    K = E.K
    import scene as SC
    import fb_cut as F
    import make_srt as MS
    ep = folder.name[:10]
    shots = K.shots()
    total = sum(s.dur for s in shots)
    voice = K.VOICE

    # 1. one running text: no info captions; nothing drawn in the subtitle zone; no weekday names on screen
    check("no info captions in the film", getattr(K, "SHOW_CAPTIONS", True) is False)
    texts, low = [], []
    orig = ImageDraw.ImageDraw.text

    def spy(self, xy, text, fill=None, font=None, anchor=None, *a, **kw):
        try:
            texts.append((text, self.textbbox(xy, text, font=font, anchor=anchor)))
        except Exception:
            pass
        return orig(self, xy, text, fill, font, anchor, *a, **kw)
    ImageDraw.ImageDraw.text = spy
    seen = set()
    for sh in shots:
        for frac in (0.15, 0.4, 0.65, 0.92):
            t = sh.dur * frac
            texts.clear()
            SC.render_frame(sh, t)
            z, cx, cy = SC.cam_at(sh, t)
            for txt, (x0, y0, x1, y1) in texts:
                seen.add(txt)
                yb = (y1 - cy * 1080) * z + 540
                if yb > 860 and 0 < y0 < 1080:
                    low.append(f"{sh.name}:{txt[:30]!r}@{round(yb)}")
    ImageDraw.ImageDraw.text = orig
    check("subtitle zone (bottom 20%) free of picture text", not low, ", ".join(sorted(set(low))[:8]))
    wd = [t for t in seen if WEEKDAYS.search(t)]
    check("no weekday names on screen", not wd, ", ".join(wd))

    # 2. opening and pacing
    first = min(t0 for nm, lid, t0 in K.CUES if nm == shots[0].name) if K.CUES else 99
    check("voice starts within 0.5 s", first <= 0.5, f"first line at {first:.2f}s")
    long_ = [f"{s.name} {s.dur:.0f}s" for s in shots if s.dur > 17 and s.bg != "endcard"]
    check("no single shot longer than 17 s", not long_, ", ".join(long_))

    # 3. word timing for every spoken line
    durs = json.loads((voice / "durations.json").read_text())
    bad = []
    lids = sorted({lid for _, lid, _ in K.CUES})
    for lid in lids:
        f = voice / f"{lid}_words.json"
        if not f.exists():
            bad.append(f"{lid} missing")
            continue
        w = json.loads(f.read_text(encoding="utf-8"))
        st = [x[1] for x in w]
        if any(b < a for a, b in zip(st, st[1:])) or durs[lid] - w[-1][2] > 1.2 or sum(1 for a, b in zip(st, st[1:]) if b - a < 0.02) > 1:
            bad.append(lid)
    check(f"word timing valid for all {len(lids)} lines", not bad, ", ".join(bad))

    # 4. subtitles
    srt = folder / "YouTube" / f"{ep} - Subtitles (English).srt"
    if srt.exists():
        blocks = [b for b in srt.read_text(encoding="utf-8").strip().split("\n\n") if b.strip()]

        def sec(s):
            h, m, r = s.split(":")
            return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))
        cues, probs = [], []
        for b in blocks:
            ls = b.split("\n")
            a, c = [sec(x.strip()) for x in ls[1].split("-->")]
            cues.append((a, c))
            body = ls[2:]
            if len(body) > 2 or any(len(x) > 46 for x in body):
                probs.append(f"#{ls[0]} too long")
            if re.search(r"\b(seventeen|sixteen|twelve|eleven|nineteen|twenty) (hundred|[a-z]+-[a-z]+|oh)\b", " ".join(body), re.I):
                probs.append(f"#{ls[0]} spoken year")
        over = [i for i in range(len(cues) - 1) if cues[i][1] > cues[i + 1][0] + 1e-3]
        check("subtitles: no overlaps, max 2 short lines, years as digits", not over and not probs, f"overlaps {len(over)} {probs[:5]}")
        expect = sum(len(MS.line_chunks(K, lid)) for _, lid, _ in K.CUES)
        check("subtitles match the word-timed script", len(blocks) == expect, f"{len(blocks)} subtitles, expected {expect}")
        check("subtitles end inside the film", cues[-1][1] <= total + 0.5, f"last {cues[-1][1]:.1f}s, film {total:.1f}s")
    else:
        check("subtitles file present", False, str(srt))

    # 5. the YouTube film
    film = folder / "YouTube" / f"{ep} - Full Film.mp4"
    p = media_ok("YouTube film: H.264/AAC 48k, quick-start, length", film, 1920, 1080, total)
    if film.exists():
        import buildstamp
        meta = subprocess.run([ff(), "-hide_banner", "-i", str(film)], capture_output=True, text=True).stderr
        m = re.search(r"comment\s*:\s*te-storyboard:(\w+)", meta)
        check("film rendered from the current storyboard code (not stale)", bool(m) and m.group(1) == buildstamp.digest(),
              f"film {m.group(1) if m else 'unstamped'}, code {buildstamp.digest()}")
    if p:
        r = subprocess.run([ff(), "-nostdin", "-hide_banner", "-i", str(film), "-af", "ebur128=framelog=verbose", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
        st = [float(x) for x in re.findall(r"t: ([\d.]+)\s+TARGET.*?S:\s*(-?[\d.]+)", r) for x in [x[1]]] if False else []
        shortterm = [(float(t), float(s)) for t, s in re.findall(r"t: ([\d.]+)\s.*?S:\s*(-?[\d.]+)", r)]
        integ = float(I[-1]) if I else -99
        early = [s for t, s in shortterm if t <= 3.0]
        swell = max(early) - integ if early else 0
        check("loudness about -14 LUFS (YouTube)", -15.5 <= integ <= -12.5, f"{integ} LUFS")
        check("no loudness swell at the start", swell <= 4.0, f"first 3 s up to {swell:+.1f} dB vs average")

    # 6. Facebook video and clips
    K2, segs, ftotal = F.plan(module)
    media_ok("Facebook video (upload this)", folder / "Facebook" / f"{ep} - Facebook video (upload this).mp4", 1080, 1350, ftotal + F.END)
    clips = sorted((folder / "Short clips").glob(f"{ep} - Short clip *.mp4"))
    check("3 short clips", len(clips) == 3, f"{len(clips)} found")
    for c in clips:
        p = media_ok(f"clip {c.name[13:40]}", c, 1080, 1350)
        if p:
            check(f"clip length 20-60 s: {c.name[13:40]}", 20 <= p["dur"] <= 60, f"{p['dur']:.1f}s")

    # 7. folders, thumbnails, texts
    for f in ["YouTube/{e} - Thumbnail.jpg", "YouTube/{e} - Thumbnail B (for Test and compare).jpg", "YouTube/{e} - YouTube upload text.txt",
              "Facebook/{e} - Facebook cover (upload this).jpg", "Facebook/{e} - Facebook post text.txt", "Short clips/{e} - Short clips post text.txt"]:
        path = folder / f.format(e=ep)
        check(f"present: {path.name}", path.exists())
    for t in ("YouTube/{e} - Thumbnail.jpg", "YouTube/{e} - Thumbnail B (for Test and compare).jpg"):
        path = folder / t.format(e=ep)
        if path.exists():
            im = Image.open(path)
            check(f"thumbnail 1280x720 under 2 MB: {path.name}", im.size == (1280, 720) and path.stat().st_size < 2_000_000, f"{im.size}")
    up = folder / "YouTube" / f"{ep} - YouTube upload text.txt"
    if up.exists():
        s = up.read_text(encoding="utf-8")
        title = s.split("TITLE\n", 1)[1].split("\n", 1)[0]
        desc = s.split("DESCRIPTION\n", 1)[1].split("\nTAGS", 1)[0].strip()
        tags = s.split("TAGS\n", 1)[1].split("\n", 1)[0]
        ch = [(int(m), int(sx)) for m, sx in re.findall(r"^(\d+):(\d\d) ", desc, re.M)]
        secs = [m * 60 + x for m, x in ch]
        okc = len(secs) >= 3 and secs[0] == 0 and all(b - a >= 10 for a, b in zip(secs, secs[1:])) and secs[-1] < total
        check("chapters valid (start 0:00, 3+, 10 s apart, inside film)", okc, f"{len(secs)} chapters")
        check("title/description/tags within YouTube limits", len(title) <= 100 and len(desc) <= 5000 and len(tags) <= 500,
              f"{len(title)}/{len(desc)}/{len(tags)}")
    wd = [str(p.relative_to(folder)) for p in folder.rglob("*.txt") if WEEKDAYS.search(p.read_text(encoding="utf-8"))]
    check("no weekday names in upload/post texts", not wd, ", ".join(wd))

    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)}/{len(results)} checks passed" + ("" if not fails else f"  ({len(fails)} FAILED)"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
