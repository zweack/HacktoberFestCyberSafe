import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Case, CheckinAnswer, Notification } from "../api/types";
import { BackHome } from "../components";
import { useI18n } from "../i18n";

const fmt = (iso: string) => new Date(iso).toLocaleString(undefined, { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" });

export default function CasePage() {
  const { id = "" } = useParams();
  const { t } = useI18n();
  const [c, setC] = useState<Case | null>(null);
  const [notes, setNotes] = useState<Notification[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [answered, setAnswered] = useState(false);

  const load = useCallback(async () => {
    try {
      const [cc, nn] = await Promise.all([api.getCase(id), api.notifications(id)]);
      setC(cc); setNotes(nn); setErr(null);
    } catch (e) { setErr(e instanceof Error ? e.message : t.tryAgain); }
  }, [id, t.tryAgain]);

  useEffect(() => {
    load();
    const h = setInterval(load, 3000);
    return () => clearInterval(h);
  }, [load]);

  async function markDone(stepId: string) {
    try { setC(await api.stepDone(id, stepId)); } catch { setErr(t.tryAgain); }
  }
  async function answer(a: CheckinAnswer) {
    try { setC(await api.checkin(id, { answer: a })); setAnswered(true); } catch { setErr(t.tryAgain); }
  }

  if (!c) return (<><BackHome /><p>{err ?? t.loading}</p></>);
  return (
    <>
      <BackHome />
      <h1>{t.caseTitle}</h1>
      <p className={`status status-${c.status}`}>{t[`status_${c.status}`]}{c.coordinator ? ` · ${t.helper}: ${c.coordinator}` : ""}</p>
      {err && <p className="error" role="alert">{err}</p>}

      <section>
        <h2>{t.yourSteps}</h2>
        <p className="muted">{t.tapWhenDone}</p>
        <ul className="checklist">
          {c.steps.map((s) => (
            <li key={s.id}>
              <button className={s.done ? "check done" : "check"} disabled={s.done} onClick={() => markDone(s.id)} aria-pressed={s.done}>
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
          {answered && <p className="ok" role="status">{t.thanks}</p>}
          <div className="answers">
            <button className="btn btn-safe" onClick={() => answer("done")}>✓ {t.ansDone}</button>
            <button className="btn btn-quiet" onClick={() => answer("not_yet")}>{t.ansNotYet}</button>
            <button className="btn btn-help" onClick={() => answer("need_help")}>🙋 {t.ansHelp}</button>
          </div>
        </section>
      )}

      <section>
        <h2>{t.timeline}</h2>
        <ol className="timeline">
          {[...c.timeline].reverse().map((e, i) => (
            <li key={i} className={`tl-${e.kind}`}><time>{fmt(e.at)}</time> {e.message}</li>
          ))}
        </ol>
      </section>

      <section>
        <h2>{t.messagesSent}</h2>
        <ul className="notes">
          {notes.map((n) => (
            <li key={n.id} className={`note-${n.status}`}>
              <span className={`pill pill-${n.status}`}>{n.status}</span>
              <span className="muted">{n.channel} → {n.recipient} · {n.attempts} {t.attempts}</span>
              <div>{n.message}</div>
              {n.last_error && <div className="error small">{n.last_error}</div>}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
