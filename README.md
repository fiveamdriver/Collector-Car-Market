# pcarmarket

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
