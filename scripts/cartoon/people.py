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

import costume as K
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
    footwear: str = "barefoot"       # barefoot | sandals | boots | shoes | slippers
    foot_col: tuple = (150, 110, 70)
    prop: str = ""                   # staff | scroll | palette | spear | bow | rope | bread | jar (+ costume.prop kinds)
    # ---- period kit (costume.py); all optional, the Egypt cast ignores them
    head_col2: tuple = (212, 165, 55)    # turban band / hat trim
    jewel: bool = False                  # sarpech and plume, hat jewel, Persian kulah
    garment_col3: tuple = (107, 66, 38)  # belt / sash / lacing / waistcoat
    hem: float = -1.0                    # robe length below the hip (head units); -1 = the garment's usual length
    flags: tuple = ()                    # garment details: fur, pleats, pattern, gold, gold_belt, translucent, officer, venetians, cross, eagle
    neck: str = ""                       # ruff | rebato | falling_band | stock | jabot | gorget | fur_collar | beads ("stock+gorget")
    pearls: bool = False
    earrings: bool = False
    chain: bool = False
    tilak: bool = False
    cloak: str = ""                      # long | gown | fur | short | nadiri | shawl | cape
    cloak_col: tuple = (40, 40, 44)
    cloak_trim: tuple = (150, 112, 74)
    legs: tuple = ()                     # (thigh, shin) colours: trousers, hose, stockings, gaiters, mail
    sleeves: tuple = ()                  # (upper, fore) sleeve colours
    arm_w: float = 0.56
    cuff_col: tuple = ()
    hand_col: tuple = ()
    tiraz: bool = False                  # gold bands on the upper arms
    prop2: str = ""                      # held in the far hand
    shield: str = ""                     # round | heater
    shield_col: tuple = (150, 40, 40)
    shield_charge: str = ""              # eagle | boss
    brows_thick: bool = False
    old: bool = False
    blush: bool = False
    mount: str = ""                      # mongol | big: drawn riding that horse
    horse_col: tuple = (184, 150, 104)
    mane_col: tuple = (60, 44, 32)
    tack_col: tuple = (107, 66, 38)
    cloth_col: tuple = ()                # saddle cloth
    blaze: bool = False
    gait: str = "gallop"                 # gallop | walk (mounts), pace (camel)
    creature: str = ""                   # camel
    load: bool = True


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


def modern(person):
    """True for people dressed from the costume kit (drawn by draw2); the Egypt cast keeps the original path."""
    return bool(person.mount or person.creature or person.garment in K.GARMENTS or person.headwear in K.HATS or person.hair in K.HAIR
                or person.beard in K.BEARDS)


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
    elif kind:
        K.prop(d, kind, x, y, u, f)


# ------------------------------------------------------------------------------------------------ the figure
def draw(person: Person, p, s=1.0, flip=False, view=0.6):
    if modern(person):
        return draw2(person, p, s, flip, view)
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


# ================================================================================================ period cast (costume kit)
# draw2 dresses people from costume.py (hats, hair, beards, garments, cloaks, props) and can seat them on a horse.
HEM = {"deel": 2.5, "deel_w": 3.0, "lamellar": 1.9, "kazaghand": 1.9, "mail_surcoat": 2.3, "oyoroi": 1.45, "robe_round": 3.0, "habit": 3.15,
       "cotta": 2.3, "doublet": 1.0, "buffcoat": 1.2, "farthingale": 3.4, "slops": 1.6, "jerkin": 1.5, "jama": 2.2, "frock": 1.6, "redcoat": 1.5,
       "sepoy": 0.9, "dhoti": 2.2}
EARS_HIDDEN_HAIR = {"bob", "long", "red_curls", "long_wig", "short_wig"}
EARS_HIDDEN_HAT = {"hood", "boqta", "great_helm", "kettle_hat", "mongol_flaps", "mamluk_helmet"}
HOST_PROPS = {"map", "book", "seal", "stamp", "cane", "pepper", "chart", "rifle"}
SEAT = {"mongol": (64, 108), "big": (30, 42)}                    # rider's thigh angle and knee bend per horse (short / long stirrups)


def _held(d, kind, x, y, u, f):
    if kind in HOST_PROPS:
        H.prop(d, kind, x, y, u, f)
    elif kind:
        prop(d, kind, x, y, u, f)


def gait_phase(p):
    """Gait phase (0..1) of a walking pose from its leg angles, or None when standing still (drives the horse/camel legs)."""
    dx = (p.th_l - p.th_r) / 40.0
    dy = (p.kn_l - p.kn_r) / 50.0
    if math.hypot(dx, dy) < 0.15:
        return None
    return (-math.atan2(dy, dx) / (2 * math.pi)) % 1.0


@lru_cache(maxsize=4000)
def head_sprite2(person: Person, face, kq, u):
    k = kq / 10
    tall = person.headwear in K.TALL_HATS
    W = int((16 if tall else 12) * u)
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, W * (0.68 if tall else 0.6)
    R = 1.55 * u
    p = person
    hw = p.headwear if p.headwear in K.HATS else ""
    hatted = bool(hw) and hw != "hood_down"
    hc1 = None if p.head_col == (244, 240, 230) else p.head_col                  # unset: the kit's own colours for that hat
    hc2 = None if p.head_col2 == (212, 165, 55) else p.head_col2
    if hw:
        K.hat_back(d, hw, cx, cy, R, u, k, hc1, hc2)
    if p.hair in K.HAIR:
        K.hair_back(d, p.hair, cx, cy, R, u, k, p.hair_col)
    if p.hair not in EARS_HIDDEN_HAIR and hw not in EARS_HIDDEN_HAT:
        for side in (-1, 1):
            if side * k > 0.5:
                continue
            ex = cx + side * R * 0.98 - k * 0.2 * u
            ell(d, ex, cy + 0.15 * u, 0.26 * u, 0.36 * u, shade(p.skin, 0.92))
            if p.earrings:                                                       # pearl or gold drop
                ell(d, ex, cy + 0.62 * u, 0.12 * u, 0.15 * u, (246, 242, 230) if p.pearls else (226, 190, 90), w=3)
    shaded_ell(d, cx + k * 0.12 * u, cy + 0.1 * u, R * (1 - 0.07 * abs(k)), R * 1.05, p.skin, 1 if k >= 0 else -1)
    fx = cx + k * 0.65 * u
    if p.blush:
        for side in (-1, 1):
            if abs(k) < 0.85 or side * k > 0:
                d.ellipse([fx + side * 0.75 * u - 0.28 * u, cy + 0.42 * u, fx + side * 0.75 * u + 0.28 * u, cy + 0.72 * u], fill=(236, 150, 150))
    if p.old:                                                                     # a few lines, kindly drawn
        for side in (-1, 1):
            if abs(k) > 0.85 and side * k < 0:
                continue
            x = fx + side * 0.55 * u * (1 - 0.5 * abs(k))
            d.arc([x - 0.35 * u, cy + 0.35 * u, x + 0.35 * u, cy + 1.05 * u], 200 if side < 0 else 270, 270 if side < 0 else 340, fill=shade(p.skin, 0.72),
                  width=3)
            d.arc([x - 0.25 * u, cy + 0.12 * u, x + 0.25 * u, cy + 0.42 * u], 20, 160, fill=shade(p.skin, 0.75), width=2)
    eyes(d, fx, cy + 0.05 * u, u, face, k, gap=0.52, w=0.3, h=0.36, iris=(40, 28, 20) if p.skin[0] < 230 else (70, 90, 120))
    if p.brows_thick and face.blink < 0.6:
        for side in (-1, 1):
            if abs(k) > 0.85 and side * k < 0:
                continue
            ex = fx + side * 0.52 * u * (1 - 0.5 * abs(k))
            d.line([(ex - 0.32 * u, cy - 0.42 * u), (ex + 0.32 * u, cy - 0.45 * u)], fill=(40, 30, 26), width=int(0.16 * u))
    if p.tilak:
        d.rounded_rectangle([fx - 0.07 * u, cy - 0.75 * u, fx + 0.07 * u, cy - 0.35 * u], radius=3, fill=(200, 40, 40))
    ell(d, fx + k * 0.45 * u, cy + 0.55 * u, 0.17 * u, 0.15 * u, shade(p.skin, 0.88), w=3)
    if p.beard in K.BEARDS:
        K.beard_chin(d, p.beard, fx + k * 0.2 * u, cy, R, u, k, p.beard_col)
    elif p.beard == "stubble":
        d.chord([cx - R * 0.85, cy - R * 0.1, cx + R * 0.85 + k * 0.1 * u, cy + R * 1.05], 20, 160, fill=shade(p.skin, 0.8))
    elif p.beard == "full":
        d.chord([cx - R * 0.95, cy - R * 0.3, cx + R * 0.95 + k * 0.1 * u, cy + R * 1.35], 0, 180, fill=p.beard_col, outline=LINE)
    mouth(d, fx + k * 0.2 * u, cy + 0.95 * u, u, face.mouth, k, sz=0.85)
    if p.beard in K.BEARDS or p.beard == "droop":
        K.moustache(d, p.beard, fx + k * 0.2 * u, cy + 0.95 * u, R, u, k, p.beard_col)
    elif p.beard == "moustache":
        d.polygon([(fx - 0.45 * u, cy + 0.78 * u), (fx + k * 0.2 * u, cy + 0.66 * u), (fx + 0.45 * u, cy + 0.78 * u), (fx, cy + 0.84 * u)], fill=p.beard_col)
    if p.hair in K.HAIR:
        K.hair_front(d, p.hair, cx, cy, R, u, k, p.hair_col, p.skin, hatted=hatted and hw not in ("hood_down",))
    elif p.hair == "shaved":
        d.chord([cx - R * 0.98, cy - R * 0.98, cx + R * 0.98, cy + R * 0.3], 190, 350, fill=shade(p.skin, 0.88))
    if hw:
        K.hat(d, hw, cx, cy, R, u, k, hc1, hc2, jewel=p.jewel)
    bb = im.getbbox()
    return im.crop(bb), cx - bb[0], cy - bb[1]


@lru_cache(maxsize=2000)
def torso_sprite2(person: Person, ang, u, k, mounted=False):
    v = abs(k)
    f = 1 if k >= 0 else -1
    T = 3.2 * u * person.height
    sw = 1.3 * u * person.build * (1 - 0.3 * v)
    hem = (person.hem if person.hem >= 0 else HEM.get(person.garment, 1.0)) * person.height
    if mounted:
        hem = min(hem, 1.5)
    top_pad = 3.4 * u
    W, Hh = int(2 * sw * 2.6 + 7 * u), int(T + top_pad + hem * u + 2.0 * u)
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hx, hy = W / 2, T + top_pad
    top = hy - T
    necks = person.neck.split("+") if person.neck else []
    if "rebato" in necks:                                                         # wired lace fan behind the head, gauze wings
        lay = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        for side in (-1, 1):
            ld.ellipse([hx + side * 1.6 * u - 1.1 * u, top - 3.0 * u, hx + side * 1.6 * u + 1.1 * u, top + 0.2 * u], fill=(250, 250, 250, 110),
                       outline=(170, 170, 176, 200), width=3)
        im.alpha_composite(lay)
        r = 2.25 * u
        for i in range(15):                                                       # scalloped lace edge
            a = math.pi * (1 + i / 14)
            ell(d, hx + r * math.cos(a), top + 0.1 * u + r * 1.05 * math.sin(a), 0.24 * u, 0.24 * u, (250, 250, 248), w=3)
        d.pieslice([hx - r, top + 0.1 * u - r * 1.05, hx + r, top + 0.1 * u + r * 1.05], 180, 360, fill=(250, 250, 248))
        for i in range(1, 10):
            a = math.pi * (1 + i / 10)
            d.line([(hx, top + 0.1 * u), (hx + r * 0.98 * math.cos(a), top + 0.1 * u + r * 1.03 * math.sin(a))], fill=(206, 204, 198), width=2)
    gc = person.garment_col
    K.garment(d, person.garment, hx, hy, top, sw, u, k, f, gc, person.garment_col2, person.garment_col3, hem, person.flags, person.skin)
    if person.cloak:
        K.cloak(d, person.cloak, hx, hy, top, sw, u, k, f, person.cloak_col, person.cloak_trim, hem)
    cxn = hx + k * 0.3 * u
    for n in necks:
        if n != "rebato":
            K.neck(d, n, cxn, top + 0.05 * u, u, k, person.build)
    if person.chain:
        K.chain(d, cxn, top + 0.1 * u, u, k)
    if person.pearls:
        K.pearls(d, cxn, top + 0.2 * u, u, k, n=3 if person.garment == "farthingale" else 2, drop=2.6 if person.garment == "farthingale" else 1.2)
    return rot_sprite(im, (hx, hy), ang)


def _shield(d, kind, x, y, u, f, col, charge):
    if kind == "round":
        ell(d, x, y, 1.05 * u, 1.05 * u, col)
        d.ellipse([x - 0.85 * u, y - 0.85 * u, x + 0.85 * u, y + 0.85 * u], outline=shade(col, 0.7), width=4)
        for a in range(4):
            bx, by = x + 0.55 * u * math.cos(a * math.pi / 2 + 0.78), y + 0.55 * u * math.sin(a * math.pi / 2 + 0.78)
            ell(d, bx, by, 0.12 * u, 0.12 * u, (226, 190, 90), w=2)
        ell(d, x, y, 0.28 * u, 0.28 * u, (226, 190, 90), w=3)
    elif kind == "heater":                                                        # long heater shield, painted arms
        pts = [(x - 1.0 * u, y - 1.4 * u), (x + 1.0 * u, y - 1.4 * u), (x + 0.95 * u, y + 0.2 * u), (x, y + 1.7 * u), (x - 0.95 * u, y + 0.2 * u)]
        K.poly(d, pts, col)
        if charge == "eagle":
            d.polygon([(x - 0.7 * u, y - 0.9 * u), (x, y - 0.2 * u), (x + 0.7 * u, y - 0.9 * u), (x + 0.45 * u, y + 0.2 * u), (x, y + 0.9 * u),
                       (x - 0.45 * u, y + 0.2 * u)], fill=(26, 26, 26))
            ell(d, x, y - 0.65 * u, 0.22 * u, 0.22 * u, (26, 26, 26), w=2)


def draw2(person: Person, p, s=1.0, flip=False, view=0.6):
    """Same contract as draw(): (tile at 1x, anchor x, anchor y)."""
    u = 40 * s
    f = -1 if flip else 1
    if person.creature == "camel":
        ph = gait_phase(p)
        img, ax, ay = K.camel_sprite(person.horse_col, -1 if ph is None else int(ph * 24) % 24, round(u, 2), f, person.load)
        return _finish(img, ax, ay, p, f, rotate=False)
    mounted = bool(person.mount)
    v = max(0.0, min(1.0, view))
    if mounted:
        v = max(v, 0.7)
    k = f * v
    Wt, Ht = int((30 if mounted else (20 if p.rot else 14)) * u), int(21 * u)
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gx, gy = Wt / 2, Ht - 0.9 * u
    L = 1.55 * u * person.height
    sk = person.skin
    gc = person.garment_col
    legc = person.legs or (sk, sk)
    lean = p.lean * f
    if mounted:
        ph = gait_phase(p)
        cloth = person.cloth_col or None
        hs, hax, hay, sx, sy = K.horse_sprite(person.mount, person.horse_col, person.mane_col, person.tack_col, cloth,
                                              -1 if ph is None else int(ph * 24) % 24, person.gait, round(u, 2), f, person.blaze)
        ox, oy = int(gx - hax), int(gy - hay)
        im.alpha_composite(hs, (ox, oy))
        hx, hip_y = ox + sx, oy + sy
        if ph is not None and person.gait == "gallop":
            lean += 7 * f
        th, kn = SEAT[person.mount]
        hp = (hx + f * 0.15 * u, hip_y)
        knee = _down(*hp, th, L, f)
        ankle = _down(*knee, th - kn, L, f)
        seated = (hp, knee, ankle)
    else:
        hip_y = gy - (2 * L + 0.3 * u) - p.y * u
        hx = gx
        for i, (side, th, kn) in enumerate(((-1, p.th_r, p.kn_r), (1, p.th_l, p.kn_l))):
            hp = (hx + side * 0.5 * u * (1 - 0.6 * v) * person.build, hip_y)
            knee = _down(*hp, th, L, f)
            ankle = _down(*knee, th - kn, L, f)
            _leg(d, person, hp, knee, ankle, u, f, v, 0.86 if i == 0 else 1.0, legc)
    T = 3.2 * u * person.height
    sw = 1.3 * u * person.build * (1 - 0.3 * v)

    def body_pt(dx, dy):
        rx, ry = _rot(dx, dy, lean)
        return hx + rx, hip_y + ry

    fr_sh = body_pt(f * sw * (1 - 0.6 * v), -(T - 0.45 * u))
    bk_sh = body_pt(-f * sw * (1 - 0.6 * v), -(T - 0.45 * u))
    neck = body_pt(0, -T)
    back_dir = f if v >= 0.3 else -f
    if person.sleeves:
        sl = person.sleeves
    elif person.garment == "dhoti":
        sl = (sk, sk)
    elif person.garment == "lamellar":
        sl = (person.garment_col2, person.garment_col2)
    elif person.garment == "mail_surcoat":
        sl = (person.garment_col2, person.garment_col2)
    else:
        sl = (gc, gc)
    hand_c = person.hand_col or sk
    piece = K.SHOULDER_PIECES.get(person.garment)
    hands = {}

    def arm(sh_pt, sh, el, back, held):
        fdir = back_dir if back else f
        elbow = _down(*sh_pt, sh, 1.3 * u * person.height, fdir)
        hand = _down(*elbow, sh + el, 1.2 * u * person.height, fdir)
        dk = 0.86 if back else 1.0
        limb(d, [sh_pt, elbow, hand], [person.arm_w * u, person.arm_w * 0.86 * u], [shade(sl[0], dk), shade(sl[1], dk)])
        if person.cuff_col:
            cuff = _down(*elbow, sh + el, 1.2 * u * person.height * 0.72, fdir)
            limb(d, [cuff, hand], [person.arm_w * 0.95 * u], [shade(person.cuff_col, dk)])
        if piece:
            K.arm_piece(d, piece, sh_pt, elbow, hand, u, shade(gc, dk), person.garment_col3 if piece == "pauldron" else person.garment_col2)
        if person.tiraz:
            K.arm_piece(d, "tiraz", sh_pt, elbow, hand, u, gc, gc)
        if person.bracelets:
            d.line([_down(*elbow, sh + el, 0.9 * u, fdir), _down(*elbow, sh + el, 1.0 * u, fdir)], fill=(226, 190, 90), width=int(0.45 * u))
        ell(d, hand[0], hand[1], 0.28 * u, 0.28 * u, shade(hand_c, dk), w=4)
        hands["back" if back else "front"] = hand
        if held:
            _held(d, held, hand[0], hand[1], u, fdir)

    if v >= 0.3:
        arm(bk_sh, p.sh_r, p.el_r, True, person.prop2)
    tor, piv = torso_sprite2(person, round(lean), round(u, 2), round(k, 1), mounted)
    im.alpha_composite(tor, (int(hx - piv[0]), int(hip_y - piv[1])))
    if mounted:                                                                   # near leg over the split robe, in the stirrup
        hp, knee, ankle = seated
        d.line([(hx + f * 0.05 * u, hip_y + 0.35 * u), ankle], fill=LINE, width=7)                     # stirrup leather
        d.line([(hx + f * 0.05 * u, hip_y + 0.35 * u), ankle], fill=person.tack_col, width=4)
        _leg(d, person, hp, knee, ankle, u, f, v, 1.0, legc)
        d.rounded_rectangle([ankle[0] - 0.35 * u, ankle[1] + 0.22 * u, ankle[0] + 0.45 * u, ankle[1] + 0.36 * u], radius=3, fill=(150, 150, 154),
                            outline=LINE, width=3)                                # iron stirrup tread
    if v < 0.3:
        arm(bk_sh, p.sh_r, p.el_r, True, person.prop2)
    if person.shield and "back" in hands:
        _shield(d, person.shield, hands["back"][0], hands["back"][1] - 0.3 * u, u, f, person.shield_col, person.shield_charge)
    hang = round(lean + p.head * f)
    spr, ox_, oy_ = head_sprite2(person, p.face, round(k * 10), round(u, 2))
    spr, (ox_, oy_) = rot_sprite(spr, (ox_, oy_), hang)
    hdx, hdy = _rot(0, -1.75 * u, hang)
    im.alpha_composite(spr, (int(neck[0] + hdx - ox_), int(neck[1] + hdy - oy_)))
    arm(fr_sh, p.sh_l, p.el_l, False, person.prop or p.prop_l)
    return _finish(im, gx, gy, p, f)


def _leg(d, person, hp, knee, ankle, u, f, v, dk, legc):
    limb(d, [hp, knee, ankle], [0.78 * u, 0.62 * u], [shade(legc[0], dk), shade(legc[1], dk)])
    fw = person.footwear
    if fw == "boots":
        bt = (ankle[0] + (knee[0] - ankle[0]) * 0.6, ankle[1] + (knee[1] - ankle[1]) * 0.6)
        limb(d, [bt, ankle], [0.7 * u], [shade(person.foot_col, dk)])
    foot = person.skin if fw == "barefoot" else person.foot_col
    fx_ = ankle[0] + f * 0.25 * u * v
    ell(d, fx_, ankle[1] + 0.05 * u, 0.5 * u, 0.26 * u, shade(foot, dk), w=4)
    if fw == "slippers":                                                          # pointed, slightly upturned toe
        tip = (fx_ + f * 0.75 * u, ankle[1] - 0.12 * u)
        d.polygon([(fx_ + f * 0.3 * u, ankle[1] - 0.1 * u), tip, (fx_ + f * 0.35 * u, ankle[1] + 0.2 * u)], fill=shade(foot, dk), outline=LINE)
    elif fw == "sandals":
        d.line([(ankle[0] - 0.2 * u, ankle[1] - 0.05 * u), (ankle[0] + 0.25 * u, ankle[1] + 0.1 * u)], fill=(120, 84, 48), width=4)
    elif fw == "shoes" and person.flags and "roses" in person.flags:
        ell(d, fx_ + f * 0.1 * u, ankle[1] - 0.12 * u, 0.16 * u, 0.13 * u, (168, 35, 58), w=2)


def _finish(im, gx, gy, p, f, rotate=True):
    bb = im.getbbox() or (0, 0, 2, 2)
    Wt, Ht = im.size
    x0, y0 = max(0, bb[0] - 4), max(0, bb[1] - 4)
    out = im.crop((x0, y0, min(Wt, bb[2] + 4), min(Ht, bb[3] + 4)))
    ax, ay = gx - x0, gy - y0
    if abs(p.sq - 1.0) > 0.015:
        w0, h0 = out.size
        nw, nh = max(2, int(w0 / math.sqrt(p.sq))), max(2, int(h0 * p.sq))
        out = out.resize((nw, nh), Image.BILINEAR)
        ax, ay = ax * nw / w0, ay * nh / h0
    if p.rot and rotate:
        out, (ax, ay) = rot_sprite(out, (ax, ay), p.rot * f)
    if out.width % 2 or out.height % 2:
        out = out.crop((0, 0, out.width + out.width % 2, out.height + out.height % 2))
    return out.reduce(2), ax / 2, ay / 2


# ------------------------------------------------------------------------------------------------ the worlds
def _P(name, **kw):
    kw.setdefault("kohl", False)
    kw.setdefault("bare_chest", False)
    return Person(name, **kw)


def _mounted(person, mount, **kw):
    from dataclasses import replace as _r
    return _r(person, name=person.name + " (mounted)", mount=mount, **kw)


# Mongol empire, c. 1160-1368 (visual bible 05). Hair: shaved crown, forelock, braids looped behind the ears.
MS, MS2, MS3 = (222, 178, 136), (210, 164, 120), (228, 188, 148)
DUN, BAY, CHESTNUT, WHITE_H, GREY_H, BLACK_H = (184, 150, 104), (140, 84, 52), (160, 92, 52), (236, 232, 222), (180, 180, 176), (52, 44, 40)
STEPPE = dict(hair="mongol", hair_col=(34, 28, 24), footwear="boots", foot_col=(107, 66, 38), legs=((84, 70, 60), (84, 70, 60)))
WORLDS["mongol_1200"] = {
    "temujin_boy": _P("Temujin as a boy (c. 1170)", skin=MS3, height=0.72, build=0.85, hair="boy_mongol", hair_col=(34, 28, 24), garment="deel",
                      garment_col=(216, 199, 161), garment_col2=(176, 138, 96), garment_col3=(107, 66, 38), flags=("fur",), footwear="boots",
                      foot_col=(107, 66, 38), legs=((84, 70, 60), (84, 70, 60))),
    "hoelun": _P("Hoelun, Temujin's mother", skin=(220, 176, 134), hair="none", headwear="boqta", head_col=(110, 40, 36), head_col2=(201, 165, 74),
                 garment="deel_w", garment_col=(60, 70, 96), garment_col2=(142, 31, 27), garment_col3=(201, 165, 74), footwear="boots",
                 foot_col=(107, 66, 38)),
    "temujin": _P("Temujin (c. 1206)", skin=MS2, build=1.05, beard="sparse", beard_col=(40, 32, 28), headwear="mongol_fur", head_col=(92, 64, 44),
                  head_col2=(150, 112, 74), garment="deel", garment_col=(130, 60, 44), garment_col2=(176, 138, 96), garment_col3=(60, 40, 30),
                  flags=("fur",), prop="whip", **STEPPE),
    "genghis": _P("Chinggis Khan (older, NPM portrait)", skin=(226, 190, 152), build=1.12, beard="long", beard_col=(150, 142, 130),
                  headwear="warming_cap", garment="deel", garment_col=(242, 238, 228), garment_col2=(220, 212, 194), garment_col3=(70, 50, 36),
                  flags=("gold_belt",), old=True, **{**STEPPE, "hair_col": (70, 64, 60)}),
    "borte": _P("Borte, Temujin's wife", skin=(228, 186, 148), hair="none", headwear="boqta", head_col=(142, 31, 27), head_col2=(201, 165, 74),
                garment="deel_w", garment_col=(156, 52, 44), garment_col2=(201, 165, 74), garment_col3=(46, 63, 107), footwear="boots",
                foot_col=(107, 66, 38)),
    "rider": _P("Mongol horse archer (light cavalry)", skin=MS, beard="sparse", headwear="mongol_flaps", head_col=(70, 58, 52), head_col2=(170, 132, 90),
                garment="deel", garment_col=(163, 135, 78), garment_col2=(92, 56, 34), garment_col3=(60, 40, 30), hem=2.0, prop="bow", **STEPPE),
    "rider2": _P("Mongol heavy cavalryman (lamellar)", skin=MS2, beard="sparse", headwear="mongol_helmet", garment="lamellar",
                 garment_col=(111, 114, 118), garment_col2=(46, 74, 122), garment_col3=(143, 42, 34), hem=2.0, prop="lance", **STEPPE),
    "archer": _P("Mongol archer", skin=MS3, beard="sparse", headwear="mongol_fur", head_col=(70, 50, 36), head_col2=(150, 112, 74), garment="deel",
                 garment_col=(120, 110, 70), garment_col2=(92, 56, 34), garment_col3=(60, 40, 30), hem=2.0, prop="bow", **STEPPE),
    "ogedei": _P("Ogedei Khan", skin=MS2, build=1.25, beard="sparse", headwear="mongol_brim", head_col=(60, 50, 44), head_col2=(120, 90, 60),
                 garment="deel", garment_col=(176, 140, 60), garment_col2=(120, 30, 34), garment_col3=(60, 40, 30), flags=("pattern", "pleats", "gold_belt"),
                 prop="cup", **STEPPE),
    "sorghaghtani": _P("Sorghaghtani Beki", skin=MS3, hair="none", headwear="boqta", head_col=(142, 31, 27), head_col2=(201, 165, 74), garment="deel_w",
                       garment_col=(34, 51, 94), garment_col2=(201, 165, 74), garment_col3=(142, 31, 27), flags=("pattern", "gold"), pearls=True,
                       footwear="boots", foot_col=(107, 66, 38)),
    "kublai": _P("Kublai Khan (Yuan court, c. 1280)", skin=(228, 192, 154), build=1.4, beard="sparse", beard_col=(60, 50, 46), headwear="warming_cap",
                 garment="deel", garment_col=(156, 31, 37), garment_col2=(201, 165, 74), garment_col3=(201, 165, 74), flags=("gold_belt",), cloak="fur",
                 cloak_col=(242, 239, 232), cloak_trim=(236, 230, 216), sleeves=((242, 239, 232), (156, 31, 37)), prop="cup", **STEPPE),
    "hulagu": _P("Hulagu Khan", skin=MS, build=1.15, beard="sparse", beard_col=(40, 32, 28), headwear="mongol_brim", head_col=(60, 50, 44),
                 head_col2=(201, 165, 74), garment="deel", garment_col=(98, 40, 46), garment_col2=(201, 165, 74), garment_col3=(60, 40, 30),
                 flags=("pattern", "gold", "pleats", "gold_belt"), **STEPPE),
    "marco": _P("Marco Polo (Venetian, 1270s)", skin=(240, 206, 176), hair="bob", hair_col=(96, 62, 38), headwear="hood", head_col=(42, 60, 107),
                garment="cotta", garment_col=(138, 36, 39), garment_col3=(60, 40, 28), legs=((42, 60, 107), (42, 60, 107)), footwear="shoes",
                foot_col=(60, 40, 28), prop="chao"),
    "rubruck": _P("William of Rubruck (Franciscan friar)", skin=(238, 204, 172), build=1.15, hair="tonsure", hair_col=(110, 80, 56), headwear="hood_down",
                  head_col=(120, 100, 80), garment="habit", garment_col=(120, 100, 80), footwear="barefoot", prop="cross"),
    "shah": _P("Shah Muhammad II of Khwarazm", skin=(214, 168, 124), build=1.1, hair="short", beard="full2", beard_col=(36, 30, 28), headwear="turban",
               head_col=(246, 244, 236), head_col2=(156, 42, 42), jewel=True, garment="deel", garment_col=(156, 42, 42), garment_col2=(201, 165, 74),
               garment_col3=(63, 107, 74), flags=("pattern", "gold"), tiraz=True, footwear="boots", foot_col=(60, 40, 30), prop="sabre"),
    "governor": _P("Inalchuq, governor of Otrar", skin=(220, 176, 136), hair="braids", hair_col=(40, 32, 28), beard="sparse", headwear="fur_cap",
                   head_col=(63, 107, 74), head_col2=(110, 80, 56), garment="deel", garment_col=(63, 107, 74), garment_col2=(201, 165, 74),
                   garment_col3=(120, 30, 34), tiraz=True, footwear="boots", foot_col=(60, 40, 30), legs=((120, 30, 34), (120, 30, 34)), prop="scroll"),
    "merchant": _P("Muslim caravan merchant", skin=(204, 158, 114), build=1.1, hair="short", beard="full2", beard_col=(40, 32, 28), headwear="turban",
                   head_col=(246, 244, 236), garment="deel", garment_col=(150, 120, 80), garment_col2=(110, 80, 56), garment_col3=(156, 42, 42),
                   cloak="long", cloak_col=(90, 70, 52), cloak_trim=(156, 42, 42), footwear="boots", foot_col=(80, 56, 36), prop="moneybag"),
    "jin_official": _P("Jin official", skin=(232, 196, 156), beard="sparse", beard_col=(30, 26, 24), hair="short", hair_col=(30, 26, 24), headwear="futou",
                       garment="robe_round", garment_col=(142, 35, 35), garment_col3=(31, 27, 24), footwear="boots", foot_col=(31, 27, 24), prop="tablet"),
    "jin": _P("Jin soldier (Jurchen)", skin=(228, 190, 150), hair="jurchen", hair_col=(30, 26, 24), headwear="jin_helmet", garment="lamellar",
              garment_col=(92, 95, 99), garment_col2=(43, 53, 80), garment_col3=(143, 42, 34), hem=2.3, footwear="boots", foot_col=(40, 34, 30),
              legs=((43, 53, 80), (43, 53, 80)), prop="spear_i"),
    "mamluk": _P("Mamluk cavalryman (Ain Jalut, 1260)", skin=(226, 184, 146), hair="braids", hair_col=(40, 32, 28), beard="sparse", headwear="mamluk_helmet",
                 garment="kazaghand", garment_col=(142, 43, 38), garment_col2=(123, 126, 128), garment_col3=(217, 169, 46), sleeves=((142, 43, 38), (123, 126, 128)),
                 footwear="boots", foot_col=(80, 50, 30), legs=((47, 90, 67), (47, 90, 67)), prop="lance_y", shield="round", shield_col=(217, 169, 46)),
    "knight": _P("Knight, Central Europe 1241", skin=(242, 208, 178), hair="short", hair_col=(120, 84, 50), beard="none", headwear="kettle_hat",
                 garment="mail_surcoat", garment_col=(46, 76, 140), garment_col2=(138, 140, 142), garment_col3=(80, 56, 36), hand_col=(138, 140, 142),
                 legs=((138, 140, 142), (138, 140, 142)), footwear="shoes", foot_col=(110, 112, 114), prop="sword", shield="heater",
                 shield_col=(212, 170, 58), shield_charge="eagle"),
    "knight_helm": _P("Knight in a great helm, 1241", skin=(242, 208, 178), headwear="great_helm", garment="mail_surcoat", garment_col=(163, 38, 42),
                      garment_col2=(138, 140, 142), garment_col3=(80, 56, 36), flags=("cross",), hand_col=(138, 140, 142),
                      legs=((138, 140, 142), (138, 140, 142)), footwear="shoes", foot_col=(110, 112, 114), prop="sword", shield="heater",
                      shield_col=(163, 38, 42)),
    "samurai": _P("Samurai in o-yoroi (Kamakura, 1274)", skin=(236, 200, 160), hair="hidden", beard="sparse", beard_col=(30, 26, 24), headwear="kabuto",
                  head_col=(40, 36, 34), head_col2=(163, 36, 42), garment="oyoroi", garment_col=(40, 36, 34), garment_col2=(163, 36, 42),
                  garment_col3=(176, 140, 80), sleeves=((31, 46, 85), (31, 46, 85)), legs=((31, 46, 85), (60, 56, 52)), footwear="boots",
                  foot_col=(90, 64, 44), prop="yumi"),
    "caliph": _P("Caliph al-Musta'sim (Abbasid black)", skin=(204, 156, 112), build=1.1, hair="short", beard="full2", beard_col=(40, 34, 30),
                 headwear="turban_black", garment="deel", garment_col=(24, 24, 26), garment_col2=(60, 60, 62), garment_col3=(60, 60, 62), cloak="long",
                 cloak_col=(40, 40, 44), cloak_trim=(201, 165, 74), footwear="slippers", foot_col=(40, 36, 34), prop="staff"),
    "scholar": _P("Persian scholar / scribe", skin=(212, 166, 122), hair="short", beard="full2", beard_col=(60, 50, 40), headwear="turban",
                  head_col=(246, 244, 236), garment="deel", garment_col=(70, 90, 120), garment_col2=(201, 165, 74), garment_col3=(201, 165, 74), tiraz=True,
                  cloak="long", cloak_col=(200, 190, 160), cloak_trim=(201, 165, 74), footwear="slippers", foot_col=(120, 40, 40), prop="book"),
    "camel": _P("Bactrian camel (loaded)", creature="camel", horse_col=(176, 140, 96), height=1.6),
}
_MW = WORLDS["mongol_1200"]
_MW.update({
    "rider_mounted": _mounted(_MW["rider"], "mongol", horse_col=DUN, mane_col=(60, 44, 32)),
    "rider2_mounted": _mounted(_MW["rider2"], "mongol", horse_col=BAY, mane_col=(30, 24, 22)),
    "archer_mounted": _mounted(_MW["archer"], "mongol", horse_col=CHESTNUT, mane_col=(90, 50, 30), blaze=True),
    "genghis_mounted": _mounted(_MW["genghis"], "mongol", horse_col=WHITE_H, mane_col=(220, 214, 200), gait="walk"),
    "temujin_mounted": _mounted(_MW["temujin"], "mongol", horse_col=BLACK_H, mane_col=(24, 20, 20)),
    "hulagu_mounted": _mounted(_MW["hulagu"], "mongol", horse_col=GREY_H, mane_col=(90, 90, 92), gait="walk"),
    "knight_mounted": _mounted(_MW["knight_helm"], "big", horse_col=GREY_H, mane_col=(70, 70, 72), cloth_col=(163, 38, 42), tack_col=(70, 46, 30)),
    "mamluk_mounted": _mounted(_MW["mamluk"], "big", horse_col=BAY, mane_col=(30, 24, 22), cloth_col=(217, 169, 46), tack_col=(90, 40, 30), blaze=True),
    "samurai_mounted": _mounted(_MW["samurai"], "mongol", horse_col=(70, 50, 40), mane_col=(24, 20, 20), cloth_col=(163, 36, 42)),
    "camel_walk": _P("Bactrian camel (unloaded)", creature="camel", horse_col=(186, 150, 104), height=1.6, load=False),
})

# London c. 1600 (visual bible 04, 1.3-1.4)
EN = (242, 208, 178)
WORLDS["london_1600"] = {
    "queen": _P("Queen Elizabeth I (1600, aged 67)", skin=(248, 238, 230), build=0.9, hair="red_curls", hair_col=(180, 83, 42), blush=True, old=True,
                garment="farthingale", garment_col=(244, 241, 234), garment_col2=(60, 60, 70), garment_col3=(233, 228, 216), neck="rebato", pearls=True,
                sleeves=((244, 241, 234), (244, 241, 234)), arm_w=0.78, footwear="shoes", foot_col=(244, 241, 234), prop="fan"),
    "merchant": _P("London great merchant", skin=EN, build=1.1, hair="short", hair_col=(90, 64, 44), beard="pointed", beard_col=(90, 64, 44),
                   headwear="capotain", garment="doublet", garment_col=(30, 28, 28), garment_col2=(30, 28, 28), garment_col3=(201, 165, 74),
                   flags=("venetians",), neck="ruff", cloak="gown", cloak_col=(36, 32, 32), cloak_trim=(120, 90, 60), chain=True,
                   sleeves=((36, 32, 32), (36, 32, 32)), legs=((30, 28, 28), (40, 38, 38)), footwear="shoes", foot_col=(30, 26, 24)),
    "merchant2": _P("London merchant (elder)", skin=(236, 200, 170), hair="short", hair_col=(150, 146, 140), beard="pointed", beard_col=(160, 156, 150),
                    old=True, headwear="flat_cap", garment="doublet", garment_col=(128, 74, 48), garment_col2=(96, 70, 48), garment_col3=(201, 165, 74),
                    flags=("venetians",), neck="falling_band", cloak="short", cloak_col=(60, 52, 46), cloak_trim=(150, 120, 80),
                    legs=((96, 70, 48), (200, 190, 170)), footwear="shoes", foot_col=(60, 40, 28), prop="scroll"),
    "smythe": _P("Sir Thomas Smythe, first Governor", skin=EN, build=1.15, hair="short", hair_col=(80, 56, 40), beard="pointed", beard_col=(80, 56, 40),
                 headwear="capotain", garment="doublet", garment_col=(30, 28, 28), garment_col2=(30, 28, 28), garment_col3=(201, 165, 74),
                 flags=("venetians",), neck="ruff", cloak="gown", cloak_col=(163, 38, 42), cloak_trim=(120, 90, 60), chain=True,
                 sleeves=((163, 38, 42), (163, 38, 42)), legs=((30, 28, 28), (40, 38, 38)), footwear="shoes", foot_col=(30, 26, 24), prop="charter"),
    "sailor": _P("Sailor", skin=(226, 178, 140), hair="short", hair_col=(110, 74, 44), headwear="monmouth", garment="slops", garment_col=(80, 92, 110),
                 garment_col2=(214, 204, 180), garment_col3=(236, 230, 214), sleeves=((80, 92, 110), (80, 92, 110)), legs=((214, 204, 180), (226, 178, 140)),
                 footwear="barefoot", prop="rope"),
    "shipwright": _P("Shipwright", skin=(232, 190, 156), build=1.1, hair="short", hair_col=(80, 56, 40), beard="pointed", beard_col=(80, 56, 40),
                     headwear="flat_cap", head_col=(70, 58, 50), garment="jerkin", garment_col=(110, 72, 44), garment_col2=(226, 218, 196),
                     garment_col3=(176, 150, 110), sleeves=((226, 218, 196), (226, 218, 196)), legs=((96, 80, 60), (170, 160, 140)), footwear="shoes",
                     foot_col=(60, 40, 28), prop="adze"),
}

# Jahangir's court, Ajmer 1616 (visual bible 04, section 3)
WORLDS["mughal_1616"] = {
    "jahangir": _P("Emperor Jahangir (1616)", skin=(206, 160, 118), build=1.2, hair="short", beard="droop", beard_col=(40, 32, 28), headwear="mughal_turban",
                   head_col=(236, 226, 196), head_col2=(212, 170, 64), jewel=True, garment="jama", garment_col=(206, 166, 80), garment_col2=(236, 214, 150),
                   garment_col3=(168, 35, 58), flags=("pattern", "gold"), cloak="nadiri", cloak_col=(88, 40, 96), cloak_trim=(212, 170, 64), pearls=True,
                   earrings=True, bracelets=True, legs=((168, 35, 58), (168, 35, 58)), footwear="slippers", foot_col=(168, 35, 58), prop="flower"),
    "roe": _P("Sir Thomas Roe, English ambassador", skin=EN, hair="short", hair_col=(90, 60, 40), beard="pointed", beard_col=(90, 60, 40),
              headwear="capotain", garment="doublet", garment_col=(30, 26, 28), garment_col2=(120, 24, 30), garment_col3=(212, 170, 64), neck="falling_band",
              cloak="short", cloak_col=(120, 24, 30), cloak_trim=(212, 170, 64), legs=((120, 24, 30), (226, 214, 190)), footwear="shoes",
              foot_col=(30, 26, 24), flags=("roses",), prop="scroll"),
    "courtier": _P("Mughal courtier", skin=(196, 146, 104), hair="short", beard="full2", beard_col=(30, 26, 24), headwear="mughal_turban",
                   head_col=(246, 244, 236), head_col2=(212, 170, 64), garment="jama", garment_col=(227, 162, 59), garment_col2=(60, 110, 70),
                   garment_col3=(212, 170, 64), legs=((246, 244, 236), (246, 244, 236)), footwear="slippers", foot_col=(120, 40, 40)),
    "courtier2": _P("Mughal courtier (pearl earrings)", skin=(184, 130, 90), hair="short", beard="droop", beard_col=(30, 26, 24), headwear="mughal_turban",
                    head_col=(236, 226, 200), head_col2=(168, 35, 58), jewel=True, garment="jama", garment_col=(231, 185, 176), garment_col2=(140, 40, 60),
                    garment_col3=(212, 170, 64), earrings=True, pearls=True, legs=((141, 178, 85), (141, 178, 85)), footwear="slippers",
                    foot_col=(60, 110, 70)),
    "guard": _P("Mughal palace guard", skin=(170, 116, 78), hair="short", beard="full2", beard_col=(26, 22, 20), headwear="mughal_turban",
                head_col=(240, 236, 226), head_col2=(176, 37, 42), garment="jama", garment_col=(176, 37, 42), garment_col2=(212, 170, 64),
                garment_col3=(120, 24, 30), hem=1.7, legs=((236, 230, 214), (236, 230, 214)), footwear="slippers", foot_col=(120, 30, 30), prop="spear_i",
                shield="round", shield_col=(40, 36, 34)),
    "musician": _P("Court musician", skin=(160, 108, 72), hair="short", beard="droop", beard_col=(26, 22, 20), headwear="bengal_turban",
                   head_col=(180, 40, 60), head_col2=(212, 170, 64), garment="jama", garment_col=(240, 236, 226), garment_col2=(88, 40, 96),
                   garment_col3=(212, 170, 64), legs=((236, 230, 214), (236, 230, 214)), footwear="barefoot", prop="vina"),
    "merchant": _P("Gujarati merchant (Bania)", skin=(184, 132, 92), build=1.1, hair="short", beard="moustache", beard_col=(26, 22, 20),
                   headwear="bengal_turban", head_col=(176, 46, 40), head_col2=(212, 170, 64), tilak=True, garment="jama", garment_col=(246, 244, 236),
                   garment_col2=(236, 230, 214), garment_col3=(176, 46, 40), legs=((246, 244, 236), (246, 244, 236)), footwear="slippers",
                   foot_col=(110, 70, 40), prop="ledger"),
}

# Bengal and the Company army, 1756-65 (visual bible 04, sections 5-7)
RED, GREEN39, BLUE_F, BUFF_ = (178, 42, 42), (92, 138, 74), (34, 52, 96), (214, 186, 132)
WORLDS["bengal_1757"] = {
    "clive": _P("Robert Clive (1757, aged 31)", skin=(236, 196, 166), build=1.12, hair="queue", hair_col=(214, 210, 204), brows_thick=True,
                headwear="tricorne", head_col=(26, 26, 30), head_col2=(212, 170, 64), garment="redcoat", garment_col=RED, garment_col2=BLUE_F,
                garment_col3=(236, 224, 196), flags=("officer",), neck="stock+gorget", cuff_col=BLUE_F, legs=((236, 224, 196), (236, 224, 196)),
                footwear="boots", foot_col=(30, 28, 26), prop="sword"),
    "nawab": _P("Siraj ud-Daulah, Nawab of Bengal (1756)", skin=(200, 150, 108), build=0.92, hair="short", beard="moustache", beard_col=(30, 26, 24),
                headwear="bengal_turban", head_col=(240, 230, 200), head_col2=(212, 170, 64), jewel=True, garment="jama", garment_col=(246, 244, 238),
                garment_col2=(212, 170, 64), garment_col3=(168, 35, 58), hem=3.0, flags=("translucent",), pearls=True, earrings=True, bracelets=True,
                legs=((168, 35, 58), (168, 35, 58)), sleeves=((246, 244, 238), (246, 244, 238)), footwear="slippers", foot_col=(212, 170, 64),
                prop="talwar"),
    "mir_jafar": _P("Mir Jafar (aged c. 65)", skin=(196, 148, 106), build=1.3, hair="short", hair_col=(200, 196, 190), beard="full2",
                    beard_col=(226, 222, 214), old=True, headwear="bengal_turban", head_col=(246, 244, 236), head_col2=(212, 170, 64), jewel=True,
                    garment="jama", garment_col=(246, 244, 238), garment_col2=(31, 122, 82), garment_col3=(212, 170, 64), hem=3.0, flags=("translucent",),
                    cloak="shawl", cloak_col=(217, 154, 58), cloak_trim=(168, 35, 58), pearls=True, legs=((31, 122, 82), (31, 122, 82)),
                    footwear="slippers", foot_col=(120, 40, 40)),
    "jagat_seth": _P("Jagat Seth (banker)", skin=(196, 150, 108), build=1.2, hair="short", beard="moustache", beard_col=(30, 26, 24),
                     headwear="marwari_turban", head_col=(196, 52, 44), head_col2=(236, 190, 60), tilak=True, earrings=True, garment="jama",
                     garment_col=(246, 244, 238), garment_col2=(236, 190, 60), garment_col3=(196, 52, 44), hem=2.9, legs=((246, 244, 238), (246, 244, 238)),
                     footwear="slippers", foot_col=(160, 60, 40), prop="ledger"),
    "shah_alam": _P("Shah Alam II, Mughal emperor (1765)", skin=(200, 152, 110), build=1.1, hair="short", beard="full2", beard_col=(34, 28, 26),
                    headwear="mughal_turban", head_col=(240, 230, 200), head_col2=(212, 170, 64), jewel=True, garment="jama", garment_col=(236, 220, 180),
                    garment_col2=(168, 35, 58), garment_col3=(212, 170, 64), hem=3.0, flags=("pattern", "gold"), cloak="shawl", cloak_col=(217, 154, 58),
                    cloak_trim=(168, 35, 58), pearls=True, legs=((168, 35, 58), (168, 35, 58)), footwear="slippers", foot_col=(212, 170, 64),
                    prop="scroll"),
    "redcoat": _P("Company European soldier (39th Foot pattern)", skin=(232, 184, 150), hair="queue", hair_col=(96, 66, 44), headwear="tricorne",
                  head_col=(26, 26, 30), head_col2=(246, 244, 236), garment="redcoat", garment_col=RED, garment_col2=GREEN39, garment_col3=RED,
                  neck="stock", cuff_col=GREEN39, legs=(RED, (236, 232, 220)), footwear="shoes", foot_col=(30, 28, 28), prop="musket"),
    "csepoy": _P("Company sepoy (1757, INTERPRETATION)", skin=(150, 102, 68), hair="short", beard="moustache", beard_col=(26, 22, 20),
                 headwear="bengal_turban", head_col=(240, 236, 226), head_col2=(240, 236, 226), garment="sepoy", garment_col=RED,
                 garment_col2=(240, 236, 226), garment_col3=BUFF_, legs=((240, 236, 226), (150, 102, 68)), footwear="sandals", foot_col=(120, 84, 48),
                 prop="musket"),
    "sepoy": _P("Nawab's matchlock man", skin=(156, 104, 70), hair="short", beard="full2", beard_col=(26, 22, 20), headwear="mughal_turban",
                head_col=(200, 90, 50), head_col2=(200, 90, 50), garment="jama", garment_col=(226, 214, 186), garment_col2=(140, 40, 40),
                garment_col3=(60, 46, 36), hem=1.5, legs=((226, 214, 186), (226, 214, 186)), footwear="barefoot", prop="matchlock", shield="round",
                shield_col=(60, 46, 36)),
    "weaver": _P("Bengal weaver", skin=(140, 92, 60), build=0.95, hair="short", beard="moustache", beard_col=(26, 22, 20), garment="dhoti",
                 garment_col=(242, 238, 228), legs=((140, 92, 60), (140, 92, 60)), footwear="barefoot", prop="cloth"),
    "boatman": _P("Hooghly boatman", skin=(132, 86, 56), hair="short", headwear="bengal_turban", head_col=(236, 230, 214), head_col2=(236, 230, 214),
                  garment="dhoti", garment_col=(226, 214, 186), hem=1.3, legs=((132, 86, 56), (132, 86, 56)), footwear="barefoot", prop="oar"),
    "officer": _P("Company officer (1757)", skin=(238, 200, 170), hair="queue", hair_col=(214, 210, 204), headwear="tricorne", head_col=(26, 26, 30),
                  head_col2=(212, 170, 64), garment="redcoat", garment_col=RED, garment_col2=BLUE_F, garment_col3=(236, 224, 196), flags=("officer",),
                  neck="stock+gorget", cuff_col=BLUE_F, legs=((236, 224, 196), (40, 36, 34)), footwear="shoes", foot_col=(30, 28, 28), prop="sword"),
}
WORLDS["bengal_1757"]["clive_mounted"] = _mounted(WORLDS["bengal_1757"]["clive"], "big", horse_col=BAY, mane_col=(30, 24, 22),
                                                  cloth_col=(34, 52, 96), gait="walk")
