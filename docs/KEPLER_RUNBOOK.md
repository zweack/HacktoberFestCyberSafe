# Kepler runbook — Cyber Support Navigator

For the ops team investigating the deployed app with Kepler (RubixKube AI SRE). Kepler is
operated by a human; the app never calls Kepler. Give Kepler the endpoints, logs and
commands below.

## Service map

```
  elderly user / coordinator (browser)
              │
              ▼
   ┌───────────────────┐  /api, /readyz, /metrics   ┌───────────────────────┐
   │ web  :5173 (dev)  │ ─────────────────────────▶ │ api (FastAPI) :8000   │──▶ LLM (Jarvislabs,
   │      :8080 (nginx)│                            │                       │    OpenAI-compatible)
   └───────────────────┘                            └──────┬─────────┬──────┘
                                                start wf   │         │ read/write
                                                           ▼         ▼
                                  ┌───────────────────────────┐  ┌────────────────────────┐
                                  │ Temporal :7233  UI :8233  │  │ SQLite (WAL)           │
                                  │ queue cybersafe-followups │  │ backend/data/cybersafe │
                                  └────────────┬──────────────┘  │ .db  (/data in Docker) │
                                    poll tasks │                 └──────────▲─────────────┘
                                               ▼                            │
                                  ┌───────────────────────────┐  read/write │
                                  │ worker (python -m         │─────────────┘
                                  │   app.worker)             │──▶ Telegram Bot API
                                  └───────────────────────────┘
```

## Endpoints

| URL | Meaning |
|---|---|
| `GET /healthz` | process alive (always 200) |
| `GET /readyz` | 503 if SQLite or Temporal is unreachable. Otherwise 200 with `status` `ready`, or `degraded` when `checks.worker` = `no_pollers` (no worker polled `cybersafe-followups` in 60 s). Also `checks.staff_auth` = enabled/disabled, `checks.llm` = configured/not_configured |
| `GET /metrics` | Prometheus text |
| `GET/PUT /api/ops/chaos` | fault switches: `telegram_failure_rate` 0..1, `llm_down`, `slow_analyze_ms`. PUT needs header `X-Staff-Token` when `STAFF_TOKEN` is set |

Key series: `cybersafe_http_requests_total{method,path_template,status}`,
`cybersafe_http_request_duration_seconds_sum/_count{method,path_template}`,
`cybersafe_cases{status}`, `cybersafe_notifications{status}`, `cybersafe_db_up`,
`cybersafe_worker_pollers` (workers polling in the last 60 s; 0 = worker down, -1 = Temporal unknown),
`cybersafe_notification_attempts`, `cybersafe_escalations` (from the shared DB, so they include worker retries),
`cybersafe_chaos_*`, `cybersafe_build_info`, `cybersafe_process_uptime_seconds`, plus API-process
counters added via `app.metrics.inc` (e.g. `cybersafe_analyze_total`). `app.metrics` counters incremented in the
**worker** process are not visible here (process-local); use the DB-derived series above.
Average latency per route = `_sum / _count`.

## Logs

Native (`scripts/dev.sh`): `logs/api.log`, `logs/worker.log`, `logs/web.log`, `logs/temporal.log`.
Docker: `docker compose -f ops/docker-compose.yml logs <service>`.

JSON lines: `ts, level, service, logger, msg`, plus extra fields. Access lines
(`logger=app.access`) carry `method, path, status, duration_ms, request_id`. Every response
has an `X-Request-ID` header (incoming one is reused) — grep it across logs to follow a request.

```
grep '"status": 5' logs/api.log | tail
grep '"level": "error"' logs/*.log | tail
grep <request_id> logs/*.log
```

## Temporal

- UI: http://localhost:8233 (namespace `default`)
- `temporal operator cluster health`
- `temporal workflow list --query 'ExecutionStatus="Running"'`
- `temporal workflow show --workflow-id <case workflow_id>` (event history: timers, activity retries)
- `temporal task-queue describe --task-queue cybersafe-followups` — **Pollers empty = no worker**
- `scripts/status.sh` runs cluster health, task-queue pollers, readyz, key metrics and recent log errors
  (workflow list/show are manual). It reads `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_TASK_QUEUE`.

## Symptom → cause → investigate → fix

| Symptom | Likely cause | Ask Kepler / run | Fix |
|---|---|---|---|
| Cases stay `open`, no check-ins sent, workflow tasks pile up; `/readyz` `degraded`, `worker: no_pollers`, `cybersafe_worker_pollers 0` | Worker down | "Are there pollers on task queue cybersafe-followups? When did worker.log last write?" `temporal task-queue describe --task-queue cybersafe-followups`, `cat .data/worker.pid` | Restart worker (`cd backend && uv run python -m app.worker` / `docker compose -f ops/docker-compose.yml restart worker`). Commands the API could not deliver are retried from the outbox. Workflows resume from history — nothing is lost. |
| `/readyz` 503 `temporal: error`; new cases show `followup_pending` | Temporal server down | "Why is readyz failing? Check temporal health and logs/temporal.log" `temporal operator cluster health` | Restart Temporal (`scripts/dev.sh` restarts it; Docker: `restart temporal`). Check disk for `.data/temporal.db`. |
| Analyze responses have `ai_used=false`, `ai_error` set; analyze latency up | LLM endpoint down/slow, bad creds, or `llm_down` chaos | "What's the avg duration of POST /api/analyze over the last 10 min, and what ai_error values appear in api.log?" `curl -s http://127.0.0.1:8000/api/ops/chaos`, `curl -m10 $LLM_BASE_URL/models` | `scripts/chaos.sh llm up`; check Jarvislabs instance; verify `~/.config/cybersafe/llm.env`. Rule-based answers keep working. |
| `cybersafe_notifications{status="failed"}` rising, `attempts` climbing | Telegram API errors, bad token/chat id, or chaos rate | "Which notifications failed, with what last_error?" grep worker.log for telegram; `temporal workflow show` for activity retries | `scripts/chaos.sh telegram 0`; fix `TELEGRAM_BOT_TOKEN`; in-app notifications still delivered. |
| `database is locked`, 500s on writes, `cybersafe_db_up 0` | SQLite locked (stuck writer, non-WAL copy) or disk full | `df -h`, `ls -la backend/data/`, `lsof backend/data/cybersafe.db`, grep `locked` in logs | Free disk; stop stray processes holding the file; restart api + worker. |
| Web shows "can't reach server"; browser console CORS errors | API down, wrong proxy target, or origin not in `CORS_ORIGINS` | "Is the API ready? Are there CORS preflight failures?" `curl -i -H 'Origin: http://localhost:5173' localhost:8000/healthz` | Start API; add origin to `CORS_ORIGINS`; check Vite proxy / `ops/nginx.conf`. |

## Rehearsal drills

Run the stack (`scripts/dev.sh`), then:

1. **Worker crash, Temporal recovery.** Create a case in the web app. `scripts/chaos.sh kill-worker`.
   Kepler prompt: *"Cases have stopped getting check-ins. Investigate the follow-up pipeline and tell me the root cause."*
   Expect: within about a minute `/readyz` turns `degraded` with `checks.worker: no_pollers`, `/metrics` shows
   `cybersafe_worker_pollers 0`, the task-queue backlog grows and worker.log stops. API readiness stays 200 (cases
   are still saved). Restart the worker; `worker` returns to `ok` and the workflow continues from its last event
   (show in UI :8233). `kill-worker` only kills the worker started by this checkout's `scripts/dev.sh` (`.data/worker.pid`).
2. **LLM outage.** `STAFF_TOKEN=... scripts/chaos.sh llm down` (or `slow 8000`). Analyze a message.
   Kepler prompt: *"Users say the scam checker gives less detailed answers and is slow. What changed?"*
   Expect: `cybersafe_chaos_llm_down 1`, `ai_error` in responses, `chaos updated` warning in api.log. Fix: `scripts/chaos.sh llm up`.
3. **Telegram flakiness.** `scripts/chaos.sh telegram 0.7`, create a case with a Telegram chat id.
   Kepler prompt: *"Coordinators aren't getting Telegram alerts reliably. Find out why and how bad it is."*
   Expect: failed notifications gauge rising, activity retries in workflow history. Fix: `scripts/chaos.sh reset`.
