# Contributing

Thanks for helping. Read [AGENTS.md](AGENTS.md) first: it lists who owns which folder and the
house rules (secrets, visible AI failures, official helpline sources, simple copy).

## Run it

```bash
./scripts/dev.sh          # Temporal + API + worker + web; see docs/SETUP.md
```

## Check before a PR

```bash
(cd backend && uv sync && uv run ruff check && uv run pytest -q)
(cd web && bun install && bun run build)
```

CI (`ops/ci/github-ci.yml`, to be installed as `.github/workflows/ci.yml`) runs the same commands on pushes and pull requests.

## Rules for changes

- Python with `uv`, JavaScript with `bun`. Regenerate pip files with `./scripts/export-requirements.sh`
  after changing `backend/uv.lock`.
- Contracts change together: `backend/app/schemas.py`, `docs/API.md`, `web/src/api/types.ts`.
- Tests use synthetic data only. They must never call the real LLM or Telegram
  (`backend/tests/conftest.py` blanks those settings) and never touch the chaos switches of a running stack.
- Do not log message text, names, phone numbers or tokens. Log ids and derived fields.
- Small PRs with a clear description. Say if you changed a contract.
