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
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto w-full max-w-screen-sm px-4 py-8 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-text-muted">
              Галерея персонажей
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              Выбери персонажа
            </h1>
          </div>
          <Link
            to="/characters/custom"
            className="rounded-full border border-white/10 bg-card-dark px-4 py-1 text-sm font-medium text-text-main transition hover:bg-accent hover:text-white"
          >
            Свой герой
          </Link>
        </div>

        {loading && <p className="text-sm text-text-muted">Загружаем...</p>}
        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="space-y-4">
          {items.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => navigate(`/characters/${p.id}`)}
              className="w-full text-left rounded-3xl bg-card-dark px-5 py-4 shadow-card transition-colors duration-150 hover:bg-card-elevated flex items-start justify-between gap-4"
            >
              <div className="space-y-2">
                {p.is_default && (
                  <span className="text-[11px] uppercase tracking-wide text-text-muted bg-chip-muted px-3 py-1 rounded-full inline-block">
                    По умолчанию
                  </span>
                )}
                <div>
                  <h2 className="text-lg font-semibold text-text-main">
                    {p.name}
                  </h2>
                  {p.short_description && (
                    <p className="mt-1 text-sm text-text-muted line-clamp-2">
                      {p.short_description}
                    </p>
                  )}
                </div>
              </div>
              {p.is_selected && (
                <span className="rounded-full bg-chip-selected/90 text-[11px] px-3 py-1 text-emerald-50">
                  выбрано
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
