"""
Mileage, exterior color and paint-to-sample extraction from lot detail text.

Every auction house describes a car differently — BaT has a structured
"Listing Details" bullet list, Gooding and Broad Arrow have highlight bullets,
RM, Bonhams and Mecum have prose. Each ingest script used to carry its own
regexes, and they had drifted: RM's missed the British "kilometres", Gooding's
missed "900 Total Miles", and several discarded any reading under 100 miles —
which is exactly the delivery-mileage cars that matter most.

All sources now share these functions. Input is a list of text fragments
(bullets, or prose split into sentences); fragments are checked in order and
the first confident match wins.
"""
import html
import re

from app.utils.color_parser import _COLOR_WORD_RE, _COLORS_LOWER, scan_for_color

KM_PER_MILE = 1.609344

# Upper bound on a plausible odometer reading. Anything above is a misparse
# (a price, a production number, a part number).
_MAX_MILES = 900_000

# ── Text cleanup ──────────────────────────────────────────────────────────────

_SCRIPT_RE = re.compile(r'<(script|style)\b.*?</\1>', re.DOTALL | re.IGNORECASE)
_BLOCK_RE  = re.compile(r'<(?:br|/p|/li|/div|/h\d|/tr)\b[^>]*>', re.IGNORECASE)
_TAG_RE    = re.compile(r'<[^>]+>')
_WS_RE     = re.compile(r'[ \t\r\f\v ]+')
_SENTENCE_RE = re.compile(r'(?<=[.;!?•])\s+|\n+')


def html_to_text(raw: str | None) -> str:
    """Strip markup, keeping block boundaries as newlines."""
    if not raw:
        return ""
    text = _SCRIPT_RE.sub(" ", raw)
    text = _BLOCK_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    lines = (_WS_RE.sub(" ", ln).strip() for ln in text.split("\n"))
    return "\n".join(ln for ln in lines if ln)


def split_fragments(text: str | None) -> list[str]:
    """Split stored detail text into bullet/sentence fragments."""
    if not text:
        return []
    return [f.strip(" •-\t") for f in _SENTENCE_RE.split(text) if f and f.strip(" •-\t")]


# ── Mileage ───────────────────────────────────────────────────────────────────

# "14k", "14,250", "20.408" (European thousands), "1.5k", "37"
_NUM = r'(\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?)'
_QUALIFIERS = r'(?:(?:actual|original|total|indicated|documented|recorded|genuine|verified|delivery)\s+)*'
_UNIT = r'(miles?|mi\b|kilomet(?:er|re)s?|kms?\b)'

_MILEAGE_RE = re.compile(
    _NUM + r'\s*(k)?[\s-]*' + _QUALIFIERS + _UNIT,
    re.IGNORECASE,
)
# "Odometer reads 12,345" / "odometer shows 8,900 km" — number after the word.
_ODOMETER_RE = re.compile(
    r'\b(?:odometer|odo|speedometer)\b[^.\d]{0,40}?' + _NUM + r'\s*(k)?\s*' + _UNIT,
    re.IGNORECASE,
)

# Context that makes a figure the car's odometer reading: "shows 14k miles",
# "odometer reads ...", "less than 900 miles" before it, or "... miles shown",
# "... from new" straight after it.
_POSITIVE_BEFORE = re.compile(
    r'\b(?:odometer|odo|shows?|showing|reads?|reading|indicates?|indicating|displays?|'
    r'displaying|registers?|registering|under|less than|fewer than|just|only|'
    r'covered|mileage)\W+(?:\w+\W+){0,3}$',
    re.IGNORECASE,
)
_POSITIVE_AFTER = re.compile(
    r'^\W*(?:shown|showing|indicated|from new|since new|on the (?:odometer|clock)|recorded)\b',
    re.IGNORECASE,
)
# Context that makes it something else: a service interval, a race distance
# ("500 Mile Road America", "Nürburgring 1000 KM"), a trip, distance since a rebuild.
_NEGATIVE = re.compile(
    r'\b(?:service|serviced|interval|ago|since (?:\w+ ){0,2}(?:restoration|rebuild|refresh|'
    r'overhaul|purchase|acquisition|completion|service|work)|since (?:then|\d{4})|'
    # distance over a period: "stored for the next five years, covering fewer than 100 miles"
    r'covering|for the (?:next|following)|in the (?:past|last)|over the (?:past|last|next)|'
    r'annually|a year|each year|added|races?|raced|racing|rally|'
    r'mille|miglia|road america|n[uü]rburgring|sebring|le mans|daytona|spa|monza|targa florio|'
    r'hours?|class|overall|edition|entered|contested|competed|championship|grand prix|'
    r'tour|trip|away|per|every|warranty|range|top speed|mph|km/h|rebuilt|overhauled)\b',
    re.IGNORECASE,
)
# Clause boundaries: context is judged within the clause holding the figure,
# so "Recent Service by DeMan; Approximately 7,900 Km from New" still counts.
_CLAUSE_END = re.compile(r'[;|]|\.\s')
_UNKNOWN = re.compile(
    r'\b(?:TMU|true mileage unknown|mileage unknown|exempt|not actual|odometer (?:is )?inoperative)\b',
    re.IGNORECASE,
)


def _to_miles(num_str: str, k_suffix: str | None, unit: str | None) -> int | None:
    # European period-as-thousands: "20.408" → 20408; but "1.5k" stays 1.5.
    if '.' in num_str and ',' not in num_str and not k_suffix:
        parts = num_str.split('.')
        if all(len(p) == 3 for p in parts[1:]):
            num_str = num_str.replace('.', '')
    num_str = num_str.replace(',', '')
    try:
        value = float(num_str)
    except ValueError:
        return None
    if k_suffix:
        value *= 1000
    if unit and unit.lower().startswith('k'):
        value /= KM_PER_MILE
    miles = round(value)
    return miles if 0 < miles <= _MAX_MILES else None


def _mileage_in(fragment: str, require_context: bool) -> int | None:
    if _UNKNOWN.search(fragment):
        return None
    m = _ODOMETER_RE.search(fragment)
    if m:
        return _to_miles(m.group(1), m.group(2), m.group(3))
    for m in _MILEAGE_RE.finditer(fragment):
        # Judge context from the clause around the figure, not the whole fragment.
        start = max(0, m.start() - 60)
        before = _CLAUSE_END.split(fragment[start:m.start()])[-1]
        after = _CLAUSE_END.split(fragment[m.end():m.end() + 80])[0]
        # "30,000-mile service", "500 Mile Road America", "since the rebuild".
        # Only the words right after the figure qualify it; further on they
        # usually describe something else ("107,000 miles from new and comes
        # with service history").
        if _NEGATIVE.search(before + m.group(0) + after[:40]):
            continue
        if require_context and not (
            _POSITIVE_BEFORE.search(before)
            or _POSITIVE_AFTER.search(after)
            # "actual"/"total"/"delivery" inside the match itself
            or re.search(r'\b(?:actual|total|original|indicated|delivery)\b', m.group(0), re.I)
        ):
            continue
        return _to_miles(m.group(1), m.group(2), m.group(3))
    return None


def parse_mileage(fragments: list[str], prose: bool = False) -> int | None:
    """
    Odometer reading in miles from detail fragments.

    prose=False is for short structured bullets ("14k Miles Shown", "Less than
    900 Total Miles") where any figure-plus-unit is the odometer. prose=True is
    for narrative text, where a figure only counts when the sentence says it is
    the odometer ("shows", "from new", "odometer reads", ...).
    """
    for frag in fragments:
        if _UNKNOWN.search(frag):
            return None
        miles = _mileage_in(frag, require_context=prose)
        if miles is not None:
            return miles
    return None


def parse_odometer_value(value, units: str | None) -> int | None:
    """Structured odometer field (Mecum, Broad Arrow schema.org). 0 means unrecorded."""
    if value in (None, ""):
        return None
    try:
        num = float(str(value).replace(",", ""))
    except ValueError:
        return None
    if (units or "").upper() in ("K", "KM", "KMT", "KILOMETERS"):
        num /= KM_PER_MILE
    miles = round(num)
    return miles if 0 < miles <= _MAX_MILES else None


# ── Color ─────────────────────────────────────────────────────────────────────

_PTS_RE = re.compile(r'paint[-\s]to[-\s]sample|\bPTS\b|sonderwunsch', re.IGNORECASE)

# Modifiers that precede the color name but aren't part of it.
_COLOR_LEAD = (
    r'(?:(?:a|an|the|its|original|factory|rare|special[-\s]order|non-metallic|'
    r'paint[-\s]to[-\s]sample|pts|correct|period[-\s]correct|factory[-\s]correct|striking|'
    r'stunning|beautiful|attractive|highly|very|desirable|handsome|classic|iconic|vibrant|'
    r'lovely|superb|cool|gorgeous|elegant|timeless|signature|sought[-\s]after|spectacular|'
    r'ultra[-\s]desirable|period[-\s]appropriate|turbo|its original)[\s,]+)*'
)
# (pattern, known_only). known_only patterns are loose enough that only a name
# from the color list is trusted; the others also accept unlisted Title-Case
# colors ("finished in Voodoo Blue").
_COLOR_PATTERNS = [
    # BaT bullet: "Guards Red Paint", "Paint-To-Sample Mint Green Paint",
    # "White Paint w/Black Graphics", "Original Irish Green Paint and Numbers-Matching Engine"
    # Title-Case words only, so prose like "It left the factory wearing Signal
    # Red paint" (the original color, often since changed) doesn't match.
    (re.compile(r'^(?i:' + _COLOR_LEAD + r')([A-Z~#][\w~#/-]*(?:\s+[A-Z~#][\w~#/-]*){0,4}?)'
                r'\s+(?:Metallic\s+)?Paint(?:work)?\b'), False),
    # Mecum spec block: "EXTERIOR COLOR White INTERIOR COLOR Red"
    (re.compile(r'\bEXTERIOR COLOU?R:?\s+(.+?)(?:\s+INTERIOR\b|\s+MAKE\b|$)'), False),
    # "Finished in X over Y", "painted in X", "refinished in X", "wearing X"
    (re.compile(r'\b(?:re)?(?:finished|painted|presented|resprayed|wearing|wears|dressed)\s+in\s+'
                + _COLOR_LEAD + r'(.+?)(?:\s+(?:over|with|and|paint|livery|by)\b|[,;.(]|$)',
                re.IGNORECASE), False),
    # "Paint to Sample Gulf Blue over Ascot Brown"
    (re.compile(r'\bpaint[-\s]to[-\s]sample\s+(.+?)\s+(?:over|with)\b', re.IGNORECASE), False),
    # "Restored by Marque Specialists in Original Black over Black Color Scheme"
    (re.compile(r'\bin\s+' + _COLOR_LEAD + r'([A-Za-z][\w -]{1,40}?)\s+over\b', re.IGNORECASE), False),
    # BaT excerpt: "is a black-over-Cashmere Targa", "Guards Red over black"
    (re.compile(r'(?:^|\b(?:a|an|is|this)\s+)([A-Za-z][A-Za-z -]{1,30}?)[\s-]+over[\s-]+[A-Za-z]',
                re.IGNORECASE), True),
]

# Parts of the car whose color isn't the paint ("Black Leather Upholstery",
# "the soft top was finished in Dark Blue").
_NOT_BODY = (
    r'interior|upholstery|leather|cloth|alcantara|vinyl|carpet|trim|seats?|'
    r'wheels?|calipers?|top|soft[-\s]?top|roof|hood|stripes?|decals?|dash|headliner|'
    r'stitching|piping|belts?|tartan|pasha'
)
_NOT_BODY_RE = re.compile(r'\b(?:' + _NOT_BODY + r')\b', re.IGNORECASE)
# A parenthetical, or the tail of one cut off at the start of a window.
_PAREN_RE = re.compile(r'\([^)]*\)?|^[^(]*\)')
_SUBCLAUSE_RE = re.compile(r'[,;.]|\band\b')


def _about_other_part(lead_in: str) -> bool:
    """
    True when the words just before "finished in X" name another part:
    "the soft top was finished in Dark Blue". Only the current clause counts,
    so "black upholstery, now presented in Ruby Red" and "the car (and its
    Fuchs wheels) had been refinished in Bahia Red" are about the paint.
    """
    clause = _SUBCLAUSE_RE.split(_PAREN_RE.sub("", lead_in))[-1]
    return bool(_NOT_BODY_RE.search(clause))
# A bullet the last-resort scan skips: about another part, or about who built,
# sold or owned it ("engine built by Porsche Specialist Dave Brown", "Offered
# from the Todd Blue Collection" — a collection name, not a paint colour).
_NOT_PAINT = re.compile(
    r'\b(?:' + _NOT_BODY + r'|engine|gearbox|by|specialist|owner|dealer|collection)\b',
    re.IGNORECASE,
)


_COLOR_WORDS = (
    r'(?:Blue|Green|Red|Grey|Gray|Silver|Yellow|White|Black|Brown|Orange|Purple|Violet|'
    r'Gold|Beige|Tan|Teal|Pink|Turquoise|Metallic|Olive|Pearl|Bronze|Ivory|Copper|Cream|'
    r'Crimson|Maroon|Lavender|Champagne|Charcoal|Indigo|Magenta|Coral|Slate|Jade)'
)
# A full color name inside a longer phrase: 1–3 Title-Case words ending in a
# color word ("Oryx White", "Fluid Silver", "Dark Blue Metallic").
_COLOR_NAME_RE = re.compile(r'\b(?:[A-Z][\w-]+ ){0,2}' + _COLOR_WORDS + r'(?: Metallic)?\b')
_LEAD_RE = re.compile(r'^' + _COLOR_LEAD, re.IGNORECASE)


def _normalize_color(phrase: str, known_only: bool = False) -> str | None:
    """
    Turn a captured phrase into a color name, keeping the specific name:
    "Fluid Silver" stays "Fluid Silver", not the generic "Silver" a substring
    lookup would give. Anything that isn't a color ("Targa Florio") is None.
    """
    phrase = _LEAD_RE.sub("", phrase.strip(" -,.")).strip()
    if not phrase or len(phrase) > 100:
        return None
    known = _COLORS_LOWER.get(phrase.lower())
    if known:
        return known
    # Lower-case prose ("a black-over-Cashmere") and loose patterns: list only.
    if known_only or phrase.islower():
        return scan_for_color(phrase)
    if len(phrase) <= 40 and _COLOR_WORD_RE.match(phrase):
        return _trim_to_known(phrase)
    names = [_LEAD_RE.sub("", m.group(0)) for m in _COLOR_NAME_RE.finditer(phrase)]
    names = [n for n in names if n]
    if names:
        return _trim_to_known(max(names, key=len))
    return scan_for_color(phrase)


def _trim_to_known(name: str) -> str:
    """
    "996 Turbo Arctic Silver" → "Arctic Silver": when the name ends in a known
    multi-word color, the words before it are description. A bare known word
    doesn't count — "Fluid Silver" and "Oryx White" are names in their own right.
    """
    words = name.split()
    for i in range(len(words) - 1):
        known = _COLORS_LOWER.get(" ".join(words[i:]).lower())
        if known:
            return known
    return name


def parse_color(fragments: list[str], bullets: bool = False) -> str | None:
    """
    Exterior color from detail fragments.

    Explicit phrasings ("X Paint", "finished in X", "X over Y") win. With
    bullets=True, a bare known color name in a bullet that isn't about the
    interior, wheels or top is accepted as a last resort.
    """
    for pattern, known_only in _COLOR_PATTERNS:
        for frag in fragments:
            m = pattern.search(frag)
            if m and not _about_other_part(frag[max(0, m.start() - 25):m.start()]):
                color = _normalize_color(m.group(1), known_only)
                if color:
                    return color
    if bullets:
        for frag in fragments:
            if len(frag) <= 80 and not _NOT_PAINT.search(frag):
                color = _normalize_color(frag)
                if color:
                    return color
    return None


# ── Paint to sample ──────────────────────────────────────────────────────────
#
# True only for a statement about THIS car's paint. Not counted:
#   * "Sonderwunsch" alone — Porsche's special-wishes programme also built
#     Flat-Nose bodies and special interiors ("Sonderwunsch-Innenraum").
#   * "PTS Porsche Collection" — a BaT dealer.
#   * Prose about the programme: "under its pricey paint-to-sample program".
_PTS_WORD = r'(?:paint[-\s]?to[-\s]?sample(?:\s+plus)?|\bPTS\b\+?)'
_PTS_LINE_RE = re.compile(r'paint[-\s]to[-\s]sample|\bPTS\b(?!\s+Porsche\s+Collection)', re.IGNORECASE)
_PTS_NOT_PAINT = r'(?!\s+(?:program|programme|option|options|palette|list|catalog|offering|selections?|choices?|colou?rs\b))'
_Q = r'[\'"“”‘’]?'
_PTS_PROSE_RES = [re.compile(p, re.IGNORECASE) for p in (
    # "finished in paint-to-sample Fashion Grey", "specified in rare PTS ..."
    r'\b(?:finished|painted|presented|refinished|resprayed|specified|ordered|delivered|wearing|'
    r'wears|wore|dressed|resplendent|done)\s+(?:\w+\s+){0,3}?in\s+(?:a\s+|an\s+|the\s+|its\s+|'
    r'rare\s+|original\s+|factory\s+|period\s+)*' + _Q + _PTS_WORD + _PTS_NOT_PAINT,
    # "Paint to Sample shade of Macadamia", "L999 – Paint-to-sample finish"
    _PTS_WORD + _Q + r'\s+(?:shade|colou?r|hue|finish|paint(?:work)?|code)\b(?!s)' + _PTS_NOT_PAINT,
    # "paint-to-sample Gulf Blue", "now called PTS Alex Grey"
    _PTS_WORD + _Q + r'\s+(?:(?-i:[A-Z])[\w-]+\s+){0,2}(?-i:' + _COLOR_WORDS + r')\b',
    # "this 'Paint-to-Sample' Metallic Night Blue", "a rare, single-owner paint-to-sample RSA"
    r'\b(?:a|an|this|its)\s+(?:[\w,-]+\s+){0,3}?' + _Q + _PTS_WORD + _Q + _PTS_NOT_PAINT + r'\s+\w',
)]
# "special order non-metallic Club Blue", "Custom-Order Metallic Purple",
# "special-order paint": an order for a non-catalogue colour. Not "special
# order Black leather" — that is the interior.
_SPECIAL_ORDER_PAINT_RE = re.compile(
    r'\b(?i:special|custom)[-\s](?i:order)(?i:ed)?\s+(?:(?i:non-)?(?i:metallic)\s+)?'
    r'(?:(?i:paint|colou?r|hue|shade|finish)\b'
    r'|(?:[A-Z][\w-]+\s+){0,2}' + _COLOR_WORDS + r'\b(?!\s+(?i:leather|interior|upholstery|cloth|'
    r'alcantara|vinyl|wheels?|calipers?|top|seats?|stitching|piping|carpet)))')


# "Finished in Paint to Sample <name>" / "finished in PTS <name>": the bullet
# names this car's paint, even when the name itself is unreadable.
_STATED_PTS_PAINT_RE = re.compile(
    r'\b(?:finished|painted|presented|ordered|specified|delivered)\s+in\s+(?:' + _PTS_WORD + r')', re.IGNORECASE)


# Where a colour phrase ends: what follows is no longer its name.
_PHRASE_END_RE = re.compile(r'[,.;:()]|\b(?:over|with|paint|paintwork|exterior|from|in)\b', re.IGNORECASE)


def _special_order_paint(fragment: str) -> bool:
    """A special/custom order for the paint, not for the stitching, stripes,
    wheels or interior ("custom-ordered Guards Red deviated stitching",
    "over special-ordered Petrol Green full leather")."""
    for m in _SPECIAL_ORDER_PAINT_RE.finditer(fragment):
        rest = fragment[m.end():]
        end = _PHRASE_END_RE.search(rest)
        if _NOT_BODY_RE.search(rest[:end.start()] if end else rest):
            continue
        lead = fragment[max(0, m.start() - 40):m.start()]
        if re.search(r'\bover\s*$', lead, re.IGNORECASE) or _about_other_part(lead):
            continue
        return True
    return False


# Not a factory order: a later respray in a PTS colour ("resprayed by the
# selling dealer in Slate Grey Metallic, a paint-to-sample color"; but "repainted
# in its original special-order color" is), a guess ("it would seem that this
# was a non-standard 'paint to sample'"), the colour it wears now ("the car is
# now in Bali Blue - a special order colour"), or a comparison ("a cousin to
# Porsche's own paint-to-sample color").
_PTS_NOT_FACTORY_RE = re.compile(
    r'\b(?:resprayed|repainted|refinished|repaint|respray)\b(?:(?!\boriginal\b)[^.;])*?'
    r'(?:paint[-\s]?to[-\s]?sample|\bPTS\b|special[-\s]order)'
    r'|\bit would seem\b|\bappears to have been\b|\bpossibly\b'
    r'|\bnow\s+(?:in|finished|painted|wears)\b'
    r'|\bcousin\b|\breminiscent\b|\binspired by\b',
    re.IGNORECASE)


def parse_paint_to_sample(fragments: list[str], prose: bool = False) -> bool | None:
    """True when the fragments state this car is paint-to-sample. Prose needs a
    statement about the car's paint; a bullet or title only needs the words."""
    for f in fragments:
        if _PTS_NOT_FACTORY_RE.search(f):
            continue
        if _special_order_paint(f):
            return True
        if prose:
            if any(p.search(f) for p in _PTS_PROSE_RES):
                return True
        elif _PTS_LINE_RE.search(f):
            return True
    return None


# Stored detail text is "<bullets>\n--\n<prose>"; either part may be empty.
PROSE_SEPARATOR = "\n--\n"


def join_details(bullets: list[str] | None, prose: str | None = None) -> str | None:
    """Build the details_text stored on a row from bullets and/or prose."""
    head = "\n".join(b.strip() for b in (bullets or []) if b and b.strip())
    tail = (prose or "").strip()
    if not head and not tail:
        return None
    return head + PROSE_SEPARATOR + tail if tail else head


def extract(text: str | None) -> dict:
    """
    mileage / exterior_color / paint_to_sample from stored detail text.

    Bullets are trusted more than prose: they are checked first, any
    figure-plus-unit in a bullet counts as the odometer, and a bare color name
    in a bullet is accepted. Prose needs explicit phrasing for both.
    """
    head, _, tail = (text or "").partition(PROSE_SEPARATOR)
    bullets = [ln.strip() for ln in head.split("\n") if ln.strip()]
    prose = split_fragments(tail)
    mileage = parse_mileage(bullets) or parse_mileage(prose, prose=True)
    color = parse_color(bullets, bullets=True)
    # A bullet that states the paint ("Finished in Paint to Sample azureblue356")
    # but whose name we can't read: leave the colour empty rather than take one
    # from the prose, which is as likely to be the interior or another car.
    if color is None and not any(_STATED_PTS_PAINT_RE.search(b) for b in bullets):
        color = parse_color(prose)
    return {
        "mileage":         mileage,
        "exterior_color":  color,
        "paint_to_sample": parse_paint_to_sample(bullets) or parse_paint_to_sample(prose, prose=True),
    }
