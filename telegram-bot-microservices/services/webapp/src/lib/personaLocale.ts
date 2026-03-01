import contentEn from "../i18n/content_en.json";
import type { PersonaListItem, PersonaDetails, StoryCard } from "../api/types";

type PersonaContentEntry = {
  name?: string;
  short_title?: string;
  short_description?: string;
  description_long?: string;
  story_cards?: Record<string, { title?: string; description?: string }>;
};

const content: Record<string, PersonaContentEntry> = contentEn;

function getEntry(key?: string | null): PersonaContentEntry | null {
  if (!key) return null;
  return content[key] ?? null;
}

export function localizePersonaListItem(
  persona: PersonaListItem,
  lang: string
): PersonaListItem {
  if (lang !== "en") return persona;
  const entry = getEntry(persona.key);
  if (!entry) return persona;
  return {
    ...persona,
    name: entry.name ?? persona.name,
    short_title: entry.short_title ?? persona.short_title,
    short_description: (entry.short_description ?? persona.short_description) as string,
  };
}

export function localizePersona(
  persona: PersonaDetails,
  lang: string
): PersonaDetails {
  if (lang !== "en") return persona;
  const entry = getEntry(persona.key);
  if (!entry) return persona;

  const localizedCards: StoryCard[] | null | undefined = persona.story_cards?.map((card) => {
    const cardEn = entry.story_cards?.[card.key];
    if (!cardEn) return card;
    return {
      ...card,
      title: cardEn.title ?? card.title,
      description: cardEn.description ?? card.description,
    };
  });

  return {
    ...persona,
    name: entry.name ?? persona.name,
    short_title: entry.short_title ?? persona.short_title,
    short_description: (entry.short_description ?? persona.short_description) as string,
    description_long: entry.description_long ?? persona.description_long,
    story_cards: localizedCards,
  };
}
