"""Plain-language texts for victims, in English and Hindi. Pure functions (workflow-safe)."""

from app.schemas import CaseStep, Language

# (id, urgent, en title, en detail, hi title, hi detail, contact_id)
_DEFAULT_STEPS = [
    ("call_1930", True, "Call 1930 now",
     "Call the National Cyber Crime Helpline 1930. Tell them you lost money. Fast calls can stop the money.",
     "अभी 1930 पर कॉल करें",
     "राष्ट्रीय साइबर अपराध हेल्पलाइन 1930 पर कॉल करें। बताएं कि आपके पैसे गए हैं। जल्दी कॉल करने से पैसा रुक सकता है।",
     "helpline_1930"),
    ("report_portal", True, "Report on cybercrime.gov.in",
     "Go to cybercrime.gov.in and file a complaint. Write down the complaint number.",
     "cybercrime.gov.in पर शिकायत करें",
     "cybercrime.gov.in पर जाकर शिकायत दर्ज करें। शिकायत नंबर लिखकर रखें।",
     "cybercrime_portal"),
    ("call_bank", True, "Call your bank to block card and UPI",
     "Call the number on the back of your card. Ask them to block your card and UPI.",
     "बैंक को कॉल करके कार्ड और UPI बंद करवाएं",
     "अपने कार्ड के पीछे लिखे नंबर पर कॉल करें। कार्ड और UPI बंद करने को कहें।",
     None),
    ("change_pins", False, "Change your UPI PIN and passwords",
     "Change your UPI PIN, net banking password and email password.",
     "UPI PIN और पासवर्ड बदलें",
     "अपना UPI PIN, नेट बैंकिंग पासवर्ड और ईमेल पासवर्ड बदलें।",
     None),
    ("remove_apps", False, "Uninstall screen-sharing apps",
     "If someone asked you to install an app like AnyDesk or TeamViewer, uninstall it now.",
     "स्क्रीन शेयर करने वाले ऐप हटाएं",
     "अगर किसी ने AnyDesk या TeamViewer जैसा ऐप डलवाया है, तो उसे अभी हटा दें।",
     None),
    ("keep_evidence", False, "Keep the evidence",
     "Do not delete messages. Take screenshots of chats, payment receipts and phone numbers.",
     "सबूत संभालकर रखें",
     "मैसेज न मिटाएं। चैट, पेमेंट की रसीद और फोन नंबर का स्क्रीनशॉट लें।",
     None),
]


def default_steps(language: Language) -> list[CaseStep]:
    hi = language == Language.hi
    return [
        CaseStep(id=i, urgent=u, title=ht if hi else t, detail=hd if hi else d, contact_id=c)
        for i, u, t, d, ht, hd, c in _DEFAULT_STEPS
    ]


def action_plan(name: str, language: str, step_titles: list[str]) -> str:
    lines = "\n".join(f"{n}. {t}" for n, t in enumerate(step_titles, 1))
    if language == "hi":
        return f"{name} जी, घबराएं नहीं। हम आपके साथ हैं। ये काम करें:\n{lines}"
    return f"{name}, do not worry. We are with you. Please do these steps:\n{lines}"


def checkin(name: str, language: str) -> str:
    if language == "hi":
        return f"{name} जी, क्या आपने 1930 और अपने बैंक को कॉल किया?"
    return f"{name}, did you call 1930 and your bank?"


def closing(name: str, language: str) -> str:
    if language == "hi":
        return f"{name} जी, बहुत अच्छा। आप सुरक्षित हैं। कोई OTP या PIN किसी को न बताएं।"
    return f"Well done, {name}. You are safe now. Never share an OTP or PIN with anyone."


def escalated_to_person(name: str, language: str) -> str:
    if language == "hi":
        return f"{name} जी, एक सहायक जल्द ही आपसे संपर्क करेगा।"
    return f"{name}, a helper will contact you soon."


def coordinator_alert(case_id: str, name: str, reason: str) -> str:
    return f"Case {case_id} ({name}) needs a person: {reason}. Open the coordinator queue to claim it."


def trusted_contact_alert(contact: str, name: str) -> str:
    return f"Hello {contact}, {name} may have been scammed and needs your help. Please call them now."
