import { useCallback, useEffect, useState } from "react";
import { fetchStoreConfig, fetchStoreStatus } from "../api/client";
import type { StoreConfig, StoreStatus } from "../api/types";

type StoreData = {
  config: StoreConfig | null;
  status: StoreStatus | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
};

export function useStoreData(auto = true): StoreData {
  const [config, setConfig] = useState<StoreConfig | null>(null);
  const [status, setStatus] = useState<StoreStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(auto);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const [configRes, statusRes] = await Promise.all([fetchStoreConfig(), fetchStoreStatus()]);
      setConfig(configRes);
      setStatus(statusRes);
    } catch (e: any) {
      setError(e.message ?? "Не удалось загрузить магазин");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (auto) {
      reload();
    }
  }, [auto, reload]);

  return { config, status, loading, error, reload };
}
