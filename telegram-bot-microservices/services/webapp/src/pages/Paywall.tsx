import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageHeader } from "../components/layout/PageHeader";
import { useStoreData } from "../hooks/useStoreData";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { useImagesLeft } from "../hooks/useImagesLeft";
import { buySubscription } from "../api/client";
import { tg, type InvoiceStatus } from "../lib/telegram";

export function Paywall() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { status, config, loading, reload } = useStoreData();
  const { data: accessStatus, reload: reloadAccess } = useAccessStatus();
  const { imagesLeft } = useImagesLeft();
  const [busyCode, setBusyCode] = useState<string | null>(null);

  const hasSubscription = Boolean(status?.has_active_subscription || accessStatus?.has_subscription);
  const dateLocale = i18n.language === "ru" ? "ru-RU" : "en-US";
  const endDate = status?.subscription_ends_at
    ? new Date(status.subscription_ends_at).toLocaleDateString(dateLocale)
    : null;
  const plans = config?.subscription_plans ?? [];
  const imagesAvailable = imagesLeft;
  const headerStats = {
    images: imagesAvailable,
    hasSubscription,
    isPremium: hasSubscription,
  };

  useEffect(() => {
    reload();
  }, [reload]);

  const handleBuy = async (code: string) => {
    setBusyCode(code);
    try {
      const res = await buySubscription(code);
      if (!res.invoice_url) {
        alert(t("invoice_error"));
        return;
      }

      // Open invoice in Telegram WebApp overlay
      if (tg?.openInvoice) {
        tg.openInvoice(res.invoice_url, async (status: InvoiceStatus) => {
          if (status === "paid") {
            await reload();
            await reloadAccess();
          }
          setBusyCode(null);
        });
      } else {
        // Fallback for older versions
        tg?.openTelegramLink?.(res.invoice_url);
        tg?.close?.();
      }
    } catch (e: any) {
      alert(e.message ?? t("subscription_buy_error"));
      setBusyCode(null);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto w-full max-w-screen-sm space-y-6 px-4 pb-16">
        <PageHeader title={t("subscription_title")} showBack onBack={() => navigate(-1)} stats={headerStats} />

        <section className="space-y-3 rounded-3xl border border-white/10 bg-card-elevated/80 px-5 py-5 shadow-card">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-white">CraveMe Premium</h2>
            <ul className="space-y-1 text-sm text-white/80">
              <li>• {t("feature_unlimited_messages")}</li>
              <li>• {t("feature_40_images")}</li>
              <li>• {t("feature_advanced_ai")}</li>
              <li>• {t("feature_quality")}</li>
            </ul>
            {hasSubscription && (
              <p className="text-sm text-emerald-200">
                {endDate
                  ? t("subscription_active", { date: endDate })
                  : t("subscription_active_no_date")}
              </p>
            )}
          </div>

          {!hasSubscription && (
            <div className="space-y-3">
              {loading
                ? Array.from({ length: 3 }).map((_, i) => (
                    <div
                      key={`plan-skeleton-${i}`}
                      className="h-16 rounded-3xl border border-white/10 bg-white/5 animate-pulse"
                    />
                  ))
                : plans.map((plan) => (
                    <button
                      key={plan.code}
                      type="button"
                      onClick={() => handleBuy(plan.code)}
                      disabled={busyCode === plan.code}
                      className="flex w-full items-center justify-between rounded-3xl border border-white/10 bg-card-dark/30 px-4 py-4 text-left transition hover:border-white/30 disabled:opacity-60"
                    >
                      <div className="min-w-0 pr-3">
                        <p className="text-sm font-semibold text-white">{plan.title}</p>
                        <p className="text-xs text-white/60 leading-snug">{plan.duration_days} {t("days")}</p>
                      </div>
                      <div className="flex-shrink-0 text-right">
                        <p className="text-lg font-semibold text-white whitespace-nowrap">{plan.price_stars} ⭐</p>
                        {busyCode === plan.code && (
                          <p className="text-[11px] text-white/60">{t("processing")}</p>
                        )}
                      </div>
                    </button>
                  ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
