import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { PersonaListItem } from "../api/types";
import { fetchPersonas } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { useImagesLeft } from "../hooks/useImagesLeft";
import { PersonaCard } from "../components/PersonaCard";
import { DebugTelegramBanner } from "../components/DebugTelegramBanner";
import { getAvatarPaths } from "../lib/avatars";

type CustomPersonaEntry = {
  id: "custom";
  name: string;
  short_description: string;
  isCustomEntry: true;
};

export function CharactersList() {
  const navigate = useNavigate();
  const { data: accessStatus } = useAccessStatus();
  const { imagesLeft } = useImagesLeft();
  const debugMiniapp = import.meta.env.VITE_DEBUG_MINIAPP === "1";
  const [items, setItems] = useState<PersonaListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const imagesAvailable = imagesLeft;
  const headerStats = {
    images: imagesAvailable,
    hasSubscription: accessStatus?.has_subscription,
    isPremium: accessStatus?.has_subscription,
  };

  const load = async () => {
    try {
      setError(null);
      setLoading(true);
      const data = await fetchPersonas();
      setItems(data.items);
      if (debugMiniapp) {
        const names = data.items.map((p) => (p.name || "").toLowerCase());
        console.info("[Vitte][DEBUG_MINIAPP] personas fetched", {
          count: data.items.length,
          hasAsh: names.includes("ash"),
          hasJulie: names.includes("julie"),
          names,
        });
      }
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
    const personasWithCustom: Array<PersonaListItem | CustomPersonaEntry> = [
      {
        id: "custom",
        name: "Свой герой",
        short_description: "Создай собственного персонажа",
        isCustomEntry: true,
      },
      ...items.filter((p) => !p.is_custom),
    ];

    if (loading) {
      return (
        <div className="grid grid-cols-2 gap-4 sm:gap-5">
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

    return (
      <div className="grid grid-cols-2 gap-4 sm:gap-5">
        {personasWithCustom.map((p) => {
          if ("isCustomEntry" in p) {
            return (
              <PersonaCard
                key="custom-persona"
                title="Свой герой"
                description="Создай собственного персонажа"
                gradientVariant="custom"
                showCustomAvatar
                onClick={() => navigate("/characters/custom")}
              />
            );
          }

          const avatar = {
            card: p.avatar_card_url ?? getAvatarPaths(p.name, p.is_custom).card,
            chat: p.avatar_chat_url ?? getAvatarPaths(p.name, p.is_custom).chat,
          };
          return (
            <PersonaCard
              key={p.id}
              title={p.name}
              description={p.short_description}
              selected={p.is_selected}
              gradientVariant="default"
              avatarUrl={avatar.card}
              onClick={() => navigate(`/characters/${p.id}`, { state: { name: p.name } })}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto w-full max-w-[640px] px-4 pb-16 space-y-6">
        <PageHeader title="Персонажи" showBack={false} stats={headerStats} />
        <div className="space-y-6">
          <DebugTelegramBanner />
          {renderCards()}
        </div>

        <div className="mt-6 space-y-4">
          <Link
            to="/paywall"
            className="inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-4 text-base font-semibold text-white shadow-card active:scale-[0.99]"
          >
            Перейти к подписке
          </Link>
          <Link
            to="/store"
            className="inline-flex w-full items-center justify-center rounded-full border border-white/10 bg-card-dark/80 px-4 py-4 text-base font-medium text-white/90 transition hover:bg-card-dark"
          >
            Магазин
          </Link>
          <Link
            to="/settings"
            className="inline-flex w-full items-center justify-center rounded-full border border-white/10 bg-card-dark/80 px-4 py-4 text-base font-medium text-white/90 transition hover:bg-card-dark"
          >
            Настройки и улучшения
          </Link>
        </div>
      </div>
    </div>
  );
}
