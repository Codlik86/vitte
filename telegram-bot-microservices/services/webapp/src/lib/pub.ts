// Resolve assets from /public with a stable base to avoid runtime URL errors.
export function pub(path: string): string {
  // Ensure path starts with / for absolute resolution from root
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  const origin =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "http://localhost";

  try {
    // Build absolute URL from origin + path
    return new URL(normalizedPath, origin).toString();
  } catch {
    // Fallback to simple string concat if something unexpected happens.
    return `${origin}${normalizedPath}`;
  }
}
