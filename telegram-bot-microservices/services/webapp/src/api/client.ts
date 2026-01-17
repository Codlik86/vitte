import type {
  PersonasListResponse,
  PersonaDetails,
  AccessStatusResponse,
  ChatResponse,
  PersonaSelectResponse,
  FeatureStatusResponse,
  StoreBuyResponse,
  StoreConfig,
  StoreStatus,
} from "./types";
import { getTelegramIdOptional } from "../lib/telegramId";

const BASE_URL = (import.meta.env.VITE_BACKEND_URL ?? "").replace(/\/$/, "");

if (!BASE_URL) {
  console.warn("[Vitte] VITE_BACKEND_URL is not set");
}

function buildInitDataString(): string | null {
  if (typeof window === "undefined") return null;
  const webApp = (window as any).Telegram?.WebApp;
  const raw = webApp?.initData;
  if (typeof raw === "string" && raw.length > 0) {
    return raw;
  }
  return null;
}

function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...(extra || {}) };
  const initData = buildInitDataString();
  if (initData) {
    headers["X-Telegram-Web-App-Init-Data"] = initData;
  }
  return headers;
}

function buildUrlWithTelegramId(path: string, telegramId?: number | null): string {
  if (telegramId) {
    const delimiter = path.includes("?") ? "&" : "?";
    return `${path}${delimiter}telegram_id=${telegramId}`;
  }
  return path;
}

export async function fetchPersonas(): Promise<PersonasListResponse> {
  const telegramId = await getTelegramIdOptional();
  if (import.meta.env.VITE_DEBUG_MINIAPP === "1") {
    console.info("[Vitte][DEBUG_MINIAPP][api] fetchPersonas telegramId=", telegramId, "base", BASE_URL);
  }
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/personas`, telegramId);
  const res = await fetch(url, { headers: buildHeaders() });
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажей");
  }
  return (await res.json()) as PersonasListResponse;
}

export async function selectPersona(personaId: number): Promise<PersonaDetails> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(
    `${BASE_URL}/api/personas/${personaId}/select`,
    telegramId
  );
  const res = await fetch(url, {
    method: "POST",
    headers: buildHeaders(),
  });
  if (!res.ok) {
    throw new Error("Не удалось выбрать персонажа");
  }
  return (await res.json()) as PersonaDetails;
}

export async function selectPersonaAndGreet({
  personaId,
  extraDescription,
  sendGreeting = true,
  atmosphere,
  storyId,
  settingsChanged = false,
}: {
  personaId: number;
  extraDescription?: string | null;
  sendGreeting?: boolean;
  atmosphere?: string | null;
  storyId?: string | null;
  settingsChanged?: boolean;
}): Promise<PersonaSelectResponse> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/personas/select_and_greet`, telegramId);
  const res = await fetch(url, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      persona_id: personaId,
      extra_description: extraDescription ?? undefined,
      send_greeting: sendGreeting,
      atmosphere: atmosphere ?? undefined,
      story_id: storyId ?? undefined,
      settings_changed: settingsChanged,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось выбрать персонажа");
  }
  return (await res.json()) as PersonaSelectResponse;
}

export async function createCustomPersona(payload: {
  name: string;
  short_description: string;
  vibe?: string;
  replace_existing?: boolean;
}): Promise<PersonaDetails> {
  const telegramId = await getTelegramIdOptional();
  const res = await fetch(`${BASE_URL}/api/personas/custom`, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      telegram_id: telegramId,
      name: payload.name,
      short_description: payload.short_description,
      vibe: payload.vibe ?? "",
      replace_existing: Boolean(payload.replace_existing),
    }),
  });
  if (!res.ok) {
    const contentType = res.headers.get("Content-Type") || "";
    if (contentType.includes("application/json")) {
      const data = await res.json();
      throw new Error(data.detail || "Не удалось создать персонажа");
    }
    const text = await res.text();
    throw new Error(text || "Не удалось создать персонажа");
  }
  return (await res.json()) as PersonaDetails;
}

export async function fetchPersona(id: number): Promise<PersonaDetails> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/personas/${id}`, telegramId);
  const res = await fetch(url, { headers: buildHeaders() });
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажа");
  }
  return (await res.json()) as PersonaDetails;
}

export async function fetchAccessStatus(): Promise<AccessStatusResponse> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/access/status`, telegramId);
  const res = await fetch(url, { headers: buildHeaders() });
  if (!res.ok) {
    throw new Error("Не удалось загрузить статус доступа");
  }
  return (await res.json()) as AccessStatusResponse;
}

export async function triggerBotPay(): Promise<void> {
  const telegramId = await getTelegramIdOptional();
  const res = await fetch(`${BASE_URL}/api/bot/pay_from_miniapp`, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ telegram_id: telegramId }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось открыть оплату");
  }
}

export async function logAnalyticsEvent(eventType: string, payload?: Record<string, unknown>): Promise<void> {
  try {
    const telegramId = await getTelegramIdOptional();
    await fetch(`${BASE_URL}/api/analytics/events`, {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        telegram_id: telegramId ?? undefined,
        event_type: eventType,
        payload,
      }),
    });
  } catch (error) {
    console.warn("[Vitte] Failed to log analytics event", error);
  }
}

export async function logMiniAppOpen(startParam?: string | null): Promise<void> {
  try {
    const body: Record<string, unknown> = {};
    if (startParam) {
      body.start_param = startParam;
    }
    await fetch(`${BASE_URL}/api/events/miniapp_open`, {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
  } catch (error) {
    console.warn("[Vitte] Failed to log miniapp open", error);
  }
}

export async function fetchStoreConfig(): Promise<StoreConfig> {
  const res = await fetch(`${BASE_URL}/api/store/config`, { headers: buildHeaders() });
  if (!res.ok) {
    throw new Error("Не удалось загрузить конфигурацию магазина");
  }
  return (await res.json()) as StoreConfig;
}

export async function fetchStoreStatus(): Promise<StoreStatus> {
  const telegramId = await getTelegramIdOptional();
  if (telegramId === undefined) {
    if (import.meta.env.VITE_DEBUG_MINIAPP === "1") {
      console.info("[Vitte][DEBUG_MINIAPP][api] fetchStoreStatus skipped: no telegramId");
    }
    throw new Error("Не удалось определить Telegram ID");
  }
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/store/status`, telegramId);
  if (import.meta.env.VITE_DEBUG_MINIAPP === "1") {
    console.info("[Vitte][DEBUG_MINIAPP][api] fetchStoreStatus url=", url, "base", BASE_URL);
  }
  const res = await fetch(url, { headers: buildHeaders() });
  if (!res.ok) {
    throw new Error("Не удалось загрузить статус магазина");
  }
  return (await res.json()) as StoreStatus;
}

export async function buySubscription(planCode: string): Promise<StoreBuyResponse> {
  const telegramId = await getTelegramIdOptional();
  const res = await fetch(`${BASE_URL}/api/store/buy/subscription/${planCode}`, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ telegram_id: telegramId }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось оформить подписку");
  }
  return (await res.json()) as StoreBuyResponse;
}

export async function buyImagePack(packCode: string): Promise<StoreBuyResponse> {
  const telegramId = await getTelegramIdOptional();
  const res = await fetch(`${BASE_URL}/api/store/buy/image_pack/${packCode}`, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ telegram_id: telegramId }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось купить пакет изображений");
  }
  return (await res.json()) as StoreBuyResponse;
}

export async function buyFeature(featureCode: string): Promise<StoreBuyResponse> {
  const telegramId = await getTelegramIdOptional();
  const res = await fetch(`${BASE_URL}/api/store/buy/feature/${featureCode}`, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ telegram_id: telegramId }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось разблокировать улучшение");
  }
  return (await res.json()) as StoreBuyResponse;
}

export async function sendChatMessage(payload: {
  message: string;
  mode?: string;
  atmosphere?: string;
  story_id?: string;
  persona_id?: number;
}): Promise<ChatResponse> {
  const telegramId = await getTelegramIdOptional();
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      telegram_id: telegramId,
      message: payload.message,
      mode: payload.mode ?? "default",
      atmosphere: payload.atmosphere,
      story_id: payload.story_id,
      persona_id: payload.persona_id,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось отправить сообщение");
  }
  return (await res.json()) as ChatResponse;
}

export async function fetchFeaturesStatus(): Promise<FeatureStatusResponse> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/features/status`, telegramId);
  const res = await fetch(url, { headers: buildHeaders() });
  if (!res.ok) {
    throw new Error("Не удалось загрузить статус улучшений");
  }
  return (await res.json()) as FeatureStatusResponse;
}

export async function toggleFeature(featureCode: string, enabled: boolean): Promise<FeatureStatusResponse> {
  const telegramId = await getTelegramIdOptional();
  const res = await fetch(`${BASE_URL}/api/features/toggle`, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      telegram_id: telegramId,
      feature_code: featureCode,
      enabled,
    }),
  });
  if (!res.ok) {
    throw new Error("Не удалось обновить настройку");
  }
  const data = await res.json();
  return { features: [data.feature] };
}

export async function clearDialogs(): Promise<void> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/features/clear-dialogs`, telegramId);
  await fetch(url, {
    method: "POST",
    headers: buildHeaders(),
  });
}

export async function clearLongMemory(): Promise<void> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/features/clear-long-memory`, telegramId);
  await fetch(url, {
    method: "POST",
    headers: buildHeaders(),
  });
}

export async function deleteAccount(): Promise<void> {
  const telegramId = await getTelegramIdOptional();
  const url = buildUrlWithTelegramId(`${BASE_URL}/api/features/delete-account`, telegramId);
  await fetch(url, {
    method: "POST",
    headers: buildHeaders(),
  });
}
