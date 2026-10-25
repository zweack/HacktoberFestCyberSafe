#!/usr/bin/env bash
# Fault injection for drills.
#   chaos.sh telegram 0.7 | llm down|up | slow 5000 | reset | show | kill-worker
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${API_URL:-http://127.0.0.1:${PORT:-8000}}"
cur() { curl -sf "$API/api/ops/chaos"; }
put() { curl -sf -X PUT -H 'content-type: application/json' -H "X-Staff-Token: ${STAFF_TOKEN:-}" \
  "$API/api/ops/chaos" -d "$1"; echo; }
merge() { cur | python3 -c "import json,sys; d=json.load(sys.stdin); d.update(json.loads(sys.argv[1])); print(json.dumps(d))" "$1"; }
case "${1:-show}" in
  telegram) put "$(merge "{\"telegram_failure_rate\": ${2:?rate 0..1}}")" ;;
  llm) case "${2:?down|up}" in down) put "$(merge '{"llm_down": true}')" ;; up) put "$(merge '{"llm_down": false}')" ;; esac ;;
  slow) put "$(merge "{\"slow_analyze_ms\": ${2:?ms}}")" ;;
  reset) put '{"telegram_failure_rate":0,"llm_down":false,"slow_analyze_ms":0}' ;;
  show) cur; echo ;;
  kill-worker)
    # Only the worker that this checkout's scripts/dev.sh started (its pid file), never others.
    pidfile="$ROOT/.data/worker.pid"
    [ -f "$pidfile" ] || { echo "no $pidfile: start the stack with scripts/dev.sh first"; exit 1; }
    pid=$(cat "$pidfile")
    cmd=$(ps -o command= -p "$pid" 2>/dev/null || true)
    case "$cmd" in *app.worker*) ;; *) echo "pid $pid is not a running worker (stale pid file)"; exit 1 ;; esac
    cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' || true)
    [ -z "$cwd" ] || [ "$cwd" = "$ROOT/backend" ] || { echo "pid $pid runs in $cwd, not this checkout"; exit 1; }
    echo "killing worker pid $pid"; kill -9 "$pid"; rm -f "$pidfile"
    echo "restart with: cd $ROOT/backend && (.venv/bin/python -m app.worker >>$ROOT/logs/worker.log 2>&1 & echo $! >$ROOT/.data/worker.pid)" ;;
  *) echo "usage: $0 telegram RATE | llm down|up | slow MS | reset | show | kill-worker"; exit 2 ;;
esac
