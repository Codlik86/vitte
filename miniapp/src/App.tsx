import { Routes, Route } from "react-router-dom";
import { Home } from "./pages/Home";
import { Paywall } from "./pages/Paywall";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/paywall" element={<Paywall />} />
    </Routes>
  );
}

export default App;
