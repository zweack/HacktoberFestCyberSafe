# Web app

```sh
bun install
bun run dev            # http://localhost:5173, proxies /api, /healthz, /readyz, /metrics to :8000
VITE_MOCK=1 bun run dev  # demo data only, no backend needed
bun run build
```

If the API cannot be reached, requests fall back to demo data and a yellow "Demo data" banner shows.
Demo answers always carry `ai_used=false` with an `ai_error` note, so they are never shown as AI results.

Routes: `/`, `/check`, `/now`, `/cheated`, `/case/:id`, `/inbox`, `/coordinator`, `/ops`.
