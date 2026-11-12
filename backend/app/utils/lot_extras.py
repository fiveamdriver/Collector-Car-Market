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
    # Broad Arrow / RM highlight: "Finished in Light Yellow over a black
    # interior with Shetland cloth seat inserts".
    for line in bullets:
        m = _OVER_INTERIOR_RE.search(line)
        if m:
            value = _INTERIOR_ADJ_RE.sub("", m.group(1))
            value = re.sub(r'-\s+', '-', value)  # "Leather-to- Sample"
            if (_MATERIAL_RE.search(value) and len(value.split()) <= 5
                    and not _NOT_INTERIOR_RE.search(value)
                    and not re.search(r'focused|oriented|inspired|style|package|\bpack\b', value, re.IGNORECASE)
                    # "over a leather interior in Black": a bare material says too little.
                    and not re.fullmatch(r'(?:full[-\s])?(?:leather(?:ette)?|cloth|vinyl|fabric)',
                                         value.strip(), re.IGNORECASE)):
                return value.strip(" ,")
    return None


# Praise in front of the interior's name: "a beautiful Espresso leather".
_INTERIOR_ADJ_RE = re.compile(
    r'^(?:(?:beautiful|rare|special|stunning|striking|attractive|lovely|desirable|smart|'
    r'handsome|contrasting|elegant|luxurious|rich|gorgeous|sumptuous|classic|correct|uncommon|'
    r'optional|extended|authentic|bespoke|seldom[-\s]seen|'
    r'period[-\s]correct|factory[-\s]correct)\s+)+',
    re.IGNORECASE)


_OVER_INTERIOR_RE = re.compile(
    r'\bover\s+(?:an?\s+|the\s+|its\s+)?(?:original\s+|matching\s+|factory\s+)?'
    r'([A-Za-z][\w/ -]{1,40}?)\s+(?:interior|upholstery|cabin|cockpit)\b',
    re.IGNORECASE)


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


# ── Sonderwunsch ("Special Wishes", Porsche's factory special-order department) ──
#
# True only for a statement about THIS car. Not counted: history of the
# programme ("Porsche's Exclusive Manufaktur—sometimes called Sonderwunsch—
# obliged with an option package"), look-alikes ("Sonderwunsch-Style Details"),
# hedges ("Believed to be built as part of ..."), and aftermarket work ("the
# owner also had some sonderwunsch options installed" by a restorer).
_SW = r'(?:sonderwunsch\w*|special[-\s]wish(?:es)?)'
_SW_RE = re.compile(r'\b' + _SW + r'\b', re.IGNORECASE)
_SW_NOT_RE = re.compile(
    _SW + r'[-\s]style\b|\bbelieved\b|\breportedly\b|\baccording to\b|\binstalled\b'
    # History of the programme or of the model, not this car
    r'|\bmost\s+were\b|\binitially\b|\bto be built\b|\bnow called\b(?!\s+exclusiv)'
    r'|\bsometimes\s+called\b|\balso\s+known\s+as\b|\bformerly\b|\bknown\s+as\b'
    # Figurative: "the physical actualization of 'special wishes'"
    r'|\bactuali[sz]ation\b|\bembodiment\b|\bwhat\b[^.;]{0,20}\bmeant\b'
    # The 918's catalogue accessory: "a 'Special Wishes' extended-length charging cable"
    r'|\bcharging\s+cable\b'
    # Exclusive options described with the English translation: "Porsche Special
    # Wishes custom tailoring option" is Exclusive Custom Tailoring, not Sonderwunsch.
    r'|\bcustom\s+tail[eo]r\w*'
    # A single option code (09991 / 09981) means one option from the
    # Exclusive / Sonderwunsch department, not a Sonderwunsch build.
    r'|\b0?9{2,3}[89]1\b|\boption\s+codes?\b'
    # The certificate that comes with a special edition is not a commission.
    r'|' + _SW + r'\W+certificate\b',
    re.IGNORECASE)
# Exclusive Manufaktur special editions: a series, not a Sonderwunsch commission.
_SW_SPECIAL_EDITION_RE = re.compile(r'\bheritage\s+design\s+edition\b', re.IGNORECASE)
# Model years when "Sonderwunsch" / "Special Wishes" in a listing is the old name
# used loosely for Porsche Exclusive: the department was renamed Porsche Exclusive
# in 1986 (the M505 flat-nose became a price-list option for 1987), and Sonderwunsch
# returned only in 2021 (Factory Commission / Re-Commission / One-Off). Cars from
# these years are Exclusive builds or options, however the listing words it.
SW_EXCLUSIVE_ERA = range(1987, 2021)
# Another builder's own "special wishes" (Singer's options list).
_SW_OTHER_BUILDER_RE = re.compile(r'\bsinger\b|\breimagined\b', re.IGNORECASE)  # see _OTHER_BUILDER_RE
_Q2 = r'[\'"“”‘’]?'
_SW_PROSE_RES = [re.compile(p, re.IGNORECASE) for p in (
    # "ordered through the Sonderwunsch Factory Commissioning program",
    # "optioned with slantnose bodywork as part of Porsche's Sonderwunsch program",
    # "specified with experimental paint by way of Porsche's “Special Wishes”"
    r'\b(?:ordered|specified|optioned|fitted|built|commissioned|equipped|manufactured|'
    r'delivered|finished|produced|completed)\b[^.;]{0,120}?\b(?:through|via|from|with|under|by|'
    r'as part of|for|at|by way of)\s+(?:[\w’\'$~,.“”"]+\s+){0,5}?' + _Q2 + _SW,
    # "specified with $93k of Sonderwunsch commissioning", "the $13k Sonderwunsch"
    r'\$[\d,.]+\s*k?\s+(?:(?:of|in)\s+)?(?:\w+\s+){0,2}?' + _Q2 + _SW,
    # "Two Sonderwunsch 'Z' options were specified",
    # "Special Wishes options added over $30,000 to the build"
    _SW + _Q2 + r'[^.;]{0,30}\b(?:options?|features)\b[^.;]{0,20}\b(?:(?:were|was)\s+'
    r'(?:specified|fitted|ordered)|added|total(?:l?ing)?)',
    # "a Sonderwunsch interior", "mit einem Sonderwunsch-Innenraum",
    # "This is a one owner “Special Wishes” car"
    r'\b(?:a|an|its|this|einem|einen)\s+(?:[\w-]+\s+){0,3}?' + _Q2 + _SW + _Q2
    + r'[\s-]?(?:interior|innenraum|cockpit|cabin|car|example|coupe|coupé|cabriolet|targa|turbo)\b',
    # "a well-specified example of Porsche's 1980s Sonderwunsch programme"
    r'\b(?:this|is an?|one)\b[^.;]{0,40}\bexample of\b[^.;]{0,40}?' + _SW,
)]


def parse_sonderwunsch(title: str | None, details_text: str | None, year: int | None = None) -> bool:
    """A Sonderwunsch (Special Wishes) car, by its title, a bullet, or a prose
    statement about this car."""
    if _SW_OTHER_BUILDER_RE.search(title or ""):
        return False
    if year in SW_EXCLUSIVE_ERA:
        return False
    if _SW_SPECIAL_EDITION_RE.search(title or ""):
        return False
    head, _, tail = (details_text or "").partition(PROSE_SEPARATOR)
    lines = [title or ""] + [ln.strip() for ln in head.split("\n") if ln.strip()]
    if any(_SW_RE.search(ln) and not _SW_NOT_RE.search(ln) for ln in lines):
        return True
    return any(p.search(f) and not _SW_NOT_RE.search(f)
               for f in split_fragments(tail) if _SW_RE.search(f)
               for p in _SW_PROSE_RES)


# Factory M491 "Turbo Look" (US) / "Supersport" (UK) on the 1984–89 Carrera 3.2:
# Turbo body, brakes and suspension on the normally aspirated car. Not a replica
# ("M491-Look", "Turbo-Look conversion", "930-style").
_M491_RE = re.compile(r'\bM491\b(?![-\s]?(?:look|style))|\bturbo[-\s]?look\b|\bsupersport\b', re.IGNORECASE)
_M491_NOT_RE = re.compile(r'\bconver\w*|\breplica\b|\btribute\b|\bclone\b|[-\s]style\b|\bM491[-\s]look\b|\bbackdat\w*',
                          re.IGNORECASE)


def parse_m491(title: str | None, details_text: str | None, year: int | None) -> bool:
    if not year or not 1984 <= year <= 1989:
        return False
    lines = [title or ""] + split_bullets(details_text)
    if any(_M491_NOT_RE.search(ln) for ln in lines if _M491_RE.search(ln)):
        return False
    return any(_M491_RE.search(ln) for ln in lines)


def parse_options(title: str | None, details_text: str | None, year: int | None = None) -> list[str]:
    lines = [title or ""] + split_bullets(details_text)
    found = _scan(OPTIONS, lines)
    for label, pat in _TITLE_OPTIONS:
        if label not in found and pat.search(title or ""):
            found.append(label)
    if parse_sonderwunsch(title, details_text, year):
        found.append("Sonderwunsch")
    if parse_m491(title, details_text, year):
        found.append("M491")
    order = ["Sonderwunsch", "M491"] + [label for label, _ in OPTIONS]
    return sorted(found, key=order.index)


def parse_provenance(title: str | None, details_text: str | None) -> list[str]:
    return _scan(PROVENANCE, [title or ""] + split_bullets(details_text))


# Cars rebuilt by another maker: their "paint-to-sample" is that maker's own
# paint, not a Porsche factory order. ("Turbo Remastered by Porsche
# Sonderwunsch" is Porsche's own, hence the lookahead.)
_OTHER_BUILDER_RE = re.compile(
    r'\bsinger\b|\breimagined\b|\bgunther\s+werks\b|\bremastered\s+by\s+(?!porsche)|\bemory\b'
    r'|\btheon\b|\bbackdate\b|\boutlaw\b',
    re.IGNORECASE)


def parse_pts(title: str | None, details_text: str | None) -> bool | None:
    """Paint to sample from the title, bullets, or a prose statement about this car."""
    if _OTHER_BUILDER_RE.search(title or ""):
        return None
    head, _, tail = (details_text or "").partition(PROSE_SEPARATOR)
    return (parse_paint_to_sample([title or ""] + split_bullets(head))
            or parse_paint_to_sample(split_fragments(tail), prose=True))


# ── Models built with one gearbox only ───────────────────────────────────────
#
# (model_line, generation, variant) → the only factory gearbox. Only models
# where Porsche offered exactly one; anything sold both ways is left out (991.2
# GT3 — the Touring was manual-only but the wing car had both; 992 GT3, 718
# GT4 and Spyder, 996/997 Turbo, Cayman R, 987 Spyder, 964 Speedster,
# Sportomatic-era 911S/914-6). Race cars are left out: their gearboxes vary.
_M, _P = "Manual", "PDK"
SINGLE_GEARBOX: dict[tuple[str, str, str], str] = {
    # Air-cooled
    ("911", "F-Body", "Carrera RS 2.7"): _M,
    ("911", "G-Body", "Carrera RS 3.0"): _M,
    ("911", "G-Body", "930 Turbo"): _M,
    ("911", "G-Body", "Turbo 3.3 Slant Nose"): _M,
    ("911", "G-Body", "Speedster"): _M,
    ("911", "964", "Carrera 4"): _M,
    ("911", "964", "Carrera RS"): _M,
    ("911", "964", "RS 3.8"): _M,
    ("911", "964", "RS America"): _M,
    ("911", "964", "Turbo"): _M,
    ("911", "964", "Turbo S"): _M,
    ("911", "993", "Carrera 4"): _M,
    ("911", "993", "Carrera 4S"): _M,
    ("911", "993", "Carrera RS"): _M,
    ("911", "993", "GT2"): _M,
    ("911", "993", "Turbo"): _M,
    ("911", "993", "Turbo S"): _M,
    # Mezger GT cars: manual only
    **{("911", g, v): _M for g in ("996.1", "996.2") for v in ("GT2", "GT3", "GT3 RS")},
    **{("911", g, v): _M for g in ("997.1", "997.2")
       for v in ("GT2", "GT2 RS", "GT3", "GT3 RS", "GT3 RS 4.0")},
    ("911", "997.2", "Sport Classic"): _M,
    ("911", "991.1", "R"): _M,
    ("911", "991.2", "Speedster"): _M,
    ("911", "992.1", "S/T"): _M,
    ("911", "992.1", "Sport Classic"): _M,
    ("Cayman", "981", "GT4"): _M,
    ("Boxster", "981", "Spyder"): _M,
    # PDK only
    ("911", "997.2", "Speedster"): _P,
    ("911", "997.2", "Turbo S"): _P,
    ("911", "991.1", "GT3"): _P,
    ("911", "991.1", "GT3 RS"): _P,
    ("911", "991.2", "GT3 RS"): _P,
    ("911", "991.2", "GT2 RS"): _P,
    ("911", "992.1", "GT3 RS"): _P,
    ("911", "992.1", "Dakar"): _P,
    **{("911", g, v): _P for g in ("991.1", "991.2", "992.1", "992.2") for v in ("Turbo", "Turbo S")},
    ("Cayman", "718", "GT4 RS"): _P,
    ("Boxster", "718", "Spyder RS"): _P,
    ("911 GT1", "911 GT1", "base"): _M,
}


def model_gearbox(model_line: str | None, generation: str | None, variant: str | None) -> str | None:
    return SINGLE_GEARBOX.get((model_line or "", generation or "", variant or ""))


# 964 Carrera RS N/GT (M003, ~290 built, the Group N/GT homologation car) is what
# listings also call the "Carrera RS Clubsport". On a 964 RS the tag reads N/GT.
# Title-only: lot essays on ordinary RSs and RS Americas mention the N/GT as
# background ("Then came the N/GT..."). The RS 3.8 is a different car.
_NGT_TITLE = re.compile(r'\bN[/-]GT\b|\bNGT\b|\bM003\b', re.IGNORECASE)
_964_RS = re.compile(r'\bCarrera\s+RS\b', re.IGNORECASE)
_NOT_NGT = re.compile(r'\bAmerica\b|\bRS\s?3\.8\b', re.IGNORECASE)


def ngt_options(options: list[str], title: str | None, generation: str | None) -> list[str]:
    """On a 964 Carrera RS, 'Clubsport' (or N/GT in the title) becomes 'N/GT'."""
    t = title or ""
    if generation != "964" or not _964_RS.search(t) or _NOT_NGT.search(t):
        return options
    if "Clubsport" in options or _NGT_TITLE.search(t):
        return ["N/GT"] + [o for o in options if o not in ("Clubsport", "N/GT")]
    return options


# The 964's only Leichtbau cars are the Carrera 4 Lightweight (22, Weissach Cup
# development cars, 1990-91) and the Turbo S Leichtbau (86, Porsche Exclusive,
# 1992-93). "Leichtbau sport version" on a Carrera RS is just the RS's standard
# (non-Touring) spec, so the tag stays off every other 964 (checked 2026-11-05).
_964_LEICHTBAU = re.compile(r'\bCarrera\s*4|\bC4\b|\bTurbo\s*S\b', re.IGNORECASE)


# ── Canepa (959) ──────────────────────────────────────────────────────────────
# Canepa of Scotts Valley is the 959 specialist; a 959 it re-engineered (the
# "959 SC Reimagined by Canepa", Stage One / Phase II / Gen 3 engines, 959S
# conversions, Canepa suspension) trades as its own thing (owner, 2026-11-12).
# A sentence must tie Canepa to work on the car: "serviced at Canepa",
# "imported by Bruce Canepa", "Canepa service binders" and quotes from Bruce
# Canepa are not Canepa cars.
_CANEPA_RE = re.compile(r'\bcanepa\b', re.IGNORECASE)
_CANEPA_WORK_RE = re.compile(
    r'\bupgrad\w*|\breimagined\b|\bstage\s+(?:one|two|1|2|i{1,2})\b|\bphase\s+(?:ii?|2|two)\b'
    r'|\bgen\.?\s*\d\b|\b(?-i:959\s?S)\b|\bsuspension\b|\bcoilovers?\b|\bengine\s+(?:build|enhancements?)\b',
    re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?;])\s+|\n+|\s+[*•]\s*')


def parse_canepa(title: str | None, details_text: str | None, model_line: str | None) -> bool:
    """A 959 re-engineered or upgraded by Canepa, per its title or a sentence of its listing."""
    if model_line != "959":
        return False
    if _CANEPA_RE.search(title or ""):
        return True
    return any(_CANEPA_RE.search(s) and _CANEPA_WORK_RE.search(s)
               for s in _SENTENCE_SPLIT.split(details_text or ""))


def leichtbau_options(options: list[str], title: str | None, generation: str | None) -> list[str]:
    if generation == "964" and "Lightweight" in options and not _964_LEICHTBAU.search(title or ""):
        return [o for o in options if o != "Lightweight"]
    return options


def derive(title: str | None, details_text: str | None,
           year: int | None = None, model_line: str | None = None,
           generation: str | None = None, variant: str | None = None) -> dict:
    """All fields this module derives, ready for the auction_results columns."""
    stated = parse_transmission(title, details_text, year, model_line)
    only = model_gearbox(model_line, generation, variant)
    # A single-gearbox model settles it. A listing that says otherwise (a
    # conversion, or a misread) gets None and shows up in the conflict report
    # (data/migrate_lot_extras.py) for a person to decide.
    transmission = stated if only is None else only if stated in (None, only) else None
    return {
        "transmission": transmission,
        "paint_to_sample": parse_pts(title, details_text),
        "chassis":      parse_chassis(details_text),
        "interior":     parse_interior(details_text),
        # M491 is a factory Porsche 911 option; RUF and other builders do not get the tag.
        "options":      ",".join([o for o in leichtbau_options(ngt_options(parse_options(title, details_text, year), title, generation), title, generation)
                                  if o != "M491" or model_line == "911"]
                                 + (["Canepa"] if parse_canepa(title, details_text, model_line) else [])) or None,
        "provenance":   ",".join(parse_provenance(title, details_text)) or None,
    }
