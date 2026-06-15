#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"

cd "$FRONTEND"
npm run build

rm -rf "$BACKEND/static"
cp -r "$FRONTEND/out" "$BACKEND/static"

cd "$BACKEND"
export PATH="${HOME}/.local/bin:${PATH}"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
