import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, subscribeFeed } from "../api/client";
import type { FeedMessage } from "../api/types";
import { BackHome, ResultCard, VerdictBadge } from "../components";
import { useI18n } from "../i18n";

export default function Inbox() {
  const { t } = useI18n();
  const loc = useLocation();
  const [feed, setFeed] = useState<FeedMessage[]>([]);
  const [open, setOpen] = useState<string | null>(loc.hash.slice(1) || null);

  useEffect(() => {
    api.feed().then(setFeed).catch(() => {});
    return subscribeFeed((m) => setFeed((f) => (f.some((x) => x.id === m.id) ? f : [m, ...f])));
  }, []);

  async function next() {
    const m = await api.feedNext();
    setFeed((f) => (f.some((x) => x.id === m.id) ? f : [m, ...f]));
  }
  async function reset() { await api.feedReset(); setFeed([]); setOpen(null); }

  const sel = feed.find((m) => m.id === open);
  if (sel) {
    return (
      <>
        <button className="back" onClick={() => setOpen(null)}>‹ {t.inboxTitle}</button>
        <div className="bubble"><div className="msg-from">{sel.sender}</div>{sel.subject && <strong>{sel.subject}</strong>}<p>{sel.text}</p></div>
        {sel.analysis ? <ResultCard r={sel.analysis} /> : <p className="muted">{t.notChecked}</p>}
      </>
    );
  }
  return (
    <>
      <BackHome />
      <h1>{t.inboxTitle}</h1>
      <p className="lede">{t.inboxHint}</p>
      {feed.length === 0 && <p className="muted">{t.noMessages}</p>}
      <ul className="msgs">
        {feed.map((m) => (
          <li key={m.id}>
            <button className="msg" onClick={() => setOpen(m.id)}>
              <span className="msg-from">{m.sender} <small className="muted">{t[m.channel]}</small></span>
              <VerdictBadge verdict={m.analysis?.verdict} />
              <span className="msg-text">{m.subject ? `${m.subject}: ` : ""}{m.text}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="demo-controls">
        <button className="btn-tiny" onClick={next}>{t.demoNext}</button>
        <button className="btn-tiny" onClick={reset}>{t.demoReset}</button>
      </div>
    </>
  );
}
