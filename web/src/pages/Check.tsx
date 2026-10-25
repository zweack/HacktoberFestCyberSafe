import { useState } from "react";
import { api } from "../api/client";
import type { AnalyzeResponse, Channel } from "../api/types";
import { BackHome, errorText, ResultCard } from "../components";
import { useI18n } from "../i18n";

const CHANNELS: Channel[] = ["sms", "whatsapp", "email", "call"];

export default function Check() {
  const { t, lang } = useI18n();
  const [text, setText] = useState("");
  const [channel, setChannel] = useState<Channel>("sms");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  async function paste() {
    try { setText(await navigator.clipboard.readText()); setErr(null); }
    catch { setErr(t.pasteFailed); }
  }
  async function submit() {
    setBusy(true); setErr(null);
    try { setResult(await api.analyze({ text, channel, situation: "received", language: lang })); }
    catch (e) { setErr(errorText(e, t)); }
    finally { setBusy(false); }
  }

  if (result) {
    return (
      <>
        <BackHome />
        <ResultCard r={result} message={{ text, label: t.messageYouChecked }} />
        <button className="btn btn-primary" onClick={() => { setResult(null); setText(""); }}>{t.checkAnother}</button>
      </>
    );
  }
  return (
    <>
      <BackHome />
      <h1>{t.checkTitle}</h1>
      <p className="lede">{t.checkHint}</p>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={6} maxLength={10000} aria-label={t.checkTitle} />
      <button className="btn btn-quiet" onClick={paste}>📋 {t.paste}</button>
      <fieldset className="channels">
        <legend>{t.whereFrom}</legend>
        {CHANNELS.map((c) => (
          <label key={c} className={channel === c ? "chip on" : "chip"}>
            <input type="radio" name="channel" checked={channel === c} onChange={() => setChannel(c)} />
            {t[c]}
          </label>
        ))}
      </fieldset>
      {err && <p className="error" role="alert">{err}</p>}
      <button className="btn btn-primary" disabled={!text.trim() || busy} onClick={submit}>
        {busy ? t.checking : t.checkBtn}
      </button>
    </>
  );
}
