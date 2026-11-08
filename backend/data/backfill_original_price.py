#!/usr/bin/env python3
"""
Re-price RM Sotheby's and Bonhams results at the ECB rate of their sale date.

Both ingests used to convert every non-USD sale at one fixed rate (EUR 1.09,
GBP 1.27, CHF 1.13, CAD 0.73) whatever the year, and kept only the USD figure.
This re-reads each source's search API (bulk JSON, no lot pages), matches rows
by auction_url, records the stated amount and currency, and re-converts with
app/utils/fx.py.

    python data/backfill_original_price.py            # dry run -> plan + CSV report
    python data/backfill_original_price.py --apply PLAN.json

Dry run writes, under ~/Projects/CollectorCarMarket-data/reports/:
  fx_backfill_<stamp>.json  the plan: every row it would change, with old values
  fx_backfill_<stamp>.csv   the same, one line per row, for review
--apply executes exactly that reviewed plan. Each row is updated only if its
sold_price / original_* still equal the plan's "old" values, so anything edited
since the dry run is left alone and reported. An undo file is written first.

Rows are changed only when the source amount reproduces the stored price under
the old rule (amount x old fixed rate, or amount for USD). A mismatch means the
row was corrected by hand or by another migration: it is reported, not touched.
Run data/migrate_add_original_price.py --apply first.
"""
import asyncio
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

import certifi

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "data"))

from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.utils import fx  # noqa: E402
import bonhams_ingest as bonhams  # noqa: E402
import rms_ingest as rms  # noqa: E402

REPORT_DIR = Path.home() / "Projects" / "CollectorCarMarket-data" / "reports"
SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = "CollectorCarMarket-fx-backfill/1.0 (+https://github.com/fiveamdriver/Collector-Car-Market)"

# The rates the old ingests applied, needed to prove a stored price came from them.
OLD_FIXED = {"USD": 1.00, "EUR": 1.09, "GBP": 1.27, "CHF": 1.13, "CAD": 0.73}


# ── Source reads ──────────────────────────────────────────────────────────────

def rm_prices() -> dict[str, tuple[int, str]]:
    """auction_url -> (amount, currency) for every sold RM Porsche lot."""
    out: dict[str, tuple[int, str]] = {}
    page = 0
    while True:
        body = json.dumps({"LocationCountry": [], "OfferStatus": None, "SortBy": "Availability",
                           "CategoryTag": [], "search": "", "make": "Porsche"}).encode()
        req = urllib.request.Request(
            f"{rms.SEARCH_URL}?page={page}&pageSize={rms.PAGE_SIZE}", data=body, method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/json;charset=UTF-8",
                     "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
            payload = json.loads(resp.read().decode())
        items = payload.get("items", [])
        total_pages = (payload.get("pager") or {}).get("totalPages", 0)
        for it in items:
            if not (it.get("sold") and it.get("auctioned") and it.get("link")):
                continue
            parsed = rms.parse_price(it.get("value") or "")
            if parsed:
                out[rms.lot_url_for(it["link"])] = parsed
        print(f"  RM page {page + 1}/{total_pages}: {len(out)} priced lots so far", flush=True)
        if not items or page + 1 >= total_pages:
            return out
        page += 1
        time.sleep(2)


def bonhams_key() -> str:
    req = urllib.request.Request(bonhams.RESULTS_PAGE, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'"TYPESENSE"\s*:\s*\{.*?"apiKey"\s*:\s*\{(.*?)\}', html)
        km = m and bonhams._KEY_RE.search(m.group(1))
        if km:
            return km.group(1)
    except Exception as exc:
        print(f"  Bonhams key read failed ({exc}); using the stored key")
    return bonhams.TYPESENSE_KEY_FALLBACK


def bonhams_prices() -> dict[str, tuple[int, str]]:
    out: dict[str, tuple[int, str]] = {}
    key = bonhams_key()
    page, seen = 1, 0
    while True:
        body = json.dumps({"searches": [{
            "collection": "lots", "q": "porsche", "query_by": "title",
            "filter_by": f"department.code:{bonhams.CAR_DEPT_CODE} && status:SOLD",
            "per_page": bonhams.PAGE_SIZE, "page": page}]}).encode()
        req = urllib.request.Request(
            bonhams.TYPESENSE_HOST + bonhams.TYPESENSE_PATH, data=body, method="POST",
            headers={"Content-Type": "application/json", "x-typesense-api-key": key, "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
            result = json.loads(resp.read().decode())["results"][0]
        if result.get("error"):
            raise RuntimeError(f"Typesense error: {result['error']}")
        docs = [h["document"] for h in result.get("hits", [])]
        for doc in docs:
            url = bonhams.build_lot_url(doc)
            price = doc.get("price") or {}
            local = price.get("hammerPremium") or price.get("hammerPrice")
            if url and local and local > 0:
                cur = ((doc.get("currency") or {}).get("iso_code") or "USD").upper()
                out[url] = (float(local), cur)  # unrounded: the old ingest multiplied the raw value
        seen += len(docs)
        print(f"  Bonhams page {page}: {len(out)} priced lots so far", flush=True)
        if not docs or seen >= result.get("found", 0) or len(docs) < bonhams.PAGE_SIZE:
            return out
        page += 1
        time.sleep(1)


# ── Planning (pure; unit-tested) ──────────────────────────────────────────────

def plan_row(row: dict, source: tuple[int, str] | None) -> dict:
    """Decide what to do with one DB row given the source's (amount, currency).

    Returns a dict with "action" in {"update", "unchanged", "skip"} and a reason.
    "update" carries the new values; "unchanged" means only original_* would be
    filled, which is still an update of those two columns.
    """
    base = {"id": row["id"], "source": row["auction_source"], "url": row["auction_url"],
            "sold_date": str(row["sold_date"]) if row["sold_date"] else None,
            "old": {"sold_price": row["sold_price"], "original_price": row["original_price"],
                    "original_currency": row["original_currency"]}}
    if source is None:
        return {**base, "action": "skip", "reason": "not found in source"}
    amount, cur = source
    if cur not in OLD_FIXED:
        return {**base, "action": "skip", "reason": f"currency {cur} not supported"}
    stated = round(amount)  # whole units, as stored in original_price
    if (row["original_price"], row["original_currency"]) == (stated, cur):
        return {**base, "action": "skip", "reason": "already done"}
    if row["sold_price"] != round(amount * OLD_FIXED[cur]):
        return {**base, "action": "skip", "currency": cur, "amount": amount,
                "reason": f"stored {row['sold_price']} != {amount} {cur} x {OLD_FIXED[cur]} (edited since ingest?)"}
    try:
        new_usd = fx.to_usd(amount, cur, row["sold_date"])
    except fx.FxError as exc:
        return {**base, "action": "skip", "currency": cur, "amount": amount, "reason": str(exc)}
    new = {"sold_price": new_usd, "original_price": stated, "original_currency": cur}
    action = "update" if new_usd != row["sold_price"] else "unchanged"
    return {**base, "action": action, "currency": cur, "amount": amount, "new": new,
            "rate_date": str(fx.rate_date(row["sold_date"])) if cur != "USD" else None}


# ── Main ──────────────────────────────────────────────────────────────────────

async def load_rows() -> list[dict]:
    async with AsyncSessionLocal() as s:
        cols = {r[0] for r in (await s.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'auction_results'"))).all()}
        # The dry run works before migrate_add_original_price.py has run (both read as NULL);
        # --apply needs the columns.
        orig = ("original_price, original_currency" if "original_price" in cols
                else "NULL::int AS original_price, NULL::text AS original_currency")
        res = await s.execute(text(
            f"SELECT id, auction_source, auction_url, sold_date, sold_price, {orig} "
            "FROM auction_results WHERE auction_source IN ('RM Sotheby''s', 'Bonhams') ORDER BY id"))
        return [dict(r._mapping) for r in res]


async def dry_run() -> None:
    rows = await load_rows()
    print(f"DB rows: {len(rows)} (RM + Bonhams). Reading sources...")
    src = {**rm_prices(), **bonhams_prices()}
    plans = [plan_row(r, src.get(r["auction_url"])) for r in rows]

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    plan_path = REPORT_DIR / f"fx_backfill_{stamp}.json"
    csv_path = REPORT_DIR / f"fx_backfill_{stamp}.csv"
    plan_path.write_text(json.dumps({"created": stamp, "rows": plans}, indent=1))
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "action", "sold_date", "currency", "amount", "old_usd", "new_usd",
                    "change_pct", "reason", "url"])
        for p in plans:
            old = p["old"]["sold_price"]
            new = (p.get("new") or {}).get("sold_price")
            pct = f"{(new - old) / old * 100:+.1f}" if new and old else ""
            w.writerow([p["id"], p["source"], p["action"], p["sold_date"], p.get("currency", ""),
                        p.get("amount", ""), old, new or "", pct, p.get("reason", ""), p["url"]])

    from collections import Counter
    acts = Counter((p["source"], p["action"]) for p in plans)
    print("\nPlan by source and action:")
    for (s, a), n in sorted(acts.items()):
        print(f"  {s:14} {a:10} {n}")
    cur = Counter(p["currency"] for p in plans if p["action"] == "update")
    print(f"Price changes by currency: {dict(cur)}")
    reasons = Counter("stored price mismatch" if p["reason"].startswith("stored") else p["reason"]
                      for p in plans if p["action"] == "skip")
    print(f"Skip reasons: {dict(reasons)}")
    ups = sorted((p for p in plans if p["action"] == "update"),
                 key=lambda p: abs(p["new"]["sold_price"] - p["old"]["sold_price"]), reverse=True)
    print("\nLargest 15 price changes:")
    for p in ups[:15]:
        o, n = p["old"]["sold_price"], p["new"]["sold_price"]
        print(f"  id {p['id']:>6} {p['sold_date']} {p['amount']:>11,} {p['currency']}  "
              f"${o:>11,} -> ${n:>11,} ({(n - o) / o * 100:+.1f}%)")
    print(f"\nPlan:   {plan_path}\nReport: {csv_path}\nNothing written to the database.")
    await engine.dispose()


async def apply(plan_path: str) -> None:
    plan = json.loads(Path(plan_path).read_text())
    todo = [p for p in plan["rows"] if p["action"] in ("update", "unchanged")]
    undo_path = Path(plan_path).with_name(Path(plan_path).stem + "_undo.json")
    undo_path.write_text(json.dumps({str(p["id"]): p["old"] for p in todo}, indent=1))
    print(f"Undo file: {undo_path}")
    done = stale = 0
    async with AsyncSessionLocal() as s:
        for p in todo:
            o, n = p["old"], p["new"]
            res = await s.execute(text(
                "UPDATE auction_results SET sold_price = :np, original_price = :nop, original_currency = :noc "
                "WHERE id = :id AND sold_price IS NOT DISTINCT FROM :op "
                "AND original_price IS NOT DISTINCT FROM :oop AND original_currency IS NOT DISTINCT FROM :ooc"),
                {"id": p["id"], "np": n["sold_price"], "nop": n["original_price"], "noc": n["original_currency"],
                 "op": o["sold_price"], "oop": o["original_price"], "ooc": o["original_currency"]})
            if res.rowcount == 1:
                done += 1
            else:
                stale += 1
                print(f"  id {p['id']}: changed since the dry run, left alone")
        await s.commit()
    print(f"Updated {done} rows; {stale} left alone.")
    await engine.dispose()


if __name__ == "__main__":
    if "--apply" in sys.argv:
        asyncio.run(apply(sys.argv[sys.argv.index("--apply") + 1]))
    else:
        asyncio.run(dry_run())
