import re

# Comprehensive Porsche color list: factory colors (all eras), PTS colors, and auction-validated names.
# Sources: paintlib.com (507 OEM codes), stuttcars.com, BaT auction titles, Gooding/RM highlights.
# Sorted longest-first at runtime so "Midnight Blue Metallic" matches before "Blue".
_COLORS = [
    # A
    "Achate Gray", "Acid Blue", "Acid Green", "Adriatic Blue", "Aetna Blue",
    "Agate Grey Metallic", "Agate Grey", "Alaska", "Albert Blue", "Alert Red",
    "Algarve Blue", "Alpine White", "Amarant Violet", "Amaranth Violet",
    "Amazon Green Metallic", "Amazon Green", "Amethyst Metallic", "Amethyst",
    "Anthracite Brown Metallic", "Apricot Beige", "Aqua Blue Metallic", "Aqua Blue",
    "Aquamarine Blue", "Aquamarine Metallic", "Aquarius Blue",
    "Arctic Grey", "Arctic Silver Metallic", "Arena Red Metallic", "Arena Red",
    "Arrow Blue", "Ascari Blue Metallic", "Atlas Grey Metallic", "Atlas Gray",
    "Audrain Green Metallic", "Auratium Green",
    "Aventurine Green Metallic", "Aventurine Green",
    "Azure Blue",
    "Azzurro California Metallic", "Azzurro California",
    "Azzurro Thetys Metallic", "Azzuro Thetys Metallic",
    # B
    "Bahama Blue", "Bahama Yellow", "Bahia Red", "Baltic Blue Metallic", "Basalt Black Metallic",
    "Bermuda Blue", "Biarritz White", "Birch Green", "Black Olive", "Black",
    "Blue Glacier", "Blue Turquoise", "Brewster Green", "Bright Bronze",
    "British Racing Green",
    # C
    "Carbon Black Metallic", "Carbon Steel Gray Metallic", "Carbon Steel Grey", "Caribe Blue",
    "Carmine Red", "Carmona Red Metallic",
    "Carrara White Metallic", "Carrara White", "Carrera White",
    "Casablanca White", "Cerise", "Centenaire Silver Metallic", "Chalk White", "Chalk",
    "Champagne Yellow", "Cherry", "China Gray", "Club Blue",
    "Cobalt Blue Metallic", "Cobalt Blue",
    "Cockney Brown", "Cognac", "Colorado", "Conda Green", "Continental Orange",
    "Coppa Florio Blue", "Coppa Florio", "Coral Red", "Cordoba Red", "Crayon",
    "Crystal Green", "Crystal Silver",
    # D
    "Daphne Green", "Dark Blue", "Dark Olive Metallic", "Dark Olive",
    "Dark Sapphire Metallic", "Dark Sea Blue", "Dark Teal", "Delphi Green Metallic",
    "Dolomite Grey Metallic", "Dolomite Silver Metallic",
    "Dolphin Gray",
    # E
    "Eberle Green", "Eggplant", "Emerald Green Metallic", "Emerald Green", "Etna Blue",
    # F
    "Fashion Grey", "Fayence Yellow", "Fish Silvergray Metallic",
    "Fjord Green", "Flachbau Lime Gold Metallic", "Flamingo",
    "Forest Green Metallic", "Fountain Blue Metallic", "Fountain Blue", "Fraise",
    "Frozen Berry Metallic", "Frozen Berry", "Frozen Blue Metallic", "Frozen Blue",
    # G
    "GT Silver Metallic", "GTS Red", "Gemini Blue Metallic", "Gemini Blue",
    "Gentian Blue Metallic", "Gentian Blue", "Geyser Green Metallic",
    "Glacier Blue", "Gold", "Grand Prix White",
    "Granite Green Metallic", "Granite Green",
    "Gold Green", "Golf Blue",
    "Graphite Blue", "Graphite Grey", "Graphite", "Gray Black", "Green Yellow",
    "Grey Black", "Grigio Telesto Metallic", "Grigio Telesto",
    "Guards Red Metallic", "Guards Red", "Gulf Blue", "Gulf Orange",
    # H
    "Helios Blue", "Heron Grey", "Horizon Blue Metallic",
    # I
    "Ibiza Red", "Ice Blue Metallic", "Ice Blue", "Ice Green Metallic", "Ice Grey",
    "India Red", "Indigo Blue Metallic", "Ipanema Blue Metallic",
    "Iris Blue Metallic", "Irish Green", "Ivory",
    # J
    "Jade Green", "Jet Black Metallic", "Jet Green Metallic", "Jet Green",
    "Jungle Green",
    # K
    "Kalahari Gold Metallic", "Kinematic Blue Metallic",
    # L
    "Lago Green Metallic", "Lagoon Green Metallic", "Lapis Blue Metallic", "Lava Gray", "Lava Orange",
    "Leaf Green", "Leinen", "Libelle Turquoise", "Light Blue Metallic", "Light Ivory", "Light Yellow",
    "Lime Gold", "Lime Green Metallic", "Lime Green", "Lime Yellow",
    "Linden Green", "Linen Grey Metallic", "Linen", "Liquid Metal Silver",
    "Lizard Green", "Lugano Blue",
    # M
    "Macadamia", "Magenta", "Mahogany Metallic", "Malachite Green Metallic",
    "Malachite Green", "Manaus Blue", "Marble Gray",
    "Marine Blue Metallic", "Marine Blue", "Maritim Blue", "Maritime Blue",
    "Meissen Blue", "Meridian", "Meteor", "Mexico Blue", "Miami Blue",
    "Midnight Blue Metallic", "Midnight Blue", "Minerva Blue Metallic", "Minerva Blue",
    "Mint Green", "Mirage", "Montego Blue",
    "Moonlight Blue Metallic", "Moonlight Blue",
    "Morocco Red Metallic", "Moss Green Metallic", "Murano Green",
    # N
    "Nardo Grey", "Nashy Blue", "Nato Olive", "Neo Slate Grey", "Night Blue Metallic",
    "Nogaro Blue Metallic", "Nordic Gold",
    # O
    "Oak Green Metallic", "Ocean Blue Metallic", "Ocean Blue",
    "Ocean Jade Metallic", "Olive Green", "Olive", "Olympic Blue", "Onyx", "Opal Metallic",
    "Orange Red", "Orange", "Oryx White Metallic", "Oslo Blue", "Oxford Grey",
    # P
    "Pacific Blue", "Pale Blue", "Palladium Metallic", "Palladium",
    "Panther Black Metallic", "Papaya Metallic",
    "Pastel Blue", "Pastel Orange", "Pastel Yellow", "Pearl", "Peridot",
    "Peru Red", "Phoenix Red", "Polar Silver Metallic", "Polar Silver",
    "Polo Red",
    "Prosecco", "Provence", "Prussian Blue Metallic",
    "Pure Blue", "Pure Green", "Pure Red",
    "Python Green Metallic", "Python Green",
    # Q
    "Quartzite Grey Metallic", "Quartzite Grey",
    # R
    "RS Green", "Racing Green Metallic", "Racing Green",
    "Racing Yellow", "Radium Green", "Raspberry Metallic", "Ravenna Green", "Red Orange",
    "Rhodium Silver Metallic", "Riviera Blue", "Ruby Red", "Ruby Star Neo",
    "Ruby Star", "Rubystone Red Metallic", "Rubystone Red",
    # S
    "Sahara Beige", "San Marino Blue", "Sand Beige", "Sand Yellow",
    "Sapphire Blue Metallic", "Scarlet Red", "Sea Green", "Sean Peach", "Seal Grey Metallic", "Shade Green",
    "Sholar Blue",
    "Shark Blue Metallic", "Shark Blue",
    "Signal Green Metallic", "Signal Green", "Signal Orange", "Signal Yellow",
    "Silver Green Diamond", "Silver Metallic", "Silver Rose Metallic", "Silver",
    "Slate Blue Metallic", "Slate Blue", "Slate Gray", "Slate Grey Metallic", "Slate Grey",
    "Smyrna Green", "Snow White", "South Sea Blue Metallic",
    "Speed Yellow Metallic", "Speed Yellow", "Speedster Blue", "Speedway Green",
    "Sport Classic Gray", "Steel Grey", "Stone Gray", "Stone Grey Metallic",
    "Sunflower Yellow", "Superior Red Metallic", "Superior Red",
    # T
    "Tabac", "Talbot Yellow", "Tangerine", "Tin Metallic", "Titan",
    "Topas Brown", "Truffle Brown", "Turquoise Metallic",
    # U
    "Ultraviolet", "Underberg Green",
    # V
    "Vanadium Grey", "Verde Zeltweg Metallic", "Vesuvio Grey", "Vesuvio Metallic", "Vesuvius Metallic",
    "Viola Metallic", "Viola Purple Metallic", "Violet Chrome Flair",
    "Viper Green", "Voodoo Blue",
    # W
    "White Gold Metallic", "White", "Wimbledon Green", "Wine Red Metallic",
    # Y
    "Yachting Blue Metallic", "Yachting Blue", "Yellow-Green",
    # Z
    "Zenith Blue Metallic", "Zermatt Silver Metallic", "Zinc Metallic",
]

# Deduplicate (case-insensitive, preserve first occurrence), then sort longest-first.
_PTSRS_COLOUR_WORD = re.compile(
    r"white|black|red|blue|green|grey|gray|silver|yellow|orange|brown|purple|violet|gold|beige|ivory|bronze|"
    r"pink|turquoise|aqua|lilac|magenta|olive|cream|chalk|crayon|burgundy|ruby|amethyst|copper|cognac|mint|lime|"
    r"sand|stone|rose|peach|plum|lavender|coral|cherry|emerald|jade|cobalt|graphite|anthracite|carmine|"
    r"caramel|sepia|tangerine|apricot|aubergine|grigio|rosso|verde|azzurro|azzuro|giallo|arancio|bianco|nero|blau|gr[uü]n|gelb", re.I)


def _porsche_official_names() -> list[str]:
    """English names from Porsche's own colour charts and brochures
    (data/porsche_colours/), so the parser knows Porsche's vocabulary."""
    import os
    import sys
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "data", "porsche_colours")
    if not os.path.isdir(here):
        return []
    sys.path.insert(0, here)
    try:
        from brochure_transcription import BROCHURES
        from colour_names import DE_EN
        try:
            from brochure_transcription_2 import BROCHURES_2
        except ImportError:
            BROCHURES_2 = []
    except ImportError:
        return []
    finally:
        sys.path.remove(here)
    names = {en for en, _ in DE_EN.values()}
    for b in BROCHURES + BROCHURES_2:
        for entries in b["tiers"].values():
            names.update(name for _, name, _ in entries)
    # Colours @ptsrs documents as PTS (internal evidence table, if present locally).
    import json
    table = os.path.expanduser("~/Projects/CollectorCarMarket-data/ptsrs/pts_evidence_table.json")
    if os.path.exists(table):
        try:
            for e in json.load(open(table)):
                for n in [e.get("colour")] + list(e.get("also_called") or []):
                    # only real colour names (captions sometimes give model words: 'Spyder', 'Turbo S Coupe')
                    if n and 3 <= len(n) <= 40 and _PTSRS_COLOUR_WORD.search(n) and len(n.split()) >= 2:
                        names.add(n.strip())
        except (ValueError, OSError):
            pass
    return sorted(names)


_seen: set[str] = set()
_unique: list[str] = []
for _c in _COLORS + _porsche_official_names() + ["Titanium Metallic"]:
    if _c.lower() not in _seen:
        _seen.add(_c.lower())
        _unique.append(_c)

COLORS = sorted(_unique, key=len, reverse=True)
_COLORS_LOWER = {c.lower(): c for c in COLORS}

# Patterns used to strip non-color prefixes that appear before the year in BaT titles.
_YEAR_RE      = re.compile(r'\b(19|20)\d{2}\b')
_MILEAGE_RE   = re.compile(r'^\s*[\d,]+k?-(?:Mile|Kilometer)\s+', re.IGNORECASE)
_NORESERVE_RE = re.compile(r'^\s*No\s+Reserve:\s*', re.IGNORECASE)
# Title prefixes that describe the car, not the paint: "Original-Owner Silver
# Metallic", "Repainted Black", "20-Years-Owned Guards Red".
_DESCRIPTOR_RE = re.compile(
    r'^\s*(?:(?:One|Original|Single|First|Two|Second|\d+)-Owners?|\d+-Years?-Owned|Euro-Spec|'
    r'RoW|Repainted|Refinished|Resprayed)[\s,]+', re.IGNORECASE)

# Fallback: 1–3 Title-Case words ending in a known color word.
# Catches valid colors not in the known list (e.g. new PTS releases, regional variants).
_COLOR_WORD_RE = re.compile(
    r'^(?:[A-Z][a-zA-Z-]+ ){0,2}[A-Z][a-zA-Z-]+'
    r'\s*(?:Blue|Green|Red|Grey|Gray|Silver|Yellow|White|Black|Brown|'
    r'Orange|Purple|Violet|Gold|Beige|Tan|Teal|Pink|Turquoise|Metallic|'
    r'Olive|Pearl|Bronze|Ivory|Copper|Cream|Crimson|Maroon|Lavender|'
    r'Champagne|Charcoal|Indigo|Magenta|Coral|Slate|Jade)$'
)


def scan_for_color(text: str | None) -> str | None:
    """Scan arbitrary text for any known Porsche color name (longest-first to avoid false shadows)."""
    if not text:
        return None
    text_lower = text.lower()
    for color_lower, color_canonical in _COLORS_LOWER.items():
        # Whole words only: "Titan" is a Porsche colour, and so is "Titanium
        # Metallic"; a substring test read the second as the first.
        if color_lower in text_lower and re.search(r"(?<![a-z])" + re.escape(color_lower) + r"(?![a-z])", text_lower):
            return color_canonical
    return None


_LEADING_ADJ = re.compile(
    r"^(?:(?:tasteful|stunning|beautiful|gorgeous|lovely|rare|very rare|desirable|striking|attractive|classic|timeless|"
    r"iconic|elegant|sharp|vibrant|handsome|sinister|menacing|sought[- ]after|stock|fresh|great|nice|clean|"
    r"pretty|bold|eye[- ]catching|unusual|uncommon|unique|seldom[- ]seen|popular|exquisite|spectacular|traditional|"
    r"understated|subtle)\s+)+", re.I)


def parse_color_from_phrase(phrase: str | None) -> str | None:
    """
    Normalize a raw color phrase extracted from auction text (e.g. 'Finished in X over Y').
    Known list takes priority; falls back to Title-Case pattern for unlisted colors.
    """
    if not phrase:
        return None
    # 'Tasteful White', 'Stock Black', 'Unusual Schiefergrau Metallic': the adjective is the writer's, not the paint's
    phrase = _LEADING_ADJ.sub("", phrase.strip()).strip()
    if not phrase:
        return None
    known = scan_for_color(phrase)
    if known:
        return known
    if _COLOR_WORD_RE.match(phrase):
        return phrase
    words = phrase.split()
    if 1 <= len(words) <= 3 and all(w[:1].isupper() for w in words):
        return phrase
    return None


def parse_exterior_color(title: str | None) -> str | None:
    """
    Extract exterior color from a BaT lot title.

    Color appears as a prefix before the model year:
        "Speed Yellow 2024 Porsche 911 GT3 RS Weissach"
        "752-Mile Gulf Blue 2023 Porsche 911 GT3 Touring"
    """
    if not title:
        return None

    m = _YEAR_RE.search(title)
    if not m:
        return None

    prefix = title[:m.start()]
    prefix = _MILEAGE_RE.sub('', prefix)
    prefix = _NORESERVE_RE.sub('', prefix)
    while _DESCRIPTOR_RE.match(prefix):
        prefix = _DESCRIPTOR_RE.sub('', prefix, count=1)
    prefix = prefix.strip()

    if not prefix:
        return None

    known = _COLORS_LOWER.get(prefix.lower())
    if known:
        return known

    if _COLOR_WORD_RE.match(prefix):
        return prefix

    return None
