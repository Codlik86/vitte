import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { PersonaListItem } from "../api/types";
import { fetchPersonas } from "../api/client";

export function CharactersList() {
  const navigate = useNavigate();
  const [items, setItems] = useState<PersonaListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setError(null);
      setLoading(true);
      const data = await fetchPersonas();
      setItems(data.items);
    } catch (e: any) {
      setError(e.message ?? "Не удалось загрузить персонажей");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-xl mx-auto px-4 py-6 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold">Выбери персонажа</h1>
          <Link
            to="/characters/custom"
            className="text-xs px-3 py-1.5 rounded-2xl bg-white text-slate-950"
          >
            Свой герой
          </Link>
        </div>

        {loading && <p className="text-sm text-white/60">Загружаем...</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}

        <div className="space-y-3">
          {items.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => navigate(`/characters/${p.id}`)}
              className="w-full text-left rounded-3xl border border-white/10 bg-white/5 px-4 py-3 hover:border-white/20 transition"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base font-semibold text-white">{p.name}</h2>
                  </div>
                  {p.short_description && (
                    <p className="text-sm text-white/60">{p.short_description}</p>
                  )}
                </div>
                {p.is_selected && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-400/10 text-emerald-300">
                    выбрано
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
