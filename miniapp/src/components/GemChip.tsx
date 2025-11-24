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
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <button
        type="button"
        onClick={onPrimaryClick}
        disabled={!onPrimaryClick}
        className="inline-flex min-h-10 min-w-[180px] flex-shrink-0 items-center gap-2 rounded-full bg-gradient-to-r from-[#2D1747] via-[#5C2D83] to-[#D64CC1] px-4 py-1.5 text-white shadow-card transition hover:opacity-95 active:scale-95 disabled:opacity-60"
      >
        <span className="flex flex-1 items-center justify-start gap-1 whitespace-nowrap text-sm font-semibold text-white/90 tabular-nums">
          <span aria-hidden>💎</span>
          <span>{displayGems}</span>
        </span>
        <span className="rounded-full bg-white/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-white/90">
          {labelText}
        </span>
      </button>
      <button
        type="button"
        onClick={onSettingsClick}
        disabled={!onSettingsClick}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-white transition hover:bg-white/25 active:scale-95 disabled:opacity-60"
        aria-label="Открыть настройки"
      >
        <span aria-hidden>⚙</span>
      </button>
    </div>
  );
}
