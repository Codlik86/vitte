import { useCallback, useEffect, useState } from "react";
import type { AccessStatusResponse } from "../api/types";
import { fetchAccessStatus } from "../api/client";

type UseAccessStatusResult = {
  data: AccessStatusResponse | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
};

let cachedAccessStatus: AccessStatusResponse | null = null;

export function useAccessStatus(auto = true): UseAccessStatusResult {
  const [data, setData] = useState<AccessStatusResponse | null>(() => cachedAccessStatus);
  const [loading, setLoading] = useState<boolean>(auto && !cachedAccessStatus);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const response = await fetchAccessStatus();
      cachedAccessStatus = response;
      setData(response);
    } catch (e: any) {
      setError(e.message ?? "Не удалось получить статус доступа");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (auto) {
      reload();
    }
  }, [auto, reload]);

  return { data, loading, error, reload };
}
