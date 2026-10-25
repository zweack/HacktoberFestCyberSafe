import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Case } from "../api/types";

export default function Coordinator() {
  const [queue, setQueue] = useState<Case[]>([]);
  const [who, setWho] = useState(() => localStorage.getItem("coordinator") ?? "");
  const [sel, setSel] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => api.queue().then((q) => { setQueue(q); setErr(null); }).catch((e) => setErr(String(e.message ?? e))), []);
  useEffect(() => { load(); const h = setInterval(load, 3000); return () => clearInterval(h); }, [load]);
  useEffect(() => { localStorage.setItem("coordinator", who); }, [who]);

  async function act(kind: "claim" | "resolve", id: string) {
    if (!who.trim()) { setErr("Enter your name first."); return; }
    try { await (kind === "claim" ? api.claim : api.resolve)(id, { coordinator: who.trim() }); load(); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  const c = queue.find((x) => x.id === sel);

  return (
    <div className="staff">
      <h1>Coordinator queue</h1>
      <label className="who">Your name <input value={who} onChange={(e) => setWho(e.target.value)} /></label>
      {err && <p className="error">{err}</p>}
      <div className="staff-grid">
        <table>
          <thead><tr><th>Person</th><th>Status</th><th>Lost ₹</th><th>Unanswered</th><th>Updated</th><th /></tr></thead>
          <tbody>
            {queue.length === 0 && <tr><td colSpan={6} className="muted">No cases waiting.</td></tr>}
            {queue.map((q) => (
              <tr key={q.id} className={q.id === sel ? "sel" : ""} onClick={() => setSel(q.id)}>
                <td>{q.person_name}</td>
                <td><span className={`pill pill-${q.status}`}>{q.status}</span>{q.coordinator ? ` ${q.coordinator}` : ""}</td>
                <td>{q.amount_lost_inr?.toLocaleString("en-IN") ?? "–"}</td>
                <td>{q.unanswered_checkins}</td>
                <td>{new Date(q.updated_at).toLocaleTimeString()}</td>
                <td className="row-actions">
                  {q.status === "escalated" && <button onClick={(e) => { e.stopPropagation(); act("claim", q.id); }}>Claim</button>}
                  <button onClick={(e) => { e.stopPropagation(); act("resolve", q.id); }}>Resolve</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {c && (
          <aside className="detail">
            <h2>{c.person_name} <small className="muted">{c.language}</small></h2>
            <p>{c.description}</p>
            <dl>
              <dt>Telegram</dt><dd>{c.telegram_chat_id ?? "–"}</dd>
              <dt>Trusted contact</dt><dd>{c.trusted_contact_name ?? "–"} {c.trusted_contact_telegram_chat_id ?? ""}</dd>
              <dt>Check-ins sent</dt><dd>{c.checkins_sent}</dd>
              <dt>Workflow</dt><dd>{c.workflow_id ?? "–"}</dd>
            </dl>
            <h3>Steps</h3>
            <ul>{c.steps.map((s) => <li key={s.id}>{s.done ? "✅" : "⬜"} {s.title}</li>)}</ul>
            <h3>Timeline</h3>
            <ul>{c.timeline.map((e, i) => <li key={i}><small className="muted">{new Date(e.at).toLocaleTimeString()}</small> {e.message}</li>)}</ul>
            <Link to={`/case/${c.id}`}>Open person's view</Link>
          </aside>
        )}
      </div>
    </div>
  );
}
