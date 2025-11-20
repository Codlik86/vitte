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

export type StoreProduct = {
  product_code: string;
  title: string;
  description: string;
  price_stars: number;
  type: string;
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
