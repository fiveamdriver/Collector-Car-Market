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
_WORD_BOUNDED = frozenset({"Carrera T", "Turbo S"})

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
        return re.search(re.escape(pattern) + r'\b', text) is not None
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
