import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCustomPersona } from "../api/client";

export function CharacterCustom() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [shortTitle, setShortTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setBusy(true);
      await createCustomPersona(name, shortTitle, description);
      navigate("/characters");
    } catch (e: any) {
      setError(e.message ?? "Не удалось создать персонажа");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-xl mx-auto px-4 py-6">
        <button
          className="text-xs text-white/60 mb-4"
          onClick={() => navigate(-1)}
        >
          ← Назад
        </button>

        <h1 className="text-2xl font-semibold mb-3">Свой персонаж</h1>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs text-white/60 mb-1">
              Имя персонажа
            </label>
            <input
              className="w-full rounded-2xl bg-white/5 border border-white/10 px-3 py-2 text-sm outline-none"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs text-white/60 mb-1">
              Короткое описание / вайб
            </label>
            <input
              className="w-full rounded-2xl bg-white/5 border border-white/10 px-3 py-2 text-sm outline-none"
              value={shortTitle}
              onChange={(e) => setShortTitle(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs text-white/60 mb-1">
              Пара фраз о том, какой он/она
            </label>
            <textarea
              className="w-full rounded-2xl bg-white/5 border border-white/10 px-3 py-2 text-sm outline-none min-h-[80px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </div>

          {error && <p className="text-xs text-red-300">{error}</p>}

          <button
            type="submit"
            className="w-full mt-2 px-4 py-2 rounded-2xl bg-white text-slate-950 text-sm font-medium disabled:opacity-60"
            disabled={busy}
          >
            Создать и выбрать
          </button>
        </form>
      </div>
    </div>
  );
}
