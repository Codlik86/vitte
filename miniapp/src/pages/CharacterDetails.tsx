import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { PersonaDetails } from "../api/types";
import { selectPersona, fetchPersona } from "../api/client";
import { MessageLimitChip } from "../components/MessageLimitChip";

export function CharacterDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [persona, setPersona] = useState<PersonaDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const load = async () => {
      if (!id) return;
      try {
        const data = await fetchPersona(Number(id));
        setPersona(data);
      } catch (e: any) {
        setError(e.message ?? "Ошибка загрузки");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const handleSelect = async () => {
    if (!persona) return;
    try {
      setBusy(true);
      await selectPersona(persona.id);
      navigate("/");
    } catch (e: any) {
      setError(e.message ?? "Не удалось выбрать персонажа");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto flex min-h-dvh w-full max-w-screen-sm flex-col px-4 pb-12 pt-6">
        <button
          className="text-xs text-text-muted transition hover:text-white/70"
          onClick={() => navigate(-1)}
        >
          ← Назад
        </button>

        <MessageLimitChip className="mt-4" />

        {loading ? (
          <div className="mt-6 space-y-4 rounded-4xl border border-white/5 bg-card-elevated/60 p-6 shadow-card animate-pulse">
            <div className="aspect-square w-full rounded-3xl bg-white/5" />
            <div className="h-8 w-3/4 rounded-full bg-white/10" />
            <div className="h-4 w-full rounded-full bg-white/5" />
            <div className="h-4 w-5/6 rounded-full bg-white/5" />
          </div>
        ) : error || !persona ? (
          <div className="mt-6 rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error ?? "Персонаж не найден"}
          </div>
        ) : (
          <section className="mt-6 flex flex-1 flex-col space-y-6 rounded-4xl border border-white/5 bg-card-elevated/80 p-6 shadow-card">
            <div className="w-full overflow-hidden rounded-3xl bg-gradient-to-br from-[#2C0D3E] via-[#5D267C] to-[#F05BB7]">
              <div className="relative aspect-square w-full">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.4),_transparent_55%)] opacity-70" />
                <div className="absolute inset-10 rounded-full bg-white/20 blur-3xl" />
              </div>
            </div>

            <div>
              <h1 className="text-4xl font-semibold tracking-tight">
                {persona.name}
              </h1>
              {persona.short_description && (
                <p className="mt-3 text-base text-white/70">
                  {persona.short_description}
                </p>
              )}
            </div>

            {persona.long_description && (
              <div className="space-y-2">
                <p className="text-[11px] uppercase tracking-[0.4em] text-text-muted">
                  Вайб
                </p>
                <p className="text-sm leading-relaxed text-white/80">
                  {persona.long_description}
                </p>
              </div>
            )}

            <div className="mt-auto pt-2">
              <button
                className="w-full rounded-full bg-white px-4 py-4 text-base font-semibold text-bg-dark transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
                onClick={handleSelect}
                disabled={busy || persona.is_selected}
              >
                {persona.is_selected
                  ? "Персонаж уже выбран"
                  : busy
                    ? "Выбираем..."
                    : "Выбрать персонажа"}
              </button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
