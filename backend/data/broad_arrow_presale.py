#!/usr/bin/env python3
"""
Preserve Broad Arrow's catalogue for upcoming Porsche lots, before the sale.

Broad Arrow removes a lot's description once the sale is over, so the results
we ingest afterwards carry only price and photos. The catalogue — color,
mileage at cataloguing, options, history — is recoverable only from an
archive.org copy taken while the lot was still listed. Many lots have one by
chance; this makes sure every Porsche lot does.

It asks archive.org's public Save Page Now service to capture:
  1. the "Available Lots" pages, which list every upcoming lot, then
  2. each Porsche lot page found there,
and checks that each capture really contains the catalogue. Our requests go
only to archive.org; its crawler fetches the public pages.

After the sale, `broad_arrow_ingest.py` adds the results and its enrichment
step finds them (app/services/enrichment.fetch_broad_arrow). Each catalogue is
also kept locally in ~/Projects/CollectorCarMarket-data/cache/broad_arrow_presale/
so the ingest does not depend on archive.org still serving the copy.

Run manually a few days before each Broad Arrow auction, once the catalogue
is published. Slow by design: one request every ~30 s, and it stops at the
first refusal. Re-running is safe; lots already captured with their catalogue
in the last few days are skipped.

Usage (from backend/ directory):
    python data/broad_arrow_presale.py                 # all upcoming Porsche lots
    python data/broad_arrow_presale.py --event dg26    # one sale only
    python data/broad_arrow_presale.py --dry-run       # list lots from existing captures; capture nothing
    python data/broad_arrow_presale.py --lots URL ...  # these lot pages only
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.services.enrichment import (  # noqa: E402
    SSL_CTX, WAYBACK_CDX, WAYBACK_UA, FetchBlocked, _BA_LOT_ID_RE, _LD_JSON_RE, _wayback_get,
    load_presale, parse_broad_arrow_page, save_presale,
)
from data.broad_arrow_ingest import AUCTION_EVENTS, extract_event_code  # noqa: E402

BASE = "https://www.broadarrowauctions.com"
LISTING = f"{BASE}/vehicles"
SAVE = "https://web.archive.org/save/"
SAVE_SPACING = 30          # seconds after every capture request
SAVE_TIMEOUT = 180         # a capture can take a minute or two
MAX_LISTING_PAGES = 20
RECENT = timedelta(days=3)  # a catalogue capture this fresh is not redone
# A dropped connection (Wi-Fi change, Mac waking from sleep) is waited out:
# these back-offs, then the lot counts as failed. Refusals (403/429) are not
# retried at all — they stop the run.
NETWORK_RETRY_WAITS = (30, 120, 300)
MAX_CONSECUTIVE_FAILED_LOTS = 3


def with_retry(fn, *args):
    """Call fn, waiting out network outages. HTTP errors are not retried here."""
    for wait in NETWORK_RETRY_WAITS + (None,):
        try:
            return fn(*args)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            if wait is None:
                raise
            print(f"    network problem ({exc}); retrying in {wait}s", flush=True)
            time.sleep(wait)


def save(url: str) -> str | None:
    """
    Ask archive.org to capture `url` now. Returns the capture's timestamp, or
    None when archive.org could not fetch the page. FetchBlocked on 429/403.
    """
    req = urllib.request.Request(SAVE + url, headers={"User-Agent": WAYBACK_UA})
    try:
        with urllib.request.urlopen(req, timeout=SAVE_TIMEOUT, context=SSL_CTX) as resp:
            final = resp.geturl()
            location = resp.headers.get("Content-Location") or ""
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise FetchBlocked(f"HTTP {exc.code} from Save Page Now") from exc
        if exc.code in (502, 503, 504, 520, 523):
            print(f"    archive.org could not capture it (HTTP {exc.code})")
            return None
        raise
    finally:
        time.sleep(SAVE_SPACING)
    m = re.search(r'/web/(\d{14})', location or final)
    return m.group(1) if m else None


def latest_snapshot(url: str) -> str | None:
    """Timestamp of the newest archived 200 response for exactly this URL."""
    raw = _wayback_get(f"{WAYBACK_CDX}?url={urllib.parse.quote(url, safe='')}"
                       "&filter=statuscode:200&fl=timestamp&output=json&limit=-1")
    rows = json.loads(raw)[1:] if raw and raw.strip() else []
    return rows[-1][0] if rows else None


def archived(url: str, timestamp: str) -> str | None:
    return _wayback_get(f"https://web.archive.org/web/{timestamp}id_/{url}")


def porsche_lots(page: str) -> list[str]:
    """Lot URLs of the Porsches on one archived listing page."""
    out = []
    for blob in _LD_JSON_RE.findall(page):
        try:
            car = json.loads(blob)
        except ValueError:
            continue
        if (isinstance(car, dict) and car.get("@type") == "Car"
                and "porsche" in (car.get("manufacturer") or "").lower() and car.get("url")):
            out.append(car["url"].split("?")[0])
    return out


def upcoming_lots(event: str | None, capture: bool = True) -> list[str]:
    lots: list[str] = []
    for n in range(1, MAX_LISTING_PAGES + 1):
        url = LISTING if n == 1 else f"{LISTING}?page={n}"
        print(f"  {'capturing' if capture else 'reading latest capture of'} listing page {n} ...", flush=True)
        ts = (with_retry(save, url) if capture else None) or with_retry(latest_snapshot, url)
        page = with_retry(archived, url, ts) if ts else None
        if not page:
            print(f"    no capture of {url}; stopping the listing scan")
            break
        if 'application/ld+json' not in page:
            print(f"    listing page {n} has no lot data (layout changed?)")
            break
        found = porsche_lots(page)
        cars = page.count('"@type": "Car"') + page.count('"@type":"Car"')
        new = [u for u in found if u not in lots]
        print(f"    {cars} lots on the page, {len(found)} Porsche, {len(new)} new")
        lots += new
        if f"page={n + 1}" not in page:
            break
    if event:
        lots = [u for u in lots if extract_event_code(u) == event.lower()]
    return lots


def keep(url: str, ts: str, page: str | None) -> bool:
    """Store the catalogue from an archived page locally. True if it had one."""
    if not page:
        return False
    details, is_catalogue = parse_broad_arrow_page(page)
    if is_catalogue:
        save_presale(url, details, ts, page)
    return is_catalogue


def fresh_catalogue(url: str) -> bool:
    """True when archive.org already has a recent capture with the catalogue
    (which is then kept locally)."""
    ts = latest_snapshot(url)
    if not ts:
        return False
    when = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - when > RECENT:
        return False
    return keep(url, ts, archived(url, ts))


def capture_lot(url: str, refresh: bool) -> str:
    """'ok', 'already' or 'failed' for one lot."""
    lot_id = _BA_LOT_ID_RE.search(url)
    if lot_id and load_presale(lot_id.group(1)) and not refresh:
        print("    catalogue already kept locally")
        return "already"
    if with_retry(fresh_catalogue, url):
        print("    already captured with catalogue (kept locally)")
        return "already"
    ts = with_retry(save, url)
    page = with_retry(archived, url, ts) if ts else None
    if keep(url, ts, page):
        print(f"    captured with catalogue ({ts}), kept locally")
        return "ok"
    print("    captured, but without the catalogue" if page else "    not captured")
    return "failed"


def main() -> int:
    """Exit 0 only when every lot's catalogue is kept, so a scheduler retries otherwise."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event", help="only this sale's lots, by event code (e.g. dg26)")
    parser.add_argument("--lots", nargs="+", metavar="URL",
                        help="capture these lot pages instead of scanning Available Lots "
                             "(e.g. lots that left the listing because their sale just ended)")
    parser.add_argument("--dry-run", action="store_true",
                        help="list lots from existing captures; capture nothing")
    parser.add_argument("--refresh", action="store_true",
                        help="capture again even when a catalogue is already kept locally "
                             "(e.g. Broad Arrow revised the description)")
    args = parser.parse_args()

    if args.event and args.event.lower() not in AUCTION_EVENTS:
        print(f"Note: {args.event} is not in AUCTION_EVENTS yet — add it (broad_arrow_events.py) "
              "or these lots will be ingested without a sale date.")

    try:
        if args.lots:
            lots = [u.split("?")[0] for u in args.lots]
        else:
            print("Finding upcoming Porsche lots (via archive.org captures of Available Lots)")
            lots = upcoming_lots(args.event, capture=not args.dry_run)
        print(f"{len(lots)} upcoming Porsche lot(s)")
        for u in lots:
            print(f"  {u}")
        if args.dry_run or not lots:
            return 0

        ok, already, failed, streak = 0, 0, [], 0
        for i, url in enumerate(lots, 1):
            print(f"[{i}/{len(lots)}] {url}", flush=True)
            errored = False
            try:
                outcome = capture_lot(url, args.refresh)
            except FetchBlocked:
                raise
            except Exception as exc:  # one bad lot must not end the run
                print(f"    error: {type(exc).__name__}: {exc}", flush=True)
                outcome, errored = "failed", True
            if outcome == "failed":
                failed.append(url)
                # Only errors (outage, archive.org trouble) count toward
                # stopping; a page that was already stripped is just that lot.
                streak = streak + 1 if errored else 0
                if streak >= MAX_CONSECUTIVE_FAILED_LOTS:
                    print(f"\nStopped after {streak} errors in a row; re-run later.")
                    break
            else:
                streak = 0
                ok += outcome == "ok"
                already += outcome == "already"
    except FetchBlocked as exc:
        print(f"\nStopped — archive.org is refusing requests ({exc}). Re-run later; "
              "lots already kept are skipped.")
        return 1
    except Exception as exc:
        print(f"\nStopped — {type(exc).__name__}: {exc}. Re-run later; lots already kept are skipped.")
        return 1

    print(f"\nDone — {ok} captured, {already} already kept, {len(failed)} failed")
    for u in failed:
        print(f"  failed: {u}")
    return 1 if failed or ok + already < len(lots) else 0


if __name__ == "__main__":
    sys.exit(main())
