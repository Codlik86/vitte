import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { DebugTelegramBanner } from "../components/DebugTelegramBanner";
import {
  fetchFeaturesStatus,
  toggleFeature,
  clearDialogs,
  clearLongMemory,
  deleteAccount,
} from "../api/client";
import type { FeatureStatusItem } from "../api/types";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { tg } from "../lib/telegram";

type TabKey = "upgrades" | "base";

export function Settings() {
  const navigate = useNavigate();
  const { data: accessStatus, reload: reloadAccess } = useAccessStatus();
  const [activeTab, setActiveTab] = useState<TabKey>("upgrades");
  const [features, setFeatures] = useState<FeatureStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const headerStats = {
    gems: 0,
    usedMessages: accessStatus?.free_messages_used ?? null,
    limitMessages: accessStatus?.free_messages_limit ?? null,
    hasUnlimited: Boolean(accessStatus?.has_subscription),
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
    () => features.filter((f) => f.active || Boolean(f.until)),
    [features]
  );

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

  const handleClearDialogs = async () => {
    if (!window.confirm("Очистить всю переписку? Это удалит сообщения из краткой памяти.")) return;
    try {
      await clearDialogs();
      setActionMessage("Краткая память очищена.");
    } catch (e: any) {
      setError(e.message ?? "Не удалось очистить диалоги");
    }
  };

  const handleClearLongMemory = async () => {
    if (!window.confirm("Очистить долгую память? Воспоминания будут стерты.")) return;
    try {
      await clearLongMemory();
      setActionMessage("Долгая память очищена.");
    } catch (e: any) {
      setError(e.message ?? "Не удалось очистить долгую память");
    }
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm("Удалить аккаунт и все данные? Это действие необратимо.")) return;
    try {
      await deleteAccount();
      setActionMessage("Аккаунт удалён. Можно закрыть MiniApp.");
    } catch (e: any) {
      setError(e.message ?? "Не удалось удалить аккаунт");
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
          <div className="grid gap-3">
            {FEATURE_PLACEHOLDERS.map((card) => (
              <div
                key={card.code}
                className="rounded-3xl border border-white/5 bg-card-dark/40 px-4 py-4"
              >
                <p className="text-base font-semibold text-white">{card.title}</p>
                <p className="mt-1 text-sm text-white/70">{card.description}</p>
                <button
                  className="mt-3 inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-3 text-sm font-semibold text-white"
                  onClick={() => navigate("/store")}
                >
                  Подключить
                </button>
              </div>
            ))}
          </div>
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
                {feature.until && (
                  <p className="mt-1 text-xs text-white/60">
                    Активно до {new Date(feature.until).toLocaleDateString("ru-RU", { day: "2-digit", month: "short" })}
                  </p>
                )}
              </div>
              {feature.toggleable && (
                <ToggleSwitch
                  enabled={feature.enabled}
                  onChange={(value) => handleToggle(feature, value)}
                  label={feature.enabled ? "Вкл" : "Выкл"}
                />
              )}
            </div>
            {feature.code === "voice" && (
              <p className="text-xs text-white/60">Статус: ответы приходят голосом.</p>
            )}
            {feature.code === "images" && (
              <p className="text-xs text-amber-200/80">
                Функция готовится. Статус сохраняется за твоим аккаунтом.
              </p>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderBaseSettings = () => {
    return (
      <div className="space-y-3">
        <ActionButton label="Очистить память диалогов" onClick={handleClearDialogs} tone="secondary" />
        <ActionButton label="Очистить долгую память" onClick={handleClearLongMemory} tone="secondary" />
        <ActionButton label="Удалить аккаунт" onClick={handleDeleteAccount} tone="danger" />
        <ActionButton label="Выйти из MiniApp" onClick={handleLogout} tone="ghost" />
      </div>
    );
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto w-full max-w-screen-sm space-y-6 px-4 pb-16">
        <PageHeader title="Настройки" showBack onBack={() => navigate(-1)} stats={headerStats} />
        <DebugTelegramBanner />

        {error && (
          <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}
        {actionMessage && (
          <div className="rounded-3xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
            {actionMessage}
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
      className={`relative inline-flex items-center rounded-full px-1 py-1 text-xs font-semibold transition ${
        enabled ? "bg-emerald-400/20 text-emerald-100" : "bg-white/10 text-white/70"
      }`}
    >
      <span
        className={`inline-block h-6 w-6 rounded-full bg-white transition ${
          enabled ? "translate-x-5" : "translate-x-0"
        }`}
      />
      <span className="ml-2 pr-2">{label ?? (enabled ? "On" : "Off")}</span>
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

const FEATURE_PLACEHOLDERS: FeatureStatusItem[] = [
  {
    code: "long_letters",
    title: "Большие письма",
    description: "Длинные, тёплые ответы и письма.",
    active: false,
    enabled: false,
    until: null,
    product_code: "long_letters_month",
    toggleable: true,
  },
  {
    code: "voice",
    title: "Голос персонажа",
    description: "Ответы голосом, будто вы рядом.",
    active: false,
    enabled: false,
    until: null,
    product_code: "voice_month",
    toggleable: true,
  },
  {
    code: "deep_mode",
    title: "Глубокие отношения",
    description: "Больше эмоциональной глубины и искренности.",
    active: false,
    enabled: false,
    until: null,
    product_code: "deep_mode_month",
    toggleable: true,
  },
  {
    code: "images",
    title: "Фантазии и образы",
    description: "Будущие визуальные сцены (заглушка).",
    active: false,
    enabled: false,
    until: null,
    product_code: "fantasy_pack_month",
    toggleable: false,
  },
];
