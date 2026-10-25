# v2 scene list — 1920×1080, 30 fps, 89.7 s

Device: a **focus camera** over the real screenshots. It eases to the region being narrated, outlines it in the colour of
that moment and dims the rest. Next to it, one caption at a time echoes the narration. From 0:27 a **flow rail** at the top
(Check → Stop → Recover → Follow-up → Rules + Gemma 4 → Temporal → On-call) shows where we are.
Colours mean something: red = scam/stop, yellow = recover, green = safe/follow-up, blue = the app/system. No cartoon, no gags.
Code: `film/src/v2/` (`kit.tsx` = FocusCam/Shots/Captions/Node/Wire/Code, `scenes.tsx`, `FilmV2.tsx`).

| # | Time | Picture | Focus / highlight |
|---|---|---|---|
| V1 | 0:00 | Three scam notifications stack in: SMS KYC, WhatsApp "new number", video call "CBI · digital arrest" | each card lands on its quote |
| V2 | 0:08.5 | 128 message tiles fill the screen, then dim under "What do I do now?" | |
| V3 | 0:16.4 | Flow: Is it fake? → Panic → First hour → Days after; the last three turn red, "Usually alone." | nodes light on their words |
| V4 | 0:23.5 | Home screen | outlines the three big buttons on "right now" |
| V5 | 0:27.2 | Check-message screen → scam result | message box, verdict (red), plain-words reason, helplines line, हिंदी toggle, Read aloud |
| V6 | 0:36.0 | Home "Someone is talking to me" → STOP screen | the button, then "Hang up" and "Do not share any OTP" |
| V7 | 0:40.5 | Home "I think I've been cheated" → recovery steps → help plan → check-in → coordinator queue | Call 1930, block bank/UPI, report, "We are checking on you", check-in buttons, claimed-by-volunteer row |
| V8 | 0:52.0 | Flow: Message → Rule engine (always first) → Gemma 4 (gemma-4-31b-it · Jarvislabs GPUs) → Verdict; "grounded in official helplines only"; large `llm.py` safety-floor card | the `if _SEVERITY…` line on "never weaker" |
| V9 | 1:03.0 | "Each case: a durable Temporal workflow"; Send the plan → Check in → Escalate; large `followup.py` wait_condition/timeout card | escalate line |
| V10 | 1:08.3 | Real drill captures: status.sh (worker down) → Temporal Task Queue → Kepler product page → status.sh (recovered) → workflow timeline resumed | "killed" header, `/readyz` ready (green), backlog/poller rows (red), dead worker RUNNING (red), restart header + green rows, resumed bars |
| V11 | 1:22.0 | Check / Stop / Recover lights, "Help that stays until the case is closed." → end card | |

Sound (`tools/mix2.py`): VO plus a quiet synthesised pad (D–Bm–G–A), ducked under the voice. It dips during the outage
drill and lifts slightly for the close. Nine subtle cues only: notification ding/pop/buzz on the three hook messages,
soft whooshes at 0:16, 0:23 and 0:52, a low thud at the worker kill, and soft dings at "within a second" and the end card.
Integrated loudness −12 LUFS, peak −1.5 dBFS.
