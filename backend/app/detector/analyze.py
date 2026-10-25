"""Combine rules, situation steps, directory contacts and optional LLM text."""

import asyncio
import logging
import time

from app import metrics
from app.chaos import get_chaos
from app.detector import llm, steps
from app.detector.rules import run_rules
from app.schemas import AnalyzeRequest, AnalyzeResponse, Situation, Verdict

log = logging.getLogger("cybersafe.detector")


async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    started = time.perf_counter()
    chaos = get_chaos()
    if chaos.slow_analyze_ms:
        await asyncio.sleep(chaos.slow_analyze_ms / 1000)

    text = req.text if not req.sender else f"{req.sender}\n{req.text}"
    rules = run_rules(text, req.language)
    verdict, scam_type = rules.verdict, rules.scam_type
    # Someone already paid or is being pressured live: never call that "safe".
    if req.situation != Situation.received and verdict == Verdict.safe:
        verdict = Verdict.suspicious
    contacts = steps.contacts(req.situation, verdict, scam_type, text, req.language)

    headline = steps.rule_headline(req.situation, verdict, req.language)
    explanation = steps.rule_explanation([s.label for s in rules.signals], verdict, req.situation, req.language)
    ai_used, ai_error = False, None
    try:
        result = await llm.refine(
            text=req.text, situation=req.situation, language=req.language, signals=rules.signals,
            rule_verdict=verdict, rule_scam_type=scam_type, contacts=contacts,
        )
    except llm.LLMError as e:
        ai_error = str(e)
    except Exception:  # unexpected bug: still visible, never fatal
        log.exception("llm refine crashed")
        ai_error = "AI helper failed unexpectedly. Showing rule-based advice."
    else:
        ai_used = True
        if result.verdict != verdict:
            verdict = result.verdict
            contacts = steps.contacts(req.situation, verdict, result.scam_type, text, req.language)
        scam_type, headline, explanation = result.scam_type, result.headline, result.explanation

    risk = rules.risk_score
    if verdict == Verdict.scam:
        risk = max(risk, 65)
    elif verdict == Verdict.suspicious:
        risk = max(risk, 30)

    resp = AnalyzeResponse(
        verdict=verdict, risk_score=risk, scam_type=scam_type, situation=req.situation,
        headline=headline, explanation=explanation, signals=rules.signals,
        steps=steps.steps_for(req.situation, verdict, req.language), contacts=contacts,
        language=req.language, ai_used=ai_used, ai_error=ai_error,
    )
    metrics.inc("cybersafe_analyze_total", verdict=verdict.value, ai_used=str(ai_used).lower())
    # No message text in logs (PII): only derived fields.
    log.info("analysis", extra={
        "event": "analysis", "verdict": verdict.value, "risk_score": risk, "scam_type": scam_type,
        "situation": req.situation.value, "channel": req.channel.value, "language": req.language.value,
        "signals": [s.id for s in rules.signals], "ai_used": ai_used, "ai_error": ai_error,
        "text_len": len(req.text), "duration_ms": round((time.perf_counter() - started) * 1000),
    })
    return resp
