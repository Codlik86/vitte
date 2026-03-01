import { pub } from "./pub";

const AVATARS: Record<string, { card: string; chat: string }> = {
  // Russian names
  "лина": { card: pub("personas/lina-card.png"), chat: pub("personas/lina-chat.png") },
  "марианна": { card: pub("personas/marianna-card.png"), chat: pub("personas/marianna-chat.png") },
  "аки": { card: pub("personas/aki-card.jpg"), chat: pub("personas/aki-chat.jpg") },
  "мей": { card: pub("personas/mei-card.png"), chat: pub("personas/mei-chat.png") },
  "стейси": { card: pub("personas/stacey-card.jpg"), chat: pub("personas/stacey-chat.jpg") },
  "тая": { card: pub("personas/taya-card.png"), chat: pub("personas/taya-chat.png") },
  "джули": { card: pub("personas/julie-card.png"), chat: pub("personas/julie-chat.png") },
  "эш": { card: pub("personas/ash-card.png"), chat: pub("personas/ash-chat.png") },
  "юна": { card: pub("personas/yuna-card.jpg"), chat: pub("personas/yuna-chat.jpg") },
  "анастасия романовна": { card: pub("personas/anastasia-card.png"), chat: pub("personas/anastasia-chat.png") },
  "саша": { card: pub("personas/sasha-card.png"), chat: pub("personas/sasha-chat.png") },
  "рокси": { card: pub("personas/roxy-card.png"), chat: pub("personas/roxy-chat.png") },
  "пай": { card: pub("personas/pai-card.png"), chat: pub("personas/pai-chat.png") },
  "хани": { card: pub("personas/hani-card.png"), chat: pub("personas/hani-chat.png") },
  // Persona keys (used as fallback when name is localized)
  "lina": { card: pub("personas/lina-card.png"), chat: pub("personas/lina-chat.png") },
  "marianna": { card: pub("personas/marianna-card.png"), chat: pub("personas/marianna-chat.png") },
  "aki": { card: pub("personas/aki-card.jpg"), chat: pub("personas/aki-chat.jpg") },
  "mei": { card: pub("personas/mei-card.png"), chat: pub("personas/mei-chat.png") },
  "stacey": { card: pub("personas/stacey-card.jpg"), chat: pub("personas/stacey-chat.jpg") },
  "taya": { card: pub("personas/taya-card.png"), chat: pub("personas/taya-chat.png") },
  "julie": { card: pub("personas/julie-card.png"), chat: pub("personas/julie-chat.png") },
  "ash": { card: pub("personas/ash-card.png"), chat: pub("personas/ash-chat.png") },
  "yuna": { card: pub("personas/yuna-card.jpg"), chat: pub("personas/yuna-chat.jpg") },
  "anastasia": { card: pub("personas/anastasia-card.png"), chat: pub("personas/anastasia-chat.png") },
  "sasha": { card: pub("personas/sasha-card.png"), chat: pub("personas/sasha-chat.png") },
  "roxy": { card: pub("personas/roxy-card.png"), chat: pub("personas/roxy-chat.png") },
  "pai": { card: pub("personas/pai-card.png"), chat: pub("personas/pai-chat.png") },
  "hani": { card: pub("personas/hani-card.png"), chat: pub("personas/hani-chat.png") },
};

const DEFAULT_AVATAR = {
  card: pub("personas/custom-card.jpg"),
  chat: pub("personas/custom-chat.jpg"),
};

export function getAvatarPaths(name: string | undefined, isCustom: boolean | undefined) {
  if (isCustom) return DEFAULT_AVATAR;
  if (!name) return DEFAULT_AVATAR;
  const key = name.trim().toLowerCase();
  return AVATARS[key] ?? DEFAULT_AVATAR;
}
