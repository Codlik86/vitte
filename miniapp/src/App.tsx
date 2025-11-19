import { Routes, Route, Link } from "react-router-dom";
import { Paywall } from "./pages/Paywall";
import { CharactersList } from "./pages/CharactersList";
import { CharacterDetails } from "./pages/CharacterDetails";
import { CharacterCustom } from "./pages/CharacterCustom";

function App() {
  return (
    <Routes>
      <Route path="/" element={<CharactersList />} />
      <Route path="/paywall" element={<Paywall />} />
      <Route path="/characters" element={<CharactersList />} />
      <Route path="/characters/:id" element={<CharacterDetails />} />
      <Route path="/characters/custom" element={<CharacterCustom />} />
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
  );
}

export default App;
