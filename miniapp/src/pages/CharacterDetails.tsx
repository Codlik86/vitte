import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { PersonaDetails } from "../api/types";
import { selectPersona, fetchPersona } from "../api/client";

export function CharacterDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [persona, setPersona] = useState<PersonaDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const load = async () => {
      if (!id) return;
      try {
        const data = await fetchPersona(Number(id));
        setPersona(data);
      } catch (e: any) {
        setError(e.message ?? "Ошибка загрузки");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const handleSelect = async () => {
    if (!persona) return;
    try {
      setBusy(true);
      await selectPersona(persona.id);
      navigate("/characters");
    } catch (e: any) {
      setError(e.message ?? "Не удалось выбрать персонажа");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-bg-dark text-text-main">
        <p className="text-sm text-text-muted">Загружаем...</p>
      </div>
    );
  }

  if (error || !persona) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-bg-dark text-text-main">
        <p className="text-sm text-red-400">{error ?? "Персонаж не найден"}</p>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main">
      <div className="mx-auto flex min-h-dvh w-full max-w-screen-sm flex-col px-4 pb-10 pt-6">
        <button
          className="text-xs text-text-muted mb-4"
          onClick={() => navigate(-1)}
        >
          ← Назад
        </button>

        <section className="rounded-3xl bg-card-elevated px-5 py-5 shadow-card flex-1">
          <h1 className="text-3xl font-bold tracking-tight">{persona.name}</h1>
          {persona.short_description && (
            <p className="mt-3 text-sm leading-relaxed text-text-muted">
              {persona.short_description}
            </p>
          )}
          {persona.long_description && (
            <>
              <p className="mt-4 text-xs uppercase tracking-[0.3em] text-text-muted">
                Вайб
              </p>
              <p className="mt-2 text-sm text-text-main/80 leading-relaxed">
                {persona.long_description}
              </p>
            </>
          )}
          <div className="mt-6">
            <button
              className="w-full rounded-full bg-white text-bg-dark font-semibold py-4 text-base active:scale-[0.98] transition-transform disabled:opacity-70"
              onClick={handleSelect}
              disabled={busy || persona.is_selected}
            >
              {persona.is_selected ? "Персонаж уже выбран" : "Выбрать персонажа"}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
