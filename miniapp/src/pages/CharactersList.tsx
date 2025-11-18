import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Persona } from "../api/types";
import { fetchPersonas, selectPersona } from "../api/client";

export function CharactersList() {
  const [items, setItems] = useState<Persona[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

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

  const handleSelect = async (personaId: number) => {
    try {
      setBusyId(personaId);
      await selectPersona(personaId);
      await load();
    } catch (e: any) {
      setError(e.message ?? "Не удалось выбрать персонажа");
    } finally {
      setBusyId(null);
    }
  };

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
              onClick={() => handleSelect(p.id)}
              className="w-full text-left rounded-3xl border border-white/10 bg-white/5 px-4 py-3 hover:border-white/20 transition"
              disabled={busyId === p.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base font-semibold">{p.name}</h2>
                    <div className="flex items-center gap-1 text-[11px] text-white/60">
                      {p.is_default && (
                        <span className="px-2 py-0.5 rounded-full bg-white/10">
                          По умолчанию
                        </span>
                      )}
                      {p.is_custom && (
                        <span className="px-2 py-0.5 rounded-full bg-amber-400/20 text-amber-200">
                          Мой персонаж
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-white/70">{p.short_description}</p>
                </div>
                {p.is_active && (
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
