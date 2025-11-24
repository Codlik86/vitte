import { useRef } from "react";

type GemChipProps = {
  gems: number | null;
  usedMessages: number | null;
  totalMessages: number | null;
  hasUnlimited?: boolean;
  isPremium?: boolean;
  onPrimaryClick?: () => void;
  onSettingsClick?: () => void;
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
  isPremium = false,
  onPrimaryClick,
  onSettingsClick,
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
  const remaining =
    resolvedUnlimited || isPremium
      ? "∞"
      : resolvedUsed != null && resolvedTotal != null
      ? Math.max(resolvedTotal - resolvedUsed, 0)
      : null;
  const labelText = isPremium
    ? "Premium"
    : remaining != null
    ? `Осталось ${remaining}`
    : "Осталось сообщений";

  return (
    <button
      type="button"
      onClick={onPrimaryClick}
      disabled={!onPrimaryClick}
      className={`inline-flex min-h-9 min-w-[200px] flex-shrink-0 items-center gap-2 rounded-full bg-gradient-to-r from-[#2D1747] via-[#5C2D83] to-[#D64CC1] px-4 py-1 text-white shadow-card transition hover:opacity-95 active:scale-95 disabled:opacity-60 ${className}`}
    >
      <span className="flex flex-1 items-center justify-start gap-1 whitespace-nowrap text-sm font-semibold text-white/90 tabular-nums">
        <span aria-hidden>💎</span>
        <span>{displayGems}</span>
      </span>
      <span className="rounded-full bg-white/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-white/90">
        {labelText}
      </span>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onSettingsClick?.();
        }}
        disabled={!onSettingsClick}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-white/18 text-white transition hover:bg-white/28 active:scale-95 disabled:opacity-60"
        aria-label="Открыть настройки"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 shrink-0">
          <path
            d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          />
          <path
            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 19.4a1.65 1.65 0 0 0-1.5 1V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1-1.5H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 8a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1.5-1V3a2 2 0 1 1 4 0v.09A1.65 1.65 0 0 0 15 4.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.69 0 1.3.41 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </button>
  );
}
