import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ChaosSettings, ReadyStatus } from "../api/types";

function ok(v: unknown) {
  if (v === true || v === "ok" || v === "ready") return true;
  if (v && typeof v === "object" && "ok" in v) return Boolean((v as { ok: unknown }).ok);
  return false;
}

export default function Ops() {
  const [ready, setReady] = useState<ReadyStatus | null>(null);
  const [chaos, setChaos] = useState<ChaosSettings | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => { api.ready().then(setReady).catch((e) => setErr(String(e.message ?? e))); }, []);
  useEffect(() => {
    load();
    api.getChaos().then(setChaos).catch((e) => setErr(String(e.message ?? e)));
    const h = setInterval(load, 5000);
    return () => clearInterval(h);
  }, [load]);

  async function save(next: ChaosSettings) {
    setChaos(next);
    try { setChaos(await api.putChaos(next)); setErr(null); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }

  return (
    <div className="staff">
      <h1>Ops status</h1>
      {err && <p className="error">{err}</p>}
      <p>Overall: <span className={`pill pill-${ready?.status === "ready" ? "sent" : "failed"}`}>{ready?.status ?? "…"}</span></p>
      <div className="tiles">
        {ready && Object.entries(ready.checks).map(([k, v]) => (
          <div key={k} className={`tile ${ok(v) ? "tile-ok" : "tile-bad"}`}>
            <strong>{k}</strong>
            <small>{typeof v === "object" ? JSON.stringify(v) : String(v)}</small>
          </div>
        ))}
      </div>
      <h2>Chaos switches</h2>
      {chaos && (
        <div className="chaos">
          <label>Telegram failure rate: {Math.round(chaos.telegram_failure_rate * 100)}%
            <input type="range" min={0} max={1} step={0.05} value={chaos.telegram_failure_rate}
              onChange={(e) => setChaos({ ...chaos, telegram_failure_rate: Number(e.target.value) })}
              onPointerUp={() => save(chaos)} onKeyUp={() => save(chaos)} />
          </label>
          <label className="row"><input type="checkbox" checked={chaos.llm_down} onChange={(e) => save({ ...chaos, llm_down: e.target.checked })} /> LLM down</label>
          <label>Slow analyze (ms)
            <input type="number" min={0} max={60000} step={500} value={chaos.slow_analyze_ms}
              onChange={(e) => setChaos({ ...chaos, slow_analyze_ms: Number(e.target.value) })} onBlur={() => save(chaos)} />
          </label>
        </div>
      )}
      <p><a href="http://localhost:8233" target="_blank" rel="noreferrer">Open Temporal UI (localhost:8233)</a> · <a href="/metrics" target="_blank" rel="noreferrer">/metrics</a></p>
    </div>
  );
}
