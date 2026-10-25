"""Simulated SMS/email inbox feed. Owner: detector."""

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app import db
from app.detector.analyze import analyze
from app.schemas import AnalyzeRequest, Channel, FeedMessage, Language

router = APIRouter(tags=["feed"])

_COLLECTION = "feed_messages"
_CURSOR_KEY = "feed_cursor"

# (channel, sender, subject, text, language). Order mixes scams with genuine messages.
SCRIPT: list[tuple[Channel, str, str | None, str, Language]] = [
    (Channel.sms, "VM-SBIINB", None,
     "Dear Customer, your SBI YONO account will be blocked today. Update your PAN/KYC immediately: http://sbi-kyc-update.xyz/login",
     Language.en),
    (Channel.sms, "AX-HDFCBK", None,
     "OTP is 482913 for your txn of Rs 1,250.00 at BIGBASKET on HDFC Bank card xx4321. Valid for 10 mins. Do not share it with anyone.",
     Language.en),
    (Channel.whatsapp, "+91 98765 43210", None,
     "Hi Papa, this is my new number. Phone gir gaya. I am in trouble, please send Rs 15000 urgently on this UPI. Mummy ko mat batana.",
     Language.en),
    (Channel.sms, "VK-AMAZON", None,
     "Your Amazon order #403-1182 with 1 item has been shipped and will arrive tomorrow by 9 PM. Track at amazon.in/orders",
     Language.en),
    (Channel.call, "+91 70021 88812", None,
     "Main Mumbai Police Cyber Cell se bol raha hoon. Aapke Aadhaar par case registered hai, FedEx parcel mein drugs mile hain. Video call par raho, digital arrest hai, kisi ko mat batana.",
     Language.hi),
    (Channel.sms, "BZ-MSEDCL", None,
     "प्रिय उपभोक्ता, आपका बिजली बिल अपडेट नहीं है। आज रात 9:30 बजे बिजली काट दी जाएगी। तुरंत संपर्क करें 9123456780",
     Language.hi),
    (Channel.whatsapp, "Beta Rohit", None,
     "Maa, I reached Pune safely. Will call you after dinner. Take your medicines on time.",
     Language.en),
    (Channel.email, "refunds@incometax-refund-gov.in.net", "Income Tax Refund Approved",
     "You are eligible for an income tax refund of Rs 18,450. Verify your bank account within 24 hours to receive it: https://incometax-refund-gov.in.net/claim",
     Language.en),
    (Channel.whatsapp, "+91 88263 11902", None,
     "Part time job! Like YouTube videos and earn Rs 3000 daily from home. Prepaid task bonus. Contact HR on WhatsApp.",
     Language.en),
    (Channel.sms, "+91 90011 22334", None,
     "Galti se aapke account mein Rs 5000 bhej diye. Please wapas kar do. Maine collect request bheji hai, accept karke UPI PIN daalo.",
     Language.hi),
    (Channel.call, "Bank Support", None,
     "Sir I am calling from your bank customer care. To stop the fraud transaction please install AnyDesk and tell me the OTP you receive.",
     Language.en),
    (Channel.email, "alerts@kotak.com", "Your monthly statement is ready",
     "Dear customer, your account statement for September is now available in your net banking. Kotak Bank never asks for your PIN or OTP.",
     Language.en),
]


def _cursor() -> int:
    return int(db.get_json(_CURSOR_KEY, {"next": 0}).get("next", 0))


@router.get("/feed", response_model=list[FeedMessage])
def list_feed() -> list[FeedMessage]:
    return db.list_all(_COLLECTION, FeedMessage)


@router.post("/feed/next", response_model=FeedMessage)
async def next_message() -> FeedMessage:
    i = _cursor()
    channel, sender, subject, text, lang = SCRIPT[i % len(SCRIPT)]
    db.put_json(_CURSOR_KEY, {"next": i + 1})
    analysis = await analyze(AnalyzeRequest(text=text, channel=channel, sender=sender, language=lang))
    msg = FeedMessage(channel=channel, sender=sender, subject=subject, text=text, analysis=analysis)
    db.put(_COLLECTION, msg)
    return msg


@router.post("/feed/reset")
def reset_feed() -> dict:
    for m in db.list_all(_COLLECTION, FeedMessage, limit=10_000):
        db.delete(_COLLECTION, m.id)
    db.put_json(_CURSOR_KEY, {"next": 0})
    return {"status": "ok"}


@router.get("/feed/stream")
async def stream(request: Request) -> StreamingResponse:
    async def events():
        seen = {m.id for m in db.list_all(_COLLECTION, FeedMessage)}
        yield ": connected\n\n"
        while not await request.is_disconnected():
            await asyncio.sleep(1)
            fresh = [m for m in reversed(db.list_all(_COLLECTION, FeedMessage, limit=50)) if m.id not in seen]
            for m in fresh:
                seen.add(m.id)
                yield f"event: message\nid: {m.id}\ndata: {json.dumps(m.model_dump(mode='json'), ensure_ascii=False)}\n\n"
            if not fresh:
                yield ": ping\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
