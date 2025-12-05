import { pub } from "./pub";

const AVATARS: Record<string, { card: string; chat: string }> = {
  "лина": { card: pub("personas/lina-card.jpg"), chat: pub("personas/lina-chat.jpg") },
  "марианна": { card: pub("personas/marianna-card.jpg"), chat: pub("personas/marianna-chat.jpg") },
  "аки": { card: pub("personas/aki-card.jpg"), chat: pub("personas/aki-chat.jpg") },
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
