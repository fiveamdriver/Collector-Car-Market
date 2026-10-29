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
import html
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
from app.utils.transaxle import TRANSAXLE_LINES, classify as classify_transaxle
from app.utils.transaxle import match_model_line as match_transaxle_line
from app.utils.model_lines import match_model_line as match_model_line_shared
from app.utils.variants import match_variant, is_964_rs_38, is_boxster_rs60, fix_964_carrera, strip_turbo_impostor, is_not_a_car, cabriolet_variant, resolve_911_base, parse_356_variant
from app.utils.generations import (
    get_911_generation,
    get_boxster_generation,
    get_cayman_generation,
)
from playwright.async_api import async_playwright
from sqlalchemy import select

RESULTS_BASE = "https://www.broadarrowauctions.com/vehicles/results"
PAGE_SIZE    = 50

# ── Auction event code → sold date ────────────────────────────────────────────
# The event code is the first segment of the lot URL slug:
#   /vehicles/am26_r0191/... → "am26"
#
# Regenerate this table with `python data/broad_arrow_events.py`, which joins the
# event listings (name + date) to each event's lots (code) and prints a ready-to-
# paste block.  Run it before each new auction season.
#
# Dates are the first day of a multi-day event.  Only three codes used to be
# listed here and everything else silently fell back to January 1 of the code's
# year — 396 of 478 stored rows (83%) carried that fabricated date, which is why
# the table is now exhaustive and the fallback returns None instead.
AUCTION_EVENTS: dict[str, date] = {
    "jc22":  date(2022,  8, 18),  # Monterey Jet Center 2022
    "tj22":  date(2022, 10, 14),  # Passion for the Drive: The Cars of Jim Taylor
    "pb22":  date(2022, 11, 18),  # West Palm Beach
    "am23":  date(2023,  3,  4),  # The Amelia Auction 2023
    "po23":  date(2023,  6,  1),  # Porsche 75th Anniversary Auction
    "jc23":  date(2023,  8, 17),  # Monterey Jet Center 2023
    "am24":  date(2024,  3,  1),  # The Amelia Auction 2024
    "po24":  date(2024,  4, 27),  # The Porsche Air|Water Auction
    "jc24":  date(2024,  8, 14),  # Monterey Jet Center 2024
    "ch24":  date(2024, 10, 12),  # The Chattanooga Auction 2024
    "sf25":  date(2025,  2, 15),  # The Academy of Art University Collection
    "am25":  date(2025,  3,  7),  # The Amelia Auction 2025
    "po25":  date(2025,  4, 26),  # The Porsche Air|Water Auction 2025
    "ve25":  date(2025,  5, 24),  # Concorso d'Eleganza Villa d'Este 2025
    "jc25":  date(2025,  8, 13),  # Monterey Jet Center 2025
    "zt25":  date(2025, 10, 10),  # Zoute Concours Auction 2025
    "lv25":  date(2025, 10, 31),  # The Las Vegas Auction 2025
    "dg25":  date(2025, 11,  1),  # The Zurich Auction 2025 (Dolder Grand)
    "gi26e": date(2026,  1, 23),  # Global Icons: Europe Online
    "gi26u": date(2026,  1, 23),  # Global Icons: UK Online
    "am26":  date(2026,  3,  6),  # The Amelia Auction 2026
    "cm26":  date(2026,  4, 21),  # California Mille: A Unique Opportunity
    "po26":  date(2026,  4, 25),  # The Porsche Air|Water Auction 2026
    "gi26v": date(2026,  5, 11),  # Global Icons: Spring Online Auction 2026
    "ve26":  date(2026,  5, 16),  # Concorso d'Eleganza Villa d'Este 2026
    "mb26":  date(2026,  8, 10),  # Global Icons: The Patina Collective
    "ql26":  date(2026,  8, 13),  # The Quail Auction 2026
    "ad26":  date(2026, 10,  2),  # The Audrain Auction 2026
    "gi26z": date(2026, 10,  5),  # Global Icons: Zoute Online 2026
    "zt26":  date(2026, 10,  9),  # The Zoute Concours Auction 2026
    "dg26":  date(2026, 11,  7),  # The Zurich Auction 2026 (Dolder Grand)
}

# Non-USD events: event_code → USD conversion rate (local_price × rate = USD)
# Schema.org hardcodes priceCurrency="USD" even for EUR/GBP/CHF auctions.
# Rates are approximate mid-market for the auction period.
#
# Every non-USD event needs an entry: a code that is missing here is not flagged,
# it is silently treated as already-USD, so a €500k lot is stored as $500k.  Keep
# this in step with AUCTION_EVENTS whenever a European sale is added.
NON_USD_RATES: dict[str, float] = {
    "ve25":  1.11,   # Villa d'Este 2025 (EUR)
    "ve26":  1.13,   # Villa d'Este 2026 (EUR)
    "zt25":  1.09,   # Zoute Concours 2025 (EUR, Belgium)
    "zt26":  1.13,   # Zoute Concours 2026 (EUR, Belgium)
    "gi26e": 1.12,   # Global Icons: Europe Online (EUR)
    "gi26v": 1.12,   # Global Icons: Spring Online 2026 (EUR)
    "gi26z": 1.13,   # Global Icons: Zoute Online 2026 (EUR)
    "gi26u": 1.28,   # Global Icons: UK Online (GBP)
    "dg25":  1.11,   # Zurich Auction 2025 (CHF)
    "dg26":  1.13,   # Zurich Auction 2026 (CHF)
}

# The trailing letter is not optional decoration: the Global Icons sales encode
# their region there (gi26e / gi26u / gi26v).  Without it the pattern failed to
# match those slugs at all, so 114 lots resolved to no event code and no date.
_EVENT_CODE_RE  = re.compile(r'/vehicles/([a-z]{2,4}\d{2}[a-z]?)_', re.IGNORECASE)


def extract_event_code(url: str) -> str | None:
    m = _EVENT_CODE_RE.search(url)
    return m.group(1).lower() if m else None


def event_date(code: str | None) -> date | None:
    """
    Resolve an event code to the auction's start date, or None if unknown.

    An unknown code used to fall back to January 1 of the code's year.  That is
    worse than no date: a fabricated January 1 is indistinguishable from a real
    sale date downstream, and it dragged every affected lot to the wrong end of
    the price-history time series.  Unknown codes now return None and are
    reported at the end of the run so the table can be extended.
    """
    if not code:
        return None
    return AUCTION_EVENTS.get(code)


# ── Model / variant parsing ───────────────────────────────────────────────────

YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')


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
    # Last: a bare "R" must only win when no longer name matched.
    "R",
]

_356_VARIANTS = ["Speedster", "Roadster", "Cabriolet", "Coupe", "Notchback"]
_944_VARIANTS = ["Turbo S", "Turbo", "S2", "S"]
_924_VARIANTS = ["Carrera GT", "Carrera GTS", "Turbo"]


def parse_model_line(text: str) -> str:
    if is_not_a_car(text):
        return "Other"  # engines, parts, memorabilia — see app/utils/variants.py
    return match_model_line_shared(text, match_transaxle_line)


def parse_generation(model_line: str, year: int, text: str) -> str:
    if model_line == "911":
        return get_911_generation(year, text)
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


def _parse_variant_raw(model_line: str, year: int, text: str) -> str:
    if model_line == "914":
        return "914/6" if re.search(r'914[/-]6', text) else "base"
    if model_line == "911":
        gen = get_911_generation(year, text)
        text = strip_turbo_impostor(text)
        # Before the variant list, which stops at "Carrera RS" and would file the
        # 964's separate RS 3.8 card onto the 3.6-litre one.
        if gen == "964" and is_964_rs_38(text):
            return "RS 3.8"
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
            if re.search(r'\b911\s*(?:2\.\d\s*)?S\b', text): return "911S"
            # The taxonomy's entry-level card for these generations is "911",
            # not "base" — a plain "1966 Porsche 911 Coupe" has no card under
            # "base" and renders nowhere.
            return "911"
        if gen == "F-Body":
            if "Carrera RS 2.7" in text or "Carrera RS" in text: return "Carrera RS 2.7"
            if "Carrera 2.7" in text:               return "Carrera 2.7"
            if "Targa" in text:                     return "Targa"
            if re.search(r'\b911\s*(?:2\.\d\s*)?S\b', text): return "911S"
            # The taxonomy's entry-level card for these generations is "911",
            # not "base" — a plain "1966 Porsche 911 Coupe" has no card under
            # "base" and renders nowhere.
            return "911"
        variant = match_variant(_911_VARIANTS, text)
        return fix_964_carrera(variant, text) if gen == "964" else variant

    if model_line == "356":
        return parse_356_variant(text)

    if model_line == "944":
        for pat in _944_VARIANTS:
            if pat in text: return pat
        return "base"

    if model_line == "924":
        for pat in _924_VARIANTS:
            if pat in text: return pat
        return "base"

    if model_line in ("Cayman", "Boxster"):
        if model_line == "Boxster" and is_boxster_rs60(text):
            return "RS 60 Spyder"
        for pat in ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]:
            if pat in text: return pat
        if re.search(r'\bR\b', text): return "R"
        if re.search(r'\bS\b', text): return "S"
        return "base"

    return "base"


def parse_variant(model_line: str, year: int, text: str) -> str:
    variant = _parse_variant_raw(model_line, year, text)
    if model_line == "911":
        # One Cabriolet card per generation, 2WD and 4WD together.
        if variant == "base":
            variant = resolve_911_base(parse_generation(model_line, year, text), text)
        variant = cabriolet_variant(parse_generation(model_line, year, text), variant, text)
    return variant


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

    # Title. The JSON-LD carries HTML-escaped text, so "911 Turbo S &quot;Package&quot;"
    # would otherwise be stored — and displayed — with the entities intact.
    model_name = html.unescape(schema.get("model") or "")
    title      = f"{year} Porsche {model_name}".strip()

    model_line = parse_model_line(title)
    generation = parse_generation(model_line, year, title)
    variant    = parse_variant(model_line, year, title)
    if model_line in TRANSAXLE_LINES:
        model_line, variant = classify_transaxle(model_line, title)
        generation = model_line

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
        print(f"\nWARNING: {len(unknown_events)} unknown event code(s) — those lots "
              f"were stored with sold_date = NULL and will not appear in any price "
              f"history: {sorted(unknown_events)}")
        print("  Run `python data/broad_arrow_events.py` to regenerate AUCTION_EVENTS,")
        print("  then `python data/migrate_broad_arrow_dates.py --apply` to date the")
        print("  affected rows — re-running this ingest will not, it skips known URLs.")

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
