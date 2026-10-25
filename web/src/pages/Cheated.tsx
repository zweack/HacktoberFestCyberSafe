import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { BackHome } from "../components";
import { useI18n } from "../i18n";

export default function Cheated() {
  const { t, lang } = useI18n();
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", what: "", amount: "", tg: "", fam: "", famTg: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => {
    const value = e.target.value;
    setF((prev) => ({ ...prev, [k]: value }));
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      let analysis = null;
      try { analysis = await api.analyze({ text: f.what, situation: "victim", language: lang }); } catch { /* case still opens */ }
      const c = await api.createCase({
        person_name: f.name.trim(), language: lang, situation: "victim", description: f.what.trim(),
        amount_lost_inr: f.amount ? Number(f.amount) : null,
        telegram_chat_id: f.tg.trim() || null,
        trusted_contact_name: f.fam.trim() || null,
        trusted_contact_telegram_chat_id: f.famTg.trim() || null,
        analysis,
      });
      nav(`/case/${c.id}`);
    } catch { setErr(t.tryAgain); setBusy(false); }
  }

  return (
    <>
      <BackHome />
      <h1>{t.cheatedTitle}</h1>
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
        <label>{t.yourName}<input required value={f.name} onChange={set("name")} autoComplete="name" /></label>
        <label>{t.whatHappened}<textarea required rows={4} value={f.what} onChange={set("what")} /></label>
        <label>{t.amountLost}<input inputMode="decimal" type="number" min="0" value={f.amount} onChange={set("amount")} /></label>
        <label>{t.telegramId}<input inputMode="numeric" value={f.tg} onChange={set("tg")} /></label>
        <p className="hint">{t.telegramHow}</p>
        <label>{t.familyName}<input value={f.fam} onChange={set("fam")} /></label>
        <label>{t.familyId}<input inputMode="numeric" value={f.famTg} onChange={set("famTg")} /></label>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="btn btn-primary" disabled={busy}>{busy ? t.starting : t.startFollow}</button>
      </form>
    </>
  );
}
