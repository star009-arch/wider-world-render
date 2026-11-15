"""Remove isolated audio overs (clicks) from a finished video: dip the volume for 80 ms around every sample above full scale,
re-encode the audio only (picture and metadata copied), repeat until none is left.  python declick.py <in.mp4> <out.mp4>"""
import subprocess, sys, shutil
import numpy as np, imageio_ffmpeg

ff = imageio_ffmpeg.get_ffmpeg_exe()


def overs(path):
    r = subprocess.run([ff, "-nostdin", "-loglevel", "error", "-i", path, "-ac", "2", "-ar", "48000", "-f", "f32le", "-"], capture_output=True)
    a = np.abs(np.frombuffer(r.stdout, dtype=np.float32)).reshape(-1, 2).max(axis=1)
    t = np.nonzero(a > 0.98)[0] / 48000
    out = []
    for x in t:
        if not out or x - out[-1] > 0.05:
            out.append(float(x))
    return out, float(a.max())


def main(src, dst):
    cur = src
    for i in range(4):
        ts, pk = overs(cur)
        if pk <= 0.98:
            break
        flt = ",".join(f"volume=enable='between(t,{t - 0.04:.3f},{t + 0.04:.3f})':volume={min(0.8, 0.8 / pk):.2f}" for t in ts)
        tmp = dst + f".p{i}.mp4"
        subprocess.run([ff, "-nostdin", "-y", "-loglevel", "error", "-i", cur, "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af", flt,
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-map_metadata", "0", "-movflags", "+faststart", tmp], check=True)
        cur = tmp
    if cur != dst:
        shutil.copyfile(cur, dst) if cur == src else shutil.move(cur, dst)
    print("declick:", dst, "peak", round(overs(dst)[1], 2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
