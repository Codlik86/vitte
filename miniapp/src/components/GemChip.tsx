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
        className="flex h-7 w-7 items-center justify-center rounded-full bg-white/15 text-white transition hover:bg-white/25 active:scale-95 disabled:opacity-60"
        aria-label="Открыть настройки"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
          <path
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543-.89 3.31.876 2.42 2.42a1.724 1.724 0 0 0 1.065 2.572c1.757.426 1.757 2.924 0 3.35a1.724 1.724 0 0 0-1.066 2.573c.89 1.543-.876 3.31-2.42 2.42a1.724 1.724 0 0 0-2.572 1.065c-.426 1.757-2.924 1.757-3.35 0a1.724 1.724 0 0 0-2.573-1.066c-1.543.89-3.31-.876-2.42-2.42a1.724 1.724 0 0 0-1.065-2.572c-1.757-.426-1.757-2.924 0-3.35a1.724 1.724 0 0 0 1.066-2.573c-.89-1.543.876-3.31 2.42-2.42.986.569 2.234.03 2.572-1.065Z"
            fill="currentColor"
          />
          <path
            d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
            fill="currentColor"
          />
        </svg>
      </button>
    </button>
  );
}
