import type {
  PersonasListResponse,
  PersonaDetails,
  AccessStatusResponse,
  PaymentPlan,
  SubscribeResponse,
  StoreProductsResponse,
  ChatResponse,
  PersonaSelectResponse,
  FeatureStatusResponse,
  StoreBuyResponse,
} from "./types";
import { requireTelegramId } from "../lib/telegramId";

const BASE_URL = (import.meta.env.VITE_BACKEND_URL ?? "").replace(/\/$/, "");

if (!BASE_URL) {
  console.warn("[Vitte] VITE_BACKEND_URL is not set");
}

export async function fetchPersonas(): Promise<PersonasListResponse> {
  const telegramId = await requireTelegramId();
  const url = `${BASE_URL}/api/personas?telegram_id=${telegramId}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажей");
  }
  return (await res.json()) as PersonasListResponse;
}

export async function selectPersona(personaId: number): Promise<PersonaDetails> {
  const telegramId = await requireTelegramId();
  const res = await fetch(
    `${BASE_URL}/api/personas/${personaId}/select?telegram_id=${telegramId}`,
    {
      method: "POST",
    }
  );
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
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/personas/select_and_greet?telegram_id=${telegramId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/personas/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const telegramId = await requireTelegramId();
  const res = await fetch(
    `${BASE_URL}/api/personas/${id}?telegram_id=${telegramId}`
  );
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажа");
  }
  return (await res.json()) as PersonaDetails;
}

export async function fetchAccessStatus(): Promise<AccessStatusResponse> {
  const telegramId = await requireTelegramId();
  const res = await fetch(
    `${BASE_URL}/api/access/status?telegram_id=${telegramId}`
  );
  if (!res.ok) {
    throw new Error("Не удалось загрузить статус доступа");
  }
  return (await res.json()) as AccessStatusResponse;
}

export async function fetchPaymentPlans(): Promise<PaymentPlan[]> {
  const res = await fetch(`${BASE_URL}/api/payments/plans`);
  if (!res.ok) {
    throw new Error("Не удалось загрузить планы подписки");
  }
  return (await res.json()) as PaymentPlan[];
}

export async function subscribeToPlan(planCode: string, provider?: string): Promise<SubscribeResponse> {
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/payments/subscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      telegram_id: telegramId,
      plan_code: planCode,
      provider,
    }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || "Не удалось оформить подписку");
  }
  return (await res.json()) as SubscribeResponse;
}

export async function logAnalyticsEvent(eventType: string, payload?: Record<string, unknown>): Promise<void> {
  try {
    const telegramId = await requireTelegramId().catch(() => null);
    await fetch(`${BASE_URL}/api/analytics/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

export async function fetchStoreProducts(): Promise<StoreProductsResponse> {
  const res = await fetch(`${BASE_URL}/api/store/products`);
  if (!res.ok) {
    throw new Error("Не удалось загрузить магазин");
  }
  return (await res.json()) as StoreProductsResponse;
}

export async function purchaseProduct(productCode: string): Promise<StoreBuyResponse> {
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/store/buy/${productCode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      telegram_id: telegramId,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось оформить покупку");
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
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/features/status?telegram_id=${telegramId}`);
  if (!res.ok) {
    throw new Error("Не удалось загрузить статус улучшений");
  }
  return (await res.json()) as FeatureStatusResponse;
}

export async function toggleFeature(featureCode: string, enabled: boolean): Promise<FeatureStatusResponse> {
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/features/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const telegramId = await requireTelegramId();
  await fetch(`${BASE_URL}/api/features/clear-dialogs?telegram_id=${telegramId}`, {
    method: "POST",
  });
}

export async function clearLongMemory(): Promise<void> {
  const telegramId = await requireTelegramId();
  await fetch(`${BASE_URL}/api/features/clear-long-memory?telegram_id=${telegramId}`, {
    method: "POST",
  });
}

export async function deleteAccount(): Promise<void> {
  const telegramId = await requireTelegramId();
  await fetch(`${BASE_URL}/api/features/delete-account?telegram_id=${telegramId}`, {
    method: "POST",
  });
}
