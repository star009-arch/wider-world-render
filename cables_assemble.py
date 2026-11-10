"""Assemble the 12-minute undersea cables film from footage, 3D frames, maps/charts and narration. ffmpeg only (no project
code needed), so it runs on the render server, the laptop, or a free GitHub runner.

  python scripts/cables_assemble.py <shotlist.json> <work dir>

<work dir> holds:  clips/<file>   3d/<shot>/f_0001.png ...   visuals/<name>.mp4   narration/<scene>.flac|wav
                   music/<key>.<ext>
Output: <work dir>/out/the_hidden_internet.mp4 (1080p24, -14 LUFS) + timeline.json (scene start times, for the SRT/chapters).

Each scene lasts lead + its narration + tail. Its shots split that time by weight and cross-dissolve (XF) into each other;
scenes dissolve into each other (XS). 3D frames were rendered at half rate and are slowed 2x with motion interpolation.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

W, H, FPS = 1920, 1080, 24
XF, XS = 0.5, 0.8
FONT = os.environ.get("YTG_FONT", "C:/Windows/Fonts/segoeui.ttf")
FONT_B = os.environ.get("YTG_FONT_B", "C:/Windows/Fonts/segoeuib.ttf")
FONT_L = os.environ.get("YTG_FONT_L", "C:/Windows/Fonts/segoeuil.ttf")
THREADS = os.environ.get("YTG_X264_THREADS", "4")


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def run(args, what=""):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffmpeg failed ({what}): {r.stderr[-2000:]}")


def duration(p: Path) -> float:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(p)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def fpath(p: Path) -> str:
    """A path as drawtext's textfile/fontfile wants it: forward slashes, the drive colon escaped."""
    return str(p).replace("\\", "/").replace(":", "\\:")


class Film:
    def __init__(self, shotlist: Path, work: Path):
        self.cfg = json.loads(shotlist.read_text(encoding="utf-8"))
        self.work = work
        self.seg_dir = work / "segments"; self.seg_dir.mkdir(parents=True, exist_ok=True)
        self.txt_dir = work / "txt"; self.txt_dir.mkdir(parents=True, exist_ok=True)
        self.out = work / "out"; self.out.mkdir(parents=True, exist_ok=True)
        self.n_txt = 0

    def _txt(self, text: str) -> str:
        self.n_txt += 1
        p = self.txt_dir / f"t{self.n_txt:04d}.txt"
        p.write_text(text, encoding="utf-8")
        return fpath(p)

    def narration(self, sid: str):
        for ext in ("flac", "wav"):
            p = self.work / "narration" / f"{sid}.{ext}"
            if p.exists():
                return p
        return None

    # ---------------------------------------------------------------------------------------------------- one shot
    def overlay(self, shot: dict, d: float) -> str:
        """Credit bottom-left, caption top-left, both fading in and out with the shot."""
        f = ""
        fade = f"alpha='min(1,t/0.5)*min(1,({d:.3f}-t)/0.5)'"
        if shot.get("credit"):
            f += (f",drawtext=fontfile='{fpath(Path(FONT))}':textfile='{self._txt(shot['credit'])}':fontsize=22:fontcolor=white@0.72:"
                  f"x=48:y=h-56:shadowcolor=black@0.7:shadowx=1:shadowy=1:{fade}")
        if shot.get("caption"):
            f += (f",drawtext=fontfile='{fpath(Path(FONT_B))}':textfile='{self._txt(shot['caption'])}':fontsize=30:fontcolor=white@0.9:"
                  f"x=48:y=44:box=1:boxcolor=black@0.35:boxborderw=12:{fade}")
        if shot.get("title"):
            ta = "alpha='if(lt(t,0.8),0,if(lt(t,1.8),(t-0.8),if(lt(t,{e}),1,max(0,({e2}-t)))))'".format(e=d - 1.4, e2=d - 0.4)
            f += (f",drawtext=fontfile='{fpath(Path(FONT_L))}':textfile='{self._txt(shot['title'])}':fontsize=96:fontcolor=white:"
                  f"x=(w-text_w)/2:y=h*0.36:shadowcolor=black@0.5:shadowx=2:shadowy=2:{ta}")
            if shot.get("subtitle"):
                f += (f",drawtext=fontfile='{fpath(Path(FONT))}':textfile='{self._txt(shot['subtitle'])}':fontsize=40:fontcolor=white@0.85:"
                      f"x=(w-text_w)/2:y=h*0.36+130:shadowcolor=black@0.5:shadowx=2:shadowy=2:{ta}")
        return f

    def segment(self, key: str, shot: dict, d: float, drift: int) -> Path:
        out = self.seg_dir / f"{key}.mp4"
        if out.exists() and abs(duration(out) - d) < 0.08:
            return out
        kind, src, start = shot["kind"], shot.get("src", ""), float(shot.get("in", 0))
        # slow drift: crop a 1.06x frame and slide it across the shot (cheap stand-in for a camera move)
        dx = f"(iw-ow)/2+{drift}*(iw-ow)/2*(t/{d:.3f}-0.5)"
        pan = f"scale={int(W * 1.06)}:{int(H * 1.06)},crop={W}:{H}:x='{dx}':y='(ih-oh)/2'"
        if kind == "clip":
            inp = ["-ss", f"{start:.2f}", "-t", f"{d + 0.2:.3f}", "-i", self.work / "clips" / src]
            pre = shot.get("vf", "")
            if shot.get("aspect") == "4:3":             # archive film: keep the whole picture, blurred fill at the sides
                vf = (f"fps={FPS},{pre + ',' if pre else ''}split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                      f"boxblur=30:2,eq=brightness=-0.12[bg];[b]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0")
            else:
                vf = f"fps={FPS},{pre + ',' if pre else ''}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{pan}"
            vf += f",tpad=stop_mode=clone:stop_duration={d:.2f}"
        elif kind == "3d":
            frames = self.work / "3d" / src
            have = len(list(frames.glob("f_*.png")))
            n = int((d + 0.2) * FPS / 2) + 2
            first = int(min(start, max(0, have - n)))      # move the in-point back rather than run out of frames
            inp = ["-framerate", str(FPS), "-start_number", str(first + 1), "-i", frames / "f_%04d.png"]
            vf = (f"setpts=2*PTS,minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:vsbmc=1,scale={W}:{H}:flags=lanczos,"
                  f"tpad=stop_mode=clone:stop_duration={d:.2f}")            # a shot longer than the render holds its last frame
        elif kind == "vis":
            inp = ["-ss", f"{start:.2f}", "-t", f"{d + 0.2:.3f}", "-i", self.work / "visuals" / f"{src}.mp4"]
            vf = f"fps={FPS},scale={W}:{H},tpad=stop_mode=clone:stop_duration={d:.2f}"
        elif kind == "card":
            inp = ["-f", "lavfi", "-t", f"{d + 0.2:.3f}", "-i", f"color=c=0x081520:s={W}x{H}:r={FPS}"]
            vf = "null"
            body = shot.get("text", "")
            if body:
                vf += (f",drawtext=fontfile='{fpath(Path(FONT))}':textfile='{self._txt(body)}':fontsize=30:fontcolor=white@0.9:"
                       f"line_spacing=12:x=(w-text_w)/2:y=(h-text_h)/2:alpha='min(1,t/0.6)*min(1,({d:.3f}-t)/0.6)'")
        else:
            raise SystemExit(f"unknown shot kind {kind}")
        grade = shot.get("grade", "")
        vf = vf + (("," + grade) if grade else "") + ",setsar=1,format=yuv420p" + self.overlay(shot, d)
        if ";" in vf or "[" in vf:
            args = [*inp, "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]"]
        else:
            args = [*inp, "-vf", vf]
        run([*args, "-t", f"{d:.3f}", "-an", "-r", FPS, "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-threads", THREADS,
             "-pix_fmt", "yuv420p", out], f"segment {key}")
        got = duration(out)
        if got < d - 0.04:
            if got < d - 1.5:
                raise SystemExit(f"segment {key} is {got:.2f}s, wanted {d:.2f}s (source too short at in={start}?)")
            # a fraction short (the last interpolated frames of a 3D shot): hold the last frame to the exact length
            padded = out.with_name(out.stem + "_pad.mp4")
            run(["-i", out, "-vf", f"tpad=stop_mode=clone:stop_duration={d - got + 0.2:.2f}", "-t", f"{d:.3f}", "-an", "-r", FPS,
                 "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-threads", THREADS, "-pix_fmt", "yuv420p", padded], f"pad {key}")
            padded.replace(out)
        return out

    def xfade_chain(self, parts, out: Path, xf: float, what: str):
        """parts: [(file, on-screen seconds)]; every part but the last carries xf extra seconds that the next dissolves over."""
        if len(parts) == 1:
            run(["-i", parts[0][0], "-c", "copy", out], what); return
        ins, fc, prev, off = [], [], "0:v", 0.0
        for f, _ in parts:
            ins += ["-i", f]
        for i in range(1, len(parts)):
            off += parts[i - 1][1]
            fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={xf}:offset={off:.3f}[v{i}]")
            prev = f"v{i}"
        run([*ins, "-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-r", FPS, "-c:v", "libx264", "-preset", "medium", "-crf", "16",
             "-threads", THREADS, "-pix_fmt", "yuv420p", out], what)

    # ------------------------------------------------------------------------------------------------------- build
    def plan(self):
        scenes, t = [], 0.0
        for sc in self.cfg["scenes"]:
            nar = self.narration(sc["id"])
            nd = duration(nar) if nar else 0.0
            length = sc.get("length") or (sc.get("lead", 0.7) + nd + sc.get("tail", 1.0))
            scenes.append(dict(sc, start=t, length=length, narr=str(nar) if nar else None, narr_dur=nd))
            t += length
        return scenes, t

    def scene_file(self, si: int, sc: dict, n_scenes: int) -> Path:
        out = self.seg_dir / f"scene_{sc['id']}.mp4"
        want = sc["length"] + (0 if si == n_scenes - 1 else XS)
        if not (out.exists() and abs(duration(out) - want) < 0.1):
            shots = sc["shots"]
            wsum = sum(s.get("w", 1) for s in shots)
            parts = []
            for k, shot in enumerate(shots):
                t_i = want * shot.get("w", 1) / wsum
                d = t_i + (XF if k < len(shots) - 1 else 0)
                seg = self.segment(f"{sc['id']}_{k:02d}", shot, d, drift=1 if (si + k) % 2 else -1)
                parts.append((seg, t_i))
            self.xfade_chain(parts, out, XF, f"scene {sc['id']}")
        print(f"scene {sc['id']}: {sc['length']:.1f}s", flush=True)
        return out

    @staticmethod
    def split(scenes, k: int):
        """Scenes -> k groups of similar work (3D shots cost about 3x footage: motion interpolation), largest first."""
        cost = [(sc["length"] * (1 + 2 * sum(s["kind"] == "3d" for s in sc["shots"]) / len(sc["shots"])), i) for i, sc in enumerate(scenes)]
        groups, load = [[] for _ in range(k)], [0.0] * k
        for c, i in sorted(cost, reverse=True):
            j = load.index(min(load)); groups[j].append(i); load[j] += c
        return [sorted(g) for g in groups]

    def build(self, part: int | None = None, parts: int = 1, join: bool = True):
        """part/parts: render only this share of the scenes (parallel runners); join: put the scene files together."""
        scenes, total = self.plan()
        print(f"{len(scenes)} scenes, {total / 60:.2f} min", flush=True)
        mine = self.split(scenes, parts)[part] if part is not None else range(len(scenes))
        for si in mine:
            self.scene_file(si, scenes[si], len(scenes))
        if not join:
            return
        scene_files = []
        for si, sc in enumerate(scenes):
            out = self.seg_dir / f"scene_{sc['id']}.mp4"
            if not out.exists():
                raise SystemExit(f"missing {out.name}: render its part first")
            scene_files.append((out, sc["length"]))
        picture = self.out / "picture.mp4"
        self.xfade_chain_batched(scene_files, picture)
        audio = self.mix(scenes, total)
        final = self.out / "the_hidden_internet.mp4"
        run(["-i", picture, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-t", f"{total:.3f}", "-movflags", "+faststart", final], "mux")
        (self.out / "timeline.json").write_text(json.dumps([{k: sc[k] for k in ("id", "start", "length", "narr_dur")} | {"narr_at": sc["start"] + sc.get("lead", 0.7)}
                                                            for sc in scenes], indent=1), encoding="utf-8")
        print(f"final: {final} {duration(final):.2f}s (planned {total:.2f}s)", flush=True)

    def xfade_chain_batched(self, parts, out: Path):
        """Scenes dissolve into each other; done in batches of 6 so one ffmpeg never decodes 20 streams at once."""
        batch, k = [], 0
        while len(parts) > 6:
            head, parts = parts[:6], parts[6:]
            f = self.seg_dir / f"batch_{k}.mp4"
            span = sum(L for _, L in head)
            if not (f.exists() and abs(duration(f) - (span + XS)) < 0.1):
                self.xfade_chain(head, f, XS, f"batch {k}")
            batch.append((f, span)); k += 1
        batch += parts
        self.xfade_chain(batch, out, XS, "picture")

    def mix(self, scenes, total: float) -> Path:
        out = self.out / "mix.wav"
        ins, fc, labels = [], [], []
        for sc in scenes:
            if sc["narr"]:
                i = len(ins) // 2
                at = int((sc["start"] + sc.get("lead", 0.7)) * 1000)
                ins += ["-i", sc["narr"]]
                fc.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={at}|{at}[n{i}]")
                labels.append(f"[n{i}]")
        n = len(labels)
        fc.append("".join(labels) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{total:.3f},"
                  # voice levelling: the AI voice tails off by 10-15 dB at the end of some lines (owner heard it at 5:05)
                  "dynaudnorm=f=150:g=13:m=8:p=0.9,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=150:makeup=2,asplit=2[nar][key]")
        # music: the tracks in order, each trimmed to its slot, cross-faded, ducked under the voice
        mus = []
        for j, m in enumerate(self.cfg["music"]):
            idx = len(ins) // 2
            ins += ["-i", self.work / "music" / m["file"]]
            dur = m["until"] - m["from"]
            fc.append(f"[{idx}:a]atrim={m.get('in', 0)}:{m.get('in', 0) + dur + 4},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                      f"afade=t=in:d=3,afade=t=out:st={dur:.2f}:d=4,volume={m.get('db', -18)}dB,adelay={int(m['from'] * 1000)}|{int(m['from'] * 1000)}[m{j}]")
            mus.append(f"[m{j}]")
        fc.append("".join(mus) + f"amix=inputs={len(mus)}:normalize=0,apad,atrim=0:{total:.3f},afade=t=out:st={total - 4:.2f}:d=4[mus]")
        fc.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=80:release=1000[musd]")
        idx = len(ins) // 2
        ins += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anoisesrc=color=brown:amplitude=0.5:sample_rate=48000"]
        fc.append(f"[{idx}:a]lowpass=f=300,highpass=f=40,volume=-33dB,aformat=channel_layouts=stereo,afade=t=in:d=3,afade=t=out:st={total - 3:.2f}:d=3[amb]")
        fc.append("[nar][musd][amb]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
        run([*ins, "-filter_complex", ";".join(fc), "-map", "[aout]", "-t", f"{total:.3f}", "-c:a", "pcm_s16le", out], "mix")
        return out


if __name__ == "__main__":
    # cables_assemble.py <shotlist> <work> [--part i/k] [--join-only]
    f = Film(Path(sys.argv[1]), Path(sys.argv[2]))
    if "--part" in sys.argv:
        i, k = map(int, sys.argv[sys.argv.index("--part") + 1].split("/"))
        f.build(part=i, parts=k, join=False)
    elif "--join-only" in sys.argv:
        f.build(part=0, parts=1, join=True)        # every scene file is already present, so this only joins and mixes
    else:
        f.build()
