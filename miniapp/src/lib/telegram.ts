type TelegramBackButton = {
  show: () => void;
  hide: () => void;
  onClick: (callback: () => void) => void;
  offClick?: (callback: () => void) => void;
};

type TelegramUser = {
  id?: number | string;
};

type TelegramInitData = {
  user?: TelegramUser;
};

type TelegramWebApp = {
  ready: () => void;
  BackButton: TelegramBackButton;
  initDataUnsafe?: TelegramInitData;
  initData?: TelegramInitData;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

let isReadyCalled = false;

function resolveTelegramWebApp(): TelegramWebApp | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  const instance = window.Telegram?.WebApp;
  if (instance && !isReadyCalled) {
    try {
      instance.ready();
    } catch {
      // ignore init errors, telegram may not be available locally
    }
    isReadyCalled = true;
  }
  return instance;
}

export const tg = resolveTelegramWebApp();
