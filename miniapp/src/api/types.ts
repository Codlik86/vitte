export type PersonaListItem = {
  id: number;
  name: string;
  short_title: string;
  short_description: string;
  is_default: boolean;
  is_owner: boolean;
  is_selected: boolean;
  is_custom: boolean;
  gender?: string | null;
  kind?: string | null;
};

export type PersonaDetails = PersonaListItem & {
  long_description?: string | null;
  archetype?: string | null;
  legend_full?: string | null;
  emotions_full?: string | null;
  triggers_positive?: string[] | null;
  triggers_negative?: string[] | null;
  story_cards?: StoryCard[] | null;
  has_history?: boolean;
  dialog_id?: number | null;
};

export type PersonasListResponse = {
  items: PersonaListItem[];
};

export type StoreProduct = {
  product_code: string;
  title: string;
  description: string;
  price_stars: number;
  type: string;
};

export type FeatureStatusItem = {
  code: string;
  title: string;
  description: string;
  active: boolean;
  enabled: boolean;
  until?: string | null;
  product_code: string;
  toggleable: boolean;
};

export type FeatureStatusResponse = {
  features: FeatureStatusItem[];
};

export type AccessStatusResponse = {
  telegram_id: number;
  access_status: string;
  free_messages_used: number;
  free_messages_limit: number;
  has_access: boolean;
  can_send_message: boolean;
  has_subscription: boolean;
  plan_code: string | null;
  premium_until: string | null;
  paywall_variant: "A" | "B";
  store: {
    available_products: StoreProduct[];
  };
  features?: FeatureStatusResponse | null;
};

export type ChatResponse = {
  reply: string;
  persona_id: number;
  trust_level: number;
  ritual_hint?: string | null;
  reply_kind?: string;
  voice_id?: string | null;
  voice_url?: string | null;
  feature_mode?: string | null;
};

export type PersonaSelectResponse = {
  ok: boolean;
  persona_id: number;
  dialog_id?: number | null;
  greeting_sent: boolean;
  greeting_mode?: "first" | "return" | "updated" | string | null;
};

export type PaymentPlan = {
  code: string;
  title: string;
  description: string;
  price: number;
  currency: string;
  period: "day" | "week" | "month" | "quarter" | "year";
  provider: string;
  recommended?: boolean;
};

export type SubscribeResponse = {
  subscription_id: number;
  provider: string;
  status: string;
  confirmation?: Record<string, unknown> | null;
};

export type StoreProductsResponse = {
  products: StoreProduct[];
};

export type StorePurchaseResponse = {
  purchase_id: number;
  provider: string;
  status: string;
  invoice?: Record<string, unknown> | null;
};

export type StoreBuyResponse = {
  ok: boolean;
  product_code: string;
  activated_until?: string | null;
  features?: string[] | null;
};
export type StoryCard = {
  id: string;
  title: string;
  description: string;
  atmosphere: "flirt_romance" | "support" | "cozy_evening" | "serious_talk";
  prompt: string;
};
