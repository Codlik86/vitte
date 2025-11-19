import { tg } from "./telegram";

const rawRealId = tg?.initDataUnsafe?.user?.id;
const realTelegramId = typeof rawRealId === "number" && rawRealId > 0 ? rawRealId : null;

const rawDebugId = import.meta.env.VITE_DEBUG_TELEGRAM_ID;
const debugTelegramId = rawDebugId ? Number(rawDebugId) : null;

const isDev = Boolean(import.meta.env.DEV);

export function getEffectiveTelegramId(): number {
  if (realTelegramId) {
    return realTelegramId;
  }
  if (debugTelegramId && Number.isFinite(debugTelegramId) && debugTelegramId > 0) {
    return debugTelegramId;
  }
  throw new Error(
    "Не удалось определить Telegram ID. Добавь VITE_DEBUG_TELEGRAM_ID в .env для локального запуска."
  );
}

export const telegramIdMeta = {
  isDev,
  hasRealTelegramId: Boolean(realTelegramId),
  hasDebugTelegramId: Boolean(debugTelegramId),
  shouldShowDebugAlert:
    (isDev || Boolean(debugTelegramId)) && !realTelegramId,
};
