import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { PersonaListItem } from "../api/types";
import { fetchPersonas } from "../api/client";
import { MessageLimitChip } from "../components/MessageLimitChip";

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

  const renderCards = () => {
    if (loading) {
      return (
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="rounded-3xl border border-white/5 bg-card-elevated/50 p-3 animate-pulse space-y-3"
            >
              <div className="aspect-square w-full rounded-2xl bg-white/5" />
              <div className="h-4 w-3/4 rounded-full bg-white/10" />
              <div className="h-3 w-full rounded-full bg-white/5" />
            </div>
          ))}
        </div>
      );
    }

    if (error) {
      return (
        <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      );
    }

    if (!items.length) {
      return (
        <p className="text-sm text-text-muted">
          Персонажи пока не найдены. Попробуй обновить позже.
        </p>
      );
    }

    return (
      <div className="grid grid-cols-2 gap-4">
        {items.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => navigate(`/characters/${p.id}`)}
            className="group relative flex flex-col rounded-3xl border border-white/5 bg-card-elevated/70 p-3 text-left transition hover:border-white/20 hover:bg-card-elevated/90 active:scale-[0.98]"
          >
            <div className="relative">
              <div className="aspect-square w-full rounded-2xl bg-gradient-to-br from-[#35164F] via-[#60317A] to-[#E24CBD] p-4">
                <div className="h-full w-full rounded-2xl bg-white/10 blur-3xl" />
              </div>
              {p.is_selected && (
                <span className="absolute right-2 top-2 rounded-full bg-emerald-500/90 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white shadow-card">
                  выбрано
                </span>
              )}
            </div>
            <div className="mt-3 space-y-1">
              <h2 className="text-base font-semibold text-white">{p.name}</h2>
              {p.short_description && (
                <p className="text-xs text-white/70 line-clamp-2">
                  {p.short_description}
                </p>
              )}
            </div>
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto w-full max-w-screen-sm px-4 pb-12 pt-6 space-y-6">
        <header className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.3em] text-text-muted">
              Галерея персонажей
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              Выбери персонажа
            </h1>
          </div>
          <Link
            to="/characters/custom"
            className="rounded-full border border-white/10 bg-card-elevated/80 px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-accent hover:text-white"
          >
            Свой герой
          </Link>
        </header>

        <MessageLimitChip className="pt-1" />

        {renderCards()}

        <Link
          to="/paywall"
          className="inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-4 text-base font-semibold text-white shadow-card active:scale-[0.99]"
        >
          Перейти к подписке
        </Link>
      </div>
    </div>
  );
}
