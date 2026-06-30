"""
Central configuration for all backend modules.

All environment-specific values (database paths, CORS origins, API keys) must
be read from here. Modules must never hardcode these values inline.

Local development: copy .env.example to .env and fill in values.
Production: set the variables in the deployment environment directly.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve the .env file relative to this file so scripts run from any cwd.
_env_file = Path(__file__).parent.parent / ".env"
load_dotenv(_env_file)

# Async SQLAlchemy URL used by the FastAPI app and data-pipeline scripts.
DATABASE_URL: str = os.environ["DATABASE_URL"]

# Raw filesystem path for migration scripts that use sqlite3 directly (SQLite only).
DATABASE_PATH: str = os.environ.get("DATABASE_PATH", "")

# Comma-separated allowed CORS origins.  Multiple values are supported for
# environments that run the frontend on a non-default port.
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
