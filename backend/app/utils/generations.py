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

from app.utils.variants import is_early_carrera_4, strip_turbo_impostor

_CARRERA_S = re.compile(r"Carrera S\b(?!\s*GTS)", re.IGNORECASE)

# The 992.2 facelift rolled out model by model, not all at once for MY2025. These
# stayed 992.1 through 2025: the GT3 RS (no 992.2 RS has been delivered yet), the
# Turbo / Turbo S (992.2 Turbo S launched as a 2026 model; the 2025 Turbo 50
# Years is a 992.1), and the 992.1-only specials S/T, Dakar and Sport Classic.
_992_1_IN_2025 = re.compile(
    r"\bGT3\s*RS\b|\bTurbo\b|\bS/T\b|\bDakar\b|\bSport Classic\b", re.IGNORECASE
)


def get_911_generation(year: int, title: str = "", vin: str | None = None) -> str:
    """
    Generation for a 911. Decided by MODEL YEAR, per model, in this order:

    1. A valid Porsche VIN (passed in, or written in the title) is the best
       evidence there is: position 10 is the true model year, and the chassis
       code + first serial digit name the chassis family (964 = 96/4xxxxx,
       993 = 99/3xxxxx, 996 = 99/6xxxxx, 997 = 7xxxxx, 991 = 1xxxxx, 992 =
       2xxxxx). European auction houses title cars by production year, a year
       before the model year ("2016 Porsche 911 Turbo S", VIN ...HS... = MY2017
       991.2), so the VIN's year replaces the title's.
    2. A chassis named in the title ("Type 996", "991.2", "(992)").
    3. The model year, with the per-model exceptions in
       _model_specific_generation: Porsche moved each model to the facelift in
       its own model year, not all at once.

    The 964 launched for MY1989 as the Carrera 4 alone, so a 1989 "Carrera 4"
    is a 964 even though the rest of 1989 is G-Body.
    """
    v = _clean_vin(vin) or _clean_vin(_vin_in(title))
    my = _vin_model_year(v, year) if v else None
    if v and my is None:
        v = None  # VIN year contradicts the lot by 2+ years: don't trust the VIN
    y = my or year
    fam = _vin_family(v, y) if v else None
    gen = _named_generation(y, title) if title else None
    if gen is None:
        gen = _ladder_911(y, title)
        if title:
            gen = _model_specific_generation(y, title, gen)
    if fam and _family(gen) != fam:
        gen = _phase_in_family(fam, y, title)
    return gen


# ── Chassis named in the title ───────────────────────────────────────────────
# Auction houses often state the chassis: "2008 Porsche 997 GT2", "1998 Porsche
# 911 Carrera 4 Type 996", "2016 Porsche 911 Carrera S (991.2)". That beats the
# year, which is a registration year as often as a model year on European lots.
# Each code only counts inside the years that chassis was actually sold (plus a
# year's slack for registration), so a "993-style" backdate or a "996 engine"
# swap in an older car is never refiled.
_SUBGEN = re.compile(r"(?<![\d.])(996|997|991|992)\.([12])(?![\d.])")
_CODE = re.compile(
    r"(?:\bType\s+|\bPorsche\s+(?:911\s+)?|\(\s*|\b911\s+)(964|993|996|997|991|992)\b(?![-–\s]*(?:style|look|conversion|engine|motor|body|kit)\b)",
    re.IGNORECASE,
)
_CODE_YEARS = {
    "964": (1988, 1995), "993": (1994, 1999), "996": (1997, 2006),
    "997": (2004, 2013), "991": (2011, 2020), "992": (2018, 2027),
}


def _family(gen: str) -> str:
    return gen.split(".")[0]


def _named_generation(year: int, title: str) -> str | None:
    m = _SUBGEN.search(title)
    if m:
        lo, hi = _CODE_YEARS[m.group(1)]
        if lo <= year <= hi:
            return f"{m.group(1)}.{m.group(2)}"
    m = _CODE.search(title)
    if not m:
        return None
    code = m.group(1)
    lo, hi = _CODE_YEARS[code]
    if not lo <= year <= hi:
        return None
    gen = _model_specific_generation(year, title, _ladder_911(year, title))
    if _family(gen) == code:
        return None  # the ladder already agrees; let it pick .1/.2
    # The ladder disagrees on the chassis: take the named chassis and pick the
    # phase from the nearest end of its run.
    if code in ("964", "993"):
        return code
    first, last = {"996": ("996.1", "996.2"), "997": ("997.1", "997.2"),
                   "991": ("991.1", "991.2"), "992": ("992.1", "992.2")}[code]
    return first if year < (lo + hi) / 2 else last


# ── VIN ───────────────────────────────────────────────────────────────────────
# Verified 2026-11-03 against every 911 row carrying a 17-digit VIN (3,400+):
# chassis code / first serial digit -> family held for 3,370+ rows, and every
# exception was a row already known to be misfiled (Bonhams' "1994 ... Type 993"
# filed as 964s, 2013 997.2 Turbo S filed as 991.1, 2012 991 Carrera S filed as
# 997.2, BaT 2012-porsche-911-carrera-coupe-2 = WP0AA2A96CS706070, a 997.2).
_VIN_RE = re.compile(r"\bWP[0O][A-Z0-9]{14}\b")
_VIN_YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"  # A = 1980/2010, 30-year cycle


def _vin_in(title: str) -> str | None:
    m = _VIN_RE.search(title or "")
    return m.group() if m else None


def _clean_vin(vin: str | None) -> str | None:
    if not vin:
        return None
    v = vin.strip().upper()
    if v.startswith("WPO"):
        v = "WP0" + v[3:]  # auction houses often type the zero as a letter O
    if len(v) != 17 or not v.startswith("WP0") or re.search(r"[IOQ]", v[3:]):
        return None
    return v


def _vin_model_year(v: str, title_year: int) -> int | None:
    """Model year from VIN position 10, if within a year of the lot's year."""
    i = _VIN_YEAR_CODES.find(v[9])
    if i < 0:
        return None
    my = min((1980 + i + k for k in (0, 30, -30)), key=lambda y: abs(y - title_year))
    return my if abs(my - title_year) <= 1 else None


def _vin_family(v: str, my: int) -> str | None:
    code, serial = v[6:8], v[11]
    if code in ("91", "93") and my <= 1989:
        return "G-Body"
    if code == "96" and serial == "4":
        return "964"
    if code == "99" and serial == "3":
        return "993"
    if code == "99" and serial == "6":
        return "996"
    if code in ("99", "A9") and serial == "7" and 2004 <= my <= 2013:
        return "997"
    if code in ("99", "A9") and serial == "1" and 2011 <= my <= 2020:
        return "991"
    if code in ("99", "A9") and serial == "2" and my >= 2019:
        return "992"
    return None


def _phase_in_family(fam: str, year: int, title: str) -> str:
    """The .1/.2 phase of `fam` for this model year (the VIN settled the family)."""
    if fam in ("G-Body", "964", "993"):
        return fam
    gen = _model_specific_generation(year, title, _ladder_911(year, title))
    if _family(gen) == fam:
        return gen
    lo, hi = _CODE_YEARS[fam]
    return f"{fam}.1" if year < (lo + hi) / 2 else f"{fam}.2"


# ── Models that changed generation in a different year to the Carrera ───────
# Dates fact-checked 2026-11-03 (Wikipedia generation pages; Rennlist/Elferspot):
#   997.2 Turbo: Frankfurt Sept 2009, on sale Nov 2009 -> MY2010. A 2009 Turbo is 997.1.
#   997 GT2: on sale Nov 2007, 997.1 only (MY2008-09). There is no 997.2 GT2.
#   997 GT3 / GT3 RS (Porsche Classic, porsche.com/usa/.../classic/models/997/997-gt3/):
#       "911 GT3 (2006-08)", "911 GT3 (2009-12)" -- "From MY 2009" the 3.8 -- so a
#       MY2009 GT3 is 997.2 (the US skipped MY2009); but "911 GT3 RS (2007-2009)",
#       "911 GT3 RS (2010-11)", so a MY2009 GT3 RS is 997.1.
#   991 Turbo / Turbo S: introduced May 2013 -> MY2014; the 997.2 Turbo and
#       Turbo S ran to early 2013. A 2013 Turbo is 997.2.
_TURBO = re.compile(r"\bTurbo\b", re.IGNORECASE)
_GT2 = re.compile(r"\bGT2\b(?!\s*RS)", re.IGNORECASE)
_GT3 = re.compile(r"\bGT3\b", re.IGNORECASE)
_TARGA = re.compile(r"\bTarga\b", re.IGNORECASE)


def _model_specific_generation(year: int, title: str, gen: str) -> str:
    t = strip_turbo_impostor(title)
    if year == 2009 and (_GT2.search(t) or _TURBO.search(t) or _GT3_RS.search(t)):
        return "997.1"
    if year == 2013 and _TURBO.search(t):
        return "997.2"
    # Porsche Classic: "911 Targa 4S (2009-13)"; the 991 Targa arrived for MY2014.
    if year == 2013 and _TARGA.search(t):
        return "997.2"
    # MY2005 and MY2012 each sold two chassis side by side. The rear-drive
    # Carrera / Carrera S (coupe and cabriolet) moved first; the all-wheel-drive
    # cars, Targa, Turbo and GT models followed a year later. Checked against
    # BaT's own 996/997/991 pages: 72 of 72 seen 2005 Carrera coupes sit on its
    # 997 page; 54 of 54 seen 2012 Carrera S coupes and 29 of 31 seen 2012
    # cabriolets on its 991 page (the other two say 6-Speed).
    if year == 2005 and _CARRERA_RWD.search(t) and not _NOT_RWD_CARRERA.search(t):
        return "997.1"
    if year == 2012 and _CARRERA_RWD.search(t) and not (
            _NOT_RWD_CARRERA.search(t) or _SIX_SPEED.search(t) or _BLACK_EDITION.search(t)):
        return "991.1"
    # The 996 GT3 RS (2003-04) was built only on the 996.2; a lot dated earlier
    # (RM's "2001 Porsche 911 GT3 RS") is still that car.
    if gen == "996.1" and _GT3_RS.search(t):
        return "996.2"
    # The 996 Turbo (MY2001-05) and GT2 (MY2001-05) each have ONE card, on
    # 996.2 (user decision 2026-11-03). Porsche Classic lists the Turbo as a
    # single series, "911 Turbo Coupé (2001-05)", launched with the headlights
    # the 996.2 later adopted; the GT2 is carded as one car too.
    if gen == "996.1" and (_TURBO.search(t) or _GT2.search(t)):
        return "996.2"
    # The 964 Speedster was built for MY1994 only; a 1990-91 "Speedster" is a
    # MY1989 G-Body (Carrera 3.2) Speedster titled by its registration year.
    if year in (1990, 1991) and _SPEEDSTER.search(t):
        return "G-Body"
    return gen


_SPEEDSTER = re.compile(r"\bSpeedster\b", re.IGNORECASE)
_GT3_RS = re.compile(r"\bGT3\s*RS\b", re.IGNORECASE)
_CARRERA_RWD = re.compile(r"\bCarrera\b", re.IGNORECASE)
# Anything that makes a "Carrera" title a model that did NOT change over with
# the rear-drive Carrera: 4/4S/C4, GTS, Targa, Turbo, GT cars, specials.
_NOT_RWD_CARRERA = re.compile(
    r"Carrera\s*4|\bC4S?\b|\b4S\b|\bGTS\b|\bTarga\b|\bTurbo\b|\bGT[23]\b|"
    r"Speedster|Sport Classic|40th|Anniversary|\bClub\s*Sport\b",
    re.IGNORECASE,
)
_SIX_SPEED = re.compile(r"\b6-Speed\b|\bsix-speed\b|Tiptronic", re.IGNORECASE)
_BLACK_EDITION = re.compile(r"Black Edition", re.IGNORECASE)


def _ladder_911(year: int, title: str = "") -> str:
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
    if year == 2025 and title and _992_1_IN_2025.search(title): return "992.1"
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
