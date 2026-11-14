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
    fast = []                                                                    # leg cycles faster than a natural gait flicker at 30 fps
    for s_ in shots:
        for a_ in s_.actors:
            if getattr(a_, "walks", None) and hasattr(a_, "pp"):
                hz = a_.pp.cadence * a_.pp.speed * a_.speed
                if hz > 2.6:
                    fast.append(f"{s_.name}:{a_.key} {hz:.1f}/s")
    check("walk and gallop cycles at a natural rate (no flicker)", not fast, ", ".join(sorted(set(fast))[:6]))
    import motions as MM
    feet = []                                                                    # characters' feet must stand above the subtitle strip
    for s_ in shots:
        for frac in (0.1, 0.5, 0.9):
            t = s_.dur * frac
            z, cx, cy = SC.cam_at(s_, t)
            for a_ in s_.actors:
                if not hasattr(a_, "pos_at"):
                    continue
                x, y = a_.pos_at(t)
                y2, _ = MM.stage(y)
                xs = (x - cx * 1920) * z + 960
                ys = (y2 - cy * 1080) * z + 540
                if 0 < xs < 1920 and ys > 885 and s_.bg != "endcard":
                    feet.append(f"{s_.name}:{a_.key}@{round(ys)}")
    check("no character's feet or face in the subtitle zone", not feet, ", ".join(sorted(set(feet))[:8]))
    # characters stand on the floor: not on walls (floors.json) and not in water (colour under the feet)
    import json as _json
    floors = _json.loads((Path(__file__).parent / "floors.json").read_text(encoding="utf-8"))
    from PIL import ImageDraw as _ID
    used = sorted({s_.bg[6:] for s_ in shots if s_.bg.startswith("plate:")})
    unreviewed = [p_ for p_ in used if p_ not in floors and not (p_.endswith("_air") and p_[:-4] in floors)]   # aerial openers have no characters
    check("every background's floor reviewed (floors.json)", not unreviewed, ", ".join(unreviewed))
    masks = {}
    for p_ in used:
        if p_ in floors:
            m_ = Image.new("L", (1920, 1080), 0)
            for poly in floors[p_]["walls"]:
                _ID.Draw(m_).polygon([tuple(v) for v in poly], fill=255)
            masks[p_] = m_
    offfloor = []
    for s_ in shots:
        if not s_.bg.startswith("plate:") or floors.get(s_.bg[6:], {}).get("map"):
            continue
        p_ = s_.bg[6:]
        for frac in (0.1, 0.5, 0.9):
            t = s_.dur * frac
            bgf = SC.plate_frame(p_, t, s_.dur).convert("RGB")
            for a_ in s_.actors:
                if not hasattr(a_, "pos_at") or (getattr(a_, "hide", None) and a_.hide[0] <= t < a_.hide[1]):
                    continue
                x, y = a_.pos_at(t)
                y2, _ = MM.stage(y)
                if not (0 <= x < 1920 and 0 <= y2 < 1080):
                    continue
                wet = 0
                pts = [(int(x + dx), int(y2 + dy)) for dx in (-20, -10, 0, 10, 20) for dy in (-4, 4)]
                pts = [q for q in pts if 0 <= q[0] < 1920 and 0 <= q[1] < 1080]
                for q in pts:
                    r_, g_, b_ = bgf.getpixel(q)
                    wet += (b_ > r_ + 30 and g_ > r_ + 25)
                on_wall = p_ in masks and masks[p_].getpixel((int(x), int(min(1079, y2)))) > 0
                if on_wall or (pts and wet > len(pts) * 0.5):
                    offfloor.append(f"{s_.name}:{a_.key}@{int(x)},{int(y2)}{' wall' if on_wall else ' water'}")
    check("characters' feet on the floor (not on walls or water)", not offfloor, ", ".join(sorted(set(offfloor))[:10]))

    # on-screen text never covers a character
    tboxes, cboxes = [], []
    orig_t, orig_tf, orig_paint = ImageDraw.ImageDraw.text, MM.tile_for, MM.Performer.paint
    def spy2(self, xy, text, fill=None, font=None, anchor=None, *a, **kw):
        try:
            if getattr(self, "_image", None) is not None and self._image.size == (1920, 1080):
                tboxes.append((text, self.textbbox(xy, text, font=font, anchor=anchor)))
        except Exception:
            pass
        return orig_t(self, xy, text, fill, font, anchor, *a, **kw)
    last = []
    def tf(*a, **kw):
        r_ = orig_tf(*a, **kw)
        last.append(r_)
        return r_
    tf.cache_clear = getattr(orig_tf, "cache_clear", lambda: None)               # some storyboards reset the tile cache
    def paint(self, frame, t):
        last.clear()
        orig_paint(self, frame, t)
        if last:
            tile, ax, ay = last[-1]
            x, y = self.pos_at(t)
            y, _ = MM.stage(y)
            bb = tile.getbbox()
            if bb and not getattr(self, "bg_extra", False):                  # small background passers-by may pass behind cards
                cboxes.append((self.key, (x - ax + bb[0], y - ay + bb[1], x - ax + bb[2], y - ay + bb[3])))
    ImageDraw.ImageDraw.text, MM.tile_for, MM.Performer.paint = spy2, tf, paint
    covered = []
    try:
        for s_ in shots:
            for frac in (0.2, 0.5, 0.8):
                tboxes.clear(); cboxes.clear()
                SC.render_frame(s_, s_.dur * frac)
                for txt, (a0, b0, a1, b1) in tboxes:
                    area = max(1, (a1 - a0) * (b1 - b0))
                    for key, (c0, d0, c1, d1) in cboxes:
                        ov = max(0, min(a1, c1) - max(a0, c0)) * max(0, min(b1, d1) - max(b0, d0))
                        if ov > 0.2 * area:
                            covered.append(f"{s_.name}:{txt[:24]!r} over {key}")
    finally:
        ImageDraw.ImageDraw.text, MM.tile_for, MM.Performer.paint = orig_t, orig_tf, orig_paint
    check("on-screen text never covers a character", not covered, ", ".join(sorted(set(covered))[:10]))
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
            if F.YEAR_RE.search(" ".join(body)):
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
        check("film rendered from the current storyboard code (not stale)", bool(m) and m.group(1) == buildstamp.digest(module),
              f"film {m.group(1) if m else 'unstamped'}, code {buildstamp.digest(module)}")
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
    import buildstamp

    def fb_fresh(path):
        meta = subprocess.run([ff(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
        m = re.search(r"comment\s*:\s*te-fb:(\w+)", meta)
        return bool(m) and m.group(1) == buildstamp.fb_digest(module), (m.group(1) if m else "unstamped")

    fbv = folder / "Facebook" / f"{ep} - Facebook video (upload this).mp4"
    if fbv.exists():
        ok, got = fb_fresh(fbv)
        check("Facebook video made from the current film and caption code", ok, f"file {got}, code {buildstamp.fb_digest(module)}")
    cut_keys = [module] + [k for k in F.CUTS if F.CUTS[k].get("module") == module]
    yrs = []
    for k in cut_keys:
        _, sg, _ = F.plan(k)
        for seg in sg:
            for text, a_, b_ in seg["chunks"]:
                if F.YEAR_RE.search(text) or len(text) > 90:
                    yrs.append(f"{k}:{seg['lid']}")
    check("Facebook/clip captions: phrases short, years as digits", not yrs, ", ".join(sorted(set(yrs))[:8]))
    clips = sorted((folder / "Short clips").glob(f"{ep} - Short clip *.mp4"))
    for c in clips:
        ok, got = fb_fresh(c)
        check(f"clip made from current film and caption code: {c.name[13:40]}", ok, got)
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

    # 8. added 14 Nov 2026 (owner): clean folders, every language, no clicks, sound credit, posting texts complete
    allowed = {"YouTube", "Facebook", "Short clips"}
    extra = [p.name for p in folder.iterdir() if p.name not in allowed]
    extra += [str(p.relative_to(folder)) for p in (folder / "YouTube").iterdir() if p.is_dir() and p.name != "Subtitles - other languages"]
    extra += [str(p.relative_to(folder)) for sub in ("Facebook", "Short clips") for p in (folder / sub).iterdir() if p.is_dir()]
    check("episode folder clean (only YouTube / Facebook / Short clips)", not extra, ", ".join(extra))
    fb_files = sorted((folder / "Facebook").glob("*.mp4"))
    check("exactly one Facebook video", len(fb_files) == 1, ", ".join(p.name for p in fb_files))
    import check_translations as CT
    en = folder / "YouTube" / f"{ep} - Subtitles (English).srt"
    for lang in ["Hindi", "Spanish", "Portuguese", "Arabic", "Indonesian"]:
        tr = folder / "YouTube" / "Subtitles - other languages" / f"{ep} - Subtitles ({lang}).srt"
        errs = CT.check(en, tr) if (tr.exists() and en.exists()) else ["missing"]
        check(f"subtitles ({lang}): same cues and timings as English", not errs, "; ".join(errs[:3]))
    import numpy as np

    def peak(path):
        r = subprocess.run([ff(), "-nostdin", "-loglevel", "error", "-i", str(path), "-ac", "2", "-ar", "48000", "-f", "f32le", "-"],
                           capture_output=True)
        a = np.frombuffer(r.stdout, dtype=np.float32)
        return float(np.abs(a).max()) if a.size else 0.0
    for path in [folder / "YouTube" / f"{ep} - Full Film.mp4", *fb_files, *clips]:
        if path.exists():
            pk = peak(path)
            check(f"no clicks or distortion (peak <= full scale): {path.name[:40]}", pk <= 1.0, f"{pk:.2f}")
    if up.exists():
        s = up.read_text(encoding="utf-8")
        desc = s.split("DESCRIPTION\n", 1)[1].split("\nTAGS", 1)[0]
        check("sound-effects credit in the description (CC BY)", "Sound effects:" in desc and "CC BY 4.0" in desc)
        check("upload text has pinned comment, playlist and other-language steps",
              all(k in s for k in ("PINNED COMMENT", "PLAYLIST", "SUBTITLES IN OTHER LANGUAGES")))
    ct = folder / "Short clips" / f"{ep} - Short clips post text.txt"
    if ct.exists():
        st = ct.read_text(encoding="utf-8")
        titles = re.findall(r"^Shorts title: (.+)$", st, re.M)
        check("3 Shorts titles, each under 100 characters", len(titles) == 3 and all(len(t) < 100 for t in titles), f"{len(titles)} titles")
        check("clips text explains YouTube 'Related video' step", "Related video" in st)
    promo = [str(p.relative_to(folder)) for p in folder.rglob("*.txt")
             if re.search(r"every (week|day|saturday|sunday)", p.read_text(encoding="utf-8"), re.I)]
    check("no schedule promises ('every Saturday' etc.) in texts", not promo, ", ".join(promo))

    # 9. added 15 Nov 2026 (owner + outside review): cinematic camera, living places, personality, sources, publishing pack
    epn = int(re.search(r"Episode (\d+)", folder.name).group(1))
    strict = epn >= 4                                                            # rules that every NEW episode must meet
    if getattr(SC, "LIVE_CAM", False):
        locked = []
        for s_ in shots:
            if s_.bg == "endcard" or s_.dur < 2.0:
                continue
            cams = [SC.cam_at(s_, s_.dur * f_ / 24) for f_ in range(1, 24)]                # anywhere in the shot counts
            if max(max(c_[i] for c_ in cams) - min(c_[i] for c_ in cams) for i in range(3)) < 0.004:
                locked.append(s_.name)
        locked = [n_ for n_ in locked if n_ not in getattr(SC, "STILL", set())]      # deliberate stillness is declared in SC.STILL
        nshots = sum(1 for s_ in shots if s_.bg != "endcard" and s_.dur >= 2.0)
        check("camera is purposeful: undeclared locked shots are rare (under 20%)", len(locked) <= 0.2 * nshots,
              f"{len(locked)}/{nshots}: " + ", ".join(locked[:8]))
        import life as _LF
        dup = []
        for s_ in shots:
            ex = sorted((a_.pos_at(s_.dur / 2)[0], a_.key, a_.scale) for a_ in s_.actors if getattr(a_, "bg_extra", False))
            dup += [f"{s_.name}:{k1.split(':')[-1]}" for (x1, k1, s1), (x2, k2, s2) in zip(ex, ex[1:])
                    if k1 == k2 and abs(x1 - x2) < 140 * max(s1, s2) and abs(s1 - s2) < 0.01 and not k1.endswith("camel_walk")]
        check("background people: no identical figures side by side", not dup, ", ".join(sorted(set(dup))[:8]))
    else:
        check("camera moves on still shots (switched off for this published episode)", not strict)
    try:
        import life as LF
        thin = [s_.name for s_ in shots if s_.bg.startswith("plate:") and s_.bg[6:] in LF.LIFE
                and sum(1 for a_ in s_.actors if getattr(a_, "bg_extra", False)) < 2]
        used_life = any(getattr(a_, "bg_extra", False) for s_ in shots for a_ in s_.actors)
        if used_life or strict:
            check("places are alive: background people in every town/camp/dock shot", used_life and not thin, ", ".join(thin[:8]))
    except Exception as e_:
        check("places are alive: background people", False, str(e_))
    who = [K.LINES[lid]["who"] for _nm, lid, _t in K.CUES]
    hosts = {"penny", "atlas", "quill", "zed", "pike"}
    spoke = {h_: who.count(h_) for h_ in hosts}
    others = sum(v for k_, v in spoke.items() if k_ != "penny")
    share = others / max(1, len(who))
    check("every host speaks (personality on screen)", all(v >= (2 if strict else 1) for v in spoke.values()),
          ", ".join(f"{k_} {v}" for k_, v in sorted(spoke.items())))
    check("hosts talk to each other: at least 35% of lines are not the presenter's", share >= 0.35, f"{share:.0%}")
    closeups = sum(1 for s_ in shots if any(SC.cam_at(s_, s_.dur * f_)[0] >= 1.25 for f_ in (0.2, 0.4, 0.6, 0.8)))
    check("close-ups: at least 8 shots go in close on a character", closeups >= 8, f"{closeups} shots")
    if strict:
        mod = sys.modules[module]
        serious = getattr(mod, "SERIOUS", None)
        check("serious scenes are declared (SERIOUS = {...} in the storyboard)", serious is not None)
        if serious is not None:
            jokes = [f"{nm}:{lid}" for nm, lid, _t in K.CUES if nm in serious and K.LINES[lid]["who"] in ("pike", "zed")]
            check("no comic lines in scenes marked serious", not jokes, ", ".join(jokes[:6]))
        air = {s_.bg[6:-4] for s_ in shots if s_.bg.startswith("plate:") and s_.bg.endswith("_air")}
        from collections import Counter
        mains = [p_ for p_, n_ in Counter(s_.bg[6:] for s_ in shots if s_.bg.startswith("plate:") and not s_.bg.endswith("_air")).items()
                 if n_ >= 3 and not floors.get(p_, {}).get("interior") and not floors.get(p_, {}).get("map")]
        miss = [p_ for p_ in mains if p_ not in air]
        check("each main place opens with an aerial establishing shot", not miss, ", ".join(miss))
        facts = Path(__file__).parent / "facts" / f"{module}.json"
        if facts.exists():
            fj = json.loads(facts.read_text(encoding="utf-8"))
            weak = [lid for _nm, lid, _t in K.CUES if not fj.get(lid, {}).get("no_claim") and len(fj.get(lid, {}).get("sources", [])) < 2]
            check("every factual line has two sources recorded", not weak, ", ".join(weak[:10]))
        else:
            check("fact sheet with two sources per line (scripts/cartoon/facts/<module>.json)", False, "missing")
    want_langs = ["Hindi", "Spanish", "Portuguese", "Arabic", "Indonesian", "French", "German", "Japanese", "Italian"]
    have = [l_ for l_ in want_langs if (folder / "YouTube" / "Subtitles - other languages" / f"{ep} - Subtitles ({l_}).srt").exists()]
    for lang in want_langs[5:]:
        tr = folder / "YouTube" / "Subtitles - other languages" / f"{ep} - Subtitles ({lang}).srt"
        errs = CT.check(en, tr, maxlen=24 if lang == "Japanese" else 46) if (tr.exists() and en.exists()) else ["missing"]
        check(f"subtitles ({lang}): same cues and timings as English", not errs, "; ".join(errs[:3]))
    if up.exists():
        s = up.read_text(encoding="utf-8")
        check("upload text has 3 title options and a community post", "TITLE OPTIONS" in s and "COMMUNITY POST" in s)
    try:
        import sound_design as SD_
        man = json.loads((SD_.SFX / "manifest.json").read_text(encoding="utf-8"))
        nolic = [e_["name"] for e_ in man if not (e_.get("licence") and e_.get("source_url")) and not e_.get("exclude")]
        check("licence and source recorded for every sound", not nolic, ", ".join(nolic[:6]))
    except Exception as e_:
        check("licence record for sounds readable", False, str(e_)[:80])

    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)}/{len(results)} checks passed" + ("" if not fails else f"  ({len(fails)} FAILED)"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
