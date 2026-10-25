import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, mergeFeed, subscribeFeed } from "../api/client";
import type { FeedMessage } from "../api/types";
import { BackHome, FocusHeading, ResultCard, VerdictBadge } from "../components";
import { useI18n } from "../i18n";

export default function Inbox() {
  const { t } = useI18n();
  const loc = useLocation();
  const [feed, setFeed] = useState<FeedMessage[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<string | null>(loc.hash.slice(1) || null);

  // Snapshots are merged by id, so a message that arrived on the stream first is never lost.
  const refresh = useCallback(() => api.feed()
    .then((snap) => { setFeed((f) => mergeFeed(f, snap)); setErr(false); })
    .catch(() => setErr(true))
    .finally(() => setLoaded(true)), []);

  useEffect(() => {
    refresh();
    // Reload the snapshot on every (re)connect: the stream does not replay what we missed.
    return subscribeFeed((m) => setFeed((f) => mergeFeed(f, [m])), refresh, () => setErr(true));
  }, [refresh]);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    try { await fn(); setErr(false); } catch { setErr(true); } finally { setBusy(false); }
  }
  const next = () => run(async () => { const m = await api.feedNext(); setFeed((f) => mergeFeed(f, [m])); });
  const reset = () => run(async () => { await api.feedReset(); setFeed([]); setOpen(null); });

  const sel = feed.find((m) => m.id === open);
  if (sel) {
    return (
      <>
        <button className="back" onClick={() => setOpen(null)}>‹ {t.inboxTitle}</button>
        <p className="note">{t.practiceLabel}</p>
        <div className="bubble"><div className="msg-from">{sel.sender}</div>{sel.subject && <strong>{sel.subject}</strong>}<p>{sel.text}</p></div>
        {sel.analysis ? <ResultCard r={sel.analysis} /> : <p className="muted">{t.notChecked}</p>}
      </>
    );
  }
  return (
    <>
      <BackHome />
      <FocusHeading>{t.inboxTitle}</FocusHeading>
      <p className="lede">{t.inboxHint}</p>
      {err && <p className="error" role="alert">{t.feedFailed} <button className="btn-tiny" onClick={refresh}>{t.retry}</button></p>}
      {loaded && !err && feed.length === 0 && <p className="muted">{t.noMessages}</p>}
      {!loaded && <p className="muted">{t.loading}</p>}
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
        <button className="btn-tiny" disabled={busy} onClick={next}>{t.demoNext}</button>
        <button className="btn-tiny" disabled={busy} onClick={reset}>{t.demoReset}</button>
      </div>
    </>
  );
}
