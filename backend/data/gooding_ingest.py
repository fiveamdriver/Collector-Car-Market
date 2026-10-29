#!/usr/bin/env python3
"""
Ingest Porsche auction data from Gooding & Company's GraphQL API.

Usage (from backend/ directory):
    python data/gooding_ingest.py

No API key or authentication required. Re-running is safe — duplicates are
skipped by auction_url.
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
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from app.utils.color_parser import parse_color_from_phrase, scan_for_color
from app.utils.transaxle import TRANSAXLE_LINES, classify as classify_transaxle
from app.utils.transaxle import match_model_line as match_transaxle_line
from app.utils.model_lines import match_model_line as match_model_line_shared
from app.utils.variants import match_variant, is_964_rs_38, is_boxster_rs60, fix_964_carrera, strip_turbo_impostor, is_not_a_car, cabriolet_variant, resolve_911_base, parse_356_variant
from app.utils.generations import (
    get_911_generation,
    get_boxster_generation,
    get_cayman_generation,
)
from sqlalchemy import select

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

GRAPHQL_URL   = "https://cdn.goodingco.com/graphql"
LOT_BASE_URL  = "https://www.goodingco.com/lot/"
PAGE_DATA_URL = "https://www.goodingco.com/page-data/lot/"
CDN_BASE      = "https://res.cloudinary.com/goodingco/image/upload/"
HITS_PER_PAGE = 15

# The site's own client uses Apollo automatic persisted queries — it sends only a
# sha256 of the query document.  We sent that hash too, until a Gooding redeploy
# rotated it and every request came back PersistedQueryNotFound.  The server also
# accepts a plain inline query, so we send the document itself and the hash can
# never go stale again.
#
# This is a trimmed version of the site's GetVehiclesAndFilters query: only the
# fields map_record() consumes, plus the paging counts.  Requesting less means
# fewer fields that can be renamed out from under us, and a rename now fails
# loudly with a GraphQL validation error naming the field.
#
# Note the site's own copy carries an `@connection(...)` directive.  That is an
# Apollo *client* directive which the client strips before sending; leaving it in
# gets the request rejected with `Unknown directive "@connection"`.
QUERY_DOCUMENT = """query GetVehiclesAndFilters($filtersInput: FiltersInput!, $pageNumber: Int, $sortBy: SortBy!) {
  getVehicles(filtersInput: $filtersInput, pageNumber: $pageNumber, sortBy: $sortBy) {
    vehicles {
      modelYear
      title
      model
      slug
      salePrice
      activeAuction
      auctionName
      auctionEndDate
      cloudinaryImages { public_id }
    }
    nbPages
    nbHits
  }
}"""

# ── Mileage + color parsing from page-data.json highlights ────────────────────
_SUBTITLE_MILEAGE_RE = re.compile(
    r'([\d][\d,\.]*)\s*(k)?\s*(miles?|kilometers?|km|mi)\b',
    re.IGNORECASE
)
# Matches "Finished in [Very Rare / Original Color of] X over Y"
_FINISHED_IN_RE = re.compile(
    r'\bfinished in\b\s+(?:very rare\s+|original colou?rs?\s+of\s+)?(.+?)(?:\s+over\b|\s+with\b|,|$)',
    re.IGNORECASE
)


def fetch_lot_highlights(slug: str) -> list[str] | None:
    """Fetch Gatsby page-data.json for a lot and return its highlights list."""
    url = f"{PAGE_DATA_URL}{slug}/page-data.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        item = data["result"]["data"]["contentfulLot"]["item"]
        return item.get("highlights") or []
    except Exception:
        return None


def _parse_mileage_from_text(text: str) -> int | None:
    m = _SUBTITLE_MILEAGE_RE.search(text)
    if not m:
        return None
    num_str, k_suffix, unit = m.group(1), m.group(2), m.group(3)
    # European period-as-thousands: "20.408" → 20408
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


def parse_mileage_from_highlights(highlights: list[str]) -> int | None:
    for h in highlights:
        m = _parse_mileage_from_text(h)
        if m is not None:
            return m
    return None


def parse_color_from_highlights(highlights: list[str]) -> str | None:
    for h in highlights:
        fm = _FINISHED_IN_RE.search(h)
        if fm:
            return parse_color_from_phrase(fm.group(1).strip())
    return None


# ── Model / variant parsing ───────────────────────────────────────────────────

# Ordered longest-match first to avoid partial collisions (e.g. "930" before "911")

_356_VARIANTS = ["Speedster", "Roadster", "Cabriolet", "Coupe", "Notchback"]

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
    return model_line  # 912, 914, 924, 928, 968, 959, Carrera GT, 918 Spyder, etc.


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
            if "Slant Nose" in text:           return "Turbo 3.3 Slant Nose"
            if "MFI" in text:                  return "Carrera 2.7 MFI"
            if "Carrera 2.7" in text:          return "Carrera 2.7"
            if "Carrera RS 3.0" in text:       return "Carrera RS 3.0"
            if "Carrera RS" in text:           return "Carrera RS 2.7"
            if "Speedster" in text:            return "Speedster"
            if "Turbo" in text or "930" in text: return "930 Turbo"
            if "Targa" in text:                return "Targa"
            if "Carrera" in text and year <= 1977: return "Carrera 2.7"
            if "SC" in text:                   return "SC"
            if "Carrera 3.2" in text or ("Carrera" in text and year >= 1984):
                                               return "Carrera 3.2"
            if re.search(r'\b911\s*(?:2\.\d\s*)?S\b', text): return "911S"
            # The taxonomy's entry-level card for these generations is "911",
            # not "base" — a plain "1966 Porsche 911 Coupe" has no card under
            # "base" and renders nowhere.
            return "911"
        if gen == "F-Body":
            if "Carrera RS 2.7" in text or "Carrera RS" in text: return "Carrera RS 2.7"
            if "Carrera 2.7" in text:          return "Carrera 2.7"
            if "Targa" in text:                return "Targa"
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
            if pat in text:
                return pat
        return "base"

    if model_line == "924":
        for pat in _924_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line in ("Cayman", "Boxster"):
        if model_line == "Boxster" and is_boxster_rs60(text):
            return "RS 60 Spyder"
        for pat in ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]:
            if pat in text:
                return pat
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


def parse_paint_to_sample(text: str) -> bool | None:
    if re.search(r'paint[-\s]to[-\s]sample|PTS', text, re.IGNORECASE):
        return True
    return None


# ── GraphQL fetch ─────────────────────────────────────────────────────────────

def fetch_page(page_number: int, attempts: int = 3) -> tuple[list[dict], int]:
    """
    Return (vehicles, nb_pages) for the given 1-based page number.

    We deliberately do not send hitsPerPage.  The server's default of 15 pages
    cleanly to an empty tail page, whereas larger sizes make the final page 500
    with an internal "Cannot read properties of undefined (reading 'make')" —
    nbHits (934) overcounts the rows the backend can actually serve (~919).

    Retries transient failures; raises once attempts are exhausted so that a
    mid-run failure is reported rather than silently truncating the ingest.
    """
    variables = {
        "filtersInput": {"make": ["Porsche"], "auctionType": [], "itemType": [], "venue": [], "auctionYear": []},
        "sortBy": "ENDING_SOONEST",
        "pageNumber": page_number,
    }
    body = json.dumps({
        "operationName": "GetVehiclesAndFilters",
        "variables":     variables,
        "query":         QUERY_DOCUMENT,
    }).encode()
    req = urllib.request.Request(GRAPHQL_URL, data=body, headers={
        "Accept":        "*/*",
        "Authorization": "Bearer",
        "Content-Type":  "application/json",
        "Origin":        "https://www.goodingco.com",
        "User-Agent":    "Mozilla/5.0",
    })

    last_error = "unknown error"
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
                payload = json.loads(resp.read().decode())
            gv = (payload.get("data") or {}).get("getVehicles")
            if gv:
                return gv["vehicles"], gv["nbPages"]
            last_error = json.dumps(payload.get("errors"))[:300]
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"
        except Exception as exc:  # noqa: BLE001 — network/JSON, retry then surface
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < attempts - 1:
            time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"page {page_number} failed after {attempts} attempts — {last_error}")


# ── Record mapper ─────────────────────────────────────────────────────────────

def map_record(v: dict, highlights: list[str] | None = None) -> dict | None:
    """Map a Gooding vehicle object to an auction_results row dict."""
    # Only completed, sold lots
    if v.get("activeAuction") != "false":
        return None
    sale_price_raw = v.get("salePrice") or ""
    if not sale_price_raw or sale_price_raw == "0":
        return None

    try:
        sold_price = int(float(sale_price_raw.replace(",", "")))
    except (ValueError, TypeError):
        return None
    if sold_price <= 0:
        return None

    year = v.get("modelYear")
    if not year:
        return None
    year = int(year)

    title = v.get("title") or ""
    model = v.get("model") or ""
    search_text = f"{title} {model}"

    model_line  = parse_model_line(search_text)
    generation  = parse_generation(model_line, year, search_text)
    variant     = parse_variant(model_line, year, search_text)
    if model_line in TRANSAXLE_LINES:
        model_line, variant = classify_transaxle(model_line, search_text)
        generation = model_line

    # Auction date from millisecond timestamp
    end_ts = v.get("auctionEndDate")
    if not end_ts:
        return None
    try:
        sold_date = datetime.fromtimestamp(int(end_ts) / 1000).date()
    except (ValueError, OSError):
        return None

    # Thumbnail: first cloudinary image
    thumb = None
    images = v.get("cloudinaryImages") or []
    if images:
        pid = images[0].get("public_id") or ""
        if pid:
            thumb = f"{CDN_BASE}{urllib.parse.quote(pid, safe='/')}.jpg"

    slug = v.get("slug") or ""
    lot_url = f"{LOT_BASE_URL}{slug}/" if slug else None

    return {
        "make":              "Porsche",
        "model_line":        model_line,
        "generation":        generation,
        "variant":           variant,
        "year":              year,
        "transmission":      "Manual",   # not in API; almost all collector Porsches are manual
        "is_widebody":       None,
        "mileage":           parse_mileage_from_highlights(highlights or []),
        "thumbnail_url":     thumb,
        "sold_price":        sold_price,
        "auction_source":    "Gooding & Company",
        "auction_url":       lot_url,
        "sold_date":         sold_date,
        "lot_title":         title,
        "exterior_color":    parse_color_from_highlights(highlights or []),
        "paint_to_sample":   parse_paint_to_sample(search_text),
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
                AuctionResult.auction_source == "Gooding & Company",
            )
        )
        existing: set[str] = {row[0] for row in rows.fetchall()}

    print(f"Existing Gooding records: {len(existing)}")

    pending: list[dict] = []
    total_fetched = total_skipped = total_inserted = 0
    page = 1

    async def flush() -> None:
        """Commit the queued rows through a short-lived session."""
        nonlocal pending, total_inserted
        if not pending:
            return
        async with AsyncSessionLocal() as session:
            session.add_all([AuctionResult(**r) for r in pending])
            await session.commit()
        total_inserted += len(pending)
        pending = []

    while True:
        try:
            vehicles, nb_pages = fetch_page(page)
        except Exception as exc:
            print(f"  page {page} ERROR: {exc}", flush=True)
            break

        if not vehicles:
            break

        total_fetched += len(vehicles)
        for v in vehicles:
            slug = v.get("slug") or ""

            # Check the URL before fetching highlights, not after. Highlights
            # cost one HTTP request per lot and are the slowest part of the run;
            # fetching them for a lot we already hold means ~900 requests to
            # build records that are then thrown away on a re-ingest.
            url = f"{LOT_BASE_URL}{slug}/" if slug else None
            if url and url in existing:
                total_skipped += 1
                continue

            highlights = fetch_lot_highlights(slug) if slug else None
            rec = map_record(v, highlights=highlights)
            if rec is None:
                total_skipped += 1
                continue
            if url:
                existing.add(url)
            pending.append(rec)

        # Commit as we go. The previous version held everything in memory and
        # committed once at the end, so a stall on the final commit discarded the
        # whole run — 48 minutes of fetching, zero rows written. Committing per
        # page also keeps pooled connections from sitting idle for the length of
        # the crawl, which is what killed that connection in the first place.
        await flush()

        print(f"  page {page}/{nb_pages} — fetched {len(vehicles)}, "
              f"inserted {total_inserted} total", flush=True)

        if page >= nb_pages:
            break
        page += 1
        time.sleep(1)

    await flush()

    print(f"\nDone — fetched: {total_fetched} | inserted: {total_inserted} | "
          f"skipped: {total_skipped}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
