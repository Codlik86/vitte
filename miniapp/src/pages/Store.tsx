import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/layout/PageHeader";
import { DebugTelegramBanner } from "../components/DebugTelegramBanner";
import { fetchStoreProducts, purchaseProduct } from "../api/client";
import type { StoreProduct } from "../api/types";
import { useAccessStatus } from "../hooks/useAccessStatus";

type PurchaseState = {
  [code: string]: "idle" | "loading" | "success" | "error";
};

export function Store() {
  const navigate = useNavigate();
  const { data: accessStatus } = useAccessStatus();
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [states, setStates] = useState<PurchaseState>({});

  const hasSubscription = Boolean(accessStatus?.has_subscription);
  const headerStats = {
    gems: 0,
    usedMessages: accessStatus?.free_messages_used ?? null,
    limitMessages: accessStatus?.free_messages_limit ?? null,
    hasUnlimited: hasSubscription,
    isPremium: hasSubscription,
  };

  useEffect(() => {
    async function load() {
      try {
        setError(null);
        setLoading(true);
        const res = await fetchStoreProducts();
        setProducts(res.products);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить магазин");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handlePurchase = async (productCode: string) => {
    setStates((prev) => ({ ...prev, [productCode]: "loading" }));
    try {
      await purchaseProduct(productCode);
      setStates((prev) => ({ ...prev, [productCode]: "success" }));
    } catch (err) {
      setStates((prev) => ({ ...prev, [productCode]: "error" }));
      console.error(err);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-4">
      <div className="mx-auto w-full max-w-screen-sm space-y-6 px-4 pb-12">
        <PageHeader title="Магазин" showBack onBack={() => navigate(-1)} stats={headerStats} />

        <DebugTelegramBanner />

        {error && (
          <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        <div className="space-y-4">
          {loading
            ? Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={`skeleton-${index}`}
                  className="rounded-3xl border border-white/10 bg-card-elevated/70 px-5 py-5 animate-pulse"
                >
                  <div className="h-4 w-32 rounded-full bg-white/10" />
                  <div className="mt-3 h-3 w-48 rounded-full bg-white/10" />
                </div>
              ))
            : products.map((product) => {
                const state = states[product.product_code] ?? "idle";
                return (
                  <div
                    key={product.product_code}
                    className="rounded-4xl border border-white/5 bg-card-elevated/80 px-5 py-5 shadow-card"
                  >
                    <p className="text-base font-semibold text-white">{product.title}</p>
                    <p className="mt-1 text-sm text-white/70">{product.description}</p>
                    <div className="mt-4 flex items-center justify-between">
                      <span className="text-sm text-white/80">
                        {product.price_stars} ⭐ · {product.type}
                      </span>
                      <button
                        className="rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                        onClick={() => handlePurchase(product.product_code)}
                        disabled={state === "loading"}
                      >
                        {state === "loading"
                          ? "Покупаем..."
                          : `Купить за ${product.price_stars} ⭐`}
                      </button>
                    </div>
                    {state === "success" && (
                      <p className="mt-3 text-xs text-emerald-300">
                        Покупка оформлена, ожидаем подтверждения Telegram.
                      </p>
                    )}
                    {state === "error" && (
                      <p className="mt-3 text-xs text-red-300">Не удалось оформить покупку.</p>
                    )}
                  </div>
                );
              })}
        </div>
      </div>
    </div>
  );
}
