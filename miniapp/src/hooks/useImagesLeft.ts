import { useEffect, useMemo } from "react";
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

  const imagesLeft = useMemo(() => {
    if (accessStatus?.images) {
      const free = accessStatus.images.remaining_free_today ?? 0;
      const paid = accessStatus.images.remaining_paid ?? 0;
      return free + paid;
    }
    if (storeStatus) {
      const free = storeStatus.remaining_images_today ?? 0;
      const paid = storeStatus.remaining_paid_images ?? 0;
      return free + paid;
    }
    return null;
  }, [accessStatus, storeStatus]);

  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.info("[Vitte][imagesLeft] updated", {
        imagesLeft,
        source: accessStatus?.images ? "access_status" : storeStatus ? "store_status" : "none",
      });
    }
  }, [imagesLeft, accessStatus?.images, storeStatus]);

  return {
    imagesLeft,
    loading,
    reload,
    source: accessStatus?.images ? "access_status" : storeStatus ? "store_status" : "none",
  };
}
