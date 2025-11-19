import { tg } from "./telegram";

const rawRealId = tg?.initDataUnsafe?.user?.id;
const realTelegramId =
  typeof rawRealId === "number" && rawRealId > 0 ? rawRealId : null;

const rawDebugId = import.meta.env.VITE_DEBUG_TELEGRAM_ID;
let debugTelegramId: number | null = null;
if (rawDebugId) {
  const numericId = Number(rawDebugId);
  if (Number.isFinite(numericId) && numericId > 0) {
    debugTelegramId = numericId;
  }
}

const isDev = import.meta.env.DEV === true;
const effectiveTelegramId = realTelegramId ?? debugTelegramId ?? null;

export function getEffectiveTelegramId(): number {
  if (effectiveTelegramId !== null) {
    return effectiveTelegramId;
  }
  throw new Error(
    "Не удалось определить Telegram ID. Добавь VITE_DEBUG_TELEGRAM_ID в .env для локального запуска."
  );
}

export const telegramIdMeta = {
  isDev,
  hasRealTelegramId: Boolean(realTelegramId),
  hasDebugTelegramId: Boolean(debugTelegramId),
  effectiveTelegramId,
  shouldShowDebugAlert: isDev && effectiveTelegramId === null,
};
