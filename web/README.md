# Web app

Run these from the `web/` directory (`cd web` from the repo root):

```sh
bun install
bun run dev              # http://localhost:5173, proxies /api, /healthz, /readyz, /metrics to :8000
API_PORT=8020 bun run dev --port 5180   # proxy to an API on another port
VITE_MOCK=1 bun run dev  # demo data only, no backend needed
bun run build            # type-check and build to dist/
```

Demo data is used only with `VITE_MOCK=1`, and then a yellow "Demo data" banner is always shown. Without it,
a failed request shows an error (with "call 1930" advice); it never turns into a sample answer or a fake case.

`/coordinator` and `/ops` ask for the staff token (when the server has `STAFF_TOKEN`) and keep it in
`sessionStorage` for that tab only.

Routes: `/`, `/check`, `/now`, `/cheated`, `/case/:id`, `/inbox`, `/coordinator`, `/ops`; anything else shows a
"Page not found" page.
