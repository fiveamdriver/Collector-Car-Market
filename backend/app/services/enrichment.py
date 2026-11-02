"""
Lot-detail enrichment: fetch each lot's own page, keep its cleaned text, and
fill mileage / exterior_color / paint_to_sample from it.

Ingest scripts read the auction houses' search APIs, which carry little beyond
title, price and date. The detail that matters — "14k Miles Shown",
"Guards Red Paint" — lives on the lot page. This is the second stage that
fetches it:

    ingest (search API → new rows)  →  enrich (lot page → details_text → fields)

Design points:
  * Most valuable cars first: rows are processed in sold_price order, so a
    partial run still covers the significant cars.
  * details_text is stored, so improving app/utils/lot_details.py and running
    `enrich_details.py --reparse` updates every row without re-fetching.
  * details_fetched_at marks a row done even when its page had nothing, so it
    isn't fetched again on the next run. Network errors leave it unset.
  * Only empty fields are filled (COALESCE). A value already on the row came
    from a more structured source and is kept.

Per-lot sources (BaT, RM, Gooding, Broad Arrow) fetch one page per row.
Bulk sources (Mecum, Bonhams) already return full lot text from their search
APIs, so they re-page those instead.
"""
import asyncio
import faulthandler
import gzip
import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Iterable

import certifi
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.services import derived
from app.utils.lot_details import extract, html_to_text, join_details, parse_odometer_value

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Long descriptions are mostly history; mileage and color statements fall well
# inside this. Bounds row size across ~25k rows.
MAX_PROSE_CHARS = 12_000
FLUSH_EVERY = 25
# Hard deadlines. urlopen's timeout is per socket read, so a server that
# trickles bytes can hold a request indefinitely; a dropped pooler connection
# can do the same to a commit. An early backfill stalled on exactly this.
FETCH_DEADLINE = 60
FLUSH_DEADLINE = 120
# Stop rather than keep requesting when every lot is failing.
MAX_CONSECUTIVE_ERRORS = 25
# Watchdog: if nothing completes (no fetch result, no write) for this long
# beyond a source's own deadline, dump every thread's stack to stderr and exit.
# A scheduled run must fail loudly, never sit silently. One BaT retry once
# sat 18 hours with no writes.
STALL_GRACE = 300


class FetchBlocked(Exception):
    """The site is refusing requests (403/429). Stop the run rather than hammer it."""


def http_get(url: str, timeout: int = 30, decode: bool = True,
             user_agent: str = UA) -> str | bytes | None:
    """GET a page. None on 404/410 (lot removed); FetchBlocked on 403/429."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Language": "en-US"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            # Read in chunks against a total deadline: `timeout` alone resets on
            # every chunk, so a trickling response would never time out.
            chunks = []
            while chunk := resp.read(65536):
                chunks.append(chunk)
                if time.monotonic() - started > FETCH_DEADLINE - 10:
                    raise TimeoutError(f"response still arriving after {FETCH_DEADLINE - 10}s")
            body = b"".join(chunks)
            return body.decode("utf-8", errors="replace") if decode else body
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            return None
        if exc.code in (403, 429):
            raise FetchBlocked(f"HTTP {exc.code} for {url}") from exc
        raise


def split_html(raw: str | None) -> tuple[list[str], str]:
    """
    Split an HTML description into (bullets, prose): short lines are list items
    or spec rows, long lines are paragraphs.
    """
    bullets, prose = [], []
    for line in html_to_text(raw).split("\n"):
        (bullets if len(line) <= 160 else prose).append(line)
    return bullets, " ".join(prose)[:MAX_PROSE_CHARS]


# ── Per-lot fetchers: url → details_text ("" = page had nothing) ─────────────

_BAT_DETAILS_RE = re.compile(r'<strong>Listing Details</strong>\s*<ul>(.*?)</ul>', re.DOTALL)
_BAT_EXCERPT_RE = re.compile(r'class="post-excerpt"[^>]*>(.*?)</div>', re.DOTALL)
_LI_RE = re.compile(r'<li[^>]*>(.*?)</li>', re.DOTALL)


def fetch_bat(url: str) -> str | None:
    page = http_get(url)
    if page is None:
        return ""
    m = _BAT_DETAILS_RE.search(page)
    # A removed or private lot redirects to the sign-in page: nothing to get.
    if not m and re.search(r'<title>[^<]*(?:Sign In|Log In)', page, re.IGNORECASE):
        return ""
    if not m and 'class="post-excerpt"' not in page:
        # Anything else means the page layout changed. Raise, so the row isn't
        # marked done with nothing and is retried once the parser is fixed.
        raise ValueError("unrecognized BaT page layout")
    bullets = [html_to_text(li) for li in _LI_RE.findall(m.group(1))] if m else []
    e = _BAT_EXCERPT_RE.search(page)
    prose = html_to_text(e.group(1)).replace("\n", " ")[:MAX_PROSE_CHARS] if e else ""
    return join_details(bullets, prose) or ""


_RM_BULLETS_RE = re.compile(r'<ul class="list-bullets[^"]*"[^>]*>(.*?)</ul>', re.DOTALL)
_RM_BODY_RE = re.compile(r'<div class="body-text--copy[^"]*"[^>]*>(.*?)</div>', re.DOTALL)


def fetch_rm(url: str) -> str | None:
    page = http_get(url)
    if page is None:
        return ""
    m = _RM_BULLETS_RE.search(page)
    bullets = [html_to_text(li) for li in _LI_RE.findall(m.group(1))] if m else []
    prose = " ".join(html_to_text(p).replace("\n", " ") for p in _RM_BODY_RE.findall(page))
    return join_details(bullets, prose[:MAX_PROSE_CHARS]) or ""


_GOODING_SLUG_RE = re.compile(r'goodingco\.com/lot/([^/?#]+)')


def fetch_gooding(url: str) -> str | None:
    m = _GOODING_SLUG_RE.search(url)
    if not m:
        return ""
    raw = http_get(f"https://www.goodingco.com/page-data/lot/{m.group(1)}/page-data.json")
    if raw is None:
        return ""
    item = (json.loads(raw).get("result", {}).get("data", {})
            .get("contentfulLot", {}).get("item") or {})
    bullets = (item.get("highlights") or []) + (item.get("specifications") or [])
    note = item.get("note")
    prose = html_to_text(note).replace("\n", " ") if isinstance(note, str) else ""
    return join_details(bullets, prose) or ""


# ── Broad Arrow: Internet Archive snapshots ──────────────────────────────────
#
# Broad Arrow strips the highlights list from a lot page once the sale is over,
# so the live page of a sold lot has only price and photos. The pre-sale page
# — with "Paint to Sample Riviera Blue ... under 1,300 miles at the time of
# cataloging" — survives in the Wayback Machine for roughly 70% of lots, and
# archive.org serves it over plain HTTP with no WAF challenge.

_BA_LOT_ID_RE = re.compile(r'/vehicles/([a-z0-9]+_[a-z0-9]+)')
_BA_HIGHLIGHTS_RE = re.compile(
    r"<div class=['\"]vehicle-highlights['\"]>\s*<ul[^>]*>(.*?)</ul>", re.DOTALL)
_LD_JSON_RE = re.compile(r'<script type=["\']application/ld\+json["\']>(.*?)</script>', re.DOTALL)
WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
MAX_SNAPSHOTS_TRIED = 4
# Snapshot playback tolerates far less than the documented ~15/min: bursts at
# 10/min drew 429s that lasted most of an hour. 3/min ran clean.
WAYBACK_SPACING = 20  # seconds after every archive.org request
# archive.org gets an honest, identifying User-Agent — not the browser string
# used for the auction sites. It is a nonprofit; let it see who is asking.
WAYBACK_UA = ("CollectorCarMarket-enrichment/1.0 (personal research; "
              "slow single-threaded fetch of archived auction lot pages)")


def _wayback_get(url: str) -> str | None:
    # Stop at the first refusal (429 too fast, 503 busy) instead of waiting it
    # out: the old 30-60 minute in-thread backoffs held one lot for hours and
    # looked exactly like a hang. Progress is saved; re-run later.
    try:
        raw = http_get(url, timeout=45, decode=False, user_agent=WAYBACK_UA)
    except urllib.error.HTTPError as exc:
        if exc.code in (502, 503, 504):
            raise FetchBlocked(f"HTTP {exc.code} from archive.org") from exc
        raise
    finally:
        time.sleep(WAYBACK_SPACING)
    if raw is None:
        return None
    if raw[:2] == b"\x1f\x8b":  # archived body is stored gzip-encoded
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


def _ba_structured(page: str) -> list[str]:
    """VIN / interior / transmission from the page's Schema.org Car block."""
    out = []
    for blob in _LD_JSON_RE.findall(page):
        try:
            car = json.loads(blob)
        except ValueError:
            continue
        if not isinstance(car, dict) or car.get("@type") != "Car":
            continue
        for key, label in (("vehicleIdentificationNumber", "Chassis"),
                           ("color", "Exterior"),
                           ("vehicleInteriorColor", "Interior"),
                           ("vehicleTransmission", "Transmission")):
            if car.get(key):
                out.append(f"{label}: {car[key]}")
    return out


# The snapshot index for every Broad Arrow lot comes from one bulk query
# (~1 MB), cached for a week. Per-lot index queries hit archive.org's CDX
# service ~550 times and it times out under that load; the snapshot pages
# themselves come from a separate, fast endpoint.
_CACHE_DIR = Path.home() / "Projects" / "CollectorCarMarket-data" / "cache"
_BA_INDEX_FILE = _CACHE_DIR / "broad_arrow_wayback_index.json"
_BA_INDEX_MAX_AGE = 7 * 86400
_ba_index: dict[str, list[tuple[str, str]]] | None = None
_ba_index_lock = threading.Lock()


def _broad_arrow_index() -> dict[str, list[tuple[str, str]]]:
    """lot id → [(timestamp, url)] of archived 200 responses."""
    global _ba_index
    with _ba_index_lock:
        if _ba_index is not None:
            return _ba_index
        fresh = (_BA_INDEX_FILE.exists()
                 and time.time() - _BA_INDEX_FILE.stat().st_mtime < _BA_INDEX_MAX_AGE)
        if fresh:
            rows = json.loads(_BA_INDEX_FILE.read_text())
        else:
            raw = http_get(
                f"{WAYBACK_CDX}?url=broadarrowauctions.com/vehicles/&matchType=prefix"
                "&filter=statuscode:200&fl=urlkey,timestamp&output=json", timeout=300,
                user_agent=WAYBACK_UA)
            rows = json.loads(raw)[1:] if raw and raw.strip() else []
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _BA_INDEX_FILE.write_text(json.dumps(rows))
        index: dict[str, list[tuple[str, str]]] = {}
        for urlkey, timestamp in rows:
            m = _BA_LOT_ID_RE.search(urlkey)
            if m:
                # urlkey is "com,broadarrowauctions)/vehicles/<id>/<slug>"
                path = urlkey.split(")", 1)[1]
                index.setdefault(m.group(1), []).append(
                    (timestamp, f"https://www.broadarrowauctions.com{path}"))
        _ba_index = index
        return index


def fetch_broad_arrow(url: str) -> str | None:
    """
    Pre-sale highlights for a Broad Arrow lot from its newest useful snapshot.
    None when the lot was never archived — left unmarked so a later run (or
    another source) can still fill it.
    """
    m = _BA_LOT_ID_RE.search(url)
    if not m:
        return ""
    rows = _broad_arrow_index().get(m.group(1))
    if not rows:
        return None
    # Snapshots of this lot's own URL first, newest first; the index also
    # holds pages like /vehicles/<id>/release that are not the lot page.
    path = url.split("broadarrowauctions.com", 1)[-1].rstrip("/")
    ranked = sorted(set(rows), key=lambda r: (r[1].rstrip("/").endswith(path), r[0]), reverse=True)
    for timestamp, original in ranked[:MAX_SNAPSHOTS_TRIED]:
        page = _wayback_get(f"https://web.archive.org/web/{timestamp}id_/{original}")
        if not page:
            continue
        h = _BA_HIGHLIGHTS_RE.search(page)
        if h:
            bullets = [html_to_text(li) for li in _LI_RE.findall(h.group(1))]
            return join_details(bullets + _ba_structured(page)) or ""
    # Archived, but only after the sale (no highlights in any snapshot).
    return ""


# ── Broad Arrow live pages via Playwright (superseded by fetch_broad_arrow) ──

async def run_broad_arrow(urls: list[str], on_result) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await (await browser.new_context(user_agent=UA)).new_page()
        for url in urls:
            try:
                # Not "networkidle": the lot pages keep analytics connections
                # open, so it never fires and every lot timed out at 60s.
                await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                # The WAF challenge runs first, then redirects to the lot page.
                await page.wait_for_selector("main li, main p", timeout=30_000)
                parts = await page.evaluate("""() => {
                    const root = document.querySelector('main') || document.body;
                    const li = Array.from(root.querySelectorAll('li'))
                        .map(e => e.innerText.trim()).filter(t => t.length > 10 && t.length < 200);
                    const p = Array.from(root.querySelectorAll('p'))
                        .map(e => e.innerText.trim()).filter(t => t.length > 80);
                    return {li, p};
                }""")
                text_ = join_details(parts["li"], " ".join(parts["p"])[:MAX_PROSE_CHARS]) or ""
                await on_result(url, text_, {})
            except Exception as exc:
                print(f"  ! {url}: {exc}", flush=True)
            await asyncio.sleep(1.5)
        await browser.close()


# ── Bulk sources: (url, details_text, structured fields) from search APIs ────

def bulk_mecum() -> Iterable[tuple[str, str, dict]]:
    from data.mecum_ingest import LOTS_QUERY, PAGE_SIZE, gql

    query = LOTS_QUERY.replace("vinSerial", "vinSerial content")
    offset = 0
    while True:
        resp = gql(query, {"size": PAGE_SIZE, "offset": offset})
        if "errors" in resp:
            raise RuntimeError(resp["errors"])
        edges = resp["data"]["lots"].get("edges") or []
        if not edges:
            return
        for edge in edges:
            node = edge["node"]
            if not node.get("link"):
                continue
            bullets, prose = split_html(node.get("content"))
            extra = {}
            miles = parse_odometer_value(node.get("odometer"), node.get("odometerUnits"))
            if miles is not None:
                extra["mileage"] = miles
            yield node["link"], join_details(bullets, prose) or "", extra
        offset += PAGE_SIZE
        time.sleep(1)


def bulk_bonhams() -> Iterable[tuple[str, str, dict]]:
    from data.bonhams_ingest import build_lot_url, fetch_page, scrape_typesense_key

    key = scrape_typesense_key()
    page = 1
    while True:
        docs, _ = fetch_page(key, page)
        if not docs:
            return
        for doc in docs:
            url = build_lot_url(doc)
            if not url:
                continue
            # catalogDesc holds the bullet highlights; footnotes the essay.
            bullets, desc_prose = split_html(doc.get("catalogDesc"))
            _, notes = split_html(doc.get("footnotes"))
            prose = f"{desc_prose} {notes}".strip()[:MAX_PROSE_CHARS]
            yield url, join_details(bullets, prose) or "", {}
        page += 1
        time.sleep(1)


# ── Source registry ───────────────────────────────────────────────────────────

@dataclass
class Source:
    name: str                                   # auction_results.auction_source
    fetch: Callable[[str], str | None] | None = None
    bulk: Callable[[], Iterable] | None = None
    browser: Callable[..., Awaitable] | None = None
    workers: int = 2
    delay: float = 1.0                          # seconds each worker waits between requests
    deadline: float = FETCH_DEADLINE            # seconds one lot may take, retries included


SOURCES: dict[str, Source] = {
    "bat":         Source("BaT", fetch=fetch_bat, workers=2, delay=1.0),
    "rm":          Source("RM Sotheby's", fetch=fetch_rm, workers=2, delay=1.0),
    "gooding":     Source("Gooding & Company", fetch=fetch_gooding, workers=3, delay=0.5),
    # One worker: archive.org is a nonprofit and rate-limits bursts.
    # Spacing is enforced per request inside fetch_broad_arrow. Deadline covers
    # up to MAX_SNAPSHOTS_TRIED snapshots at ~65s each (45s read + 20s spacing);
    # the first lot also loads the snapshot index (up to 300s).
    "broad-arrow": Source("Broad Arrow", fetch=fetch_broad_arrow, workers=1, delay=0,
                          deadline=600),
    # Bulk sources re-page a whole search API in one call: deadline is for all of it.
    "mecum":       Source("Mecum", bulk=bulk_mecum, deadline=3600),
    "bonhams":     Source("Bonhams", bulk=bulk_bonhams, deadline=3600),
}
SOURCE_BY_NAME = {s.name: k for k, s in SOURCES.items()}


# ── Hang protection ───────────────────────────────────────────────────────────

def _in_daemon_thread(fn: Callable, *args) -> asyncio.Future:
    """
    Run a blocking call on its own daemon thread.

    Not asyncio.to_thread: its pool threads are joined when the process exits,
    so one request stuck in a socket call (DNS has no timeout at all) keeps the
    process alive forever even after wait_for gave up on it. A daemon thread is
    simply abandoned.
    """
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def settle(result=None, exc=None):
        if not fut.done():
            fut.set_exception(exc) if exc else fut.set_result(result)

    def run():
        try:
            result = fn(*args)
        except BaseException as exc:
            loop.call_soon_threadsafe(settle, None, exc)
        else:
            loop.call_soon_threadsafe(settle, result)

    threading.Thread(target=run, daemon=True, name=f"enrich-{getattr(fn, '__name__', 'fetch')}").start()
    return fut


class Watchdog:
    """Exit with every thread's stack on stderr when nothing completes for `seconds`."""

    def __init__(self, seconds: float):
        self.seconds = seconds

    def kick(self) -> None:
        faulthandler.dump_traceback_later(self.seconds, exit=True)

    def __enter__(self):
        self.kick()
        return self

    def __exit__(self, *exc):
        faulthandler.cancel_dump_traceback_later()


# ── Database ──────────────────────────────────────────────────────────────────

# SET expressions all see the row's old values, so details_filled records
# exactly the fields that were empty and are filled by this update.
_UPDATE_SQL = text("""
    UPDATE auction_results SET
        details_filled     = NULLIF(concat_ws(',',
            CASE WHEN mileage IS NULL AND CAST(:mileage AS INTEGER) IS NOT NULL
                 THEN 'mileage' END,
            CASE WHEN exterior_color IS NULL AND CAST(:exterior_color AS VARCHAR) IS NOT NULL
                 THEN 'exterior_color' END,
            CASE WHEN paint_to_sample IS NULL AND CAST(:paint_to_sample AS BOOLEAN) IS NOT NULL
                 THEN 'paint_to_sample' END), ''),
        mileage            = COALESCE(mileage, :mileage),
        exterior_color     = COALESCE(exterior_color, :exterior_color),
        paint_to_sample    = COALESCE(paint_to_sample, :paint_to_sample),
        details_text       = :details_text,
        details_fetched_at = now()
    WHERE id = :id
""")


@dataclass
class Stats:
    fetched: int = 0
    mileage: int = 0
    color: int = 0
    errors: int = 0
    consecutive_errors: int = 0
    pending: list[dict] = field(default_factory=list)
    # Workers share `pending`; one flush at a time.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


async def _select_rows(source: str, urls: list[str] | None, limit: int | None,
                       include_complete: bool, min_price: int | None) -> list[tuple[int, str]]:
    sql = """
        SELECT id, auction_url FROM auction_results
        WHERE auction_source = :source AND auction_url IS NOT NULL
          AND details_fetched_at IS NULL
    """
    if not include_complete:
        sql += " AND (mileage IS NULL OR exterior_color IS NULL)"
    params: dict = {"source": source}
    if urls is not None:
        sql += " AND auction_url = ANY(:urls)"
        params["urls"] = urls
    if min_price:
        sql += " AND sold_price >= :min_price"
        params["min_price"] = min_price
    sql += " ORDER BY sold_price DESC NULLS LAST"
    if limit:
        sql += f" LIMIT {int(limit)}"
    async with AsyncSessionLocal() as session:
        return [(r[0], r[1]) for r in (await session.execute(text(sql), params)).fetchall()]


async def _write(batch: list[dict]) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(_UPDATE_SQL, batch)
        await session.commit()
    # New details_text: recompute transmission / chassis / interior / options /
    # provenance from it. Idempotent, so a retried batch is harmless.
    await derived.refresh([row["id"] for row in batch])


async def _flush(stats: Stats) -> None:
    async with stats.lock:
        # Take the batch before awaiting, so rows other workers add meanwhile
        # go into the next batch instead of being written twice or dropped.
        batch, stats.pending = stats.pending, []
        if not batch:
            return
        try:
            await asyncio.wait_for(_write(batch), FLUSH_DEADLINE)
        except (asyncio.TimeoutError, OSError):
            # Dead pooled connection: one retry gets a fresh one.
            await asyncio.wait_for(_write(batch), FLUSH_DEADLINE)


async def _record(stats: Stats, row_id: int, details_text: str, extra: dict,
                  current: dict | None = None) -> None:
    fields = extract(details_text)
    fields.update(extra)
    stats.fetched += 1
    stats.mileage += fields["mileage"] is not None
    stats.color += fields["exterior_color"] is not None
    stats.pending.append({"id": row_id, "details_text": details_text or None, **fields})
    if len(stats.pending) >= FLUSH_EVERY:
        await _flush(stats)


# ── Entry point ───────────────────────────────────────────────────────────────

async def enrich(key: str, *, urls: list[str] | None = None, limit: int | None = None,
                 min_price: int | None = None, include_complete: bool = True,
                 verbose: bool = True) -> Stats:
    """
    Fetch details for one source's rows that haven't been fetched yet.

    urls: restrict to these lots (ingest scripts pass the rows they just added).
    min_price: skip lots that sold for less — the high-volume everyday cars.
    include_complete: also fetch rows whose title already gave mileage and
        color. On by default: the page text also feeds PTS, gearbox, interior,
        options and provenance, which a title rarely has.
    """
    src = SOURCES[key]
    stats = Stats()
    if urls is not None and not urls:
        return stats
    rows = await _select_rows(src.name, urls, limit, include_complete, min_price)
    if verbose:
        print(f"[{src.name}] {len(rows)} lot(s) to enrich", flush=True)
    if not rows:
        return stats
    id_by_url = {url: row_id for row_id, url in rows}
    started = time.monotonic()

    watchdog = Watchdog(max(src.deadline, FLUSH_DEADLINE * 2) + STALL_GRACE)

    def progress() -> None:
        watchdog.kick()
        if verbose and stats.fetched and stats.fetched % 100 == 0:
            rate = stats.fetched / (time.monotonic() - started)
            left = (len(rows) - stats.fetched) / rate / 60 if rate else 0
            print(f"  {stats.fetched}/{len(rows)}  mileage +{stats.mileage}  color +{stats.color}"
                  f"  errors {stats.errors}  (~{left:.0f} min left)", flush=True)

    with watchdog:
        await _run(src, rows, id_by_url, stats, progress, watchdog.kick, verbose)
    if verbose:
        print(f"[{src.name}] done — fetched {stats.fetched}, mileage found {stats.mileage}, "
              f"color found {stats.color}, errors {stats.errors}", flush=True)
    return stats


async def _run(src: Source, rows, id_by_url, stats: Stats, progress, kick, verbose: bool) -> None:
    if src.bulk:
        # One long call with no per-lot progress; src.deadline covers the whole re-page.
        bulk = await asyncio.wait_for(_in_daemon_thread(lambda: list(src.bulk())), src.deadline)
        for url, details_text, extra in bulk:
            if url in id_by_url:
                await _record(stats, id_by_url[url], details_text, extra)
                progress()

    elif src.browser:
        async def on_result(url, details_text, extra):
            await _record(stats, id_by_url[url], details_text, extra)
            progress()
        await src.browser([url for _, url in rows], on_result)

    else:
        queue: asyncio.Queue = asyncio.Queue()
        for row in rows:
            queue.put_nowait(row)
        blocked: list[FetchBlocked] = []

        async def worker() -> None:
            while not queue.empty() and not blocked:
                row_id, url = queue.get_nowait()
                try:
                    details_text = await asyncio.wait_for(
                        _in_daemon_thread(src.fetch, url), src.deadline)
                except FetchBlocked as exc:
                    blocked.append(exc)
                    break
                except Exception as exc:
                    kick()  # a failed lot is still activity
                    stats.errors += 1
                    stats.consecutive_errors += 1
                    if verbose:
                        print(f"  ! {url}: {type(exc).__name__}: {exc}", flush=True)
                    if stats.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        blocked.append(FetchBlocked(
                            f"{stats.consecutive_errors} consecutive errors, last: {exc}"))
                        break
                else:
                    stats.consecutive_errors = 0
                    # None: no source for this lot yet; leave it for a later run.
                    if details_text is not None:
                        await _record(stats, row_id, details_text, {})
                    progress()
                await asyncio.sleep(src.delay)

        await asyncio.gather(*(worker() for _ in range(src.workers)))
        if blocked:
            await _flush(stats)
            raise blocked[0]

    await _flush(stats)


DETAIL_FIELDS = ("mileage", "exterior_color", "paint_to_sample")


async def reparse(source: str | None = None, dry_run: bool = False) -> tuple[int, list[dict]]:
    """
    Re-run the parsers over stored details_text. No network. Run after
    improving app/utils/lot_details.py.

    Fields enrichment filled earlier (listed in details_filled) are replaced
    with the new result, even when it is now empty, which is how a parser fix
    removes a bad value. Empty fields are filled. Values from any other source
    are never touched.

    Returns (rows checked, changes) where each change is
    {"id", "field", "old", "new"}.
    """
    sql = f"""SELECT id, details_text, details_filled, {', '.join(DETAIL_FIELDS)}
              FROM auction_results WHERE details_text IS NOT NULL"""
    params = {}
    if source:
        sql += " AND auction_source = :source"
        params["source"] = source
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(text(sql), params)).fetchall()

    changes: list[dict] = []
    updates: list[dict] = []
    for row in rows:
        row_id, details_text, filled_csv = row[0], row[1], row[2]
        current = dict(zip(DETAIL_FIELDS, row[3:]))
        filled = set((filled_csv or "").split(",")) - {""}
        parsed = extract(details_text)
        new = dict(current)
        for f in DETAIL_FIELDS:
            if f in filled or current[f] is None:
                new[f] = parsed[f]
        # A more specific name for the same color wins: a title or older
        # backfill said "Silver", the lot page says "Fluid Silver".
        old_color, page_color = current["exterior_color"], parsed["exterior_color"]
        if (old_color and page_color and "exterior_color" not in filled
                and old_color.lower() != page_color.lower()
                and re.search(rf"\b{re.escape(old_color)}\b", page_color, re.IGNORECASE)):
            new["exterior_color"] = page_color
            filled.add("exterior_color")
        now_filled = {f for f in DETAIL_FIELDS
                      if new[f] is not None and (f in filled or current[f] is None)}
        if new != current or now_filled != filled:
            changes += [{"id": row_id, "field": f, "old": current[f], "new": new[f]}
                        for f in DETAIL_FIELDS if new[f] != current[f]]
            updates.append({"id": row_id, **new,
                            "details_filled": ",".join(sorted(now_filled)) or None})

    if updates and not dry_run:
        async with AsyncSessionLocal() as session:
            await session.execute(text("""
                UPDATE auction_results SET
                    mileage = :mileage, exterior_color = :exterior_color,
                    paint_to_sample = :paint_to_sample, details_filled = :details_filled
                WHERE id = :id"""), updates)
            await session.commit()
    return len(rows), changes
