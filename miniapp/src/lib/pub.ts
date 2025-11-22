export function pub(path: string): string {
  return new URL(path, import.meta.env.BASE_URL).toString();
}
