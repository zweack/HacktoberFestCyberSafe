# Scene list — 1920×1080, 30 fps, 2:09.5

Look: flat bold cartoon on dark ink, traffic-light colours as meaning (red scam, green safe/check, yellow recover, blue = our app).
Fonts: Unbounded (display), Helvetica (body), JetBrains Mono (code). 8-frame crossfade into each scene. Source: `film/src/scenes/`.

| # | Time | File | Picture | SFX |
|---|---|---|---|---|
| S01 | 0:00 | S01.tsx | Sharma ji (cartoon: bald, big glasses, moustache, kurta) slides in; tags "Sharma ji", "Pune · Retired", "38 years at a bank"; holds phone upside down on "tech savvy" | whoosh, pops, boing |
| S02 | 0:07 | S02.tsx | MONDAY. Phone buzzes, SMS "Your SBI KYC expires TODAY. Click: sbi-kyc-update.xyz"; giant finger taps twice | buzz, click ×2 |
| S03 | 0:14 | S03.tsx | Split: proud Sharma ji vs. grinning headset scammer ("Sir, just the OTP sir"); digits 4·7·2 pop out; scammer scribbles; notes drift away | buzz, pops, cash |
| S04 | 0:23 | S04.tsx | TUESDAY. WhatsApp "Hi Papa, new number. Send 10,000. URGENT"; family frame "Daughters: 2"; ₹10,000 SENT stamp, money flies | ding, thud, cash |
| S05 | 0:31 | S05.tsx | WEDNESDAY. Video call with "officer" in a taped cardboard CBI hat; flashing DIGITAL ARREST / DO NOT DISCONNECT; Sharma ji sweats and salutes | alarm, boing |
| S06 | 0:40 | S06.tsx | Fact card: "Police never arrest anyone over a video call." Then Sharma ji squinting, arrow: glasses → other room | thud, boing |
| S07 | 0:48 | S07.tsx (mine) | Title "Cyber Support Navigator" + 3 traffic-light dots; real home screenshot in phone; "Very big buttons." | whoosh, pops |
| S08 | 0:52 | S08.tsx | Moment 1 "Is this a scam?": check-message → scam-result screenshot (scrolls); chips Traffic light / Plain words / What to do / Real helplines; Hindi screen slides in; English · हिंदी, Read aloud | click, pops |
| S09 | 1:02 | S09.tsx | Moment 2: screen floods red; STOP. HANG UP. NO OTP. NO APPS. slam in next to the real STOP screen; "Yes, Sharma ji. Even if he asks nicely." | thuds, boing |
| S10 | 1:12 | S10.tsx | Moment 3: "Call 1930" slab, golden-hour clock counting down, Block bank + UPI, Report: cybercrime.gov.in, cheated screenshot; then case-plan + check-in screenshots, "Gone quiet? A human volunteer steps in." | thud, typing, pops, dings |
| T11 | 1:24 | T11.tsx | Pipeline Message → Rule engine → Gemma 4 on Jarvislabs (gemma-4-31b-it) → verdict; code cards rules.py + llm.py (payload model/reasoning_effort, safety floor); model tries to push RED→GREEN, blocked | whoosh, pops, thud |
| T12 | 1:35 | T12.tsx | Step track Send plan → Wait for check-in (timer) → No reply → Escalate to coordinator; followup.py wait_condition/timeout card | dings |
| T13 | 1:41 | T13.tsx | Terminal `./scripts/chaos.sh kill-worker`; worker box cracks red; coordinator queue screenshot; worker back green; real Temporal timeline screenshot "Completed from history"; music drops out for the kill | type, glitch, ding |
| T14 | 1:50 | T14.tsx | Ops page screenshot in a browser frame, "Kepler · RubixKube AI SRE — used by our ops team"; chips Health / Logs / Metrics / Chaos switches / Runbook | pops |
| S15 | 1:57 | S15.tsx | Title + Check / Stop / Recover lights; smug Sharma ji hangs up on "CBI (definitely)"; end card github.com/zweack/HacktoberFestCyberSafe · Hack Day Pune 2026 | pops, thud |

Audio: VO (Gemini TTS) + synthesised SFX (numpy: pop, click, whoosh, buzz, ding, alarm, thud, glitch, typing, cash, boing) +
a synthesised pentatonic pluck bed at 100 BPM, ducked ~55% under the voice, dropping out for the worker kill (`tools/mix.py`).
Cues come from each scene's `CUES_xx` export (`tools/cues.ts`), so the sounds follow the picture timing.
