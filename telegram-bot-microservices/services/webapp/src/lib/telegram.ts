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
  start_param?: string;
};

type InvoiceStatus = "paid" | "cancelled" | "failed" | "pending";

type TelegramWebApp = {
  ready: () => void;
  expand?: () => void;
  BackButton: TelegramBackButton;
  initDataUnsafe?: TelegramInitData;
  initData?: TelegramInitData;
  openTelegramLink?: (url: string) => void;
  openInvoice?: (url: string, callback?: (status: InvoiceStatus) => void) => void;
  close?: () => void;
};

export type { InvoiceStatus };

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
      instance.expand?.();
    } catch {
      // ignore init errors, telegram may not be available locally
    }
    isReadyCalled = true;
  }
  return instance;
}

export const tg = resolveTelegramWebApp();
