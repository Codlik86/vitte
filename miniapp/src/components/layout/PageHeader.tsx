import { useNavigate } from "react-router-dom";
import { GemChip } from "../GemChip";

export type PageHeaderStats = {
  gems: number | null;
  usedMessages: number | null;
  limitMessages: number | null;
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
      {stats ? (
        <GemChip
          gems={stats.gems ?? null}
          usedMessages={stats.usedMessages ?? null}
          totalMessages={stats.limitMessages ?? null}
          hasUnlimited={stats.hasUnlimited}
          onPlusClick={() => navigate("/paywall")}
        />
      ) : null}
    </header>
  );
}
