import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import type { PersonaDetails, StoryCard } from "../api/types";
import { fetchPersona, selectPersonaAndGreet } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { tg } from "../lib/telegram";

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
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
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
        setSelectedStoryId(null);
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
    const hasChanges = Boolean(selectedStoryId);
    try {
      setBusy(true);
      setSelectError(null);
      await selectPersonaAndGreet({
        personaId: persona.id,
        storyId: selectedStoryId ?? undefined,
        settingsChanged: hasHistory && hasChanges,
        extraDescription: selectedStoryId ? `Выбран сюжет: ${selectedStoryId}` : undefined,
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

  const storyCards = useMemo(() => persona?.story_cards ?? [], [persona]);
  const hasHistory = Boolean(persona?.has_history);
  const hasChanges = Boolean(selectedStoryId);
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

            <FeelBlock
              emotions={persona.emotions_full}
              positive={persona.triggers_positive}
              negative={persona.triggers_negative}
            />

            {storyCards && storyCards.length > 0 && (
              <StoriesBlock stories={storyCards} selectedId={selectedStoryId} onSelect={setSelectedStoryId} />
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

function FeelBlock({
  emotions,
  positive,
  negative,
}: {
  emotions?: string | null;
  positive?: string[] | null;
  negative?: string[] | null;
}) {
  const hasLikes = positive && positive.length > 0;
  const hasDislikes = negative && negative.length > 0;
  return (
    <div className="space-y-3 rounded-3xl border border-white/10 bg-card-dark/30 p-4">
      <p className="text-[11px] uppercase tracking-[0.4em] text-text-muted">Как она чувствует и реагирует</p>
      {emotions && <p className="text-sm leading-relaxed text-white/80">{emotions}</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {hasLikes && (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-white/60">Что ей нравится</p>
            <div className="flex flex-wrap gap-2">
              {positive!.map((item) => (
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
        {hasDislikes && (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-white/60">Что ранит</p>
            <div className="flex flex-wrap gap-2">
              {negative!.map((item) => (
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
    </div>
  );
}

function StoriesBlock({
  stories,
  selectedId,
  onSelect,
}: {
  stories: StoryCard[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  if (!stories || stories.length === 0) return null;
  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-white">Истории</p>
      <div className="space-y-3">
        {stories.map((card) => {
          const active = selectedId === card.id;
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => onSelect(active ? null : card.id)}
              className={`w-full text-left rounded-3xl border px-4 py-4 transition ${
                active
                  ? "border-pink-400/60 bg-white/10"
                  : "border-white/10 bg-card-dark/30 hover:border-white/20"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-base font-semibold text-white">{card.title}</p>
                  <p className="text-sm text-white/70">{card.description}</p>
                </div>
                <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-white/80">
                  {mapAtmosphere(card.atmosphere)}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function mapAtmosphere(value: string) {
  const map: Record<string, string> = {
    flirt_romance: "Флирт и романтика",
    support: "Поддержка",
    cozy_evening: "Уютный вечер",
    serious_talk: "Серьёзный разговор",
  };
  return map[value] ?? value;
}
