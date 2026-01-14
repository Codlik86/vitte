import { useEffect, useRef } from "react";
import { tg } from "../lib/telegram";
import { logMiniAppOpen } from "../api/client";

export function useTrackMiniAppOpen(): void {
  const trackedRef = useRef(false);

  useEffect(() => {
    if (trackedRef.current) return;
    trackedRef.current = true;

    const startParam = tg?.initDataUnsafe?.start_param ?? null;

    logMiniAppOpen(startParam).catch(() => {
      // тихо игнорируем ошибки логирования, чтобы не ломать UX
    });
  }, []);
}
