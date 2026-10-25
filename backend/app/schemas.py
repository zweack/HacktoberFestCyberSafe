"""Shared API contracts. The web app mirrors these in web/src/api/types.ts.

Change a field here only together with docs/API.md and the TypeScript types.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Language(StrEnum):
    en = "en"
    hi = "hi"


class Channel(StrEnum):
    sms = "sms"
    email = "email"
    whatsapp = "whatsapp"
    call = "call"
    other = "other"


class Situation(StrEnum):
    """Where the person is in the scam timeline."""

    received = "received"  # "I got this message, is it real?"
    in_progress = "in_progress"  # "Someone is talking to me / asking me to do something right now"
    victim = "victim"  # "I already paid / shared OTP / installed an app"


class Verdict(StrEnum):
    safe = "safe"
    suspicious = "suspicious"
    scam = "scam"


# ---------------------------------------------------------------- directory


class Contact(BaseModel):
    id: str
    name: str
    description: str
    phone: str | None = None
    url: str | None = None
    region: str = "IN"
    category: str  # helpline | reporting | bank | telecom | regulator
    source_url: str  # where the number/link was verified
    name_hi: str | None = None
    description_hi: str | None = None


# ---------------------------------------------------------------- analysis


class Signal(BaseModel):
    id: str  # e.g. "otp_request", "urgency", "lookalike_domain"
    label: str  # plain-language, in the requested language
    weight: float = Field(ge=0, le=1)
    evidence: str | None = None  # the snippet that triggered it


class ActionStep(BaseModel):
    id: str
    title: str
    detail: str
    urgent: bool = False
    contact_id: str | None = None


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    channel: Channel = Channel.other
    sender: str | None = None
    situation: Situation = Situation.received
    language: Language = Language.en


class AnalyzeResponse(BaseModel):
    verdict: Verdict
    risk_score: int = Field(ge=0, le=100)
    scam_type: str | None = None  # e.g. "kyc_update", "digital_arrest", "upi_collect"
    situation: Situation
    headline: str  # one short sentence, e.g. "This is a scam. Do not click the link."
    explanation: str  # plain language, 2-4 sentences
    signals: list[Signal] = []
    steps: list[ActionStep] = []
    contacts: list[Contact] = []
    language: Language = Language.en
    ai_used: bool = False
    ai_error: str | None = None  # surfaced to the UI; never silently hidden


# ---------------------------------------------------------------- cases / follow-up


class CaseStatus(StrEnum):
    open = "open"
    checking_in = "checking_in"
    escalated = "escalated"  # unanswered, waiting for a human coordinator
    claimed = "claimed"  # a coordinator is handling it
    resolved = "resolved"


class CaseStep(ActionStep):
    done: bool = False
    done_at: datetime | None = None


class CaseCreate(BaseModel):
    person_name: str = Field(min_length=1, max_length=120)
    language: Language = Language.en
    situation: Situation = Situation.victim
    description: str = Field(min_length=1, max_length=10_000)
    amount_lost_inr: float | None = None
    telegram_chat_id: str | None = None
    trusted_contact_name: str | None = None
    trusted_contact_telegram_chat_id: str | None = None
    analysis: AnalyzeResponse | None = None


class Case(BaseModel):
    id: str = Field(default_factory=lambda: new_id("case"))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    status: CaseStatus = CaseStatus.open
    person_name: str
    language: Language = Language.en
    situation: Situation
    description: str
    amount_lost_inr: float | None = None
    telegram_chat_id: str | None = None
    trusted_contact_name: str | None = None
    trusted_contact_telegram_chat_id: str | None = None
    analysis: AnalyzeResponse | None = None
    steps: list[CaseStep] = []
    workflow_id: str | None = None
    checkins_sent: int = 0
    unanswered_checkins: int = 0
    coordinator: str | None = None
    # True while a change could not reach the follow-up service yet; it is retried automatically.
    followup_pending: bool = False
    timeline: list["TimelineEvent"] = []


class TimelineEvent(BaseModel):
    at: datetime = Field(default_factory=utcnow)
    kind: str  # created | notified | checkin_sent | checkin_answered | step_done | escalated | claimed | resolved | error
    message: str


class CheckinAnswer(StrEnum):
    done = "done"  # "I did the steps"
    not_yet = "not_yet"
    need_help = "need_help"  # escalate to a human now


class CheckinResponse(BaseModel):
    answer: CheckinAnswer
    note: str | None = None


class CoordinatorAction(BaseModel):
    coordinator: str = Field(min_length=1, max_length=120)
    note: str | None = None


# ---------------------------------------------------------------- notifications


class NotificationChannel(StrEnum):
    in_app = "in_app"
    telegram = "telegram"


class NotificationStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ntf"))
    created_at: datetime = Field(default_factory=utcnow)
    case_id: str | None = None
    channel: NotificationChannel
    recipient: str  # person name, chat id, or "coordinator"
    message: str
    status: NotificationStatus = NotificationStatus.pending
    attempts: int = 0
    last_error: str | None = None


# ---------------------------------------------------------------- simulated inbox feed


class FeedMessage(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    received_at: datetime = Field(default_factory=utcnow)
    channel: Channel
    sender: str
    subject: str | None = None
    text: str
    analysis: AnalyzeResponse | None = None


# ---------------------------------------------------------------- ops


class ChaosSettings(BaseModel):
    """Fault switches the ops team (and the Kepler demo) can flip."""

    telegram_failure_rate: float = Field(default=0.0, ge=0, le=1)
    llm_down: bool = False
    slow_analyze_ms: int = Field(default=0, ge=0, le=60_000)


Case.model_rebuild()
