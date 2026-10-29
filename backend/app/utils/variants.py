"""
Variant-name matching, shared by every ingest script.

Variant lists are scanned longest-match-first against the raw lot title, which
works for almost every name. It breaks when one variant name is a prefix of an
unrelated word: "Carrera T" is a prefix of both "Carrera Targa" (a different
variant entirely) and "Carrera Type 996" (an auction-house phrasing), so a plain
substring test files those lots as Carrera Ts.

Ordering fixes the Targa case — list "Targa" first and it wins — but nothing in
the list can rescue "Carrera Type", so the genuinely ambiguous names are matched
on a word boundary instead.
"""
import re

# Variant names that are a prefix of a longer, unrelated word and therefore must
# not match mid-word. Keep this as small as possible: a word-boundary match also
# rejects legitimate run-together forms, so only add names that actually collide.
#   "Carrera T" -> "Carrera Targa", "Carrera Type 996"
#   "Turbo S"   -> "Turbo Study" (a Singer commission, not a Turbo S)
#   "R"         -> the 991 R. A single letter matches inside almost anything, so
#                  it is only ever correct bounded on both sides: "RS", "RSR",
#                  "RUF" and "RoW" must not become the 991 R.
_WORD_BOUNDED = frozenset({"Carrera T", "Turbo S", "R"})

# Coachbuilt cars are identified by their builder, not by the donor car's trim.
# They have to be tested before the trim list, because a title like "911 Carrera 2
# Coupe by Singer" matches "Carrera" long before it reaches "Singer" — which filed
# 25 seven-figure restomods under the Carrera, Targa and Turbo cards, inflating
# every one of those averages.
_COACHBUILT = (
    (re.compile(r'\bby Singer\b', re.IGNORECASE), "Singer"),
)


def variant_matches(pattern: str, text: str) -> bool:
    """True if `pattern` names a variant present in `text`."""
    if pattern in _WORD_BOUNDED:
        return re.search(r'\b' + re.escape(pattern) + r'\b', text) is not None
    return pattern in text


def coachbuilder_variant(text: str) -> str | None:
    """Return the coachbuilder's variant name for `text`, or None if it isn't one."""
    for pattern, name in _COACHBUILT:
        if pattern.search(text):
            return name
    return None


def match_variant(patterns, text: str, default: str = "base") -> str:
    """Return the first variant in `patterns` that `text` matches, else `default`."""
    coachbuilt = coachbuilder_variant(text)
    if coachbuilt:
        return coachbuilt
    for pattern in patterns:
        if variant_matches(pattern, text):
            return pattern
    return default


# The 964 Carrera RS 3.8 is its own card in the taxonomy, separate from the 964
# Carrera RS (3.6). Nothing in the variant lists can separate them: "Carrera RS
# 3.8" matches "Carrera RS" long before the displacement is read, so every RS 3.8
# lands on the plain RS card and drags a seven-figure sale into a card that
# averages a fraction of it. migrate_964_38.py cleans this up after the fact; the
# rule below stops the ingests from reintroducing it.
#
# 964 only. The 993 Carrera RS *is* the 3.8, and its titles say so — applying
# this to the 993 would empty its RS card into a variant that generation's
# taxonomy does not have.
#
# "RSR 3.8" does not match: the pattern needs "RS" followed by a space, and the
# competition cars are routed to 911 Race / RSR 3.8 by migrate_race_cleanup.py.
_RS_38 = re.compile(r'\bRS 3\.8')

# Swaps, backdates and tributes carry the same "RS 3.8" text without being one of
# the ~55 factory cars. Kept in sync with migrate_964_38.py.
_RS_38_NOT_FACTORY = re.compile(
    r'3\.8L?-Powered|Conversion|Tribute|Recreation|Replica|Evocation|Backdate',
    re.IGNORECASE,
)


# The 2008 Boxster RS 60 Spyder (1,960 built, a 987.1) is its own card, not the
# 2011 Boxster Spyder (987.2) nor the 718 Spyder RS. It is titled "RS 60 Spyder"
# or "RS60 Spyder", which the generic "Spyder" pattern files onto a card that
# does not exist for the 987.1. The historic 1960 RS 60 racer is routed to its
# own model line before variants are parsed, so this only ever sees Boxsters.
_RS_60 = re.compile(r'\bRS\s?60\b', re.IGNORECASE)


def is_boxster_rs60(text: str) -> bool:
    """True if `text` names the 2008 Boxster RS 60 Spyder."""
    return bool(_RS_60.search(text))


def is_964_rs_38(text: str) -> bool:
    """True if `text` names a factory 964 Carrera RS 3.8 (the street car)."""
    return bool(_RS_38.search(text)) and not _RS_38_NOT_FACTORY.search(text)


# ── 964 Carrera 2 / Carrera 4 ─────────────────────────────────────────────────
# The 964 was sold as the rear-drive Carrera 2 and the all-wheel-drive Carrera 4,
# and the site shows those two cards instead of a generic "Carrera". Titles that
# say neither ("1990 Porsche 911 Carrera Cabriolet 5-Speed") are filed as Carrera
# 2: it is the larger-volume car and the one a title leaves unmarked.
#
# The Carrera 4 came first — the 964 launched for MY1989 as the C4 alone, and the
# C2 followed for 1990. A 1989 "Carrera 4" is therefore a 964, but the year
# ladder files every 1989 car as G-Body; callers use is_early_carrera_4().
_C4 = re.compile(r'\bCarrera\s*4\b|\bC4\b', re.IGNORECASE)
_C2 = re.compile(r'\bCarrera\s*2\b|\bC2\b', re.IGNORECASE)
_964_SPECIALS = [
    (re.compile(r'\bAmerica\b', re.IGNORECASE), "RS America"),
    (re.compile(r'\bSpeedster\b', re.IGNORECASE), "Speedster"),
    (re.compile(r'\bTarga\b', re.IGNORECASE), "Targa"),
    (re.compile(r'\bTurbo\s*S\b', re.IGNORECASE), "Turbo S"),
    (re.compile(r'\bTurbo\b', re.IGNORECASE), "Turbo"),
]


def is_early_carrera_4(year: int, text: str) -> bool:
    """True for a 1989 Carrera 4 — a 964, though the year ladder says G-Body."""
    return year == 1989 and bool(_C4.search(text)) and not _C2.search(text)


def fix_964_carrera(variant: str, text: str) -> str:
    """
    Resolve a generic 964 'Carrera' / 'base' (or a mislabelled 'Carrera 2' /
    'Carrera 4') into Carrera 2 or Carrera 4. Variants that are already a
    specific car (RS America, Turbo, Speedster...) pass through untouched; a
    'base' that is really one of them (title says Targa) is promoted to it. A
    'base' whose title names neither drive layout nor a car stays 'base'.
    """
    if variant not in ("Carrera", "base", "Carrera 2", "Carrera 4"):
        return variant
    if variant == "base":
        for pat, name in _964_SPECIALS:
            if pat.search(text):
                return name
    has4, has2 = bool(_C4.search(text)), bool(_C2.search(text))
    if has4 and not has2:
        return "Carrera 4"
    if variant == "base" and not has2:
        return "base"  # no drive marker and no named car: too thin to call
    return "Carrera 2"


# ── "Turbo" the word vs. Turbo the car ────────────────────────────────────────
# A Carrera 3.2 with the factory M491 "Turbo-Look" package, a 911SC with a turbo
# engine swap, a 964 Carrera 2 "Turbo Look": each says "Turbo" in its title and
# none is a Turbo. The variant matchers read the word and filed them on the 930 /
# 964 / 993 Turbo cards, averaging $60-90k cars into a card of $150k+ ones. The
# phrases below are removed before a title is classified. The title itself is
# never altered — M491 and "Turbo-Look" stay in the displayed name, where
# enthusiasts look for them.
#
# Deliberately narrow: "Turbo Special Wishes" (a real Turbo) and "3.3 Turbo
# Coupe" (a real 1981 Turbo, no "L") must survive.
_TURBO_IMPOSTOR = re.compile(
    r"Turbo[- ]?Looks?|Turbo[- ]?Bodied|Turbo[- ]?Style|\bM491\b|"
    r"(?:Twin[- ]?)?Turbocharged|"
    r"Twin[- ]Turbo[- ]?Powered|Turbo(?:\s+3\.\dL?)?\s*[-\u2013]\s*Powered|930[- ]Powered|"
    r"\d\.\dL\s+Turbo",
    re.IGNORECASE,
)


def strip_turbo_impostor(text: str) -> str:
    """`text` with the phrases that borrow the word Turbo removed, for classifying."""
    return _TURBO_IMPOSTOR.sub(" ", text or "")


# ── Lots that are not cars ────────────────────────────────────────────────────
# Auction houses sell engines, transaxles, seats, body kits and memorabilia next
# to the cars, and a "1974 Porsche 911 Carrera Type 911/83 2.7L MFI Engine"
# parses as a 1974 Carrera MFI: a $40k "car" on the Carrera 2.7 MFI card. These
# go to model line 'Other', which no page shows.
#
# Anchored to the END of the title: auction titles for real cars routinely carry
# "Engine no. 6631129" mid-string, and "Engine" must not match there. Titles that
# end "...& Spare 914/6 Engine" or "Project and M64 Engine" are cars sold with a
# spare engine, so they are excluded.
_NOT_A_CAR = re.compile(
    r"(?:\bEngine(?:\s+Project)?|Engine\s*(?:&|and)\s*(?:915/\d+\s+)?(?:\d-Speed\s+)?Transaxle|"
    r"Flat-Six Engine|\bTransaxle|\bGearbox|Body\s*kit|Training Chassis|Turbo Chassis)\s*$|"
    r"^Seats for\b|\bDashboard for\b|Tool\s?Kit|Owner[\u2019']?s Manual|Manual Collection|"
    r"Promotional Kit|Media Pack|Pinball Machine",
    re.IGNORECASE,
)
_CAR_WITH_SPARE = re.compile(r"Spare\s+\S+\s+Engine|Project\s+and\s+\S+\s+Engine", re.IGNORECASE)


def is_not_a_car(title: str) -> bool:
    """True for engines, parts, memorabilia and other lots that are not a car."""
    t = title or ""
    return bool(_NOT_A_CAR.search(t)) and not _CAR_WITH_SPARE.search(t)


# ── Cabriolet ─────────────────────────────────────────────────────────────────
# Each 911 generation has one Cabriolet card, merging rear- and all-wheel-drive
# (and the S / 4S trims). Cabriolets trade far below the coupes on the air-cooled
# cars — roughly half on a 964 or 993 — so leaving them inside the Carrera 2 /
# Carrera 4 averages made both numbers misleading. The Targa already has its own
# card for the same reason.
#
# Only the Carrera-family trims move. Turbo, Speedster and the GT cars keep their
# own cards: a Turbo Cabriolet is a rare outlier (993 Turbo cabs average ~$880k
# against ~$230k for coupes) and would wreck the merged average.
_CABRIOLET = re.compile(r"Cabriolet|Convertible|\bCabrio\b|\bCab\b", re.IGNORECASE)
_TARGA_WORD = re.compile(r"Targa", re.IGNORECASE)
_CABRIOLET_SOURCE_TRIMS = {
    "G-Body": {"Carrera 3.2", "SC"},
    "964": {"Carrera 2", "Carrera 4"},
}
for _gen in ("993", "996.1", "996.2", "997.1", "997.2", "991.1", "991.2", "992.1", "992.2"):
    _CABRIOLET_SOURCE_TRIMS[_gen] = {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S"}


def cabriolet_variant(generation: str, variant: str, text: str) -> str:
    """'Cabriolet' for a Carrera-family cabriolet, else `variant` unchanged."""
    trims = _CABRIOLET_SOURCE_TRIMS.get(generation)
    if (
        trims
        and variant in trims
        and _CABRIOLET.search(text or "")
        and not _TARGA_WORD.search(text or "")
    ):
        return "Cabriolet"
    return variant


# ── The 'base' bucket ─────────────────────────────────────────────────────────
# A title that names no variant used to be filed as 'base', a variant no card
# shows, so those sales vanished (~300 of them). The rules below follow how the
# cars were actually named:
#   * 964: the rear-drive car is the Carrera 2, so plain -> Carrera 2.
#   * 993 and later: the rear-drive car is simply "Carrera".
#   * body style wins where the card exists: Targa, Cabriolet, Speedster.
#   * a Turbo / Turbo S / GTS in the title is that car, not a plain Carrera.
# For 356 the 'base' fallback is Coupe, the commonest body style.
_BASE_GENS = {"964", "993", "996.1", "996.2", "997.1", "997.2", "991.1", "991.2", "992.1", "992.2"}
_B_TARGA = re.compile(r"Targa", re.I)
_B_SPEEDSTER = re.compile(r"Speedster", re.I)
_B_TURBO_S = re.compile(r"Turbo\s*S\b", re.I)
_B_TURBO = re.compile(r"Turbo", re.I)
_B_GTS = re.compile(r"\bGTS\b", re.I)
_B_4S = re.compile(r"Carrera\s*4\s*S\b|\bC4S\b", re.I)
_B_C4 = re.compile(r"Carrera\s*4\b|\bC4\b", re.I)
_B_CARRERA_S = re.compile(r"Carrera\s*S\b|\b911\s+S\b", re.I)


def resolve_911_base(generation: str, text: str) -> str:
    """A 911 'base' resolved to the card its title points at; 'base' if not a 911 gen we card."""
    if generation not in _BASE_GENS:
        return "base"
    t = (text or "").replace("Carerra", "Carrera")
    if _B_TARGA.search(t):
        return "Targa"
    if _B_SPEEDSTER.search(t):
        return "Speedster"
    if _B_TURBO_S.search(t):
        return "Turbo S"
    if _B_TURBO.search(t):
        return "Turbo"
    if _B_GTS.search(t):
        return "Carrera GTS"
    if _CABRIOLET.search(t):
        return "Cabriolet"
    if _B_4S.search(t):
        return "Carrera 4S"
    if _B_C4.search(t):
        return "Carrera 4"
    if _B_CARRERA_S.search(t):
        return "Carrera S"
    return "Carrera 2" if generation == "964" else "Carrera"


_356_RULES = [
    ("Speedster", re.compile(r"Speedster", re.I)),
    ("Roadster", re.compile(r"Roadster", re.I)),
    ("Cabriolet", re.compile(r"Cabriolet|Convertible|Cabrio|Carbiolet|Drophead", re.I)),
    ("Coupe", re.compile(r"Coup[e\u00e9]|Hardtop|Sunroof", re.I)),
    ("Notchback", re.compile(r"Notchback", re.I)),
]


def parse_356_variant(text: str) -> str:
    """356 body style from a title: Speedster, Roadster, Cabriolet, Coupe, Notchback; Coupe if none."""
    for name, pat in _356_RULES:
        if pat.search(text or ""):
            return name
    return "Coupe"
