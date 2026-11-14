"""Sound design for Tiny Empires: background ambience per scene + event effects, quiet under the voices.

  python scripts/cartoon/sound_design.py sample <module> <film.mp4> <t0> <t1> <out_dir> <name>
      -> "<name> - BEFORE.mp4" (the film as it is) and "<name> - AFTER.mp4" (with the sound layer)

How it decides (all from the storyboard, nothing hand-placed):
- each 3D set has an ambience bed (AMBIENCE); maps and title cards stay quiet (music only);
- riders that move get galloping hooves; walking work crews get crowd/work sounds;
- on-screen events get a matching cue (title sting -> whoosh, crossed-out words -> thud, scrolls -> paper, coins -> coins, rain -> rain);
- the whole layer is ducked under the dialogue (sidechain on the voice bus), faded in and out at every cut, and the final
  mix is loudness-normalised in two passes like the films.
Sounds come from D:/Temp/cartoon/sfx (manifest.json lists licences; CC-BY credits go into the video description).
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SFX = Path(os.environ.get("TE_SFX", "D:/Temp/cartoon/sfx"))

# plate -> [(sound, gain dB)]; gains are relative and the whole layer sits well below the voices
AMBIENCE = {
    "giza_later": [("wind_desert", -6)], "giza_build": [("wind_desert", -9), ("crowd_work", -14), ("hammer_chisel", -20)],
    "workers_street": [("crowd_work", -8), ("wind_desert", -16)], "harbour": [("water_river", -8), ("crowd_work", -18)],
    "nile": [("water_river", -6)], "fields": [("wind_desert", -12), ("water_river", -16)], "quarry": [("hammer_chisel", -12), ("wind_desert", -12)],
    "tura": [("hammer_chisel", -14), ("water_river", -14)], "saqqara2": [("wind_desert", -8)], "palace": [], "house_interior": [("fire_crackle", -16)],
    "memphis": [("market_crowd", -10)],
    "m_steppe_dawn": [("wind_steppe", -6)], "m_ger_inside": [("fire_crackle", -8), ("wind_steppe", -22)], "m_karakorum": [("market_crowd", -10), ("wind_steppe", -16)],
    "m_zhongdu": [("wind_steppe", -10)], "m_bukhara": [("wind_desert", -10), ("fire_crackle", -18)], "m_mohi": [("wind_steppe", -9), ("water_river", -18)],
    "m_baghdad": [("water_river", -12), ("fire_crackle", -16)], "m_hakata": [("rain_heavy", -6)], "m_dadu_hall": [], "m_caravan": [("wind_desert", -8)],
    "steppe": [("wind_steppe", -8)],
    "e_spice_quay": [("market_crowd", -9), ("water_river", -16)], "e_london": [("market_crowd", -12), ("water_river", -18)], "e_whitehall": [],
    "e_deptford": [("hammer_chisel", -14), ("water_river", -14)], "e_ajmer_court": [], "e_surat": [("market_crowd", -12)],
    "e_calcutta": [("water_river", -12), ("market_crowd", -18)], "e_murshidabad": [("water_river", -16)], "e_plassey": [("wind_steppe", -12)],
    "e_allahabad": [("wind_steppe", -20)], "e_hooghly": [("water_river", -8)], "ocean": [("water_river", -8)], "plassey_rain": [("rain_heavy", -5)],
}
LAYER_DB = -21          # overall level of the effects layer before ducking (relative to full scale)


def pick(name):
    """First good file for a sound name from the manifest (or None if it was not found)."""
    man = SFX / "manifest.json"
    if man.exists():
        for e in json.loads(man.read_text(encoding="utf-8")):
            if e.get("name") == name and (SFX / Path(e["file"]).name).exists():
                return SFX / Path(e["file"]).name
    cands = sorted(SFX.glob(f"{name}_*.wav"))
    return cands[0] if cands else None


def events_for(shot, t_shot0):
    """Event cues for one shot: [(t_abs, sound, gain, dur or None)]."""
    ev = []
    keys = [getattr(a, "key", "") for a in shot.actors]
    riders = [a for a in shot.actors if "_mounted" in getattr(a, "key", "")]
    moving = [a for a in riders if getattr(a, "walks", None) and a.speed >= 1.2]   # galloping, not ambling
    if moving:                                                                   # hooves while riders move
        t0 = min(w[0] for a in moving for w in a.walks)
        ev.append((t_shot0 + max(0.0, t0), "hooves_gallop", -6 if len(moving) > 3 else -10, shot.dur - max(0.0, t0)))
        ev.append((t_shot0 + max(0.0, t0) + 0.4, "horse_neigh", -12, None))
    elif riders:
        ev.append((t_shot0 + 0.5, "horse_snort", -14, None))
        ev.append((t_shot0 + 0.5, "hooves_gallop", -20, shot.dur - 0.5)) if any(getattr(a, "walks", None) for a in riders) else None
    for f in shot.fx:
        name = getattr(f, "__qualname__", "")
        if name.startswith("title_sting"):
            ev.append((t_shot0 + _closure(f, "t0", 3.0), "whoosh", -6, None))
        elif name.startswith("no_list"):
            t0 = _closure(f, "t0", 0.2)
            for dt in (_closure(f, "times", []) or []):
                ev.append((t_shot0 + t0 + dt + 0.35, "stamp_thud", -8, None))
        elif name.startswith("charter"):
            ev.append((t_shot0 + _closure(f, "t0", 0.5), "paper_rustle", -8, None))
            ev.append((t_shot0 + _closure(f, "stamp_t", 2.0), "stamp_thud", -6, None))
        elif name.startswith(("paper_money", "paiza")):
            ev.append((t_shot0 + _closure(f, "t0", 0.5), "paper_rustle", -10, None))
        elif name.startswith(("coins_flow", "coins")):
            ev.append((t_shot0 + _closure(f, "t0", 0.5), "coins", -10, None))
        elif name.startswith("arrows_volley"):
            ev.append((t_shot0 + _closure(f, "t0", 1.0), "arrows", -8, None))
        elif name.startswith("year_counter"):
            ev.append((t_shot0 + _closure(f, "t0", 0.5), "tick", -14, 2.5))
    if any(getattr(f, "__name__", "") == "PL_rain" or getattr(f, "__qualname__", "").startswith("rain") for f in shot.fx):
        ev.append((t_shot0, "rain_heavy", -6, shot.dur))
        ev.append((t_shot0 + shot.dur * 0.4, "thunder", -10, None))
    return ev


def _closure(f, var, default):
    """Read a captured variable (t0, times, ...) from an fx closure."""
    try:
        names = f.__code__.co_freevars
        if var in names:
            return f.__closure__[names.index(var)].cell_contents
    except Exception:
        pass
    return default


def plan(module, t0, t1):
    """Beds and events over [t0, t1] of the film: list of (sound, start, dur, gain dB, fade)."""
    E = importlib.import_module(module)
    K = E.K
    ss = K.shots()
    out, acc = [], 0.0
    for sh in ss:
        a, b = acc, acc + sh.dur
        acc = b
        if b <= t0 or a >= t1:
            continue
        lo, hi = max(a, t0), min(b, t1)
        if sh.bg.startswith("plate:"):
            for snd, g in AMBIENCE.get(sh.bg[6:], []):
                out.append((snd, lo - t0, hi - lo, g, 0.5))
        for te, snd, g, d in events_for(sh, a):
            if t0 <= te < t1:
                dd = None if d is None else min(d, t1 - te, b - te)            # None = a one-shot, played once
                out.append((snd, te - t0, dd, g, 0.15))
    return K, out


def build_layer(items, total, out_wav, ff):
    """Render the effects layer (48 kHz stereo WAV) from (sound, start, dur, gain, fade) items."""
    ins, flt, labs, n = [], [], [], 0
    for snd, st, du, g, fd in items:
        src = pick(snd)
        if src is None or (du is not None and du <= 0.05):
            continue
        if du is None:                                                          # one-shot: natural length (max 6 s), no loop
            ins += ["-i", str(src)]
            du = min(6.0, total - st)
        else:
            ins += ["-stream_loop", "-1", "-i", str(src)]
        fd = min(fd, du / 3)
        ms = int(st * 1000)
        flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{du:.3f},asetpts=PTS-STARTPTS,"
                   f"afade=t=in:d={fd:.2f},afade=t=out:st={max(0, du - fd):.3f}:d={fd:.2f},volume={g + LAYER_DB}dB,adelay={ms}|{ms}[s{n}]")
        labs.append(f"[s{n}]")
        n += 1
    if not n:
        subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", f"{total:.3f}", str(out_wav)],
                       check=True)
        return 0
    flt.append(f"{''.join(labs)}amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={total:.3f},atrim=0:{total:.3f}[fx]")
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(flt), "-map", "[fx]", "-ar", "48000", str(out_wav)],
                   check=True)
    return n


def voice_bus(K, t0, t1, out_wav, ff):
    """Dialogue only over [t0, t1] (the ducking key)."""
    ss = K.shots()
    start, acc = {}, 0.0
    for sh in ss:
        start[sh.name] = acc
        acc += sh.dur
    ins, flt, labs, n = [], [], [], 0
    for nm, lid, tc in K.CUES:
        ta = start[nm] + tc
        d = K.dur(lid)
        if ta + d < t0 or ta > t1:
            continue
        ins += ["-i", str(K.VOICE / f"{lid}.mp3")]
        off = ta - t0
        if off >= 0:
            flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(off * 1000)}|{int(off * 1000)}[v{n}]")
        else:
            flt.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=start={-off:.3f},asetpts=PTS-STARTPTS[v{n}]")
        labs.append(f"[v{n}]")
        n += 1
    total = t1 - t0
    flt.append(f"{''.join(labs)}amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={total:.3f},atrim=0:{total:.3f}[v]")
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(flt), "-map", "[v]", "-ar", "48000", str(out_wav)],
                   check=True)


def sample(module, film, t0, t1, out_dir, name):
    t0, t1 = float(t0), float(t1)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    K, items = plan(module, t0, t1)
    ff = K.SC.ffmpeg()
    work = out_dir / f"_{name}_work"
    work.mkdir(exist_ok=True)
    total = t1 - t0
    before = out_dir / f"{name} - BEFORE.mp4"
    subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", str(film), "-t", f"{total:.3f}",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", str(before)], check=True)
    layer = work / "layer.wav"
    nfx = build_layer(items, total, layer, ff)
    key = work / "voice.wav"
    voice_bus(K, t0, t1, key, ff)
    graph = ";".join([
        "[0:a]aresample=48000,aformat=channel_layouts=stereo[film]",
        "[1:a]anull[fx]", "[2:a]asplit=1[key]",
        "[fx][key]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=450:makeup=1[duck]",   # effects dip under every word
        f"[film][duck]amix=inputs=2:normalize=0:duration=first,{{LN}},alimiter=limit=0.89,afade=t=in:d=0.3,afade=t=out:st={total - 0.4:.2f}:d=0.4[a]"])
    after = out_dir / f"{name} - AFTER.mp4"
    K.two_pass_loudnorm([ff, "-nostdin", "-y", "-loglevel", "error"],
                        ["-i", str(before), "-i", str(layer), "-i", str(key)], graph,
                        ["-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(after)])
    print("wrote", before.name, "and", after.name, f"({nfx} sound layers)")
    for it in items:
        print("   ", it)


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sample(*sys.argv[2:8])
