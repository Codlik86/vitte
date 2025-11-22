type PersonaCardProps = {
  title: string;
  description?: string | null;
  gradientVariant?: "default" | "custom";
  selected?: boolean;
  onClick: () => void;
};

export function PersonaCard({
  title,
  description,
  gradientVariant = "default",
  selected = false,
  onClick,
}: PersonaCardProps) {
  const gradientClass =
    gradientVariant === "custom"
      ? "from-[#4E9BFF] via-[#A855FF] to-[#FF6FD8]"
      : "from-[#35164F] via-[#60317A] to-[#E24CBD]";

  return (
    <button
      type="button"
      onClick={onClick}
      className="group relative flex flex-col rounded-3xl border border-white/5 bg-card-elevated/70 p-3 text-left transition hover:border-white/20 hover:bg-card-elevated/90 active:scale-[0.98]"
    >
      <div className="relative">
        <div className="relative w-full overflow-hidden rounded-2xl">
          <div
            className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${gradientClass}`}
            aria-hidden
          />
          <div
            className="pointer-events-none absolute inset-4 rounded-2xl bg-white/20 blur-3xl opacity-80"
            aria-hidden
          />
          <div className="aspect-square" />
        </div>
        {selected && (
          <span className="absolute right-2 top-2 rounded-full bg-emerald-500/90 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white shadow-card">
            выбрано
          </span>
        )}
      </div>
      <div className="mt-3 space-y-1">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {description && (
          <p className="text-xs text-white/70 line-clamp-2">
            {description}
          </p>
        )}
      </div>
    </button>
  );
}
