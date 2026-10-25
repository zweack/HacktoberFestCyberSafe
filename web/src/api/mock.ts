// Demo data used when VITE_MOCK=1 or when the API cannot be reached.
// Mock analyses always say ai_used=false and carry an ai_error, so they are never shown as AI results.
import type {
  AnalyzeRequest, AnalyzeResponse, Case, CaseCreate, CaseStep, ChaosSettings, Contact,
  FeedMessage, Notification, Signal, TimelineEvent,
} from "./types";

const MOCK_NOTE = "Demo data: the server is not connected, so this is a sample answer, not a real check.";

const now = () => new Date().toISOString();
const id = (p: string) => `${p}_${Math.random().toString(16).slice(2, 14)}`;

const CONTACTS: Contact[] = [
  {
    id: "ncrp_1930", name: "Cyber crime helpline 1930", name_hi: "साइबर क्राइम हेल्पलाइन 1930",
    description: "Call within 1 hour if money left your account. They can try to freeze it.",
    description_hi: "पैसा कटने के 1 घंटे के अंदर कॉल करें। वे पैसा रोकने की कोशिश कर सकते हैं।",
    phone: "1930", region: "IN", category: "helpline", source_url: "https://cybercrime.gov.in/",
  },
  {
    id: "ncrp_portal", name: "Report online: cybercrime.gov.in", name_hi: "ऑनलाइन शिकायत: cybercrime.gov.in",
    description: "File a complaint on the official government website.",
    description_hi: "सरकारी वेबसाइट पर शिकायत दर्ज करें।",
    url: "https://cybercrime.gov.in/", region: "IN", category: "reporting", source_url: "https://cybercrime.gov.in/",
  },
  {
    id: "chakshu", name: "Report a fraud call or SMS (Chakshu)", name_hi: "धोखाधड़ी कॉल या SMS की शिकायत (चक्षु)",
    description: "Tell the government about the number that contacted you.",
    description_hi: "जिस नंबर से संपर्क हुआ, उसकी जानकारी सरकार को दें।",
    url: "https://sancharsaathi.gov.in/sfc/", region: "IN", category: "telecom", source_url: "https://sancharsaathi.gov.in/",
  },
];

const RULES: { id: string; re: RegExp; en: string; hi: string; w: number }[] = [
  { id: "otp_request", re: /otp|pin|cvv|password/i, en: "Asks for an OTP, PIN or password", hi: "OTP, PIN या पासवर्ड माँगा गया", w: 0.9 },
  { id: "urgency", re: /urgent|immediately|today|within|blocked|suspend|turant|band/i, en: "Tries to rush you", hi: "जल्दी करने का दबाव", w: 0.6 },
  { id: "link", re: /https?:\/\/|bit\.ly|\.xyz|\.top/i, en: "Has a link to click", hi: "क्लिक करने के लिए लिंक है", w: 0.5 },
  { id: "kyc_update", re: /kyc|pan|aadhaar/i, en: "Talks about KYC, PAN or Aadhaar update", hi: "KYC, PAN या आधार अपडेट की बात", w: 0.7 },
  { id: "digital_arrest", re: /police|cbi|arrest|customs|court/i, en: "Claims to be police or a government officer", hi: "पुलिस या सरकारी अफ़सर होने का दावा", w: 0.8 },
  { id: "app_install", re: /anydesk|teamviewer|apk|install|download/i, en: "Asks you to install an app", hi: "ऐप इंस्टॉल करने को कहा", w: 0.8 },
  { id: "prize", re: /won|prize|lottery|cashback|refund/i, en: "Promises a prize or refund", hi: "इनाम या रिफ़ंड का लालच", w: 0.6 },
];

function step(sid: string, en: [string, string], hi: [string, string], lang: string, urgent = false, contact_id?: string) {
  const [title, detail] = lang === "hi" ? hi : en;
  return { id: sid, title, detail, urgent, contact_id: contact_id ?? null };
}

export function mockAnalyze(req: AnalyzeRequest): AnalyzeResponse {
  const lang = req.language ?? "en";
  const situation = req.situation ?? "received";
  const signals: Signal[] = RULES.filter((r) => r.re.test(req.text)).map((r) => ({
    id: r.id, label: lang === "hi" ? r.hi : r.en, weight: r.w, evidence: req.text.match(r.re)?.[0] ?? null,
  }));
  let score = Math.min(100, Math.round(signals.reduce((s, x) => s + x.weight * 40, 0)));
  if (situation !== "received") score = Math.max(score, 80);
  const verdict = score >= 70 ? "scam" : score >= 30 ? "suspicious" : "safe";
  const hi = lang === "hi";
  const headline = {
    scam: hi ? "यह धोखा है। कुछ भी न भेजें, लिंक न खोलें।" : "This is a scam. Do not reply or click anything.",
    suspicious: hi ? "यह संदिग्ध लगता है। पहले किसी से पूछ लें।" : "This looks suspicious. Check with someone first.",
    safe: hi ? "इसमें धोखे के आम संकेत नहीं मिले।" : "We did not find common scam signs.",
  }[verdict];
  const explanation = hi
    ? "बैंक और सरकार कभी फ़ोन या मैसेज पर OTP या PIN नहीं माँगते। जल्दी करने का दबाव धोखेबाज़ों की आम चाल है।"
    : "Banks and the government never ask for your OTP or PIN by phone or message. Rushing you is a common trick.";
  const steps =
    situation === "victim"
      ? [
          step("call_1930", ["Call 1930 now", "Tell them what happened. Have your bank details ready."], ["अभी 1930 पर कॉल करें", "जो हुआ बताएँ। बैंक की जानकारी पास रखें।"], lang, true, "ncrp_1930"),
          step("block_bank", ["Call your bank and block your card/UPI", "Use the number on the back of your card."], ["बैंक को कॉल करके कार्ड/UPI बंद कराएँ", "कार्ड के पीछे लिखा नंबर इस्तेमाल करें।"], lang, true),
          step("report_portal", ["File a complaint online", "Go to cybercrime.gov.in, or ask family to help."], ["ऑनलाइन शिकायत करें", "cybercrime.gov.in पर जाएँ, या परिवार से मदद लें।"], lang, false, "ncrp_portal"),
        ]
      : situation === "in_progress"
        ? [
            step("hang_up", ["Hang up now", "You do not have to be polite to them."], ["अभी फ़ोन काट दें", "उनसे विनम्र रहने की ज़रूरत नहीं।"], lang, true),
            step("no_otp", ["Do not share any OTP or PIN", "No real bank or police officer will ask."], ["कोई OTP या PIN न बताएँ", "असली बैंक या पुलिस कभी नहीं माँगती।"], lang, true),
            step("tell_family", ["Tell a family member", "Talk to someone you trust before doing anything."], ["परिवार को बताएँ", "कुछ भी करने से पहले किसी भरोसेमंद से बात करें।"], lang),
          ]
        : [
            step("dont_reply", ["Do not reply or click the link", "Delete the message."], ["जवाब न दें, लिंक न खोलें", "मैसेज मिटा दें।"], lang, verdict === "scam"),
            step("report", ["Report the number", "Use Chakshu on Sanchar Saathi."], ["नंबर की शिकायत करें", "संचार साथी पर चक्षु का उपयोग करें।"], lang, false, "chakshu"),
          ];
  return {
    verdict, risk_score: score, scam_type: signals[0]?.id ?? null, situation, headline, explanation, signals, steps,
    contacts: situation === "victim" ? CONTACTS : CONTACTS.filter((c) => c.id !== "ncrp_portal"),
    language: lang, ai_used: false, ai_error: MOCK_NOTE,
  };
}

// ------------------------------------------------------------- in-memory state

const cases = new Map<string, Case>();
const notifications: Notification[] = [];
let feed: FeedMessage[] = [];
let chaos: ChaosSettings = { telegram_failure_rate: 0, llm_down: false, slow_analyze_ms: 0 };

const SCRIPT: Omit<FeedMessage, "id" | "received_at" | "analysis">[] = [
  { channel: "sms", sender: "VM-SBIINB", text: "Dear customer your SBI account will be blocked today. Update KYC immediately: http://sbi-kyc.xyz/update" },
  { channel: "whatsapp", sender: "+91 98xxx 12345", text: "Hi Papa, this is my new number. Phone broke. Can you send ₹8,000 urgently on this UPI?" },
  { channel: "sms", sender: "AX-APOLLO", text: "Your appointment with Dr. Mehta is confirmed for Tuesday 10:30 AM." },
  { channel: "call", sender: "+91 70xxx 99881", text: "Caller says he is from CBI. Your Aadhaar is linked to a parcel with drugs. Stay on video call, you are under digital arrest." },
  { channel: "email", sender: "refunds@incometax-gov.top", subject: "Income tax refund ₹15,490", text: "You won a refund. Download the app (apk) and enter your card PIN to receive it." },
];
let scriptIdx = 0;
const listeners = new Set<(m: FeedMessage) => void>();

function event(c: Case, kind: string, message: string) {
  const e: TimelineEvent = { at: now(), kind, message };
  c.timeline.push(e);
  c.updated_at = e.at;
}

function notify(c: Case, recipient: string, message: string) {
  const fail = Math.random() < chaos.telegram_failure_rate;
  notifications.unshift({
    id: id("ntf"), created_at: now(), case_id: c.id, channel: c.telegram_chat_id ? "telegram" : "in_app",
    recipient, message, status: fail ? "failed" : "sent", attempts: fail ? 3 : 1,
    last_error: fail ? "Demo: simulated Telegram failure" : null,
  });
}

function getCase(cid: string): Case {
  const c = cases.get(cid);
  if (!c) throw new Error("Case not found");
  return c;
}

export function mockFeedSubscribe(fn: (m: FeedMessage) => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export async function mockRequest(method: string, path: string, body?: unknown): Promise<unknown> {
  await new Promise((r) => setTimeout(r, 250));
  const url = new URL(path, "http://mock");
  const p = url.pathname;
  let m: RegExpMatchArray | null;

  if (p === "/healthz") return { status: "ok" };
  if (p === "/readyz") return { status: "not_ready", checks: { database: "demo", temporal: "demo", llm: "demo" } };
  if (p === "/api/ops/chaos") {
    if (method === "PUT") chaos = { ...(body as ChaosSettings) };
    return chaos;
  }
  if (p === "/api/analyze") return mockAnalyze(body as AnalyzeRequest);
  if (p === "/api/directory") return CONTACTS;

  if (p === "/api/feed") return feed;
  if (p === "/api/feed/reset") { feed = []; scriptIdx = 0; return {}; }
  if (p === "/api/feed/next") {
    const s = SCRIPT[scriptIdx++ % SCRIPT.length];
    const msg: FeedMessage = { ...s, id: id("msg"), received_at: now(), analysis: mockAnalyze({ text: s.text, channel: s.channel }) };
    feed = [msg, ...feed];
    listeners.forEach((l) => l(msg));
    return msg;
  }

  if (p === "/api/cases" && method === "POST") {
    const b = body as CaseCreate;
    const a = b.analysis ?? mockAnalyze({ text: b.description, situation: "victim", language: b.language });
    const c: Case = {
      id: id("case"), created_at: now(), updated_at: now(), status: "checking_in",
      person_name: b.person_name, language: b.language ?? "en", situation: b.situation ?? "victim",
      description: b.description, amount_lost_inr: b.amount_lost_inr ?? null,
      telegram_chat_id: b.telegram_chat_id ?? null, trusted_contact_name: b.trusted_contact_name ?? null,
      trusted_contact_telegram_chat_id: b.trusted_contact_telegram_chat_id ?? null, analysis: a,
      steps: a.steps.map((s): CaseStep => ({ ...s, done: false, done_at: null })),
      workflow_id: null, checkins_sent: 1, unanswered_checkins: 0, coordinator: null, timeline: [],
    };
    cases.set(c.id, c);
    event(c, "created", "Case opened (demo)");
    notify(c, c.person_name, "Your action plan is ready.");
    event(c, "checkin_sent", "Check-in sent: Did you call 1930?");
    return c;
  }
  if (p === "/api/cases") return [...cases.values()];
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/steps\/([^/]+)\/done$/))) {
    const c = getCase(m[1]);
    const s = c.steps.find((x) => x.id === m![2]);
    if (s && !s.done) { s.done = true; s.done_at = now(); event(c, "step_done", `Done: ${s.title}`); }
    return c;
  }
  if ((m = p.match(/^\/api\/cases\/([^/]+)\/checkin$/))) {
    const c = getCase(m[1]);
    const ans = (body as { answer: string }).answer;
    event(c, "checkin_answered", `Answer: ${ans}`);
    if (ans === "need_help") {
      c.status = "escalated";
      event(c, "escalated", "Sent to a helper");
      notify(c, "coordinator", `${c.person_name} needs help.`);
    } else if (ans === "done" && c.steps.every((s) => s.done)) {
      c.status = "resolved";
      event(c, "resolved", "All steps done");
    }
    return c;
  }
  if ((m = p.match(/^\/api\/cases\/([^/]+)$/))) return getCase(m[1]);
  if (p === "/api/notifications") {
    const cid = url.searchParams.get("case_id");
    return notifications.filter((n) => !cid || n.case_id === cid);
  }
  if (p === "/api/coordinator/queue") return [...cases.values()].filter((c) => c.status === "escalated" || c.status === "claimed");
  if ((m = p.match(/^\/api\/coordinator\/cases\/([^/]+)\/(claim|resolve)$/))) {
    const c = getCase(m[1]);
    const who = (body as { coordinator: string }).coordinator;
    c.coordinator = who;
    c.status = m[2] === "claim" ? "claimed" : "resolved";
    event(c, c.status, `${m[2] === "claim" ? "Claimed" : "Resolved"} by ${who}`);
    return c;
  }
  throw new Error(`Demo mode has no data for ${method} ${p}`);
}
