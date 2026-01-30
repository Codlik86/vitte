import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import type { PersonaDetails, StoryCard } from "../api/types";
import { fetchPersona, selectPersonaAndGreet } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { useImagesLeft } from "../hooks/useImagesLeft";
import { getAvatarPaths } from "../lib/avatars";
import { pub } from "../lib/pub";
import { tg } from "../lib/telegram";

export function CharacterDetails() {
  const { id } = useParams();
  const location = useLocation();
  const locationState = (location.state as { name?: string } | null) ?? null;
  const fallbackTitle = locationState?.name ?? "Персонаж";
  const navigate = useNavigate();
  const { data: accessStatus } = useAccessStatus();
   const { imagesLeft } = useImagesLeft();
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

  const hasSubscription = accessStatus?.has_subscription;
  const imagesAvailable = imagesLeft;
  const headerStats = {
    images: imagesAvailable,
    hasSubscription: hasSubscription,
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
    if (!selectedStoryId) {
      setSelectError("Сначала выбери историю");
      return;
    }
    const hasHistory = Boolean(persona.has_history);
    const hasChanges = Boolean(selectedStoryId);

    // Get selected story for atmosphere
    const selectedStory = persona.story_cards?.find((s) => s.id === selectedStoryId);

    try {
      setBusy(true);
      setSelectError(null);
      await selectPersonaAndGreet({
        personaId: persona.id,
        storyId: selectedStoryId ?? undefined,
        atmosphere: selectedStory?.atmosphere,
        settingsChanged: hasHistory && hasChanges,
        extraDescription: selectedStoryId ? `Выбран сюжет: ${selectedStoryId}` : undefined,
      });

      // Закрываем webapp - приветствие придёт в чат Telegram
      if (tg?.close) {
        tg.close();
      }
    } catch (e: any) {
      setSelectError(e.message ?? "Не удалось выбрать персонажа");
    } finally {
      setBusy(false);
    }
  };

  const storyCards = useMemo(() => {
    if (!persona?.story_cards) return [];
    const priority: Record<string, number> = {
      flirt_romance: 0,
      support: 1,
      cozy_evening: 2,
      serious_talk: 3,
    };
    return [...persona.story_cards].sort((a, b) => {
      const pa = priority[a.atmosphere] ?? 99;
      const pb = priority[b.atmosphere] ?? 99;
      if (pa === pb) return 0;
      return pa - pb;
    });
  }, [persona]);
  const hasHistory = Boolean(persona?.has_history);
  const actionLabel = selectedStoryId
    ? hasHistory
      ? "Обновить и продолжить"
      : "Начать разговор"
    : "Выбери историю";

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto flex min-h-dvh w-full max-w-screen-md flex-col px-4 pb-16 sm:px-5">
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
          <section className="mt-6 flex flex-1 flex-col space-y-6">
            <div className="relative w-full overflow-hidden rounded-3xl pb-[100%]">
              <img
                src={persona.avatar_chat_url ?? getAvatarPaths(persona.name, persona.is_custom).chat}
                alt={persona.name}
                className="absolute inset-0 h-full w-full rounded-3xl object-cover object-[50%_0%]"
              />
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

            <InfoBlock title="О персонаже" text={persona.legend_full ?? persona.long_description} />

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
                className={`w-full rounded-full bg-white px-4 py-4 text-base font-semibold text-bg-dark transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70 ${busy ? "loading-pulse" : ""}`}
                onClick={handleSelect}
                disabled={busy || !selectedStoryId}
              >
                {busy ? (
                  <span className="inline-flex items-center gap-1 leading-none">
                    Всего несколько секунд
                    <span className="loading-dots" aria-hidden>
                      <span />
                      <span />
                      <span />
                    </span>
                  </span>
                ) : (
                  actionLabel
                )}
              </button>
              <button
                className="mt-3 w-full rounded-full bg-gradient-to-r from-[#2c1a52] via-[#5a2b80] to-[#c23ba7] px-4 py-4 text-base font-semibold text-white shadow-card transition active:scale-[0.98]"
                onClick={() => navigate("/store")}
              >
                Сделать общение лучше
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
      <p className="text-sm font-semibold text-white">{title}</p>
      <p className="text-sm leading-relaxed text-white/80 sm:text-base sm:leading-relaxed">{text}</p>
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
  const [emotionsOpen, setEmotionsOpen] = useState(false);
  const hasLikes = positive && positive.length > 0;
  const hasDislikes = negative && negative.length > 0;
  return (
    <div className="space-y-3 rounded-3xl border border-white/10 bg-card-dark/30 p-4">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2"
        onClick={() => setEmotionsOpen((prev) => !prev)}
        aria-expanded={emotionsOpen}
      >
        <p className="text-sm font-semibold text-white">Эмоции и чувства</p>
        <span
          className={`inline-flex h-5 w-5 items-center justify-center text-white transition-transform ${
            emotionsOpen ? "rotate-180" : "-rotate-90"
          }`}
          aria-hidden
        >
          ▼
        </span>
      </button>
      {emotionsOpen && (
        <div className="space-y-3">
          {emotions && (
            <p className="text-sm leading-relaxed text-white/80 sm:text-base sm:leading-relaxed">
              {emotions}
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            {hasLikes && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-white">Что ей нравится</p>
                <div className="flex flex-wrap gap-2">
                  {positive!.map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/80 sm:text-sm"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {hasDislikes && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-white">Что ранит</p>
                <div className="flex flex-wrap gap-2">
                  {negative!.map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/80 sm:text-sm"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
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
              className={`relative w-full text-left rounded-3xl transition ${
                active
                  ? "border border-pink-400/60 bg-white/10"
                  : "border border-white/10 bg-card-dark/30 hover:border-white/20"
              }`}
            >
              <div className="flex w-full flex-col gap-2 rounded-[22px] text-left px-4 py-4 sm:px-5 sm:py-5">
                {card.image && (
                  <div className="relative w-full overflow-hidden rounded-2xl pb-[55%]">
                    <img
                      src={pub(card.image)}
                      alt={card.title}
                      className="absolute inset-0 h-full w-full object-cover object-[50%_0%]"
                    />
                  </div>
                )}
                <span
                  className="inline-flex max-w-full items-center justify-start truncate rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-white/80 md:px-4 md:text-xs"
                >
                  {mapAtmosphere(card.atmosphere)}
                </span>
                <p className="w-full text-base font-semibold leading-tight text-white sm:text-lg">
                  {card.title}
                </p>
                <p className="w-full text-sm text-white/70 sm:text-base">{card.description}</p>
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
