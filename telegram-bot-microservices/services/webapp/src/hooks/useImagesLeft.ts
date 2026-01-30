import { useEffect, useMemo, useState } from "react";
import { useAccessStatus } from "./useAccessStatus";
import { useStoreData } from "./useStoreData";

type UseImagesLeftResult = {
  imagesLeft: number | null;
  loading: boolean;
  reload: () => Promise<void>;
  source: string;
};

export function useImagesLeft(): UseImagesLeftResult {
  const { data: accessStatus, loading, reload } = useAccessStatus();
  const { status: storeStatus } = useStoreData(true);
  const [lastValue, setLastValue] = useState<number | null>(() => {
    const raw = sessionStorage.getItem("vitte_images_left_cache");
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as { value: number; ts: number };
      const fresh = Date.now() - parsed.ts < 120_000;
      return fresh ? parsed.value : null;
    } catch {
      return null;
    }
  });

  const calculateFromStore = () => {
    if (!storeStatus) return null;
    const { remaining_images_today, remaining_paid_images } = storeStatus;
    const hasData =
      typeof remaining_images_today === "number" || typeof remaining_paid_images === "number";
    if (!hasData) return null;
    const free = typeof remaining_images_today === "number" ? remaining_images_today : 0;
    const paid = typeof remaining_paid_images === "number" ? remaining_paid_images : 0;
    return free + paid;
  };

  const calculateFromAccess = () => {
    if (!accessStatus?.images) return null;
    const { remaining_free_today, remaining_paid } = accessStatus.images;
    const hasData =
      typeof remaining_free_today === "number" || typeof remaining_paid === "number";
    if (!hasData) return null;
    const free = typeof remaining_free_today === "number" ? remaining_free_today : 0;
    const paid = typeof remaining_paid === "number" ? remaining_paid : 0;
    return free + paid;
  };

  const imagesLeft = useMemo(() => {
    return calculateFromStore() ?? calculateFromAccess() ?? null;
  }, [accessStatus, storeStatus]);

  useEffect(() => {
    if (imagesLeft !== null) {
      setLastValue(imagesLeft);
      try {
        sessionStorage.setItem(
          "vitte_images_left_cache",
          JSON.stringify({ value: imagesLeft, ts: Date.now() })
        );
      } catch {
        // ignore storage errors
      }
    }
  }, [imagesLeft]);

  useEffect(() => {
    if (import.meta.env.VITE_DEBUG_MINIAPP === "1") {
      console.info("[Vitte][DEBUG_MINIAPP][imagesLeft]", {
        imagesLeft: imagesLeft ?? lastValue,
        source: storeStatus
          ? "store_status"
          : accessStatus?.images
            ? "access_status"
            : "none",
        storeStatus,
        accessImages: accessStatus?.images,
      });
    }
  }, [imagesLeft, accessStatus?.images, storeStatus, lastValue]);

  return {
    imagesLeft: imagesLeft ?? lastValue,
    loading,
    reload,
    source: storeStatus
      ? "store_status"
      : accessStatus?.images
        ? "access_status"
        : "none",
  };
}
