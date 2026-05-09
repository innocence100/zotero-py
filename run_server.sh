#!/usr/bin/env bash
# Quick-start script for zotero_server (no WebDAV, no Docker)

set -euo pipefail

cd "$(dirname "$0")"

ENV_FILE=".env"
DB_FILE="zotero.db"
PORT="${ZOTERO_PORT:-8080}"

# Load ZOTERO_ADMIN_TOKEN from .env if not already exported
if [ -z "${ZOTERO_ADMIN_TOKEN:-}" ] && [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs -0)
fi

if [ -z "${ZOTERO_ADMIN_TOKEN:-}" ]; then
    echo "Error: ZOTERO_ADMIN_TOKEN not set. Either export it or create $ENV_FILE" >&2
    exit 1
fi

export ZOTERO_ADMIN_TOKEN
export ZOTERO_DATABASE_URL="sqlite+aiosqlite:///./$DB_FILE"

if [ -x ".venv/bin/uvicorn" ]; then
    exec .venv/bin/uvicorn zotero_server.main:app --host 127.0.0.1 --port "$PORT" "$@"
else
    echo "No .venv/bin/uvicorn found. Trying: uv run uvicorn ..."
    exec uv run uvicorn zotero_server.main:app --host 127.0.0.1 --port "$PORT" "$@"
fi
