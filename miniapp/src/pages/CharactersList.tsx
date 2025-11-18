import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Persona } from "../api/types";
import { fetchPersonas } from "../api/client";

export function CharactersList() {
  const [items, setItems] = useState<Persona[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchPersonas();
        setItems(data.items);
      } catch (e: any) {
        setError(e.message ?? "Ошибка загрузки");
      } finally {
        setLoading(false);
      }
    };
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
            <Link
              key={p.id}
              to={`/characters/${p.id}`}
              className="block rounded-3xl border border-white/10 bg-white/5 px-4 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold">{p.name}</h2>
                    <span className="text-xs text-white/50">{p.short_title}</span>
                  </div>
                  <p className="mt-1 text-xs text-white/60">
                    {p.description_short}
                  </p>
                </div>
                {p.is_selected && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-400/10 text-emerald-300">
                    выбрано
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
