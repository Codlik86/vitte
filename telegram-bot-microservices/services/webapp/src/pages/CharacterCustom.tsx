import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { createCustomPersona, fetchPersona, fetchPersonas, selectPersonaAndGreet } from "../api/client";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { useImagesLeft } from "../hooks/useImagesLeft";
import { tg } from "../lib/telegram";

export function CharacterCustom() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: accessStatus } = useAccessStatus();
  const { imagesLeft } = useImagesLeft();
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [vibe, setVibe] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingPersonaId, setExistingPersonaId] = useState<number | null>(null);
  const [initialForm, setInitialForm] = useState({ name: "", shortDescription: "", vibe: "" });
  const [hasHistory, setHasHistory] = useState(false);
  const hasSubscription = accessStatus?.has_subscription;
  const imagesAvailable = imagesLeft;
  const headerStats = {
    images: imagesAvailable,
    hasSubscription,
    isPremium: hasSubscription,
  };

  useEffect(() => {
    const load = async () => {
      try {
        const personas = await fetchPersonas();
        const customItem = personas.items.find((p) => p.is_custom);
        if (customItem) {
          const details = await fetchPersona(customItem.id);
          setExistingPersonaId(details.id);
          setName(details.name);
          setShortDescription(details.short_description);
          setVibe(details.long_description ?? details.legend_full ?? "");
          setInitialForm({
            name: details.name,
            shortDescription: details.short_description,
            vibe: details.long_description ?? details.legend_full ?? "",
          });
          setHasHistory(Boolean(details.has_history));
        }
      } catch (e: any) {
        setError(e.message ?? t("custom_load_error"));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const isDirty =
    name !== initialForm.name ||
    shortDescription !== initialForm.shortDescription ||
    vibe !== initialForm.vibe;

  const buttonLabel = useMemo(() => {
    if (!existingPersonaId) {
      return t("create_and_start");
    }
    if (!hasHistory) {
      return t("start_chat");
    }
    return isDirty ? t("save_and_continue") : t("continue_chat");
  }, [existingPersonaId, hasHistory, isDirty, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setBusy(true);
      let personaId = existingPersonaId;

      if (!existingPersonaId) {
        const created = await createCustomPersona({
          name,
          short_description: shortDescription,
          vibe,
          replace_existing: false,
        });
        personaId = created.id;
        setExistingPersonaId(created.id);
        setInitialForm({
          name,
          shortDescription,
          vibe,
        });
        setHasHistory(Boolean(created.has_history));
      } else if (isDirty) {
        const updated = await createCustomPersona({
          name,
          short_description: shortDescription,
          vibe,
          replace_existing: true,
        });
        personaId = updated.id;
        setInitialForm({
          name,
          shortDescription,
          vibe,
        });
        setHasHistory(Boolean(updated.has_history));
      }

      if (!personaId) {
        throw new Error(t("custom_id_error"));
      }

      await selectPersonaAndGreet({
        personaId,
        extraDescription: vibe || shortDescription,
        settingsChanged: Boolean(hasHistory && isDirty),
      });
      if (tg?.close) {
        tg.close();
      } else {
        navigate("/");
      }
    } catch (e: any) {
      const message = e.message ?? t("custom_save_error");
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto w-full max-w-screen-md px-4 pb-16 space-y-6 sm:px-5">
        <PageHeader
          title={t("custom_character_title")}
          showBack
          onBack={() => navigate(-1)}
          stats={headerStats}
        />

        <section className="mt-4 rounded-4xl border border-white/5 bg-card-elevated/80 p-6 shadow-card">
          <div className="space-y-3">
            <h1 className="text-3xl font-semibold text-white">{t("create_me")}</h1>
            <p className="text-sm leading-relaxed text-white/80 sm:text-base">
              {t("create_me_description")}
            </p>
          </div>

          {!hasSubscription ? (
            <div className="mt-6 space-y-4 rounded-3xl border border-white/10 bg-card-dark/60 p-5 text-center text-sm text-white/80">
              <p>{t("premium_required")}</p>
              <Link
                to="/paywall"
                className="inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-3 text-base font-semibold text-white shadow-card"
              >
                {t("subscribe")}
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-6 space-y-6">
              {loading && (
                <div className="rounded-3xl border border-white/10 bg-card-dark/60 px-4 py-3 text-sm text-white/70">
                  {t("loading_hero")}
                </div>
              )}
              <label className="block space-y-2">
                <span className="text-sm font-medium text-white/80">
                  {t("character_name_label")}
                </span>
                <input
                  className="w-full rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none transition focus:border-white/40 placeholder:text-sm placeholder:text-white/40"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("name_placeholder")}
                  required
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-white/80">
                  {t("short_description_vibe")}
                </span>
                <input
                  className="w-full rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none transition focus:border-white/40 placeholder:text-sm placeholder:text-white/40"
                  value={shortDescription}
                  onChange={(e) => setShortDescription(e.target.value)}
                  placeholder={t("description_placeholder")}
                  required
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-white/80">
                  {t("extra_vibe")}
                </span>
                <textarea
                  className="w-full min-h-[120px] rounded-3xl border border-white/10 bg-card-dark px-4 py-3 text-base text-white outline-none transition focus:border-white/40 placeholder:text-sm placeholder:text-white/40"
                  value={vibe}
                  onChange={(e) => setVibe(e.target.value)}
                  placeholder={t("vibe_placeholder")}
                />
              </label>

              {error && (
                <p className="text-sm text-red-300">
                  {error}
                </p>
              )}

              <button
                type="submit"
                className="w-full rounded-full bg-gradient-to-r from-[#7B4DF0] to-[#E44CC6] px-4 py-4 text-base font-semibold text-white shadow-card transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy || loading}
              >
                {busy ? t("saving") : buttonLabel}
              </button>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
