# Exchange rates

`ecb_eurofxref.csv` — European Central Bank euro foreign exchange reference
rates, one row per ECB business day, 1999-01-04 onward. Values are units of
each currency per 1 EUR, exactly as published (only the USD, GBP, CHF and CAD
columns are kept).

Source: https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip
Downloaded 2026-11-08 (last row 2026-11-06).

`app/utils/fx.py` reads this file to convert a sale price to USD at the rate of
its sale date. To extend it, download the zip again and re-run the trim:
keep `Date,USD,GBP,CHF,CAD`, drop rows with `N/A`, sort by date.

A sale dated after the last row raises `FxDateOutOfRange` rather than
silently using a stale rate; refresh the file before ingesting newer sales.
