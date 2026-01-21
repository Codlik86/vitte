import { useEffect } from "react";
import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { Paywall } from "./pages/Paywall";
import { CharactersList } from "./pages/CharactersList";
import { CharacterDetails } from "./pages/CharacterDetails";
import { CharacterCustom } from "./pages/CharacterCustom";
import { Store } from "./pages/Store";
import { Settings } from "./pages/Settings";
import { Chat } from "./pages/Chat";
import { Dialogs } from "./pages/Dialogs";
import { tg } from "./lib/telegram";
import { useTrackMiniAppOpen } from "./hooks/useTrackMiniAppOpen";

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  useTrackMiniAppOpen();

  useEffect(() => {
    tg?.expand?.();
  }, []);

  useEffect(() => {
    const telegram = tg;
    if (!telegram?.BackButton) return;

    const handleBack = () => navigate(-1);
    const backButton = telegram.BackButton;

    const normalizedPath = location.pathname.toLowerCase();
    const isGallery = normalizedPath === "/" || normalizedPath === "/characters";

    if (isGallery) {
      backButton.hide();
      return;
    }

    backButton.show();
    backButton.onClick(handleBack);

    return () => {
      backButton.offClick?.(handleBack);
    };
  }, [location.pathname, navigate]);

  return (
    <div className="safe-top">
      <Routes>
        <Route path="/" element={<CharactersList />} />
        <Route path="/paywall" element={<Paywall />} />
        <Route path="/characters" element={<CharactersList />} />
        <Route path="/characters/:id" element={<CharacterDetails />} />
        <Route path="/characters/custom" element={<CharacterCustom />} />
        <Route path="/store" element={<Store />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/chat/:dialogId?" element={<Chat />} />
        <Route path="/dialogs" element={<Dialogs />} />
        <Route
          path="*"
          element={
            <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
              <div className="text-center space-y-2">
                <p className="text-sm text-white/60">Страница не найдена</p>
                <Link
                  to="/"
                  className="inline-flex px-4 py-2 rounded-2xl bg-white text-slate-950 text-sm"
                >
                  На главную
                </Link>
              </div>
            </div>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
