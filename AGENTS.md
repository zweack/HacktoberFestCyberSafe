# Working in this repo

Cyber Support Navigator helps elderly and non-technical people in India spot scams,
get out of a scam that is happening, and recover after falling for one.

## Layout and ownership

| Area | Paths | Owner |
|---|---|---|
| Contracts | `backend/app/schemas.py`, `docs/API.md`, `web/src/api/types.ts` | shared; change together |
| Detector | `backend/app/detector/`, `backend/app/directory/`, `backend/app/api/analyze.py`, `backend/app/api/feed.py` | detector |
| Follow-up | `backend/app/workflows/`, `backend/app/notify/`, `backend/app/worker.py`, `backend/app/api/cases.py` | followup |
| Web | `web/` | web |
| Ops | `backend/app/api/ops.py`, `backend/app/api/health.py`, `ops/`, `scripts/`, `docs/KEPLER_RUNBOOK.md` | ops |

Stay inside your area. If you need a contract change, make the smallest additive change
and say so in the PR description.

## Tooling

- Python: `uv` only (`cd backend && uv sync && uv run pytest -q`). Python 3.13.
- JavaScript: `bun` only (`cd web && bun install && bun run dev`).
- Temporal dev server: `temporal server start-dev` (UI on http://localhost:8233).
- No Docker on the dev Mac; `ops/` has Compose files for deployment, `scripts/dev.sh` runs everything natively.

## Rules

- Secrets never go in the repo. LLM credentials load from `~/.config/cybersafe/llm.env`.
- Model failures are visible: `ai_used=false` and `ai_error` set. Never fake an AI answer.
- Helpline numbers and URLs in the directory must carry a `source_url` from an official site.
- Tests must pass before a PR: `uv run pytest -q` and, for web, `bun run build`.
- Copy for elderly users: short sentences, no jargon, tell them exactly what to do next.
