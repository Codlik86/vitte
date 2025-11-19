import { Link } from "react-router-dom";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { MessageLimitChip } from "../components/MessageLimitChip";

export function Paywall() {
  const { data, loading, error } = useAccessStatus();
  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto flex min-h-dvh w-full max-w-screen-sm flex-col px-4 pb-12 pt-10">
        <MessageLimitChip
          className="mb-6"
          align="end"
          status={data}
          loading={loading}
          error={error}
        />

        <section className="w-full rounded-4xl border border-white/5 bg-card-elevated/85 px-6 py-8 shadow-card">
          <p className="text-[11px] uppercase tracking-[0.4em] text-text-muted">
            Подписка Vitte+
          </p>
          <h1 className="mt-2 text-4xl font-semibold leading-tight tracking-tight">
            Открой безлимит
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-text-muted">
            Сейчас у тебя есть ограниченное число бесплатных сообщений. Когда
            лимит закончится, можно подключить подписку и продолжить общение без
            преград.
          </p>

          {data && (
            <p className="mt-4 text-xs uppercase tracking-[0.3em] text-text-muted">
              Использовано {data.free_messages_used} из{" "}
              {data.free_messages_limit}
            </p>
          )}
          {error && !data && (
            <p className="mt-4 text-sm text-red-300">{error}</p>
          )}

          <ul className="mt-6 space-y-3 text-sm text-white/80">
            <li className="flex items-start gap-3">
              <span className="text-base leading-none text-pink-300">•</span>
              <span>Безлимитные сообщения и свободный флирт.</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-base leading-none text-pink-300">•</span>
              <span>Более глубокие эмоции, длинные ветки и сцены.</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-base leading-none text-pink-300">•</span>
              <span>Приоритетные ответы Vitte и быстрые обновления.</span>
            </li>
          </ul>

          <div className="mt-8 space-y-3">
            <button className="w-full rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-4 text-base font-semibold text-white shadow-card active:scale-[0.98]">
              Перейти к подписке
            </button>
            <Link
              to="/"
              className="block w-full rounded-full border border-white/10 bg-card-dark/80 px-4 py-4 text-center text-base font-medium text-white transition hover:bg-card-dark"
            >
              Вернуться к персонажам
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
