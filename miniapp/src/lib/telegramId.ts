export function resolveTelegramId(): number | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const tg = window.Telegram?.WebApp;
  const webAppId =
    tg?.initDataUnsafe?.user?.id ??
    tg?.initData?.user?.id ??
    undefined;

  if (typeof webAppId === "number" && Number.isFinite(webAppId)) {
    return webAppId;
  }

  const debugEnv = import.meta.env.VITE_DEBUG_TELEGRAM_ID;
  const debugId =
    typeof debugEnv === "string" && debugEnv.trim() !== ""
      ? Number(debugEnv)
      : undefined;

  if (
    import.meta.env.DEV &&
    typeof debugId === "number" &&
    Number.isFinite(debugId)
  ) {
    return debugId;
  }

  return undefined;
}

export async function waitTelegramId(timeoutMs = 8000): Promise<number | undefined> {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const id = resolveTelegramId();
    if (typeof id === "number" && Number.isFinite(id)) {
      return id;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  return undefined;
}
