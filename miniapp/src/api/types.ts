export type Persona = {
  id: number;
  name: string;
  short_description: string;
  archetype: string | null;
  is_default: boolean;
  is_custom: boolean;
  is_active: boolean;
};

export type PersonasListResponse = {
  items: Persona[];
};
