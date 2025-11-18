import type { PersonasListResponse, Persona } from "./types";

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

if (!BASE_URL) {
  console.warn("[Vitte] VITE_BACKEND_URL is not set");
}

const TELEGRAM_ID = 123456; // TODO: заменить на реальный ID из Telegram WebApp

export async function fetchPersonas(): Promise<PersonasListResponse> {
  const url = `${BASE_URL}/api/personas?telegram_id=${TELEGRAM_ID}`;
  console.log("[Vitte] fetchPersonas ->", url);
  const res = await fetch(url);
  if (!res.ok) {
    console.error("[Vitte] fetchPersonas error status", res.status, res.statusText);
    throw new Error("Не удалось загрузить персонажей");
  }
  return (await res.json()) as PersonasListResponse;
}

export async function fetchPersona(id: number): Promise<Persona> {
  const res = await fetch(
    `${BASE_URL}/api/personas/${id}?telegram_id=${TELEGRAM_ID}`
  );
  if (!res.ok) throw new Error("Не удалось загрузить персонажа");
  return (await res.json()) as Persona;
}

export async function selectPersona(id: number): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/api/personas/select?telegram_id=${TELEGRAM_ID}&persona_id=${id}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Не удалось выбрать персонажа");
}

export async function createCustomPersona(
  name: string,
  shortTitle: string,
  descriptionShort: string
): Promise<Persona> {
  const params = new URLSearchParams({
    telegram_id: String(TELEGRAM_ID),
    name,
    short_title: shortTitle,
    description_short: descriptionShort,
  });

  const res = await fetch(`${BASE_URL}/api/personas/custom?${params.toString()}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Не удалось создать персонажа");
  const json = await res.json();
  return json.persona as Persona;
}
