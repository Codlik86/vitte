export const TELEGRAM_ID_ERROR_MESSAGE =
  "Для локального запуска без Telegram задай VITE_DEBUG_TELEGRAM_ID в .env.";
export const TELEGRAM_WEBAPP_RETRY_MESSAGE =
  "Не получилось получить данные, попробуй закрыть и открыть мини-приложение ещё раз.";

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

  // 1) явный query-параметр (удобно для отладки)
  const urlParamId = normalizeId(new URLSearchParams(window.location.search).get("telegram_id"));
  if (urlParamId !== undefined) {
    return urlParamId;
  }

  const tg = window.Telegram?.WebApp;
  const webAppId = normalizeId(
    tg?.initDataUnsafe?.user?.id ?? tg?.initData?.user?.id
  );
  if (webAppId !== undefined) {
    return webAppId;
  }

  // 2) попробуем распарсить initData как строку
  const initDataStr: string | null =
    typeof (tg as any)?.initData === "string" ? (tg as any).initData : null;
  if (initDataStr && initDataStr.length > 0) {
    try {
      const params = new URLSearchParams(initDataStr);
      const rawUser = params.get("user");
      if (rawUser) {
        const parsedUser = JSON.parse(rawUser);
        const parsedId = normalizeId(parsedUser?.id);
        if (parsedId !== undefined) {
          return parsedId;
        }
      }
    } catch {
      // ignore parse errors
    }
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

export function isTelegramWebApp(): boolean {
  return typeof window !== "undefined" && Boolean(window.Telegram?.WebApp);
}

export async function getTelegramIdOptional(timeoutMs = 8000): Promise<number | undefined> {
  return waitTelegramId(timeoutMs);
}

export async function requireTelegramId(timeoutMs = 8000): Promise<number> {
  const id = await waitTelegramId(timeoutMs);
  if (typeof id === "number" && Number.isFinite(id)) {
    return id;
  }
  if (isTelegramWebApp()) {
    throw new Error(TELEGRAM_WEBAPP_RETRY_MESSAGE);
  }
  const isProd = import.meta.env.MODE === "production" || import.meta.env.PROD;
  if (!isProd) {
    throw new Error(TELEGRAM_ID_ERROR_MESSAGE);
  }
  throw new Error(TELEGRAM_WEBAPP_RETRY_MESSAGE);
}
