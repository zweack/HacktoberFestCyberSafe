# Setup and requirements

Everything runs natively on macOS or Linux. Docker is optional (see `ops/`).

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

Without uv, the same pins are exported to plain requirements files:

```sh
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # runtime: FastAPI, uvicorn, temporalio, httpx, pydantic
pip install -r requirements-dev.txt      # tests: pytest, pytest-asyncio
```

Regenerate them after changing dependencies:

```sh
uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt
uv export --frozen --only-group dev --no-hashes --no-emit-project -o requirements-dev.txt
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
| `TEMPORAL_ADDRESS` | `localhost:7233` | Temporal frontend |
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
```

| What | URL |
|---|---|
| App | http://localhost:5173 |
| Coordinator queue | http://localhost:5173/coordinator |
| Ops status and chaos switches | http://localhost:5173/ops |
| API docs | http://localhost:8000/docs |
| Temporal UI | http://localhost:8233 |

## 6. Verify

```sh
cd backend && uv run pytest -q      # backend tests (never call real LLM/Telegram)
cd web && bun run build             # type-check and build the web app
./scripts/status.sh                 # readiness, Temporal, worker pollers, recent errors
curl -s localhost:8000/readyz       # {"status":"ready","checks":{"database":"ok","temporal":"ok","llm":"configured"}}
```
