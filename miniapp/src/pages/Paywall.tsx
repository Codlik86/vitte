import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { DebugTelegramBanner } from "../components/DebugTelegramBanner";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { fetchPaymentPlans, logAnalyticsEvent, subscribeToPlan } from "../api/client";
import type { PaymentPlan } from "../api/types";
import { tg } from "../lib/telegram";

function getPeriodLabel(period: PaymentPlan["period"]) {
  switch (period) {
    case "week":
      return "неделя";
    case "month":
      return "месяц";
    case "quarter":
      return "квартал";
    default:
      return "год";
  }
}

export function Paywall() {
  const { data, error, reload } = useAccessStatus();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<PaymentPlan[]>([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [actionPlan, setActionPlan] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const variant = data?.paywall_variant ?? "A";
  const remainingMessages = Math.max(
    0,
    (data?.free_messages_limit ?? 15) - (data?.free_messages_used ?? 0),
  );

  const headerStats = {
    gems: 0,
    usedMessages: data?.free_messages_used ?? null,
    limitMessages: data?.free_messages_limit ?? null,
    hasUnlimited: data?.has_access,
    isPremium: Boolean(data?.is_premium),
  };

  useEffect(() => {
    async function loadPlans() {
      try {
        setPlansError(null);
        setPlansLoading(true);
        const response = await fetchPaymentPlans();
        setPlans(response);
      } catch (err) {
        setPlansError(err instanceof Error ? err.message : "Не удалось загрузить планы");
      } finally {
        setPlansLoading(false);
      }
    }
    loadPlans();
  }, []);

  useEffect(() => {
    if (data?.paywall_variant) {
      logAnalyticsEvent("paywall_shown", { variant: data.paywall_variant }).catch(() => {});
    }
  }, [data?.paywall_variant]);

  const recommendedPlan = useMemo(
    () => plans.find((plan) => plan.recommended) ?? plans[0],
    [plans],
  );

  const handleSubscribe = async (planCode: string | undefined) => {
    if (!planCode) return;
    setActionPlan(planCode);
    setActionError(null);
    try {
      await logAnalyticsEvent("paywall_cta_click", { plan_code: planCode, variant });
      const response = await subscribeToPlan(planCode);
      const confirmation = response.confirmation as { confirmation_url?: string } | undefined;
      if (response.provider === "yookassa" && confirmation?.confirmation_url) {
        if (tg?.openTelegramLink) {
          tg.openTelegramLink(confirmation.confirmation_url);
        } else {
          window.open(confirmation.confirmation_url, "_blank");
        }
      } else if (response.provider === "stars") {
        // TODO: интеграция openInvoice при подключении Stars
        console.info("[Vitte] Stars invoice payload", confirmation);
      }
      await reload();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Не удалось инициировать подписку";
      setActionError(message);
    } finally {
      setActionPlan(null);
    }
  };

  const renderVariantA = () => (
    <section className="w-full rounded-4xl border border-white/5 bg-card-elevated/85 px-6 py-8 shadow-card">
      <p className="text-sm uppercase tracking-[0.2em] text-white/60">
        Premium безлимит
      </p>
      <h1 className="mt-2 text-4xl font-semibold leading-tight tracking-tight">
        Открой безлимит и улучшенные сцены
      </h1>
      <ul className="mt-5 space-y-3 text-sm text-white/80">
        <li>• Безлимитные сообщения и расширенные эмоции.</li>
        <li>• Доступ к кастомному герою и интимным сценам.</li>
        <li>• Сохранённые эпизоды и длинные письма.</li>
      </ul>
      {plansError && <p className="mt-4 text-sm text-red-300">{plansError}</p>}
      {actionError && <p className="mt-4 text-sm text-red-300">{actionError}</p>}
      <button
        className="mt-6 w-full rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-4 text-base font-semibold text-white shadow-card active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
        disabled={!recommendedPlan || actionPlan === recommendedPlan.code || plansLoading}
        onClick={() => handleSubscribe(recommendedPlan?.code)}
      >
        {actionPlan === recommendedPlan?.code ? "Оформляем..." : "Оформить подписку"}
      </button>
      <Link
        to="/"
        className="mt-3 block text-center text-sm text-white/70 underline-offset-2 hover:text-white"
      >
        Вернуться к персонажам
      </Link>
    </section>
  );

  const renderVariantB = () => (
    <section className="space-y-4">
      <div className="rounded-4xl border border-white/5 bg-card-elevated/80 px-6 py-5 text-sm text-white/80 shadow-card">
        <p>
          Бесплатно осталось{" "}
          <span className="font-semibold text-white">{remainingMessages} сообщений</span>. Premium
          снимает лимит и включает расширенный режим.
        </p>
      </div>

      <div className="space-y-4">
        {plansLoading
          ? Array.from({ length: 3 }).map((_, index) => (
              <div
                key={`skeleton-${index}`}
                className="rounded-3xl border border-white/5 bg-card-elevated/60 px-5 py-4 animate-pulse"
              >
                <div className="h-4 w-32 rounded-full bg-white/10" />
                <div className="mt-3 h-3 w-48 rounded-full bg-white/10" />
              </div>
            ))
          : plans.map((plan) => {
              const isProcessing = actionPlan === plan.code;
              return (
                <div
                  key={plan.code}
                  className={`rounded-3xl border px-5 py-4 shadow-card ${
                    plan.recommended
                      ? "border-pink-400/60 bg-card-elevated/90"
                      : "border-white/5 bg-card-elevated/70"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-base font-semibold text-white">{plan.title}</p>
                      <p className="text-xs text-white/60">
                        {plan.description} · {getPeriodLabel(plan.period)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-semibold text-white">
                        {plan.price.toLocaleString("ru-RU")} ₽
                      </p>
                      <p className="text-xs text-white/60">за {getPeriodLabel(plan.period)}</p>
                    </div>
                  </div>
                  <button
                    className="mt-4 w-full rounded-2xl bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
                    disabled={isProcessing}
                    onClick={() => handleSubscribe(plan.code)}
                  >
                    {isProcessing ? "Оформляем..." : "Выбрать план"}
                  </button>
                </div>
              );
            })}
      </div>

      {actionError && <p className="text-sm text-red-300">{actionError}</p>}

      <button
        onClick={() => navigate("/")}
        className="w-full rounded-full border border-white/10 bg-transparent px-4 py-3 text-sm text-white/80 transition hover:bg-white/5"
      >
        Продолжить с лимитом 15 сообщений
      </button>
    </section>
  );

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto w-full max-w-screen-sm space-y-6 px-4 pb-12 pt-6">
        <PageHeader
          title="Подписка"
          showBack
          onBack={() => navigate(-1)}
          stats={headerStats}
        />

        <DebugTelegramBanner />

        {error && !data && (
          <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        {data?.is_premium && (
          <div className="rounded-3xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
            Premium активна{" "}
            {data.premium_until
              ? `до ${new Date(data.premium_until).toLocaleDateString("ru-RU")}`
              : "без ограничения"}
          </div>
        )}

        {variant === "A" ? renderVariantA() : renderVariantB()}
      </div>
    </div>
  );
}
