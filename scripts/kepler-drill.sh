#!/usr/bin/env bash
# Run the worker-crash drill and capture Kepler's window into docs/screenshots/kepler/.
# Run it yourself in Terminal while ./scripts/dev.sh is running (macOS asks once for Screen Recording).
#
#   ./scripts/kepler-drill.sh
#
# 1. opens a test case and kills this checkout's Temporal worker,
# 2. copies the Kepler prompt to the clipboard and opens Kepler,
# 3. each time you press Enter, you click the Kepler window and it is saved as NN-<name>.png,
# 4. restarts the worker and checks /readyz.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${API_URL:-http://127.0.0.1:${PORT:-8000}}"
OUT="$ROOT/docs/screenshots/kepler"
mkdir -p "$OUT"

restart_worker() {
  echo "restarting worker..."
  (cd "$ROOT/backend" && nohup .venv/bin/python -m app.worker >>"$ROOT/logs/worker.log" 2>&1 & echo $! >"$ROOT/.data/worker.pid")
  for _ in $(seq 1 30); do
    curl -sf "$API/readyz" | grep -q '"worker":"ok"' && { echo "worker is back: $(curl -s "$API/readyz")"; return; }
    sleep 2
  done
  echo "worker not polling yet; check logs/worker.log"
}
trap 'echo; restart_worker' INT

curl -sf "$API/readyz" >/dev/null || { echo "API not reachable at $API: start ./scripts/dev.sh first"; exit 1; }
curl -s -XPOST "$API/api/cases" -H 'content-type: application/json' \
  -d '{"person_name":"Drill User","language":"en","situation":"victim","description":"Shared OTP with a caller, 18000 debited","amount_lost_inr":18000}' >/dev/null
sleep 3
"$ROOT/scripts/chaos.sh" kill-worker

PROMPT="Our scam-help app (Cyber Support Navigator) runs locally: API on $API, Temporal on localhost:7233 (UI http://localhost:8233), task queue cybersafe-followups, logs in $ROOT/logs, status script $ROOT/scripts/status.sh. Cases have stopped getting check-ins. Investigate the follow-up pipeline and tell me the root cause and the fix."
printf '%s' "$PROMPT" | pbcopy
open -a Kepler
echo
echo "Kepler prompt copied to the clipboard. Paste it into a new Kepler chat and let it investigate."
echo

n=1
for name in prompt investigating root-cause; do
  read -r -p "Press Enter, then click the Kepler window to capture '$name'... " _
  file="$OUT/$(printf '%02d' "$n")-$name.png"
  screencapture -o -W "$file" && echo "saved $file"
  n=$((n + 1))
done

trap - INT
restart_worker
read -r -p "Optional: ask Kepler to confirm the recovery, then press Enter and click its window (Ctrl-C to skip)... " _ \
  && screencapture -o -W "$OUT/04-recovered.png" && echo "saved $OUT/04-recovered.png"
echo "Done. Commit docs/screenshots/kepler/ and they appear in docs/KEPLER_DRILLS.md."
