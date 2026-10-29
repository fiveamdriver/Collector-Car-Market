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

import re

from app.utils.variants import is_early_carrera_4

_CARRERA_S = re.compile(r"Carrera S\b(?!\s*GTS)", re.IGNORECASE)


def get_911_generation(year: int, title: str = "") -> str:
    """
    Generation for a 911 model year. Pass the lot title where it is at hand: the
    964 launched for MY1989 as the all-wheel-drive Carrera 4 alone, so a 1989
    "Carrera 4" is a 964 even though the rest of 1989 is G-Body.
    """
    if title and is_early_carrera_4(year, title): return "964"
    # The 997 launched for MY2005 (Europe: 2004) and the 996 never had a Carrera S,
    # so a "Carrera S" from 2004-05 is a 997.1 even though the year ladder below
    # still says 996.2. (4S is the 996's — the 997 4S came in 2006 — and a GTS is
    # a later car, so neither matches.)
    if title and year in (2004, 2005) and _CARRERA_S.search(title): return "997.1"
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
