"""Plain-language texts for victims, in English and Hindi. Pure functions (workflow-safe)."""

def action_plan(name: str, language: str, step_titles: list[str]) -> str:
    lines = "\n".join(f"{n}. {t}" for n, t in enumerate(step_titles, 1))
    if language == "hi":
        return f"{name} जी, घबराएं नहीं। हम आपके साथ हैं। ये काम करें:\n{lines}"
    return f"{name}, do not worry. We are with you. Please do these steps:\n{lines}"


def confirm_done(name: str, language: str) -> str:
    if language == "hi":
        return f"{name} जी, आपने सारे कदम पूरे कर दिए। क्या सब ठीक है? 'हो गया' दबाकर बताएं।"
    return f"{name}, you ticked every step. Is everything done? Press Done to confirm."


def checkin(name: str, language: str) -> str:
    if language == "hi":
        return f"{name} जी, क्या आपने 1930 और अपने बैंक को कॉल किया?"
    return f"{name}, did you call 1930 and your bank?"


def closing(name: str, language: str) -> str:
    if language == "hi":
        return (f"{name} जी, आपकी सूची पूरी हुई। बैंक और 1930 की सलाह मानते रहें। "
                "कोई OTP या PIN किसी को न बताएं।")
    return (f"Well done, {name}. Your checklist is complete. Keep following your bank's and 1930's advice. "
            "Never share an OTP or PIN with anyone.")


def escalated_to_person(name: str, language: str) -> str:
    if language == "hi":
        return (f"{name} जी, आपका अनुरोध सहायकों की सूची में है। कोई सहायक इसे लेगा तो यहाँ दिखेगा। "
                "तब तक ऊपर दिए कदम करें और 1930 पर कॉल करें।")
    return (f"{name}, your request is in the helpers' queue. When a helper takes it, you will see it here. "
            "Until then, do the steps above and call 1930.")


def coordinator_alert(case_id: str, name: str, reason: str) -> str:
    return f"Case {case_id} ({name}) needs a person: {reason}. Open the coordinator queue to claim it."


def trusted_contact_alert(contact: str, name: str) -> str:
    return f"Hello {contact}, {name} may have been scammed and needs your help. Please call them now."
