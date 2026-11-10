"""Download the film's public-domain / CC BY media listed in media.json into <work>/<dir>/<name>, checking SHA-1."""
import hashlib, json, os, sys, time, urllib.request
from pathlib import Path

UA = {"User-Agent": "TheWiderWorldDocumentaryBot/1.0 (https://www.youtube.com/@TheWiderWorldDocs)"}
work = Path(sys.argv[1])


def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


only = sys.argv[2] if len(sys.argv) > 2 else None          # e.g. "music": fetch one folder only; "any" = every folder
if only == "any":
    only = None
names = set(sys.argv[3].split()) if len(sys.argv) > 3 else None   # only these files (a part's own clips)
MEDIA = os.environ.get("YTG_MEDIA", "media.json")          # one manifest per film (svalbard_media.json, ...)
for m in json.load(open(Path(__file__).parent / MEDIA)):
    if only and m["dir"] != only:
        continue
    if names is not None and m["name"] not in names:
        continue
    dest = work / m["dir"] / m["name"]
    if dest.exists() and "sha1" in m and sha1(dest) == m["sha1"]:
        print(f"cached {m['name']}", flush=True)
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    if "archive" in m:
        item, fname = m["archive"]
        meta = json.load(urllib.request.urlopen(urllib.request.Request(f"https://archive.org/metadata/{item}", headers=UA), timeout=60))
        m["sha1"] = next(x["sha1"] for x in meta["files"] if x["name"] == fname)
        m["url"] = f"https://archive.org/download/{item}/{fname}"
    for attempt in range(5):
        try:
            t0 = time.time()
            with urllib.request.urlopen(urllib.request.Request(m["url"], headers=UA), timeout=180) as r, open(dest, "wb") as f:
                for b in iter(lambda: r.read(1 << 20), b""):
                    f.write(b)
            if sha1(dest) != m["sha1"]:
                raise IOError("sha1 mismatch")
            print(f"ok {m['name']} {dest.stat().st_size / 1e6:.0f} MB in {time.time() - t0:.0f}s", flush=True)
            break
        except Exception as e:
            print(f"retry {m['name']}: {e}", flush=True)
            time.sleep(15 * (attempt + 1))
    else:
        sys.exit(f"failed: {m['name']}")
