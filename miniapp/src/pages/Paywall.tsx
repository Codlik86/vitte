import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { DebugTelegramBanner } from "../components/DebugTelegramBanner";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { fetchPaymentPlans, logAnalyticsEvent, subscribeToPlan } from "../api/client";
import type { PaymentPlan } from "../api/types";
import { tg } from "../lib/telegram";

const BOT_USERNAME = "<ИМЯ_БОТА>"; // TODO: заменить на актуальный username

const FALLBACK_PLANS: PaymentPlan[] = [
  {
    code: "premium_3d",
    title: "3 дня Premium",
    description: "Познакомься с безлимитными ответами.",
    price: 299,
    currency: "RUB",
    period: "day",
    provider: "yookassa",
  },
  {
    code: "premium_1w",
    title: "Неделя Premium",
    description: "7 дней глубоких сцен и флирта.",
    price: 599,
    currency: "RUB",
    period: "week",
    provider: "yookassa",
  },
  {
    code: "premium_1m",
    title: "Месяц Premium",
    description: "30 дней безлимитного общения.",
    price: 999,
    currency: "RUB",
    period: "month",
    provider: "yookassa",
    recommended: true,
  },
  {
    code: "premium_3m",
    title: "3 месяца Premium",
    description: "Экономия и длинные истории.",
    price: 2199,
    currency: "RUB",
    period: "quarter",
    provider: "yookassa",
  },
];

const PLAN_ORDER = ["premium_3d", "premium_1w", "premium_1m", "premium_3m"];

function getPeriodLabel(period: PaymentPlan["period"]) {
  switch (period) {
    case "day":
      return "день";
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

function openBotPayment(planCode: string) {
  const startParam = `pay_${planCode}`;
  const url = `https://t.me/${BOT_USERNAME}?start=${startParam}`;
  if (tg?.openTelegramLink) {
    tg.openTelegramLink(url);
  } else {
    window.open(url, "_blank");
  }
}

export function Paywall() {
  const { data, error, reload } = useAccessStatus();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<PaymentPlan[]>([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const remainingMessages = Math.max(
    0,
    (data?.free_messages_limit ?? 15) - (data?.free_messages_used ?? 0),
  );

  const hasSubscription = Boolean(data?.has_subscription);
  const headerStats = {
    gems: 0,
    usedMessages: data?.free_messages_used ?? null,
    limitMessages: data?.free_messages_limit ?? null,
    hasUnlimited: hasSubscription,
    isPremium: hasSubscription,
  };

  useEffect(() => {
    async function loadPlans() {
      try {
        setPlansError(null);
        setPlansLoading(true);
        const response = await fetchPaymentPlans();
        const normalized = response.length ? response : FALLBACK_PLANS;
        setPlans(normalized);
      } catch (err) {
        setPlansError(err instanceof Error ? err.message : "Не удалось загрузить планы");
        setPlans(FALLBACK_PLANS);
      } finally {
        setPlansLoading(false);
      }
    }
    loadPlans();
  }, []);

  useEffect(() => {
    if (!hasSubscription) {
      logAnalyticsEvent("paywall_shown", { source: "miniapp" }).catch(() => {});
    }
  }, [hasSubscription]);

  const orderedPlans = useMemo(() => {
    if (!plans.length) {
      return [];
    }
    return [...plans].sort(
      (a, b) => PLAN_ORDER.indexOf(a.code) - PLAN_ORDER.indexOf(b.code),
    );
  }, [plans]);

  const activePlan = orderedPlans.find((plan) => plan.code === selectedPlan) ?? null;

  const handlePay = async () => {
    if (!activePlan) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await logAnalyticsEvent("paywall_cta_click", { plan_code: activePlan.code });
      const response = await subscribeToPlan(activePlan.code);
      const confirmation = response.confirmation as { confirmation_url?: string } | undefined;
      if (response.provider === "yookassa" && confirmation?.confirmation_url) {
        if (tg?.openTelegramLink) {
          tg.openTelegramLink(confirmation.confirmation_url);
        } else {
          window.open(confirmation.confirmation_url, "_blank");
        }
      } else if (response.provider === "stars") {
        // TODO: интеграция openInvoice при запуске Stars
        console.info("[Vitte] Stars invoice", confirmation);
      } else {
        openBotPayment(activePlan.code);
      }
      await reload();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Не удалось инициировать подписку";
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const renderPremiumState = () => (
    <section className="space-y-6 rounded-4xl border border-emerald-500/30 bg-card-elevated/85 px-6 py-7 shadow-card">
      <div className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-200">
          Premium активна
        </p>
        <h1 className="text-3xl font-semibold text-white">У тебя подписка Vitte</h1>
        <p className="text-sm text-white/80">
          Действует до:{" "}
          {data?.premium_until
            ? new Date(data.premium_until).toLocaleDateString("ru-RU")
            : "без ограничений"}
        </p>
      </div>
      <ul className="space-y-2 text-sm text-white/80">
        <li>• Безлимитные сообщения и приоритетные ответы.</li>
        <li>• Более умная и внимательная модель для диалогов.</li>
        <li>• Доступ к кастомному персонажу и эмоциональным сценам.</li>
      </ul>
      <Link
        to="/characters"
        className="inline-flex w-full items-center justify-center rounded-full border border-white/10 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/5"
      >
        Вернуться к персонажам
      </Link>
    </section>
  );

  const renderPlanSelector = () => (
    <div className="space-y-3">
      {plansLoading
        ? Array.from({ length: 4 }).map((_, index) => (
            <div
              key={`skeleton-${index}`}
              className="h-14 rounded-3xl border border-white/10 bg-white/5 animate-pulse"
            />
          ))
        : orderedPlans.map((plan) => {
            const isSelected = plan.code === activePlan?.code;
            return (
              <button
                key={plan.code}
                type="button"
                onClick={() => setSelectedPlan(plan.code)}
                className={`flex w-full items-start justify-between rounded-3xl border px-4 py-3 text-left transition min-h-[88px] ${
                  isSelected
                    ? "border-pink-400/60 bg-white/10"
                    : "border-white/10 bg-transparent hover:border-white/30"
                }`}
              >
                <div className="min-w-0 pr-3">
                  <p className="text-sm font-semibold text-white">{plan.title}</p>
                  <p className="text-xs text-white/60 leading-snug line-clamp-2">
                    {plan.description}
                  </p>
                </div>
                <div className="flex-shrink-0 text-right">
                  <p className="text-lg font-semibold text-white whitespace-nowrap">
                    {plan.price.toLocaleString("ru-RU")} ₽
                  </p>
                  <p className="text-[11px] uppercase text-white/50">
                    {plan.period === "day"
                      ? "3 дня"
                      : plan.period === "quarter"
                        ? "3 месяца"
                        : getPeriodLabel(plan.period)}
                  </p>
                </div>
              </button>
            );
          })}
      {plansError && (
        <p className="text-xs text-red-300">
          {plansError}. Используем рекомендации по умолчанию.
        </p>
      )}
    </div>
  );

  const renderPaywall = () => (
    <section className="space-y-5">
      <div className="rounded-4xl border border-white/10 bg-card-elevated/70 px-5 py-4 shadow-card">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/60">
          Бесплатный доступ
        </p>
        <p className="mt-2 text-sm text-white/80">
          Сегодня можно отправить до {data?.free_messages_limit ?? 15} бесплатных сообщений. Осталось{" "}
          <span className="font-semibold text-white">{remainingMessages}</span>.
        </p>
      </div>

      <div className="rounded-4xl border border-white/10 bg-card-elevated/85 px-5 py-6 shadow-card space-y-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Premium</h2>
          <p className="mt-1 text-sm text-white/70">
            Безлимитные сообщения, более внимательные и глубокие ответы, доступ к кастомному герою и
            эмоциональным сценам общения.
          </p>
        </div>

        {renderPlanSelector()}

        {submitError && <p className="text-sm text-red-300">{submitError}</p>}

        <button
          type="button"
          onClick={handlePay}
          disabled={!activePlan || submitting}
          className="w-full rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-4 text-base font-semibold text-white shadow-card transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Оформляем..." : "Оплатить"}
        </button>
        <button
          type="button"
          onClick={() => navigate("/characters")}
          className="w-full rounded-full border border-white/10 px-4 py-3 text-sm text-white/80 transition hover:bg-white/5"
        >
          Продолжить бесплатно
        </button>
        <Link
          to="/store"
          className="inline-flex w-full items-center justify-center rounded-full border border-white/10 bg-card-dark/80 px-4 py-4 text-base font-medium text-white/90 transition hover:bg-card-dark"
        >
          Магазин
        </Link>
      </div>
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

        {hasSubscription ? renderPremiumState() : renderPaywall()}
      </div>
    </div>
  );
}
