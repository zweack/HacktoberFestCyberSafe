# Version C: "Live demo". Narration

Voice: Gemini TTS `en-in-commercial-5` (female, en-IN), one request. Processing: pauses over 0.6 s trimmed to 0.4 s, atempo 1.08, loudnorm -16 LUFS. The VO starts 0.3 s into the film.

| Film time | Line |
|---|---|
| 0:00.3 | Fake bank alerts, fake police calls, fake family emergencies. Cyber Support Navigator helps older people in India spot them. In the practice inbox, scams are already flagged. |
| 0:11.4 | Paste a message and tap Check. Red light: scam. Do not click the link. Then a plain reason, what to do now, and official helplines, in English or Hindi, read aloud. |
| 0:22.6 | Someone on the phone right now? One tap shows a giant STOP. Hang up. No OTP, no apps, no money. |
| 0:30.7 | Money already gone? Call nineteen thirty now, block your bank and UPI, and report it. Then the app keeps checking on you. |
| 0:38.8 | Under the hood, a rule engine always runs first. Then Gemma 4, on Jarvislabs GPUs, explains the risk in plain words, grounded in official helplines. The model can make a verdict more cautious, never less. If it tries, its answer is discarded and the rule-based advice stays. Switch the model off, and the rules still flag the scam. |
| 0:59.1 | Each cheated case is a durable Temporal workflow: it sends the plan, schedules check-ins, retries, and escalates silent cases to a volunteer. |
| 1:07.9 | The ops team runs Kepler, RubixKube's AI SRE app, on the live service. In a drill, we killed the worker mid-case. Readiness still said ready, but check-ins had stopped. That gap is what Kepler catches. We restarted the worker, Temporal resumed from history, and the missed check-in went out one second later. |
| 1:25.9 | Cyber Support Navigator. Help before, during and after a scam. |

Word timings: `vo/vo.words.json` (transcript seconds; film time = 0.3 + t × 1.06 / 1.08, see `T()` in `film/src/final/kitC.tsx`).
