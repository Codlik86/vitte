export const TELEGRAM_ID_ERROR_MESSAGE =
  "Не удалось определить Telegram ID. Добавь VITE_DEBUG_TELEGRAM_ID в .env для локального запуска.";

export function resolveTelegramId(): number | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const tg = window.Telegram?.WebApp;
  const webAppId = tg?.initDataUnsafe?.user?.id ?? tg?.initData?.user?.id;

  if (typeof webAppId === "number" && Number.isFinite(webAppId)) {
    return webAppId;
  }

  if (typeof webAppId === "string" && webAppId.trim() !== "") {
    const parsed = Number(webAppId);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
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

export async function requireTelegramId(timeoutMs = 8000): Promise<number> {
  const id = await waitTelegramId(timeoutMs);
  if (typeof id === "number" && Number.isFinite(id)) {
    return id;
  }
  throw new Error(TELEGRAM_ID_ERROR_MESSAGE);
}
