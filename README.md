# Collector Car Tracker

A full-stack web app that tracks collector car auction results and market prices. Porsche-focused in v1, with architecture designed to expand to additional marques (Ferrari, BMW, Mercedes, etc.) in v2.

## Project Goals
- Track sold prices and market trends from major auction houses (BaT, Cars & Bids, RM, Mecum)
- Display model-specific price history and active listings
- Built as a portfolio project demonstrating REST API design, React frontend, and data pipeline architecture

## Tech Stack
- **Backend:** Python, FastAPI, SQLite, pandas
- **Frontend:** React, Recharts
- **Data:** Apify BaT scraper, OldCarsData API
- **Dev Environment:** macOS, VS Code, Claude Code CLI

## Project Structure
## Build Log

### Session 1
- Designed project architecture and data model
- Defined Porsche model taxonomy (911 generations, Cayman/Boxster, SUVs)
- Established controlled vocabulary for makes, models, variants
- Planned multi-marque expansion strategy (brand-agnostic schema from day one)

### Session 2
- Configured Git (global name, email, defaultBranch = main)
- Created project folder structure
- Initialized Git repository
- Added .gitignore
- First commit: `ee494c2`
- Created README.md

### Session 3
- Installed Claude Code CLI
- Set up Python virtual environment and installed FastAPI, SQLAlchemy, pydantic, pandas, uvicorn
- Built FastAPI backend with async SQLAlchemy database setup
- Created SQLAlchemy ORM models: AuctionResult and ActiveListing with full field set including make, model_line, generation, variant, transmission, paint_to_sample, production_number
- Created Pydantic v2 schemas with Create/Read pattern and from_attributes for ORM compatibility
- Built 5 API routes: GET/POST auction-results, GET by id, GET/POST active-listings with query filter support
- Verified all endpoints via FastAPI auto-generated Swagger UI at /docs
- Created seed script with 300 realistic Porsche auction results — generation assigned by model year, variant rules enforced per generation, realistic price ranges per variant, transmission probabilities by era
- Scaffolded React frontend with Vite, installed recharts and axios
- Built React Router architecture with URL-based routing: / → model index, /:model → generation index, /:model/:gen → variant index, /:model/:gen/:variant → market detail page
- Each page has sparkline cards with avg price and sale count
- Market detail page: stats bar (avg/high/low/count), time range toggles (1M/3M/6M/1Y/All), Recharts price history LineChart, results table sorted by date
- Fixed slug round-trip bugs for variants with special characters (GT3 RS 4.0, S/T)
- Added comprehensive variant taxonomy covering all 911 generations (964 through 992) including rare variants: Carrera RS, Carrera RS America, GT3 RS 4.0, GT2 RS, S/T, Sport Classic, Speedster, R, Dakar
- Polished UI: dark theme with warm gold accent (#c4a35a), two-column hero layout, card design improvements, alternating table rows, chart line in gold, active state styling on time range buttons
