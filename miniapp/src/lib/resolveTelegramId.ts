import { tg } from "./telegram";

export function resolveTelegramId(): number | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const webAppId =
    tg?.initDataUnsafe?.user?.id ??
    tg?.initData?.user?.id ??
    undefined;

  const debugEnv = import.meta.env.VITE_DEBUG_TELEGRAM_ID;
  const debugId =
    typeof debugEnv === "string" && debugEnv.trim() !== ""
      ? Number(debugEnv)
      : undefined;

  const id = webAppId ?? debugId;
  if (typeof id === "number" && Number.isFinite(id) && id > 0) {
    if (import.meta.env.DEV) {
      console.log("[resolveTelegramId]", {
        webAppId,
        debugId,
        result: id,
      });
    }
    return id;
  }

  if (import.meta.env.DEV) {
    console.log("[resolveTelegramId]", {
      webAppId,
      debugId,
      result: undefined,
    });
  }

  return undefined;
}
