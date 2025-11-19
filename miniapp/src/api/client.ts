import type {
  PersonasListResponse,
  PersonaDetails,
  AccessStatusResponse,
} from "./types";
import { tg } from "../lib/telegram";

const BASE_URL = (import.meta.env.VITE_BACKEND_URL ?? "").replace(/\/$/, "");
const DEBUG_TELEGRAM_ID = Number(import.meta.env.VITE_DEBUG_TELEGRAM_ID ?? "0");

if (!BASE_URL) {
  console.warn("[Vitte] VITE_BACKEND_URL is not set");
}

function ensureTelegramId(): number {
  const idFromWebApp = tg?.initDataUnsafe?.user?.id;
  if (typeof idFromWebApp === "number" && idFromWebApp > 0) {
    return idFromWebApp;
  }
  if (DEBUG_TELEGRAM_ID > 0) {
    return DEBUG_TELEGRAM_ID;
  }
  throw new Error(
    "Не удалось определить Telegram ID. Добавь VITE_DEBUG_TELEGRAM_ID в .env для локального запуска."
  );
}

export async function fetchPersonas(): Promise<PersonasListResponse> {
  const telegramId = ensureTelegramId();
  const url = `${BASE_URL}/api/personas?telegram_id=${telegramId}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажей");
  }
  return (await res.json()) as PersonasListResponse;
}

export async function selectPersona(personaId: number): Promise<PersonaDetails> {
  const telegramId = ensureTelegramId();
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
  const telegramId = ensureTelegramId();
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
  const telegramId = ensureTelegramId();
  const res = await fetch(
    `${BASE_URL}/api/personas/${id}?telegram_id=${telegramId}`
  );
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажа");
  }
  return (await res.json()) as PersonaDetails;
}

export async function fetchAccessStatus(): Promise<AccessStatusResponse> {
  const telegramId = ensureTelegramId();
  const res = await fetch(
    `${BASE_URL}/api/access/status?telegram_id=${telegramId}`
  );
  if (!res.ok) {
    throw new Error("Не удалось загрузить статус доступа");
  }
  return (await res.json()) as AccessStatusResponse;
}
