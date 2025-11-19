import { useEffect, useState } from "react";
import {
  TELEGRAM_ID_ERROR_MESSAGE,
  waitTelegramId,
} from "../lib/telegramId";

export function DebugTelegramBanner() {
  const [shouldShow, setShouldShow] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function checkTelegram() {
      const hasDebugEnv = Boolean(import.meta.env.VITE_DEBUG_TELEGRAM_ID);
      if (!import.meta.env.DEV || hasDebugEnv) {
        return;
      }

      const id = await waitTelegramId(2000);
      if (!cancelled) {
        setShouldShow(!id);
      }
    }

    checkTelegram();

    return () => {
      cancelled = true;
    };
  }, []);

  if (!import.meta.env.DEV || !shouldShow) {
    return null;
  }

  return (
    <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
      {TELEGRAM_ID_ERROR_MESSAGE}
    </div>
  );
}
