export type PersonaListItem = {
  id: number;
  name: string;
  short_description: string;
  is_default: boolean;
  is_owner: boolean;
  is_selected: boolean;
};

export type PersonaDetails = PersonaListItem & {
  long_description?: string | null;
  archetype?: string | null;
};

export type PersonasListResponse = {
  items: PersonaListItem[];
};

export type AccessStatusResponse = {
  telegram_id: number;
  access_status: string;
  free_messages_used: number;
  free_messages_limit: number;
  has_access: boolean;
};
