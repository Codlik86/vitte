import type { AccessStatusResponse } from "../api/types";
import { useAccessStatus } from "../hooks/useAccessStatus";

type MessageLimitChipProps = {
  align?: "start" | "center" | "end";
  className?: string;
  status?: AccessStatusResponse | null;
  loading?: boolean;
  error?: string | null;
};

export function MessageLimitChip({
  align = "center",
  className = "",
  status,
  loading: providedLoading,
  error: providedError,
}: MessageLimitChipProps) {
  const shouldSelfLoad =
    status === undefined && providedLoading === undefined && providedError === undefined;
  const { data, loading, error } = useAccessStatus(shouldSelfLoad);

  const chipData = shouldSelfLoad ? data : status ?? null;
  const chipLoading = shouldSelfLoad ? loading : providedLoading ?? false;
  const chipError = shouldSelfLoad ? error : providedError ?? null;

  const limit = chipData?.free_messages_limit ?? 15;
  const used = chipData?.free_messages_used ?? 0;
  const alignClass =
    align === "end"
      ? "justify-end"
      : align === "start"
        ? "justify-start"
        : "justify-center";

  if (chipError && !chipData && !chipLoading) {
    return null;
  }

  return (
    <div className={`flex ${alignClass} ${className}`}>
      <div className="inline-flex items-center gap-3 rounded-full bg-gradient-to-r from-[#2D1747] via-[#5C2D83] to-[#D64CC1] px-4 py-2 shadow-card">
        <span className="text-lg leading-none drop-shadow">💎</span>
        {chipLoading ? (
          <div className="h-3 w-28 rounded-full bg-white/50 animate-pulse" />
        ) : (
          <span className="text-[11px] font-semibold uppercase tracking-[0.25em] text-white">
            {used} 💎 {used} / {limit} сообщений
          </span>
        )}
      </div>
    </div>
  );
}
