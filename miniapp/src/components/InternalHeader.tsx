import type { AccessStatusResponse } from "../api/types";
import { MessageLimitChip } from "./MessageLimitChip";

type InternalHeaderProps = {
  onBack: () => void;
  showCounter?: boolean;
  status?: AccessStatusResponse | null;
  loading?: boolean;
  error?: string | null;
};

export function InternalHeader({
  onBack,
  showCounter = true,
  status,
  loading,
  error,
}: InternalHeaderProps) {
  return (
    <div className="mb-6 flex items-center justify-between gap-4">
      <button
        type="button"
        onClick={onBack}
        className="flex h-11 w-11 items-center justify-center rounded-full bg-[#151826] text-white shadow-card transition active:scale-95"
        aria-label="Назад"
      >
        <span className="text-xl leading-none">←</span>
      </button>

      {showCounter && (
        <div className="flex flex-1 justify-end">
          <MessageLimitChip
            align="end"
            status={status}
            loading={loading}
            error={error}
          />
        </div>
      )}
    </div>
  );
}
