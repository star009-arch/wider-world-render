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


def digits(text):
    for a, b in SPOKEN:
        text = text.replace(a, b)
    return text


def plan(module):
    E = importlib.import_module(module)
    K = E.K
    ss = K.shots()
    start, acc = {}, 0.0
    for sh in ss:
        start[sh.name] = acc
        acc += sh.dur
    when = {lid: start[nm] + t0 for nm, lid, t0 in K.CUES}
    segs, t = [], 0.0
    for lid in CUTS[module]["lines"]:
        d = K.dur(lid)
        a = max(0.0, when[lid] - PRE)
        b = when[lid] + d + POST
        segs.append({"lid": lid, "src": (a, b), "at": t, "voice_at": t + (when[lid] - a), "dur": d,
                     "who": K.LINES[lid]["who"], "text": digits(K.LINES[lid]["text"])})
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
                        ";".join(flt), ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", str(mixd)])
    return mixd


def layout(cut, audio, segs, total, out, W, H, cfg, ff):
    """Compose each frame: blurred backdrop, badge + title, the full 16:9 picture, captions, end card."""
    vert = H > 1500
    pw = W
    ph = int(pw * 9 / 16)
    py = 430 if vert else 330
    cap_y = py + ph + (110 if vert else 50)
    fh = S.font(84 if vert else 62, "impact")
    fb = S.font(56 if vert else 50)
    fs = S.font(46 if vert else 42)
    fn = S.font(38 if vert else 34)
    dec = subprocess.Popen([ff, "-nostdin", "-loglevel", "error", "-i", str(cut), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([ff, "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total + END:.2f}", str(out)],
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
        bg.paste(fr.resize((pw, ph), Image.LANCZOS), (0, py))
        dr = ImageDraw.Draw(bg)
        dr.rounded_rectangle([W / 2 - 200, 40, W / 2 + 200, 104], radius=18, fill=(180, 40, 40))
        dr.text((W / 2, 72), "TINY EMPIRES", font=S.font(40), fill=(255, 236, 190), anchor="mm")
        for i, ln in enumerate(cfg["title"]):
            dr.text((W / 2, (190 if vert else 150) + i * (92 if vert else 68)), ln, font=fh, fill=(255, 255, 255) if i == 0 else (255, 206, 60),
                    anchor="mm", stroke_width=7, stroke_fill=(16, 12, 16))
        if t < total:
            cur = [s for s in segs if s["voice_at"] - 0.05 <= t < s["voice_at"] + s["dur"] + 0.2]
            sec = [s for s in segs if s["at"] <= t and s["lid"] in cfg["chapters"]]
            if sec:
                dr.text((W / 2, py - 34), cfg["chapters"][sec[-1]["lid"]].upper(), font=fn, fill=(255, 206, 60), anchor="mm",
                        stroke_width=4, stroke_fill=(16, 12, 16))
            if cur:
                s = cur[-1]
                dr.text((W / 2, cap_y), NAMES.get(s["who"], s["who"].upper()), font=fn, fill=(255, 206, 60), anchor="mm",
                        stroke_width=4, stroke_fill=(16, 12, 16))
                wrap = textwrap.wrap(s["text"], 30 if vert else 34)
                f = fb if len(wrap) <= 4 else fs
                step = 70 if len(wrap) <= 4 else 58
                for i, ln in enumerate(wrap[:6 if vert else 5]):
                    dr.text((W / 2, cap_y + 70 + i * step), ln, font=f, fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(16, 12, 16))
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
            dr.text((W / 2, cy + 150), "New episode every Saturday", font=S.font(48), fill=(255, 206, 60), anchor="mm")
        enc.stdin.write(bg.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    dec.kill()
    print("wrote", out, round(total + END, 1), "s")


def main():
    module, film, outdir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    music = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("D:/Temp/cartoon/sneaky_snitch.mp3")
    cfg = CUTS[module]
    K, segs, total = plan(module)
    ff = K.SC.ffmpeg()
    import os
    work = Path(os.environ.get("FB_WORK", str(Path("D:/Temp/cartoon") / module / "fb_work")))
    work.mkdir(parents=True, exist_ok=True)
    cut = picture(film, segs, work, ff)
    audio = sound(K, segs, total, music, work, ff)
    outdir.mkdir(parents=True, exist_ok=True)
    tag = cfg["ep"]
    only = sys.argv[5] if len(sys.argv) > 5 else "both"
    if only in ("both", "4x5"):
        layout(cut, audio, segs, total, outdir / f"{tag} - Facebook (2 min, 4x5 feed).mp4", 1080, 1350, cfg, ff)
    if only in ("both", "9x16"):
        layout(cut, audio, segs, total, outdir / f"{tag} - Facebook (2 min, 9x16 reel).mp4", 1080, 1920, cfg, ff)


if __name__ == "__main__":
    main()
