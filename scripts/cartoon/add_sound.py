"""Add the ambience/effects layer to a finished Facebook video or short clip, without touching its picture.

  python scripts/cartoon/add_sound.py <cut key> <in.mp4> <out.mp4>      e.g. ep03 | ep03_c1 | ep02_c2 | eic

The cut's moments come from fb_cut.plan (same as when it was rendered); the sound layer is built from the episode's
sound plan for those moments (sound_design.fb_layer), kept at least sound_design.MARGIN_DB under the voices in every
spoken half-second (protect_voice), ducked under the voices and loudness-normalised in two passes. Picture and
metadata (te-fb fingerprint) are copied unchanged.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fb_cut as F
import sound_design as SD


def main(key, src, out):
    src, out = Path(src), Path(out)
    cfg = F.CUTS[key]
    module = cfg.get("module", key)
    K, segs, total = F.plan(key)
    ff = K.SC.ffmpeg()
    work = out.parent / f"_{key}_sound_work"
    work.mkdir(parents=True, exist_ok=True)
    ins, flt, labs = [], [], []                                                  # the voices alone, placed as in the cut
    for n, s in enumerate(segs):
        ins += ["-i", str(K.VOICE / f"{s['lid']}.mp3")]
        ms = int(s["voice_at"] * 1000)
        flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{n}]")
        labs.append(f"[v{n}]")
    flt.append(f"{''.join(labs)}amix=inputs={len(segs)}:normalize=0:duration=longest,apad=whole_dur={total:.2f},atrim=0:{total:.2f}[dia]")
    key_wav = work / "voice.wav"
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(flt), "-map", "[dia]", "-ar", "48000",
                    str(key_wav)], check=True)
    layer = work / "layer.wav"
    n = SD.fb_layer(module, segs, total, layer, ff)
    worst = SD.protect_voice(layer, key_wav, ff)
    print(f"voice clarity: worst margin {worst:.1f} dB")
    if worst < SD.MARGIN_DB - 1:
        raise SystemExit(f"voice clarity check failed ({worst:.1f} dB)")
    graph = ";".join([
        "[0:a]aresample=48000,aformat=channel_layouts=stereo[film]", "[1:a]anull[fx]", "[2:a]anull[key]",
        f"[fx][key]{SD.DUCK}[duck]",
        "[film][duck]amix=inputs=2:normalize=0:duration=first,{LN},volume=-1.3dB,alimiter=limit=0.84[a]"])        # full length incl. the end card
    K.two_pass_loudnorm([ff, "-nostdin", "-y", "-loglevel", "error"], ["-i", str(src), "-i", str(layer), "-i", str(key_wav)], graph,
                        ["-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                         "-map_metadata", "0", "-movflags", "+faststart", str(out)])
    print("wrote", out, f"({n} sound layers over {total:.1f}s)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
