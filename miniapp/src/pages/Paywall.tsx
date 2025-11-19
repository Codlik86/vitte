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
    <div className="relative min-h-dvh bg-bg-dark text-text-main">
      <div className="absolute top-4 right-4 rounded-full bg-accent-soft px-4 py-1 text-xs font-semibold flex items-center gap-2 text-white shadow-card">
        <span>0 💎</span>
        {data && (
          <span className="opacity-90">
            {data.free_messages_used} / {data.free_messages_limit} сообщений
          </span>
        )}
      </div>
      <div className="mx-auto flex min-h-dvh w-full max-w-screen-sm items-start justify-center px-4 pb-12 pt-16">
        <section className="w-full rounded-4xl bg-card-elevated px-6 py-7 shadow-card space-y-4">
          <h1 className="text-3xl font-bold tracking-tight">Vitte</h1>
          <p className="text-sm text-text-muted leading-relaxed">
            Романтический AI-компаньон. Сейчас у тебя есть ограниченное число
            бесплатных сообщений. Чтобы продолжать общение без лимитов, можно
            оформить подписку.
          </p>

          {error && <p className="text-sm text-red-400">{error}</p>}
          {data && (
            <p className="text-sm text-text-muted">
              Использовано {data.free_messages_used} из{" "}
              {data.free_messages_limit} бесплатных сообщений.
            </p>
          )}

          <ul className="space-y-1 text-sm text-text-muted pt-1">
            <li>• Безлимитные сообщения</li>
            <li>• Более глубокий флирт и эмоциональные сцены</li>
            <li>• Приоритетные ответы модели</li>
          </ul>

          <div className="space-y-3 pt-4">
            <button className="w-full rounded-full bg-accent text-white font-semibold py-4 text-base shadow-card active:scale-[0.98] transition-transform">
              Перейти к подписке
            </button>
            <button className="w-full rounded-full bg-card-dark text-text-main font-medium py-4 text-base border border-white/10">
              Выбрать персонажа
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
