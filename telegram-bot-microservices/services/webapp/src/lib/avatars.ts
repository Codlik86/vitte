import { pub } from "./pub";

const AVATARS: Record<string, { card: string; chat: string }> = {
  "лина": { card: pub("personas/lina-card.jpg"), chat: pub("personas/lina-chat.jpg") },
  "марианна": { card: pub("personas/marianna-card.jpg"), chat: pub("personas/marianna-chat.jpg") },
  "аки": { card: pub("personas/aki-card.jpg"), chat: pub("personas/aki-chat.jpg") },
  "мей": { card: pub("personas/mei-card.jpg"), chat: pub("personas/mei-chat.jpg") },
  "стейси": { card: pub("personas/stacey-card.jpg"), chat: pub("personas/stacey-chat.jpg") },
  "тая": { card: pub("personas/taya-card.jpg"), chat: pub("personas/taya-chat.jpg") },
  "джули": { card: pub("personas/julie-card.jpg"), chat: pub("personas/julie-chat.jpg") },
  "эш": { card: pub("personas/ash-card.jpg"), chat: pub("personas/ash-chat.jpg") },
  "юна": { card: pub("personas/yuna-card.jpg"), chat: pub("personas/yuna-chat.jpg") },
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
