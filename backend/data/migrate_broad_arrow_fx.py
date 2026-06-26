#!/usr/bin/env python3
"""
Convert Broad Arrow non-USD sold_prices to USD.

Broad Arrow's Schema.org data hardcodes priceCurrency="USD" even for
European auctions. Prices for European events are in local currency
(EUR, GBP, CHF) and must be converted to USD for consistency.

Identified non-USD events (from inspecting actual lot pages):
  EUR: ve25 (Villa d'Este 2025), ve26 (Villa d'Este 2026),
       zt25 (Zoute Concours 2025), gi26e (Global Icons: Europe),
       gi26v (Global Icons: Spring Online 2026)
  GBP: gi26u (Global Icons: UK Online)
  CHF: dg25 (Zurich Auction 2025)

Exchange rates are approximate mid-market rates for the auction period.

Usage (from backend/ directory):
    python data/migrate_broad_arrow_fx.py
"""
import asyncio
import os
import re
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, engine
from app.models.listing import AuctionResult
from sqlalchemy import select, update

# event_code → (currency, usd_rate)
# Rates are approximate period averages at time of each auction
NON_USD_EVENTS = {
    # EUR events
    've25':  ('EUR', 1.110),   # Villa d'Este, May 2025
    've26':  ('EUR', 1.130),   # Villa d'Este, May 2026
    'zt25':  ('EUR', 1.090),   # Zoute Concours, October 2025
    'gi26e': ('EUR', 1.120),   # Global Icons: Europe, 2026
    'gi26v': ('EUR', 1.120),   # Global Icons: Spring Online, 2026
    # GBP events
    'gi26u': ('GBP', 1.280),   # Global Icons: UK Online, 2026
    # CHF events
    'dg25':  ('CHF', 1.110),   # Zurich Auction, 2025
}

EVENT_RE = re.compile(r'/vehicles/([a-z0-9]+)_')


def extract_event(url: str) -> str | None:
    m = EVENT_RE.search(url)
    return m.group(1) if m else None


async def migrate() -> None:
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.id, AuctionResult.auction_url, AuctionResult.sold_price).where(
                AuctionResult.auction_source == 'Broad Arrow',
                AuctionResult.auction_url.isnot(None),
                AuctionResult.sold_price.isnot(None),
            )
        )
        records = rows.fetchall()

    updates: list[tuple[int, int, str, float]] = []
    for row in records:
        event = extract_event(row.auction_url or '')
        if not event or event not in NON_USD_EVENTS:
            continue
        currency, rate = NON_USD_EVENTS[event]
        usd_price = round(row.sold_price * rate)
        updates.append((row.id, usd_price, currency, rate))

    print(f"Records to convert: {len(updates)}")
    for record_id, usd_price, currency, rate in updates:
        orig = next(r.sold_price for r in records if r.id == record_id)
        print(f"  id={record_id}  {currency} {orig:,} × {rate} → ${usd_price:,}")

    if not updates:
        return

    async with AsyncSessionLocal() as session:
        for record_id, usd_price, _currency, _rate in updates:
            await session.execute(
                update(AuctionResult)
                .where(AuctionResult.id == record_id)
                .values(sold_price=usd_price)
            )
        await session.commit()

    print(f"\nConverted {len(updates)} records to USD")
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(migrate())
