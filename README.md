# Cyber Support Navigator (HacktoberFestCyberSafe)

A helper for elderly and non-technical people that answers three questions:

1. **"Is this message a scam?"** Paste or forward an SMS, email, or WhatsApp message.
2. **"Is this happening to me right now?"** Someone is on the phone asking for an OTP or telling you to install an app. The navigator tells you to stop and what to say.
3. **"I already fell for it. What now?"** Exactly who to call (1930, your bank), what to report, and in what order. Then it follows up until you are safe, and brings in a human if you go quiet.

## How the three sponsor tools are used

| Tool | Job |
|---|---|
| **Gemma on Jarvislabs** | Understands the message and explains the risk in plain English or Hindi, grounded in a curated directory of official Indian helplines. Runs on Jarvislabs, not on the person's phone. |
| **Temporal** | Runs the follow-up: sends the action plan, schedules check-ins, retries failed notifications, escalates unanswered cases to a human coordinator. |
| **Kepler** | The ops team's tool for inspecting the deployed service and investigating outages (see `docs/KEPLER_RUNBOOK.md`). |

## Run it locally

```sh
./scripts/dev.sh          # Temporal dev server, API, worker, web
```

Or by hand:

```sh
temporal server start-dev                       # UI: http://localhost:8233
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd backend && uv run python -m app.worker
cd web && bun install && bun run dev            # http://localhost:5173
```

Requirements, secrets and all settings: [`docs/SETUP.md`](docs/SETUP.md). Python dependencies: [`requirements.txt`](requirements.txt) (`pip install -r requirements.txt`).

API reference: [`docs/API.md`](docs/API.md).

## Screenshots

### Mobile (412 × 915)

| | | | |
|---|---|---|---|
| ![Home](docs/screenshots/mobile/01-home.png) Home | ![Check](docs/screenshots/mobile/02-check-message.png) Check a message | ![Scam](docs/screenshots/mobile/03-scam-result.png) Scam result (Gemma 4) | ![STOP](docs/screenshots/mobile/04-happening-now-stop.png) Happening now |
| ![Hindi](docs/screenshots/mobile/05-happening-now-hindi.png) Hindi "digital arrest" | ![Hindi home](docs/screenshots/mobile/06-home-hindi.png) हिंदी home | ![Cheated](docs/screenshots/mobile/07-cheated.png) I've been cheated | ![Plan](docs/screenshots/mobile/08-case-plan.png) Help plan |
| ![Check-in](docs/screenshots/mobile/09-case-checkin.png) Check-in | ![Inbox](docs/screenshots/mobile/10-inbox.png) Simulated inbox | ![Message](docs/screenshots/mobile/11-inbox-message.png) Message verdict | |

### Desktop (1440 × 810)

| | |
|---|---|
| ![Home](docs/screenshots/desktop/01-home.png) Home | ![Scam result](docs/screenshots/desktop/02-scam-result.png) Scam result |
| ![STOP](docs/screenshots/desktop/03-happening-now-stop.png) Happening now | ![Cheated](docs/screenshots/desktop/04-cheated.png) I've been cheated |
| ![Case](docs/screenshots/desktop/05-case.png) Help plan | ![Inbox](docs/screenshots/desktop/06-inbox.png) Simulated inbox |
| ![Coordinator](docs/screenshots/desktop/07-coordinator.png) Coordinator queue | ![Ops](docs/screenshots/desktop/08-ops.png) Ops status and chaos switches |
| ![Temporal](docs/screenshots/desktop/09-temporal-workflows.png) Temporal: case workflows | ![Timeline](docs/screenshots/desktop/10-temporal-case-timeline.png) Temporal: escalation and recovery |

Full-length page captures are in [`docs/screenshots/full`](docs/screenshots/full).
