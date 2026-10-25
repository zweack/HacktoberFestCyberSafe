"""Deterministic scam rule engine. Always runs, never touches the network.

Covers common Indian scam patterns in English, Hindi (Devanagari) and Hinglish.
"""

import re
from dataclasses import dataclass

from app.schemas import Language, Signal, Verdict

SCAM_THRESHOLD = 65
SUSPICIOUS_THRESHOLD = 30


@dataclass(frozen=True)
class Rule:
    id: str
    weight: float
    label_en: str
    label_hi: str
    patterns: tuple[str, ...]
    scam_type: str | None = None  # None = generic signal

    def compiled(self) -> tuple[re.Pattern, ...]:
        return _COMPILED[self.id]


def _r(id, weight, en, hi, *patterns, scam_type=None) -> Rule:
    return Rule(id, weight, en, hi, tuple(patterns), scam_type)


# Scam-type rules: a single strong hit should usually be enough to be "suspicious";
# combined with generic signals it crosses into "scam".
SCAM_RULES: tuple[Rule, ...] = (
    _r("kyc_update", 0.6, "Asks you to update KYC / PAN or says your account will be blocked",
       "KYC / PAN अपडेट करने या खाता बंद होने की बात करता है",
       r"\bkyc\b.{0,40}(updat|expir|pending|suspend|block|verify|complete)",
       r"(updat|complete|verify).{0,20}\bkyc\b",
       r"\bpan\b.{0,30}(updat|link|block|suspend)",
       r"(account|a/c|khata|yono|net ?banking).{0,40}(block|suspend|deactivat|band|freeze)",
       r"(खाता|अकाउंट).{0,30}(ब्लॉक|बंद|निलंबित)", r"केवाईसी|KYC.{0,20}(अपडेट|पूरा)",
       scam_type="kyc_update"),
    _r("otp_request", 0.7, "Asks for your OTP, PIN, CVV or password", "आपका OTP, PIN, CVV या पासवर्ड माँगता है",
       r"(share|send|tell|give|provide|forward|read out|confirm|enter).{0,30}\b(otp|cvv|atm pin|upi pin|m-?pin|password|code)\b",
       r"\b(otp|cvv|pin)\b.{0,25}(batao|bata do|bhejo|bhej do|share karo|de do|bolo)",
       r"(ओटीपी|OTP|पिन|PIN|सीवीवी).{0,20}(बताएं|बताओ|बता दो|भेजें|भेजो|शेयर करें|दे दो)",
       scam_type="otp_request"),
    _r("upi_collect", 0.7, "Says you must enter your UPI PIN to receive money (PIN is only for paying)",
       "पैसे पाने के लिए UPI PIN डालने को कहता है (PIN सिर्फ़ पैसे भेजने के लिए होता है)",
       r"(enter|put|dalo|daalo|daliye).{0,30}(upi )?pin.{0,40}(receive|get|credit|refund|milega|aayega|paane)",
       r"(receive|get|claim|accept).{0,30}(money|amount|refund|cashback|payment).{0,40}(enter|approve).{0,15}pin",
       r"(collect request|payment request).{0,40}(accept|approve)",
       r"पैसे (पाने|लेने) के लिए.{0,20}पिन",
       scam_type="upi_collect"),
    _r("lottery_prize", 0.6, "Promises a lottery, KBC or prize you never entered", "ऐसी लॉटरी, KBC या इनाम का वादा जिसमें आपने भाग नहीं लिया",
       r"\b(lottery|lucky draw|jackpot|kbc|kaun banega crorepati)\b",
       r"(you have|you've|aapne) (won|jeet)", r"(won|winner|jeeta|jeete).{0,30}(rs\.?|₹|inr|lakh|crore|lac|prize|car)",
       r"लॉटरी|केबीसी|कौन बनेगा करोड़पति|इनाम जीत|जीते हैं",
       scam_type="lottery_prize"),
    _r("digital_arrest", 0.8, "Claims police / CBI / customs / TRAI will arrest you (police never arrest on video call)",
       "पुलिस / CBI / कस्टम / TRAI गिरफ़्तारी की धमकी (पुलिस कभी वीडियो कॉल पर गिरफ़्तार नहीं करती)",
       r"digital(ly)? arrest", r"\b(cbi|ed|ncb|customs|trai|cyber cell|narcotics|crime branch|mumbai police|delhi police)\b.{0,60}(case|arrest|warrant|fir|investigation|video call|verify|disconnect)",
       r"(case|fir|warrant).{0,40}(registered|filed|issued|darj).{0,40}(aadhaar|aadhar|your name|mobile number|aapke)",
       r"(arrest|warrant|giraftar).{0,40}(aadhaar|aadhar|video call|skype)",
       r"डिजिटल अरेस्ट|गिरफ़्तार|गिरफ्तार|वारंट|सीबीआई|आधार.{0,30}(केस|मामला)",
       scam_type="digital_arrest"),
    _r("courier_parcel", 0.65, "Says a parcel in your name has drugs or is held by customs", "आपके नाम के पार्सल में ड्रग्स या कस्टम में रुका होने की बात",
       r"(parcel|package|courier|fedex|dhl|shipment).{0,60}(drug|mdma|narcotic|illegal|seized|customs|held|suspicious|passport)",
       r"(fedex|dhl).{0,40}(press|dial|call)",
       r"पार्सल.{0,40}(ड्रग्स|कस्टम|ज़ब्त|जब्त|अवैध)",
       scam_type="courier_parcel"),
    _r("electricity_disconnect", 0.65, "Threatens to cut your electricity tonight", "आज रात बिजली काटने की धमकी",
       r"(electricity|power|bijli|light).{0,50}(disconnect|cut|kaat|kat jayegi|band)",
       r"(bill|connection).{0,40}(not updated|unpaid|pending).{0,60}(tonight|today|9[: ]?30|10[: ]?30)",
       r"बिजली.{0,40}(काट|कट|बंद|डिस्कनेक्ट)",
       scam_type="electricity_disconnect"),
    _r("task_job", 0.65, "Offers easy part-time money for likes, reviews or tasks", "लाइक, रिव्यू या टास्क के बदले आसान पार्ट-टाइम कमाई का लालच",
       r"part[- ]?time.{0,40}(job|work|income|earn)", r"(like|subscribe|rate|review).{0,40}(youtube|video|hotel|google map|product).{0,60}(earn|pay|₹|rs|income)",
       r"(earn|kamao|kamaye).{0,20}(₹|rs\.?|inr)?\s?\d[\d,]{2,}.{0,30}(daily|per day|roz|from home|ghar baithe)",
       r"work from home.{0,40}(earn|₹|rs)", r"prepaid task|task (based|reward)",
       r"पार्ट टाइम|घर बैठे.{0,20}(कमाएं|कमाई)|रोज़ाना.{0,20}कमाएं",
       scam_type="task_job"),
    _r("investment", 0.6, "Promises big guaranteed returns on stocks or crypto", "शेयर या क्रिप्टो में पक्के बड़े मुनाफ़े का वादा",
       r"(guaranteed|assured|fixed|daily|double).{0,20}(return|profit|income|munafa)",
       r"(stock|share|ipo|crypto|bitcoin|usdt|trading).{0,60}(vip|group|tips|guaranteed|profit|\d+\s?%)",
       r"(double|2x|3x|10x).{0,20}(money|amount|paisa)",
       r"(पक्का|गारंटी|दोगुना).{0,20}(मुनाफ़ा|मुनाफा|रिटर्न|पैसा)|शेयर.{0,30}(ग्रुप|टिप्स)",
       scam_type="investment"),
    _r("loan_app", 0.5, "Instant loan with no documents or checks", "बिना कागज़ या जाँच के तुरंत लोन",
       r"(instant|quick|pre[- ]?approved|turant).{0,20}loan", r"loan.{0,40}(no documents|no cibil|without (documents|cibil)|in \d+ minutes)",
       r"(तुरंत|बिना).{0,20}लोन",
       scam_type="loan_app"),
    _r("fake_customer_care", 0.55, "Pretends to be customer care or offers a refund", "ग्राहक सेवा बनकर या रिफ़ंड का झांसा देकर संपर्क",
       r"(refund|cashback).{0,60}(process|initiat|claim|click|download|install|call)",
       r"(customer care|helpdesk|support team).{0,40}(call|contact|whatsapp).{0,20}\d{8,}",
       r"रिफ़ंड|रिफंड.{0,30}(पाने|लेने)",
       scam_type="fake_customer_care"),
    _r("income_tax_refund", 0.6, "Claims an income-tax refund is waiting for you", "इनकम टैक्स रिफ़ंड मिलने का दावा",
       r"(income[- ]?tax|it dept|itr).{0,40}refund", r"tax refund.{0,40}(approved|pending|click|claim|verify)",
       r"आयकर.{0,20}(रिफ़ंड|रिफंड|वापसी)",
       scam_type="income_tax_refund"),
    _r("reward_points", 0.55, "Says your credit card reward points are expiring", "क्रेडिट कार्ड रिवॉर्ड पॉइंट खत्म होने की बात",
       r"(reward|redeem).{0,20}points?.{0,60}(expir|redeem|claim|today|worth)",
       r"रिवॉर्ड पॉइंट",
       scam_type="reward_points"),
    _r("family_emergency", 0.6, "Someone claims to be family in trouble from a new number", "नए नंबर से परिवार का कोई सदस्य मुसीबत में होने का दावा",
       r"(this is my new number|my new number|new number h|naya number)",
       r"(mom|mum|maa|papa|dad|mummy|beta|son|daughter).{0,60}(trouble|urgent|accident|hospital|stuck|phone (broke|lost)|send money|paise bhej)",
       r"(मम्मी|पापा|माँ|बेटा).{0,40}(मुसीबत|अस्पताल|पैसे भेज)|मेरा नया नंबर",
       scam_type="family_emergency"),
    _r("wrong_transfer", 0.6, "Says money was sent to you by mistake and asks you to return it", "गलती से पैसे भेजने और वापस माँगने की बात",
       r"(sent|transferred|bheje|bhej diye).{0,40}(by mistake|galti se|wrongly)",
       r"(by mistake|galti se).{0,40}(sent|transfer|bhej).{0,60}(return|wapas|refund)",
       r"गलती से.{0,30}(पैसे|भेज)",
       scam_type="wrong_transfer"),
    _r("remote_access", 0.8, "Asks you to install AnyDesk, TeamViewer or another app that controls your phone",
       "AnyDesk, TeamViewer जैसा ऐप डालने को कहता है जिससे आपका फ़ोन कोई और चला सके",
       r"\b(anydesk|any desk|teamviewer|team viewer|quicksupport|quick support|rustdesk|airdroid|screen ?share|screen sharing)\b",
       r"(install|download|daalo|dalo).{0,40}\.?apk\b", r"\.apk\b",
       r"एनीडेस्क|स्क्रीन शेयर",
       scam_type="remote_access"),
    _r("sextortion", 0.75, "Threatens to leak private videos or photos", "निजी वीडियो या फ़ोटो फैलाने की धमकी",
       r"(video|photo|pic|recording).{0,40}(viral|leak|share|upload|send).{0,40}(family|contacts|friends|youtube|social)",
       r"(nude|obscene|private|intimate|naked|ashleel).{0,30}(video|photo|call)",
       r"(वीडियो|फ़ोटो|फोटो).{0,30}(वायरल|लीक)|अश्लील",
       scam_type="sextortion"),
)

GENERIC_RULES: tuple[Rule, ...] = (
    _r("urgency", 0.3, "Rushes you with a deadline", "जल्दबाज़ी कराता है, समय-सीमा देता है",
       r"\b(urgent|urgently|immediately|asap|right now|within \d+ ?(hours?|hrs|minutes?|mins)|today itself|tonight|last chance|final notice|expires? today|jaldi|turant|abhi)\b",
       r"तुरंत|अभी|आज ही|जल्दी|आज रात|अंतिम"),
    _r("threat", 0.3, "Threatens you with penalty, blocking or legal action", "जुर्माना, ब्लॉक या कानूनी कार्रवाई की धमकी",
       r"\b(legal action|penalty|fine of|will be (blocked|suspended|disconnected|arrested)|police case|jail)\b",
       r"कानूनी कार्रवाई|जुर्माना|जेल"),
    _r("secrecy", 0.35, "Tells you to keep it secret from family", "परिवार से छिपाने को कहता है",
       r"(don'?t|do not|never) tell (anyone|your family|family|anybody|your (son|daughter|wife|husband))",
       r"keep (this|it) (secret|confidential)", r"(kisi|mummy|papa|maa|ghar mein|family) ko (mat|na) batana",
       r"(परिवार|घर में|किसी) को (मत|न) बताना"),
    _r("payment_request", 0.3, "Asks you to pay or transfer money", "पैसे भेजने या भुगतान करने को कहता है",
       r"\b(pay|transfer|send)\b.{0,20}(₹|rs\.?|inr|amount|money|fee|charges|deposit)",
       r"(processing|registration|security|verification) (fee|charge)", r"paise? (bhejo|bhej do|transfer karo)",
       r"(पैसे|रकम|शुल्क).{0,20}(भेजें|भेजो|जमा करें|ट्रांसफर)"),
    _r("call_unknown_number", 0.2, "Asks you to call or WhatsApp an unknown number", "किसी अनजान नंबर पर कॉल या WhatsApp करने को कहता है",
       r"(call|contact|whatsapp|dial|sampark).{0,25}(\+91[\s-]?)?[6-9]\d{9}\b",
       r"(कॉल|संपर्क).{0,20}[6-9]\d{9}"),
)

_NEGATED = re.compile(r"(do not|don'?t|never|mat|nahi|kabhi bhi|\bन\s|\bना\s|मत\s)", re.I)

_COMPILED = {r.id: tuple(re.compile(p, re.I | re.S) for p in r.patterns) for r in SCAM_RULES + GENERIC_RULES}

# ---------------------------------------------------------------- links

_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"')]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|in|net|org|xyz|top|info|co|link|ly|me|io|site|online|app|apk)(?:/[^\s<>\"')]*)?", re.I)
_SHORTENERS = {"bit.ly", "tinyurl.com", "t.ly", "cutt.ly", "rb.gy", "is.gd", "goo.gl", "shorturl.at", "tiny.cc", "ow.ly", "rebrand.ly", "t.co", "s.id", "wa.me"}
_BANK_WORDS = ("sbi", "hdfc", "icici", "axis", "kotak", "pnb", "baroda", "bob", "yono", "paytm", "phonepe", "npci", "rbi", "uidai", "aadhaar", "incometax", "epfo")
_OFFICIAL_DOMAINS = (
    "sbi.co.in", "onlinesbi.sbi", "sbi.bank.in", "sbicard.com", "hdfcbank.com", "hdfc.bank.in", "icicibank.com", "icici.bank.in",
    "axisbank.com", "axis.bank.in", "kotak.com", "kotak.bank.in", "pnbindia.in", "pnb.bank.in", "bankofbaroda.in",
    "bankofbaroda.bank.in", "paytm.com", "phonepe.com", "npci.org.in", "rbi.org.in", "amazon.in", "amzn.in", "flipkart.com",
)
_GOV_WORDS = ("gov", "govt", "police", "cbi", "trai", "customs", "incometax", "uidai", "epfo", "court")
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _host(url: str) -> str:
    u = re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split(":")[0].lower()
    return u.removeprefix("www.")


def _is_official(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in _OFFICIAL_DOMAINS) or host.endswith(".gov.in") or host.endswith(".nic.in")


def link_signals(text: str) -> list[tuple[str, float, str, str, str]]:
    """(id, weight, label_en, label_hi, evidence) for each link problem found."""
    out: list[tuple[str, float, str, str, str]] = []
    seen: set[str] = set()

    def add(id, w, en, hi, ev):
        if id not in seen:
            seen.add(id)
            out.append((id, w, en, hi, ev))

    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(".,;")
        host = _host(url)
        if not host or "." not in host:
            continue
        if url.lower().endswith(".apk") or ".apk?" in url.lower():
            add("apk_link", 0.7, "Link downloads an app file (.apk) – this can take over your phone",
                "लिंक एक ऐप फ़ाइल (.apk) डाउनलोड करता है – इससे आपका फ़ोन हैक हो सकता है", url)
        if host in _SHORTENERS:
            add("short_link", 0.35, "Uses a shortened link that hides where it goes", "छोटा किया गया लिंक जो असली पता छिपाता है", url)
        elif _IP_RE.match(host):
            add("ip_link", 0.5, "Link is a bare number address, not a real website", "लिंक किसी असली वेबसाइट का नहीं, सिर्फ़ नंबर वाला पता है", url)
        elif not _is_official(host):
            name = host.replace("-", "").replace(".", "")
            if any(b in name for b in _BANK_WORDS):
                add("lookalike_domain", 0.55, "Link pretends to be a bank or government site but is not the official one",
                    "लिंक बैंक या सरकारी साइट जैसा दिखता है पर असली नहीं है", url)
            elif any(g in name for g in _GOV_WORDS):
                add("fake_gov_link", 0.5, "Claims to be government but the site does not end in .gov.in",
                    "सरकारी होने का दावा, पर वेबसाइट .gov.in पर नहीं है", url)
            else:
                add("unknown_link", 0.15, "Contains a link to an unknown website", "किसी अनजान वेबसाइट का लिंक है", url)
    return out


# ---------------------------------------------------------------- scoring


@dataclass
class RuleResult:
    signals: list[Signal]
    risk_score: int
    verdict: Verdict
    scam_type: str | None


def verdict_for(score: int) -> Verdict:
    if score >= SCAM_THRESHOLD:
        return Verdict.scam
    if score >= SUSPICIOUS_THRESHOLD:
        return Verdict.suspicious
    return Verdict.safe


def _snippet(text: str, m: re.Match) -> str:
    s, e = max(0, m.start() - 15), min(len(text), m.end() + 15)
    return text[s:e].strip()[:120]


def run_rules(text: str, language: Language = Language.en) -> RuleResult:
    hi = language == Language.hi
    signals: list[Signal] = []
    best: tuple[float, str] | None = None
    for rule in SCAM_RULES + GENERIC_RULES:
        for pat in rule.compiled():
            m = pat.search(text)
            if m and rule.id == "otp_request" and _NEGATED.search(text[max(0, m.start() - 25):m.end()]):
                m = None  # "do not share your OTP" is advice, not a request
            if m:
                signals.append(Signal(id=rule.id, label=rule.label_hi if hi else rule.label_en,
                                      weight=rule.weight, evidence=_snippet(text, m)))
                if rule.scam_type and (best is None or rule.weight > best[0]):
                    best = (rule.weight, rule.scam_type)
                break
    for id, w, en, h, ev in link_signals(text):
        signals.append(Signal(id=id, label=h if hi else en, weight=w, evidence=ev))
        if id == "apk_link" and (best is None or w > best[0]):
            best = (w, "remote_access")

    # Noisy-OR: independent signals each reduce the chance this is innocent.
    p_safe = 1.0
    for s in signals:
        p_safe *= 1 - s.weight
    score = round((1 - p_safe) * 100)
    # A known scam pattern plus any pressure/link signal is a scam.
    if best and len(signals) >= 2:
        score = max(score, SCAM_THRESHOLD)
    score = max(0, min(100, score))
    signals.sort(key=lambda s: s.weight, reverse=True)
    return RuleResult(signals=signals, risk_score=score, verdict=verdict_for(score),
                      scam_type=best[1] if best and score >= SUSPICIOUS_THRESHOLD else None)
