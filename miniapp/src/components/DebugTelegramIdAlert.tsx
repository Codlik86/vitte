import { telegramIdMeta } from "../lib/telegramId";

export function DebugTelegramIdAlert() {
  if (!telegramIdMeta.shouldShowDebugAlert) {
    return null;
  }

  return (
    <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
      Не удалось определить Telegram ID. Добавь VITE_DEBUG_TELEGRAM_ID в .env для локального запуска.
    </div>
  );
}
