import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import type { PersonaDetails, StoryCard } from "../api/types";
import {
  fetchPersona,
  sendChatMessage,
  selectPersonaAndGreet,
} from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { tg } from "../lib/telegram";

const ATMOSPHERE_OPTIONS = [
  { id: "cozy_evening", label: "Уютный вечер" },
  { id: "support_after_day", label: "Поддержка" },
  { id: "light_flirt", label: "Лёгкий флирт" },
  { id: "serious_talk", label: "Серьёзный разговор" },
];

export function CharacterDetails() {
  const { id } = useParams();
  const location = useLocation();
  const locationState = (location.state as { name?: string } | null) ?? null;
  const fallbackTitle = locationState?.name ?? "Персонаж";
  const navigate = useNavigate();
  const { data: accessStatus } = useAccessStatus();
  const [persona, setPersona] = useState<PersonaDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState<string>(fallbackTitle);
  const [selectedAtmosphere, setSelectedAtmosphere] = useState<string | null>(null);
  const [deepMode, setDeepMode] = useState(false);
  const [storyInFlight, setStoryInFlight] = useState<string | null>(null);
  const [storyReply, setStoryReply] = useState<{ title: string; reply: string } | null>(null);
  const [storyError, setStoryError] = useState<string | null>(null);
  const [selectError, setSelectError] = useState<string | null>(null);

  useEffect(() => {
    setTitle(fallbackTitle);
  }, [fallbackTitle, id]);
  const hasSubscription = Boolean(accessStatus?.has_subscription);
  const headerStats = {
    gems: 0,
    usedMessages: accessStatus?.free_messages_used ?? null,
    limitMessages: accessStatus?.free_messages_limit ?? null,
    hasUnlimited: hasSubscription,
    isPremium: hasSubscription,
  };

  useEffect(() => {
    const load = async () => {
      if (!id) return;
      try {
        const data = await fetchPersona(Number(id));
        setPersona(data);
        setTitle(data.name);
        setSelectedAtmosphere(null);
        setStoryReply(null);
        setStoryError(null);
        setDeepMode(false);
        setStoryInFlight(null);
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
    const hasHistory = Boolean(persona.has_history);
    const hasChanges = Boolean(selectedAtmosphere);
    const selectedAtmosphereLabel = ATMOSPHERE_OPTIONS.find((opt) => opt.id === selectedAtmosphere)?.label;
    try {
      setBusy(true);
      setSelectError(null);
      await selectPersonaAndGreet({
        personaId: persona.id,
        atmosphere: selectedAtmosphere ?? undefined,
        settingsChanged: hasHistory && hasChanges,
        extraDescription: selectedAtmosphereLabel
          ? `Выбранная атмосфера: ${selectedAtmosphereLabel}`
          : undefined,
      });
      if (tg?.close) {
        tg.close();
      } else {
        navigate("/");
      }
    } catch (e: any) {
      setSelectError(e.message ?? "Не удалось выбрать персонажа");
    } finally {
      setBusy(false);
    }
  };

  const handleLaunchStory = async (card: StoryCard) => {
    if (!persona) return;
    setStoryError(null);
    setStoryInFlight(card.id);
    try {
      const mode = deepMode ? "deep" : "story";
      const res = await sendChatMessage({
        message: card.prompt,
        mode,
        story_id: card.id,
        atmosphere: selectedAtmosphere ?? card.atmosphere,
        persona_id: persona.id,
      });
      setStoryReply({ title: card.title, reply: res.reply });
    } catch (err: any) {
      setStoryError(err.message ?? "Не удалось запустить сцену");
    } finally {
      setStoryInFlight(null);
    }
  };

  const canUseDeepMode = hasSubscription;

  const storyCards = useMemo(() => persona?.story_cards ?? [], [persona]);
  const hasHistory = Boolean(persona?.has_history);
  const hasChanges = Boolean(selectedAtmosphere);
  const actionLabel = hasHistory
    ? hasChanges
      ? "Обновить и продолжить"
      : "Продолжить разговор"
    : "Начать разговор";

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto flex min-h-dvh w-full max-w-screen-sm flex-col px-4 pb-12 pt-6">
        <PageHeader
          title={title}
          showBack
          onBack={() => navigate(-1)}
          stats={headerStats}
        />

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

            <InfoBlock title="Легенда" text={persona.legend_full ?? persona.long_description} />
            <InfoBlock title="Эмоции и отношения" text={persona.emotions_full} />
            <TriggerBlock
              positive={persona.triggers_positive}
              negative={persona.triggers_negative}
            />

            <div className="rounded-3xl border border-white/10 bg-card-dark/40 p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-white">Глубокий режим</p>
                  <p className="text-xs text-white/60">
                    Более развёрнутые ответы и глубокая эмоциональная работа.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setDeepMode((prev) => !prev)}
                  disabled={!canUseDeepMode}
                  className={`inline-flex items-center rounded-full border px-3 py-1 text-sm ${
                    deepMode ? "border-pink-300 text-pink-100" : "border-white/20 text-white/70"
                  } disabled:opacity-40`}
                >
                  {deepMode ? "Включено" : "Выключено"}
                </button>
              </div>

              <div>
                <p className="text-sm font-semibold text-white">Атмосфера</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {ATMOSPHERE_OPTIONS.map((option) => {
                    const active = selectedAtmosphere === option.id;
                    return (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() =>
                          setSelectedAtmosphere((prev) =>
                            prev === option.id ? null : option.id
                          )
                        }
                        className={`rounded-full border px-3 py-1 text-xs transition ${
                          active
                            ? "border-pink-400/70 bg-white/10 text-white"
                            : "border-white/15 text-white/70"
                        }`}
                      >
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {storyCards && storyCards.length > 0 && (
              <div className="space-y-3">
                <p className="text-sm font-semibold text-white">Истории</p>
                <div className="space-y-3">
                  {storyCards.map((card) => (
                    <div
                      key={card.id}
                      className="rounded-3xl border border-white/10 bg-card-dark/30 p-4"
                    >
                      <div>
                        <p className="text-base font-semibold text-white">{card.title}</p>
                        <p className="text-sm text-white/70">{card.description}</p>
                      </div>
                      <button
                        type="button"
                        className="mt-3 inline-flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                        onClick={() => handleLaunchStory(card)}
                        disabled={Boolean(storyInFlight)}
                      >
                        {storyInFlight === card.id ? "Готовимся…" : "Попробовать"}
                      </button>
                    </div>
                  ))}
                </div>
                {storyError && (
                  <p className="rounded-2xl border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs text-red-200">
                    {storyError}
                  </p>
                )}
                {storyReply && (
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                    <p className="text-sm font-semibold text-white">{storyReply.title}</p>
                    <p className="mt-2 text-sm text-white/80 whitespace-pre-line">
                      {storyReply.reply}
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="pt-2">
              <button
                className="w-full rounded-full bg-white px-4 py-4 text-base font-semibold text-bg-dark transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
                onClick={handleSelect}
                disabled={busy}
              >
                {busy ? "Отправляем приветствие..." : actionLabel}
              </button>
              {selectError && (
                <p className="mt-2 rounded-2xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
                  {selectError}
                </p>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function InfoBlock({ title, text }: { title: string; text?: string | null }) {
  if (!text) return null;
  return (
    <div className="space-y-1">
      <p className="text-[11px] uppercase tracking-[0.4em] text-text-muted">{title}</p>
      <p className="text-sm leading-relaxed text-white/80">{text}</p>
    </div>
  );
}

function TriggerBlock({
  positive,
  negative,
}: {
  positive?: string[] | null;
  negative?: string[] | null;
}) {
  if ((!positive || positive.length === 0) && (!negative || negative.length === 0)) return null;
  return (
    <div className="space-y-3 rounded-3xl border border-white/10 bg-card-dark/30 p-4">
      {positive && positive.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-[0.4em] text-text-muted">Что нравится</p>
          <div className="flex flex-wrap gap-2">
            {positive.map((item) => (
              <span
                key={item}
                className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/80"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}
      {negative && negative.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-[0.4em] text-text-muted">Что ранит</p>
          <div className="flex flex-wrap gap-2">
            {negative.map((item) => (
              <span
                key={item}
                className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/80"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
