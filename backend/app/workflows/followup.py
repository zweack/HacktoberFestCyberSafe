"""CaseFollowUpWorkflow: follows up with a scam victim until they are safe.

Deterministic: no I/O here, only activities, timers and signals.
"""

import asyncio
from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.schemas import CaseStatus, CheckinAnswer, CheckinResponse, CoordinatorAction, NotificationChannel
    from app.workflows import messages
    from app.workflows.activities import (
        EscalateInput,
        EscalateResult,
        SendNotificationInput,
        UpdateCaseInput,
        escalate_to_coordinator,
        send_notification,
        update_case,
    )

NOTIFY_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=6,
)
DB_RETRY = RetryPolicy(initial_interval=timedelta(seconds=1), maximum_interval=timedelta(seconds=10))


def workflow_id(case_id: str) -> str:
    return f"case-{case_id}"


class FollowUpInput(BaseModel):
    case_id: str
    person_name: str
    language: str = "en"
    step_ids: list[str] = []
    step_titles: list[str] = []
    telegram_chat_id: str | None = None
    checkin_interval_seconds: int = 60
    max_unanswered_checkins: int = 2


class FollowUpState(BaseModel):
    status: CaseStatus = CaseStatus.open
    checkins_sent: int = 0
    unanswered_checkins: int = 0
    steps_done: list[str] = []
    coordinator: str | None = None
    last_answer: CheckinAnswer | None = None


@workflow.defn
class CaseFollowUpWorkflow:
    def __init__(self) -> None:
        self.s = FollowUpState()
        self._answers: list[CheckinResponse] = []
        self._resolve: CoordinatorAction | None = None
        self._all_steps: set[str] = set()

    # ------------------------------------------------------------ signals / query

    @workflow.signal
    def checkin_response(self, resp: CheckinResponse) -> None:
        self._answers.append(resp)

    @workflow.signal
    def step_done(self, step_id: str) -> None:
        if step_id not in self.s.steps_done:
            self.s.steps_done.append(step_id)

    @workflow.signal
    def coordinator_claim(self, action: CoordinatorAction) -> None:
        if self.s.status != CaseStatus.resolved:
            self.s.status, self.s.coordinator = CaseStatus.claimed, action.coordinator

    @workflow.signal
    def resolve(self, action: CoordinatorAction) -> None:
        self._resolve = action

    @workflow.query
    def state(self) -> FollowUpState:
        return self.s

    # ------------------------------------------------------------ helpers

    async def _notify(self, inp: FollowUpInput, message: str, *, checkin: bool = False,
                      telegram_chat: str | None = None, in_app_recipient: str | None = None) -> None:
        sends = []
        if in_app_recipient is not None:
            sends.append((NotificationChannel.in_app, in_app_recipient))
        if telegram_chat:
            sends.append((NotificationChannel.telegram, telegram_chat))
        for channel, recipient in sends:
            arg = SendNotificationInput(notification_id=f"ntf_{workflow.uuid4().hex[:12]}", case_id=inp.case_id,
                                        channel=channel, recipient=recipient, message=message, checkin=checkin)
            try:
                await workflow.execute_activity(send_notification, arg, start_to_close_timeout=timedelta(seconds=30),
                                                retry_policy=NOTIFY_RETRY)
            except Exception as e:  # retries exhausted: record it, but keep following up
                workflow.logger.warning("notification gave up: %s", e)
                await self._update(inp, event_kind="error", event_message=f"{channel.value} message failed after retries")

    async def _update(self, inp: FollowUpInput, **kw) -> None:
        await workflow.execute_activity(update_case, UpdateCaseInput(case_id=inp.case_id, **kw),
                                        start_to_close_timeout=timedelta(seconds=30), retry_policy=DB_RETRY)

    def _all_done(self) -> bool:
        return bool(self._all_steps) and self._all_steps <= set(self.s.steps_done)

    async def _escalate(self, inp: FollowUpInput, reason: str) -> None:
        if self.s.status not in (CaseStatus.claimed, CaseStatus.resolved):
            self.s.status = CaseStatus.escalated
        res: EscalateResult = await workflow.execute_activity(
            escalate_to_coordinator, EscalateInput(case_id=inp.case_id, reason=reason),
            start_to_close_timeout=timedelta(seconds=30), retry_policy=DB_RETRY)
        if res.coordinator_chat_id:
            await self._notify(inp, res.coordinator_message, telegram_chat=res.coordinator_chat_id)
        if res.trusted_contact_chat_id and res.trusted_contact_message:
            await self._notify(inp, res.trusted_contact_message, telegram_chat=res.trusted_contact_chat_id)

    async def _close(self, inp: FollowUpInput, why: str) -> None:
        self.s.status = CaseStatus.resolved
        await self._notify(inp, messages.closing(inp.person_name, inp.language),
                           in_app_recipient=inp.person_name, telegram_chat=inp.telegram_chat_id)
        await self._update(inp, status=CaseStatus.resolved, event_kind="resolved", event_message=why)

    # ------------------------------------------------------------ main

    @workflow.run
    async def run(self, inp: FollowUpInput) -> FollowUpState:
        self._all_steps = set(inp.step_ids)
        await self._notify(inp, messages.action_plan(inp.person_name, inp.language, inp.step_titles),
                           in_app_recipient=inp.person_name, telegram_chat=inp.telegram_chat_id)
        await self._update(inp, event_kind="notified", event_message="Action plan sent")
        self.s.status = CaseStatus.checking_in
        await self._update(inp, status=CaseStatus.checking_in)

        while True:
            if self._resolve is not None:
                break
            if self.s.status in (CaseStatus.escalated, CaseStatus.claimed):
                # A human owns it now; wait for the coordinator to resolve.
                await workflow.wait_condition(lambda: self._resolve is not None)
                break
            if self._all_done():
                await self._close(inp, "All steps done")
                return self.s
            try:
                await workflow.wait_condition(
                    lambda: bool(self._answers) or self._resolve is not None or self._all_done()
                    or self.s.status == CaseStatus.claimed,
                    timeout=timedelta(seconds=inp.checkin_interval_seconds),
                )
            except asyncio.TimeoutError:
                if self.s.unanswered_checkins >= inp.max_unanswered_checkins:
                    await self._escalate(inp, f"{self.s.unanswered_checkins} check-ins unanswered")
                    continue
                self.s.checkins_sent += 1
                self.s.unanswered_checkins += 1
                await self._notify(inp, messages.checkin(inp.person_name, inp.language), checkin=True,
                                   in_app_recipient=inp.person_name, telegram_chat=inp.telegram_chat_id)
                await self._update(inp, checkins_sent_inc=1, unanswered_checkins=self.s.unanswered_checkins,
                                   event_kind="checkin_sent", event_message=messages.checkin(inp.person_name, "en"))
                continue

            while self._answers:
                ans = self._answers.pop(0)
                self.s.last_answer = ans.answer
                self.s.unanswered_checkins = 0
                if ans.answer == CheckinAnswer.done:
                    await self._close(inp, "Person confirmed the steps are done")
                    return self.s
                if ans.answer == CheckinAnswer.need_help:
                    await self._escalate(inp, "Person asked for help")
                    break

        action = self._resolve
        self.s.status = CaseStatus.resolved
        await self._notify(inp, messages.closing(inp.person_name, inp.language),
                           in_app_recipient=inp.person_name, telegram_chat=inp.telegram_chat_id)
        await self._update(inp, status=CaseStatus.resolved, event_kind="resolved",
                           event_message=f"Resolved by {action.coordinator}" + (f": {action.note}" if action.note else ""))
        return self.s
