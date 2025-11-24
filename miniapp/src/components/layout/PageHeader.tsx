import { useNavigate } from "react-router-dom";
import { GemChip } from "../GemChip";

export type PageHeaderStats = {
  gems: number | null;
  usedMessages: number | null;
  limitMessages: number | null;
  hasUnlimited?: boolean;
  isPremium?: boolean;
};

type PageHeaderProps = {
  title: string;
  showBack?: boolean;
  onBack?: () => void;
  stats?: PageHeaderStats;
};

export function PageHeader({
  title,
  showBack = false,
  onBack,
  stats,
}: PageHeaderProps) {
  const navigate = useNavigate();
  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  const remainingMessages =
    stats?.limitMessages != null && stats?.usedMessages != null
      ? Math.max(stats.limitMessages - stats.usedMessages, 0)
      : null;
  const premiumLabel = stats?.isPremium
    ? "Premium"
    : remainingMessages != null
    ? `Осталось ${remainingMessages} сообщений`
    : "Осталось сообщений";

  return (
    <header className="flex w-full flex-wrap items-center gap-3 min-[420px]:flex-nowrap">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {showBack && (
          <button
            type="button"
            onClick={handleBack}
            className="inline-flex items-center text-2xl font-medium text-white/80 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
            aria-label="Назад"
          >
            <span className="leading-none">←</span>
          </button>
        )}
        <h1 className="truncate text-2xl font-semibold text-white">{title}</h1>
      </div>
      {stats ? (
        <div className="w-full min-[420px]:w-auto min-[420px]:justify-end flex flex-wrap items-center justify-start gap-2">
          <GemChip
            gems={stats.gems ?? null}
            usedMessages={stats.usedMessages ?? null}
            totalMessages={stats.limitMessages ?? null}
            hasUnlimited={stats.hasUnlimited}
            isPremium={stats.isPremium}
            hidePlus
            showMessages={false}
          />
          <button
            type="button"
            onClick={() => navigate("/paywall")}
            className="inline-flex min-h-10 min-w-[140px] flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-[#2c1a52] via-[#5a2b80] to-[#c23ba7] px-4 py-1.5 text-sm font-semibold text-white shadow-card transition hover:opacity-95 active:scale-95"
          >
            {premiumLabel}
          </button>
          <button
            type="button"
            onClick={() => navigate("/settings")}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-white transition hover:bg-white/25 active:scale-95"
            aria-label="Настройки"
          >
            <span aria-hidden>⚙</span>
          </button>
        </div>
      ) : null}
    </header>
  );
}
