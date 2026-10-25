#!/usr/bin/env bash
# One-shot health summary for humans and Kepler.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${API_URL:-http://127.0.0.1:${PORT:-8000}}"
TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-localhost:7233}"
QUEUE="${TASK_QUEUE:-cybersafe-followups}"
echo "== API readyz ($API)"; curl -s -m 5 -w '\nHTTP %{http_code}\n' "$API/readyz" || echo "API unreachable"
echo; echo "== Temporal cluster health"; temporal operator cluster health --address "$TEMPORAL_ADDRESS" 2>&1
echo; echo "== Task queue $QUEUE pollers"
temporal task-queue describe --task-queue "$QUEUE" --address "$TEMPORAL_ADDRESS" 2>&1 | head -20
echo; echo "== Key metrics"; curl -s -m 5 "$API/metrics" | grep -E '^cybersafe_(cases|notifications|chaos|db_up)' || true
echo; echo "== Recent errors/warnings in logs/"
for f in "$ROOT"/logs/*.log; do
  [ -f "$f" ] || continue
  hits=$(grep -E '"level": "(error|warning|critical)"|Traceback|ERROR' "$f" | tail -5)
  [ -n "$hits" ] && { echo "-- $(basename "$f")"; echo "$hits"; }
done
exit 0
