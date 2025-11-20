import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createCustomPersona, selectPersonaAndGreet } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { tg } from "../lib/telegram";

export function CharacterCustom() {
  const navigate = useNavigate();
  const { data: accessStatus } = useAccessStatus();
  const [name, setName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [vibe, setVibe] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasSubscription = Boolean(accessStatus?.has_subscription);
  const headerStats = {
    gems: 0,
    usedMessages: accessStatus?.free_messages_used ?? null,
    limitMessages: accessStatus?.free_messages_limit ?? null,
    hasUnlimited: hasSubscription,
    isPremium: hasSubscription,
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setBusy(true);
      const created = await createCustomPersona({
        name,
        short_description: shortDescription,
        vibe,
      });
      await selectPersonaAndGreet({
        personaId: created.id,
        extraDescription: vibe || shortDescription,
      });
      if (tg?.close) {
        tg.close();
      } else {
        navigate("/");
      }
    } catch (e: any) {
      setError(e.message ?? "Не удалось создать персонажа");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto w-full max-w-screen-sm px-4 pb-12 pt-6 space-y-6">
        <PageHeader
          title="Свой персонаж"
          showBack
          onBack={() => navigate(-1)}
          stats={headerStats}
        />

        <section className="rounded-4xl border border-white/5 bg-card-elevated/80 p-6 shadow-card">
          <div className="space-y-3">
            <h1 className="text-3xl font-semibold text-white">Создай меня</h1>
            <p className="text-base leading-relaxed text-white/70">
              Придумай собеседника под любое желание: реального или вымышленного, популярного
              артиста или близкого человека, старого друга или незнакомца, с которым хочется
              поделиться чем-то важным или обсудить любую тему. Расскажи, каким он должен быть, и
              Vitte подстроится под выбранный образ.
            </p>
          </div>

          {!hasSubscription ? (
            <div className="mt-6 space-y-4 rounded-3xl border border-white/10 bg-card-dark/60 p-5 text-center text-sm text-white/80">
              <p>Создание своего персонажа доступно в подписке Premium.</p>
              <Link
                to="/paywall"
                className="inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-3 text-base font-semibold text-white shadow-card"
              >
                Оформить подписку
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-6 space-y-6">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-white/80">
                Имя персонажа
              </span>
              <input
                className="w-full rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none transition focus:border-white/40 placeholder:text-sm placeholder:text-white/40"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Например, Серафина"
                required
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-white/80">
                Короткое описание / вайб
              </span>
              <input
                className="w-full rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none transition focus:border-white/40 placeholder:text-sm placeholder:text-white/40"
                value={shortDescription}
                onChange={(e) => setShortDescription(e.target.value)}
                placeholder="Например, дерзкая и заботливая подруга"
                required
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-white/80">
                Доп. вайб (необязательно)
              </span>
              <textarea
                className="w-full min-h-[120px] rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none transition focus:border-white/40 placeholder:text-sm placeholder:text-white/40"
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
          )}
        </section>
      </div>
    </div>
  );
}
