import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { DebugTelegramBanner } from "../components/DebugTelegramBanner";
import {
  fetchFeaturesStatus,
  toggleFeature,
  clearDialogs,
  clearLongMemory,
} from "../api/client";
import type { FeatureStatusItem } from "../api/types";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { useImagesLeft } from "../hooks/useImagesLeft";
import { tg } from "../lib/telegram";

type TabKey = "upgrades" | "base";
const FEATURE_CODES = ["intense_mode", "fantasy_scenes"];

export function Settings() {
  const navigate = useNavigate();
  const { data: accessStatus, reload: reloadAccess } = useAccessStatus();
  const { imagesLeft } = useImagesLeft();
  const [activeTab, setActiveTab] = useState<TabKey>("upgrades");
  const [features, setFeatures] = useState<FeatureStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const imagesAvailable = imagesLeft;

  const headerStats = {
    images: imagesAvailable,
    hasSubscription: Boolean(accessStatus?.has_subscription),
    isPremium: Boolean(accessStatus?.has_subscription),
  };

  const load = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const data = await fetchFeaturesStatus();
      setFeatures(data.features);
    } catch (e: any) {
      setError(e.message ?? "Не удалось загрузить настройки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (accessStatus?.features?.features?.length) {
      setFeatures(accessStatus.features.features);
      setLoading(false);
    } else {
      load();
    }
  }, [accessStatus?.features?.features, load]);

  const ownedFeatures = useMemo(
    () => features.filter((f) => FEATURE_CODES.includes(f.code) && (f.active || f.enabled)),
    [features],
  );
  const lockedFeatures = useMemo(
    () => features.filter((f) => FEATURE_CODES.includes(f.code) && !(f.active || f.enabled)),
    [features],
  );
  const featurePrices = useMemo(() => {
    const map = new Map<string, number>();
    accessStatus?.store?.features?.forEach((item) => {
      map.set(item.code, item.price_stars);
    });
    return map;
  }, [accessStatus?.store?.features]);

  const handleToggle = async (feature: FeatureStatusItem, next: boolean) => {
    try {
      const res = await toggleFeature(feature.code, next);
      setFeatures((prev) => {
        const updated = prev.map((item) =>
          item.code === feature.code ? { ...item, ...res.features[0] } : item
        );
        return updated;
      });
      await reloadAccess();
    } catch (e: any) {
      setError(e.message ?? "Не удалось обновить настройку");
    }
  };

  const handleClearAllDialogs = async () => {
    if (!window.confirm("Очистить все диалоги и память? Это удалит все сообщения и воспоминания персонажей. Действие необратимо.")) return;
    try {
      // Очищаем краткую память (диалоги)
      await clearDialogs();
      // Очищаем долгую память (Qdrant)
      await clearLongMemory();

      // Закрываем webapp - пользователь вернётся в бот с чистой историей
      if (tg?.close) {
        tg.close();
      } else {
        navigate("/");
      }
    } catch (e: any) {
      setError(e.message ?? "Не удалось очистить диалоги");
    }
  };

  const handleLogout = () => {
    if (tg?.close) {
      tg.close();
    } else {
      navigate("/");
    }
  };

  const renderFeatures = () => {
    if (loading) {
      return (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={`feat-skeleton-${i}`}
              className="h-20 w-full rounded-3xl border border-white/5 bg-white/5 animate-pulse"
            />
          ))}
        </div>
      );
    }

    if (ownedFeatures.length === 0) {
      return (
        <div className="space-y-4">
          <p className="text-sm text-white/70">
            Пока нет активных улучшений. Подключи фичи, чтобы сделать общение богаче.
          </p>
          <LockedFeatureList
            lockedFeatures={lockedFeatures}
            onUnlock={() => navigate("/store")}
            priceMap={featurePrices}
          />
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {ownedFeatures.map((feature) => (
          <div
            key={feature.code}
            className="flex flex-col gap-2 rounded-3xl border border-white/5 bg-card-elevated/70 px-4 py-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-base font-semibold text-white">{feature.title}</p>
                <p className="text-sm text-white/70">{feature.description}</p>
              </div>
              {feature.toggleable && (
                <ToggleSwitch
                  enabled={feature.enabled}
                  onChange={(value) => handleToggle(feature, value)}
                  label={feature.enabled ? "Вкл" : "Выкл"}
                />
              )}
            </div>
          </div>
        ))}

        {lockedFeatures.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-semibold text-white">Недоступные улучшения</p>
            <LockedFeatureList
              lockedFeatures={lockedFeatures}
              onUnlock={() => navigate("/store")}
              priceMap={featurePrices}
            />
          </div>
        )}
      </div>
    );
  };

  const renderBaseSettings = () => {
    return (
      <div className="space-y-3">
        <ActionButton label="Очистить все диалоги" onClick={handleClearAllDialogs} tone="secondary" />
        <ActionButton label="Выйти из MiniApp" onClick={handleLogout} tone="ghost" />
      </div>
    );
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto w-full max-w-screen-sm space-y-6 px-4 pb-16">
        <PageHeader title="Настройки" showBack onBack={() => navigate(-1)} stats={headerStats} />
        <DebugTelegramBanner />

        {!accessStatus?.has_subscription && (
          <div className="rounded-3xl bg-gradient-to-r from-[#2c1a52] via-[#5a2b80] to-[#c23ba7] px-4 py-4 text-white shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-base font-semibold">Открой полный доступ</p>
                <p className="text-sm text-white/80">Неограниченные диалоги и все персонажи без ограничений.</p>
              </div>
              <button
                type="button"
                onClick={() => navigate("/paywall")}
                className="rounded-full bg-white/15 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/25 active:scale-95"
              >
                Перейти к подписке
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        <div className="flex rounded-3xl border border-white/5 bg-card-dark/60 p-1">
          <TabButton active={activeTab === "upgrades"} onClick={() => setActiveTab("upgrades")}>
            Мои улучшения
          </TabButton>
          <TabButton active={activeTab === "base"} onClick={() => setActiveTab("base")}>
            Основные
          </TabButton>
        </div>

        {activeTab === "upgrades" ? renderFeatures() : renderBaseSettings()}
      </div>
    </div>
  );
}

function LockedFeatureList({
  lockedFeatures,
  onUnlock,
  priceMap,
}: {
  lockedFeatures: FeatureStatusItem[];
  onUnlock: () => void;
  priceMap: Map<string, number>;
}) {
  return (
    <div className="grid gap-3">
      {lockedFeatures.map((card) => (
        <div
          key={card.code}
          className="rounded-3xl border border-white/5 bg-card-dark/40 px-4 py-4"
        >
          <p className="text-base font-semibold text-white">{card.title}</p>
          <p className="mt-1 text-sm text-white/70">{card.description}</p>
          <button
            className="mt-3 inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-3 text-sm font-semibold text-white"
            onClick={onUnlock}
          >
            Разблокировать
            {priceMap.has(card.code) ? ` · ${priceMap.get(card.code)} ⭐` : ""}
          </button>
        </div>
      ))}
    </div>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 rounded-2xl px-4 py-3 text-sm font-semibold transition ${
        active ? "bg-white text-bg-dark shadow" : "text-white/70 hover:text-white"
      }`}
    >
      {children}
    </button>
  );
}

function ToggleSwitch({
  enabled,
  onChange,
  label,
}: {
  enabled: boolean;
  onChange: (value: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className={`inline-flex items-center gap-2 text-xs font-semibold transition ${
        enabled ? "text-emerald-100" : "text-white/70"
      }`}
    >
      <span
        className={`relative flex h-7 w-12 items-center rounded-full px-1 transition ${
          enabled ? "bg-emerald-400/60" : "bg-white/15"
        }`}
      >
        <span
          className={`h-5 w-5 rounded-full bg-white shadow transition-transform ${
            enabled ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </span>
      <span className="pr-1">{label ?? (enabled ? "On" : "Off")}</span>
    </button>
  );
}

function ActionButton({
  label,
  onClick,
  tone = "secondary",
}: {
  label: string;
  onClick: () => void;
  tone?: "secondary" | "danger" | "ghost";
}) {
  const toneClass =
    tone === "danger"
      ? "border-red-500/50 bg-red-500/10 text-red-100"
      : tone === "ghost"
      ? "border-white/10 bg-white/5 text-white/80"
      : "border-white/10 bg-card-elevated/60 text-white";
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center justify-between rounded-3xl border px-4 py-4 text-left text-sm font-semibold transition hover:translate-y-[-1px] ${toneClass}`}
    >
      <span>{label}</span>
      <span aria-hidden>→</span>
    </button>
  );
}
