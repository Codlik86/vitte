import { useNavigate } from "react-router-dom";
import { ImageChip } from "../ImageChip";

export type PageHeaderStats = {
  images: number | null;
  hasSubscription?: boolean;
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

  return (
    <header className="flex w-full flex-nowrap items-center gap-3">
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
        <div className="flex flex-shrink-0 justify-end">
          <ImageChip
            imagesRemaining={stats.images ?? null}
            hasSubscription={stats.hasSubscription}
            isPremium={stats.isPremium}
            onImagesClick={() => navigate("/store")}
            onBadgeClick={() => navigate("/paywall")}
            onSettingsClick={() => navigate("/settings")}
          />
        </div>
      ) : null}
    </header>
  );
}
