# Broad Arrow catalogue backfill (2026-11-03)

For lots archive.org never captured. Broad Arrow publishes each sale's full
pre-sale catalogue as a FlipHTML5 flipbook (publisher `kfgkh`) with a public
Download (PDF) button. The user downloads the PDF; nothing here fetches it.

1. `swiftc -O pdftext.swift -o pdftext && ./pdftext <catalogue.pdf> <pages.json>`
   (macOS PDFKit; one text string per PDF page).
2. `python catalogue_parse.py <pages.json> <lots.json>` — per-lot details_text in
   the enrichment format (highlight bullets, Documents/Chassis lines, `\n--\n`,
   essay). Page-based: a lot's title page holds meta + bullets (─ / → markers);
   the essay is on the following pages.
3. `match_catalogue.py` — one-to-one match to DB lots by exact title within the
   sale (prefix only to unclaimed lots; duplicate titles split by mileage). Any
   mileage disagreement >3% is HELD for a human, never written. Paths in it
   point at the session scratchpad — adjust before reuse.
4. Accepted lots are written to cache/broad_arrow_presale/<lot>.json with
   `"source": "catalogue_pdf"`, then `enrich("broad-arrow", urls=...)` and
   `derived.refresh(ids)`.

Review every new PTS flag against its sentence before trusting it.
Do not commit the PDFs (Broad Arrow's copyright).

`commoncrawl_scan.py` lists Common Crawl captures of missing lot pages.
