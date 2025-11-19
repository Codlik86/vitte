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
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
        <p className="text-sm text-white/60">Загружаем...</p>
      </div>
    );
  }

  if (error || !persona) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
        <p className="text-sm text-red-300">{error ?? "Персонаж не найден"}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-xl mx-auto px-4 py-6 space-y-4">
        <button
          className="text-xs text-white/60 mb-2"
          onClick={() => navigate(-1)}
        >
          ← Назад
        </button>

        <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4 space-y-2">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-semibold">{persona.name}</h1>
            {persona.short_description && (
              <p className="text-sm text-white/70">
                {persona.short_description}
              </p>
            )}
            {persona.long_description && (
              <p className="text-sm text-white/60">{persona.long_description}</p>
            )}
          </div>
        </div>

        <button
          className="w-full mt-4 px-4 py-2 rounded-2xl bg-white text-slate-950 text-sm font-medium disabled:opacity-60"
          onClick={handleSelect}
          disabled={busy || persona.is_selected}
        >
          {persona.is_selected ? "Уже выбран" : "Выбрать персонажа"}
        </button>
      </div>
    </div>
  );
}
