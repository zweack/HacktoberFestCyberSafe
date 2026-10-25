import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, recentCase } from "../api/client";
import type { FeedMessage } from "../api/types";
import { VerdictBadge } from "../components";
import { useI18n } from "../i18n";

export default function Home() {
  const { t } = useI18n();
  const [feed, setFeed] = useState<FeedMessage[] | null>(null);
  const [feedErr, setFeedErr] = useState(false);
  const planId = recentCase.get();
  useEffect(() => { api.feed().then(setFeed).catch(() => setFeedErr(true)); }, []);
  return (
    <>
      <h1 className="greet">{t.greeting}</h1>
      <p className="lede">{t.greetingSub}</p>
      <nav className="choices">
        <Link to="/check" className="choice choice-check">
          <span className="choice-icon" aria-hidden="true">✉️</span>
          <span><strong>{t.homeCheck}</strong><small>{t.homeCheckSub}</small></span>
        </Link>
        <Link to="/now" className="choice choice-now">
          <span className="choice-icon" aria-hidden="true">📞</span>
          <span><strong>{t.homeNow}</strong><small>{t.homeNowSub}</small></span>
        </Link>
        <Link to="/cheated" className="choice choice-cheated">
          <span className="choice-icon" aria-hidden="true">🆘</span>
          <span><strong>{t.homeCheated}</strong><small>{t.homeCheatedSub}</small></span>
        </Link>
      </nav>
      {planId && <Link to={`/case/${planId}`} className="btn btn-primary">📋 {t.openPlan}</Link>}
      <section className="inbox-preview">
        <h2>{t.myMessages}</h2>
        <p className="muted">{t.practiceLabel}</p>
        {feedErr && <p className="error">{t.feedFailed}</p>}
        {feed && feed.length === 0 && <p className="muted">{t.noMessages}</p>}
        <ul className="msgs">
          {feed?.slice(0, 3).map((m) => (
            <li key={m.id}>
              <Link to={`/inbox#${m.id}`} className="msg">
                <span className="msg-from">{m.sender}</span>
                <VerdictBadge verdict={m.analysis?.verdict} />
                <span className="msg-text">{m.text}</span>
              </Link>
            </li>
          ))}
        </ul>
        <Link to="/inbox" className="btn btn-quiet">{t.seeAll}</Link>
      </section>
    </>
  );
}
