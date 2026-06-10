#!/usr/bin/env python3
"""
Ingest real Porsche auction data from the OldCarsData API into auction_results.

Usage (from backend/ directory):
    OCD_API_KEY=<key> python data/ocd_ingest.py

Requires the OCD_API_KEY environment variable. New records are matched on
auction_url — re-running the script will not create duplicates.
"""
import asyncio
import certifi
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import Base
from app.models.listing import AuctionResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BACKEND_DIR, 'pcarmarket.db')}"
engine       = create_async_engine(DATABASE_URL)
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

API_BASE = "https://api.oldcarsdata.com"   # adjust if the base URL differs
API_KEY  = os.environ.get("OCD_API_KEY")


# ── Generation lookup (911 only) ─────────────────────────────────────────────

def get_911_generation(year: int) -> str:
    if year <= 1994: return "964"
    if year <= 1998: return "993"
    if year <= 2001: return "996.1"
    if year <= 2005: return "996.2"
    if year <= 2008: return "997.1"
    if year <= 2012: return "997.2"
    if year <= 2016: return "991.1"
    if year <= 2019: return "991.2"
    return "992"


# ── Transmission normalizer ──────────────────────────────────────────────────

def normalize_transmission(value: str | None) -> str:
    if not value:
        return "manual"
    v = value.lower()
    if "manual" in v:
        return "manual"
    if any(k in v for k in ("pdk", "doppelkupplung", "automatic")):
        return "pdk"
    return "manual"   # default — Porsche GT cars are manual


# ── Variant extractor ────────────────────────────────────────────────────────

def extract_variant(listing_model: str | None) -> str:
    if not listing_model:
        return "Carrera"
    m = listing_model.strip()
    # Most-specific patterns first
    if "GT3 RS 4.0" in m: return "GT3 RS 4.0"
    if "GT3 RS"     in m: return "GT3 RS"
    if "GT3"        in m: return "GT3"
    if "GT2 RS"     in m: return "GT2 RS"
    if "GT2"        in m: return "GT2"
    if "Turbo S"    in m: return "Turbo S"
    if "Turbo"      in m: return "Turbo"
    if "Carrera 4S" in m or "Carrera S" in m: return "Carrera S"
    if "Carrera 4"  in m or "GTS"       in m: return "Carrera GTS"
    if "Carrera T"  in m: return "Carrera T"
    return "Carrera"


# ── Model line lookup ────────────────────────────────────────────────────────

def get_model_line(ocd_model: str, listing_model: str | None) -> str:
    if ocd_model in ("911", "964", "993", "996", "997", "991", "992"):
        return "911"
    if ocd_model == "Boxster":   return "Boxster"
    if ocd_model == "Cayman":    return "Cayman"
    if ocd_model == "718":
        lm = (listing_model or "").lower()
        return "Cayman" if "cayman" in lm else "Boxster"
    if ocd_model == "Carrera GT": return "Carrera GT"
    if ocd_model == "918 Spyder": return "918 Spyder"
    if ocd_model == "959":        return "959"
    return "911"


# ── API fetch ────────────────────────────────────────────────────────────────

def fetch_ocd(make: str, model: str, status: str = "sold", limit: int = 20) -> list[dict]:
    if not API_KEY:
        raise RuntimeError("OCD_API_KEY environment variable is not set")
    params = urllib.parse.urlencode({
        "make":   make,
        "model":  model,
        "status": status,
        "limit":  limit,
    })
    url = f"{API_BASE}/auctions?{params}"
    req = urllib.request.Request(url, headers={
        "Accept":        "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent":    "Mozilla/5.0",
    })
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        payload = json.loads(resp.read().decode())
    # Unwrap common envelope shapes
    if isinstance(payload, list):
        return payload
    for key in ("results", "data", "auctions", "items"):
        if key in payload and isinstance(payload[key], list):
            return payload[key]
    return []


# ── Record mapper ────────────────────────────────────────────────────────────

def map_record(raw: dict) -> dict | None:
    if raw.get("auction_status") != "sold":
        return None

    price = raw.get("price") or raw.get("sold_price") or raw.get("sale_price")
    if price is None:
        return None

    year = raw.get("year") or raw.get("model_year")
    if not year:
        return None
    year = int(year)

    ocd_model     = str(raw.get("model") or "")
    listing_model = str(raw.get("listing_model") or raw.get("model_trim") or "")

    model_line   = get_model_line(ocd_model, listing_model)
    generation   = get_911_generation(year) if model_line == "911" else ocd_model
    variant      = extract_variant(listing_model)
    transmission = normalize_transmission(
        raw.get("transmission") or raw.get("gearbox")
    )

    sold_date_raw = (
        raw.get("sold_date") or raw.get("auction_date") or raw.get("date")
    )
    try:
        sold_date = datetime.strptime(str(sold_date_raw)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        sold_date = date.today()

    return dict(
        make              = "Porsche",
        model_line        = model_line,
        generation        = generation,
        variant           = variant,
        year              = year,
        transmission      = transmission,
        mileage           = raw.get("mileage") or raw.get("odometer"),
        color             = raw.get("color") or raw.get("exterior_color"),
        sold_price        = int(price),
        auction_source    = raw.get("source") or raw.get("auction_house") or "OldCarsData",
        auction_url       = raw.get("url") or raw.get("listing_url") or raw.get("auction_url"),
        sold_date         = sold_date,
        lot_title         = raw.get("title") or raw.get("listing_title"),
        paint_to_sample   = None,
        production_number = None,
    )


# ── Queries to run ───────────────────────────────────────────────────────────

QUERIES = [
    dict(make="Porsche", model="997", status="sold", limit=20),
    dict(make="Porsche", model="993", status="sold", limit=20),
    dict(make="Porsche", model="964", status="sold", limit=20),
]


# ── Main ─────────────────────────────────────────────────────────────────────

async def ingest() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load existing auction URLs so we can skip duplicates without a schema change
    async with AsyncSession() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url).where(
                AuctionResult.auction_url.isnot(None)
            )
        )
        existing_urls: set[str] = {row[0] for row in rows.fetchall()}

    total_fetched = total_inserted = total_skipped_status = total_skipped_dup = 0
    to_insert: list[dict] = []

    for q in QUERIES:
        label = f"make={q['make']} model={q['model']} limit={q['limit']}"
        print(f"Fetching {label} …")
        try:
            raw_list = fetch_ocd(**q)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue

        total_fetched += len(raw_list)
        batch_inserted = batch_skipped = 0

        for raw in raw_list:
            rec = map_record(raw)
            if rec is None:
                total_skipped_status += 1
                batch_skipped += 1
                continue
            url = rec.get("auction_url")
            if url and url in existing_urls:
                total_skipped_dup += 1
                batch_skipped += 1
                continue
            if url:
                existing_urls.add(url)
            to_insert.append(rec)
            batch_inserted += 1

        print(f"  → {batch_inserted} queued, {batch_skipped} skipped")

    if to_insert:
        async with AsyncSession() as session:
            session.add_all([AuctionResult(**r) for r in to_insert])
            await session.commit()
        total_inserted = len(to_insert)

    print(
        f"\nSummary — fetched: {total_fetched} | inserted: {total_inserted} | "
        f"skipped (not sold / no price): {total_skipped_status} | "
        f"skipped (duplicate URL): {total_skipped_dup}"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
