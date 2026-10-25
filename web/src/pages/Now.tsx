import { useState } from "react";
import { api } from "../api/client";
import type { AnalyzeResponse } from "../api/types";
import { BackHome, ReadAloud, ResultCard } from "../components";
import { useI18n } from "../i18n";

export default function Now() {
  const { t, lang } = useI18n();
  const [stage, setStage] = useState<"stop" | "describe">("stop");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  async function submit() {
    setBusy(true); setErr(null);
    try { setResult(await api.analyze({ text, channel: "call", situation: "in_progress", language: lang })); }
    catch { setErr(t.tryAgain); }
    finally { setBusy(false); }
  }

  if (stage === "stop") {
    return (
      <>
        <BackHome />
        <section className="stop" role="alert">
          <h1>{t.stopTitle}</h1>
          <ul>{t.stopLines.map((l) => <li key={l}>{l}</li>)}</ul>
        </section>
        <p className="lede">{t.stopCalm}</p>
        <ReadAloud text={[t.stopTitle, ...t.stopLines, t.stopCalm].join(" ")} />
        <button className="btn btn-primary" onClick={() => setStage("describe")}>{t.iHungUp}</button>
      </>
    );
  }
  if (result) return (<><BackHome /><ResultCard r={result} /></>);
  return (
    <>
      <BackHome />
      <h1>{t.describeTitle}</h1>
      <p className="lede">{t.describeHint}</p>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={5} aria-label={t.describeTitle} />
      {err && <p className="error" role="alert">{err}</p>}
      <button className="btn btn-primary" disabled={!text.trim() || busy} onClick={submit}>
        {busy ? t.checking : t.describeBtn}
      </button>
    </>
  );
}
