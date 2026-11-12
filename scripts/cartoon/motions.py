"""Motion library (Cartoon Engine V2, Phase 1): walks with planted feet, gestures with anticipation and follow-through,
reactions, blinking, Rhubarb lip-sync, and a Performer that the scene engine paints frame by frame.

Principles built in:
- weight: the hips drop on every footfall (from leg IK), and land/jump squash and stretch;
- foot contact: feet are planted in world space and legs solved with 2-bone IK, so feet never slide;
- anticipation: every big move starts with a small opposite move (lean back before pointing, crouch before jumping);
- follow-through: arms and head lag the body and overshoot before settling;
- personality: each character has its own walk speed, stride, bounce, lean and gesture timing.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from functools import lru_cache

from PIL import Image

import hosts3 as H3
import natural as N
import rig as R

FPS = 30
USE_V3 = True                       # host designs v3 (owner references, 11 Nov 2026); False = pilot-era rig hosts
USE_NATURAL = False                 # visual direction locked 11 Nov 2026: stylised mascots, not natural humans


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out_back(t, k=1.6):
    t = max(0.0, min(1.0, t))
    t -= 1
    return 1 + t * t * ((k + 1) * t + k)


# ------------------------------------------------------------------------------------------------ personality
@dataclass(frozen=True)
class Persona:
    stride: float = 2.4         # distance per full gait cycle, head units
    lift: float = 0.45          # foot lift on swing, head units
    bounce: float = 0.08        # extra bob on top of the IK hip drop
    arm: float = 26.0           # arm swing, degrees
    lean: float = 4.0           # forward lean while walking
    sway: float = 0.0           # side-to-side body roll (waddle), degrees
    speed: float = 1.0          # walk speed multiplier (u/s = stride * cadence)
    cadence: float = 1.0        # gait cycles per second
    snap: float = 1.0           # gesture speed (>1 snappier, <1 slower)
    jitter: float = 0.0         # nervous tremble (Pike)
    stance: float = 0.15        # idle foot spread, head units


PERSONA = {
    "atlas": Persona(stride=3.4, lift=0.6, bounce=0.12, arm=32, cadence=1.0, snap=1.1),
    "penny": Persona(stride=2.6, lift=0.4, bounce=0.04, arm=14, lean=-5, sway=1.5, cadence=1.25, snap=1.3),
    "pike": Persona(stride=2.9, lift=0.65, bounce=0.06, arm=14, lean=9, cadence=1.3, snap=1.4, jitter=0.6),
    "quill": Persona(stride=2.4, lift=0.35, bounce=0.04, arm=12, lean=3, sway=0, cadence=0.95, snap=0.9),
    "stampy": Persona(stride=2.6, lift=0.4, bounce=0.03, arm=8, lean=0, cadence=0.8, snap=0.75),
    "zed": Persona(stride=1.8, lift=0.4, bounce=0.1, arm=18, lean=2, sway=3, cadence=1.4, snap=1.2),
}
DEFAULT = Persona(stride=3.0, lift=0.55, cadence=0.95, snap=1.0)


def persona(key):
    return PERSONA.get(key, DEFAULT)


# ------------------------------------------------------------------------------------------------ leg IK
def leg_ik(dx, dy, L):
    """Thigh angle and knee bend (degrees, rig convention) so a 2-segment leg of segment length L reaches (dx fwd, dy down)."""
    dist = math.hypot(dx, dy)
    dist = min(dist, 2 * L * 0.999)
    base = math.degrees(math.atan2(dx, dy))
    alpha = math.degrees(math.acos(dist / (2 * L)))
    return base + alpha, 2 * alpha


# ------------------------------------------------------------------------------------------------ gesture clips
# keys: (time in s at snap=1, {pose fields}, {face fields}). Numeric pose fields are eased between keys; face fields switch.
CLIPS = {
    "point": (1.2, [(0.0, {}, {}), (0.16, {"sh_l": 20, "el_l": 70, "lean": -5}, {"brows": 0.3}),
                    (0.32, {"sh_l": 102, "el_l": -4, "lean": 8}, {"mouth": "grin"}),
                    (0.42, {"sh_l": 94, "el_l": 2, "lean": 5}, {}), (1.2, {"sh_l": 92, "el_l": 0, "lean": 4}, {})]),
    "wave": (1.4, [(0.0, {}, {}), (0.18, {"sh_l": 150, "el_l": -10, "head": 6}, {"mouth": "smile"}),
                   (0.38, {"el_l": 30}, {}), (0.58, {"el_l": -10}, {}), (0.78, {"el_l": 30}, {}), (0.98, {"el_l": -5}, {}),
                   (1.4, {"sh_l": 150, "el_l": 0}, {})]),
    "shrug": (1.1, [(0.0, {}, {}), (0.12, {"y": -0.12, "sh_l": 10, "sh_r": 10}, {}),
                    (0.3, {"y": 0.08, "sh_l": 28, "el_l": 85, "sh_r": 28, "el_r": 85, "head": 12}, {"brows": 1.0, "mouth": "worried"}),
                    (0.45, {"y": 0.0, "head": 9}, {}), (1.1, {"sh_l": 26, "el_l": 80, "sh_r": 26, "el_r": 80, "head": 9}, {})]),
    "facepalm": (1.5, [(0.0, {}, {}), (0.2, {"sh_l": 60, "el_l": 40, "head": -4}, {}),
                       (0.36, {"sh_l": 150, "el_l": 75, "head": -14, "lean": 6}, {"blink": 1.0, "mouth": "frown"}),
                       (0.46, {"head": -11}, {}), (1.5, {"sh_l": 148, "el_l": 78, "head": -12, "lean": 5}, {})]),
    "flinch": (0.9, [(0.0, {}, {}), (0.08, {"lean": -14, "y": -0.25, "sq": 0.9, "sh_l": 150, "el_l": 60, "sh_r": 150, "el_r": 60, "head": -8},
                                    {"bulge": 1.35, "mouth": "wide", "brows": 1.0}),
                     (0.2, {"lean": -10, "y": -0.15, "sq": 1.04}, {}), (0.9, {"lean": -8, "y": -0.1, "sq": 1.0}, {})]),
    "double_take": (1.3, [(0.0, {}, {}), (0.25, {"head": 4}, {"mouth": "X"}), (0.45, {"head": 0}, {}),
                          (0.55, {"head": -10, "y": -0.1, "lean": -4}, {"blink": 1.0}),
                          (0.68, {"head": 6, "y": 0.35, "sq": 1.12, "lean": -9}, {"bulge": 1.6, "mouth": "o", "brows": 1.0}),
                          (0.85, {"y": 0.0, "sq": 0.94}, {}), (1.3, {"head": 3, "sq": 1.0, "lean": -5}, {})]),
    "jump": (1.2, [(0.0, {}, {}), (0.22, {"y": -0.45, "sq": 0.84, "lean": 10, "sh_l": -30, "sh_r": -30}, {}),
                   (0.42, {"y": 2.2, "sq": 1.16, "lean": -4, "sh_l": 165, "sh_r": 165}, {"mouth": "grin"}),
                   (0.6, {"y": 2.6, "sq": 1.0}, {}), (0.82, {"y": 0.0, "sq": 1.06}, {}),
                   (0.92, {"y": -0.35, "sq": 0.82, "sh_l": 120, "sh_r": 120}, {}), (1.2, {"y": 0.0, "sq": 1.0}, {})]),
    "fall": (1.6, [(0.0, {}, {}), (0.15, {"rot": -6, "lean": -6, "sh_l": 60, "sh_r": 60}, {"bulge": 1.4, "mouth": "o"}),
                   (0.5, {"rot": 88, "sh_l": 160, "sh_r": 140, "el_l": 20}, {"mouth": "wide"}),
                   (0.6, {"rot": 82}, {}), (0.7, {"rot": 90}, {"blink": 1.0, "mouth": "frown"}), (1.6, {"rot": 90}, {})]),
    "stamp": (1.0, [(0.0, {}, {}), (0.25, {"sh_l": 175, "el_l": 10, "lean": -6, "y": 0.1}, {"brows": -0.6, "mouth": "smirk"}),
                    (0.38, {"sh_l": 55, "el_l": 25, "lean": 12, "y": -0.25, "sq": 0.9}, {"blink": 1.0}),
                    (0.5, {"sh_l": 60, "lean": 9, "y": -0.1, "sq": 1.0}, {"mouth": "grin"}), (1.0, {"sh_l": 40, "el_l": 30, "lean": 3}, {})]),
    "celebrate": (1.6, [(0.0, {}, {}), (0.15, {"y": -0.2, "sq": 0.9}, {}),
                        (0.3, {"y": 0.9, "sq": 1.1, "sh_l": 165, "sh_r": 165, "el_l": -10, "el_r": -10}, {"mouth": "grin"}),
                        (0.5, {"y": 0.0, "sq": 0.92}, {}), (0.65, {"y": 0.7, "sq": 1.08}, {}), (0.85, {"y": 0.0, "sq": 0.95}, {}),
                        (1.6, {"y": 0.0, "sq": 1.0, "sh_l": 150, "sh_r": 150}, {})]),
    "cower": (1.0, [(0.0, {}, {}), (0.15, {"y": -0.4, "sq": 0.88, "lean": -8, "sh_l": 140, "el_l": 90, "sh_r": 140, "el_r": 90, "head": -8},
                                    {"bulge": 1.3, "brows": 1.0, "mouth": "worried"}),
                    (1.0, {"y": -0.35, "sq": 0.9}, {})]),
    "think": (1.4, [(0.0, {}, {}), (0.3, {"sh_l": 40, "el_l": 120, "head": 8}, {"look": 0.8, "brows": 0.4, "mouth": "smirk"}),
                    (1.4, {"sh_l": 40, "el_l": 122, "head": 10}, {})]),
    "nod": (0.8, [(0.0, {}, {}), (0.15, {"head": -10}, {}), (0.3, {"head": 3}, {}), (0.45, {"head": -8}, {}), (0.8, {"head": 0}, {})]),
    "headshake": (1.0, [(0.0, {}, {}), (0.15, {"head": 9}, {"mouth": "frown"}), (0.35, {"head": -9}, {}), (0.55, {"head": 8}, {}),
                        (0.75, {"head": -5}, {}), (1.0, {"head": 0}, {})]),
    "present": (1.0, [(0.0, {}, {}), (0.14, {"sh_l": 10, "el_l": 40, "lean": -3}, {}),
                      (0.34, {"sh_l": 70, "el_l": 30, "lean": 4}, {"mouth": "smile"}), (1.0, {"sh_l": 68, "el_l": 34, "lean": 3}, {})]),
}
CLIPS.update({
    "fold": (0.6, [(0.0, {}, {}), (0.35, {"sh_l": 38, "el_l": 112, "sh_r": 38, "el_r": 112, "lean": -3}, {}),
                   (0.6, {"sh_l": 36, "el_l": 110, "sh_r": 36, "el_r": 110, "lean": -3}, {})]),
    "sit": (1.0, [(0.0, {}, {}), (0.3, {"y": -0.2, "lean": 6}, {}), (0.7, {"y": -1.75, "lean": -6, "sh_l": 36, "el_l": 110, "sh_r": 36, "el_r": 110,
                                                                        "sq": 0.9}, {"mouth": "smirk"}),
                  (1.0, {"y": -1.7, "sq": 0.92}, {})]),
    "rub": (1.6, [(0.0, {}, {}), (0.2, {"sh_l": 40, "el_l": 80, "sh_r": 40, "el_r": 80, "lean": 4}, {"mouth": "grin", "brows": -0.6}),
                  (0.4, {"sh_l": 46, "el_l": 72}, {}), (0.6, {"sh_l": 38, "el_l": 84}, {}), (0.8, {"sh_l": 46, "el_l": 72}, {}),
                  (1.0, {"sh_l": 38, "el_l": 84}, {}), (1.2, {"sh_l": 46, "el_l": 72}, {}), (1.6, {"sh_l": 40, "el_l": 80}, {})]),
    "hold_up": (0.5, [(0.0, {}, {}), (0.12, {"y": -0.15, "sh_l": 40}, {}), (0.3, {"sh_l": 168, "el_l": 6, "y": 0.1}, {"brows": 0.5}),
                      (0.5, {"sh_l": 165, "el_l": 8, "y": 0.0}, {})]),
    "cheer": (0.8, [(0.0, {}, {}), (0.2, {"sh_l": 150, "el_l": 20, "sh_r": 150, "el_r": 20}, {"mouth": "grin"}),
                    (0.4, {"y": 0.3}, {}), (0.6, {"y": 0.0}, {}), (0.8, {"y": 0.25}, {})]),
})
NUMERIC = ("lean", "head", "sh_l", "el_l", "sh_r", "el_r", "y", "sq", "rot")


def clip_sample(name, t, snap, base: dict):
    """Pose overrides of a clip at local time t (seconds), eased between keys; returns (pose dict, face dict)."""
    dur, keys = CLIPS[name]
    tt = t * snap
    vals, face = {}, {}
    for f in NUMERIC:
        pts = [(k[0], k[1][f]) for k in keys if f in k[1]]
        if not pts:
            continue
        pts = [(0.0, base[f])] + pts
        v = pts[-1][1]
        for (a, va), (b, vb) in zip(pts, pts[1:]):
            if a <= tt <= b:
                v = va + (vb - va) * ease((tt - a) / max(1e-6, b - a))
                break
            if tt < a:
                v = va
                break
        vals[f] = v
    for k in keys:
        if tt >= k[0]:
            face.update(k[2])
    if "blink" in face and tt > max(k[0] for k in keys if "blink" in k[2]) + 0.12:
        face.pop("blink")                                                          # blinks inside clips are brief
    return vals, face


def clip_len(name, snap):
    return CLIPS[name][0] / snap


# ------------------------------------------------------------------------------------------------ lip-sync
def load_rhubarb(path, offset=0.0):
    data = json.loads(open(path, encoding="utf-8").read())
    return [(c["start"] + offset, c["end"] + offset, c["value"]) for c in data["mouthCues"]]


def mouth_at(cues, t):
    for a, b, v in cues:
        if a <= t < b:
            return v
    return None


# ------------------------------------------------------------------------------------------------ performer
@dataclass
class Performer:
    key: str
    x: float
    ground: float                                   # screen y of the feet
    scale: float = 1.0
    flip: bool = False
    walks: list = field(default_factory=list)       # [(t0, x1)]: walk from wherever they are to x1, starting at t0
    acts: list = field(default_factory=list)        # [(t0, clip name, hold seconds after the clip ends or None = stay)]
    faces: list = field(default_factory=list)       # [(t, {face fields})] the resting expression from t on
    lips: list = field(default_factory=list)        # rhubarb cues (absolute shot times)
    turns: list = field(default_factory=list)       # [(t, flip)]
    props: dict = field(default_factory=dict)       # {"prop_l": "stamp", ...}
    shadow: bool = True
    speed: float = 1.0                              # walk speed multiplier (gait cycles faster; feet stay planted)
    hide: tuple | None = None                       # (t0, t1): not drawn in this window (e.g. exited)
    view: float = 0.6                               # 0 front, 0.6 three-quarter, 1 profile (v3 hosts)
    y = 0                                           # sort key used by the scene engine

    def __post_init__(self):
        self.pp = persona(self.key)
        self.y = self.ground
        self.upx = 20 * self.scale                  # pixels per head unit at 1x
        if ":" in self.key:                                                  # period people "<world>:<name>" (people.py)
            import people as PP
            w, n = self.key.split(":", 1)
            self.ch = None
            self.natural = False
            self.L = 1.55 * PP.get(w, n).height
            k = self.L / 0.75
            self.pp = replace(DEFAULT, stride=DEFAULT.stride * k * 0.8, lift=DEFAULT.lift * k * 0.7, arm=DEFAULT.arm * 0.9)
            self._plan()
            return
        if USE_V3 and self.key in H3.KEYS:                                  # v3 hosts: leg length straight from their build
            self.ch = None
            self.natural = False
            self.L = H3.leg_len(self.key)
            k = self.L / 0.75
            self.pp = replace(self.pp, stride=self.pp.stride * k * 0.8, lift=self.pp.lift * k * 0.7, arm=self.pp.arm * 0.9)
            self._plan()
            return
        self.ch = R.get(self.key)
        self.natural = USE_NATURAL and self.key in N.LOOKS
        self.L = 0.75 * (N.LEG_LEN * N.LOOKS[self.key].height if self.natural else self.ch.leg_len)
        if not self.natural and self.ch.leg_len != 1.0:                      # longer mascot legs: proportionally longer strides
            k = self.ch.leg_len
            self.pp = replace(self.pp, stride=self.pp.stride * k * 0.85, lift=self.pp.lift * k * 0.7, arm=self.pp.arm * 0.85)
        if self.natural:                                                    # longer legs: longer strides and lifts
            k = self.L / 0.75 / 1.0 * 0.5
            self.pp = replace(self.pp, stride=self.pp.stride * k * 0.9, lift=self.pp.lift * k * 0.55, bounce=self.pp.bounce * 0.6, arm=self.pp.arm * 0.7)
        self.upx = 20 * self.scale                  # pixels per head unit at 1x
        self._plan()

    # walking plan: each walk segment covers its distance at the persona's speed; feet are planted by distance
    def _plan(self):
        self.segs = []
        x = self.x
        for t0, x1 in sorted(self.walks):
            dist = abs(x1 - x) / self.upx
            v = self.pp.stride * self.pp.cadence * self.pp.speed * self.speed   # u/s
            dur = max(0.4, dist / v + 0.25)                                 # +ease in/out
            self.segs.append((t0, t0 + dur, x, x1))
            x = x1

    def _travel(self, t):
        """(screen x, distance walked in this segment in u, segment length in u, direction, walking weight)."""
        x = self.x
        for t0, t1, xa, xb in self.segs:
            if t < t0:
                return x, 0, 0, 1, 0.0
            if t <= t1:
                s = (t - t0) / (t1 - t0)
                e = s * s * (3 - 2 * s) * 0.35 + s * 0.65                  # mostly linear, soft start/stop
                xx = xa + (xb - xa) * e
                tot = abs(xb - xa) / self.upx
                w = min(1.0, (t - t0) / 0.25, (t1 - t) / 0.25)
                return xx, tot * e, tot, (1 if xb >= xa else -1), max(0.0, w)
            x = xb
        return x, 0, 0, 1, 0.0

    def facing(self, t):
        fl = self.flip
        for tt, f in sorted(self.turns):
            if t >= tt:
                fl = f
        for t0, t1, xa, xb in self.segs:
            if t0 <= t <= t1 + 0.6 and xb != xa:
                fl = xb < xa
        return fl

    def pos_at(self, t):
        return self._travel(t)[0], self.ground

    def pose_at(self, t):
        pp = self.pp
        L = self.L
        flip = self.facing(t)
        x, dist, tot, dirn, w = self._travel(t)
        face = {}
        for tt, fd in sorted(self.faces, key=lambda a: a[0]):
            if t >= tt:
                face.update(fd)
        ph_breathe = (hash(self.key) % 97) / 97 * 6.28
        base = {"lean": 0.0, "head": 1.5 * math.sin(t * 1.3 + ph_breathe), "sh_l": 10.0, "el_l": 8.0, "sh_r": 8.0, "el_r": 6.0,
                "y": 0.04 * math.sin(t * 2.2 + ph_breathe), "sq": 1.0 + 0.012 * math.sin(t * 2.2 + ph_breathe), "rot": 0.0}
        if pp.jitter:
            base["head"] += pp.jitter * 2.0 * math.sin(t * 31)
            base["sh_l"] += pp.jitter * 3 * math.sin(t * 27)
        feet = [-pp.stance, pp.stance]                                      # (back, front) foot x relative to hip, u
        lift = [0.0, 0.0]
        if w > 0:
            cyc = dist / pp.stride                                          # gait cycles walked
            ph = cyc * 2 * math.pi
            for i, off in enumerate((0.5, 0.0)):                            # back leg (r) half a cycle out of phase
                fr = (cyc + off) % 1.0
                if fr < 0.5:                                                # stance: planted, slides back relative to hip
                    rel = 0.25 - fr                                         # +0.25 -> -0.25 strides
                    lf = 0.0
                else:                                                       # swing: eased forward, lifted
                    s = (fr - 0.5) / 0.5
                    rel = -0.25 + 0.5 * ease(s)
                    lf = math.sin(math.pi * s) * pp.lift
                feet[i] = feet[i] * (1 - w) + rel * pp.stride * w
                lift[i] = lf * w
            reach = max(abs(f) for f, lf in zip(feet, lift) if lf < 0.05 * L) if min(lift) < 0.05 * L else 0.0
            drop = 2 * L - math.sqrt(max(0.0, (2 * L * 0.997) ** 2 - reach ** 2))   # stance leg nearly straight
            base["y"] = -drop - pp.bounce * (0.5 + 0.5 * math.cos(4 * math.pi * cyc)) * w
            base["lean"] = pp.lean * w
            base["head"] += -2.5 * math.cos(4 * math.pi * cyc - 0.6) * w   # head lags the body (follow-through)
            swing = pp.arm * w
            base["sh_l"] = 6 - swing * math.sin(ph - 0.35)                  # arms counter the legs, lagging a little
            base["sh_r"] = 6 + swing * math.sin(ph - 0.35)
            base["el_l"] = 12 + 10 * max(0, -math.sin(ph - 0.35)) * w
            base["el_r"] = 12 + 10 * max(0, math.sin(ph - 0.35)) * w
            base["rot"] = pp.sway * math.sin(ph) * w
        # gesture clips layered on top, blended in and out
        for t0, name, hold in self.acts:
            ln = clip_len(name, pp.snap)
            end = t0 + ln + (hold if hold is not None else 1e9)
            if t0 <= t <= end + 0.3:
                vals, fc = clip_sample(name, t - t0, pp.snap, base)
                bw = 1.0 if t <= end else 1 - ease((t - end) / 0.3)
                for k, v in vals.items():
                    base[k] = base[k] + (v - base[k]) * bw
                if bw > 0.5:
                    face.update(fc)
        # legs: airborne -> tucked, grounded -> IK to planted feet
        hip_drop = -base["y"]
        th, kn = [0, 0], [0, 0]
        for i in range(2):
            if base["y"] > 0.15:
                th[i], kn[i] = leg_ik(feet[i] * 0.5 + 0.2, 2 * L * 0.8, L)
            else:
                th[i], kn[i] = leg_ik(feet[i], 2 * L - hip_drop - lift[i], L)
        # face: blink, lip-sync
        blink = face.get("blink", 0.0)
        bt = (t + ph_breathe) % 3.7
        if bt < 0.13 or (int((t + ph_breathe) / 3.7) % 3 == 1 and 0.25 < bt < 0.36):
            blink = 1.0
        m = mouth_at(self.lips, t)
        mouth = m if m is not None else face.get("mouth", "X")
        if m is not None and m in "CDH":
            base["head"] += 1.5                                             # small accents on open vowels
        fc = R.Face(brows=round(face.get("brows", 0.0), 1), look=round(face.get("look", 0.0), 1), blink=blink,
                    mouth=mouth, bulge=round(face.get("bulge", 1.0), 2))
        q = lambda v, step: round(v / step) * step
        return R.Pose(lean=q(base["lean"], 1), head=q(base["head"], 1), sh_l=q(base["sh_l"], 2), el_l=q(base["el_l"], 2),
                      sh_r=q(base["sh_r"], 2), el_r=q(base["el_r"], 2), th_l=q(th[1], 1), kn_l=q(kn[1], 1), th_r=q(th[0], 1),
                      kn_r=q(kn[0], 1), y=q(base["y"], 0.02), sq=q(base["sq"], 0.01), rot=q(base["rot"], 1), face=fc,
                      prop_l=self.props.get("prop_l", ""), prop_r=self.props.get("prop_r", "")), flip

    def paint(self, frame, t):
        pose, flip = self.pose_at(t)
        x, y = self.pos_at(t)
        if self.shadow and not pose.rot:                                    # soft contact shadow, shrinks as they jump
            k = max(0.35, 1 - max(0.0, pose.y) * 0.25)
            w, h = 2.6 * self.upx * k, 0.55 * self.upx * k
            sh = _shadow(int(w), int(h))
            frame.alpha_composite(sh, (int(x - w), int(y - h)))
        tile, ax, ay = tile_for(self.key, pose, self.scale, flip, self.view)
        frame.alpha_composite(tile, (int(x - ax), int(y - ay)))


@lru_cache(maxsize=64)
def _shadow(w, h):
    from PIL import ImageDraw, ImageFilter
    im = Image.new("RGBA", (2 * w, 2 * h), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([w * 0.2, h * 0.4, w * 1.8, h * 1.6], fill=(20, 14, 10, 90))
    return im.filter(ImageFilter.GaussianBlur(max(2, h // 4)))


@lru_cache(maxsize=6000)
def tile_for(key, pose, scale, flip, view=0.6):
    if ":" in key:
        import people as PP
        w, n = key.split(":", 1)
        return PP.draw(PP.get(w, n), pose, scale, flip, view)
    if USE_V3 and key in H3.KEYS:
        return H3.draw(key, pose, scale, flip, view)
    if USE_NATURAL and key in N.LOOKS:
        return N.draw(key, pose, scale, flip)
    return R.draw_character(R.get(key), pose, scale, flip)



def set_world(name):
    """Dress all hosts for an episode's world (period costumes) and drop cached tiles."""
    H3.set_world(name)
    tile_for.cache_clear()
