import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError, recentCase } from "../api/client";
import type { AnalyzeResponse } from "../api/types";
import { BackHome, ReadAloud } from "../components";
import { useI18n } from "../i18n";

export default function Cheated() {
  const { t, lang } = useI18n();
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", what: "", amount: "", tg: "", fam: "", famTg: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  // One key per form submission attempt: a retry after a network error returns the same case.
  const [requestKey] = useState(() => crypto.randomUUID());
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => {
    const value = e.target.value;
    setF((prev) => ({ ...prev, [k]: value }));
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!f.name.trim() || !f.what.trim()) { setErr(t.formIncomplete); return; }
    setBusy(true); setErr(null);
    try {
      // Analysis is optional: wait at most 8 s, then open the case with the standard plan.
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 8000);
      let analysis: AnalyzeResponse | null = null;
      try { analysis = await api.analyze({ text: f.what, situation: "victim", language: lang }, ctrl.signal); }
      catch { /* case still opens */ }
      finally { clearTimeout(timer); }
      const c = await api.createCase({
        person_name: f.name.trim(), language: lang, situation: "victim", description: f.what.trim(),
        amount_lost_inr: f.amount ? Number(f.amount) : null,
        telegram_chat_id: f.tg.trim() || null,
        trusted_contact_name: f.fam.trim() || null,
        trusted_contact_telegram_chat_id: f.famTg.trim() || null,
        analysis,
      }, requestKey);
      recentCase.set(c.id);
      nav(`/case/${c.id}`);
    } catch (e) {
      const d = e instanceof ApiError ? e.detail : null;
      if (d && typeof d === "object" && "case_id" in d) setSavedId(String((d as { case_id: unknown }).case_id));
      setErr(e instanceof ApiError && e.offline ? t.offline : t.tryAgain);
      setBusy(false);
    }
  }

  return (
    <>
      <BackHome />
      <h1>{t.cheatedTitle}</h1>
      <ReadAloud text={[t.cheatedTitle, t.call1930, t.call1930Sub, t.blockBank, t.blockBankSub, t.reportOnline].join(" ")} />
      <ol className="urgent-list">
        <li>
          <a className="btn btn-stop big" href="tel:1930">📞 {t.call1930}</a>
          <p>{t.call1930Sub}</p>
        </li>
        <li><strong>{t.blockBank}</strong><p>{t.blockBankSub}</p></li>
        <li><a className="btn btn-quiet" href="https://cybercrime.gov.in/" target="_blank" rel="noreferrer">{t.reportOnline}</a></li>
      </ol>
      <form className="form" onSubmit={submit}>
        <h2>{t.followTitle}</h2>
        <p className="lede">{t.followSub}</p>
        <label>{t.yourName}<input required maxLength={120} value={f.name} onChange={set("name")} autoComplete="name" /></label>
        <label>{t.whatHappened}<textarea required maxLength={10000} rows={4} value={f.what} onChange={set("what")} /></label>
        <label>{t.amountLost}<input inputMode="decimal" type="number" min="0" step="0.01" value={f.amount} onChange={set("amount")} /></label>
        <label>{t.telegramId}<input inputMode="numeric" value={f.tg} onChange={set("tg")} /></label>
        <p className="hint">{t.telegramHow}</p>
        <label>{t.familyName}<input value={f.fam} onChange={set("fam")} /></label>
        <label>{t.familyId}<input inputMode="numeric" value={f.famTg} onChange={set("famTg")} /></label>
        {err && <p className="error" role="alert">{err}</p>}
        {savedId && <p>{t.savedCase} <Link to={`/case/${savedId}`}>{t.openPlan}</Link></p>}
        <button className="btn btn-primary" disabled={busy}>{busy ? t.starting : t.startFollow}</button>
      </form>
    </>
  );
}
