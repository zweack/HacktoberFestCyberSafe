"""Optional LLM refinement through any OpenAI-compatible endpoint.

The rule engine is the safety floor: the model may raise risk, never lower a scam to safe.
Every failure is reported back as a short reason; we never invent an AI answer.
"""

import json
import re
from dataclasses import dataclass

import httpx

from app.chaos import get_chaos
from app.config import get_settings
from app.schemas import Contact, Language, Signal, Situation, Verdict


class LLMError(Exception):
    """Short, human-readable reason the model could not help."""


@dataclass
class LLMResult:
    verdict: Verdict
    scam_type: str | None
    headline: str
    explanation: str


_SYSTEM = (
    "You help elderly, non-technical people in India deal with scams. "
    "Reply ONLY with a JSON object: {\"verdict\": \"safe\"|\"suspicious\"|\"scam\", \"scam_type\": string|null, "
    "\"headline\": string, \"explanation\": string}. "
    "Write headline and explanation in {lang}. Use very short, simple sentences. No jargon. "
    "headline: one sentence telling them what to do. explanation: 2-4 sentences. "
    "Only mention phone numbers or websites that appear in the provided directory. Never invent numbers."
)

_SEVERITY = {Verdict.safe: 0, Verdict.suspicious: 1, Verdict.scam: 2}


def _extract_json(content: str) -> dict:
    content = content.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", content, re.S)
    if fence:
        content = fence.group(1)
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end <= start:
        raise LLMError("The AI gave an answer we could not read.")
    try:
        return json.loads(content[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMError("The AI gave an answer we could not read.") from e


async def refine(
    *,
    text: str,
    situation: Situation,
    language: Language,
    signals: list[Signal],
    rule_verdict: Verdict,
    rule_scam_type: str | None,
    contacts: list[Contact],
    client: httpx.AsyncClient | None = None,
) -> LLMResult:
    if get_chaos().llm_down:
        raise LLMError("AI helper is switched off right now (maintenance).")
    s = get_settings()
    if not s.llm_configured:
        raise LLMError("AI helper is not set up. Showing rule-based advice.")

    user = {
        "message": text[:4000],
        "situation": situation.value,
        "rule_verdict": rule_verdict.value,
        "rule_scam_type": rule_scam_type,
        "rule_signals": [{"id": x.id, "label": x.label, "evidence": x.evidence} for x in signals],
        "directory": [{"id": c.id, "name": c.name, "phone": c.phone, "url": c.url} for c in contacts],
    }
    payload = {
        "model": s.llm_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": _SYSTEM.replace("{lang}", "Hindi (Devanagari)" if language == Language.hi else "English")},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    }
    headers = {"Authorization": f"Bearer {s.llm_api_key}"} if s.llm_api_key else {}
    url = s.llm_base_url.rstrip("/") + "/chat/completions"
    own = client is None
    client = client or httpx.AsyncClient(timeout=s.llm_timeout_seconds)
    try:
        resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise LLMError("AI helper took too long to answer.") from e
    except httpx.HTTPError as e:
        raise LLMError("Could not reach the AI helper.") from e
    finally:
        if own:
            await client.aclose()
    if resp.status_code != 200:
        raise LLMError(f"AI helper returned an error ({resp.status_code}).")
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError("The AI gave an answer we could not read.") from e

    data = _extract_json(content or "")
    try:
        verdict = Verdict(str(data["verdict"]).lower())
        headline = str(data["headline"]).strip()
        explanation = str(data["explanation"]).strip()
    except (KeyError, ValueError) as e:
        raise LLMError("The AI gave an answer we could not read.") from e
    if not headline or not explanation:
        raise LLMError("The AI gave an empty answer.")
    scam_type = data.get("scam_type") or rule_scam_type
    # Safety floor: the model may raise risk but never lower it. Its text would then
    # contradict the verdict, so discard it and show the rule-based advice instead.
    if _SEVERITY[verdict] < _SEVERITY[rule_verdict]:
        raise LLMError("AI answer was less cautious than our safety rules, so we show the rule-based advice.")
    return LLMResult(verdict=verdict, scam_type=scam_type if isinstance(scam_type, str) else None,
                     headline=headline[:300], explanation=explanation[:1500])
