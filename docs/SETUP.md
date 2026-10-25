# Setup and requirements

Everything runs natively on macOS or Linux. Docker is optional (see `ops/`).

## Quick start (new machine)

```sh
git clone https://github.com/zweack/HacktoberFestCyberSafe.git && cd HacktoberFestCyberSafe
brew install temporal                       # or: curl -sSf https://temporal.download/cli.sh | sh
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://bun.sh/install | bash
mkdir -p ~/.config/cybersafe && cp ops/llm.env.example ~/.config/cybersafe/llm.env && chmod 600 ~/.config/cybersafe/llm.env
# put your Jarvislabs key in ~/.config/cybersafe/llm.env, then:
./scripts/dev.sh                            # open http://localhost:5173
```

## 1. System requirements

| Tool | Version tested | Install |
|---|---|---|
| Python | 3.13 | managed by uv (`uv python install 3.13`) |
| [uv](https://docs.astral.sh/uv/) | 0.11 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Bun](https://bun.sh) | 1.3 | `curl -fsSL https://bun.sh/install \| bash` |
| [Temporal CLI](https://docs.temporal.io/cli) | 1.9 (server 1.32) | `brew install temporal` or `curl -sSf https://temporal.download/cli.sh \| sh` |
| curl, bash | any | preinstalled on macOS |

Accounts (optional; the app works without them, showing rule-based advice and in-app messages):

- **Jarvislabs** Model API key, for Gemma 4 explanations.
- **Telegram** bot token from [@BotFather](https://t.me/BotFather), for check-ins on the phone.

## 2. Python dependencies

The source of truth is `backend/uv.lock`. With uv:

```sh
cd backend
uv sync            # creates .venv with exact locked versions, including dev tools
```

Without uv, use the root `requirements.txt` (same pins, exported from `uv.lock`):

```sh
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt       # runtime: FastAPI, uvicorn, temporalio, httpx, pydantic
pip install -r requirements-dev.txt      # dev tools: pytest, pytest-asyncio, ruff
```

Regenerate all three pip files after changing dependencies (from the repo root; keeps the root header):

```sh
./scripts/export-requirements.sh
```

## 3. Web dependencies

```sh
cd web
bun install        # React 19, react-router 7, Vite, TypeScript (locked in bun.lock)
```

## 4. Secrets and settings

Settings are read from environment variables, `backend/.env`, or `~/.config/cybersafe/llm.env`.
Keep secrets in the last one; it is outside the repo.

```sh
mkdir -p ~/.config/cybersafe
cp ops/llm.env.example ~/.config/cybersafe/llm.env
chmod 600 ~/.config/cybersafe/llm.env
# then edit the file and fill in your keys
```

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | empty | OpenAI-compatible endpoint, e.g. `https://models.jarvislabs.net/v1` |
| `LLM_API_KEY` | empty | Jarvislabs API key |
| `LLM_MODEL` | empty | e.g. `gemma-4-31b-it` (or `gemma-4-26b-a4b-it`) |
| `LLM_REASONING_EFFORT` | `none` | Gemma 4 thinks by default; `none` keeps answers around 1 s |
| `LLM_MAX_TOKENS` | `700` | Upper bound per answer |
| `TELEGRAM_BOT_TOKEN` | empty | Enables Telegram check-ins and the `/start` reply with the chat id |
| `COORDINATOR_TELEGRAM_CHAT_ID` | empty | Where escalations are sent |
| `CHECKIN_INTERVAL_SECONDS` | `60` | Time between check-ins (use 20 for demos) |
| `MAX_UNANSWERED_CHECKINS` | `2` | Unanswered check-ins before a human coordinator is called |
| `STAFF_TOKEN` | empty | Shared secret for coordinator and ops endpoints (`X-Staff-Token`). Empty = open, local development only |
| `LLM_URGENT_TIMEOUT_SECONDS` | `6` | "Happening now" and "I've been cheated" answers wait at most this long for the AI |
| `TEMPORAL_ADDRESS` | `localhost:7233` | Temporal frontend |
| `TEMPORAL_NAMESPACE` | `default` | Temporal namespace |
| `TEMPORAL_TASK_QUEUE` | `cybersafe-followups` | Task queue of the follow-up worker |
| `DATABASE_PATH` | `data/cybersafe.db` | SQLite file (relative to `backend/`) |

List the models your key can use:

```sh
set -a; . ~/.config/cybersafe/llm.env; set +a
curl -s https://models.jarvislabs.net/v1/models -H "Authorization: Bearer $LLM_API_KEY"
```

## 5. Run

```sh
./scripts/dev.sh                               # Temporal + API + worker + web
CHECKIN_INTERVAL_SECONDS=20 ./scripts/dev.sh   # faster check-ins for a demo
STAFF_TOKEN=$(openssl rand -hex 16) ./scripts/dev.sh   # protect coordinator/ops pages
PORT=8020 WEB_PORT=5180 ./scripts/dev.sh       # other ports (e.g. a second checkout)
```

The coordinator and ops pages ask for the staff token once per browser tab when `STAFF_TOKEN` is set.

| What | URL |
|---|---|
| App | http://localhost:5173 |
| Coordinator queue | http://localhost:5173/coordinator |
| Ops status and chaos switches | http://localhost:5173/ops |
| API docs | http://localhost:8000/docs |
| Temporal UI | http://localhost:8233 |

## 6. Verify

From the repo root (each line is independent):

```sh
(cd backend && uv run pytest -q)        # backend tests (never call real LLM/Telegram)
(cd backend && uv run ruff check)       # lint
(cd web && bun run build)               # type-check and build the web app
./scripts/status.sh                     # readiness, Temporal, worker pollers, recent errors
curl -s localhost:8000/readyz           # {"status":"ready","checks":{"database":"ok","temporal":"ok","worker":"ok","staff_auth":"disabled","llm":"configured"}}
```

`/readyz` returns 503 only when the API cannot work (database or Temporal down). If no worker polls the
task queue it stays 200 with `"status":"degraded"` and `"worker":"no_pollers"`: cases are saved, but
check-ins and escalations wait until a worker is back.
