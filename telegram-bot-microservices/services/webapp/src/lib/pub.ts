// Resolve assets from /public with a stable base to avoid runtime URL errors.
export function pub(path: string): string {
  const base = import.meta.env.BASE_URL || "/";
  const origin =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "http://localhost";

  try {
    // Build against an absolute base so new URL never throws even when base is "/".
    const absoluteBase = new URL(base, origin);
    return new URL(path, absoluteBase).toString();
  } catch {
    // Fallback to simple string concat if something unexpected happens.
    const normalizedBase = base.endsWith("/") ? base : `${base}/`;
    return `${normalizedBase}${path}`;
  }
}
