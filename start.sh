#!/bin/bash
# Resolve the repo root from this script's location so the script works
# regardless of where the project directory lives or is invoked from.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install frontend dependencies if node_modules is missing or package.json is newer.
if [ ! -d "$ROOT/frontend/node_modules" ] || \
   [ "$ROOT/frontend/package.json" -nt "$ROOT/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm --prefix "$ROOT/frontend" install
fi

osascript -e "tell app \"Terminal\" to do script \"source $ROOT/venv/bin/activate && cd $ROOT/backend && uvicorn app.main:app --reload\""
osascript -e "tell app \"Terminal\" to do script \"cd $ROOT/frontend && npm run dev\""
echo "Servers starting — open http://localhost:5173"
