import { useEffect, useState } from "react";

type AccessStatusResponse = {
  telegram_id: number;
  access_status: string;
  free_messages_used: number;
  free_messages_limit: number;
  has_access: boolean;
};

export function Paywall() {
  const [data, setData] = useState<AccessStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Пока без Telegram WebApp — для теста можно подставить ID руками
  const telegramId = 123456; // TODO: заменить на реальный ID из WebApp initData

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(
          `${import.meta.env.VITE_BACKEND_URL ?? ""}/api/access/status?telegram_id=${telegramId}`
        );
        if (!res.ok) {
          throw new Error("Failed to load access status");
        }
        const json = (await res.json()) as AccessStatusResponse;
        setData(json);
      } catch (e: any) {
        setError(e.message || "Ошибка загрузки статуса доступа");
      }
    };

    fetchStatus();
  }, [telegramId]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full px-6 py-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur">
        <h1 className="text-2xl font-semibold mb-3">Подписка Vitte</h1>

        {error && <p className="text-sm text-red-300 mb-3">{error}</p>}

        {data && (
          <p className="text-sm text-white/70 mb-4">
            Ты использовал {data.free_messages_used} из {data.free_messages_limit} бесплатных сообщений.
          </p>
        )}

        <p className="text-sm text-white/70 mb-4">
          Подписка откроет безлимитное общение, более глубокий флирт и
          эмоциональные сцены. Пока это только демо-пейвол, логика оплаты будет
          добавлена позже.
        </p>

        <div className="space-y-2">
          <button className="w-full px-4 py-2 rounded-2xl bg-white text-slate-950 text-sm font-medium">
            Оформить подписку (YooKassa)
          </button>
          <button className="w-full px-4 py-2 rounded-2xl bg-white/10 text-white text-sm font-medium">
            Оплатить через Stars
          </button>
        </div>
      </div>
    </div>
  );
}
