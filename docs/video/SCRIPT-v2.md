# Cyber Support Navigator — v2 voiceover script

Female narrator, calm and credible Indian-English documentary read. 240 words, 87.2 s of speech; the film runs 89.7 s.
Generated with Gemini TTS (`gemini-3.8-flash-tts`, voice `en-in-advisor-6`) in one request, sped up 1.06× (`vo/v2f/vo.wav`).
Times are line starts in `video-v2.mp4`, taken from Gemini word timings (`vo/v2f/vo.words.json`). To re-record, hit these marks
(±0.3 s) or re-time `film/src/v2/FilmV2.tsx` and the `t:` values in `film/src/v2/scenes.tsx`.

| Time | Scene | Line |
|---|---|---|
| 0:00 | V1 | "Your KYC expires today. Click this link." "Hi Papa, this is my new number." "This is the CBI. You are under digital arrest." |
| 0:08.7 | V2 | Messages like these reach phones across India every day. And the people they hurt most are often the least sure what to do next. |
| 0:16.7 | V3 | Spotting the fake is only half of it. The panic, the first hour, the days after: that's where people are left alone. |
| 0:23.8 | V4 | So this starts with one question. What's happening right now? |
| 0:27.5 | V5 | Got a message? Paste it in. You get a clear verdict, the reason in plain words, and the real helplines. In English or Hindi, read aloud. |
| 0:36.3 | V6 | Someone on the line? Stop. Hang up. Never share the OTP. |
| 0:40.8 | V7 | Already paid? Call nineteen thirty within the hour. Block your bank and UPI, and report it. Then a case opens, checks in on you, and brings in a human volunteer if you go quiet. |
| 0:52.3 | V8 | Every message hits a rule engine first. Then Gemma 4, running on Jarvislabs GPUs, explains it using official sources only. It can make a warning stronger. Never weaker. |
| 1:03.3 | V9 | Each case runs as a durable Temporal workflow. Plan, check in, escalate. |
| 1:08.6 | V10 | We killed its worker mid-case. The app still said ready, but check-ins had stopped. That's the gap our on-call team catches with Kepler. Restart the worker, and Temporal resumes from history. The missed check-in goes out within a second. |
| 1:22.4 | V11 | Check. Stop. Recover. Help that stays until the case is closed. |
| 1:26.9–1:29.7 | V11 | End card: Cyber Support Navigator · Team CyberSafe · Hack Day Pune 2026 · github.com/zweack/HacktoberFestCyberSafe |

Fact sources: 1930 = national cyber crime helpline, first hour matters most (the app's own copy). The drill facts come from
`docs/KEPLER_DRILLS.md`: worker killed 16:33:03, `/readyz` still "ready", backlog growing, Temporal UI lists the dead worker
as RUNNING, new worker pid 79058 at 16:34:34, missed check-in sent 16:34:35. Kepler is the on-call team's tool and the app
never calls it. The Kepler chat window is not shown because there is no screenshot of it. Telegram, Marathi and guardian
alerts are not shown.
