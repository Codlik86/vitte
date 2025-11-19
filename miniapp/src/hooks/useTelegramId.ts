import { useMemo } from "react";
import { resolveTelegramId } from "../lib/resolveTelegramId";

export function useTelegramId() {
  const telegramId = useMemo(() => resolveTelegramId(), []);
  return telegramId;
}
