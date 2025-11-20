import { useRef } from "react";

type GemChipProps = {
  gems: number | null;
  usedMessages: number | null;
  totalMessages: number | null;
  hasUnlimited?: boolean;
  onPlusClick?: () => void;
  className?: string;
};

function useStableNumber(value: number | null) {
  const ref = useRef<number | null>(null);
  if (typeof value === "number" && Number.isFinite(value)) {
    ref.current = value;
  }
  return ref.current;
}

function useStableBoolean(value: boolean | undefined) {
  const ref = useRef<boolean | null>(null);
  if (typeof value === "boolean") {
    ref.current = value;
  }
  return ref.current;
}

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
  const stableGems = useStableNumber(gems);
  const stableUsed = useStableNumber(usedMessages);
  const stableTotal = useStableNumber(totalMessages);
  const stableUnlimited = useStableBoolean(hasUnlimited);

  const resolvedGems = stableGems ?? gems;
  const resolvedUsed = stableUsed ?? usedMessages;
  const resolvedTotal = stableTotal ?? totalMessages;
  const resolvedUnlimited = (stableUnlimited ?? hasUnlimited) === true;

  const displayGems = formatCounter(resolvedGems ?? null);
  const displayMessages = resolvedUnlimited
    ? "∞"
    : `${formatCounter(resolvedUsed ?? null)}/${formatCounter(resolvedTotal ?? null)}`;

  return (
    <div
      className={`inline-flex min-h-10 min-w-[140px] flex-shrink-0 items-center gap-2 rounded-full bg-gradient-to-r from-[#2D1747] via-[#5C2D83] to-[#D64CC1] px-4 py-1.5 shadow-card sm:min-w-[160px] ${className}`}
    >
      <div className="flex flex-1 items-center justify-between gap-0.5 whitespace-nowrap text-sm font-semibold text-white/90 tabular-nums">
        <span className="flex items-center gap-0.5">
          <span aria-hidden>💎</span>
          <span>{displayGems}</span>
        </span>
        <span className="flex min-w-[58px] items-center justify-end gap-0.5">
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
        <svg
          viewBox="0 0 24 24"
          aria-hidden="true"
          className="h-[18px] w-[18px] text-white"
        >
          <path
            d="M12 5v14M5 12h14"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}
