# Production Readiness Audit

**Date:** 2026-06-11  
**Scope:** Full codebase — backend (FastAPI/SQLAlchemy), data pipeline (BaT/OCD ingest), frontend (React/Vite)

---

## Summary

13 files changed. The most critical issues were hardcoded secrets/paths scattered across 7 files and a data pipeline that was writing to the wrong database entirely. Secondary issues included missing schema validation, a silent error handler masking API failures, dead code, and an untyped stats endpoint.

---

## Issues Found and Fixed

### 1. Hardcoded Database Path and API URLs (Critical)

**Risk:** Any path change (e.g. moving the project directory, changing the DB location) requires hunting down and editing 7 separate files. Secrets accidentally committed to version control if the DB is ever on a remote host.

**Files affected:** `app/database.py`, `app/main.py`, `data/bat_ingest.py`, `data/ocd_ingest.py`, `data/seed.py`, `data/migrate_color.py`, `data/migrate_thumbnail.py`, `frontend/src/api/client.js`

**Fix:**
- Created `backend/app/config.py` — the single source of truth for all environment-specific values. Uses `python-dotenv` (already in `requirements.txt`) to load from `backend/.env`.
- Created `backend/.env` with `DATABASE_URL`, `DATABASE_PATH`, and `CORS_ORIGINS`.
- Created `backend/.env.example` and `frontend/.env.example` — committed templates with no real values, so new developers know what to fill in.
- All 7 Python files now import from `app.config` instead of defining their own values.
- `frontend/src/api/client.js` now reads `import.meta.env.VITE_API_BASE_URL` from `frontend/.env`.
- `.gitignore` already correctly excludes `.env` files — no change needed.

### 2. Wrong Database Path in ocd_ingest.py (Critical — Silent Data Loss)

**Risk:** `ocd_ingest.py` constructed its database URL as:
```python
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BACKEND_DIR, 'pcarmarket.db')}"
```
This resolves to `backend/pcarmarket.db` — a 0-byte empty file — not the live database at `~/pcarmarket-data/pcarmarket.db`. Any OCD ingest run would insert records into the wrong database and silently appear to succeed.

**Fix:** Removed the inline `DATABASE_URL` and `engine` definitions. `ocd_ingest.py` now imports `engine`, `AsyncSessionLocal`, and `Base` from `app.database`, the same as every other script.

### 3. Duplicate engine/AsyncSession Definitions (High)

**Risk:** `bat_ingest.py`, `ocd_ingest.py`, and `seed.py` each defined their own SQLAlchemy `engine` and `AsyncSession` factory. This bypassed the WAL-mode pragma and `busy_timeout` configuration set up in `app/database.py`, and meant changes to connection settings had to be made in 4 places.

**Fix:** All three scripts now import `engine` and `AsyncSessionLocal` directly from `app.database`. The WAL pragma event handler in `database.py` fires automatically on any connection from any engine pointing to the same URL.

### 4. Wrong Database Path in Summary Print (Medium)

**Risk:** `bat_ingest.py` printed:
```python
db_path = os.path.join(BACKEND_DIR, "pcarmarket.db")
print(f"Database: {db_path}")
```
This displayed `backend/pcarmarket.db` — a different path from where data was actually written. Misleading output makes debugging and auditing harder.

**Fix:** Replaced with `print(f"Database: {DATABASE_PATH}")` using the value from `app.config`.

### 5. Missing is_widebody Field in Schema (High — Silent Data Truncation)

**Risk:** `AuctionResult` model has `is_widebody: Mapped[Optional[bool]]`, but `AuctionResultCreate` did not include this field. Any record created via the POST endpoint would silently drop `is_widebody`, even if the caller provided it. The Pydantic model would accept it but `model_dump()` would not include it.

**Fix:** Added `is_widebody: Optional[bool] = None` to `AuctionResultCreate`.

### 6. No Validation on auction_results Schema Fields (High — Data Integrity)

**Risk:** The `AuctionResultCreate` schema accepted any integer for `year` and `sold_price`, and any string for `transmission`. A typo or off-by-one in a parser could insert `year=202` or `sold_price=-1` without any error.

**Fix:** Added Pydantic `@field_validator`s to `AuctionResultCreate`:
- `year`: must be in the range 1950–2030. Rejects clearly wrong years from title-parsing bugs.
- `sold_price`: must be > 0. Guards against zero-price records that would skew averages.
- `mileage`: must be ≥ 0 if provided.
- `transmission`: enforced via `Literal["PDK", "Manual"]` type — Pydantic rejects any other value at the API boundary. Also added `TransmissionType` alias used by both `AuctionResultCreate` and `ActiveListingCreate`.

Note: The data pipeline writes directly via SQLAlchemy ORM, bypassing these validators. The validators protect the REST API entry point. Future work: add equivalent validation in `map_record()` before DB insertion.

### 7. transmission Normalization in ocd_ingest.py (Medium)

**Risk:** `ocd_ingest.py`'s `normalize_transmission()` returned lowercase `"manual"` and `"pdk"`, but the database now stores `"Manual"` and `"PDK"` (normalized in a previous migration). Any OCD ingest run would have inserted lowercase values, causing mixed casing in the `transmission` column and breaking the frontend filter display.

**Fix:** Updated `normalize_transmission()` to return `"PDK"` and `"Manual"`.

### 8. CORS: Hardcoded Origin and Overly Broad Methods (Medium — Security)

**Risk:** `allow_origins=["http://localhost:5173"]` was hardcoded inline. `allow_methods=["*"]` permitted DELETE, PATCH, and PUT requests from browser origins — methods that don't exist on this API and should never be issued cross-origin.

**Fix:**
- Origins now read from `CORS_ORIGINS` in `app.config` (sourced from `.env`).
- `allow_methods` changed to `["GET"]`. The POST endpoints in `listings.py` are internal data-pipeline tools; the frontend only reads. CORS restricts browser-to-server requests — curl and the ingest scripts are unaffected.

### 9. No Ordering on Auction Results Query (Medium)

**Risk:** `GET /auction-results` returned rows in arbitrary insertion order. Frontend pages that display recent sales would show results in a random order that changed across requests if new records were inserted between loads.

**Fix:** Added `.order_by(AuctionResult.sold_date.desc())` to the query. Newest records are always returned first within the `limit` window.

### 10. Untyped Stats Endpoint (Low)

**Risk:** `GET /stats/model-lines` had no `response_model`, so FastAPI performed no serialization or validation on the response. Bugs in the aggregation logic could return malformed JSON silently.

**Fix:** Added a `ModelLineStats` Pydantic model and wired it as `response_model=list[ModelLineStats]`. Added `ge=1` to the `limit` query parameter on `list_auction_results` (previously only had `le=10000`).

### 11. Silent Error Swallowing in MarketHome (Low — Observability)

**Risk:**
```javascript
fetchModelLineStats().catch(() => {})
```
Any API failure on the home page — network down, backend crash, mismatched response shape — would be silently ignored. The cards would show no stats with no indication of why.

**Fix:** Changed to `.catch(err => console.error('Failed to load model line stats:', err))`. Errors surface in the browser console for developers without showing a broken UI to users.

### 12. Dead Code: GEN_IMAGES in GenerationIndex (Low)

**Risk:** `GenerationIndex.jsx` defined a `GEN_IMAGES` constant mapping generation names to image file paths, then commented out the only usage. The constant was never referenced and the images it pointed to (959.jpg, 993.jpg) were deleted from the repo.

**Fix:** Removed the `GEN_IMAGES` object and the associated commented-out JSX block.

### 13. Missing Docstrings on Core Parser Functions (Low)

**Risk:** `parse_variant`, `parse_gbody_variant`, `parse_cayman_boxster_variant`, `parse_transmission`, `fetch_page`, and `map_record` in `bat_ingest.py` had no docstrings. The G-Body parser in particular has a non-obvious priority chain that requires explanation to be safely modified.

**Fix:** Added docstrings to all six functions explaining their logic, priority order, and edge cases (e.g. why `parse_gbody_variant` takes `year`, why `parse_cayman_boxster_variant` uses word-boundary regex for `R` and `S`).

---

## Issues Noted — Not Fixed in This Pass

These issues were identified but left for a dedicated follow-up to avoid scope creep:

**SubGenerationIndex over-fetches:** `SubGenerationIndex.jsx` calls `fetchAuctionResults({ model_line })` to load all records for a model (up to 10,000) and then filters client-side down to the 2–3 sub-generations it actually needs. The right fix is a multi-value `generation` filter on the API (`generation__in`), which requires a backend query change and frontend contract update.

**Schema validation not enforced at ingest:** Pydantic validators in `AuctionResultCreate` only fire on the REST API. The bulk ingest pipeline bypasses them by writing directly through SQLAlchemy. Validation logic should be duplicated or extracted into a shared function called from both `map_record()` and the schema.

**No rate limiting:** The API has no rate limiting. At production traffic levels with a public URL, the `/auction-results` endpoint could be abused to extract the full dataset. Mitigation: add `slowapi` or a reverse-proxy rate limit before making the backend public.

**PropTypes / TypeScript:** React components have no runtime type checking. The codebase uses `.jsx` throughout. Given React 19's deprecation of the `prop-types` package, the right path is migrating to `.tsx` with TypeScript strict mode rather than adding a deprecated library.

**Empty `app/crud/` directory:** The `crud/` package was scaffolded but never populated. All DB logic currently lives in the route handlers. Either populate it or remove it to avoid confusion for new contributors.

---

## Addendum — 2026-07-10

This document describes the June 11 state of the codebase and has drifted. Corrections:

- **Item 3:** The WAL pragma / `busy_timeout` handler it references no longer exists; the database moved from SQLite to Supabase Postgres, where it would be moot.
- **Item 6:** `TransmissionType` grew a third value (`Automatic`). The Create schemas and their validators were later removed entirely along with the POST endpoints (the API is now read-only); validators on the read path turned one bad row into a 500 for the whole endpoint.
- **Item 8:** CORS was never a real control for the POST endpoints — CORS binds browsers only, not curl/scripts. The endpoints were removed on 2026-07-10.
- **"SubGenerationIndex over-fetches":** the description was wrong — the page passed no `limit` at all and silently computed stats from the API's 500-row default. Fixed 2026-07-10 (`limit: 10000` to match sibling pages).
- A unique index on `auction_results.auction_url` and a composite index `(model_line, generation, variant, sold_date)` were applied to the live database on 2026-07-10.
