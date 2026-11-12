"""Period people: historical cast and crowds drawn in the hosts' (v3) style, assembled from a visual-bible spec.

A Person spec lists what the visual bible prescribes for one character or class: skin, hair or wig, beard (incl. the
royal false beard), eye make-up, headwear/crown, garment cut and colours, jewellery, footwear, held object.
draw(spec, pose, s, flip, view) has the same contract as hosts3.draw, so every motion and lip-sync works.

Worlds live in WORLDS (e.g. "egypt_ok"); each entry is a dict of named people. Sources: projects/tiny-empires/visual_bibles/.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

from PIL import Image, ImageDraw

import hosts3 as H
from hosts3 import LINE, OUT, ell, eyes, limb, mouth, rot_sprite, shade, shaded_ell, tint, _down, _rot


@dataclass(frozen=True)
class Person:
    name: str
    skin: tuple = (176, 112, 74)
    build: float = 1.0               # body width (heavy-set officials > 1)
    height: float = 1.0
    hair: str = "short_wig"          # shaved | short_wig | long_wig | plait_side | bun | none | curls | long_loose | braids_loops
    hair_col: tuple = (26, 22, 22)
    beard: str = "none"              # none | false_beard | stubble | full | moustache | long
    beard_col: tuple = (26, 22, 22)
    kohl: bool = True                # dark eye-lines (green malachite under, black kohl)
    malachite: bool = False
    headwear: str = "none"           # none | white_crown | red_crown | double_crown | nemes | headband | fur_hat | turban | tricorne | cap
    head_col: tuple = (244, 240, 230)
    garment: str = "kilt"            # kilt | loincloth | sheath_dress | robe | tunic | coat_breeches | deel | jama
    garment_col: tuple = (244, 240, 230)
    garment_col2: tuple = (212, 165, 55)
    bare_chest: bool = True
    collar: bool = False
    bracelets: bool = False
    sash: bool = False
    footwear: str = "barefoot"       # barefoot | sandals | boots | shoes
    foot_col: tuple = (150, 110, 70)
    prop: str = ""                   # staff | scroll | palette | spear | bow | rope | bread | jar


WORLDS: dict = {}
SKIN_M, SKIN_F = (168, 98, 62), (214, 164, 112)        # Egyptian art convention: reddish-brown men, pale ochre elite women
WORLDS["egypt_ok"] = {
    "khufu": Person("Khufu", skin=SKIN_M, build=1.05, hair="none", beard="false_beard", headwear="nemes", head_col=(244, 240, 230),
                    garment="kilt", garment_col2=(212, 165, 55), collar=True, bracelets=True, footwear="sandals", prop="staff", malachite=True),
    "khufu_white": Person("Khufu (white crown)", skin=SKIN_M, build=1.05, hair="none", beard="false_beard", headwear="white_crown",
                          garment="kilt", collar=True, bracelets=True, footwear="sandals", prop="staff"),
    "djoser": Person("Djoser / Netjerikhet", skin=SKIN_M, hair="none", beard="false_beard", headwear="white_crown", garment="robe",
                     garment_col=(244, 240, 230), bare_chest=False, collar=True, footwear="sandals", prop="staff"),
    "sneferu": Person("Sneferu", skin=SKIN_M, hair="none", beard="false_beard", headwear="double_crown", garment="kilt", collar=True,
                      bracelets=True, footwear="sandals", prop="staff"),
    "imhotep": Person("Imhotep", skin=SKIN_M, hair="shaved", garment="kilt", collar=True, footwear="sandals", prop="scroll"),
    "official": Person("High official (Hemiunu/Ankhhaf type)", skin=SKIN_M, build=1.3, hair="short_wig", garment="kilt", collar=True,
                       footwear="sandals", prop="staff"),
    "merer": Person("Merer, inspector of a boat crew", skin=SKIN_M, hair="short_wig", garment="kilt", collar=False, prop="scroll"),
    "scribe": Person("Scribe", skin=SKIN_M, build=1.1, hair="short_wig", garment="kilt", prop="palette"),
    "worker": Person("Labourer", skin=(150, 92, 58), hair="shaved", beard="stubble", kohl=False, garment="loincloth", prop="rope"),
    "worker2": Person("Labourer", skin=(160, 98, 62), hair="short_wig", kohl=False, garment="loincloth", prop=""),
    "baker": Person("Baker", skin=(156, 96, 60), hair="shaved", kohl=False, garment="loincloth", prop="bread"),
    "boatman": Person("Boatman", skin=(150, 92, 58), hair="shaved", kohl=False, garment="loincloth", prop="spear"),
    "soldier": Person("Expedition soldier", skin=(160, 98, 62), hair="short_wig", kohl=True, garment="kilt", prop="spear"),
    "noblewoman": Person("Noblewoman (Nofret type)", skin=SKIN_F, hair="long_wig", kohl=True, malachite=True, headwear="headband",
                         head_col=(244, 240, 230), garment="sheath_dress", bare_chest=False, collar=True, bracelets=True),
    "woman": Person("Woman", skin=(196, 140, 92), hair="long_wig", garment="sheath_dress", bare_chest=False),
    "child": Person("Child", skin=(170, 110, 72), height=0.7, hair="plait_side", kohl=False, garment="loincloth"),
}


def get(world, key):
    return WORLDS[world][key]


# ------------------------------------------------------------------------------------------------ the head
@lru_cache(maxsize=4000)
def head_sprite(person: Person, face, kq, u):
    k = kq / 10
    W = int(10 * u)
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, W * 0.6
    R = 1.55 * u
    p = person
    hc = p.hair_col
    # behind the head: long wigs, nemes lappets, plaits
    if p.hair == "long_wig" and p.headwear not in ("nemes",):
        d.rounded_rectangle([cx - R * 1.25 - OUT, cy - R * 1.15 - OUT, cx + R * 1.25 + OUT, cy + R * 1.45 + OUT], radius=R * 0.6, fill=LINE)
        d.rounded_rectangle([cx - R * 1.25, cy - R * 1.15, cx + R * 1.25, cy + R * 1.45], radius=R * 0.6, fill=hc)
        for i in range(7):
            x = cx - R * 1.1 + i * R * 0.37
            d.line([(x, cy - R * 0.4), (x, cy + R * 1.4)], fill=shade(hc, 0.6) if hc[0] > 40 else (60, 56, 60), width=3)
    if p.headwear == "nemes":
        for side in (-1, 1):
            if side * k > 0.6:
                continue
            x0 = cx + side * R * 0.9
            d.polygon([(x0 - 0.6 * u, cy - R * 0.2), (x0 + 0.6 * u, cy - R * 0.2), (x0 + side * 0.2 * u + 0.55 * u, cy + R * 1.5),
                       (x0 + side * 0.2 * u - 0.55 * u, cy + R * 1.5)], fill=p.head_col, outline=LINE)
            for i in range(1, 6):
                yy = cy - R * 0.2 + i * R * 0.3
                d.line([(x0 - 0.5 * u, yy), (x0 + 0.5 * u, yy)], fill=shade(p.head_col, 0.8), width=3)
    if p.hair == "plait_side":
        sx = cx - (1 if k >= 0 else -1) * R * 0.95
        d.line([(sx, cy - R * 0.3), (sx - 0.1 * u, cy + R * 1.2)], fill=hc, width=int(0.35 * u))
    # ears (hidden under wigs and headcloths)
    if p.hair in ("shaved", "none", "stubble") and p.headwear in ("none", "white_crown", "red_crown", "double_crown", "headband"):
        for side in (-1, 1):
            if side * k > 0.5:
                continue
            ell(d, cx + side * R * 0.98 - k * 0.2 * u, cy + 0.15 * u, 0.26 * u, 0.36 * u, shade(p.skin, 0.92))
    shaded_ell(d, cx + k * 0.12 * u, cy + 0.1 * u, R * (1 - 0.07 * abs(k)), R * 1.05, p.skin, 1 if k >= 0 else -1)
    fx = cx + k * 0.65 * u
    # face
    eyes(d, fx, cy + 0.05 * u, u, face, k, gap=0.52, w=0.3, h=0.36, iris=(40, 28, 20))
    if p.kohl and face.blink < 0.6:                                              # black kohl line extended to the temple
        for side in (-1, 1):
            if abs(k) > 0.85 and side * k < 0:
                continue
            ex = fx + side * 0.52 * u * (1 - 0.5 * abs(k))
            d.line([(ex - 0.32 * u, cy - 0.25 * u), (ex + 0.32 * u, cy - 0.25 * u), (ex + side * 0.55 * u, cy - 0.12 * u)], fill=(20, 18, 18), width=5)
            if p.malachite:
                d.line([(ex - 0.28 * u, cy + 0.38 * u), (ex + 0.3 * u, cy + 0.38 * u)], fill=(60, 150, 100), width=4)
    ell(d, fx + k * 0.45 * u, cy + 0.55 * u, 0.17 * u, 0.15 * u, shade(p.skin, 0.88), w=3)
    if p.beard == "stubble":
        d.chord([cx - R * 0.85, cy - R * 0.1, cx + R * 0.85 + k * 0.1 * u, cy + R * 1.05], 20, 160, fill=shade(p.skin, 0.8))
    if p.beard == "full":
        d.chord([cx - R * 0.95, cy - R * 0.3, cx + R * 0.95 + k * 0.1 * u, cy + R * 1.35], 0, 180, fill=p.beard_col, outline=LINE)
    mouth(d, fx + k * 0.2 * u, cy + 0.95 * u, u, face.mouth, k, sz=0.85)
    if p.beard == "false_beard":                                                 # narrow straight royal false beard
        bx = fx + k * 0.2 * u
        d.rectangle([bx - 0.22 * u - 3, cy + R * 0.95 - 3, bx + 0.22 * u + 3, cy + R * 1.65 + 3], fill=LINE)
        d.rectangle([bx - 0.22 * u, cy + R * 0.95, bx + 0.22 * u, cy + R * 1.65], fill=(40, 34, 30))
        for i in range(3):
            d.line([(bx - 0.2 * u, cy + R * (1.1 + i * 0.18)), (bx + 0.2 * u, cy + R * (1.1 + i * 0.18))], fill=(90, 80, 70), width=3)
    if p.beard == "moustache":
        d.polygon([(fx - 0.45 * u, cy + 0.78 * u), (fx + k * 0.2 * u, cy + 0.66 * u), (fx + 0.45 * u, cy + 0.78 * u), (fx, cy + 0.84 * u)], fill=p.beard_col)
    # hair and headwear on top
    if p.hair == "short_wig" and p.headwear in ("none", "headband"):
        d.chord([cx - R * 1.12 - OUT, cy - R * 1.2 - OUT, cx + R * 1.12 + OUT, cy + R * 0.5 + OUT], 180, 360, fill=LINE)
        d.chord([cx - R * 1.12, cy - R * 1.2, cx + R * 1.12, cy + R * 0.5], 180, 360, fill=hc)
        for side in (-1, 1):
            if side * k > 0.55:
                continue
            d.rounded_rectangle([cx + side * R * 0.8 - 0.32 * u, cy - R * 0.45, cx + side * R * 0.8 + 0.32 * u, cy + R * 0.35], radius=6, fill=hc)
        for i in range(5):
            d.arc([cx - R + i * R * 0.45, cy - R * 1.05, cx - R + i * R * 0.45 + R * 0.5, cy - R * 0.6], 200, 340, fill=(60, 54, 54), width=3)
    if p.hair == "long_wig" and p.headwear in ("none", "headband"):
        d.chord([cx - R * 1.18 - OUT, cy - R * 1.22 - OUT, cx + R * 1.18 + OUT, cy + R * 0.4 + OUT], 180, 360, fill=LINE)
        d.chord([cx - R * 1.18, cy - R * 1.22, cx + R * 1.18, cy + R * 0.4], 180, 360, fill=hc)
    if p.hair == "shaved":
        d.chord([cx - R * 0.98, cy - R * 0.98, cx + R * 0.98, cy + R * 0.3], 190, 350, fill=shade(p.skin, 0.88))
    if p.headwear == "headband":
        d.line([(cx - R * 1.1, cy - R * 0.55), (cx + R * 1.1, cy - R * 0.55)], fill=p.head_col, width=int(0.25 * u))
        ell(d, fx, cy - R * 0.58, 0.18 * u, 0.18 * u, (181, 69, 43), w=3)
    if p.headwear == "nemes":
        d.chord([cx - R * 1.18 - OUT, cy - R * 1.25 - OUT, cx + R * 1.18 + OUT, cy + R * 0.25 + OUT], 180, 360, fill=LINE)
        d.chord([cx - R * 1.18, cy - R * 1.25, cx + R * 1.18, cy + R * 0.25], 180, 360, fill=p.head_col)
        for i in range(1, 4):
            d.arc([cx - R * 1.1, cy - R * (1.2 - i * 0.18), cx + R * 1.1, cy + R * 0.25], 190, 350, fill=shade(p.head_col, 0.8), width=3)
        d.line([(cx - R * 1.05, cy - R * 0.45), (cx + R * 1.05, cy - R * 0.45)], fill=LINE, width=4)
        ux = fx + k * 0.1 * u                                                    # uraeus cobra on the brow
        d.polygon([(ux - 0.15 * u, cy - R * 0.45), (ux + 0.15 * u, cy - R * 0.45), (ux + 0.05 * u, cy - R * 0.85), (ux - 0.12 * u, cy - R * 0.8)],
                  fill=(212, 165, 55), outline=LINE)
    if p.headwear in ("white_crown", "double_crown"):                            # tall white crown (hedjet), bulbous top
        col = (244, 240, 230)
        pts = [(cx - R * 0.9, cy - R * 0.35), (cx - R * 0.75, cy - R * 2.0), (cx - R * 0.35, cy - R * 2.6), (cx, cy - R * 2.75),
               (cx + R * 0.35, cy - R * 2.6), (cx + R * 0.75, cy - R * 2.0), (cx + R * 0.9, cy - R * 0.35)]
        if p.headwear == "double_crown":                                         # red outer crown (deshret) around it
            red = (181, 52, 40)
            d.polygon([(cx - R * 1.12, cy - R * 0.3), (cx - R * 1.05, cy - R * 1.55), (cx + R * 1.05, cy - R * 1.55), (cx + R * 1.12, cy - R * 0.3)],
                      fill=red, outline=LINE)                                    # the red crown's low cap
            d.polygon([(cx + R * 0.75, cy - R * 1.5), (cx + R * 1.05, cy - R * 1.5), (cx + R * 1.05, cy - R * 2.45), (cx + R * 0.8, cy - R * 2.45)],
                      fill=red, outline=LINE)                                    # its tall back piece
            pts = [(x * 0.62 + cx * 0.38, y) for x, y in pts]
        d.polygon(pts, fill=col, outline=LINE)
        ux = fx + k * 0.1 * u
        d.polygon([(ux - 0.15 * u, cy - R * 0.4), (ux + 0.15 * u, cy - R * 0.4), (ux + 0.05 * u, cy - R * 0.8)], fill=(212, 165, 55), outline=LINE)
    bb = im.getbbox()
    return im.crop(bb), cx - bb[0], cy - bb[1]


# ------------------------------------------------------------------------------------------------ props
def prop(d, kind, x, y, u, f):
    if kind in ("staff", "spear", "scroll"):
        H.prop(d, kind, x, y, u, f)
    elif kind == "palette":
        d.rounded_rectangle([x - 0.25 * u, y - 1.5 * u, x + 0.25 * u, y + 0.3 * u], radius=6, fill=(222, 196, 150), outline=LINE, width=4)
        ell(d, x, y - 1.1 * u, 0.1 * u, 0.1 * u, (180, 40, 30), w=2)
        ell(d, x, y - 0.8 * u, 0.1 * u, 0.1 * u, (20, 18, 18), w=2)
    elif kind == "rope":
        d.arc([x - 0.6 * u, y - 0.2 * u, x + 0.6 * u, y + 1.4 * u], 0, 360, fill=(170, 140, 90), width=int(0.18 * u))
    elif kind == "bread":                                                        # bell-shaped Old Kingdom bread mould
        d.polygon([(x - 0.5 * u, y), (x + 0.5 * u, y), (x + 0.3 * u, y - 1.0 * u), (x - 0.3 * u, y - 1.0 * u)], fill=(176, 100, 60), outline=LINE)
    elif kind == "jar":
        ell(d, x, y - 0.6 * u, 0.5 * u, 0.7 * u, (176, 100, 60))


# ------------------------------------------------------------------------------------------------ the figure
def draw(person: Person, p, s=1.0, flip=False, view=0.6):
    u = 40 * s
    f = -1 if flip else 1
    v = max(0.0, min(1.0, view))
    k = f * v
    Wt, Ht = int((20 if p.rot else 12) * u), int(16 * u)
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gx, gy = Wt / 2, Ht - 0.9 * u
    L = 1.55 * u * person.height
    hip_y = gy - (2 * L + 0.3 * u) - p.y * u
    hx = gx
    sk = person.skin
    gc = person.garment_col
    legs = []
    for side, th, kn in ((-1, p.th_r, p.kn_r), (1, p.th_l, p.kn_l)):
        hp = (hx + side * 0.5 * u * (1 - 0.6 * v) * person.build, hip_y)
        knee = _down(*hp, th, L, f)
        ankle = _down(*knee, th - kn, L, f)
        legs.append((hp, knee, ankle))
    long_dress = person.garment in ("sheath_dress", "robe", "jama", "deel")
    for i, (hp, knee, ankle) in enumerate(legs):
        dk = 0.86 if i == 0 else 1.0
        thigh = gc if person.garment in ("coat_breeches",) else sk
        limb(d, [hp, knee, ankle], [0.78 * u, 0.62 * u], [shade(thigh, dk), shade(sk, dk)])
        foot = sk if person.footwear == "barefoot" else person.foot_col
        ell(d, ankle[0] + f * 0.25 * u * v, ankle[1] + 0.05 * u, 0.5 * u, 0.26 * u, shade(foot, dk), w=4)
        if person.footwear == "sandals":
            d.line([(ankle[0] - 0.2 * u, ankle[1] - 0.05 * u), (ankle[0] + 0.25 * u, ankle[1] + 0.1 * u)], fill=(120, 84, 48), width=4)
    lean = p.lean * f
    T = 3.2 * u * person.height
    sw = 1.3 * u * person.build * (1 - 0.3 * v)

    def body_pt(dx, dy):
        rx, ry = _rot(dx, dy, lean)
        return hx + rx, hip_y + ry

    fr_sh = body_pt(f * sw * (1 - 0.6 * v), -(T - 0.45 * u))
    bk_sh = body_pt(-f * sw * (1 - 0.6 * v), -(T - 0.45 * u))
    neck = body_pt(0, -T)
    back_dir = f if v >= 0.3 else -f

    def arm(sh_pt, sh, el, back, held):
        fdir = back_dir if back else f
        elbow = _down(*sh_pt, sh, 1.3 * u * person.height, fdir)
        hand = _down(*elbow, sh + el, 1.2 * u * person.height, fdir)
        dk = 0.86 if back else 1.0
        sleeve = gc if (not person.bare_chest and person.garment in ("robe", "jama", "deel", "coat_breeches", "tunic")) else sk
        limb(d, [sh_pt, elbow, hand], [0.56 * u, 0.48 * u], [shade(sleeve, dk), shade(sk, dk)])
        if person.bracelets:
            d.line([_down(*elbow, sh + el, 0.9 * u, fdir), _down(*elbow, sh + el, 1.0 * u, fdir)], fill=(47, 163, 154), width=int(0.5 * u))
        ell(d, hand[0], hand[1], 0.28 * u, 0.28 * u, shade(sk, dk), w=4)
        if held:
            prop(d, held, hand[0], hand[1], u, fdir)

    if v >= 0.3:
        arm(bk_sh, p.sh_r, p.el_r, True, "")
    # torso sprite
    tor, piv = torso_sprite(person, round(lean), round(u, 2), round(k, 1))
    im.alpha_composite(tor, (int(hx - piv[0]), int(hip_y - piv[1])))
    if v < 0.3:
        arm(bk_sh, p.sh_r, p.el_r, True, "")
    hang = round(lean + p.head * f)
    spr, ox, oy = head_sprite(person, p.face, round(k * 10), round(u, 2))
    spr, (ox, oy) = rot_sprite(spr, (ox, oy), hang)
    hdx, hdy = _rot(0, -1.75 * u, hang)
    im.alpha_composite(spr, (int(neck[0] + hdx - ox), int(neck[1] + hdy - oy)))
    arm(fr_sh, p.sh_l, p.el_l, False, person.prop or p.prop_l)
    bb = im.getbbox() or (0, 0, 2, 2)
    x0, y0 = max(0, bb[0] - 4), max(0, bb[1] - 4)
    out = im.crop((x0, y0, min(Wt, bb[2] + 4), min(Ht, bb[3] + 4)))
    ax, ay = gx - x0, gy - y0
    if abs(p.sq - 1.0) > 0.015:
        w0, h0 = out.size
        nw, nh = max(2, int(w0 / math.sqrt(p.sq))), max(2, int(h0 * p.sq))
        out = out.resize((nw, nh), Image.BILINEAR)
        ax, ay = ax * nw / w0, ay * nh / h0
    if p.rot:
        out, (ax, ay) = rot_sprite(out, (ax, ay), p.rot * f)
    if out.width % 2 or out.height % 2:
        out = out.crop((0, 0, out.width + out.width % 2, out.height + out.height % 2))
    return out.reduce(2), ax / 2, ay / 2


@lru_cache(maxsize=2000)
def torso_sprite(person: Person, ang, u, k):
    v = abs(k)
    f = 1 if k >= 0 else -1
    T = 3.2 * u * person.height
    sw = 1.3 * u * person.build * (1 - 0.3 * v)
    long_dress = person.garment in ("sheath_dress", "robe", "jama", "deel")
    drop = (2.6 * u * person.height) if long_dress else 0.0
    W, Hh = int(2 * sw + 3 * u), int(T + drop + 1.6 * u)
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hx, hy = W / 2, T + 0.6 * u
    top = hy - T
    sk, gc = person.skin, person.garment_col
    chest = sk if person.bare_chest else gc
    body = [(hx - sw * 0.88, top), (hx + sw * 0.88, top), (hx + sw * 0.95, top + 0.5 * u), (hx + sw * 0.85, hy + 0.2 * u),
            (hx - sw * 0.85, hy + 0.2 * u), (hx - sw * 0.95, top + 0.5 * u)]
    d.polygon([(x + (OUT if x > hx else -OUT), y + (OUT if y > hy - T / 2 else -OUT)) for x, y in body], fill=LINE)
    d.polygon(body, fill=chest)
    d.polygon([(hx - f * sw * 0.95, top + 0.5 * u), (hx - f * sw * 0.85, hy + 0.2 * u), (hx - f * sw * 0.45, hy + 0.2 * u),
               (hx - f * sw * 0.55, top + 0.3 * u)], fill=shade(chest, 0.88))
    if person.garment == "sheath_dress":                                         # strapped white sheath dress
        d.polygon([(hx - sw * 0.85, top + 1.0 * u), (hx + sw * 0.85, top + 1.0 * u), (hx + sw * 0.75, hy + drop), (hx - sw * 0.75, hy + drop)],
                  fill=gc, outline=LINE)
        for side in (-1, 1):
            d.line([(hx + side * sw * 0.45, top), (hx + side * sw * 0.55, top + 1.05 * u)], fill=gc, width=int(0.25 * u))
    elif person.garment in ("robe", "jama", "deel"):
        d.polygon([(hx - sw * 0.92, top + 0.3 * u), (hx + sw * 0.92, top + 0.3 * u), (hx + sw * 1.05, hy + drop), (hx - sw * 1.05, hy + drop)],
                  fill=gc, outline=LINE)
        d.line([(hx + k * 0.3 * u, top + 0.3 * u), (hx + k * 0.3 * u, hy + drop)], fill=shade(gc, 0.8), width=4)
    elif person.garment in ("kilt", "loincloth"):
        kt = hy - 0.9 * u
        bottom = hy + (0.4 * u if person.garment == "loincloth" else 1.3 * u)
        d.polygon([(hx - sw * 0.9, kt), (hx + sw * 0.9, kt), (hx + sw * 0.95, bottom), (hx - sw * 0.95, bottom)], fill=gc, outline=LINE)
        if person.garment == "kilt":
            for i in range(1, 6):
                xx = hx - sw * 0.9 + i * sw * 0.3
                d.line([(xx, kt + 0.2 * u), (xx + k * 0.1 * u, bottom - 0.05 * u)], fill=shade(gc, 0.82), width=3)
            d.rectangle([hx - sw * 0.92, kt - 0.15 * u, hx + sw * 0.92, kt + 0.15 * u], fill=person.garment_col2 if person.collar else shade(gc, 0.9),
                        outline=LINE, width=3)
    if person.collar:
        H.collar(d, hx + k * 0.3 * u, top + 0.1 * u, sw * 0.95, u)
    if person.sash:
        d.polygon([(hx - sw * 0.8, top + 0.5 * u), (hx - sw * 0.55, top + 0.3 * u), (hx + sw * 0.85, hy - 0.6 * u), (hx + sw * 0.6, hy - 0.3 * u)],
                  fill=person.garment_col2, outline=LINE)
    return rot_sprite(im, (hx, hy), ang)
