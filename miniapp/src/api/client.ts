import type {
  PersonasListResponse,
  PersonaDetails,
  AccessStatusResponse,
  PaymentPlan,
  SubscribeResponse,
  StoreProductsResponse,
  StorePurchaseResponse,
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

export async function createCustomPersona(payload: {
  name: string;
  short_description: string;
  vibe?: string;
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
    }),
  });
  if (!res.ok) {
    throw new Error("Не удалось создать персонажа");
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

export async function purchaseProduct(productCode: string): Promise<StorePurchaseResponse> {
  const telegramId = await requireTelegramId();
  const res = await fetch(`${BASE_URL}/api/store/purchase`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      telegram_id: telegramId,
      product_code: productCode,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Не удалось оформить покупку");
  }
  return (await res.json()) as StorePurchaseResponse;
}
