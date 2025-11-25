export const TELEGRAM_ID_ERROR_MESSAGE =
  "Не удалось определить Telegram ID. Добавь VITE_DEBUG_TELEGRAM_ID в .env для локального запуска.";

const DEBUG_ENV_KEYS = ["VITE_DEBUG_TELEGRAM_ID", "VITTE_DEBUG_TELEGRAM_ID", "VITE_DEBUG_ID"];

function normalizeId(id: unknown): number | undefined {
  if (typeof id === "number") {
    return Number.isFinite(id) ? id : undefined;
  }
  if (typeof id === "string" && id.trim() !== "") {
    const parsed = Number(id);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

export function resolveTelegramId(): number | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const tg = window.Telegram?.WebApp;
  const webAppId = normalizeId(
    tg?.initDataUnsafe?.user?.id ?? tg?.initData?.user?.id
  );
  if (webAppId !== undefined) {
    return webAppId;
  }

  if (import.meta.env.DEV) {
    for (const key of DEBUG_ENV_KEYS) {
      const candidate = normalizeId((import.meta.env as any)?.[key]);
      if (candidate !== undefined) {
        return candidate;
      }
    }
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
