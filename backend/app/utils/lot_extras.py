"""
Transmission, chassis, interior, options and provenance from a lot's title and
stored detail text (details_text, see app/utils/lot_details.py).

Only the title and the bullet/spec lines are read, never the prose essay: prose
talks about other cars and about the factory ("developed at Weissach", "unlike
the PDK cars, this one..."), while bullets describe this car.

Every parser returns None / [] when the text doesn't say. Unknown is a real
answer: a filter for "manual" must not include cars that were only guessed to
be manual. (Every ingest script used to default transmission to "Manual", which
filed 991 GT3 RS and Turbo S cars — PDK only — as manuals.)
"""
import re

from app.utils.lot_details import _COLOR_WORDS, PROSE_SEPARATOR, parse_paint_to_sample, split_fragments

_N = r'(?:[3-8]|three|four|five|six|seven|eight)'

_PDK_RE = re.compile(r'\bPDK\b|dual[-\s]clutch|doppelkupplung', re.IGNORECASE)
_AUTO_RE = re.compile(
    r'\btiptronic\b|\bsportomatic\b'
    rf'|\b{_N}[-\s]speed\s+(?:\w+\s+)?automatic\b'
    r'|\bautomatic\s+(?:transmission|transaxle|gearbox)\b'
    r'|^automatic$',
    re.IGNORECASE)
# BaT's bullets misspell "transaxle" often enough to match the variants seen.
_MANUAL_RE = re.compile(
    rf'\b{_N}[-\s]speed\s+(?:[\w-]+\s+)?manual\b'
    r'|\bmanual\s*(?:transmission|trans\b|transaxle|transasxle|transale|tansaxle|gearbox)'
    r'|\bG50\b|\bstick[-\s]?shift\b|\bgated\s+shifter\b',
    re.IGNORECASE)
_TITLE_SPEED_RE = re.compile(rf'\b{_N}[-\s]speed\b', re.IGNORECASE)
_BARE_SPEED_RE = re.compile(rf'^{_N}[-\s]speed$', re.IGNORECASE)
# Front-engined transaxle cars were offered with automatics, so a bare
# "4-Speed" is not proof of a manual on them.
_HAD_AUTOMATICS = {"924", "928", "944", "968", "Cayenne", "Panamera", "Macan", "Taycan"}
# Built with one gearbox only.
_MANUAL_ONLY_LINES = {"356", "550", "904", "959", "Carrera GT"}
_PDK_ONLY_LINES = {"918 Spyder", "Taycan"}
FIRST_AUTOMATIC_YEAR = 1968   # Sportomatic
# From MY2009 PDK replaced Tiptronic in these lines (Panamera and Macan were
# PDK from launch), so an "Automatic" there is a PDK. Mecum labels them so.
_PDK_ERA_LINES = {"911", "Boxster", "Cayman", "Panamera", "Macan"}
PDK_ERA_START = 2009


def split_bullets(details_text: str | None) -> list[str]:
    head = (details_text or "").partition(PROSE_SEPARATOR)[0]
    return [ln.strip() for ln in head.split("\n") if ln.strip()]


def _labelled(bullets: list[str], label: str) -> str | None:
    """Mecum spec block: a label line ("TRANSMISSION") followed by its value."""
    for i, line in enumerate(bullets[:-1]):
        if line.upper() == label:
            value = bullets[i + 1]
            return None if value.isupper() and len(value.split()) <= 3 and value != "PDK" else value
    return None


def parse_transmission(title: str | None, details_text: str | None,
                       year: int | None = None, model_line: str | None = None) -> str | None:
    """'Manual', 'PDK', 'Automatic' or None. Conflicting statements give None."""
    bullets = split_bullets(details_text)
    lines = [title or ""] + bullets
    mecum = _labelled(bullets, "TRANSMISSION")
    if mecum:
        lines.append(mecum)
    hits: set[str] = set()
    for i, line in enumerate(lines):
        pdk, auto = bool(_PDK_RE.search(line)), bool(_AUTO_RE.search(line))
        if pdk:
            hits.add("PDK")
        elif auto:
            hits.add("Automatic")
        if _MANUAL_RE.search(line):
            hits.add("Manual")
        elif not (pdk or auto):
            # Titles name a manual only as "6-Speed" (BaT's convention;
            # automatics are titled "Tiptronic"/"PDK"). That includes the 991's
            # 7-speed manual, which the old title parser filed as PDK.
            if i == 0 and _TITLE_SPEED_RE.search(line):
                hits.add("Manual")
            elif (_BARE_SPEED_RE.match(line) and year and year < 1990
                  and model_line not in _HAD_AUTOMATICS):
                hits.add("Manual")
    # PDK is a dual-clutch automatic; "PDK Dual-Clutch Automatic" is one fact.
    if hits == {"PDK", "Automatic"}:
        hits = {"PDK"}
    if hits == {"Automatic"} and model_line in _PDK_ERA_LINES and year and year >= PDK_ERA_START:
        hits = {"PDK"}
    if len(hits) == 1:
        return hits.pop()
    if hits:
        return None
    if model_line in _MANUAL_ONLY_LINES or (year and year < FIRST_AUTOMATIC_YEAR):
        return "Manual"
    if model_line in _PDK_ONLY_LINES:
        return "PDK"
    return None


_CHASSIS_RE = re.compile(
    r'^(?:chassis|vin|serial)(?:\s*(?:no\.?|number|#))?\s*[:.]?\s*([A-Z0-9][A-Z0-9 -]{4,22})$',
    re.IGNORECASE)


def parse_chassis(details_text: str | None) -> str | None:
    for line in split_bullets(details_text):
        m = _CHASSIS_RE.match(line)
        if m:
            value = m.group(1).strip(" -")
            # RM's page has the labels with the values stripped:
            # "Chassis No. Engine No".
            if re.search(r'\d', value) and not re.match(r'engine', value, re.IGNORECASE):
                return value.upper()
    return None


_INTERIOR_LINE_RE = re.compile(r'^(.{3,50}?)\s+(?:upholstery|interior)$', re.IGNORECASE)
# A spec line names a material; a sentence fragment ending in "interior"
# ("Wonderfully Preserved Original Interior") does not.
_MATERIAL_RE = re.compile(
    r'\b(?:leather(?:ette)?|cloth|vinyl|alcantara|race-?tex|houndstooth|tartan|pasha|'
    r'corduroy|velour|suede|fabric|tweed|leatherette|to\s+sample)\b'
    r'|\b(?:' + _COLOR_WORDS[3:-1] + r'|cork|cognac|espresso|bordeaux|burgundy|'
    r'saddle|camel|cashmere|graphite|carrera|marsala|luxor|agate|stone|natural|lin+en|oyster)\b',
    re.IGNORECASE)
_INTERIOR_LABEL_RE = re.compile(r'^interior\s*:\s*(.{2,50})$', re.IGNORECASE)
# Bullets about work done, not what the car has: "Refreshed Interior".
_NOT_INTERIOR_RE = re.compile(
    r'\b(?:new|recent|refresh|restor|replac|redone|reupholster|clean|detail|original|'
    r'updated|refurbish|retrimm|rebuilt|exterior|paint|and)\w*\b',
    re.IGNORECASE)


def parse_interior(details_text: str | None) -> str | None:
    bullets = split_bullets(details_text)
    mecum = _labelled(bullets, "INTERIOR COLOR")
    if mecum:
        return mecum
    for line in bullets:
        m = _INTERIOR_LABEL_RE.match(line)
        if m:
            return m.group(1).strip()
    for line in bullets:
        m = _INTERIOR_LINE_RE.match(line)
        if not m:
            continue
        value = m.group(1)
        # "Finished in Dolomite Grey over a Black leather": the interior is
        # the part after "over".
        if re.search(r'\bover\b', value, re.IGNORECASE):
            value = re.split(r'\bover\b', value, flags=re.IGNORECASE)[-1]
            value = re.sub(r'^\s*(?:an?|the)\s+', '', value, flags=re.IGNORECASE)
        if (_MATERIAL_RE.search(value) and len(value.split()) <= 7
                and not _NOT_INTERIOR_RE.match(value)
                and not re.search(r'\b(?:new|refresh|restor|replac|redone|upgraded|finished)\w*\b',
                                  value, re.IGNORECASE)):
            return value.strip(" ,")
    return None


# (label, pattern for the title and bullets). Order is display order.
OPTIONS: list[tuple[str, re.Pattern]] = [(label, re.compile(p, re.IGNORECASE)) for label, p in [
    # Bullets must name the package or edition: bare "Weissach" in a bullet is
    # usually the R&D centre ("hand-built by Weissach", "Weissach award",
    # the 928's "Weissach transaxle"). A bare mention in the title is the option.
    ("Weissach",         r'\bWeissach\s+(?:package|pack|edition|special)\b|[“"\']Weissach[”"\']'),
    ("PCCB",             r'\bPCCB\b|ceramic[-\s]composite\s+brakes?|carbon[-\s]ceramic\s+brakes?'),
    ("Sport Chrono",     r'\bsport\s+chrono\b'),
    ("Front-Axle Lift",  r'\b(?:front[-\s]axle|nose|front)[-\s]lift\b'),
    ("Carbon Buckets",   r'\bbucket\s+seats?\b|\bfull[-\s]buckets?\b'),
    ("Touring Package",  r'\btouring\s+package\b'),
    # Bullets: only the package. "Clubsport Steering Wheel" / "Clubsport
    # interior" are parts; the title names Clubsport cars (see _TITLE_OPTIONS).
    ("Clubsport",        r'\bclub\s?sport\s+(?:package|pack)\b'),
    # Leichtbau: Porsche's German name for the lightweight packages.
    ("Lightweight",      r'\blightweight\s+(?:package|pack|edition)\b|\bM471\b(?![-\s]style)|\bleichtbau\b'),
    ("Aerokit",          r'\baero\s?kit\b'),
    ("X50/X51",          r'\bX5[01]\b'),
    ("Burmester",        r'\bburmester\b'),
    ("Sport Exhaust",    r'\bsports?\s+exhaust\b'),
    ("Heritage Design",  r'\bheritage\s+design\b'),
]]
# Title-only: a variant name that is also a package ("911 GT3 Touring",
# "Carrera 3.2 Lightweight"); in bullets these words have other meanings.
_TITLE_OPTIONS = [
    ("Weissach",        re.compile(r'\bWeissach\b', re.IGNORECASE)),
    ("Touring Package", re.compile(r'\bGT3\s+Touring\b|\bTouring\s+Package\b', re.IGNORECASE)),
    ("Lightweight",     re.compile(r'\bLightweight\b|\bLeichtbau\b', re.IGNORECASE)),
    ("Clubsport",       re.compile(r'\bClub\s?sport\b(?!\s+(?:steering|wheel|seat|interior))', re.IGNORECASE)),
]

PROVENANCE: list[tuple[str, re.Pattern]] = [(label, re.compile(p, re.IGNORECASE)) for label, p in [
    ("One Owner",        r'\b(?:one|single|1)[-\s]owner\b(?![\'’]s)|\boriginal[-\s]owner\b(?![\'’]s)'),
    ("Matching Numbers", r'(?<!non-)(?<!non )(?<!not )\bmatching[-\s]numbers?\b'),
    ("Porsche COA",      r'\bcertificate\s+of\s+authenticity\b|\bCOA\b'),
    ("Kardex",           r'\bkardex\b'),
    ("Window Sticker",   r'\bwindow\s+sticker\b|\bmonroney\b'),
    ("Service Records",  r'\b(?:service|maintenance)\s+(?:records|history)\b'),
]]


def _scan(patterns, lines: list[str]) -> list[str]:
    found = []
    for label, pat in patterns:
        if label not in found and any(pat.search(ln) for ln in lines):
            found.append(label)
    return found


def parse_options(title: str | None, details_text: str | None) -> list[str]:
    lines = [title or ""] + split_bullets(details_text)
    found = _scan(OPTIONS, lines)
    for label, pat in _TITLE_OPTIONS:
        if label not in found and pat.search(title or ""):
            found.append(label)
    order = [label for label, _ in OPTIONS]
    return sorted(found, key=order.index)


def parse_provenance(title: str | None, details_text: str | None) -> list[str]:
    return _scan(PROVENANCE, [title or ""] + split_bullets(details_text))


def parse_pts(title: str | None, details_text: str | None) -> bool | None:
    """Paint to sample from the title, bullets, or a prose statement about this car."""
    head, _, tail = (details_text or "").partition(PROSE_SEPARATOR)
    return (parse_paint_to_sample([title or ""] + split_bullets(head))
            or parse_paint_to_sample(split_fragments(tail), prose=True))


def derive(title: str | None, details_text: str | None,
           year: int | None = None, model_line: str | None = None) -> dict:
    """All fields this module derives, ready for the auction_results columns."""
    return {
        "transmission": parse_transmission(title, details_text, year, model_line),
        "paint_to_sample": parse_pts(title, details_text),
        "chassis":      parse_chassis(details_text),
        "interior":     parse_interior(details_text),
        "options":      ",".join(parse_options(title, details_text)) or None,
        "provenance":   ",".join(parse_provenance(title, details_text)) or None,
    }
