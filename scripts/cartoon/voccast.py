"""VOC pilot historical cast, drawn with the shared costume kit (people.py / costume.py) in the hosts' style.

Sources: research_notes/voc/02_visual_research.md (clothing by decade and group, weapons by date) and the approved
Stage 4b cast table. Two worlds, so a 1620s company soldier and a 1741 company soldier can never be mixed up:
  voc_1620       Banda / the hook: company merchant, sailors, matchlock soldier (morion, bandolier), Banda islanders
  travancore_1741  Colachel: VOC soldier (tricorne, flintlock, bayonet), young De Lannoy, Nair soldiers, Ramayyan
Import this module once; it registers both worlds in people.WORLDS.
"""
from __future__ import annotations

import people as PP
from people import _P

EU = (238, 204, 174)
EU2 = (228, 186, 150)
TAN = (214, 168, 124)
BANDA = (168, 112, 74)
BANDA2 = (150, 98, 62)
KER = (150, 100, 66)
KER2 = (128, 84, 54)
KER3 = (164, 112, 76)
BLACK = (28, 26, 28)
LINEN = (238, 232, 216)
VOC_BLUE = (44, 62, 104)
MUNDU = (244, 241, 232)
GOLD = (212, 170, 64)
BUFF = (204, 170, 112)

PP.WORLDS["voc_1620"] = {
    "merchant": _P("Company merchant, 1620s (black, millstone ruff, tall hat)", skin=EU, build=1.08, hair="short", hair_col=(96, 66, 42),
                   beard="pointed", beard_col=(96, 66, 42), headwear="capotain", head_col=(26, 24, 26), garment="doublet", garment_col=BLACK,
                   garment_col2=BLACK, garment_col3=GOLD, neck="ruff", cloak="short", cloak_col=(36, 32, 34), cloak_trim=(70, 60, 56),
                   sleeves=(BLACK, BLACK), legs=(BLACK, (40, 38, 40)), footwear="shoes", foot_col=(30, 26, 24), prop="ledger"),
    "sailor": _P("Company sailor, 1620s", skin=TAN, hair="short", hair_col=(120, 82, 46), headwear="monmouth", head_col=(178, 52, 40),
                 garment="slops", garment_col=(112, 84, 58), garment_col2=(222, 212, 186), garment_col3=LINEN,
                 sleeves=(LINEN, LINEN), legs=((222, 212, 186), TAN), footwear="barefoot", prop="rope"),
    "sailor2": _P("Company sailor (older), 1620s", skin=(206, 160, 118), build=1.1, hair="short", hair_col=(80, 62, 48), beard="full2",
                  beard_col=(80, 62, 48), headwear="flat_cap", head_col=(70, 60, 54), garment="slops", garment_col=(58, 76, 108),
                  garment_col2=(170, 164, 150), garment_col3=(214, 206, 186), sleeves=((214, 206, 186), (214, 206, 186)),
                  legs=((170, 164, 150), (206, 160, 118)), footwear="barefoot", prop=""),
    "soldier": _P("Company soldier, 1620s (morion, buff coat, matchlock)", skin=EU2, hair="short", hair_col=(110, 74, 44), beard="moustache",
                  beard_col=(110, 74, 44), headwear="morion", head_col=(176, 180, 184), garment="buffcoat", garment_col=BUFF,
                  garment_col2=(170, 136, 84), garment_col3=(120, 40, 36), sleeves=(BUFF, BUFF), legs=((96, 84, 70), (170, 160, 140)),
                  footwear="boots", foot_col=(70, 50, 34), prop="musket", neck="falling_band"),
    "banda_man": _P("Banda islander, porter", skin=BANDA, hair="short", hair_col=(24, 20, 20), headwear="headband", head_col=(150, 44, 36),
                    garment="dhoti", garment_col=(122, 64, 44), garment_col2=(200, 150, 70), bare_chest=True,
                    legs=(BANDA, BANDA), footwear="barefoot", prop=""),
    "banda_man2": _P("Banda islander, older porter", skin=BANDA2, build=1.05, hair="short", hair_col=(60, 56, 54), beard="sparse",
                     beard_col=(60, 56, 54), old=True, garment="dhoti", garment_col=(70, 84, 62), garment_col2=(200, 150, 70),
                     bare_chest=True, legs=(BANDA2, BANDA2), footwear="barefoot", prop=""),
    "banda_woman": _P("Banda islander woman", skin=(176, 120, 82), hair="bun", hair_col=(24, 20, 20), garment="robe_round", hem=2.2,
                      garment_col=(150, 66, 50), garment_col2=(214, 170, 80), garment_col3=(214, 170, 80), bare_chest=False,
                      footwear="barefoot", prop="", sleeves=((150, 66, 50), (176, 120, 82))),
}

PP.WORLDS["travancore_1741"] = {
    "voc_soldier": _P("Company soldier, 1741 (tricorne, blue coat, flintlock, bayonet)", skin=EU2, hair="queue", hair_col=(110, 78, 50),
                      headwear="tricorne", head_col=(26, 26, 30), head_col2=(240, 236, 226), garment="redcoat", garment_col=VOC_BLUE,
                      garment_col2=(170, 46, 40), garment_col3=VOC_BLUE, neck="stock", cuff_col=(170, 46, 40),
                      legs=((226, 218, 196), (236, 232, 220)), footwear="shoes", foot_col=(30, 28, 28), prop="musket"),
    "voc_soldier2": _P("Company soldier, 1741 (older)", skin=(226, 182, 146), build=1.1, hair="queue", hair_col=(70, 56, 46), beard="moustache",
                       beard_col=(70, 56, 46), headwear="tricorne", head_col=(26, 26, 30), head_col2=(240, 236, 226), garment="redcoat",
                       garment_col=VOC_BLUE, garment_col2=(170, 46, 40), garment_col3=VOC_BLUE, neck="stock", cuff_col=(170, 46, 40),
                       legs=((226, 218, 196), (236, 232, 220)), footwear="shoes", foot_col=(30, 28, 28), prop="musket"),
    "delannoy": _P("Eustachius De Lannoy, a young officer (1741)", skin=(240, 208, 178), hair="queue", hair_col=(150, 108, 66),
                   headwear="tricorne", head_col=(26, 26, 30), head_col2=GOLD, garment="redcoat", garment_col=VOC_BLUE,
                   garment_col2=(236, 224, 196), garment_col3=(236, 224, 196), flags=("officer",), neck="stock+gorget",
                   cuff_col=(236, 224, 196), legs=((236, 224, 196), (40, 36, 34)), footwear="shoes", foot_col=(30, 28, 28), prop="sword"),
    "nair": _P("Nair soldier, Travancore (sword and shield)", skin=KER, hair="kudumi", hair_col=(22, 20, 20), beard="moustache",
               beard_col=(22, 20, 20), garment="dhoti", garment_col=MUNDU, garment_col2=(200, 160, 70), bare_chest=True, hem=0.9,
               legs=(KER, KER), footwear="barefoot", prop="talwar", shield="round", shield_col=(120, 70, 40), shield_charge="boss"),
    "nair2": _P("Nair soldier, Travancore (matchlock)", skin=KER2, build=1.05, hair="kudumi", hair_col=(22, 20, 20), beard="moustache",
                beard_col=(22, 20, 20), garment="dhoti", garment_col=MUNDU, garment_col2=(170, 50, 40), bare_chest=True, hem=0.9,
                legs=(KER2, KER2), footwear="barefoot", prop="matchlock"),
    "nair3": _P("Nair soldier, Travancore (spear)", skin=KER3, hair="kudumi", hair_col=(30, 26, 24), garment="dhoti", garment_col=MUNDU,
                garment_col2=(200, 160, 70), bare_chest=True, hem=0.9, legs=(KER3, KER3), footwear="barefoot", prop="spear"),
    "ramayyan": _P("Ramayyan, Dalawa of Travancore (1741)", skin=(156, 106, 70), build=1.08, hair="kudumi", hair_col=(26, 22, 22),
                   beard="moustache", beard_col=(26, 22, 22), garment="dhoti", garment_col=MUNDU, garment_col2=GOLD, bare_chest=True,
                   cloak="shawl", cloak_col=MUNDU, cloak_trim=GOLD, earrings=True, chain=True, legs=((156, 106, 70), (156, 106, 70)),
                   footwear="barefoot", prop="sword"),
}
