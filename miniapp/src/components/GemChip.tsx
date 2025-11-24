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
      className={`inline-flex min-h-10 min-w-[200px] flex-shrink-0 items-center gap-2 rounded-full bg-gradient-to-r from-[#2D1747] via-[#5C2D83] to-[#D64CC1] px-4 py-1.5 text-white shadow-card transition hover:opacity-95 active:scale-95 disabled:opacity-60 ${className}`}
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
        className="flex h-9 w-9 items-center justify-center rounded-full bg-white/18 text-white transition hover:bg-white/28 active:scale-95 disabled:opacity-60"
        aria-label="Открыть настройки"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5">
          <path
            d="M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M20 12.93v-1.86a1 1 0 0 0-.68-.95l-1.24-.42a6.5 6.5 0 0 0-.54-1.29l.53-1.22a1 1 0 0 0-.18-1.07l-1.31-1.3a1 1 0 0 0-1.06-.19l-1.22.53a6.5 6.5 0 0 0-1.3-.54L12.88 4a1 1 0 0 0-.95-.68h-1.86a1 1 0 0 0-.95.68l-.42 1.24c-.45.13-.88.3-1.3.54l-1.22-.53a1 1 0 0 0-1.07.18l-1.3 1.31a1 1 0 0 0-.19 1.06l.53 1.22c-.23.42-.41.85-.54 1.3L4 11.07a1 1 0 0 0-.68.95v1.86a1 1 0 0 0 .68.95l1.24.42c.13.45.3.88.54 1.3l-.53 1.22a1 1 0 0 0 .18 1.07l1.31 1.3a1 1 0 0 0 1.06.19l1.22-.53c.42.23.85.41 1.3.54L11.07 20a1 1 0 0 0 .95.68h1.86a1 1 0 0 0 .95-.68l.42-1.24c.45-.13.88-.3 1.3-.54l1.22.53a1 1 0 0 0 1.07-.18l1.3-1.31a1 1 0 0 0 .19-1.06l-.53-1.22c.23-.42.41-.85.54-1.3l1.24-.42a1 1 0 0 0 .68-.95Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </button>
  );
}
