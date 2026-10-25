import json

import httpx
import pytest

from app import metrics
from app.chaos import set_chaos
from app.config import get_settings
from app.detector import llm
from app.detector.analyze import analyze
from app.detector.rules import run_rules
from app.directory.directory import get_contact, load_directory
from app.schemas import AnalyzeRequest, ChaosSettings, Language, Situation, Verdict


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "llm_base_url", "")
    monkeypatch.setattr(s, "llm_model", "")
    monkeypatch.setattr(s, "llm_api_key", "")


SCAMS = [
    ("Your SBI account will be blocked today. Update KYC now: http://sbi-kyc.xyz", "kyc_update"),
    ("Sir please share the OTP you just received to cancel the order", "otp_request"),
    ("You will receive Rs 2000 cashback. Enter UPI PIN to receive money now", "upi_collect"),
    ("Congratulations! You have won Rs 25 lakh in KBC lottery. Pay processing fee of Rs 5000", "lottery_prize"),
    ("This is CBI. A case is registered on your Aadhaar. Stay on video call, you are under digital arrest. Don't tell anyone.", "digital_arrest"),
    ("Your FedEx parcel containing drugs was seized by customs. Press 1 urgently.", "courier_parcel"),
    ("Dear consumer your electricity will be disconnected tonight at 9:30 as bill not updated. Call 9876543210", "electricity_disconnect"),
    ("Part time job: like YouTube videos and earn Rs 5000 daily from home. Pay registration fee", "task_job"),
    ("Join our VIP stock group for guaranteed returns of 30% monthly. Join now, last chance", "investment"),
    ("Pre-approved instant loan of Rs 50000 with no documents, in 5 minutes! Pay processing fee today", "loan_app"),
    ("Your income tax refund of Rs 15,490 is approved. Verify at http://itrefund-gov.in.net now", "income_tax_refund"),
    ("Your credit card reward points worth Rs 7,850 expire today. Redeem now: bit.ly/rwd", "reward_points"),
    ("Hi Mom this is my new number, phone broke. I'm in trouble, send money urgently", "family_emergency"),
    ("I sent Rs 3000 by mistake to your number, please return it immediately", "wrong_transfer"),
    ("To get your refund please install AnyDesk and share the code", "remote_access"),
    ("I have your private video call recording. I will make it viral to your family contacts unless you pay", "sextortion"),
]


@pytest.mark.parametrize("text,scam_type", SCAMS)
def test_scam_types_detected(text, scam_type):
    r = run_rules(text)
    assert r.verdict == Verdict.scam, (r.risk_score, [s.id for s in r.signals])
    assert any(s.id == scam_type for s in r.signals)


def test_hindi_digital_arrest():
    r = run_rules("मैं सीबीआई से बोल रहा हूँ। आपके आधार पर केस दर्ज है। आपको गिरफ्तार किया जाएगा, तुरंत पैसे भेजें।", Language.hi)
    assert r.verdict == Verdict.scam and r.scam_type == "digital_arrest"
    assert all(any("ऀ" <= ch <= "ॿ" for ch in s.label) for s in r.signals)


def test_hinglish_otp():
    r = run_rules("Bank se bol raha hoon, aapka OTP batao jaldi warna account band ho jayega")
    assert r.verdict == Verdict.scam and {"otp_request", "kyc_update"} <= {s.id for s in r.signals}


@pytest.mark.parametrize("text", [
    "OTP is 482913 for your txn of Rs 1,250.00 at BIGBASKET on HDFC Bank card xx4321. Do not share it with anyone.",
    "Your Amazon order has been shipped and will arrive tomorrow. Track at amazon.in/orders",
    "Maa, I reached Pune safely. Will call you after dinner.",
    "आपका OTP 123456 है। इसे किसी को न बताएं।",
    "Your account statement for September is ready. Kotak Bank never asks for your PIN or OTP.",
])
def test_safe_messages_stay_safe(text):
    r = run_rules(text)
    assert r.verdict == Verdict.safe, [s.id for s in r.signals]


def test_apk_and_ip_links():
    ids = {s.id for s in run_rules("Download http://192.168.4.2/update.apk").signals}
    assert {"apk_link", "ip_link"} <= ids


def test_directory_has_sources_and_hindi():
    d = load_directory()
    assert len(d) >= 15
    for c in d:
        assert c.source_url.startswith("https://") and c.name_hi and c.description_hi
    assert get_contact("ncrp_1930").phone == "1930"
    assert get_contact("elderline").phone == "14567"


async def test_received_steps():
    r = await analyze(AnalyzeRequest(text=SCAMS[0][0]))
    ids = [s.id for s in r.steps]
    assert ids[:2] == ["dont_click", "dont_reply"] and "report_chakshu" in ids
    assert "chakshu" in [c.id for c in r.contacts]
    assert not r.ai_used and r.ai_error


async def test_in_progress_steps_hindi():
    r = await analyze(AnalyzeRequest(text="He is asking me to install AnyDesk", situation=Situation.in_progress, language=Language.hi))
    assert r.steps[0].id == "hang_up" and r.steps[0].urgent
    assert "फ़ोन" in r.steps[0].title
    assert r.verdict == Verdict.scam


async def test_victim_steps_and_bank_contact():
    r = await analyze(AnalyzeRequest(text="I shared OTP with HDFC caller and lost money", situation=Situation.victim))
    assert r.steps[0].id == "call_1930" and r.steps[0].urgent
    ids = [c.id for c in r.contacts]
    assert ids[0] == "ncrp_1930" and "bank_hdfc" in ids
    assert r.verdict != Verdict.safe


async def test_safe_received_has_minimal_steps():
    r = await analyze(AnalyzeRequest(text="Maa, I reached Pune safely."))
    assert r.verdict == Verdict.safe and [s.id for s in r.steps] == ["verify_official"]


# ---------------------------------------------------------------- LLM paths


def _configure(monkeypatch, handler):
    s = get_settings()
    monkeypatch.setattr(s, "llm_base_url", "http://llm.test/v1")
    monkeypatch.setattr(s, "llm_model", "gemma")
    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw))


def _reply(obj):
    return lambda req: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(obj)}}]})


async def test_llm_not_configured():
    r = await analyze(AnalyzeRequest(text="hello"))
    assert r.ai_used is False and "not set up" in r.ai_error


async def test_llm_success(monkeypatch):
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return _reply({"verdict": "scam", "scam_type": "kyc_update", "headline": "Do not click.", "explanation": "Fake bank."})(req)

    _configure(monkeypatch, handler)
    r = await analyze(AnalyzeRequest(text=SCAMS[0][0]))
    assert r.ai_used and r.ai_error is None and r.explanation == "Fake bank."
    assert r.headline == "This is a scam. Do not click, reply or pay."  # headline is never model text
    user = json.loads(seen["body"]["messages"][1]["content"])
    assert user["rule_signals"] and user["directory"]


async def test_llm_cannot_downgrade(monkeypatch):
    _configure(monkeypatch, _reply({"verdict": "safe", "scam_type": None, "headline": "All fine.", "explanation": "Safe."}))
    r = await analyze(AnalyzeRequest(text=SCAMS[0][0]))
    assert r.verdict == Verdict.scam and not r.ai_used and r.headline != "All fine."


async def test_llm_can_raise(monkeypatch):
    _configure(monkeypatch, _reply({"verdict": "suspicious", "scam_type": "other", "headline": "Be careful.", "explanation": "Odd."}))
    r = await analyze(AnalyzeRequest(text="Hello uncle, how are you?"))
    assert r.verdict == Verdict.suspicious and r.risk_score >= 30 and r.ai_used


@pytest.mark.parametrize("handler,needle", [
    (lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}), "could not read"),
    (lambda req: httpx.Response(500, text="boom"), "500"),
    (lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("t")), "too long"),
    (lambda req: (_ for _ in ()).throw(httpx.ConnectError("x")), "reach"),
])
async def test_llm_failures(monkeypatch, handler, needle):
    _configure(monkeypatch, handler)
    r = await analyze(AnalyzeRequest(text=SCAMS[1][0]))
    assert not r.ai_used and needle in r.ai_error and r.verdict == Verdict.scam


async def test_chaos_llm_down(monkeypatch):
    _configure(monkeypatch, _reply({"verdict": "scam", "headline": "x", "explanation": "y"}))
    set_chaos(ChaosSettings(llm_down=True))
    r = await analyze(AnalyzeRequest(text="hello"))
    assert not r.ai_used and "switched off" in r.ai_error


async def test_metrics_and_no_pii_in_logs(caplog):
    caplog.set_level("INFO")
    await analyze(AnalyzeRequest(text="SECRETTEXT please share OTP now"))
    assert 'cybersafe_analyze_total{ai_used="false",verdict="scam"}' in metrics.render()
    assert "SECRETTEXT" not in caplog.text
    rec = next(r for r in caplog.records if getattr(r, "event", None) == "analysis")
    assert rec.verdict == "scam" and "SECRETTEXT" not in json.dumps(rec.__dict__, default=str)


def test_evidence_snippets_start_and_end_on_word_boundaries():
    from app.detector.rules import run_rules

    text = "Dear Customer, your SBI YONO account will be blocked today. Update PAN immediately: http://sbi-yono-kyc.in/update"
    words = set(text.split())
    for sig in run_rules(text).signals:
        assert sig.evidence
        first, last = sig.evidence.split()[0], sig.evidence.split()[-1]
        assert first in words and last in words, sig.evidence
