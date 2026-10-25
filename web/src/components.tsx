import { Link } from "react-router-dom";
import type { AnalyzeResponse, Contact, Verdict } from "./api/types";
import { useI18n } from "./i18n";
import { useSpeech } from "./speech";

export function TrafficLight({ verdict }: { verdict: Verdict }) {
  return (
    <div className="light" aria-hidden="true">
      {(["scam", "suspicious", "safe"] as Verdict[]).map((v) => (
        <span key={v} className={`lamp lamp-${v} ${v === verdict ? "on" : ""}`} />
      ))}
    </div>
  );
}

export function VerdictBadge({ verdict }: { verdict?: Verdict | null }) {
  const { t } = useI18n();
  if (!verdict) return <span className="badge badge-none">{t.notChecked}</span>;
  return <span className={`badge badge-${verdict}`}>{t[`verdict_${verdict}`]}</span>;
}

export function ContactCard({ c }: { c: Contact }) {
  const { lang, t } = useI18n();
  const name = (lang === "hi" && c.name_hi) || c.name;
  const desc = (lang === "hi" && c.description_hi) || c.description;
  return (
    <li className="contact">
      <div className="contact-name">{name}</div>
      <p>{desc}</p>
      <div className="contact-actions">
        {c.phone && <a className="btn btn-call" href={`tel:${c.phone}`}>📞 {t.callBtn} {c.phone}</a>}
        {c.url && <a className="btn btn-quiet" href={c.url} target="_blank" rel="noreferrer">{t.open}</a>}
      </div>
    </li>
  );
}

export function ReadAloud({ text }: { text: string }) {
  const { lang, t } = useI18n();
  const s = useSpeech();
  if (!s.supported) return null;
  return s.speaking
    ? <button className="btn btn-quiet" onClick={s.stop}>{t.stopReading}</button>
    : <button className="btn btn-quiet" onClick={() => s.speak(text, lang)}>{t.readAloud}</button>;
}

export function ResultCard({ r }: { r: AnalyzeResponse }) {
  const { t } = useI18n();
  const spoken = [r.headline, r.explanation, ...r.steps.map((s) => `${s.title}. ${s.detail}`)].join(" ");
  return (
    <article className={`result result-${r.verdict}`}>
      <header className="result-head">
        <TrafficLight verdict={r.verdict} />
        <div>
          <div className={`verdict-word verdict-${r.verdict}`}>{t[`verdict_${r.verdict}`]}</div>
          <h2 className="headline">{r.headline}</h2>
        </div>
      </header>
      <p className="explain">{r.explanation}</p>
      <ReadAloud text={spoken} />
      {!r.ai_used && (
        <p className="note">{t.aiUnavailable}{r.ai_error ? `: ${r.ai_error}` : "."}</p>
      )}
      {r.steps.length > 0 && (
        <section>
          <h3>{t.whatToDo}</h3>
          <ol className="steps">
            {r.steps.map((s) => (
              <li key={s.id} className={s.urgent ? "urgent" : ""}>
                <strong>{s.title}</strong>
                <span>{s.detail}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
      {r.signals.length > 0 && (
        <section>
          <h3>{t.whyTitle}</h3>
          <ul className="signals">
            {r.signals.map((s) => (
              <li key={s.id}>
                {s.label}
                {s.evidence && <q>{s.evidence}</q>}
              </li>
            ))}
          </ul>
        </section>
      )}
      {r.contacts.length > 0 && (
        <section>
          <h3>{t.whoToCall}</h3>
          <ul className="contacts">{r.contacts.map((c) => <ContactCard key={c.id} c={c} />)}</ul>
        </section>
      )}
    </article>
  );
}

export function BackHome() {
  const { t } = useI18n();
  return <Link className="back" to="/">‹ {t.home}</Link>;
}
