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
_WORD_BOUNDED = frozenset({"Carrera T", "Carrera 4", "Turbo S", "R"})

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
    # Gooding writes the RS as "993 Carrera 3.8 RS"; every pattern expects
    # "Carrera RS", so those cars fell through to plain Carrera. Tributes keep
    # their words and are not rewritten.
    if _CARRERA_38_RS.search(text) and not _RS_38_NOT_FACTORY.search(text):
        text = _CARRERA_38_RS.sub("Carrera RS 3.8", text)
    for pattern in patterns:
        if variant_matches(pattern, text):
            # "Carrera 4 GTS" contains "Carrera 4" but is a GTS, which the site
            # cards as Carrera GTS (as BaT's "997 Carrera 4 GTS" config does).
            if (pattern == "Carrera 4" and "Carrera GTS" in patterns
                    and re.search(r"Carrera\s*4\s*GTS\b", text)):
                return "Carrera GTS"
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
_CARRERA_38_RS = re.compile(r'\bCarrera\s+3\.8\s+RS\b')

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
    named = _RS_38.search(text) or _CARRERA_38_RS.search(text)   # "RS 3.8" or "Carrera 3.8 RS"
    return bool(named) and not _RS_38_NOT_FACTORY.search(text)


# ── 964 Carrera 2 / Carrera 4 ─────────────────────────────────────────────────
# The 964 was sold as the rear-drive Carrera 2 and the all-wheel-drive Carrera 4,
# and the site shows those two cards instead of a generic "Carrera". Titles that
# say neither ("1990 Porsche 911 Carrera Cabriolet 5-Speed") are filed as Carrera
# 2: it is the larger-volume car and the one a title leaves unmarked.
#
# The Carrera 4 came first — the 964 launched for MY1989 as the C4 alone, and the
# C2 followed for 1990. A 1989 "Carrera 4" is therefore a 964, but the year
# ladder files every 1989 car as G-Body; callers use is_early_carrera_4().
# "Carrera 4RS Lightweight" (Bonhams' name for a C4 Leichtbau) is a Carrera 4 too.
_C4 = re.compile(r'\bCarrera\s*4(?:\b|RS\b)|\bC4\b', re.IGNORECASE)
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


# The 964 Turbo is two cars: the 3.3 (MY1991-92, the G-Body engine) and the 3.6
# (MY1993-94: 360 PS, lower, 18" Cup wheels). They have separate cards. Model
# year decides — in the data every 1991-92 Turbo is a 3.3 and every 1993-94 one a
# 3.6; "3.6" in a 3.3's text is the Carrera's engine or "Turbo 3.6" wheels
# (checked 2026-11-05, 151 cars). Turbo S stays its own card.
TURBO_36_FROM_MY = 1993


def split_964_turbo(variant: str, year: int | None) -> str:
    """964 'Turbo' -> 'Turbo 3.3' (MY1991-92) or 'Turbo 3.6' (MY1993+); anything
    else unchanged. Without a year a Turbo stays 'Turbo' (not a card: shows up
    in checks rather than landing on the wrong one)."""
    if variant == "Turbo" and year:
        return "Turbo 3.6" if year >= TURBO_36_FROM_MY else "Turbo 3.3"
    return variant


# The Carrera 4 Leichtbau (22 built at Weissach, 1990-91, Carrera Cup development
# cars; sold $450k-$1M+) has its own card, apart from the ~$110k Carrera 4.
# Bonhams titles one "Carrera 4RS Lightweight". Look-alikes stay on their card.
_C4_LEICHTBAU = re.compile(
    r'\b(?:Carrera\s*4|C4)\s*(?:RS\s*)?[\'"“”‘’]?(?:Lightweight|Leichtbau)\b'
    r'|\b(?:Lightweight|Leichtbau)\s+(?:Carrera\s*4|C4)\b', re.IGNORECASE)
_C4_LEICHTBAU_NOT = re.compile(r'tribute|replica|recreation|evocation|-style|\bstyle\b|conversion', re.IGNORECASE)


def is_964_c4_leichtbau(text: str) -> bool:
    """True if `text` names a factory 964 Carrera 4 Leichtbau."""
    return bool(_C4_LEICHTBAU.search(text or "")) and not _C4_LEICHTBAU_NOT.search(text or "")


def fix_964_carrera(variant: str, text: str, year: int | None = None) -> str:
    """
    Resolve a generic 964 'Carrera' / 'base' (or a mislabelled 'Carrera 2' /
    'Carrera 4') into Carrera 2 or Carrera 4. Variants that are already a
    specific car (RS America, Turbo, Speedster...) pass through untouched; a
    'base' that is really one of them (title says Targa) is promoted to it. A
    'base' whose title names neither drive layout nor a car stays 'base'.
    With `year`, a Turbo is filed on the 3.3 or 3.6 card (split_964_turbo).
    """
    if variant not in ("Carrera", "base", "Carrera 2", "Carrera 4"):
        return split_964_turbo(variant, year)
    if is_964_c4_leichtbau(text):
        return "Carrera 4 Leichtbau"
    if variant == "base":
        for pat, name in _964_SPECIALS:
            if pat.search(text):
                return split_964_turbo(name, year)
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


# The factory G-Body Cabriolet arrived for MY1983; earlier ones are conversions
# and stay on their chassis's card.
_CABRIOLET_FIRST_YEAR = {"G-Body": 1983}


# Same for the Targa, on every water-/air-cooled generation that has a Targa card
# (996.1 has none: the glass-roof 996 Targa is a 996.2). Search configs stamp the
# drivetrain ("Carrera 2", "Carrera 4") on a "Carrera 2 Targa", which filed 75
# Targas on the coupe cards until 2026-11-05. F-/G-Body body styles are decided
# by their own year-based rules.
_TARGA_GENS = {"964", "993", "996.2", "997.1", "997.2", "991.1", "991.2", "992.1", "992.2"}


# A title that says "Turbo S" is the Turbo S, on generations that card it. BaT's
# search groups stamped "Turbo" / "Cabriolet" / "Carrera S" on 77 of them (74
# 2005 996 Turbo S on the Turbo card; 997.2 Turbo S Cabriolets) until 2026-11-05.
# Turbo cabriolets stay with their Turbo card (see _CABRIOLET_SOURCE_TRIMS).
_TURBO_S = re.compile(r"\bTurbo\s+S\b(?![-\s]?(?:style|look|wheels?))", re.IGNORECASE)
_TURBO_S_GENS = {"993", "996.2", "997.2", "991.1", "991.2", "992.1", "992.2"}
_TURBO_S_FROM = {"Turbo", "Cabriolet", "Carrera", "Carrera S", "Carrera 4S", "Targa", "base"}


def cabriolet_variant(generation: str, variant: str, text: str, year: int | None = None) -> str:
    """'Turbo S' / 'Cabriolet' / 'Targa' by what the title names, else `variant` unchanged."""
    if generation in _TURBO_S_GENS and variant in _TURBO_S_FROM and _TURBO_S.search(text or ""):
        return "Turbo S"
    trims = _CABRIOLET_SOURCE_TRIMS.get(generation)
    if (generation in _TARGA_GENS and trims and variant in trims
            and _TARGA_WORD.search(text or "")):
        return "Targa"
    first = _CABRIOLET_FIRST_YEAR.get(generation)
    if first and year is not None and year < first:
        return variant
    if (
        trims
        and variant in trims
        and _CABRIOLET.search(text or "")
        and not _TARGA_WORD.search(text or "")
    ):
        return "Cabriolet"
    return fold_merged_card(generation, variant, text)


# ── Merged cards ──────────────────────────────────────────────────────────────
# The 992.1 has no Carrera 4 card (owner, 2026-11-12): its coupes sit on the
# Carrera card. Search configs stamp "Carrera 4" on Carrera 4S lots too (id
# 30358), so a title that says 4S goes to the Carrera 4S card instead.
def fold_merged_card(generation: str, variant: str, text: str) -> str:
    """`variant` re-filed onto the card that holds it, where a card was merged away."""
    if generation == "992.1" and variant == "Carrera 4":
        return "Carrera 4S" if _B_4S.search(text or "") else "Carrera"
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


# ── Early G-Body Carrera (1974–1977) ─────────────────────────────────────────
#
# Three different cars share the "Carrera" name in these years:
#   * Carrera 2.7 (MY1974–75): RoW cars with the RS 2.7 MFI engine (their own
#     "Carrera 2.7 MFI" card), US cars with a K-Jetronic 2.7.
#   * Carrera RS 3.0 (1974–75): the homologation RS. Titles say "Carrera RS 3.0"
#     or "Carrera 3.0 RS".
#   * Carrera 3.0 (MY1976–77): RoW-only 3.0 (930/02 engine). The US "Turbo
#     Carrera" of 1976 is the 930 and is handled before this function.
_RS_30_RE = re.compile(r'\bCarrera\s+(?:RS\s+3\.0|3\.0\s+RS)\b', re.IGNORECASE)


def early_carrera_variant(text: str, year: int | None) -> str:
    """Variant for a G-Body "Carrera" title of model year 1977 or earlier."""
    if _RS_30_RE.search(text or ""):
        return "Carrera RS 3.0"
    # The model year decides: a 1974–75 chassis with a 3.0 engine (an IROC
    # recreation, an engine swap) is still a Carrera 2.7 underneath.
    if year in (1976, 1977) or (year is None and re.search(r'\bCarrera\s+3\.0\b', text or "", re.IGNORECASE)):
        return "Carrera 3.0"
    return "Carrera 2.7"


# ── G-Body 911 (MY1974–1989) ──────────────────────────────────────────────────
#
# One classifier for every ingest script (each used to carry its own copy).
# Matching is case-insensitive on whole words: several houses write titles in
# capitals, and "SC" found inside "PORSCHE" filed 1974–75 Carreras as SCs.
# Factory model years gate each card, so a conversion lands on its chassis's
# card (a 1984 "Speedster Conversion" is a Carrera 3.2).
def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text or "", re.IGNORECASE) is not None


def gbody_variant(text: str, year: int | None, targa_card: bool = True) -> str:
    y = year or 0
    # Bonhams runs the VIN label into the title: "CARRERA SPEEDSTERVIN. WP0..."
    text = re.sub(r'VIN\.', ' VIN.', text or "")
    # A title that names the SC is an SC chassis, whatever else it says: an
    # aftermarket "Turbocharged 911SC ... Slant Nose", or an SC whose stored model
    # year is off by one.
    names_sc = _has(r'\b(?:911\s*)?SC\b(?!CA)', text) and 1977 <= y <= 1984
    # The 1984 SC RS homologation car (20 built) has its own card.
    if _has(r'\bSC\s*/?\s*RS\b', text) and 1983 <= y <= 1985:
        return "SC RS"
    if _has(r'\bSpeedster\b', text) and y >= 1988:
        return "Speedster"
    # The 930 (incl. its factory Targa / Cabriolet and Flachbau) keeps its cards.
    if not names_sc:
        # The factory Flachbau was a Turbo programme: a Carrera with a converted
        # nose stays on its own card.
        if (_has(r'\bslant[-\s]?nose\b|\bflat[-\s]?nose\b|\bflachbau\b', text) and y >= 1981
                and _has(r'\bTurbo\b(?![-\s]?(?:powered|look|style))|\b930S?\b(?!/)', text)):
            return "Turbo 3.3 Slant Nose"
        # Not an engine swap ("993 Turbo-Powered") or the M491 "Turbo-Look" body.
        # "930/02" is the Carrera 3.0's engine type, not a 930.
        if (_has(r'\bTurbo\b(?![-\s]?(?:powered|look|style))|\b930\b(?!/)', text)
                and not _has(r'\bturbo[-\s]?(?:powered|look|style)\b', text) and y >= 1975):
            return "930 Turbo"
    # Every other Targa is on the Targa card, whatever its engine (2.7, Carrera
    # 2.7 / 3.0, SC, 3.2). Cabriolets: cabriolet_variant, from MY1983.
    if targa_card and _has(r'\bTarga\b', text):
        return "Targa"
    if names_sc and not _has(r'\bCarrera\s+3\.2\b', text):
        return "SC"
    if _has(r'\bMFI\b', text) and y <= 1976:
        return "Carrera 2.7 MFI"
    if _has(r'\bCarrera\s+2\.7\b', text) and y <= 1976:
        return "Carrera 2.7"
    if _RS_30_RE.search(text) or (_has(r'\bCarrera\s+RS\b', text) and y <= 1975):
        return "Carrera RS 3.0"
    # The 1987–89 Carrera 3.2 Club Sport has its own card; a "Clubsport-style"
    # or tribute car stays a Carrera 3.2.
    if (_has(r'\bclub\s?sport\b', text) and 1987 <= y <= 1989
            and not _has(r'club\s?sport[-\s]?(?:style|spec)|tribute|replica|clone|evocation', text)):
        return "Carrera 3.2 Club Sport"
    if _has(r'\bCarrera\b', text) and y <= 1977:
        return early_carrera_variant(text, year)
    if _has(r'\b(?:911\s*)?SC\b(?!CA)', text) and 1978 <= y <= 1983:
        return "SC"
    if _has(r'\bCarrera\s+3\.2\b', text) or (_has(r'\bCarrera\b', text) and y >= 1984):
        return "Carrera 3.2"
    if _has(r'\b911\s*(?:2\.\d\s*)?S\b', text) and y <= 1977:
        return "911S"
    # Plain "911" titles: the model year says which car it is.
    if 1978 <= y <= 1983:
        return "SC"
    if y >= 1984:
        return "Carrera 3.2"
    return "911"


# Porsche Classic's "911 Turbo Classic Series 'Project Gold'" (one car, built
# 2018, sold by RM at the Porsche Experience Center 2018) is a new-build 993
# Turbo with the 450 hp WLS power kit of the period Turbo S. Its model year says
# 991.2, so every ingest would file it there; owner decision 2026-11-10: the
# 993 Turbo S card.
_PROJECT_GOLD = re.compile(r"\bProject\s+Gold\b|\bTurbo\s+Classic\s+Series\b", re.IGNORECASE)


def is_project_gold(text: str) -> bool:
    return bool(_PROJECT_GOLD.search(text or ""))
