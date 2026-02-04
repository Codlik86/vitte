import { pub } from "./pub";

const AVATARS: Record<string, { card: string; chat: string }> = {
  "лина": { card: pub("personas/lina-card.png"), chat: pub("personas/lina-chat.png") },
  "марианна": { card: pub("personas/marianna-card.png"), chat: pub("personas/marianna-chat.png") },
  "аки": { card: pub("personas/aki-card.jpg"), chat: pub("personas/aki-chat.jpg") },
  "мей": { card: pub("personas/mei-card.png"), chat: pub("personas/mei-chat.png") },
  "стейси": { card: pub("personas/stacey-card.jpg"), chat: pub("personas/stacey-chat.jpg") },
  "тая": { card: pub("personas/taya-card.png"), chat: pub("personas/taya-chat.png") },
  "джули": { card: pub("personas/julie-card.png"), chat: pub("personas/julie-chat.png") },
  "эш": { card: pub("personas/ash-card.png"), chat: pub("personas/ash-chat.png") },
  "юна": { card: pub("personas/yuna-card.jpg"), chat: pub("personas/yuna-chat.jpg") },
  "училка": { card: pub("personas/uchilka-card.jpeg"), chat: pub("personas/uchilka-chat.jpeg") },
  "инста": { card: pub("personas/insta-card.jpeg"), chat: pub("personas/insta-chat.jpeg") },
  "косплей": { card: pub("personas/cosplay-card.jpeg"), chat: pub("personas/cosplay-chat.jpeg") },
  "аниме 1": { card: pub("personas/anime1-card.jpeg"), chat: pub("personas/anime1-chat.jpeg") },
  "аниме 2": { card: pub("personas/anime2-card.jpeg"), chat: pub("personas/anime2-chat.jpeg") },
  "милфа": { card: pub("personas/milfa-card.jpeg"), chat: pub("personas/milfa-chat.jpeg") },
  "толстушка": { card: pub("personas/tolstushka-card.jpeg"), chat: pub("personas/tolstushka-chat.jpeg") },
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
