import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageHeader } from "../components/layout/PageHeader";
import { DebugTelegramBanner } from "../components/DebugTelegramBanner";
import {
  // fetchFeaturesStatus,  // ОТКЛЮЧЕНО
  // toggleFeature,  // ОТКЛЮЧЕНО
  clearDialogs,
  clearLongMemory,
} from "../api/client";
// import type { FeatureStatusItem } from "../api/types";  // ОТКЛЮЧЕНО
import { useAccessStatus } from "../hooks/useAccessStatus";
import { useImagesLeft } from "../hooks/useImagesLeft";
import { tg } from "../lib/telegram";

// type TabKey = "upgrades" | "base";  // ОТКЛЮЧЕНО - больше нет улучшений
// const FEATURE_CODES = ["intense_mode", "fantasy_scenes"];

export function Settings() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: accessStatus } = useAccessStatus();
  const { imagesLeft } = useImagesLeft();
  const [error, setError] = useState<string | null>(null);

  const imagesAvailable = imagesLeft;

  const headerStats = {
    images: imagesAvailable,
    hasSubscription: Boolean(accessStatus?.has_subscription),
    isPremium: Boolean(accessStatus?.has_subscription),
  };

  const handleClearAllDialogs = async () => {
    if (!window.confirm(t("clear_confirm"))) return;
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
      setError(e.message ?? t("clear_error"));
    }
  };

  const handleLogout = () => {
    if (tg?.close) {
      tg.close();
    } else {
      navigate("/");
    }
  };

  const renderBaseSettings = () => {
    return (
      <div className="space-y-3">
        <ActionButton label={t("clear_all_dialogs")} onClick={handleClearAllDialogs} tone="secondary" />
        <ActionButton label={t("exit_miniapp")} onClick={handleLogout} tone="ghost" />
      </div>
    );
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto w-full max-w-screen-sm space-y-6 px-4 pb-16">
        <PageHeader title={t("settings_title")} showBack onBack={() => navigate(-1)} stats={headerStats} />
        <DebugTelegramBanner />

        {!accessStatus?.has_subscription && (
          <div className="rounded-3xl bg-gradient-to-r from-[#2c1a52] via-[#5a2b80] to-[#c23ba7] px-4 py-4 text-white shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-base font-semibold">{t("open_full_access")}</p>
                <p className="text-sm text-white/80">{t("unlimited_text")}</p>
              </div>
              <button
                type="button"
                onClick={() => navigate("/paywall")}
                className="rounded-full bg-white/15 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/25 active:scale-95"
              >
                {t("go_to_subscription")}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        {/* Показываем только Основные настройки */}
        {renderBaseSettings()}
      </div>
    </div>
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
