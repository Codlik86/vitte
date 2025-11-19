import { Link } from "react-router-dom";

export function Home() {
  return (
    <div className="min-h-dvh bg-bg-dark text-text-main flex items-center justify-center px-4 py-10">
      <section className="relative w-full max-w-screen-sm rounded-4xl bg-card-elevated px-6 py-7 shadow-card space-y-4">
        <h1 className="text-3xl font-bold tracking-tight">Vitte</h1>
        <p className="text-sm text-text-muted leading-relaxed">
          Романтический AI-компаньон. У тебя есть 15 бесплатных сообщений,
          чтобы прочувствовать вайб Vitte. После лимита открывай подписку и
          продолжай общение без ограничений.
        </p>
        <ul className="space-y-1 text-sm text-text-muted">
          <li>• Поддерживающие и флиртующие диалоги</li>
          <li>• Встроенный выбор персонажей</li>
          <li>• Аниме, забота и глубокие эмоции</li>
        </ul>
        <div className="space-y-3 pt-2">
          <Link
            to="/paywall"
            className="block w-full rounded-full bg-accent text-white font-semibold py-4 text-base text-center shadow-card active:scale-[0.98] transition-transform"
          >
            Перейти к подписке
          </Link>
          <Link
            to="/characters"
            className="block w-full rounded-full bg-card-dark text-text-main font-medium py-4 text-base text-center border border-white/10"
          >
            Выбрать персонажа
          </Link>
        </div>
      </section>
    </div>
  );
}
