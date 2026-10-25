# Demo video script (≈2.5 min)

Setup before recording: `scripts/dev.sh` running, `scripts/chaos.sh reset`, Temporal UI
(:8233) and a terminal open, `CHECKIN_INTERVAL_SECONDS=20` for a fast follow-up loop.

| Time | Screen | Say / do |
|---|---|---|
| 0:00–0:15 | Web home | "Cyber Support Navigator helps older people in India with scams — before, during and after." |
| 0:15–0:40 | **Spot a scam** | Paste a fake "KYC expired, click link" SMS. Show verdict, plain-language reasons, what to do. |
| 0:40–1:05 | **Scam happening now** | Choose "Someone is on the phone asking for OTP". Show the "hang up, don't share OTP" steps and 1930 helpline. |
| 1:05–1:30 | **Already lost money** | Report ₹25,000 lost via UPI. Show the recovery steps (1930, cybercrime.gov.in, bank) and that a case is created. |
| 1:30–1:55 | Temporal UI + terminal | Show the case workflow and its timer. `scripts/chaos.sh kill-worker` → `scripts/status.sh` shows no pollers. Restart the worker; the workflow sends the check-in anyway. Ignore check-ins → case becomes **escalated**, coordinator gets a Telegram alert. |
| 1:55–2:30 | Kepler | `scripts/chaos.sh llm down`. Ask Kepler: *"The scam checker answers got worse. Investigate."* Kepler reads /readyz, /metrics (`cybersafe_chaos_llm_down 1`), api.log `ai_error`. `scripts/chaos.sh llm up`. |
| 2:30–2:40 | Web | "Simple for users, observable and recoverable for the people who run it." |
