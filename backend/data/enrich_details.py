#!/usr/bin/env python3
"""
Fill mileage, exterior color and paint-to-sample from each lot's own page.

See app/services/enrichment.py for how it works. Rows are processed most
expensive first, and every run picks up where the last stopped, so it is safe
to Ctrl-C a long backfill and run it again later.

Usage (from backend/ directory):
    python data/enrich_details.py --stats                 # coverage by source
    python data/enrich_details.py bat --limit 50          # trial run
    python data/enrich_details.py bat --min-price 100000  # skip the everyday cars
    python data/enrich_details.py bat rm gooding          # per-lot sources
    python data/enrich_details.py mecum bonhams           # bulk sources (minutes)
    python data/enrich_details.py broad-arrow             # archive.org snapshots, ~3 lots/min
    python data/enrich_details.py broad-arrow --refetch-thin   # redo lots fetched highlights-only
    python data/enrich_details.py all
    python data/enrich_details.py --reparse --dry-run     # re-run parsers on stored text, no network
    python data/enrich_details.py --reparse               #   ...and write the changes

Transmission / chassis / interior / options / provenance are re-derived from
the stored text after every write. After changing app/utils/lot_extras.py,
re-derive every row with: python data/migrate_lot_extras.py [--apply]

Sources: bat, rm, gooding, broad-arrow, mecum, bonhams
"""
import argparse
import asyncio
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.database import AsyncSessionLocal, engine
from app.services.enrichment import SOURCES, FetchBlocked, enrich, reparse
from app.utils.lot_details import PROSE_SEPARATOR
from sqlalchemy import text

SIGNIFICANT_PRICE = 150_000

_STATS_SQL = text(f"""
    SELECT auction_source,
           count(*)                                              AS n,
           count(mileage)                                        AS mileage,
           count(exterior_color)                                 AS color,
           count(*) FILTER (WHERE sold_price >= {SIGNIFICANT_PRICE})                 AS sig,
           count(exterior_color) FILTER (WHERE sold_price >= {SIGNIFICANT_PRICE})    AS sig_color,
           count(mileage) FILTER (WHERE sold_price >= {SIGNIFICANT_PRICE})           AS sig_mileage,
           count(details_fetched_at)                             AS fetched
    FROM auction_results GROUP BY 1 ORDER BY 2 DESC
""")


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:5.1f}%" if b else "   — "


async def print_stats() -> None:
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(_STATS_SQL)).fetchall()
    print(f"{'source':<20}{'rows':>7}{'mileage':>9}{'color':>8}   "
          f"{'$150k+':>7}{'mileage':>9}{'color':>8}   {'fetched':>8}")
    tot = [0] * 7
    for src, n, mi, co, sig, sig_co, sig_mi, fetched in rows:
        print(f"{src:<20}{n:>7}{pct(mi, n):>9}{pct(co, n):>8}   "
              f"{sig:>7}{pct(sig_mi, sig):>9}{pct(sig_co, sig):>8}   {fetched:>8}")
        for i, v in enumerate((n, mi, co, sig, sig_co, sig_mi, fetched)):
            tot[i] += v
    n, mi, co, sig, sig_co, sig_mi, fetched = tot
    print(f"{'TOTAL':<20}{n:>7}{pct(mi, n):>9}{pct(co, n):>8}   "
          f"{sig:>7}{pct(sig_mi, sig):>9}{pct(sig_co, sig):>8}   {fetched:>8}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="*", help=f"{', '.join(SOURCES)} or all")
    parser.add_argument("--limit", type=int, help="at most N lots per source (most expensive first)")
    parser.add_argument("--min-price", type=int, metavar="USD",
                        help="only lots that sold for at least this much")
    parser.add_argument("--only-incomplete", action="store_true",
                        help="skip lots whose title already gave mileage and color")
    parser.add_argument("--include-complete", action="store_true",  # default now; kept for old commands
                        help="also fetch lots that already have mileage and color, to store their text")
    parser.add_argument("--refetch-thin", action="store_true",
                        help="first mark already-fetched lots with no description text as unfetched, "
                             "so this run fetches them again (e.g. after a fetcher starts keeping more)")
    parser.add_argument("--reparse", action="store_true", help="re-run parsers over stored text; no network")
    parser.add_argument("--dry-run", action="store_true", help="with --reparse: show changes, write nothing")
    parser.add_argument("--stats", action="store_true", help="print coverage by source")
    args = parser.parse_args()

    keys = list(SOURCES) if args.sources == ["all"] else args.sources
    unknown = [k for k in keys if k not in SOURCES]
    if unknown:
        parser.error(f"unknown source(s): {', '.join(unknown)}")

    try:
        if args.reparse:
            names = [SOURCES[k].name for k in keys] or [None]
            for name in names:
                checked, changes = await reparse(name, dry_run=args.dry_run)
                for c in changes[:40]:
                    print(f"  #{c['id']} {c['field']}: {c['old']!r} -> {c['new']!r}")
                if len(changes) > 40:
                    print(f"  ... and {len(changes) - 40} more")
                verb = "would change" if args.dry_run else "changed"
                print(f"[{name or 'all sources'}] re-parsed {checked} row(s), {verb} {len(changes)} value(s)")
        for key in keys if not args.reparse else []:
            if args.refetch_thin:
                # Stored text without a prose part came from a fetcher that kept
                # only highlight bullets (Broad Arrow before 2026-11-02).
                async with AsyncSessionLocal() as session:
                    n = (await session.execute(text(
                        "UPDATE auction_results SET details_fetched_at = NULL "
                        "WHERE auction_source = :src AND details_fetched_at IS NOT NULL "
                        "AND (details_text IS NULL OR strpos(details_text, :sep) = 0)"),
                        {"src": SOURCES[key].name, "sep": PROSE_SEPARATOR})).rowcount
                    await session.commit()
                print(f"[{SOURCES[key].name}] {n} thin lot(s) marked for re-fetch")
            try:
                await enrich(key, limit=args.limit, min_price=args.min_price,
                             include_complete=not args.only_incomplete)
            except FetchBlocked as exc:
                print(f"[{SOURCES[key].name}] stopped — site is refusing requests ({exc}). "
                      "Progress is saved; re-run later.")
        if args.stats or not (keys or args.reparse):
            await print_stats()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
