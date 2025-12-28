import { useEffect, useMemo } from "react";
import { useAccessStatus } from "./useAccessStatus";

type UseImagesLeftResult = {
  imagesLeft: number | null;
  loading: boolean;
  reload: () => Promise<void>;
  source: string;
};

export function useImagesLeft(): UseImagesLeftResult {
  const { data: accessStatus, loading, reload } = useAccessStatus();

  const imagesLeft = useMemo(() => {
    if (!accessStatus?.images) return null;
    const free = accessStatus.images.remaining_free_today ?? 0;
    const paid = accessStatus.images.remaining_paid ?? 0;
    return free + paid;
  }, [accessStatus]);

  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.info("[Vitte][imagesLeft] updated", {
        imagesLeft,
        source: "access_status",
      });
    }
  }, [imagesLeft]);

  return { imagesLeft, loading, reload, source: "access_status" };
}

