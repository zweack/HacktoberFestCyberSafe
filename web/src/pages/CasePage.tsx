import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, recentCase } from "../api/client";
import type { Case, CheckinAnswer, Notification } from "../api/types";
import { BackHome, errorText, FocusHeading, ReadAloud } from "../components";
import { useI18n } from "../i18n";

const fmt = (iso: string) => new Date(iso).toLocaleString(undefined, { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" });
const POLL_MS = 3000;

export default function CasePage() {
  const { id = "" } = useParams();
  const { t, lang } = useI18n();
  const [c, setC] = useState<Case | null>(null);
  const [notes, setNotes] = useState<Notification[]>([]);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [notesErr, setNotesErr] = useState(false);
  const [actionErr, setActionErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // The check-in number we answered; a new check-in (higher count) shows the question again.
  const [answeredAt, setAnsweredAt] = useState<number | null>(null);
  // Bumped by every successful action: a poll that started before it is stale and dropped.
  const revision = useRef(0);

  // Reset everything when the case id changes.
  useEffect(() => {
    setC(null); setNotes([]); setLoadErr(null); setNotesErr(false); setActionErr(null); setAnsweredAt(null);
    revision.current++;
  }, [id]);

  const load = useCallback(async (isCurrent: () => boolean) => {
    const rev = revision.current;
    // Case and notification log load independently: a failing log never hides the plan.
    const [cc, nn] = await Promise.allSettled([api.getCase(id), api.notifications(id)]);
    if (!isCurrent() || rev !== revision.current) return;
    if (cc.status === "fulfilled") { setC(cc.value); setLoadErr(null); recentCase.set(id); }
    else setLoadErr(errorText(cc.reason, t));
    if (nn.status === "fulfilled") { setNotes(nn.value); setNotesErr(false); } else setNotesErr(true);
  }, [id, t]);

  useEffect(() => {
    // One request at a time: the next poll is scheduled only after the previous one ends.
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      await load(() => alive);
      if (alive) timer = setTimeout(tick, POLL_MS);
    };
    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [load]);

  async function act(fn: () => Promise<Case>, after?: (c: Case) => void) {
    setBusy(true); setActionErr(null);
    try { const next = await fn(); revision.current++; setC(next); after?.(next); }
    catch (e) { setActionErr(errorText(e, t)); }
    finally { setBusy(false); }
  }
  const markDone = (stepId: string) => act(() => api.stepDone(id, stepId));
  const answer = (a: CheckinAnswer) => act(() => api.checkin(id, { answer: a }), (next) => setAnsweredAt(next.checkins_sent));

  if (!c) return (<><BackHome /><p role={loadErr ? "alert" : "status"}>{loadErr ?? t.loading}</p></>);
  const answered = answeredAt !== null && answeredAt >= c.checkins_sent;
  const spoken = [t.caseTitle, t[`status_${c.status}`], ...c.steps.filter((s) => !s.done).map((s) => `${s.title}. ${s.detail}`)].join(" ");
  return (
    <>
      <BackHome />
      <FocusHeading>{t.caseTitle}</FocusHeading>
      {/* Only the status line is a live region, so polling does not re-announce the page. */}
      <p className={`status status-${c.status}`} role="status">{t[`status_${c.status}`]}{c.coordinator ? ` · ${t.helper}: ${c.coordinator}` : ""}</p>
      {c.followup_pending && <p className="note">{t.followupPending}</p>}
      {loadErr && <p className="error">{loadErr}</p>}
      {actionErr && <p className="error" role="alert">{actionErr}</p>}
      <p className="muted">{t.returnHint}</p>
      <ReadAloud text={spoken} language={c.language} />

      <section>
        <h2>{t.yourSteps}</h2>
        <p className="muted">{t.tapWhenDone}</p>
        <ul className="checklist" lang={c.language}>
          {c.steps.map((s) => (
            <li key={s.id}>
              <button className={s.done ? "check done" : "check"} disabled={s.done || busy} onClick={() => markDone(s.id)} aria-pressed={s.done}>
                <span className="box" aria-hidden="true">{s.done ? "✓" : ""}</span>
                <span><strong>{s.title}</strong><small>{s.detail}</small></span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {c.status !== "resolved" && (
        <section className="checkin">
          <h2>{t.howAreYou}</h2>
          {answered ? <p className="ok" role="status">{t.thanks}</p>
            : answeredAt !== null && <p className="note" role="status">{t.newQuestion}</p>}
          <div className="answers">
            <button className="btn btn-safe" disabled={busy} onClick={() => answer("done")}>✓ {t.ansDone}</button>
            <button className="btn btn-quiet" disabled={busy} onClick={() => answer("not_yet")}>{t.ansNotYet}</button>
            <button className="btn btn-help" disabled={busy} onClick={() => answer("need_help")}>🙋 {t.ansHelp}</button>
          </div>
        </section>
      )}

      <section>
        <h2>{t.timeline}</h2>
        <ol className="timeline">
          {[...c.timeline].reverse().map((e, i) => {
            const label = (t as Record<string, unknown>)[`tl_${e.kind}`];
            return (
              <li key={i} className={`tl-${e.kind}`}>
                <time>{fmt(e.at)}</time> {typeof label === "string" ? label : e.kind}
                {lang === "en" && typeof label === "string" && e.message !== label && <span className="muted"> · {e.message}</span>}
              </li>
            );
          })}
        </ol>
      </section>

      <section>
        <h2>{t.messagesSent}</h2>
        {notesErr && <p className="error">{t.notesFailed}</p>}
        <ul className="notes">
          {notes.map((n) => (
            <li key={n.id} className={`note-${n.status}`}>
              <span className={`pill pill-${n.status}`}>{t[`pill_${n.status}`]}</span>
              <span className="muted">{t[`chan_${n.channel}`]} · {n.attempts} {t.attempts}</span>
              <div lang={c.language}>{n.message}</div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
