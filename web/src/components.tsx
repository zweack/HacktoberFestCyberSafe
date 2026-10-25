import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ApiError, setStaffToken, useStaffToken } from "./api/client";
import type { AnalyzeResponse, Contact, Language, Verdict } from "./api/types";
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

/** Reads text aloud in the language the text is written in (not just the UI language). */
export function ReadAloud({ text, language }: { text: string; language?: Language }) {
  const { lang, t } = useI18n();
  const s = useSpeech();
  if (!s.supported) return null;
  return s.speaking
    ? <button className="btn btn-quiet" onClick={s.stop}>{t.stopReading}</button>
    : <button className="btn btn-quiet" onClick={() => s.speak(text, language ?? lang)}>{t.readAloud}</button>;
}

/** A heading that takes focus when it appears, so keyboard and screen-reader users land on the new content. */
export function FocusHeading({ level = 1, className, children }: { level?: 1 | 2; className?: string; children: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => { ref.current?.focus(); }, []);
  const Tag = level === 1 ? "h1" : "h2";
  return <Tag ref={ref} tabIndex={-1} className={className}>{children}</Tag>;
}

/** Short, localized text for a failed request. */
export function errorText(e: unknown, t: ReturnType<typeof useI18n>["t"]): string {
  if (e instanceof ApiError && e.offline) return t.offline;
  return t.tryAgain;
}

export function ResultCard({ r }: { r: AnalyzeResponse }) {
  const { t, lang } = useI18n();
  const contactLines = r.contacts.map((c) => [c.name, c.phone].filter(Boolean).join(" "));
  const spoken = [
    r.headline, r.explanation, !r.ai_used && r.ai_error ? r.ai_error : "",
    ...r.steps.map((s) => `${s.title}. ${s.detail}`), ...contactLines,
  ].filter(Boolean).join(" ");
  return (
    <article className={`result result-${r.verdict}`} lang={r.language}>
      <header className="result-head">
        <TrafficLight verdict={r.verdict} />
        <div>
          <div className={`verdict-word verdict-${r.verdict}`}>{t[`verdict_${r.verdict}`]}</div>
          <FocusHeading level={2} className="headline">{r.headline}</FocusHeading>
        </div>
      </header>
      {r.language !== lang && <p className="note" lang={lang}>{t[`contentIn_${r.language}`]}</p>}
      <p className="explain">{r.explanation}</p>
      <ReadAloud text={spoken} language={r.language} />
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

/** Coordinator and ops pages: ask once for the shared staff token (kept for this browser tab only). */
export function StaffGate({ children }: { children: ReactNode }) {
  const token = useStaffToken();
  const [draft, setDraft] = useState("");
  return (
    <>
      <form className="staff-token" onSubmit={(e) => { e.preventDefault(); setStaffToken(draft.trim()); setDraft(""); }}>
        {token
          ? <p>Staff token set for this tab. <button type="button" className="btn-tiny" onClick={() => setStaffToken("")}>Forget token</button></p>
          : <label>Staff token (ask the team lead; not needed if the server has none)
              <input type="password" autoComplete="off" value={draft} onChange={(e) => setDraft(e.target.value)} />
              <button className="btn-tiny">Save</button>
            </label>}
      </form>
      {children}
    </>
  );
}

/** Text for a staff request error: a 401 means the token is missing or wrong. */
export function staffError(e: unknown): string {
  if (e instanceof ApiError && e.status === 401) return "Staff token missing or wrong. Enter it above.";
  if (e instanceof ApiError && e.offline) return "Server not reachable.";
  return e instanceof Error ? e.message : String(e);
}

export function NotFound() {
  const { t } = useI18n();
  return (
    <>
      <FocusHeading>{t.notFoundTitle}</FocusHeading>
      <p>{t.notFoundText}</p>
      <a className="btn btn-stop" href="tel:1930">📞 {t.call1930}</a>
      <Link className="btn btn-primary" to="/">{t.home}</Link>
    </>
  );
}

export function BackHome() {
  const { t } = useI18n();
  return <Link className="back" to="/">‹ {t.home}</Link>;
}
