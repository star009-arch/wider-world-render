"""Facebook "whole story in ~2 minutes" cut of a Tiny Empires episode, in 4:5 (feed) and 9:16 (reels).

Picks one or two lines from every section of the episode, takes those moments from the finished 16:9 film (picture only),
rebuilds the sound from the clean voice takes plus one continuous ducked music bed (no jumpy music cuts), and lays it out:
channel badge + title on top, the full 16:9 picture (nothing cropped), big burned-in captions (most Facebook viewing is muted),
and an end card "Full episode on YouTube".

  python scripts/cartoon/fb_cut.py ep03 <film.mp4> <out dir> [music]
"""
from __future__ import annotations

import importlib
import re
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sets as S  # noqa: E402

FPS = 30
PRE, POST, END = 0.25, 0.35, 4.0
CUTS = {
    "ep02": {
        "title": ["HOW THE MONGOLS CONQUERED", "ALMOST EVERYTHING"],
        "ep": "Episode 02",
        "lines": ["M01", "M03", "M04", "M08", "M11", "M13", "M15", "M17", "M24", "M25", "M26", "M31", "M35", "M37", "M38", "M39", "M46"],
        "chapters": {"M01": "The hook", "M08": "Temujin", "M13": "The army", "M24": "The war with Khwarazm", "M31": "Into Europe",
                     "M35": "Baghdad and Japan", "M39": "Kublai Khan", "M46": "From a boy to an empire"},
    },
    "eic": {
        "title": ["HOW A COMPANY", "TOOK OVER INDIA"],
        "ep": "Episode 03",
        "lines": ["E01", "E03", "E04", "E06", "E08", "E12", "E19", "C02", "C04", "E23", "E24", "E25", "E28", "E29", "E35", "E37", "E39",
                  "E41", "E43", "E45", "E48", "E50"],
        "chapters": {"E01": "The hook", "E06": "London, 1600", "E12": "Spices", "E19": "Mughal India", "C02": "The cloth craze",
                     "E23": "A shop with an army", "E28": "Siraj and Calcutta", "E35": "The secret deal", "E39": "Plassey", "E45": "The traders become rulers"},
    },
    "ep03": {
        "title": ["HOW THE EGYPTIANS BUILT", "THE GREAT PYRAMIDS"],
        "ep": "Episode 01",
        "lines": ["G01", "G02", "G10", "G12", "G14", "G19", "G21", "G25", "G28", "G29", "G30", "G34", "G35", "G37", "G38", "G39", "G42", "G45"],
        "chapters": {"G01": "The hook", "G10": "Why a pyramid?", "G14": "Practice pyramids", "G19": "Khufu goes big",
                     "G25": "Who really built it", "G34": "A 4,500-year-old diary", "G37": "Moving the stones", "G45": "The last wonder"},
    },
}
def _clip(module, ep, n, name, title, lines):
    return {"module": module, "ep": ep, "clip": f"Short clip {n} - {name}", "title": title, "lines": lines, "chapters": {}}


CUTS.update({
    "ep03_c1": _clip("ep03", "Episode 01", 1, "No cranes", ["HOW DID THEY BUILD", "THE GREAT PYRAMID?"], ["G01", "G02", "G03", "G04", "G05"]),
    "ep03_c2": _clip("ep03", "Episode 01", 2, "Not slaves", ["WHO REALLY BUILT", "THE PYRAMIDS?"], ["G25", "G26", "G27", "G28", "G29", "G30"]),
    "ep03_c3": _clip("ep03", "Episode 01", 3, "The wet sand trick", ["THE WET SAND", "TRICK"], ["G36", "G37", "G38", "G39", "G41", "G42"]),
    "ep02_c1": _clip("ep02", "Episode 02", 1, "Only horses", ["ONLY HORSES...", "VS EMPIRES"], ["M01", "M02", "M03", "M04", "M05"]),
    "ep02_c2": _clip("ep02", "Episode 02", 2, "The fake retreat", ["THE MONGOLS'", "FAKE RETREAT"], ["M14", "M15", "M16", "M17"]),
    "ep02_c3": _clip("ep02", "Episode 02", 3, "The caravan that started a war", ["THE CARAVAN THAT", "STARTED A WAR"], ["M23", "M24", "M25", "M26", "M27"]),
    "eic_c1": _clip("eic", "Episode 03", 1, "From spices to rulers", ["FROM SPICES", "TO RULERS"], ["E01", "E02", "E03", "E04", "E05"]),
    "eic_c2": _clip("eic", "Episode 03", 2, "The cloth craze", ["THE CLOTH CRAZE", "THAT BUILT AN EMPIRE"], ["C01", "C02", "C03", "C04", "C05"]),
    "eic_c3": _clip("eic", "Episode 03", 3, "Plassey in the rain", ["PLASSEY,", "23 JUNE 1757"], ["E39", "E40", "E41", "E42", "E43", "E44"]),
})


# lines whose 3D scenes carry wide on-screen graphics (icon rows, swatches): always shown full-frame
FORCE_FULL = {"E12", "E22", "C01", "C02", "C06", "G28", "Y03", "G21", "G22"}


SPOKEN = [("Twenty-third of June, seventeen fifty-seven", "23 June 1757"), ("eleven sixty-two", "1162"), ("twelve-oh-six", "1206"),
          ("twelve-eighteen", "1218"), ("twelve forty-one", "1241"), ("twelve fifty-eight", "1258"), ("twelve seventy-four", "1274"),
          ("twelve eighty-one", "1281"), ("twelve seventy-one", "1271"), ("twelve seventy-nine", "1279"), ("sixteen hundred", "1600"),
          ("sixteen-thirteen", "1613"), ("seventeen fifty-six", "1756"), ("seventeen fifty-seven", "1757"), ("seventeen sixty-five", "1765"),
          ("seventeen twenty-one", "1721"), ("seventeen hundred", "1700"),
          ("two point three million", "2.3 million"), ("two and a half tonnes", "2.5 tonnes"),
          ("one hundred and forty-six metres", "146 metres"), ("twenty-six fifty BC", "2650 BC"), ("twenty thirteen", "2013"),
          ("twenty eighteen", "2018"), ("nineteen fifty-four", "1954"), ("forty-three metres", "43 metres"),
          ("four and a half thousand", "4,500"), ("four thousand", "4,000"), ("twenty years", "20 years"), ("Twenty years", "20 years"),
          ("twenty-three years", "23 years"), ("forty-seven to forty-two centuries", "47 to 42 centuries")]
NAMES = {"penny": "PENNY", "atlas": "ATLAS", "quill": "QUILL", "zed": "ZED", "pike": "PIKE"}


_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
_TEENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
          "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_CENT = r"(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)"
_TAIL = r"(hundred|oh[- ](?:one|two|three|four|five|six|seven|eight|nine)|(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:-(?:one|two|three|four|five|six|seven|eight|nine))?|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)"
YEAR_RE = re.compile(r"\b" + _CENT + r"[- ]" + _TAIL + r"\b", re.I)


def _year(m):
    c = _TEENS[m.group(1).lower()] * 100
    t = m.group(2).lower()
    if t == "hundred":
        return str(c)
    if t.startswith("oh"):
        return str(c + _UNITS[t[3:]])
    if t in _TEENS:
        return str(c + _TEENS[t])
    parts = t.split("-")
    return str(c + _TENS[parts[0]] + (_UNITS[parts[1]] if len(parts) > 1 else 0))


def digits(text):
    for a, b in SPOKEN:
        text = text.replace(a, b)
    return YEAR_RE.sub(_year, text)                                              # any remaining spoken year -> digits


def _chunks(K, lid):
    """Phrases of one line timed word by word from the voice (make_srt.line_chunks): [(text, start, end)] relative to the line."""
    import make_srt
    return make_srt.line_chunks(K, lid)


_STAMP_MODULE = [None]


def _stamp():
    import buildstamp
    return buildstamp.fb_digest(_STAMP_MODULE[0])


def _phrase(seg, t):
    """The phrase being spoken at cut time t (only one text on screen, in sync with the voice)."""
    rel = t - seg["voice_at"]
    ch = seg["chunks"]
    for i, (text, a, b) in enumerate(ch):
        nxt = ch[i + 1][1] if i + 1 < len(ch) else b + 0.6
        if a - 0.05 <= rel < nxt:
            return text
    return None


def plan(module):
    E = importlib.import_module(CUTS[module].get("module", module))
    K = E.K
    ss = K.shots()
    start, acc = {}, 0.0
    for sh in ss:
        start[sh.name] = acc
        acc += sh.dur
    when = {lid: start[nm] + t0 for nm, lid, t0 in K.CUES}
    where = {lid: (nm, t0) for nm, lid, t0 in K.CUES}
    by_name = {sh.name: sh for sh in ss}
    segs, t = [], 0.0
    for lid in CUTS[module]["lines"]:
        d = K.dur(lid)
        a = max(0.0, when[lid] - PRE)
        b = when[lid] + d + POST
        who = K.LINES[lid]["who"]
        nm, t0 = where[lid]
        sx = None                                                                # where the speaker stands in that shot
        xs = []                                                                  # where everyone stands (on screen)
        for p in by_name[nm].actors:
            x = p.pos_at(t0 + d / 2)[0]
            if -60 < x < 1980:
                xs.append(x)
            if getattr(p, "key", None) == who and sx is None:
                sx = x
        span = (min(xs) - 110, max(xs) + 110) if xs else None
        if span and span[1] - span[0] > 1600 + 60:                               # wide casts (riders, crews, armies): show everything
            span = None
            sx = None
            wide = True
        else:
            wide = False
        full = wide or lid in FORCE_FULL or not by_name[nm].bg.startswith("plate:")  # cards, maps, wide casts, big graphics: never crop
        segs.append({"lid": lid, "src": (a, b), "at": t, "voice_at": t + (when[lid] - a), "dur": d, "sx": sx, "span": span, "full": full,
                     "who": who, "text": digits(K.LINES[lid]["text"]), "chunks": _chunks(K, lid)})
        t += b - a
    return K, segs, t


def picture(film, segs, work, ff):
    """Cut the 16:9 picture (no audio) to the chosen moments."""
    parts = []
    for i, s in enumerate(segs):
        p = work / f"seg{i:02d}.mp4"
        a, b = s["src"]
        subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-i", str(film), "-t", f"{b - a:.3f}", "-an",
                        "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", str(p)], check=True)
        parts.append(p)
    lst = work / "segs.txt"
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts))
    out = work / "cut169.mp4"
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    return out


def sound(K, segs, total, music, work, ff):
    ins, flt, labs = [], [], []
    for n, s in enumerate(segs):
        ins += ["-i", str(K.VOICE / f"{s['lid']}.mp3")]
        ms = int(s["voice_at"] * 1000)
        flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{n}]")
        labs.append(f"[v{n}]")
    flt.append(f"{''.join(labs)}amix=inputs={len(segs)}:normalize=0:duration=longest,apad=whole_dur={total:.2f},atrim=0:{total:.2f}[dia]")
    bus = work / "dia.wav"
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(flt), "-map", "[dia]", "-ar", "48000", str(bus)],
                   check=True)
    mixd = work / "mix.m4a"
    flt = ["[0:a]anull[key]", "[1:a]anull[dia]",
           f"[2:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume=0.22,afade=t=in:d=2,"
           f"afade=t=out:st={total - 2.5:.2f}:d=2.5[mus]",
           "[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck]",
           f"[duck][dia]amix=inputs=2:normalize=0:duration=first,{{LN}},alimiter=limit=0.89,afade=t=in:d=0.15,atrim=0:{total:.2f}[a]"]
    K.two_pass_loudnorm([ff, "-nostdin", "-y", "-loglevel", "error"], ["-i", str(bus), "-i", str(bus), "-stream_loop", "-1", "-i", str(music)],
                        ";".join(flt), ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(mixd)])
    return mixd


def layout(cut, audio, segs, total, out, W, H, cfg, ff):
    """Compose each frame: blurred backdrop, badge + title, the full 16:9 picture, captions, end card."""
    vert = H > 1500
    CW = 1600                                                                    # 3:2-ish window of the 16:9 frame -> a bigger picture
    pw = W
    ph = 1100 if vert else int(pw * 1080 / CW)                                   # vertical: a tall picture area (about 57% of the screen)
    py = 335 if vert else 215
    cap_y = py + ph + (60 if vert else 40)
    CWV = int(1080 * 1080 / ph)                                                  # narrowest window that fills the tall area
    fh = S.font(84 if vert else 56, "impact")
    fb = S.font(56 if vert else 44)
    fs = S.font(46 if vert else 38)
    fn = S.font(38 if vert else 30)

    def window_v(t):
        """Vertical: the tightest window that still holds the whole cast (bigger people when few are on screen)."""
        cur = [s for s in segs if s["at"] <= t]
        if not cur:
            return 960, 1920
        sg = cur[-1]
        if sg["span"]:
            cw = int(min(1920, max(CWV, sg["span"][1] - sg["span"][0])))
            cx = (sg["span"][0] + sg["span"][1]) / 2
        elif sg["sx"] is not None:
            cw, cx = CWV, sg["sx"]
        else:
            cw, cx = 1920, 960
        return int(min(max(cx, cw / 2), 1920 - cw / 2)), cw

    def window(t):
        """Crop centre: keep the speaker in frame (host on the right -> show the right part), else the middle."""
        cur = [s for s in segs if s["at"] <= t]
        if not cur:
            return 960
        sg = cur[-1]
        if sg["span"] and sg["span"][1] - sg["span"][0] <= CW + 60:             # the whole cast fits: frame them all
            cx = (sg["span"][0] + sg["span"][1]) / 2
        elif sg["sx"] is not None:                                               # too wide: keep the speaker and as much as possible
            cx = sg["sx"] - CW * 0.22
        else:
            cx = 960
        return int(min(max(cx, CW / 2), 1920 - CW / 2))
    dec = subprocess.Popen([ff, "-nostdin", "-loglevel", "error", "-i", str(cut), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([ff, "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", "-metadata", f"comment=te-fb:{_stamp()}", "-t", f"{total + END:.2f}", str(out)],
                           stdin=subprocess.PIPE)
    last = None
    n = 0
    nframes = int((total + END) * FPS)
    while n < nframes:
        t = n / FPS
        raw = dec.stdout.read(1920 * 1080 * 3) if t < total else b""
        if len(raw) == 1920 * 1080 * 3:
            last = Image.frombytes("RGB", (1920, 1080), raw)
        fr = last
        bg = fr.resize((int(H * 16 / 9), H), Image.BILINEAR)
        x0 = (bg.width - W) // 2
        bg = bg.crop((x0, 0, x0 + W, H)).filter(ImageFilter.GaussianBlur(30))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (12, 10, 16)), 0.5)
        cur_seg = [s for s in segs if s["at"] <= t]
        if t < total and cur_seg and cur_seg[-1]["full"]:
            fh_ = int(pw * 9 / 16)                                               # whole 16:9 frame, centred in the picture area
            bg.paste(fr.resize((pw, fh_), Image.LANCZOS), (0, py + (ph - fh_) // 2))
        elif vert and t < total:
            cx, cw = window_v(t)
            win = fr.crop((cx - cw // 2, 0, cx - cw // 2 + cw, 1080))
            h_ = int(pw * 1080 / cw)
            bg.paste(win.resize((pw, h_), Image.LANCZOS), (0, py + (ph - h_) // 2))
        else:
            cx = window(t) if t < total else 960
            win = fr.crop((cx - CW // 2, 0, cx + CW // 2, 1080)) if t < total else fr.crop((240, 0, 1680, 1080))
            bg.paste(win.resize((pw, ph if not vert else int(pw * 1080 / CW)), Image.LANCZOS), (0, py if not vert else py + (ph - int(pw * 1080 / CW)) // 2))
        dr = ImageDraw.Draw(bg)
        dr.rounded_rectangle([W / 2 - 200, 40, W / 2 + 200, 104], radius=18, fill=(180, 40, 40))
        dr.text((W / 2, 72), "TINY EMPIRES", font=S.font(40), fill=(255, 236, 190), anchor="mm")
        for i, ln in enumerate(cfg["title"]):
            dr.text((W / 2, (190 if vert else 128) + i * (92 if vert else 58)), ln, font=fh, fill=(255, 255, 255) if i == 0 else (255, 206, 60),
                    anchor="mm", stroke_width=7, stroke_fill=(16, 12, 16))
        if t < total:
            cur = [s for s in segs if s["voice_at"] - 0.05 <= t < s["voice_at"] + s["dur"] + 0.2]
            sec = [s for s in segs if s["at"] <= t and s["lid"] in cfg["chapters"]]
            if sec:
                lab = cfg["chapters"][sec[-1]["lid"]].upper()
                ly = py - 34 if vert else py + 30
                if not vert:
                    tw = dr.textlength(lab, font=fn)
                    dr.rounded_rectangle([W / 2 - tw / 2 - 22, ly - 24, W / 2 + tw / 2 + 22, ly + 24], radius=14, fill=(16, 12, 16))
                dr.text((W / 2, ly), lab, font=fn, fill=(255, 206, 60), anchor="mm", stroke_width=4, stroke_fill=(16, 12, 16))
            phrase = _phrase(cur[-1], t) if cur else None
            if cur and phrase:
                s = dict(cur[-1], text=phrase)
                dr.text((W / 2, cap_y), NAMES.get(s["who"], s["who"].upper()), font=fn, fill=(255, 206, 60), anchor="mm",
                        stroke_width=4, stroke_fill=(16, 12, 16))
                if vert:
                    wrap = textwrap.wrap(s["text"], 30)
                    f, step, top = (fb, 70, 70) if len(wrap) <= 5 else (fs, 58, 64)
                else:
                    wrap = textwrap.wrap(s["text"], 40)
                    f, step, top = (fb, 58, 56) if len(wrap) <= 3 else (fs, 48, 52)
                    if len(wrap) > 5:
                        wrap = textwrap.wrap(s["text"], 48)
                        f, step = S.font(32), 40
                for i, ln in enumerate(wrap):                                    # always the whole line, never cut
                    dr.text((W / 2, cap_y + top + i * step), ln, font=f, fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(16, 12, 16))
        else:
            k = min(1.0, (t - total) / 0.4)
            ov = Image.new("RGBA", (W, H), (12, 10, 16, int(200 * k)))
            bg = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
            dr = ImageDraw.Draw(bg)
            cy = H // 2
            dr.text((W / 2, cy - 160), "WATCH THE FULL EPISODE", font=S.font(80 if vert else 70, "impact"), fill=(255, 255, 255), anchor="mm",
                    stroke_width=6, stroke_fill=(16, 12, 16))
            dr.rounded_rectangle([W / 2 - 400, cy - 70, W / 2 + 400, cy + 70], radius=30, fill=(200, 30, 30))
            dr.text((W / 2, cy), "on YouTube: Tiny Empires", font=S.font(58), fill=(255, 255, 255), anchor="mm")
            dr.text((W / 2, cy + 150), "Animated history, made with care", font=S.font(48), fill=(255, 206, 60), anchor="mm")
        enc.stdin.write(bg.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    dec.kill()
    print("wrote", out, round(total + END, 1), "s")


def layout_wide(cut, audio, segs, total, out, cfg, ff):
    """16:9 version for laptops and TVs: the full picture, a small badge, the section name, captions on a band at the bottom."""
    W, H = 1920, 1080
    fb, fs, fn = S.font(46), S.font(40), S.font(32)
    dec = subprocess.Popen([ff, "-nostdin", "-loglevel", "error", "-i", str(cut), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([ff, "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
                            "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                            "-t", f"{total + END:.2f}", str(out)], stdin=subprocess.PIPE)
    last = None
    for n in range(int((total + END) * FPS)):
        t = n / FPS
        raw = dec.stdout.read(W * H * 3) if t < total else b""
        if len(raw) == W * H * 3:
            last = Image.frombytes("RGB", (W, H), raw)
        bg = last.copy()
        if t < total:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.rounded_rectangle([30, 26, 330, 82], radius=14, fill=(180, 40, 40, 235))
            cur = [s for s in segs if s["voice_at"] - 0.05 <= t < s["voice_at"] + s["dur"] + 0.2]
            phrase = _phrase(cur[-1], t) if cur else None
            if not phrase:
                cur = []
            if cur:
                wrap = textwrap.wrap(phrase, 62)
                f, step = (fb, 56) if len(wrap) <= 3 else (fs, 46)
                band = 40 + len(wrap) * step
                od.rectangle([0, H - band - 30, W, H], fill=(10, 8, 12, 170))
            bg = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
            dr = ImageDraw.Draw(bg)
            dr.text((180, 54), "TINY EMPIRES", font=S.font(34), fill=(255, 236, 190), anchor="mm")
            sec = [s for s in segs if s["at"] <= t and s["lid"] in cfg["chapters"]]
            if sec:
                dr.text((360, 54), cfg["chapters"][sec[-1]["lid"]].upper(), font=fn, fill=(255, 206, 60), anchor="lm",
                        stroke_width=4, stroke_fill=(16, 12, 16))
            if cur and phrase:
                top = H - band - 30 + 20 + step / 2
                for i, ln in enumerate(wrap):
                    dr.text((W / 2, top + i * step), ln, font=f, fill=(255, 255, 255), anchor="mm", stroke_width=5, stroke_fill=(16, 12, 16))
        else:
            k = min(1.0, (t - total) / 0.4)
            ov = Image.new("RGBA", (W, H), (12, 10, 16, int(200 * k)))
            bg = Image.alpha_composite(bg.convert("RGBA"), ov).convert("RGB")
            dr = ImageDraw.Draw(bg)
            dr.text((W / 2, H / 2 - 150), "WATCH THE FULL EPISODE", font=S.font(90, "impact"), fill=(255, 255, 255), anchor="mm",
                    stroke_width=6, stroke_fill=(16, 12, 16))
            dr.rounded_rectangle([W / 2 - 460, H / 2 - 70, W / 2 + 460, H / 2 + 70], radius=30, fill=(200, 30, 30))
            dr.text((W / 2, H / 2), "on YouTube: Tiny Empires", font=S.font(64), fill=(255, 255, 255), anchor="mm")
            dr.text((W / 2, H / 2 + 150), "Animated history, made with care", font=S.font(50), fill=(255, 206, 60), anchor="mm")
        enc.stdin.write(bg.tobytes())
    enc.stdin.close()
    enc.wait()
    dec.kill()
    print("wrote", out, round(total + END, 1), "s")


def main():
    module, film, outdir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    music = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("D:/Temp/cartoon/sneaky_snitch.mp3")
    cfg = CUTS[module]
    _STAMP_MODULE[0] = cfg.get("module", module)
    K, segs, total = plan(module)
    ff = K.SC.ffmpeg()
    import os
    work = Path(os.environ.get("FB_WORK", str(Path("D:/Temp/cartoon") / module / "fb_work")))
    work.mkdir(parents=True, exist_ok=True)
    cut = picture(film, segs, work, ff)
    audio = sound(K, segs, total, music, work, ff)
    outdir.mkdir(parents=True, exist_ok=True)
    tag = cfg["ep"] + (f" - {cfg['clip']}" if "clip" in cfg else "")
    only = sys.argv[5] if len(sys.argv) > 5 else "both"
    if only in ("both", "4x5"):
        layout(cut, audio, segs, total, outdir / (f"{tag} - Facebook (2 min, 4x5 feed).mp4" if "clip" not in cfg else f"{tag}.mp4"), 1080, 1350, cfg, ff)
    if only in ("both", "9x16"):
        layout(cut, audio, segs, total, outdir / f"{tag} - Facebook (2 min, 9x16 reel).mp4", 1080, 1920, cfg, ff)
    if only in ("both", "16x9"):
        layout_wide(cut, audio, segs, total, outdir / f"{tag} - Facebook (2 min, 16x9 laptop and TV).mp4", cfg, ff)


if __name__ == "__main__":
    main()
