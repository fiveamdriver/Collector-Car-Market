"""
Dated currency conversion to USD, from ECB reference rates.

Every sold_price in auction_results is USD. A sale in another currency is
converted at the rate of its own sale date, never at one fixed rate: EUR/USD
alone ran from 0.83 to 1.60 over the years this data covers.

The rates are the ECB's daily euro reference rates (data/fx/ecb_eurofxref.csv,
units per 1 EUR). A sale on a weekend or ECB holiday uses the last published
rate before it, up to MAX_GAP_DAYS back. A date outside the file raises, so a
stale table can never quietly price a new sale.
"""
from __future__ import annotations

import bisect
import csv
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

RATES_FILE = Path(__file__).resolve().parents[2] / "data" / "fx" / "ecb_eurofxref.csv"

SUPPORTED = ("USD", "EUR", "GBP", "CHF", "CAD")

# Longest run of days with no ECB fix (Christmas to New Year is the worst).
MAX_GAP_DAYS = 7


class FxError(ValueError):
    """No trustworthy rate for this conversion."""


class FxDateOutOfRange(FxError):
    pass


@lru_cache(maxsize=1)
def _table() -> tuple[list[date], dict[str, list[float]]]:
    dates: list[date] = []
    cols: dict[str, list[float]] = {"USD": [], "GBP": [], "CHF": [], "CAD": []}
    with open(RATES_FILE, newline="") as f:
        for row in csv.DictReader(f):
            dates.append(date.fromisoformat(row["date"]))
            for k in cols:
                cols[k].append(float(row[k]))
    if dates != sorted(dates):
        raise FxError(f"{RATES_FILE} is not sorted by date")
    return dates, cols


def rate_date(on: date) -> date:
    """The ECB fixing date used for a sale on `on`."""
    dates, _ = _table()
    i = bisect.bisect_right(dates, on) - 1
    if i < 0 or on - dates[i] > timedelta(days=MAX_GAP_DAYS):
        raise FxDateOutOfRange(
            f"no ECB rate within {MAX_GAP_DAYS} days before {on} "
            f"(table covers {dates[0]} to {dates[-1]})"
        )
    return dates[i]


def usd_per_unit(currency: str, on: date) -> float:
    """USD value of one unit of `currency` on date `on`."""
    cur = (currency or "").upper()
    if cur not in SUPPORTED:
        raise FxError(f"unsupported currency {currency!r}")
    if cur == "USD":
        return 1.0
    dates, cols = _table()
    i = dates.index(rate_date(on))
    eur_usd = cols["USD"][i]
    if cur == "EUR":
        return eur_usd
    return eur_usd / cols[cur][i]


def to_usd(amount: int | float, currency: str, on: date | None) -> int:
    """Convert `amount` in `currency` on date `on` to whole USD.

    A non-USD amount with no date raises: without a date there is no honest rate.
    """
    if (currency or "").upper() == "USD":
        return round(amount)
    if on is None:
        raise FxError(f"{currency} amount with no sale date")
    return round(amount * usd_per_unit(currency, on))
