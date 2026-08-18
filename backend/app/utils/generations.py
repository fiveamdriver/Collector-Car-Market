"""
Model-year → generation lookup, shared by every ingest script.

This is the single source of truth for the generation ladders. The same
functions were previously copy-pasted into each ingest script and had begun
to drift (ocd_ingest.py was missing the F-Body/G-Body branches, filing every
pre-1995 911 as a 964).

Every value returned here must exist in the frontend taxonomy
(frontend/src/data/taxonomy.js). Generations rendered as a group — 996, 997,
991, 992 — have no card of their own; the site draws their sub-generations and
sums them for the parent. A bare group name therefore has nowhere to appear, so
these ladders always return the sub-generation. `scripts/preflight-taxonomy.mjs`
checks the database for values that have drifted out of the taxonomy.

Race cars are deliberately excluded from this: the 911 Race line uses flat
generations and keeps its own ladder in data/migrate_race_cars.py.
"""


def get_911_generation(year: int) -> str:
    if year <= 1973: return "F-Body"
    if year <= 1989: return "G-Body"
    if year <= 1994: return "964"
    if year <= 1998: return "993"
    if year <= 2001: return "996.1"
    if year <= 2005: return "996.2"
    if year <= 2008: return "997.1"
    if year <= 2012: return "997.2"
    if year <= 2016: return "991.1"
    if year <= 2019: return "991.2"
    # The 992.2 facelift arrived for the 2025 model year.
    if year <= 2024: return "992.1"
    return "992.2"


def get_cayman_generation(year: int) -> str:
    if year <= 2008: return "987.1"
    if year <= 2012: return "987.2"
    if year <= 2016: return "981"
    return "718"


def get_boxster_generation(year: int) -> str:
    if year <= 2004: return "986"
    if year <= 2008: return "987.1"
    if year <= 2012: return "987.2"
    if year <= 2016: return "981"
    return "718"
