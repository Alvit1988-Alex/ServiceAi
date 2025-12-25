const rawApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ?? "";
const normalizedApiBaseUrl = rawApiBaseUrl ? rawApiBaseUrl.replace(/\/$/, "") : "/api";

export const API_BASE_URL = normalizedApiBaseUrl;

export function buildWsUrl(path: string): string {
  const base = API_BASE_URL;
  const wsBase = base.startsWith("https") ? base.replace("https", "wss") : base.replace("http", "ws");
  return `${wsBase}${path}`;
}
