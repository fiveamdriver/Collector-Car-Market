"""
Model-line matching, shared by every ingest script.

Each script used to carry its own copy of the list and the matcher, and they had
drifted: bonhams_ingest had no "918 Spyder" entry at all, and three scripts were
missing "Macan". Anything unmatched falls through to "911", so a drifted list does
not fail loudly — it quietly files another car as a 911.

Three matching rules earn their keep:

1. **Case-insensitive.** Mecum and Bonhams publish uppercase titles, so a
   substring test against "Panamera" missed "2010 PORSCHE PANAMERA TURBO" and
   filed it as a 911.

2. **Numeric models match on the bare number**, not on a full phrase. The 918s
   arrive titled `918 'Weissach' Spyder`, where the nickname splits the words and
   `\\b918 Spyder\\b` cannot match — eleven seven-figure hypercars sat in the 911
   line because of it. A number can't appear inside a VIN run (no word boundary),
   so the bare match is safe.

3. **Modifier contexts are excluded.** A model name in a title does not always
   name the car being sold:
       "918-Mile 2007 Porsche 911 Turbo"          -> 918 is the mileage
       "911 Turbo S Cabriolet Edition 918 Spyder" -> a 911 trim named after the 918
       "959-Style 1994 Porsche 911 Carrera 4"     -> a tribute, not a 959
       "2001 Porsche 911 Carrera GT Package"      -> an option package on a 911
"""
import re

# Ordered most-specific first; the first match wins. Transaxle cars are resolved
# before this list (see match_model_line) because "924S"/"944S"/"928S4" carry a
# suffix that a word-boundary match cannot see.
PORSCHE_MODEL_LINES = [
    # Matched as the bare number, not "918 Spyder": the cars arrive titled
    # "918 'Weissach' Spyder", with the nickname splitting the two words.
    ("918",        "918 Spyder"),
    ("959",        "959"),
    # Not collector lines, but they must be matched so they don't fall through to
    # the "911" default and pollute it.
    ("Cayenne",    "Cayenne"),
    ("Macan",      "Macan"),
    ("Panamera",   "Panamera"),
    ("Taycan",     "Taycan"),
    ("Boxster",    "Boxster"),
    ("Cayman",     "Cayman"),
    ("968",        "968"),
    ("944",        "944"),
    ("930",        "911"),
    ("928",        "928"),
    ("924",        "924"),
    ("914",        "914"),
    ("912E",       "912"),
    ("912",        "912"),
    ("356",        "356"),
    ("904",        "904"),
    ("962",        "962"),
    ("956",        "956"),
    ("935",        "935"),
    ("934",        "934"),
    ("917",        "917"),
    ("908",        "908"),
    ("907",        "907"),
    ("906",        "906"),
    ("Carrera GT", "Carrera GT"),  # after the numerics; "Carrera GTS" must not match
    ("911",        "911"),
]

# Model lines that are road/race Porsches we track. The rest are matched only to
# keep them out of the 911 bucket.
NON_COLLECTOR_LINES = frozenset({"Cayenne", "Macan", "Panamera", "Taycan"})

# Coachbuilders get their own model line, following the same reasoning as the
# "<line> Race" lines in transaxle.py: the cars stay queryable but are kept out of
# the street averages they would otherwise dominate. A Singer 964 averages $1.3M
# against roughly $86k for a street 964 Carrera, so leaving them in the 964 makes
# that generation's numbers meaningless.
#
# Checked before everything else — these titles all name the donor car too
# ("911 Carrera 2 Coupe by Singer"), and the donor would otherwise win.
COACHBUILT_LINES = (
    (re.compile(r'\bby\s+Singer\b', re.IGNORECASE), "Singer"),
    (re.compile(r'\bGunther\s*Werks\b', re.IGNORECASE), "Gunther Werks"),
    # Emory builds 356 Outlaws, so this one also pulls cars off the 356 line —
    # the titles vary ("by Emory", "'Emory Outlaw'"), hence the bare name.
    (re.compile(r'\bEmory\b', re.IGNORECASE), "Emory"),
)

# A token appearing in one of these contexts is describing the car, not naming it.
_MODIFIER_CONTEXTS = (
    r'{tok}[-\s]?mile',        # "918-Mile 2007 Porsche 911 Turbo"
    r'{tok}[-\s]?kilometer',
    r'{tok}[-\s]?style',       # "959-Style 1994 Porsche 911"
    r'{tok}[-\s]?inspired',
    r'{tok}[-\s]?powered',     # "968-Powered 1987 Porsche 924S" — an engine swap
    r'{tok}\s+package',        # "911 Carrera GT Package"
    r'{tok}\s+tribute',
    r'tribute\s+to\s+(?:the\s+)?{tok}',
    r'edition\s+{tok}',        # "911 Turbo S Cabriolet Edition 918 Spyder"
    r'{tok}\s+spyder\s+edition',
    r'homage\s+to\s+(?:the\s+)?{tok}',
    r'\bDP\s*{tok}',           # "911 Turbo DP 935" — DP is a bodykit tuner
)

# Titles from the auction houses append chassis/engine/VIN numbers, and those
# digits collide with model numbers: "…Coupé Chassis no. 304 449 Engine no.
# 907 672" was matching \b907\b and filing a 911 as a 907. The model is always
# named before this tail, so matching stops here.
_ID_TAIL = re.compile(
    r'\b(?:chassis|engine|body|gearbox|transmission)\s*(?:no\.?|number|#)'
    r'|\bvin\b',
    re.IGNORECASE,
)


def strip_identifier_tail(text: str) -> str:
    m = _ID_TAIL.search(text)
    return text[:m.start()] if m else text


# A three-digit number bound to one of these words is describing the car, not
# naming it: "968-Powered 1987 Porsche 924S" is a 924 with a swapped engine, and
# "918-Mile" is an odometer reading. Removed before matching because the
# transaxle matcher runs ahead of the per-token modifier checks and would
# otherwise claim the number first.
_DESCRIPTIVE_NUMBER = re.compile(
    r'\b\d{3}[-\s]?(?:powered|swapped|style|styled|inspired|look|tribute'
    r'|mile|miles|kilometer|kilometers|km)\b',
    re.IGNORECASE,
)


def scrub_descriptive_numbers(text: str) -> str:
    return _DESCRIPTIVE_NUMBER.sub(' ', text)


def _is_modifier(token: str, text: str) -> bool:
    """True if every occurrence of `token` is descriptive rather than the model."""
    tok = re.escape(token)
    return any(
        re.search(ctx.format(tok=tok), text, re.IGNORECASE)
        for ctx in _MODIFIER_CONTEXTS
    )


def _token_present(token: str, text: str) -> bool:
    if token == "Carrera GT":
        # Word-boundary so "Carrera GTS" doesn't match.
        return re.search(r'\bCarrera GT\b', text, re.IGNORECASE) is not None
    if token[0].isdigit():
        # Bare number: "918 'Weissach' Spyder" has the words split by a nickname.
        # One optional trailing letter catches the racing suffixes — 962C, 917K,
        # 356A. A number inside a VIN still can't match: the surrounding
        # alphanumerics leave no word boundary.
        return re.search(
            r'\b' + re.escape(token) + r'[A-Z]?\b', text, re.IGNORECASE
        ) is not None
    return re.search(re.escape(token), text, re.IGNORECASE) is not None


# 356 and its sub-series. The suffix is often attached ("356A", "356SC"), which a
# word-boundary match can't see, and this has to beat "Carrera GT" because a 356
# Carrera GT is a 356, not the 2003-07 supercar. Requiring 356 to be flanked by
# non-digits keeps it out of chassis and engine numbers.
_RE_356 = re.compile(r'(?<!\d)356(?!\d)')

# The 906 is marketed as the "Carrera 6" / "Carrera Six"; some titles use only that
# name and carry "906" solely in the (stripped) chassis number. The speed guard
# avoids catching a modern "Carrera 6-speed".
_RE_906 = re.compile(r'\bCarrera[\s\-]?(?:6|Six)\b(?!\s*[-–]?\s*speed)', re.IGNORECASE)

# "718" is reused across eras: the 1950s RSK sports-racer, and the modern
# Cayman/Boxster. The modern cars are frequently titled without the words
# "Cayman"/"Boxster" at all — "2021 Porsche 718 Spyder 6-Speed" is a Boxster, and
# without this rule it fell through to the 911 default.
# The 1950s-60s cars are checked first: "1960 Porsche 718 RS 60 Spyder" and
# "1959 Porsche 718 RSK Spyder" both carry "718" and "Spyder", so the modern rule
# below would otherwise claim seven-figure sports-racers as Boxsters. The names
# also appear without "718" at all ("1958 Porsche RSK", "1961 Porsche RS61").
_RE_RSK  = re.compile(r'\bRSK\b', re.IGNORECASE)
_RE_RS60 = re.compile(r'\bRS[-\s]?6[01]\b', re.IGNORECASE)
# ...but the 987 "Boxster RS 60 Spyder" is a modern limited edition named after
# that racer, and it says so. If the title names the Boxster, believe it.
_RE_BOXSTER_WORD = re.compile(r'\bBoxster\b', re.IGNORECASE)

_RE_718_CAYMAN  = re.compile(r'\b718\b.*\bCayman\b', re.IGNORECASE)
_RE_718_BOXSTER = re.compile(r'\b718\b.*\b(?:Boxster|Spyder)\b', re.IGNORECASE)


def match_model_line(text: str, transaxle_matcher=None) -> str:
    """
    Return the Porsche model line named by `text`, defaulting to "911".

    `transaxle_matcher` is app.utils.transaxle.match_model_line, passed in to keep
    this module free of that import cycle; it runs first because suffixed transaxle
    names ("924S") don't survive a word-boundary match.
    """
    text = scrub_descriptive_numbers(strip_identifier_tail(text))

    for pattern, line in COACHBUILT_LINES:
        if pattern.search(text):
            return line

    # These beat the ordered list: each names a model the list would otherwise
    # lose to a later, broader token.
    if _RE_356.search(text):
        return "356"
    if _RE_906.search(text):
        return "906"
    if _RE_RSK.search(text):
        return "718 RSK"
    if _RE_RS60.search(text) and not _RE_BOXSTER_WORD.search(text):
        return "RS60"
    if _RE_718_CAYMAN.search(text):
        return "Cayman"
    if _RE_718_BOXSTER.search(text):
        return "Boxster"

    if transaxle_matcher is not None:
        transaxle = transaxle_matcher(text)
        if transaxle:
            return transaxle

    for token, line in PORSCHE_MODEL_LINES:
        if not _token_present(token, text):
            continue
        if token != "911" and _is_modifier(token, text):
            # Descriptive use — keep looking for the car actually being sold.
            continue
        return line
    return "911"
