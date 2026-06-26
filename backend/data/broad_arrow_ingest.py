#!/usr/bin/env python3
"""
Ingest Porsche auction results from Broad Arrow Auctions.

Uses Playwright (headless Chromium) to bypass the AWS WAF JavaScript challenge.
Data is extracted from Schema.org JSON-LD embedded in server-rendered results pages.

Usage (from backend/ directory):
    python data/broad_arrow_ingest.py

Re-running is safe — duplicates are skipped by auction_url.

Price encoding: Schema.org offers.price ÷ 10 = USD  (e.g. "67150000" → $6,715,000)
Mileage:       already in miles (Schema.org unitCode "SMI")
Color:         not in Schema.org — run migrate_broad_arrow_color.py afterward.

Before each new auction season, verify AUCTION_EVENTS below and add new entries.
Unknown event codes are logged as warnings; those records get sold_date = NULL.
"""
import asyncio
import os
import re
import sys
from datetime import date

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from playwright.async_api import async_playwright
from sqlalchemy import select

RESULTS_BASE = "https://www.broadarrowauctions.com/vehicles/results"
PAGE_SIZE    = 50

# ── Auction event code → sold date ────────────────────────────────────────────
# The event code is the first segment of the lot URL slug:
#   /vehicles/am26_r0191/... → "am26"
# Check https://www.broadarrowauctions.com/auctions to look up event dates.
# Dates are approximate (first day of the auction event).
AUCTION_EVENTS: dict[str, date] = {
    "am24": date(2024, 3,  1),   # The Amelia Auction 2024
    "am25": date(2025, 3,  7),   # The Amelia Auction 2025
    "am26": date(2026, 3,  7),   # The Amelia Auction 2026
}

# Non-USD events: event_code → USD conversion rate (local_price × rate = USD)
# Schema.org hardcodes priceCurrency="USD" even for EUR/GBP/CHF auctions.
# Rates are approximate mid-market for the auction period.
NON_USD_RATES: dict[str, float] = {
    "ve24":  1.08,   # Villa d'Este 2024 (EUR)
    "ve25":  1.11,   # Villa d'Este 2025 (EUR)
    "ve26":  1.13,   # Villa d'Este 2026 (EUR)
    "zt25":  1.09,   # Zoute Concours 2025 (EUR, Belgium)
    "gi26e": 1.12,   # Global Icons: Europe Online (EUR)
    "gi26v": 1.12,   # Global Icons: Spring Online 2026 (EUR)
    "gi26u": 1.28,   # Global Icons: UK Online (GBP)
    "dg25":  1.11,   # Zurich Auction 2025 (CHF)
}

_EVENT_CODE_RE  = re.compile(r'/vehicles/([a-z]{2,4}\d{2})_', re.IGNORECASE)
_EVENT_YEAR_RE  = re.compile(r'(\d{2})$')


def extract_event_code(url: str) -> str | None:
    m = _EVENT_CODE_RE.search(url)
    return m.group(1).lower() if m else None


def event_date(code: str | None) -> date | None:
    if not code:
        return None
    if code in AUCTION_EVENTS:
        return AUCTION_EVENTS[code]
    # Fallback: derive year from last two digits of code (e.g. "po25" → 2025-01-01)
    m = _EVENT_YEAR_RE.search(code)
    if m:
        return date(2000 + int(m.group(1)), 1, 1)
    return None


# ── Generation helpers ────────────────────────────────────────────────────────

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
    ("962",         "962"),
    ("956",         "956"),
    ("935",         "935"),
    ("934",         "934"),
    ("917",         "917"),
    ("908",         "908"),
    ("907",         "907"),
    ("906",         "906"),
    ("Carrera GT",  "Carrera GT"),
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

_356_VARIANTS = ["Speedster", "Roadster", "Cabriolet", "Coupe", "Notchback"]
_944_VARIANTS = ["Turbo S", "Turbo", "S2", "S"]
_924_VARIANTS = ["Carrera GT", "Carrera GTS", "Turbo"]


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
            if pat in text: return pat
        return "base"

    if model_line == "944":
        for pat in _944_VARIANTS:
            if pat in text: return pat
        return "base"

    if model_line == "924":
        for pat in _924_VARIANTS:
            if pat in text: return pat
        return "base"

    if model_line in ("Cayman", "Boxster"):
        for pat in ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]:
            if pat in text: return pat
        if re.search(r'\bR\b', text): return "R"
        if re.search(r'\bS\b', text): return "S"
        return "base"

    return "base"


# ── Schema.org car mapper ─────────────────────────────────────────────────────

def map_schema_car(schema: dict) -> dict | None:
    lot_url = schema.get("url") or ""
    if not lot_url:
        return None

    # Only Porsche — the makes= URL param is client-side; Schema.org includes all makes
    manufacturer = (schema.get("manufacturer") or "").lower()
    if "porsche" not in manufacturer:
        return None

    # Price: raw integer ÷ 10 = local currency amount
    # Apply FX conversion for non-USD events (Schema.org always says "USD" — unreliable)
    offers     = schema.get("offers") or {}
    price_raw  = offers.get("price")
    if not price_raw:
        return None
    try:
        local_price = int(str(price_raw).replace(",", "")) // 10
    except (ValueError, TypeError):
        return None
    if local_price <= 0:
        return None
    event_code_for_price = extract_event_code(lot_url)
    fx_rate    = NON_USD_RATES.get(event_code_for_price or "", 1.0)
    sold_price = round(local_price * fx_rate)

    # Mileage (already in miles from Schema.org unitCode "SMI")
    odo        = schema.get("mileageFromOdometer") or {}
    mileage_v  = odo.get("value")
    unit_code  = (odo.get("unitCode") or "").upper()
    mileage    = None
    if mileage_v:
        try:
            mileage = int(float(str(mileage_v)))
            if unit_code == "KMT":
                mileage = round(mileage / 1.609)
            mileage = mileage if mileage >= 100 else None
        except (ValueError, TypeError):
            mileage = None

    # Year
    year_str = schema.get("vehicleModelDate") or ""
    try:
        year = int(str(year_str)[:4])
    except (ValueError, TypeError):
        return None
    if year < 1948 or year > 2030:
        return None

    # Title
    model_name = schema.get("model") or ""
    title      = f"{year} Porsche {model_name}".strip()

    model_line = parse_model_line(title)
    generation = parse_generation(model_line, year, title)
    variant    = parse_variant(model_line, year, title)

    # Thumbnail (CDN URL for 1st image)
    thumbnail  = schema.get("image") or None

    # Date from event code
    event_code = extract_event_code(lot_url)
    sold_date  = event_date(event_code)

    return {
        "make":              "Porsche",
        "model_line":        model_line,
        "generation":        generation,
        "variant":           variant,
        "year":              year,
        "transmission":      "Manual",
        "is_widebody":       None,
        "mileage":           mileage,
        "thumbnail_url":     thumbnail,
        "sold_price":        sold_price,
        "auction_source":    "Broad Arrow",
        "auction_url":       lot_url,
        "sold_date":         sold_date,
        "lot_title":         title,
        "exterior_color":    None,     # backfilled by migrate_broad_arrow_color.py
        "paint_to_sample":   None,     # backfilled by migrate_broad_arrow_color.py
        "production_number": None,
    }


# ── Playwright page fetch ─────────────────────────────────────────────────────

async def fetch_results_page(page, page_num: int) -> list[dict]:
    url = f"{RESULTS_BASE}?makes=Porsche&per_page={PAGE_SIZE}&page={page_num}"
    await page.goto(url, wait_until="networkidle", timeout=60_000)
    schemas = await page.evaluate("""() =>
        Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
            .map(s => { try { return JSON.parse(s.textContent) } catch(e) { return null } })
            .filter(s => s && s['@type'] === 'Car')
    """)
    return schemas or []


# ── Main ──────────────────────────────────────────────────────────────────────

async def ingest() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url).where(
                AuctionResult.auction_url.isnot(None),
                AuctionResult.auction_source == "Broad Arrow",
            )
        )
        existing: set[str] = {row[0] for row in rows.fetchall()}

    print(f"Existing Broad Arrow records: {len(existing)}")

    to_insert:      list[dict] = []
    unknown_events: set[str]   = set()
    total_seen = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        page_num = 1
        while True:
            try:
                schemas = await fetch_results_page(page, page_num)
            except Exception as exc:
                print(f"  page {page_num} ERROR: {exc}")
                break

            if not schemas:
                break

            total_seen += len(schemas)

            for schema in schemas:
                lot_url = schema.get("url") or ""

                if lot_url and lot_url in existing:
                    continue

                code = extract_event_code(lot_url)
                if code and code not in AUCTION_EVENTS:
                    unknown_events.add(code)

                rec = map_schema_car(schema)
                if rec is None:
                    continue

                if lot_url:
                    existing.add(lot_url)
                to_insert.append(rec)

            print(
                f"  page {page_num} — {len(schemas)} cars seen, "
                f"{len(to_insert)} queued total"
            )
            page_num += 1
            await asyncio.sleep(1.5)

        await browser.close()

    if unknown_events:
        print(f"\nWARNING: unknown event codes (sold_date set by year fallback): "
              f"{sorted(unknown_events)}")
        print("  Add exact dates to AUCTION_EVENTS for better accuracy.")

    async with AsyncSessionLocal() as session:
        if to_insert:
            session.add_all([AuctionResult(**r) for r in to_insert])
            await session.commit()

    print(
        f"\nDone — pages: {page_num - 1} | cars seen: {total_seen} | "
        f"inserted: {len(to_insert)} | skipped (existing): "
        f"{total_seen - len(to_insert)}"
    )
    print(f"Database: {DATABASE_PATH}")
    print("Run migrate_broad_arrow_color.py to backfill color and PTS data.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
