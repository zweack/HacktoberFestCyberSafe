# Security

## Reporting a problem

Please do not open a public issue for a security problem. Use GitHub's
"Report a vulnerability" (Security tab → Advisories) on this repository, or contact the
maintainers privately. Include steps to reproduce with synthetic data. We will reply as soon as we can.

## What this demo does and does not protect

- Coordinator and ops endpoints need the shared `STAFF_TOKEN` (header `X-Staff-Token`). Without it
  set, they are open: local development only. There are no user accounts.
- A person's case is reachable by anyone who has its unguessable case link.
- Case details (name, description, amounts, Telegram ids) are stored in SQLite and in Temporal
  workflow history. There is no automatic deletion yet. See the privacy section in the README.
- Digits in a pasted message are masked before it is sent to the AI model; the rest of the text is sent.

## What must never be logged or committed

- `~/.config/cybersafe/llm.env`, any `.env`, API keys, the Telegram bot token
  (the app redacts `bot<token>` from logs; do not paste raw httpx URLs elsewhere).
- Message text, OTPs, phone numbers, names or case descriptions from real people.
- Database files (`backend/data/`, `.data/`) and logs (`logs/`).

If a token was exposed, rotate it with the provider first, then clean up.
