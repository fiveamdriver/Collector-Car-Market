#!/usr/bin/env python3
"""
Ingest Porsche auction results from RM Sotheby's internal search API.

Usage (from backend/ directory):
    python data/rms_ingest.py

No API key or authentication required. Re-running is safe — duplicates are
skipped by auction_url. Non-USD lots are skipped (most major US events are USD).
"""
import asyncio
import certifi
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from app.utils.color_parser import scan_for_color
from sqlalchemy import select

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

SEARCH_URL   = "https://rmsothebys.com/api/search/SearchLots"
LOT_BASE_URL = "https://rmsothebys.com"
PAGE_SIZE    = 40

# ── Mileage parsing ────────────────────────────────────────────────────────────
# Handles RM collection subtitle formats:
#   "4,952 Miles From New", "Just Under 26,800 km From New",
#   "Just 20.408 km From New"  ← European period-as-thousands separator
_SUBTITLE_MILEAGE_RE = re.compile(
    r'([\d][\d,\.]*)\s*(k)?\s*(miles?|kilometers?|km|mi)\b',
    re.IGNORECASE
)


def parse_mileage_from_subtitle(text: str) -> int | None:
    if not text:
        return None
    m = _SUBTITLE_MILEAGE_RE.search(text)
    if not m:
        return None
    num_str, k_suffix, unit = m.group(1), m.group(2), m.group(3)
    # European period-as-thousands-separator: "20.408" → 20408
    if '.' in num_str and ',' not in num_str:
        parts = num_str.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            num_str = num_str.replace('.', '')
    num_str = num_str.replace(',', '')
    try:
        value = float(num_str)
    except ValueError:
        return None
    if k_suffix:
        value *= 1000
    if unit.lower() in ('km', 'kilometer', 'kilometers'):
        value /= 1.609
    result = round(value)
    return result if result >= 100 else None


# ── Generation lookups (mirror bat_ingest.py) ────────────────────────────────

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


# ── Model / variant parsing ───────────────────────────────────────────────────

YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

# Ordered longest-match first
PORSCHE_MODEL_LINES = [
    ("918 Spyder", "918 Spyder"),
    ("959",         "959"),
    ("Cayenne",     "Cayenne"),
    ("Panamera",    "Panamera"),
    ("Taycan",      "Taycan"),
    ("Boxster",     "Boxster"),
    ("Cayman",      "Cayman"),
    ("968",         "968"),
    ("944",         "944"),
    ("930",         "911"),
    ("928",         "928"),
    ("924",         "924"),
    ("914",         "914"),
    ("912E",        "912"),
    ("912",         "912"),
    ("356",         "356"),
    ("904",         "904"),
    # Race cars — word-boundary matched to avoid year-digit false positives
    ("962",         "962"),
    ("956",         "956"),
    ("935",         "935"),
    ("934",         "934"),
    ("917",         "917"),
    ("908",         "908"),
    ("907",         "907"),
    ("906",         "906"),
    ("Carrera GT",  "Carrera GT"),  # after all numeric models; uses word-boundary match
    ("911",         "911"),
]

_911_VARIANTS = [
    "GT3 RS 4.0", "GT3 RS", "GT3",
    "GT2 RS", "GT2",
    "Turbo S", "Turbo",
    "Sport Classic", "S/T", "Dakar",
    "Speedster", "Targa",
    "RS America", "Carrera RS 3.0", "Carrera RS 2.7", "Carrera RS",
    "Carrera 4S", "Carrera 4", "Carrera S", "Carrera GTS", "Carrera T",
    "Carrera 3.2", "Carrera 2.7",
    "Carrera", "Singer",
    "SC", "911S",
]

_356_VARIANTS  = ["Speedster", "Roadster", "Cabriolet", "Coupe", "Notchback"]
_944_VARIANTS  = ["Turbo S", "Turbo", "S2", "S"]
_924_VARIANTS  = ["Carrera GT", "Carrera GTS", "Turbo"]


def parse_year(text: str) -> int | None:
    m = YEAR_RE.search(text)
    return int(m.group()) if m else None


def parse_model_line(text: str) -> str:
    for token, ml in PORSCHE_MODEL_LINES:
        if token == "Carrera GT":
            if re.search(r'\bCarrera GT\b', text):
                return ml
        elif token[0].isdigit():
            if re.search(r'\b' + re.escape(token) + r'\b', text):
                return ml
        elif token in text:
            return ml
    return "911"


def parse_generation(model_line: str, year: int, text: str) -> str:
    if model_line == "911":
        return get_911_generation(year)
    if model_line == "Cayman":
        return get_cayman_generation(year)
    if model_line == "Boxster":
        return get_boxster_generation(year)
    if model_line == "356":
        if year <= 1955: return "Pre-A"
        if year <= 1959: return "356 A"
        if year <= 1963: return "356 B"
        return "356 C"
    if model_line == "944":
        if "Turbo" in text: return "944 Turbo"
        if "S2" in text:    return "944 S2"
        return "944"
    return model_line


def parse_variant(model_line: str, year: int, text: str) -> str:
    if model_line == "911":
        gen = get_911_generation(year)
        if gen == "G-Body":
            if "Slant Nose" in text:                return "Turbo 3.3 Slant Nose"
            if "MFI" in text:                       return "Carrera 2.7 MFI"
            if "Carrera 2.7" in text:               return "Carrera 2.7"
            if "Carrera RS 3.0" in text:            return "Carrera RS 3.0"
            if "Carrera RS" in text:                return "Carrera RS 2.7"
            if "Speedster" in text:                 return "Speedster"
            if "Turbo" in text or "930" in text:    return "930 Turbo"
            if "Targa" in text:                     return "Targa"
            if "Carrera" in text and year <= 1977:  return "Carrera 2.7"
            if "SC" in text:                        return "SC"
            if "Carrera 3.2" in text or ("Carrera" in text and year >= 1984):
                                                    return "Carrera 3.2"
            if "911S" in text or "911 S" in text:   return "911S"
            return "base"
        if gen == "F-Body":
            if "Carrera RS 2.7" in text or "Carrera RS" in text: return "Carrera RS 2.7"
            if "Carrera 2.7" in text:               return "Carrera 2.7"
            if "911S" in text:                      return "911S"
            if "Targa" in text:                     return "Targa"
            return "base"
        for pat in _911_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line == "356":
        for pat in _356_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line == "944":
        for pat in _944_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line == "924":
        for pat in _924_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line in ("Cayman", "Boxster"):
        for pat in ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]:
            if pat in text:
                return pat
        if re.search(r'\bR\b', text): return "R"
        if re.search(r'\bS\b', text): return "S"
        return "base"

    return "base"


def parse_paint_to_sample(text: str) -> bool | None:
    if re.search(r'paint[-\s]to[-\s]sample|PTS', text, re.IGNORECASE):
        return True
    return None


# ── Price parsing ─────────────────────────────────────────────────────────────

_PRICE_RE = re.compile(r'[\$£€]?([\d,]+)\s*(USD|CAD|EUR|GBP|CHF)?', re.IGNORECASE)


def parse_price_usd(value: str) -> int | None:
    """
    Parse the sold price from RM's value string (e.g. '$1,250,000 USD').
    Returns None if the value is not USD or unparseable.
    Currently only USD lots are stored; add FX conversion here to support others.
    """
    if not value:
        return None
    # Reject estimate ranges (contain " - " or "–")
    if re.search(r'\s[-–]\s', value):
        return None
    currency = "USD"
    if "CAD" in value: currency = "CAD"
    elif "EUR" in value or "€" in value: currency = "EUR"
    elif "GBP" in value or "£" in value: currency = "GBP"
    elif "CHF" in value: currency = "CHF"

    if currency != "USD":
        return None  # skip non-USD; add conversion here if needed

    m = _PRICE_RE.search(value)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


# ── Lot date fetch ────────────────────────────────────────────────────────────

_DATE_RE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"')


def fetch_lot_date(lot_path: str) -> str | None:
    """
    Fetch the lot HTML page and extract datePublished from its JSON-LD block.
    Returns an ISO date string (YYYY-MM-DD) or None on failure.
    """
    url = f"{LOT_BASE_URL}{lot_path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = _DATE_RE.search(html)
        return m.group(1) if m else None
    except Exception:
        return None


# ── Search API fetch ──────────────────────────────────────────────────────────

def fetch_page(page: int) -> tuple[list[dict], int]:
    """Return (items, total_pages) for the given 0-based page."""
    body = json.dumps({
        "LocationCountry": [],
        "OfferStatus":     None,
        "SortBy":          "Availability",
        "CategoryTag":     [],
        "search":          "",
        "make":            "Porsche",
    }).encode()
    url = f"{SEARCH_URL}?page={page}&pageSize={PAGE_SIZE}"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Accept":       "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin":       "https://rmsothebys.com",
        "Referer":      "https://rmsothebys.com/search",
        "User-Agent":   "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
        payload = json.loads(resp.read().decode())
    pager = payload.get("pager", {})
    total_pages = pager.get("totalPages", 0)
    return payload.get("items", []), total_pages


# ── Record mapper ─────────────────────────────────────────────────────────────

def map_record(item: dict, lot_date: str | None) -> dict | None:
    """Map a raw RM Sotheby's search item to an auction_results row dict."""
    if not (item.get("sold") and item.get("auctioned")):
        return None

    title = item.get("publicName") or ""
    year = parse_year(title)
    if not year:
        return None

    sold_price = parse_price_usd(item.get("value") or "")
    if sold_price is None:
        return None

    if lot_date is None:
        return None

    try:
        sold_date = datetime.strptime(lot_date, "%Y-%m-%d").date()
    except ValueError:
        return None

    model_line = parse_model_line(title)
    generation = parse_generation(model_line, year, title)
    variant    = parse_variant(model_line, year, title)

    link = item.get("link") or ""
    lot_url = f"{LOT_BASE_URL}{link}" if link else None

    collection = item.get("collection") or ""
    mileage = parse_mileage_from_subtitle(collection)
    exterior_color = scan_for_color(collection)

    return {
        "make":              "Porsche",
        "model_line":        model_line,
        "generation":        generation,
        "variant":           variant,
        "year":              year,
        "transmission":      "Manual",   # not in API; almost all collector Porsches are manual
        "is_widebody":       None,
        "mileage":           mileage,
        "thumbnail_url":     item.get("crop") or None,
        "sold_price":        sold_price,
        "auction_source":    "RM Sotheby's",
        "auction_url":       lot_url,
        "sold_date":         sold_date,
        "lot_title":         title,
        "exterior_color":    exterior_color,
        "paint_to_sample":   parse_paint_to_sample(title),
        "production_number": None,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

async def ingest() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url).where(
                AuctionResult.auction_url.isnot(None),
                AuctionResult.auction_source == "RM Sotheby's",
            )
        )
        existing: set[str] = {row[0] for row in rows.fetchall()}

    print(f"Existing RM Sotheby's records: {len(existing)}")

    to_insert: list[dict] = []
    total_fetched = total_sold = total_skipped = 0
    page = 0

    while True:
        try:
            items, total_pages = fetch_page(page)
        except Exception as exc:
            print(f"  page {page} ERROR: {exc}")
            break

        if not items:
            break

        total_fetched += len(items)
        sold_items = [i for i in items if i.get("sold") and i.get("auctioned")]
        total_sold += len(sold_items)

        for item in sold_items:
            link = item.get("link") or ""
            lot_url = f"{LOT_BASE_URL}{link}" if link else None

            if lot_url and lot_url in existing:
                total_skipped += 1
                continue

            lot_date = fetch_lot_date(link)
            rec = map_record(item, lot_date)
            time.sleep(0.5)  # be polite when fetching lot pages

            if rec is None:
                total_skipped += 1
                continue

            if lot_url:
                existing.add(lot_url)
            to_insert.append(rec)

        print(
            f"  page {page + 1}/{total_pages} — fetched {len(items)}, "
            f"sold {len(sold_items)}, queued {len(to_insert)} total"
        )

        if page + 1 >= total_pages:
            break
        page += 1
        time.sleep(2)

    async with AsyncSessionLocal() as session:
        if to_insert:
            session.add_all([AuctionResult(**r) for r in to_insert])
            await session.commit()

    print(f"\nDone — fetched: {total_fetched} | sold lots found: {total_sold} | "
          f"inserted: {len(to_insert)} | skipped: {total_skipped}")
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
