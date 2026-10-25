import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, useStaffToken } from "../api/client";
import type { Case } from "../api/types";
import { StaffGate, staffError } from "../components";

// Staff page: English only (lang="en"), behind the shared staff token.
export default function Coordinator() {
  const token = useStaffToken();
  const [queue, setQueue] = useState<Case[]>([]);
  const [who, setWho] = useState(() => localStorage.getItem("coordinator") ?? "");
  const [sel, setSel] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const revision = useRef(0);

  const load = useCallback(async () => {
    const rev = revision.current;
    try { const q = await api.queue(); if (rev === revision.current) { setQueue(q); setErr(null); } }
    catch (e) { setErr(staffError(e)); }
  }, []);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => { await load(); if (alive) timer = setTimeout(tick, 3000); };
    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [load, token]);
  useEffect(() => { localStorage.setItem("coordinator", who); }, [who]);

  async function act(kind: "claim" | "resolve", id: string) {
    if (!who.trim()) { setErr("Enter your name first."); return; }
    try { await (kind === "claim" ? api.claim : api.resolve)(id, { coordinator: who.trim() }); revision.current++; load(); }
    catch (e) { setErr(staffError(e)); }
  }
  const c = queue.find((x) => x.id === sel);

  return (
    <div className="staff" lang="en">
      <h1>Coordinator queue</h1>
      <StaffGate>
        <label className="who">Your name <input value={who} onChange={(e) => setWho(e.target.value)} /></label>
        {err && <p className="error" role="alert">{err}</p>}
        <div className="staff-grid">
          <table>
            <thead><tr><th>Person</th><th>Status</th><th>Lost ₹</th><th>Unanswered</th><th>Updated</th><th>Actions</th></tr></thead>
            <tbody>
              {queue.length === 0 && <tr><td colSpan={6} className="muted">No cases waiting.</td></tr>}
              {queue.map((q) => (
                <tr key={q.id} className={q.id === sel ? "sel" : ""}>
                  <td>{q.person_name}</td>
                  <td><span className={`pill pill-${q.status}`}>{q.status}</span>{q.coordinator ? ` ${q.coordinator}` : ""}</td>
                  <td>{q.amount_lost_inr?.toLocaleString("en-IN") ?? "–"}</td>
                  <td>{q.unanswered_checkins}</td>
                  <td>{new Date(q.updated_at).toLocaleTimeString()}</td>
                  <td className="row-actions">
                    <button aria-pressed={q.id === sel} aria-label={`View case of ${q.person_name}`} onClick={() => setSel(q.id)}>View</button>
                    {q.status === "escalated" && <button aria-label={`Claim case of ${q.person_name}`} onClick={() => act("claim", q.id)}>Claim</button>}
                    <button aria-label={`Resolve case of ${q.person_name}`} onClick={() => act("resolve", q.id)}>Resolve</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {c && (
            <aside className="detail" aria-label={`Case of ${c.person_name}`}>
              <h2>{c.person_name} <small className="muted">{c.language}</small></h2>
              <p lang={c.language}>{c.description}</p>
              <dl>
                <dt>Telegram</dt><dd>{c.telegram_chat_id ?? "– (in-app only: no way to contact them directly)"}</dd>
                <dt>Trusted contact</dt><dd>{c.trusted_contact_name ?? "–"} {c.trusted_contact_telegram_chat_id ?? ""}</dd>
                <dt>Check-ins sent</dt><dd>{c.checkins_sent}</dd>
                <dt>Workflow</dt><dd>{c.workflow_id ?? "–"}{c.followup_pending ? " (follow-up update pending)" : ""}</dd>
              </dl>
              <h3>Steps</h3>
              <ul>{c.steps.map((s) => <li key={s.id}>{s.done ? "✅" : "⬜"} {s.title}</li>)}</ul>
              <h3>Timeline</h3>
              <ul>{c.timeline.map((e, i) => <li key={i}><small className="muted">{new Date(e.at).toLocaleTimeString()}</small> {e.message}</li>)}</ul>
              <Link to={`/case/${c.id}`}>Open person's view</Link>
            </aside>
          )}
        </div>
      </StaffGate>
    </div>
  );
}
