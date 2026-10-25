#!/usr/bin/env bash
# Run the whole stack natively on macOS. Ctrl-C stops everything this script started
# (a Temporal dev server we start is left alone only if KEEP_TEMPORAL=1).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-localhost:7233}"
mkdir -p "$ROOT/logs" "$ROOT/.data" "$ROOT/backend/data"
PIDS=()

cleanup() {
  echo; echo "stopping: ${PIDS[*]:-none}"
  for pid in "${PIDS[@]:-}"; do [ -n "$pid" ] && kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

temporal_ok() { temporal operator cluster health --address "$TEMPORAL_ADDRESS" >/dev/null 2>&1; }

if temporal_ok; then
  echo "temporal: already healthy at $TEMPORAL_ADDRESS (reusing)"
else
  echo "temporal: starting dev server"
  temporal server start-dev --db-filename "$ROOT/.data/temporal.db" --log-level warn \
    --log-format json >>"$ROOT/logs/temporal.log" 2>&1 &
  [ "${KEEP_TEMPORAL:-0}" = 1 ] || PIDS+=($!)
  for _ in $(seq 1 30); do temporal_ok && break; sleep 1; done
  temporal_ok || echo "temporal: WARNING not healthy yet, see logs/temporal.log"
fi

cd "$ROOT/backend"
uv sync -q
uv run uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --no-access-log \
  >>"$ROOT/logs/api.log" 2>&1 &
PIDS+=($!)

if [ -f "$ROOT/backend/app/worker.py" ]; then
  uv run python -m app.worker >>"$ROOT/logs/worker.log" 2>&1 &
  PIDS+=($!); echo $! >"$ROOT/.data/worker.pid"
else
  echo "worker: backend/app/worker.py not present yet, skipping"
fi

if [ -f "$ROOT/web/package.json" ]; then
  (cd "$ROOT/web" && bun install --silent && exec bun run dev --port "$WEB_PORT" --strictPort) \
    >>"$ROOT/logs/web.log" 2>&1 &
  PIDS+=($!)
else
  echo "web: web/package.json not present yet, skipping"
fi

cat <<MSG

  API        http://127.0.0.1:$PORT   (readyz: /readyz, metrics: /metrics, docs: /docs)
  Web        http://localhost:$WEB_PORT
  Temporal   $TEMPORAL_ADDRESS   UI http://localhost:8233
  Logs       $ROOT/logs/{api,worker,web,temporal}.log
  Ctrl-C to stop.
MSG
wait
