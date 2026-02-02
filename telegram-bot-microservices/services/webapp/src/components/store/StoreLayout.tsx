import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { buyFeature, buyImagePack } from "../../api/client";
import type { StoreConfig, StoreStatus } from "../../api/types";
import { useAccessStatus } from "../../hooks/useAccessStatus";
import { useStoreData } from "../../hooks/useStoreData";
import { PageHeader } from "../layout/PageHeader";
import { DebugTelegramBanner } from "../DebugTelegramBanner";
import { tg, type InvoiceStatus } from "../../lib/telegram";

type BusyMap = Record<string, boolean>;

type StoreLayoutProps = {
  title: string;
  showBack?: boolean;
};

export function StoreLayout({ title, showBack = true }: StoreLayoutProps) {
  const navigate = useNavigate();
  const { data: accessStatus, reload: reloadAccess } = useAccessStatus();
  const { config, status, loading, error, reload } = useStoreData();
  const [busy, setBusy] = useState<BusyMap>({});
  const hasSubscription = Boolean(status?.has_active_subscription || accessStatus?.has_subscription);
  const imagesAvailable = useMemo(() => {
    if (status) {
      return (status.remaining_images_today ?? 0) + (status.remaining_paid_images ?? 0);
    }
    if (accessStatus?.images) {
      return (accessStatus.images.remaining_free_today ?? 0) + (accessStatus.images.remaining_paid ?? 0);
    }
    return null;
  }, [status, accessStatus?.images]);
  const headerStats = {
    images: imagesAvailable,
    hasSubscription,
    isPremium: hasSubscription,
  };

  const setBusyFlag = (code: string, value: boolean) => {
    setBusy((prev) => ({ ...prev, [code]: value }));
  };

  const handleAfterPurchase = async () => {
    await Promise.all([reload(), reloadAccess()]);
  };

  const handleBuyPack = async (code: string) => {
    setBusyFlag(code, true);
    try {
      const res = await buyImagePack(code);
      if (!res.invoice_url) {
        alert("Не удалось создать счёт. Попробуй позже.");
        setBusyFlag(code, false);
        return;
      }

      if (tg?.openInvoice) {
        tg.openInvoice(res.invoice_url, async (status: InvoiceStatus) => {
          if (status === "paid") {
            await handleAfterPurchase();
          }
          setBusyFlag(code, false);
        });
      } else {
        tg?.openTelegramLink?.(res.invoice_url);
        tg?.close?.();
      }
    } catch (e: any) {
      alert(e.message ?? "Не удалось купить пакет изображений");
      setBusyFlag(code, false);
    }
  };

  const handleBuyFeature = async (code: string) => {
    setBusyFlag(code, true);
    try {
      const res = await buyFeature(code);
      if (!res.invoice_url) {
        alert("Не удалось создать счёт. Попробуй позже.");
        setBusyFlag(code, false);
        return;
      }

      if (tg?.openInvoice) {
        tg.openInvoice(res.invoice_url, async (status: InvoiceStatus) => {
          if (status === "paid") {
            await handleAfterPurchase();
          }
          setBusyFlag(code, false);
        });
      } else {
        tg?.openTelegramLink?.(res.invoice_url);
        tg?.close?.();
      }
    } catch (e: any) {
      alert(e.message ?? "Не удалось разблокировать улучшение");
      setBusyFlag(code, false);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto w-full max-w-screen-sm space-y-6 px-4 pb-16">
        <PageHeader
          title={title}
          showBack={showBack}
          onBack={() => navigate(-1)}
          stats={headerStats}
        />

        <DebugTelegramBanner />

        {error && (
          <div className="rounded-3xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        )}

        <StoreImagesAndFeaturesSection
          config={config}
          status={status}
          loading={loading}
          busy={busy}
          onBuyPack={handleBuyPack}
          onBuyFeature={handleBuyFeature}
        />
      </div>
    </div>
  );
}

function StoreImagesAndFeaturesSection({
  config,
  status,
  loading,
  busy,
  onBuyPack,
  // onBuyFeature,  // ОТКЛЮЧЕНО - больше нет улучшений
}: {
  config: StoreConfig | null;
  status: StoreStatus | null;
  loading: boolean;
  busy: BusyMap;
  onBuyPack: (code: string) => void;
  onBuyFeature: (code: string) => void;
}) {
  const packs = config?.image_packs ?? [];
  // const features = config?.emotional_features ?? [];  // ОТКЛЮЧЕНО
  // const unlocked = new Set(status?.unlocked_features ?? []);  // ОТКЛЮЧЕНО
  const imagesAvailable = (status?.remaining_images_today ?? 0) + (status?.remaining_paid_images ?? 0);

  return (
    <section className="space-y-4 rounded-3xl border border-white/10 bg-card-elevated/75 px-5 py-5 shadow-card">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-white">Изображения</h2>
        <p className="text-sm text-white/70">
          У вас {imagesAvailable} изображений. Докупите ещё — выберите нужный пакет ниже.
        </p>
      </div>

      <div className="space-y-3">
        {loading
          ? Array.from({ length: 2 }).map((_, i) => (
              <div
                key={`pack-skeleton-${i}`}
                className="h-16 rounded-3xl border border-white/10 bg-white/5 animate-pulse"
              />
            ))
          : packs.map((pack) => {
              const isBusy = busy[pack.code];
              return (
                <div
                  key={pack.code}
                  className="flex items-center justify-between rounded-3xl border border-white/10 bg-card-dark/40 px-4 py-3"
                >
                  <p className="text-sm font-semibold text-white">{pack.images} изображений</p>
                  <button
                    type="button"
                    onClick={() => onBuyPack(pack.code)}
                    disabled={isBusy}
                    className="rounded-full bg-gradient-to-r from-[#2c1a52] via-[#5a2b80] to-[#c23ba7] px-4 py-2 text-sm font-semibold text-white shadow-card transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isBusy ? "Покупаем..." : `${pack.price_stars} ⭐`}
                  </button>
                </div>
              );
            })}
      </div>

      {/* ОТКЛЮЧЕНО - больше нет улучшений */}
      {/* <div className="space-y-3">
        {loading
          ? Array.from({ length: 2 }).map((_, i) => (
              <div
                key={`feat-skeleton-${i}`}
                className="h-16 rounded-3xl border border-white/10 bg-white/5 animate-pulse"
              />
            ))
          : features.map((feature) => {
              const isUnlocked = unlocked.has(feature.code);
              const isBusy = busy[feature.code];
              return (
                <div
                  key={feature.code}
                  className="flex flex-col gap-2 rounded-3xl border border-white/10 bg-card-dark/35 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <p className="text-sm font-semibold text-white">{feature.title}</p>
                      <p className="text-xs text-white/70 line-clamp-2">{feature.description}</p>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${
                        isUnlocked
                          ? "bg-emerald-400/15 text-emerald-100"
                          : "bg-white/10 text-white/80"
                      }`}
                      style={{ whiteSpace: "nowrap", flexShrink: 0, minWidth: "fit-content" }}
                    >
                      {isUnlocked ? "Активировано" : `${feature.price_stars} ⭐`}
                    </span>
                  </div>
                  {!isUnlocked && (
                    <button
                      type="button"
                      onClick={() => onBuyFeature(feature.code)}
                      disabled={isBusy}
                      className="self-start rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-2 text-sm font-semibold text-white shadow-card transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isBusy ? "Оформляем..." : "Разблокировать"}
                    </button>
                  )}
                </div>
              );
            })}
      </div> */}
    </section>
  );
}
