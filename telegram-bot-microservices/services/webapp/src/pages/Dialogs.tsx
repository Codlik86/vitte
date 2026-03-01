import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { fetchDialogs, clearDialog } from "../api/client";
import type { DialogInfo } from "../api/types";
import { PageHeader } from "../components/layout/PageHeader";
import { useAccessStatus } from "../hooks/useAccessStatus";
import { useImagesLeft } from "../hooks/useImagesLeft";
import { getAvatarPaths } from "../lib/avatars";

export function Dialogs() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: accessStatus } = useAccessStatus();
  const { imagesLeft } = useImagesLeft();
  const [dialogs, setDialogs] = useState<DialogInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const hasSubscription = accessStatus?.has_subscription;

  useEffect(() => {
    loadDialogs();
  }, []);

  const loadDialogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchDialogs();
      setDialogs(data.dialogs);
    } catch (e: any) {
      setError(e.message ?? t("load_error"));
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = (dialog: DialogInfo) => {
    navigate(`/chat/${dialog.dialog_id}`, {
      state: {
        personaId: dialog.persona_id,
        personaName: dialog.persona_name,
        personaKey: dialog.persona_key,
        storyId: dialog.story_id,
        atmosphere: dialog.atmosphere,
        dialogId: dialog.dialog_id,
        isReturn: true,
      },
    });
  };

  const handleDelete = async (dialogId: number) => {
    if (deletingId) return;
    setDeletingId(dialogId);
    try {
      await clearDialog(dialogId);
      setDialogs((prev) => prev.filter((d) => d.dialog_id !== dialogId));
    } catch (e: any) {
      setError(e.message ?? t("delete_error"));
    } finally {
      setDeletingId(null);
    }
  };

  const handleNewDialog = () => {
    navigate("/characters");
  };

  const canStartNew = dialogs.length < 10;

  return (
    <div className="min-h-dvh bg-bg-dark text-text-main pt-6">
      <div className="mx-auto flex min-h-dvh w-full max-w-screen-md flex-col px-4 pb-16 sm:px-5">
        <PageHeader
          title={t("dialogs_title")}
          showBack
          onBack={() => navigate(-1)}
          stats={{ images: imagesLeft, hasSubscription }}
        />

        <div className="mt-6 space-y-4">
          {/* New dialog button */}
          <button
            onClick={handleNewDialog}
            disabled={!canStartNew}
            className={`w-full rounded-2xl border-2 border-dashed p-4 text-center transition ${
              canStartNew
                ? "border-white/20 text-white/70 hover:border-white/40 hover:text-white"
                : "border-white/10 text-white/30 cursor-not-allowed"
            }`}
          >
            {canStartNew ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  className="h-5 w-5"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                {t("start_new_dialog")}
              </span>
            ) : (
              <span>{t("max_dialogs")}</span>
            )}
          </button>

          {/* Loading state */}
          {loading && (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="animate-pulse rounded-2xl border border-white/5 bg-card-elevated/60 p-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-12 w-12 rounded-full bg-white/10" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-1/3 rounded-full bg-white/10" />
                      <div className="h-3 w-2/3 rounded-full bg-white/5" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
              <button
                onClick={loadDialogs}
                className="ml-2 underline hover:no-underline"
              >
                {t("retry")}
              </button>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && dialogs.length === 0 && (
            <div className="text-center py-12">
              <p className="text-white/50">{t("no_dialogs")}</p>
              <p className="mt-2 text-sm text-white/30">
                {t("choose_character")}
              </p>
            </div>
          )}

          {/* Dialogs list */}
          {!loading && !error && dialogs.length > 0 && (
            <div className="space-y-3">
              {dialogs.map((dialog) => {
                const avatarUrl = getAvatarPaths(dialog.persona_key, false).card;
                const isDeleting = deletingId === dialog.dialog_id;

                return (
                  <div
                    key={dialog.dialog_id}
                    className="relative rounded-2xl border border-white/5 bg-card-elevated/60 overflow-hidden"
                  >
                    <button
                      onClick={() => handleContinue(dialog)}
                      className="w-full p-4 text-left hover:bg-white/5 transition"
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={avatarUrl}
                          alt={dialog.persona_name}
                          className="h-12 w-12 rounded-full object-cover"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="text-base font-semibold text-white truncate">
                              {dialog.persona_name}
                            </h3>
                            <span className="shrink-0 rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-white/50">
                              {t("slot", { number: dialog.slot_number })}
                            </span>
                          </div>
                          {dialog.last_message && (
                            <p className="mt-1 text-sm text-white/50 truncate">
                              {dialog.last_message}
                            </p>
                          )}
                          <p className="mt-1 text-xs text-white/30">
                            {t("messages_count", { count: dialog.message_count })}
                          </p>
                        </div>
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2}
                          stroke="currentColor"
                          className="h-5 w-5 text-white/30"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M8.25 4.5l7.5 7.5-7.5 7.5"
                          />
                        </svg>
                      </div>
                    </button>

                    {/* Delete button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(dialog.dialog_id);
                      }}
                      disabled={isDeleting}
                      className="absolute top-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/30 transition disabled:opacity-50"
                    >
                      {isDeleting ? (
                        <span className="loading-dots text-xs">
                          <span />
                        </span>
                      ) : (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2}
                          stroke="currentColor"
                          className="h-4 w-4"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
