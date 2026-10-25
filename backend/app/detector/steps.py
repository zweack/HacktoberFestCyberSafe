"""Situation-aware next steps and rule-based plain-language text (English + Hindi)."""

from app.directory.directory import contacts_for
from app.schemas import ActionStep, Contact, Language, Situation, Verdict

# (id, urgent, contact_id, title_en, detail_en, title_hi, detail_hi)
_STEPS: dict[Situation, list[tuple]] = {
    Situation.received: [
        ("dont_click", True, None, "Do not click any link", "Do not open links or download anything from this message.",
         "किसी लिंक पर क्लिक न करें", "इस संदेश के किसी लिंक को न खोलें, कुछ भी डाउनलोड न करें।"),
        ("dont_reply", True, None, "Do not reply or call back", "Do not reply. Do not call the number in the message.",
         "जवाब न दें, वापस कॉल न करें", "जवाब न दें। संदेश में दिए नंबर पर कॉल न करें।"),
        ("report_chakshu", False, "chakshu", "Report it on Chakshu", "Report the number on Sanchar Saathi (Chakshu). Then block the sender.",
         "चक्षु पर रिपोर्ट करें", "संचार साथी (चक्षु) पर नंबर की रिपोर्ट करें। फिर भेजने वाले को ब्लॉक करें।"),
        ("delete", False, None, "Delete the message", "After reporting, delete the message.",
         "संदेश मिटा दें", "रिपोर्ट करने के बाद संदेश मिटा दें।"),
        ("verify_official", False, None, "Check with the official number", "If unsure, call the number printed on your card or passbook.",
         "असली नंबर से जाँचें", "शक हो तो अपने कार्ड या पासबुक पर छपे नंबर पर कॉल करें।"),
    ],
    Situation.in_progress: [
        ("hang_up", True, None, "HANG UP NOW", "End the call or chat right now. It is okay to be rude.",
         "अभी फ़ोन काट दें", "कॉल या चैट अभी बंद करें। मना करना ठीक है।"),
        ("no_otp", True, None, "Never share OTP or PIN", "No bank, police or company will ever ask for your OTP, PIN or CVV.",
         "OTP या PIN कभी न बताएं", "कोई बैंक, पुलिस या कंपनी कभी आपका OTP, PIN या CVV नहीं माँगती।"),
        ("no_apps", True, None, "Do not install any app", "Do not install AnyDesk, TeamViewer or any app they send.",
         "कोई ऐप इंस्टॉल न करें", "AnyDesk, TeamViewer या उनका भेजा कोई भी ऐप न डालें।"),
        ("no_video_arrest", False, None, "Police never arrest on video call", "There is no 'digital arrest'. Real police do not ask for money on a call.",
         "पुलिस वीडियो कॉल पर गिरफ़्तार नहीं करती", "'डिजिटल अरेस्ट' जैसा कुछ नहीं होता। असली पुलिस फ़ोन पर पैसे नहीं माँगती।"),
        ("call_official", False, None, "Call back on the official number", "Call your bank on the number printed on your card or passbook.",
         "असली नंबर पर खुद कॉल करें", "अपने कार्ड या पासबुक पर छपे नंबर पर बैंक को खुद कॉल करें।"),
        ("tell_family", False, None, "Tell a family member", "Tell someone you trust what happened.",
         "परिवार को बताएं", "किसी भरोसेमंद व्यक्ति को बताएं कि क्या हुआ।"),
    ],
    Situation.victim: [
        ("call_1930", True, "ncrp_1930", "Call 1930 now", "Call 1930 right away. The first hour matters most to stop the money.",
         "अभी 1930 पर कॉल करें", "तुरंत 1930 पर कॉल करें। पैसा रोकने के लिए पहला घंटा सबसे ज़रूरी है।"),
        ("block_bank", True, None, "Call your bank to block card and UPI", "Ask your bank to block your card, UPI and net banking.",
         "बैंक को कॉल करके कार्ड और UPI ब्लॉक कराएं", "बैंक से अपना कार्ड, UPI और नेट बैंकिंग ब्लॉक कराएं।"),
        ("report_portal", True, "ncrp_portal", "Report on cybercrime.gov.in", "File a complaint on cybercrime.gov.in. Keep the complaint number.",
         "cybercrime.gov.in पर शिकायत करें", "cybercrime.gov.in पर शिकायत दर्ज करें। शिकायत नंबर संभाल कर रखें।"),
        ("uninstall_apps", True, None, "Remove remote-access apps", "Uninstall AnyDesk, TeamViewer or any app they asked you to install.",
         "रिमोट ऐप हटाएं", "AnyDesk, TeamViewer या उनके कहने पर डाला गया कोई भी ऐप हटा दें।"),
        ("change_pins", False, None, "Change UPI PIN and passwords", "Change your UPI PIN, ATM PIN and banking passwords.",
         "UPI PIN और पासवर्ड बदलें", "अपना UPI PIN, ATM PIN और बैंकिंग पासवर्ड बदलें।"),
        ("keep_evidence", False, None, "Keep proof", "Save screenshots, phone numbers and transaction IDs. Do not delete the chat.",
         "सबूत संभालें", "स्क्रीनशॉट, फ़ोन नंबर और ट्रांज़ैक्शन ID संभालें। चैट न मिटाएं।"),
        ("tell_family", False, None, "Tell a family member", "You are not alone. Tell someone you trust today.",
         "परिवार को बताएं", "आप अकेले नहीं हैं। आज ही किसी भरोसेमंद व्यक्ति को बताएं।"),
    ],
}

_BANK_IDS = ["bank_sbi", "bank_hdfc", "bank_icici", "bank_axis", "bank_pnb", "bank_kotak", "bank_bob"]
_BANK_HINTS = {"sbi": "bank_sbi", "yono": "bank_sbi", "hdfc": "bank_hdfc", "icici": "bank_icici", "axis": "bank_axis",
               "pnb": "bank_pnb", "punjab national": "bank_pnb", "kotak": "bank_kotak", "baroda": "bank_bob", "bob": "bank_bob"}


def steps_for(situation: Situation, verdict: Verdict, lang: Language) -> list[ActionStep]:
    hi = lang == Language.hi
    rows = _STEPS[situation]
    if situation == Situation.received and verdict == Verdict.safe:
        rows = [r for r in rows if r[0] == "verify_official"]
    return [ActionStep(id=r[0], urgent=r[1], contact_id=r[2], title=r[5] if hi else r[3], detail=r[6] if hi else r[4])
            for r in rows]


def relevant_contact_ids(situation: Situation, verdict: Verdict, scam_type: str | None, text: str) -> list[str]:
    low = text.lower()
    banks = list(dict.fromkeys(v for k, v in _BANK_HINTS.items() if k in low))
    if situation == Situation.victim:
        ids = ["ncrp_1930", "ncrp_portal", *(banks or _BANK_IDS), "rbi_cms", "elderline"]
        if scam_type in {"upi_collect", "wrong_transfer"}:
            ids.insert(2, "npci_upi")
        if scam_type in {"digital_arrest", "sextortion"}:
            ids.insert(2, "emergency_112")
        return ids
    if situation == Situation.in_progress:
        ids = ["ncrp_1930", "emergency_112", *banks, "chakshu", "elderline"]
        return ids
    if verdict == Verdict.safe:
        return []
    ids = ["chakshu", "ncrp_portal", "ncrp_1930"]
    if scam_type in {"investment", "loan_app"}:
        ids.append("rbi_sachet")
    return ids + banks


def contacts(situation: Situation, verdict: Verdict, scam_type: str | None, text: str, lang: Language) -> list[Contact]:
    return contacts_for(relevant_contact_ids(situation, verdict, scam_type, text), lang)


_HEADLINES = {
    (Situation.received, Verdict.scam): ("This is a scam. Do not click, reply or pay.", "यह धोखा है। क्लिक, जवाब या भुगतान न करें।"),
    (Situation.received, Verdict.suspicious): ("This looks suspicious. Do not act on it yet.", "यह संदेश संदिग्ध है। अभी कुछ न करें।"),
    (Situation.received, Verdict.safe): ("No scam signs found. Still, never share your OTP or PIN.", "धोखे के संकेत नहीं मिले। फिर भी OTP या PIN कभी न बताएं।"),
    (Situation.in_progress, None): ("Stop now. Hang up and do not share anything.", "अभी रुकें। फ़ोन काटें और कुछ भी न बताएं।"),
    (Situation.victim, None): ("Act now: call 1930 and your bank immediately.", "तुरंत 1930 और अपने बैंक को कॉल करें।"),
}


def rule_headline(situation: Situation, verdict: Verdict, lang: Language) -> str:
    key = (situation, verdict) if situation == Situation.received else (situation, None)
    en, hi = _HEADLINES[key]
    return hi if lang == Language.hi else en


def rule_explanation(signal_labels: list[str], verdict: Verdict, situation: Situation, lang: Language) -> str:
    hi = lang == Language.hi
    if not signal_labels:
        base = "हमें इसमें धोखे के आम संकेत नहीं मिले।" if hi else "We did not find common scam signs in this."
    else:
        joined = "; ".join(signal_labels[:3])
        base = f"हमें ये चेतावनी संकेत मिले: {joined}।" if hi else f"We found these warning signs: {joined}."
    tail = {
        Situation.received: ("असली बैंक या सरकार कभी OTP, PIN या पैसे नहीं माँगते।" if hi
                             else "Real banks and government never ask for OTP, PIN or money by message."),
        Situation.in_progress: ("जो भी व्यक्ति दबाव डाल रहा है, उससे बात बंद करें।" if hi
                                else "Whoever is pressuring you, stop talking to them now."),
        Situation.victim: ("घबराएं नहीं। जल्दी कदम उठाने से पैसा वापस मिलने की संभावना बढ़ती है।" if hi
                           else "Do not panic. Acting fast gives the best chance to get money back."),
    }[situation]
    return f"{base} {tail}"
