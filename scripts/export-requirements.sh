#!/usr/bin/env bash
# Regenerate pip-style requirement files from backend/uv.lock (uv stays the source of truth).
#   requirements.txt               runtime deps, for `pip install -r requirements.txt` at the repo root
#   backend/requirements.txt       same runtime deps, for builds that only see backend/
#   backend/requirements-dev.txt   dev tools only (pytest, ruff); install with requirements.txt
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
export_to() { uv export --frozen --no-hashes --no-emit-project "$@"; }
# Keep the hand-written header (leading comment lines) of the root file.
header=$(sed -n '/^#/!q;p' "$ROOT/requirements.txt" 2>/dev/null || true)
{ [ -n "$header" ] && printf '%s\n\n' "$header"; export_to --no-dev --no-header --no-annotate; } >"$ROOT/requirements.txt"
export_to --no-dev >"$ROOT/backend/requirements.txt"
export_to --only-group dev >"$ROOT/backend/requirements-dev.txt"
echo "wrote requirements.txt, backend/requirements.txt, backend/requirements-dev.txt"
