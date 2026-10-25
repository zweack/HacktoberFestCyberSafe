import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ChaosSettings, ReadyStatus } from "../api/types";
import { StaffGate, staffError } from "../components";

// Matches backend/app/api/health.py. "warn" = works, but something optional is off.
function tone(key: string, v: unknown): "ok" | "warn" | "bad" {
  if (v === "ok" || v === "configured" || v === "enabled") return "ok";
  if (v === "not_configured" || (key === "staff_auth" && v === "disabled")) return "warn";
  return "bad";
}

export default function Ops() {
  const [ready, setReady] = useState<ReadyStatus | null>(null);
  const [saved, setSaved] = useState<ChaosSettings | null>(null); // what the server confirmed
  const [draft, setDraft] = useState<ChaosSettings | null>(null); // what the controls show
  const [state, setState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [err, setErr] = useState<string | null>(null);
  const seq = useRef(0);

  const load = useCallback(() => { api.ready().then(setReady).catch((e) => setErr(staffError(e))); }, []);
  useEffect(() => {
    load();
    api.getChaos().then((c) => { setSaved(c); setDraft(c); }).catch((e) => setErr(staffError(e)));
    const h = setInterval(load, 5000);
    return () => clearInterval(h);
  }, [load]);

  async function save(next: ChaosSettings) {
    if (!(next.slow_analyze_ms >= 0 && next.slow_analyze_ms <= 60000)) { setErr("Slow analyze must be 0–60000 ms."); return; }
    const mine = ++seq.current; // only the latest save may update the screen
    setDraft(next); setState("saving");
    try {
      const c = await api.putChaos(next);
      if (mine === seq.current) { setSaved(c); setDraft(c); setState("saved"); setErr(null); }
    } catch (e) {
      if (mine === seq.current) { setState("failed"); setErr(staffError(e)); setDraft(saved); }
    }
  }

  const overall = ready?.status === "ready" ? "sent" : ready?.status === "degraded" ? "pending" : "failed";
  return (
    <div className="staff" lang="en">
      <h1>Ops status</h1>
      <StaffGate>
        {err && <p className="error" role="alert">{err}</p>}
        <p>Overall: <span className={`pill pill-${overall}`}>{ready?.status ?? "…"}</span></p>
        {ready?.checks.worker === "no_pollers" && (
          <p className="error">No worker is polling the follow-up queue: check-ins and escalations are paused. Restart the worker.</p>
        )}
        <div className="tiles">
          {ready && Object.entries(ready.checks).map(([k, v]) => (
            <div key={k} className={`tile tile-${tone(k, v)}`}>
              <strong>{k}</strong>
              <small>{typeof v === "object" ? JSON.stringify(v) : String(v)}</small>
            </div>
          ))}
        </div>
        <h2>Chaos switches <small className="muted" role="status">{state === "idle" ? "" : state}</small></h2>
        {draft && (
          <div className="chaos">
            <label>Telegram failure rate: {Math.round(draft.telegram_failure_rate * 100)}%
              <input type="range" min={0} max={1} step={0.05} value={draft.telegram_failure_rate} disabled={state === "saving"}
                onChange={(e) => setDraft({ ...draft, telegram_failure_rate: Number(e.target.value) })}
                onPointerUp={() => save(draft)} onKeyUp={() => save(draft)} />
            </label>
            <label className="row"><input type="checkbox" checked={draft.llm_down} disabled={state === "saving"}
              onChange={(e) => save({ ...draft, llm_down: e.target.checked })} /> LLM down</label>
            <label>Slow analyze (ms)
              <input type="number" min={0} max={60000} step={500} value={draft.slow_analyze_ms} disabled={state === "saving"}
                onChange={(e) => setDraft({ ...draft, slow_analyze_ms: Number(e.target.value) })} onBlur={() => save(draft)} />
            </label>
          </div>
        )}
        <p><a href="http://localhost:8233" target="_blank" rel="noreferrer">Open Temporal UI (localhost:8233)</a> · <a href="/metrics" target="_blank" rel="noreferrer">/metrics</a></p>
      </StaffGate>
    </div>
  );
}
