import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCustomPersona } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";

export function CharacterCustom() {
  const navigate = useNavigate();
  const { data: accessStatus } = useAccessStatus();
  const [name, setName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [vibe, setVibe] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const headerStats = {
    gems: 0,
    usedMessages: accessStatus?.free_messages_used,
    limitMessages: accessStatus?.free_messages_limit,
    hasUnlimited: accessStatus?.has_access,
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setBusy(true);
      await createCustomPersona({
        name,
        short_description: shortDescription,
        vibe,
      });
      navigate("/");
    } catch (e: any) {
      setError(e.message ?? "Не удалось создать персонажа");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto w-full max-w-screen-sm px-4 pb-12 pt-6">
        <PageHeader
          title="Свой персонаж"
          showBack
          onBack={() => navigate(-1)}
          stats={headerStats}
        />

        <section className="rounded-4xl border border-white/5 bg-card-elevated/80 p-6 shadow-card">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold">Свой персонаж</h1>
            <p className="text-sm text-text-muted">
              Создай своего героя: задай имя, вайб и пару деталей, чтобы Vitte
              отвечала в нужном стиле.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.3em] text-text-muted">
                Имя персонажа
              </span>
              <input
                className="w-full rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none focus:border-white/40"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Например, Серафина"
                required
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.3em] text-text-muted">
                Короткое описание / вайб
              </span>
              <input
                className="w-full rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none focus:border-white/40"
                value={shortDescription}
                onChange={(e) => setShortDescription(e.target.value)}
                placeholder="Например, дерзкая и заботливая подруга"
                required
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs uppercase tracking-[0.3em] text-text-muted">
                Доп. vibe (необязательно)
              </span>
              <textarea
                className="w-full min-h-[120px] rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none focus:border-white/40"
                value={vibe}
                onChange={(e) => setVibe(e.target.value)}
                placeholder="Любимые темы, скорость переписки, триггеры"
              />
            </label>

            {error && (
              <p className="text-sm text-red-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              className="w-full rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-4 text-base font-semibold text-white shadow-card transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={busy}
            >
              {busy ? "Создаём..." : "Создать и выбрать"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
