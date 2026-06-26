#!/usr/bin/env python3
"""
Ingest Porsche auction data from BaT's internal API into auction_results.

Usage (from backend/ directory):
    python data/bat_ingest.py

No API key required. Re-running is safe — duplicates are skipped by auction_url.
"""
import asyncio
import certifi
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from app.utils.color_parser import parse_exterior_color
from sqlalchemy import select, update

API_URL   = "https://bringatrailer.com/wp-json/bringatrailer/1.0/data/listings-filter"
SSL_CTX   = ssl.create_default_context(cafile=certifi.where())
MAX_PAGES = None  # set to an integer to limit pages per config during test runs


# ── Query configs ─────────────────────────────────────────────────────────────

CONFIGS = [
    # ── Multi-generation ──────────────────────────────────────────────────────
    {"name": "911 GT3/GT3 RS",    "ids": [2015688, 55778434, 55778221, 55778351], "model_line": "911",        "variant": None},
    # ── F-Body ─────────────────────────────────────────────────────────────
    {"name": "Carrera RS 2.7",    "ids": [68399612],                              "model_line": "911",        "variant": "Carrera RS 2.7"},
    # ── G-Body ───────────────────────────────────────────────────────────────
    {"name": "911 SC",            "ids": [16982431],                              "model_line": "911",        "variant": None},
    {"name": "911 Carrera 3.2",   "ids": [1833037],                               "model_line": "911",        "variant": None},
    {"name": "930 Turbo",         "ids": [1833042],                               "model_line": "911",        "variant": None},
    {"name": "G-Body Speedster",  "ids": [18545334],                              "model_line": "911",        "variant": None},
    {"name": "Carrera 2.7 MFI",  "ids": [47454972],                              "model_line": "911",        "variant": None},
    # ── 964 ──────────────────────────────────────────────────────────────────
    {"name": "964",               "ids": [1833038],                               "model_line": "911",        "variant": "Carrera 2"},
    {"name": "964 Carrera RS",    "ids": [74679063],                              "model_line": "911",        "variant": "Carrera RS"},
    {"name": "964 RS America",    "ids": [13042525],                              "model_line": "911",        "variant": "RS America"},
    {"name": "964 Turbo",         "ids": [1833043],                               "model_line": "911",        "variant": None},
    {"name": "964 Speedster",     "ids": [107034406],                             "model_line": "911",        "variant": "Speedster"},
    {"name": "964 Singer",        "ids": [49009648],                              "model_line": "911",        "variant": "Singer"},
    # ── 993 ──────────────────────────────────────────────────────────────────
    {"name": "993 Carrera",       "ids": [1833039],                               "model_line": "911",        "variant": "Carrera"},
    {"name": "993 Carrera 4",     "ids": [113028272],                             "model_line": "911",        "variant": "Carrera 4"},
    {"name": "993 Carrera 4S",    "ids": [113028394],                             "model_line": "911",        "variant": "Carrera 4S"},
    {"name": "993 Carrera S",     "ids": [113028363],                             "model_line": "911",        "variant": "Carrera S"},
    {"name": "993 Carrera RS",    "ids": [113029626],                             "model_line": "911",        "variant": "Carrera RS"},
    {"name": "993 Turbo",         "ids": [1833044],                               "model_line": "911",        "variant": None},
    {"name": "993 GT2",           "ids": [55777633],                              "model_line": "911",        "variant": "GT2"},
    # ── 996 ──────────────────────────────────────────────────────────────────
    {"name": "996 Carrera",       "ids": [1833242],                               "model_line": "911",        "variant": "Carrera"},
    {"name": "996 Turbo",         "ids": [1833045],                               "model_line": "911",        "variant": "Turbo"},
    {"name": "996 GT2",           "ids": [55777735],                              "model_line": "911",        "variant": "GT2"},
    # ── 997 ──────────────────────────────────────────────────────────────────
    {"name": "997 Carrera",       "ids": [107031422],                             "model_line": "911",        "variant": "Carrera"},
    {"name": "997 Carrera S",     "ids": [1833041],                               "model_line": "911",        "variant": "Carrera S"},
    {"name": "997 Carrera GTS",   "ids": [107031793],                             "model_line": "911",        "variant": "Carrera GTS"},
    {"name": "997 Turbo",         "ids": [2069776],                               "model_line": "911",        "variant": None},
    {"name": "997 Sport Classic", "ids": [107031857],                             "model_line": "911",        "variant": "Sport Classic"},
    {"name": "997 GT2",           "ids": [55777781],                              "model_line": "911",        "variant": None},
    {"name": "997 Speedster",     "ids": [107032063],                             "model_line": "911",        "variant": "Speedster"},
    # ── 991 ──────────────────────────────────────────────────────────────────
    {"name": "991 Carrera",       "ids": [107019763],                             "model_line": "911",        "variant": "Carrera"},
    {"name": "991 Carrera S",     "ids": [4247680],                               "model_line": "911",        "variant": "Carrera S"},
    {"name": "991 Carrera T",     "ids": [107020080],                             "model_line": "911",        "variant": "Carrera T"},
    {"name": "991 Carrera GTS",   "ids": [107020671],                             "model_line": "911",        "variant": "Carrera GTS"},
    {"name": "991 Turbo",         "ids": [36019255],                              "model_line": "911",        "variant": None},
    {"name": "991 GT2 RS",        "ids": [12792997],                              "model_line": "911",        "variant": None},
    {"name": "991 R",             "ids": [107021997],                             "model_line": "911",        "variant": "R"},
    {"name": "991 Speedster",     "ids": [107022050],                             "model_line": "911",        "variant": "Speedster"},
    # ── 992 ──────────────────────────────────────────────────────────────────
    {"name": "992 Carrera",       "ids": [107008946],                             "model_line": "911",        "variant": "Carrera"},
    {"name": "992 Carrera S",     "ids": [40032430],                              "model_line": "911",        "variant": "Carrera S"},
    {"name": "992 Carrera T",     "ids": [107009365],                             "model_line": "911",        "variant": "Carrera T"},
    {"name": "992 Carrera GTS",   "ids": [107009458],                             "model_line": "911",        "variant": "Carrera GTS"},
    {"name": "992 Turbo",         "ids": [40033130],                              "model_line": "911",        "variant": "Turbo"},
    {"name": "992 Turbo S",       "ids": [40033138],                              "model_line": "911",        "variant": "Turbo S"},
    {"name": "992 S/T",           "ids": [106842163],                             "model_line": "911",        "variant": "S/T"},
    {"name": "992 Sport Classic", "ids": [106277777],                             "model_line": "911",        "variant": "Sport Classic"},
    {"name": "992 Dakar",         "ids": [106526993],                             "model_line": "911",        "variant": "Dakar"},
    # ── Cayman ───────────────────────────────────────────────────────────────
    {"name": "987 Cayman",        "ids": [2662294],                               "model_line": "Cayman",     "variant": None},
    {"name": "981 Cayman",        "ids": [45900428],                              "model_line": "Cayman",     "variant": None},
    {"name": "718 Cayman",        "ids": [45900495],                              "model_line": "Cayman",     "variant": None},
    {"name": "Cayman GT4",        "ids": [12819306],                              "model_line": "Cayman",     "variant": None},
    # ── Boxster ──────────────────────────────────────────────────────────────
    {"name": "986 Boxster",       "ids": [2014390],                               "model_line": "Boxster",    "variant": None},
    {"name": "987 Boxster",       "ids": [44426381],                              "model_line": "Boxster",    "variant": None},
    {"name": "981 Boxster",       "ids": [44426447],                              "model_line": "Boxster",    "variant": None},
    {"name": "718 Boxster",       "ids": [44426756],                              "model_line": "Boxster",    "variant": None},
    # ── Standalone models ─────────────────────────────────────────────────────
    {"name": "Carrera GT",        "ids": [38349021],                              "model_line": "Carrera GT", "variant": "base"},
    {"name": "959",               "ids": [39491899],                              "model_line": "959",        "variant": "base"},
    {"name": "918 Spyder",        "ids": [38553278],                              "model_line": "918 Spyder", "variant": None},
]


# ── Generation lookup ─────────────────────────────────────────────────────────

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
    return "992"


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


# ── Field parsers ─────────────────────────────────────────────────────────────

YEAR_RE     = re.compile(r'\b(19|20)\d{2}\b')
MILEAGE_RE  = re.compile(r'([\d,]+)(k)?-(Mile|Kilometer)', re.IGNORECASE)

VARIANT_PATTERNS = [
    "GT3 RS 4.0", "GT3 RS", "GT3",
    "GT2 RS", "GT2",
    "Turbo S", "Turbo",
    "RS America", "Carrera RS", "Carrera S", "Carrera GTS", "Carrera T", "Carrera",
]

WIDEBODY_VARIANTS = {"GT3 RS", "GT3 RS 4.0", "GT2", "GT2 RS", "Turbo", "Turbo S", "Turbo 3.3", "Turbo 3.0"}
WIDEBODY_MODELS   = {"959", "Carrera GT", "918 Spyder"}


def parse_year(title: str) -> int | None:
    m = YEAR_RE.search(title)
    return int(m.group()) if m else None


def parse_variant(title: str) -> str:
    """
    Extract the 911 variant from a BaT lot title using longest-match priority.

    VARIANT_PATTERNS is ordered most-specific to least-specific so that
    "GT3 RS 4.0" is matched before "GT3 RS" and "GT3 RS" before "GT3".
    Returns "base" when no pattern matches (i.e. a stock Carrera).
    """
    for pat in VARIANT_PATTERNS:
        if pat in title:
            return pat
    return "base"


CAYMAN_BOXSTER_PATTERNS = ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]


def parse_cayman_boxster_variant(title: str) -> str:
    """
    Extract the Cayman/Boxster variant from a BaT lot title.

    Named patterns (GT4 RS, GT4, GTS, Spyder RS, Spyder) are checked first.
    Then word-boundary checks for the single-letter variants R and S, which
    must be whole words to avoid false matches against other abbreviations.
    Returns "base" for an unspecced car.
    """
    for pat in CAYMAN_BOXSTER_PATTERNS:
        if pat in title:
            return pat
    if re.search(r'\bR\b', title):
        return 'R'
    if re.search(r'\bS\b', title):
        return 'S'
    return 'base'


def parse_gbody_variant(title: str, year: int) -> str:
    """
    Extract the G-Body 911 variant from a BaT lot title and production year.

    Priority chain runs most-specific to least-specific:
      Slant Nose (modified Turbo) → MFI → Carrera 2.7 → Carrera RS →
      Speedster → Turbo (930) → early Carrera (≤1977) → SC → Carrera 3.2 →
      911S → base 911

    Year is used to disambiguate "Carrera" titles, since both the early
    Carrera 2.7 (1972–1977) and the Carrera 3.2 (1984–1989) appear in
    G-Body production years.
    """
    if 'Slant Nose' in title:
        return 'Turbo 3.3 Slant Nose'
    if 'MFI' in title:
        return 'Carrera 2.7 MFI'
    if 'Carrera 2.7' in title:
        return 'Carrera 2.7'
    if 'Carrera RS' in title:
        return 'Carrera RS 3.0'
    if 'Speedster' in title:
        return 'Speedster'
    if 'Turbo' in title:
        return '930 Turbo'
    if 'Carrera' in title and year <= 1977:
        return 'Carrera 2.7'
    if 'SC' in title:
        return 'SC'
    if 'Carrera 3.2' in title or ('Carrera' in title and year >= 1984):
        return 'Carrera 3.2'
    if '911S' in title or '911 S' in title:
        return '911S'
    return '911'


def parse_transmission(title: str) -> str:
    """
    Infer transmission type from the lot title.

    BaT titles consistently include speed/type tokens when the transmission
    is notable (e.g. "7-Speed PDK", "6-Speed Manual").  PDK is always 7-speed;
    manual cars are 5- or 6-speed depending on generation.  Defaults to Manual
    because the majority of historic Porsches sold on BaT are manual.
    """
    if any(k in title for k in ("PDK", "7-Speed", "7-speed")):
        return "PDK"
    if any(k in title for k in ("6-Speed", "6-speed", "5-Speed", "5-speed", "Manual")):
        return "Manual"
    return "Manual"


def parse_mileage(title: str) -> int | None:
    m = MILEAGE_RE.search(title)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    if m.group(2):                              # 'k' suffix
        value *= 1_000
    if "kilometer" in m.group(3).lower():
        value /= 1.609
    return round(value)


def parse_paint_to_sample(title: str) -> bool | None:
    if re.search(r'paint[-\s]to[-\s]sample|PTS', title, re.IGNORECASE):
        return True
    return None


def compute_is_widebody(variant: str, model_line: str) -> bool:
    # Not stored in DB schema — computed here for future use / logging
    return variant in WIDEBODY_VARIANTS or model_line in WIDEBODY_MODELS


# ── Autocomplete discovery ────────────────────────────────────────────────────

AUTOCOMPLETE_URL = "https://bringatrailer.com/wp-json/bringatrailer/1.0/data/autocomplete"


def discover_keyword_pages(term: str) -> list[dict]:
    """
    Hit BaT's autocomplete endpoint for a search term and return all matches.

    Each match is a dict with at minimum 'id' and 'label' keys. The correct
    keyword_pages ID for a given model is not always the first result — callers
    should review all matches and pick the right one before adding to CONFIGS.

    Returns an empty list if the request fails or no matches are found.
    """
    url = f"{AUTOCOMPLETE_URL}?{urllib.parse.urlencode({'term': term})}"
    req = urllib.request.Request(url, headers={
        "Accept":     "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"  autocomplete error for {term!r}: {exc}", file=sys.stderr)
        return []

    # Response: {"results": [{"title": "...", "destination": "<id>", "result_type": "item", ...}, ...]}
    items = payload.get("results") if isinstance(payload, dict) else payload if isinstance(payload, list) else []

    matches = []
    for item in items:
        if not isinstance(item, dict):
            continue
        id_ = item.get("destination")
        label = item.get("title") or str(id_)
        result_type = item.get("result_type", "")
        if id_ is not None:
            matches.append({"id": id_, "label": label, "result_type": result_type, "raw": item})
    return matches


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_page(ids: list[int], page: int) -> list[dict]:
    """
    Fetch one page of auction listings from BaT's internal listings-filter API.

    Returns the raw item list from the response, or an empty list if no items
    were returned.  The caller is responsible for catching network exceptions.
    """
    params = [
        ("page",                     page),
        ("per_page",                 24),
        ("get_items",                1),
        ("get_stats",                0),
        ("base_filter[items_type]",  "model"),
        ("sort",                     "td"),
    ]
    for id_ in ids:
        params.append(("base_filter[keyword_pages][]", id_))

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "Accept":     "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("items") or []


# ── Record mapper ─────────────────────────────────────────────────────────────

def map_record(raw: dict, model_line: str, config_variant: str | None) -> dict | None:
    """
    Map a raw BaT API item to an auction_results row dict.

    Returns None for unsold lots (auctions that ended without a sale) and for
    items missing a year or price.  config_variant overrides title-parsed
    variants for configs where the variant is unambiguous (e.g. "964 RS America").
    Generation-specific parsers (G-Body, Cayman/Boxster) are selected before
    the generic 911 parse_variant fallback.
    """
    sold_text = raw.get("sold_text") or ""
    if not sold_text.startswith("Sold for"):
        return None

    price = raw.get("current_bid")
    if price is None:
        return None

    title = raw.get("title") or ""
    year  = parse_year(title)
    if not year:
        return None

    if model_line == "911":
        generation = get_911_generation(year)
    elif model_line == "Cayman":
        generation = get_cayman_generation(year)
    elif model_line == "Boxster":
        generation = get_boxster_generation(year)
    else:
        generation = model_line

    if generation == '964' and 'RS America' in title:
        variant = 'RS America'
    elif config_variant is not None:
        variant = config_variant
    elif generation == 'G-Body':
        variant = parse_gbody_variant(title, year)
    elif model_line in ('Cayman', 'Boxster'):
        variant = parse_cayman_boxster_variant(title)
    else:
        variant = parse_variant(title)
    transmission = parse_transmission(title)

    ts = raw.get("sold_text_timestamp")
    try:
        sold_date = datetime.fromtimestamp(int(ts)).date()
    except (TypeError, ValueError, OSError):
        sold_date = None

    return dict(
        make              = "Porsche",
        model_line        = model_line,
        generation        = generation,
        variant           = variant,
        year              = year,
        transmission      = transmission,
        is_widebody       = compute_is_widebody(variant, model_line) or None,
        mileage           = parse_mileage(title),
        thumbnail_url     = raw.get("thumbnail_url"),
        sold_price        = int(price),
        auction_source    = "BaT",
        auction_url       = raw.get("url"),
        sold_date         = sold_date,
        lot_title         = title,
        exterior_color    = parse_exterior_color(title),
        paint_to_sample   = parse_paint_to_sample(title),
        production_number = None,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

async def ingest(only: list[str] | None = None) -> None:
    """
    only: optional list of substrings; a config is run only if its name contains
          at least one of them (case-insensitive). Pass None to run all configs.
    """
    configs = CONFIGS
    if only:
        patterns = [p.lower() for p in only]
        configs = [c for c in CONFIGS if any(p in c["name"].lower() for p in patterns)]
        print(f"Running {len(configs)}/{len(CONFIGS)} configs matching: {only}\n")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load existing records: url → thumbnail_url (None means no thumbnail yet)
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url, AuctionResult.thumbnail_url).where(
                AuctionResult.auction_url.isnot(None)
            )
        )
        existing: dict[str, str | None] = {row[0]: row[1] for row in rows.fetchall()}

    total_fetched = total_skipped = 0
    to_insert:  list[dict] = []
    to_backfill: list[tuple[str, str]] = []  # (auction_url, thumbnail_url)

    for cfg in configs:
        name        = cfg["name"]
        ids         = cfg["ids"]
        model_line  = cfg["model_line"]
        cfg_variant = cfg["variant"]

        cfg_fetched = cfg_queued = cfg_updated = cfg_skipped = 0
        page = 1

        print(f"[{name}]")
        while MAX_PAGES is None or page <= MAX_PAGES:
            try:
                items = fetch_page(ids, page)
            except Exception as exc:
                print(f"  page {page} ERROR: {exc}")
                break

            if not items:
                break

            cfg_fetched += len(items)

            for raw in items:
                rec = map_record(raw, model_line, cfg_variant)
                if rec is None:
                    cfg_skipped += 1
                    continue
                url = rec.get("auction_url")
                # BaT always provides URLs; null-URL records skip dedup and would duplicate on re-run.
                if url and url in existing:
                    if existing[url] is None and rec.get("thumbnail_url"):
                        to_backfill.append((url, rec["thumbnail_url"]))
                        existing[url] = rec["thumbnail_url"]  # prevent double-queue
                        cfg_updated += 1
                    else:
                        cfg_skipped += 1
                    continue
                if url:
                    existing[url] = rec.get("thumbnail_url")
                to_insert.append(rec)
                cfg_queued += 1

            page += 1
            time.sleep(2)

        total_fetched += cfg_fetched
        total_skipped += cfg_skipped
        print(f"  fetched: {cfg_fetched} | queued: {cfg_queued} | backfilled: {cfg_updated} | skipped: {cfg_skipped}")
        time.sleep(5)

    async with AsyncSessionLocal() as session:
        if to_insert:
            session.add_all([AuctionResult(**r) for r in to_insert])
        for url, thumb in to_backfill:
            await session.execute(
                update(AuctionResult)
                .where(AuctionResult.auction_url == url)
                .values(thumbnail_url=thumb)
            )
        await session.commit()

    print(
        f"\nTotal — fetched: {total_fetched} | inserted: {len(to_insert)} | "
        f"backfilled: {len(to_backfill)} | skipped: {total_skipped}"
    )
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only", metavar="PATTERN",
        help="Comma-separated substrings; only run configs whose name contains one (e.g. '996,997,991,992')",
    )
    args = parser.parse_args()
    only = [p.strip() for p in args.only.split(",")] if args.only else None
    asyncio.run(ingest(only=only))
