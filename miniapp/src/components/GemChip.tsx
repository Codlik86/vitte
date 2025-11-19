type GemChipProps = {
  gems: number | null;
  usedMessages: number | null;
  totalMessages: number | null;
  hasUnlimited?: boolean;
  onPlusClick?: () => void;
  className?: string;
};

function formatCounter(value: number | null): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return "–";
}

export function GemChip({
  gems,
  usedMessages,
  totalMessages,
  hasUnlimited = false,
  onPlusClick,
  className = "",
}: GemChipProps) {
  const displayGems = formatCounter(gems);
  const displayMessages = hasUnlimited
    ? "∞"
    : `${formatCounter(usedMessages)}/${formatCounter(totalMessages)}`;

  return (
    <div
      className={`inline-flex min-h-10 min-w-[170px] items-center gap-3 rounded-full bg-gradient-to-r from-[#2D1747] via-[#5C2D83] to-[#D64CC1] px-4 py-1.5 shadow-card ${className}`}
    >
      <div className="flex flex-1 items-center justify-between gap-3 whitespace-nowrap text-sm font-semibold text-white/90 tabular-nums">
        <span className="flex items-center gap-1">
          <span aria-hidden>💎</span>
          <span>{displayGems}</span>
        </span>
        <span className="flex items-center gap-1">
          <span aria-hidden>💬</span>
          <span>{displayMessages}</span>
        </span>
      </div>
      <button
        type="button"
        onClick={onPlusClick}
        className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20 text-white transition hover:bg-white/30 active:scale-95 disabled:opacity-50"
        aria-label="Открыть экран подписки"
        disabled={!onPlusClick}
      >
        <span className="text-lg leading-none">+</span>
      </button>
    </div>
  );
}
