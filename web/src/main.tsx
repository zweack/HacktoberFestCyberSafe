import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { useDemoMode } from "./api/client";
import { NotFound } from "./components";
import { I18nProvider, useI18n } from "./i18n";
import Home from "./pages/Home";
import Check from "./pages/Check";
import Now from "./pages/Now";
import Cheated from "./pages/Cheated";
import CasePage from "./pages/CasePage";
import Inbox from "./pages/Inbox";
import Coordinator from "./pages/Coordinator";
import Ops from "./pages/Ops";
import "./styles.css";

function Shell() {
  const { t, lang, setLang } = useI18n();
  const demo = useDemoMode();
  return (
    <>
      {demo && <div className="demo-banner" role="status">{t.demoBanner}</div>}
      <header className="top">
        <Link to="/" className="brand">🛡️ {t.appName}</Link>
        <button className="lang" onClick={() => setLang(lang === "en" ? "hi" : "en")}>{t.langToggle}</button>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/check" element={<Check />} />
          <Route path="/now" element={<Now />} />
          <Route path="/cheated" element={<Cheated />} />
          <Route path="/case/:id" element={<CasePage />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/coordinator" element={<Coordinator />} />
          <Route path="/ops" element={<Ops />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </I18nProvider>
  </StrictMode>,
);
