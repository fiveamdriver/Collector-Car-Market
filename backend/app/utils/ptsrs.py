"""
Parse @ptsrs (PTSRS, Will Lee) Instagram captions into PTS evidence rows.

PTSRS documents factory Paint to Sample cars. Every relevant caption opens
with a fixed sentence:

    Presenting this Paint to Sample Malachite Green Metallic
    (malachitgrünmetallic; 2B5) Porsche 911 (992.1) GT3 RS with Weissach
    Package. Delivered to ...

    Presenting this brand new Paint to Sample Nato Olive (natooliv;
    non-metallic UNI; L6H) Porsche 911 (992.2) GT3, delivered to ...

Each parsed caption says: this colour (name, German name, finish, paint
code) was factory PTS on this exact model / generation / variant. Captions
that are not a Porsche PTS car (events, other brands, "Special Color" cars)
return None — only an explicit "Paint to Sample" opening counts.
"""
import re
from dataclasses import dataclass

_OPEN_RE = re.compile(
    # Openings vary ("Presenting this…", "Here is a…", "Congratulations… on his
    # brand new…"); the tier word, a colour with its code in brackets and then a
    # model are what make it a car.
    r'\b(?P<tier>Paint\s+to\s+Sample(?:\s+Plus)?|PTS(?:\s+Plus)?)\s+'
    r'(?P<colour>[^()]{2,60}?)\s*'
    r'\((?P<paren>[^()]{2,120})\)\s*',
    re.IGNORECASE)
# The sentence ends at a period followed by whitespace — not the one in "992.1".
_SENTENCE_END_RE = re.compile(r'\.(?:\s|$)|\n')
_OVER_RE = re.compile(r'^over\s+(?P<interior>.+?)\s+(?=(?:19|20)\d{2}\s+Porsche\b|Porsche\b)', re.IGNORECASE)
_MY_RE = re.compile(r'^(?P<my>(?:19|20)\d{2})\s+')
_PORSCHE_RE = re.compile(r'^Porsche\s+(?P<model>.+)$', re.IGNORECASE)
_GEN_RE = re.compile(r'\((?P<gen>[^()]{2,20})\)')
_CODE_RE = re.compile(r'^[A-Z0-9]{2,4}$')
# "1YH, formerly 114": today's PTS code, then the colour's original code.
_CODE_FORMERLY_RE = re.compile(r'^(?P<code>[A-Z0-9]{2,4}),?\s+formerly\s+(?P<former>[A-Z0-9]{2,4})$', re.IGNORECASE)
# Older captions (2016–2022) skip "Porsche 911 (992)": "PTS Gulf Blue (...) 992 GT3".
_SHORT_MODEL_RE = re.compile(
    r'^(?P<gen>99[1-7](?:\.[12])?|964|930|718|981|982|987(?:\.[12])?|986)\s+(?P<variant>.+)$')
_SHORT_MODEL_LINE = {"718": "718", "981": "718", "982": "718", "986": "Boxster",
                     "987": "Boxster", "987.1": "Boxster", "987.2": "Boxster"}
# A whole item that is only a finish ("non-metallic UNI", "metallic"), not a
# German colour name that ends in "metallic" ("malachitgrünmetallic").
_FINISH_RE = re.compile(r'^(?:(?:non-)?metallic|uni|pearl(?:escent)?|matte?|satin|chromaflair|special|colou?r)'
                        r'(?:[\s-]+(?:(?:non-)?metallic|uni|pearl(?:escent)?|matte?|satin|chromaflair|special|colou?r))*$',
                        re.IGNORECASE)
# Where the variant name ends: "with Weissach Package", ", delivered to", "."
_VARIANT_END_RE = re.compile(
    r'\s+(?:with|in|delivered|that|which|from|for|at|on|shared|captured|spotted|seen|presented|'
    r'photographed|owned|ordered|built|has|is|was|and)\b|[,;:]', re.IGNORECASE)


@dataclass(frozen=True)
class PtsEvidence:
    tier: str               # "Paint to Sample" or "Paint to Sample Plus"
    colour: str             # English name as PTSRS writes it
    german_name: str | None
    finish: str | None      # e.g. "non-metallic UNI"
    paint_code: str | None
    model_year: int | None
    model: str              # e.g. "911", "718 Cayman"
    generation: str | None  # e.g. "992.1"
    variant: str | None     # e.g. "GT3 RS"
    extra: str | None       # e.g. "with Weissach Package"
    interior: str | None = None  # "over Ascot Brown"
    former_code: str | None = None  # "1YH, formerly 114" -> 114"


def parse_caption(caption: str | None) -> PtsEvidence | None:
    if not caption:
        return None
    m = _OPEN_RE.search(caption)
    if not m:
        return None
    parts = [p.strip() for p in m.group("paren").split(";") if p.strip()]
    german = (parts[0] if parts and not _CODE_RE.match(parts[0]) and not _CODE_FORMERLY_RE.match(parts[0])
              and not _FINISH_RE.search(parts[0]) else None)
    code = former = None
    if parts:
        fm = _CODE_FORMERLY_RE.match(parts[-1])
        if fm:
            code, former = fm.group("code").upper(), fm.group("former").upper()
        elif _CODE_RE.match(parts[-1]):
            code = parts[-1]
    finish = next((p for p in parts[:-1] if _FINISH_RE.search(p)), None)

    tail = caption[m.end():m.end() + 220]
    end = _SENTENCE_END_RE.search(tail)
    rest = (tail[:end.start()] if end else tail).strip()
    interior = None
    om = _OVER_RE.match(rest)  # "over Ascot Brown 2005 Porsche Carrera GT"
    if om:
        interior, rest = om.group("interior").strip(), rest[om.end():]
    my = None
    mm = _MY_RE.match(rest)
    if mm:
        my, rest = int(mm.group("my")), rest[mm.end():]
    pm = _PORSCHE_RE.match(rest)
    sm = None if pm else _SHORT_MODEL_RE.match(rest)
    if not pm and not sm:
        return None  # not a Porsche (PTSRS also posts Porsche colours on other brands)
    if sm:  # "992 GT3 with Touring Package": generation first, model implied
        gen = sm.group("gen")
        model_part = f'{_SHORT_MODEL_LINE.get(gen, "911")} ({gen}) {sm.group("variant")}'
    else:
        model_part = pm.group("model")
    gm = _GEN_RE.search(model_part)
    generation = gm.group("gen").strip() if gm else None
    if gm:
        model = model_part[:gm.start()].strip()
        after = model_part[gm.end():].strip()
    else:
        model, after = model_part.strip(), ""
    variant, extra = after or None, None
    if after:
        em = _VARIANT_END_RE.search(after)
        if em:
            variant = after[:em.start()].strip() or None
            tail_ = re.split(r'[,;:]', after[em.start():].strip(" ,;"))[0].strip()
            extra = tail_ if re.match(r'with\b', tail_, re.IGNORECASE) else None  # packages only
    return PtsEvidence(
        tier="Paint to Sample Plus" if re.search(r"plus", m.group("tier"), re.IGNORECASE) else "Paint to Sample",
        colour=m.group("colour").strip(),
        german_name=german, finish=finish, paint_code=code, model_year=my,
        model=model, generation=generation, variant=variant, extra=extra, interior=interior,
        former_code=former)
