export type Persona = {
  id: number;
  key: string;
  name: string;
  short_title: string;
  gender: string;
  kind: string;
  description_short: string;
  description_long: string;
  style_tags: Record<string, string>;
  is_custom: boolean;
  is_selected: boolean;
};

export type PersonasListResponse = {
  items: Persona[];
};
