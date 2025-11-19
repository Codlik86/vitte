import type { PersonasListResponse, PersonaDetails } from "./types";

const BASE_URL = import.meta.env.VITE_BACKEND_URL;
const TELEGRAM_ID = 53652078; // TODO: заменить на реальный ID из Telegram WebApp

if (!BASE_URL) {
  console.warn("[Vitte] VITE_BACKEND_URL is not set");
}

export async function fetchPersonas(): Promise<PersonasListResponse> {
  const url = `${BASE_URL}/api/personas?telegram_id=${TELEGRAM_ID}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажей");
  }
  return (await res.json()) as PersonasListResponse;
}

export async function selectPersona(personaId: number): Promise<PersonaDetails> {
  const res = await fetch(
    `${BASE_URL}/api/personas/${personaId}/select?telegram_id=${TELEGRAM_ID}`,
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
  const res = await fetch(`${BASE_URL}/api/personas/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      telegram_id: TELEGRAM_ID,
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
  const res = await fetch(
    `${BASE_URL}/api/personas/${id}?telegram_id=${TELEGRAM_ID}`
  );
  if (!res.ok) {
    throw new Error("Не удалось загрузить персонажа");
  }
  return (await res.json()) as PersonaDetails;
}
