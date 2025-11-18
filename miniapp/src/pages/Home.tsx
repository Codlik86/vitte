import { Link } from "react-router-dom";

export function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full px-6 py-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur">
        <h1 className="text-3xl font-semibold mb-3">Vitte</h1>
        <p className="text-sm text-white/70 mb-4">
          Романтический AI-компаньон 💌 Сейчас у тебя есть ограниченное число
          бесплатных сообщений. Чтобы продолжать общение без лимитов, можно
          будет оформить подписку.
        </p>
        <Link
          to="/paywall"
          className="inline-flex items-center justify-center px-4 py-2 rounded-2xl bg-white text-slate-950 text-sm font-medium"
        >
          Перейти к подписке
        </Link>
        <div className="mt-3">
          <Link
            to="/characters"
            className="inline-flex items-center justify-center px-4 py-2 rounded-2xl bg-white/10 text-white text-sm font-medium"
          >
            Выбрать персонажа
          </Link>
        </div>
      </div>
    </div>
  );
}
