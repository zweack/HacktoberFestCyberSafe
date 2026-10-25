# API contract

Base URL in dev: `http://localhost:8000`. JSON bodies follow `backend/app/schemas.py`;
the web app mirrors them in `web/src/api/types.ts`. Change all three together.

## Health (ops)

| Method | Path | Returns |
|---|---|---|
| GET | `/healthz` | `{"status":"ok"}` (process alive) |
| GET | `/readyz` | `{"status":"ready"|"degraded"|"not_ready","checks":{database,temporal,worker,staff_auth,llm}}`; 503 only when not_ready (DB or Temporal down); `degraded` = no worker polling (`worker: "no_pollers"`) |
| GET | `/metrics` | Prometheus text format |
| GET | `/api/ops/chaos` | `ChaosSettings` |
| PUT | `/api/ops/chaos` | body `ChaosSettings` → `ChaosSettings` (staff) |

**Staff** endpoints need header `X-Staff-Token: <STAFF_TOKEN>` when the server has `STAFF_TOKEN` set; otherwise 401.
With `STAFF_TOKEN` unset (local development) they are open and `/readyz` shows `staff_auth: "disabled"`.

## Analysis (detector)

| Method | Path | Body → Returns |
|---|---|---|
| POST | `/api/analyze` | `AnalyzeRequest` → `AnalyzeResponse` |
| GET | `/api/directory?lang=en` | `Contact[]` (curated, India-first) |

`AnalyzeRequest.situation` picks the flow:

- `received`: "Is this message a scam?" → verdict + what not to do.
- `in_progress`: "Someone is on the phone / chatting with me right now" → stop-now instructions first (hang up, don't share OTP, don't install apps).
- `victim`: "I already paid / shared OTP" → urgent recovery steps (1930 within the golden hour, cybercrime.gov.in, bank block) and an offer to open a case.

The rule engine always runs. The LLM refines the explanation when configured; the headline and steps are always
rule-based. Model text that mentions a number or website outside the directory, or contradicts the verdict, is
rejected (`ai_error` set). Digits in the message are masked before it is sent. For `in_progress` and `victim`
the answer waits at most `LLM_URGENT_TIMEOUT_SECONDS` for the model.
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
| POST | `/api/cases` | `CaseCreate` → `Case` (starts `CaseFollowUpWorkflow`). Optional header `Idempotency-Key`: a retry with the same key returns the same case |
| GET | `/api/cases` | `Case[]` (staff) |
| GET | `/api/cases/{id}` | `Case` |
| POST | `/api/cases/{id}/steps/{step_id}/done` | → `Case` |
| POST | `/api/cases/{id}/checkin` | `CheckinResponse` → `Case`; 409 if resolved |
| GET | `/api/notifications?case_id=` | `Notification[]` for one case; without `case_id` (all notifications) staff only |
| GET | `/api/coordinator/queue` | `Case[]` with status `escalated` or `claimed` (staff) |
| POST | `/api/coordinator/cases/{id}/claim` | `CoordinatorAction` → `Case` (staff); 409 if resolved |
| POST | `/api/coordinator/cases/{id}/resolve` | `CoordinatorAction` → `Case` (staff) |

Case endpoints are reachable by anyone with the unguessable case id. If Temporal cannot be reached, the change is
still saved and the response has `followup_pending: true`; the worker retries the start/signal from an outbox
(in order per case, at least once) and clears the flag. No 503 is returned for this.

### CaseFollowUpWorkflow

1. Send the action plan (in-app + Telegram if a chat id is set). Notification activities retry with backoff, in the
   background, so a slow Telegram never delays an answer, escalation or resolve. A claim that arrives during this
   first send is kept (the case does not go back to `checking_in`).
2. Every `CHECKIN_INTERVAL_SECONDS`, send a check-in ("Did you call 1930?").
3. Signals: `checkin_response(CheckinResponse)`, `step_done(step_id)`, `coordinator_claim`, `resolve`.
4. After `MAX_UNANSWERED_CHECKINS` unanswered check-ins, or a `need_help` answer, escalate: case → `escalated`, coordinator notified.
5. Ends when a coordinator resolves it, or when the person answers `done` (their confirmation; remaining steps are
   marked done). Ticking every step does not close the case: it sends a check-in asking the person to confirm.
6. Telegram buttons are signed and only accepted from the chat the case is bound to.
