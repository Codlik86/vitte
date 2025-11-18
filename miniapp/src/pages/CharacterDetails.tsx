import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { Persona } from "../api/types";
import { selectPersona } from "../api/client";

export function CharacterDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [persona, setPersona] = useState<Persona | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const load = async () => {
      if (!id) return;
      try {
        // This page is optional; we only show shallow details based on current list
        // For now, we just show minimal info using provided id.
        setPersona({
          id: Number(id),
          name: "Персонаж",
          short_description: "",
          archetype: null,
          is_default: true,
          is_custom: false,
          is_active: false,
        });
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
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{persona.name}</h1>
            <span className="text-xs text-white/50">{persona.short_title}</span>
          </div>
          <p className="text-sm text-white/70">{persona.description_long}</p>
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
