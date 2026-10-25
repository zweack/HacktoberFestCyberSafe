Cyber Support Navigator: Scope and Pitch Script
Hack Day Pune project plan: a scam-help assistant for elderly and non-technical people, built with Jarvislabs, Temporal and Kepler.
Vision
A scam-help assistant that tells people whether a message or call is a scam, guides them step by step if they are already caught in one, and keeps following up until the case is resolved.
Target users
Primary: elderly and non-technical users who receive scam SMS, emails, WhatsApp messages and calls.
Secondary: a trusted family member (guardian) who gets alerts.
Operators: a human coordinator who handles unanswered cases, and an operations team that keeps the service running.
Problem
Scams arrive as fake KYC alerts, fake investment and job offers, loan-app harassment, phishing links and "digital arrest" calls. Victims cannot tell real from fake, panic under pressure, and do not know what to do once they are caught. The delay is what costs them money.
Existing tools only flag a number or message, or let you report after the fact. None of them stay with a frightened person through the whole situation.
Objectives
Detect and explain scams in plain language, in English, Hindi and Marathi.
Give immediate, correct next steps to someone mid-scam or after a payment.
Follow up over hours and days, and never leave a case unattended.
Involve family and a human coordinator when needed.
Keep the service reliable, because people use it in a crisis.
In scope (MVP)
Module 1: Scam checker
The user forwards or pastes an SMS, email text or call description into a chat bot (WhatsApp or Telegram).
A classifier identifies the type: digital arrest, KYC/bank, investment, job, loan app or phishing.
The reply gives a verdict, the reason and what to do, in simple language.
Module 2: "I'm being scammed right now" flow
A single button or keyword starts an emergency flow.
It gives short, ordered steps: stop, don't pay, don't share OTPs, hang up, call 1930, inform the bank.
If money has already been sent, it prepares the details needed for reporting (amount, time, transaction ID, scammer's number).
Module 3: Curated guidance directory
A verified set of official contacts and procedures (1930 helpline, the cybercrime portal, bank steps).
The model answers from this directory instead of improvising.
Module 4: Case follow-up (Temporal)
Every reported case becomes a workflow with check-ins, retries on failed notifications, and a wait-for-reply with a timeout.
Unanswered or high-risk cases are escalated to the coordinator.
Module 5: Trusted-contact alert
The user can nominate a family member who is notified on high-risk or active cases.
Module 6: Coordinator view
A simple page listing open and unanswered cases, so a human can call or follow up.
Module 7: Operations monitoring (Kepler)
The team running the service uses Kepler to inspect the deployed app and investigate outages or operational problems.
Privacy and safety
All scanning is opt-in.
OTPs, account numbers and phone numbers are masked before anything goes to the model.
Raw messages are not stored longer than needed.
Low-confidence results go to a human instead of guessing.
Out of scope
Freezing funds, blocking transactions or contacting police on the user's behalf. We prepare and guide, and official channels act.
Secret or automatic monitoring of anyone's phone.
Legal or financial advice beyond pointing to official procedures.
Constraints and assumptions
iOS does not let apps read SMS, and automatic call monitoring is heavily restricted. The MVP works through forwarding, sharing and chat, not background scanning.
Scam detection will not be perfect. The design handles that with a directory-based answer and a human fallback.
Demo data is fake. No real victim data is used.
Future scope
An Android app with consented on-device SMS scanning
Link and domain reputation checks
Voice input for users who cannot type
Integration with official reporting portals
More Indian languages
Role of each tool
Tool
Role
Jarvislabs
A model on a rented GPU understands the message, classifies the scam and explains it in simple language using the curated directory. Running it server-side means it works on any phone.
Temporal
Runs each case as a durable workflow with several activities: classify, fetch guidance, send reply, alert the trusted contact, schedule a check-in, wait for reply, escalate to a coordinator, and close the case. It handles retries and keeps timers alive across crashes.
Kepler
The operations tool for the team running the service, used to inspect the deployed app and investigate outages or operational problems.

Before the pitch, check what Kepler actually shows for your deployed app, and describe only what you see on screen.
How we are different
Detection and guidance together, not just a warning label.
A live mid-scam mode, which most tools lack.
Durable follow-up over days, with human escalation.
Built for the elderly and non-technical, with regional languages and a family guardian.
Run as a reliable service with proper operations monitoring.
Demo flow
A scam message is flagged and explained.
"I've been scammed" starts a case.
The Temporal view shows the workflow steps and a scheduled check-in.
An unanswered case appears on the coordinator page.
The operations view in Kepler.

Pitch script (short version)
Opening
Good [morning/afternoon], everyone. India recorded over 12 lakh financial cyber fraud complaints in the first half of 2026, with losses above Rs 10,000 crore, and Maharashtra had the highest losses (Ministry of Home Affairs data, as reported by The Indian Express). Behind those numbers is a retired person who gets a "digital arrest" call, panics, and has nobody to ask.
The problem
Elderly and non-technical users cannot tell a real message from a fake one, and once caught in a scam they do not know what to do. Today's tools flag a number or take a report afterwards. Nothing stays with a frightened person while it is happening.
Our solution
Cyber Support Navigator does three things. It tells you if a message or call is a scam, and why, in your own language. If you are already in the middle of it, it tells you exactly what to do right now. And it does not forget you: it checks in, alerts a family member, and brings in a real person if you go quiet.
How it works
The understanding runs on Jarvislabs: a model on a rented GPU explains the scam in simple words, using a verified directory, so it works on any phone. Temporal runs the follow-up as a chain of steps with retries, timers and human escalation, so no case is lost. Kepler is how our operations team inspects the deployed service, because help that is down at the wrong moment is no help.
Demo
[Show a scam message flagged, then the "I've been scammed" case in Temporal, then the coordinator page, then Kepler.]
Closing
We are not building another spam filter. We are building the one who stays on the line with you. Thank you.
Likely questions
Why not Truecaller or Google's filters? They flag, but they do not explain, guide someone already in trouble, or follow up.
What if the model is wrong? It answers from a verified directory, and low-confidence cases go to a human.
Why Temporal? The process is multi-day, time-based and depends on services that can fail.
Privacy? Opt-in scanning, masked sensitive data, short retention.


