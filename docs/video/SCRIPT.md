# Cyber Support Navigator — voiceover script (final)

Male narrator, warm Indian-English storyteller, brisk with dry comic timing. ~126 s of speech, ~374 words.
Generated with Gemini TTS (`gemini-3.8-flash-tts`, voice `en-in-assistant-1`) in 4 requests, then sped up 1.19× (`vo/vo.wav`).
Timestamps are where each line starts in the final video (from Gemini word timings). To re-record, hit these marks
(±0.5 s is fine) or re-time `film/src/timeline.ts`.

| Time | Scene | Line |
|---|---|---|
| 0:00 | S01 | Meet Sharma ji. Pune. Retired. Thirty-eight years at a bank. Describes himself as... very tech savvy. |
| 0:07 | S02 | Monday. An SMS. "Your SBI KYC expires today. Click the link." Sharma ji clicks. Twice. To be sure. |
| 0:14 | S03 | Then a very polite man calls, asking for the OTP. Sharma ji reads it out. Slowly. Proudly. "Four. Seven. Two. Beta, are you writing it down?" |
| 0:23 | S04 | Tuesday. WhatsApp. "Hi Papa, new number. Send ten thousand, urgent." Sharma ji has two daughters. He sends it anyway. Just in case. |
| 0:31 | S05 | Wednesday. A video call. "CBI. You are under digital arrest. Do not disconnect." The officer's hat is made of cardboard. Sharma ji salutes it. |
| 0:40 | S06 | Real fact: police never arrest anyone over a video call. But panic is fast. And Sharma ji's glasses are always in the other room. |
| 0:48 | S07 | So we built Cyber Support Navigator. Three moments. Very big buttons. |
| 0:52 | S08 | One. Is this a scam? Paste the message. Get a traffic light, the reason in plain words, what to do, and the real helplines. In English or Hindi. It even reads it out loud. |
| 1:02 | S09 | Two. Someone is talking to me right now. No lecture. Just: Stop. Hang up. Don't share the OTP. Yes, Sharma ji, even if he asks nicely. |
| 1:12 | S10 | Three. I already got cheated. Call nineteen thirty, now. The first hour matters most. Block your bank and UPI. Report it. Then the app opens a case, checks in on you, and if you go quiet, a human volunteer steps in. |
| 1:24 | T11 | Under the hood, a rule engine always runs first. Then Gemma 4, on Jarvislabs GPUs, explains it in plain English or Hindi, using only official helplines. The model can make a verdict more careful. It can never call a scam safe. |
| 1:35 | T12 | The follow-up is a Temporal workflow. Send the plan. Wait for a check-in. No reply? Escalate to a human coordinator. |
| 1:41 | T13 | So we tried to break it. We killed the worker, mid-case. The coordinator resolved it anyway. Worker back up, and Temporal finished the case from history. Nothing lost. |
| 1:50 | T14 | Our ops team watches the live app with Kepler, RubixKube's AI SRE. Health, logs, metrics, chaos switches, a runbook. |
| 1:57 | S15 | Cyber Support Navigator. Check. Stop. Recover. Next time the "CBI" calls, Sharma ji hangs up. Then calls his daughter. On her old number. |
| 2:06–2:09.5 | S15 | (end card hold: repo URL + Hack Day Pune 2026, music tail) |

Accuracy notes: 1930 = national cyber crime helpline; first hour matters most; police never arrest over video call.
Gemma 4 (`gemma-4-31b-it`) runs on Jarvislabs GPUs (not the phone); rule engine first, model can only raise caution.
Temporal runs the follow-up and finished a case after the worker was killed and restarted. Kepler is used by the ops
team on the deployed app (the app does not call Kepler). Telegram check-ins are not mentioned (not tested live).
