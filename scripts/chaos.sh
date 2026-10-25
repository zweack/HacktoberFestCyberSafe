#!/usr/bin/env bash
# Fault injection for drills.
#   chaos.sh telegram 0.7 | llm down|up | slow 5000 | reset | show | kill-worker
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${API_URL:-http://127.0.0.1:${PORT:-8000}}"
cur() { curl -sf "$API/api/ops/chaos"; }
put() { curl -sf -X PUT -H 'content-type: application/json' "$API/api/ops/chaos" -d "$1"; echo; }
merge() { cur | python3 -c "import json,sys; d=json.load(sys.stdin); d.update(json.loads(sys.argv[1])); print(json.dumps(d))" "$1"; }
case "${1:-show}" in
  telegram) put "$(merge "{\"telegram_failure_rate\": ${2:?rate 0..1}}")" ;;
  llm) case "${2:?down|up}" in down) put "$(merge '{"llm_down": true}')" ;; up) put "$(merge '{"llm_down": false}')" ;; esac ;;
  slow) put "$(merge "{\"slow_analyze_ms\": ${2:?ms}}")" ;;
  reset) put '{"telegram_failure_rate":0,"llm_down":false,"slow_analyze_ms":0}' ;;
  show) cur; echo ;;
  kill-worker)
    pids=$(pgrep -f 'python -m app.worker' || true)
    [ -n "$pids" ] || { echo "no worker running"; exit 1; }
    echo "killing worker pid(s): $pids"; kill -9 $pids
    echo "restart with: cd $ROOT/backend && uv run python -m app.worker >>$ROOT/logs/worker.log 2>&1 &" ;;
  *) echo "usage: $0 telegram RATE | llm down|up | slow MS | reset | show | kill-worker"; exit 2 ;;
esac
