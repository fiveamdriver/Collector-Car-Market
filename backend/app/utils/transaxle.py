"""
Model-line and variant classification for the transaxle cars (924/944/968/928).

Every auction source imports from this module, so the taxonomy has exactly one
definition.  The previous per-source copies drifted: 968 and 928 had no variant
rules at all and filed every car as "base", and the 924 list matched
"Carrera GT" before "Carrera GTS", swallowing the GTS and GTR cars.

Two product decisions are encoded here:

  * The S-suffix cars (924S, 944S, 928S) fold into the base variant.  The
    frontend labels the base card with the model name, so a 924S shows up
    under "924" rather than a separate "S" card.

  * Competition and non-street cars (924 GTP, 924 Carrera GTR, 944 GTP,
    968 Turbo RS/S, prototypes, clones, race conversions) move to a
    "<line> Race" model line.  They stay queryable in the database but are
    kept out of the street averages, which they otherwise dominate — a
    924 GTP sold for $423,000 against a $8,600 median for a street 924.
"""
import re

# Street model lines handled by this module.
TRANSAXLE_LINES: tuple[str, ...] = ("968", "944", "928", "924")

# A transaxle designation may carry an S suffix and a digit ("924S", "928S4",
# "944S2").  \b alone will not match those, which is why the non-BaT sources
# fell through to their "911" default and filed a 928S as a G-Body 911.
_LINE_RES: tuple[tuple[str, re.Pattern], ...] = (
    ("968", re.compile(r'\b968\b')),
    ("944", re.compile(r'\b944\s?S?\d?\b')),
    ("928", re.compile(r'\b928\s?S?\d?\b')),
    ("924", re.compile(r'\b924\s?S?\b')),
)

# Non-street cars.  "Clone", "Replica" and "Prototype" are not race cars as
# such, but they are not comparable to a factory street sale either, and
# lumping them into the street average is the behaviour we are fixing.
_RACE_RE = re.compile(
    r'\bGTP\b'
    r'|\bGTR\b'
    r'|\bD[-\s]Production\b'
    r'|\bRace\s?car\b'
    r'|\bSCCA\b'
    r'|\bNASA\b'
    r'|\bTrack Car\b'
    r'|\bChallenge\b'
    r'|\bTurbo Cup\b'      # 944 Turbo Cup: one-make race series car, not a street Turbo
    r'|\bPrototype\b'
    r'|\bClone\b'
    r'|\bReplica\b',
    re.IGNORECASE,
)


# A car that only wears the bodywork of a limited model must not claim its
# variant.  Two title conventions, which mean different things:
#
#   "Carrera GT-Style 1982 Porsche 924 Turbo"  → a real 924 Turbo, GT bodywork.
#       The "-Style" token precedes the model year and names what is imitated,
#       so it is stripped before the variant is parsed.
#
#   "Twin-Plug 1970 Porsche 914-6 GT-Style Race Car"  → a real 914-6.
#       Here "-Style" trails the year and describes a genuine car, so nothing
#       is stripped.  The year test below is what separates the two.
#
#   "1986 Porsche 944 Turbo Tribute"  → not a Turbo at all; falls back to base.
#
# Replica / Clone / Prototype are caught earlier by _RACE_RE and never reach here.
_STYLE_PREFIX_RE = re.compile(r'^[^,]*?-Style\b,?\s*', re.IGNORECASE)
_YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
_TRIBUTE_RE = re.compile(
    r'\bTribute\b|\bRe-?creation\b|\bEvocation\b|\bHomage\b',
    re.IGNORECASE,
)


def strip_style_prefix(title: str) -> str:
    """Drop a leading '<model>-Style' prefix that names an imitated car."""
    title = title or ""
    m = _STYLE_PREFIX_RE.match(title)
    if not m:
        return title
    if _YEAR_RE.search(m.group(0)):
        # The prefix swallowed the model year, so "-Style" trails the actual
        # car and is describing it rather than naming an imitation.
        return title
    return title[m.end():]


def is_tribute(title: str) -> bool:
    """True when the lot imitates a model it is not."""
    return bool(_TRIBUTE_RE.search(title or ""))


def match_model_line(text: str) -> str | None:
    """Return the transaxle model line named in `text`, or None."""
    if not text:
        return None
    for line, pattern in _LINE_RES:
        if pattern.search(text):
            return line
    return None


def is_race(model_line: str, title: str) -> bool:
    """
    True when the lot is a competition, prototype, or replica car rather than
    a factory street sale.

    The 968 Turbo RS is the competition car (4 built).  The 968 Turbo S is the
    road-legal homologation car it was derived from (14 built) and stays on the
    street line — though a "Turbo S Prototype" or "Turbo S Clone" still lands
    here via the generic patterns above.
    """
    title = title or ""
    if _RACE_RE.search(title):
        return True
    if model_line == "968" and re.search(r'\bTurbo RS\b', title):
        return True
    return False


def classify_variant(model_line: str, title: str) -> str:
    """
    Return the street variant for a transaxle lot.

    Callers must check is_race() first; this function assumes a street car.
    Returns "base" for the entry-level car, which includes the S-suffix
    models (924S / 944S / 928S) per the folding decision above, and any
    tribute / re-creation that is not the model it imitates.
    """
    if is_tribute(title):
        return "base"
    t = strip_style_prefix(title)

    if model_line == "924":
        # "Carrera GTS" must precede "Carrera GT" — the latter is a prefix of
        # the former and previously matched first.
        if "Carrera GTS" in t:
            return "Carrera GTS"
        if "Carrera GT" in t:
            return "Carrera GT"
        if "Turbo" in t:
            return "Turbo"
        return "base"

    if model_line == "944":
        # \bTurbo S\b, not "Turbo S" as a substring: the latter also matches
        # "Turbo Sunroof" and "Turbo Special".
        if re.search(r'\bTurbo S\b', t):
            return "Turbo S"
        if "Turbo" in t:
            return "Turbo"
        # Bonhams and some BaT titles write the designation unspaced ("944S2"),
        # where \bS2\b cannot match.
        if re.search(r'\bS2\b|944\s?S2\b', t):
            return "S2"
        return "base"

    if model_line == "968":
        # Road-legal homologation special; the competition Turbo RS is routed
        # to the race line before this function is reached.
        if re.search(r'\bTurbo S\b', t):
            return "Turbo S"
        if re.search(r'\bClub\s?Sport\b', t, re.IGNORECASE):
            return "Club Sport"
        return "base"

    if model_line == "928":
        # Club Sport first: a "928 S4 Club Sport" is a Club Sport, not an S4.
        if re.search(r'\bClub\s?Sport\b', t, re.IGNORECASE):
            return "Club Sport"
        if "GTS" in t:
            return "GTS"
        if re.search(r'\bGT\b', t):
            return "GT"
        if re.search(r'\bS4\b|928\s?S4\b', t):
            return "S4"
        return "base"

    return "base"


def classify(model_line: str, title: str) -> tuple[str, str]:
    """
    Return (model_line, variant) for a transaxle lot, routing competition cars
    to the "<line> Race" model line.
    """
    if is_race(model_line, title):
        return f"{model_line} Race", classify_race_variant(model_line, title)
    return model_line, classify_variant(model_line, title)


def classify_race_variant(model_line: str, title: str) -> str:
    """Best-effort designation for a non-street transaxle car."""
    t = strip_style_prefix(title)
    if re.search(r'\bGTP\b', t):
        return "GTP"
    if "Carrera GTR" in t:
        return "Carrera GTR"
    if re.search(r'\bGTR\b', t):
        return "GTR"
    if re.search(r'\bTurbo Cup\b', t, re.IGNORECASE):
        return "Turbo Cup"
    if "Turbo RS" in t:
        return "Turbo RS"
    if re.search(r'\bTurbo S\b', t):
        return "Turbo S"
    if re.search(r'\bClub\s?Sport\b', t, re.IGNORECASE):
        return "Club Sport"
    if re.search(r'\bD[-\s]Production\b', t, re.IGNORECASE):
        return "D Production"
    return "Race"
