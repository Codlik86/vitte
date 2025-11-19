import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

export type PageHeaderStats = {
  gems: number;
  usedMessages?: number;
  limitMessages?: number;
  hasUnlimited?: boolean;
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

  return (
    <header className="flex w-full items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3">
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
      <StatsChip stats={stats} />
    </header>
  );
}

type StatsChipProps = {
  stats?: PageHeaderStats;
};

function StatsChip({ stats }: StatsChipProps) {
  const navigate = useNavigate();
  const gems = stats?.gems ?? 0;
  const used = stats?.usedMessages;
  const limit = stats?.limitMessages;
  const hasUnlimited = stats?.hasUnlimited === true;
  const hasCounters = used !== undefined && limit !== undefined;

  let content: ReactNode;
  if (hasUnlimited) {
    content = (
      <span className="text-sm font-semibold text-white">
        💎 {gems}
      </span>
    );
  } else if (hasCounters) {
    content = (
      <span className="text-sm font-semibold text-white">
        💎 {gems} 💬 {used}/{limit}
      </span>
    );
  } else {
    content = <div className="h-4 w-24 animate-pulse rounded-full bg-white/40" />;
  }

  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#2D1747] via-[#5C2D83] to-[#D64CC1] px-4 py-1 shadow-card">
      {content}
      <button
        type="button"
        onClick={() => navigate("/paywall")}
        className="flex h-7 w-7 items-center justify-center rounded-full bg-white/15 text-white transition hover:bg-white/25 active:scale-95"
        aria-label="Открыть экран подписки"
      >
        <span className="text-lg leading-none">+</span>
      </button>
    </div>
  );
}
