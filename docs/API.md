# API contract

Base URL in dev: `http://localhost:8000`. JSON bodies follow `backend/app/schemas.py`;
the web app mirrors them in `web/src/api/types.ts`. Change all three together.

## Health (ops)

| Method | Path | Returns |
|---|---|---|
| GET | `/healthz` | `{"status":"ok"}` (process alive) |
| GET | `/readyz` | `{"status":"ready"|"not_ready","checks":{database,temporal,llm}}`, 503 when not ready |
| GET | `/metrics` | Prometheus text format |
| GET | `/api/ops/chaos` | `ChaosSettings` |
| PUT | `/api/ops/chaos` | body `ChaosSettings` → `ChaosSettings` |

## Analysis (detector)

| Method | Path | Body → Returns |
|---|---|---|
| POST | `/api/analyze` | `AnalyzeRequest` → `AnalyzeResponse` |
| GET | `/api/directory?lang=en` | `Contact[]` (curated, India-first) |

`AnalyzeRequest.situation` picks the flow:

- `received`: "Is this message a scam?" → verdict + what not to do.
- `in_progress`: "Someone is on the phone / chatting with me right now" → stop-now instructions first (hang up, don't share OTP, don't install apps).
- `victim`: "I already paid / shared OTP" → urgent recovery steps (1930 within the golden hour, cybercrime.gov.in, bank block) and an offer to open a case.

The rule engine always runs. The LLM refines the explanation when configured.
`ai_used=false` + `ai_error` tells the UI the model was unavailable; never hide it.

## Simulated inbox (detector)

| Method | Path | Returns |
|---|---|---|
| GET | `/api/feed` | `FeedMessage[]` newest first, each with `analysis` |
| POST | `/api/feed/next` | delivers the next scripted demo message → `FeedMessage` |
| POST | `/api/feed/reset` | clears the feed |
| GET | `/api/feed/stream` | Server-Sent Events, `event: message` with a `FeedMessage` JSON |

## Cases and follow-up (followup / Temporal)

| Method | Path | Body → Returns |
|---|---|---|
| POST | `/api/cases` | `CaseCreate` → `Case` (starts `CaseFollowUpWorkflow`) |
| GET | `/api/cases` | `Case[]` |
| GET | `/api/cases/{id}` | `Case` |
| POST | `/api/cases/{id}/steps/{step_id}/done` | → `Case` |
| POST | `/api/cases/{id}/checkin` | `CheckinResponse` → `Case` |
| GET | `/api/notifications?case_id=` | `Notification[]` |
| GET | `/api/coordinator/queue` | `Case[]` with status `escalated` or `claimed` |
| POST | `/api/coordinator/cases/{id}/claim` | `CoordinatorAction` → `Case` |
| POST | `/api/coordinator/cases/{id}/resolve` | `CoordinatorAction` → `Case` |

### CaseFollowUpWorkflow

1. Send the action plan (in-app + Telegram if a chat id is set). Notification activities retry with backoff.
2. Every `CHECKIN_INTERVAL_SECONDS`, send a check-in ("Did you call 1930?").
3. Signals: `checkin_response(CheckinResponse)`, `step_done(step_id)`, `coordinator_claim`, `resolve`.
4. After `MAX_UNANSWERED_CHECKINS` unanswered check-ins, or a `need_help` answer, escalate: case → `escalated`, coordinator notified.
5. Ends when resolved, or when all steps are done and the person confirms.
