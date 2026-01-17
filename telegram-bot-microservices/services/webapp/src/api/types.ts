export type PersonaListItem = {
  id: number;
  name: string;
  short_title: string;
  short_description: string;
  is_default: boolean;
  is_owner: boolean;
  is_selected: boolean;
  is_custom: boolean;
  avatar_url?: string | null;
  avatar_chat_url?: string | null;
  avatar_card_url?: string | null;
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
    plans: Array<{
      code: string;
      title: string;
      description: string;
      duration_days: number;
      price_stars: number;
      is_most_popular?: boolean;
    }>;
    image_packs: Array<{
      code: string;
      images: number;
      price_stars: number;
    }>;
    features: Array<{
      code: string;
      title: string;
      description: string;
      price_stars: number;
    }>;
  };
  features?: FeatureStatusResponse | null;
  images?: {
    remaining_free_today: number;
    remaining_paid: number;
    total_remaining: number;
  };
};

export type ChatResponse = {
  reply: string;
  persona_id: number;
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

export type StoreBuyResponse = {
  ok: boolean;
  product_code: string;
  activated_until?: string | null;
  features?: string[] | null;
  invoice_url?: string | null;
};

export type StoreConfig = {
  subscription_plans: Array<{
    code: string;
    title: string;
    description: string;
    duration_days: number;
    price_stars: number;
    is_most_popular?: boolean;
  }>;
  image_packs: Array<{
    code: string;
    images: number;
    price_stars: number;
  }>;
  emotional_features: Array<{
    code: string;
    title: string;
    description: string;
    price_stars: number;
  }>;
};

export type StoreStatus = {
  has_active_subscription: boolean;
  subscription_ends_at: string | null;
  remaining_images_today: number;
  remaining_paid_images: number;
  unlocked_features: string[];
  is_free_user?: boolean;
};
export type StoryCard = {
  id: string;
  key: string;
  title: string;
  description: string;
  atmosphere: "flirt_romance" | "support" | "cozy_evening" | "serious_talk";
  prompt: string;
  image?: string | null;
};
